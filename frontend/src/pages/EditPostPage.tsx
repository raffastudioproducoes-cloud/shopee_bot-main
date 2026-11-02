import { useCallback, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useParams } from "@tanstack/react-router"
import { postsApi, type PostNetwork, type PostSchedule } from "../api/posts"
import { credentialsApi } from "../api/credentials"
import { PostComposer } from "../components/posts/PostComposer"
import { router } from "../router"
import { useProfileStore } from "../stores/profileStore"

/** A edição nunca cria outro post nem publica novamente: mantém o ID original. */
export function EditPostPage() {
  const { postId } = useParams({ from: "/panel/posts/$postId/editar" })
  const id = Number(postId)
  const validId = Number.isSafeInteger(id) && id > 0
  const activeProfileId = useProfileStore((state) => state.activeProfileId)
  const queryClient = useQueryClient()
  const [localWarning, setLocalWarning] = useState<string | null>(null)

  const postQuery = useQuery({
    queryKey: ["post-details", activeProfileId, id],
    queryFn: () => postsApi.get(id),
    enabled: validId && !!activeProfileId,
    retry: false,
  })
  const credentialsQuery = useQuery({
    queryKey: ["credentials"],
    queryFn: credentialsApi.list,
    staleTime: 30_000,
  })
  const updateMutation = useMutation({
    mutationFn: async ({ texts, productIds }: { texts: string[]; productIds: number[] }) =>
      (postQuery.data?.scheduled
        ? postsApi.updateFuture(id, { texts, product_ids: productIds })
        : postsApi.update(id, { texts, product_ids: productIds })),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["posts"] }),
        queryClient.invalidateQueries({ queryKey: ["post-details", activeProfileId, id] }),
      ])
      void router.navigate({ to: "/posts" })
    },
    meta: { toast: { success: "Post atualizado", error: "Não foi possível atualizar o post" } },
  })

  const handleSave = useCallback((
    textsByNetwork: Partial<Record<PostNetwork, string[]>>,
    productIds: number[],
    _schedule: PostSchedule,
    _networks: PostNetwork[],
    files: File[],
    productImageIds: number[],
  ) => {
    const post = postQuery.data
    if (!post) return
    // Manter mídias originais; novos uploads não podem modificar slots bloqueados.
    if (files.length || productImageIds.length) {
      setLocalWarning("Novas fotos e vídeos para posts já agendados ainda não podem ser salvos nesta revisão. As mídias anteriores foram preservadas.")
      return
    }
    setLocalWarning(null)
    const originalNetwork = post.network ?? "threads"
    updateMutation.mutate({
      texts: textsByNetwork[originalNetwork] ?? [],
      productIds,
    })
  }, [postQuery.data, updateMutation])

  const goBack = () => void router.navigate({ to: "/posts" })
  if (!validId) return <p role="alert">Identificador de post inválido.</p>
  if (postQuery.isPending) return <p role="status">Carregando post #{id}…</p>
  if (postQuery.isError || !postQuery.data) return (
    <div role="alert">
      <p>Não foi possível encontrar este post no perfil ativo.</p>
      <button type="button" onClick={goBack}>Voltar aos posts</button>
    </div>
  )

  const post = postQuery.data
  const postForEditor = post.future_revision?.texts?.length
    ? { ...post, texts: post.future_revision.texts }
    : post
  return (
    <div className="edit-post-page" style={{ width: "100%", paddingBottom: 32 }}>
      <header style={{ marginBottom: 22 }}>
        <h1>Editar POST #{post.id}</h1>
        <p style={{ color: "var(--text-muted)" }}>
          O identificador permanece o mesmo. Uma edição agendada só vale para ocorrências
          pendentes a mais de 30 minutos; publicações já iniciadas ou concluídas não mudam.
        </p>
      </header>
      <PostComposer
        key={post.id}
        post={postForEditor}
        onClose={goBack}
        onSave={handleSave}
        loading={updateMutation.isPending}
        error={localWarning ?? updateMutation.error?.message}
        credentials={credentialsQuery.data}
        onClear={() => { updateMutation.reset(); setLocalWarning(null) }}
      />
    </div>
  )
}
