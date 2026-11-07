import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useCallback, useState } from "react"
import { useAuthStore } from "../stores/authStore"
import { useProfileStore } from "../stores/profileStore"
import { router } from "../router"
import { postsApi, type PostBatchResult, type PostSchedule, type PostNetwork } from "../api/posts"
import { credentialsApi } from "../api/credentials"
import { ApiError } from "../lib/api"
import { formDraftKey, clearFormDraft } from "../lib/formDraftStorage"
import { PostComposer, type NetworkResult } from "../components/posts/PostComposer"
import { CampaignPlanner } from "../components/campaigns/CampaignPlanner"
import { ResourceQuotaBar } from "../components/plans/ProductQuotaBar"
import { usePlanUsage } from "../hooks/usePlanUsage"
import { SegmentedToggle } from "../components/ui/SegmentedToggle"

/** Página dedicada de criação. Preserva o fluxo de envio e o rascunho anterior. */
export function CreatePostPage() {
  const { logout } = useAuthStore()
  const [creationMode, setCreationMode] = useState<"single" | "campaign">("single")
  const activeProfileId = useProfileStore((state) => state.activeProfileId)
  const queryClient = useQueryClient()
  const planQuery = usePlanUsage()

  // Carrega antes do editor: uma conexão já testada não fica
  // momentaneamente parecendo indisponível no compositor.
  const { data: credentials } = useQuery({
    queryKey: ["credentials", activeProfileId],
    queryFn: () => credentialsApi.list(),
    staleTime: 30_000,
    enabled: Boolean(activeProfileId),
  })

  const onAuthError = useCallback(
    (err: Error) => {
      if (err.message.includes("401") || err.message === "Não autenticado") {
        logout()
        router.navigate({ to: "/login" })
      }
    },
    [logout],
  )

  // A publicação roda no scheduler depois do 200: recarrega a lista
  // algumas vezes pra mostrar o resultado real (last_result).
  const refreshPublishResult = () => {
    for (const ms of [5000, 15000, 40000]) {
      setTimeout(() => queryClient.invalidateQueries({ queryKey: ["posts"] }), ms)
    }
  }

  const createMutation = useMutation({
    // Um post por rede. A mídia sobe UMA vez (no 1º post criado) e as outras
    // redes reaproveitam os mesmos media_ids. Falha numa rede não cancela as
    // outras: cada uma volta com seu resultado.
    mutationFn: async (data: {
      textsByNetwork: Partial<Record<PostNetwork, string[]>>
      product_ids: number[]
      schedule: PostSchedule
      networks: PostNetwork[]
      files: File[]
      productImageIds: number[]
      publishNow: boolean
    }): Promise<NetworkResult[]> => {
      const draftMedia = []
      try {
        // Antes de enviar arquivos ao Storage, verificar se há worker ativo.
        // O backend repete a verificação imediatamente antes de criar posts.
        const scheduler = await postsApi.schedulerStatus()
        if (!scheduler.available) throw new Error(scheduler.message)
        for (const file of data.files) draftMedia.push(await postsApi.uploadDraftMedia(file))
        for (const productId of data.productImageIds) draftMedia.push(await postsApi.importProductImageDraft(productId))
        const payload = {
          compositions: data.networks.map((network) => ({ network, texts: data.textsByNetwork[network] ?? [] })),
          product_ids: data.product_ids,
          draft_media_ids: draftMedia.map((draft) => draft.id),
          schedule: data.schedule,
          publish_immediately: data.publishNow,
        }
        // O preview compartilha o mesmo planejador do batch; a criação continua
        // a autoridade final para evitar divergência entre o aviso e o envio.
        await postsApi.preview(payload)
        const result: PostBatchResult = await postsApi.createBatch(payload)
        // O lote já pode ter gravado posts antes de um erro de dispatch.
        // Um 502 no disparo NÃO transforma um post existente em "falha de criação":
        // a agenda de segurança permanece e reenviar o formulário duplicaria posts.
        const dispatch = data.publishNow
          ? await Promise.allSettled(result.created.map((created) => postsApi.publishNow(created.post_id)))
          : []
        return [
          ...result.created.map((created, index) => ({
            network: created.network,
            ok: true,
            postId: created.post_id,
            warning: data.publishNow && dispatch[index]?.status === "rejected"
              ? "Post criado, mas o disparo imediato não foi confirmado. Confira o histórico antes de tentar novamente."
              : undefined,
          })),
          ...result.blocked.map((blocked) => ({ network: blocked.network, ok: false, error: blocked.blocked_reason ?? blocked.warnings[0] ?? "Esta rede não aceita esta composição." })),
        ]
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) onAuthError(err)
        throw err
      } finally {
        // Somente drafts ainda prontos são excluídos; os consumidos pelo lote
        // permanecem ligados aos posts criados pelo servidor.
        await Promise.all(draftMedia.map((draft) => postsApi.deleteDraftMedia(draft.id).catch(() => undefined)))
      }
    },
    // Resultado por rede continua no modal; o aviso só resume.
    meta: {
      toast: {
        pending: "Criando post…",
        success: (results: unknown) => {
          const list = results as NetworkResult[]
          const failed = list.filter((r) => !r.ok).length
          const pendingDispatch = list.some((r) => r.warning)
          if (failed === list.length) return null
          if (pendingDispatch) return "Post salvo, mas algum disparo não foi confirmado. Confira o histórico."
          return failed === 0 ? "Post criado" : `Post criado em ${list.length - failed} de ${list.length} redes`
        },
        error: "Não foi possível criar o post",
      },
    },
    onSuccess: (results, data) => {
      queryClient.invalidateQueries({ queryKey: ["posts"] })
      if (data.publishNow) refreshPublishResult()
      if (results.every((r) => r.ok)) {
        clearFormDraft(formDraftKey(useAuthStore.getState().user?.id, "post-create", activeProfileId))
        void router.navigate({ to: "/posts" })
      }
    },
    onError: onAuthError,
  })

  const handleSave = useCallback(
    (
      textsByNetwork: Partial<Record<PostNetwork, string[]>>,
      productIds: number[],
      schedule: PostSchedule,
      networks: PostNetwork[],
      files: File[],
      productImageIds: number[],
      publishNow: boolean,
    ) => {
      createMutation.mutate({ textsByNetwork, product_ids: productIds, schedule, networks, files, productImageIds, publishNow })
    },
    [createMutation],
  )

  return (
    <div className="create-post-page">
      <header className="create-post-page-header">
        <h1 className="csp-s-0315">Criar POST</h1>
        <p>{creationMode === "single" ? "Prepare a publicação, adapte o conteúdo por rede e escolha quando enviar." : "Prepare o rascunho, confira os horários e ative a campanha conforme o plano."}</p>
      </header>
      <div style={{ maxWidth: 510, width: "100%", marginBottom: "var(--sp-8)" }}>
        <SegmentedToggle
          options={[{ value: "single", label: "Publicação única" }, { value: "campaign", label: "Campanha por lista" }]}
          value={creationMode}
          onChange={(mode) => setCreationMode(mode as "single" | "campaign")}
        />
      </div>
      <ResourceQuotaBar
        resource={creationMode === "campaign" ? "campaigns" : "publishing"}
        plan={planQuery.data}
        loading={planQuery.isPending}
        error={planQuery.isError}
        onUpgrade={() => void router.navigate({ to: "/settings", hash: "planos" })}
      />
      {creationMode === "campaign" ? <CampaignPlanner key={activeProfileId} credentials={credentials} /> : <PostComposer
        post={null}
        onClose={() => void router.navigate({ to: "/posts" })}
        onSave={handleSave}
        loading={createMutation.isPending}
        error={createMutation.error?.message}
        results={createMutation.data}
        credentials={credentials}
        onClear={() => createMutation.reset()}
      />}
    </div>
  )
}

