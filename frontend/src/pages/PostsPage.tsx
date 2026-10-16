import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, useCallback, useRef } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import { postsApi, type Post, type PostBatchResult, type PostSchedule, type PostNetwork } from "../api/posts"
import { credentialsApi } from "../api/credentials"
import { ApiError } from "../lib/api"
import {
  NETWORK_RULES,
  isNetworkDisabled,
  mediaKind,
  planVariants,
  readMediaInfo,
  validateForNetwork,
  type Issue,
  type MediaInfo,
} from "../lib/networkLimits"
import { TextVariantTabs } from "../components/posts/TextVariantTabs"
import { MediaSummary } from "../components/posts/MediaSummary"
import { MediaTray } from "../components/posts/MediaTray"
import { planMediaComposition } from "../lib/mediaComposition"
import { filterPicked, pickLimits, pickNotice } from "../lib/mediaAdapt"
import { isoToBr, maskDate, maskTime, parseDate, parseTime } from "../lib/ptBrDateTime"
import { moveItem } from "../lib/mediaTray"
import {
  NetworkLimitsPanel,
  NetworkLogo,
  NetworkPicker,
  PICKER_NETWORKS,
  type NetworkState,
} from "../components/posts/NetworkPicker"
import { productsApi, type Product } from "../api/products"
import { aiCredentialsApi } from "../api/credentials"
import { Panel, PanelHeader, Divider } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { IconButton } from "../components/ui/IconButton"
import { Badge } from "../components/ui/Badge"
import { StatusBadge } from "../components/ui/StatusBadge"
import { Modal } from "../components/ui/Modal"
import { TextInput } from "../components/ui/TextInput"
import { Textarea } from "../components/ui/Textarea"
import { Select } from "../components/ui/Select"
import { SegmentedToggle } from "../components/ui/SegmentedToggle"
import { PageSkeleton } from "../components/ui/Skeleton"

// Ver buildSchedule: run_date de segurança do "Agora" (disparado de fato
// assim que a mídia termina de subir).
const NOW_SAFETY_DELAY_MS = 5 * 60 * 1000

const PERSONAS = [
  { value: "casual", label: "Casual" },
  { value: "profissional", label: "Profissional" },
  { value: "divertido", label: "Divertido" },
  { value: "persuasivo", label: "Persuasivo" },
]

// "Data específica" é sempre horário de Brasília, independente do fuso do
// navegador. ponytail: offset fixo -03:00 (Brasil sem horário de verão desde
// 2019); se voltar, trocar por cálculo de offset via Intl.
const SP_OFFSET = "-03:00"
const nowInSaoPaulo = () => {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date())
  const value = (type: Intl.DateTimeFormatPartTypes) => parts.find((part) => part.type === type)?.value ?? ""
  return { day: `${value("year")}-${value("month")}-${value("day")}`, time: `${value("hour")}:${value("minute")}` }
}

// Posts do mesmo envio multi-rede: `group_id` (UUID gerado por envio,
// migração 044). Posts antigos sem group_id: heurística de antes (mesmo
// texto, criados juntos, redes diferentes).
const GROUP_WINDOW_MS = 2 * 60 * 1000
function groupPosts(posts: Post[]): Map<number, { key: number; size: number }> {
  const groups: Post[][] = []
  const byId = new Map<string, Post[]>()
  for (const p of posts) {
    if (p.group_id) {
      const g = byId.get(p.group_id)
      if (g) g.push(p)
      else {
        byId.set(p.group_id, [p])
        groups.push(byId.get(p.group_id)!)
      }
      continue
    }
    const g = groups[groups.length - 1]
    const head = g?.[0]
    const sameGroup =
      head &&
      !head.group_id &&
      head.text === p.text &&
      Math.abs(new Date(head.created_at).getTime() - new Date(p.created_at).getTime()) < GROUP_WINDOW_MS &&
      !g.some((x) => (x.network ?? "threads") === (p.network ?? "threads"))
    if (sameGroup) g.push(p)
    else groups.push([p])
  }
  const out = new Map<number, { key: number; size: number }>()
  for (const g of groups) {
    if (g.length < 2) continue
    const key = Math.min(...g.map((p) => p.id))
    for (const p of g) out.set(p.id, { key, size: g.length })
  }
  return out
}

export interface NetworkResult {
  network: PostNetwork
  ok: boolean
  error?: string
}

const WEEKDAYS = [
  { value: 0, label: "Segunda" },
  { value: 1, label: "Terça" },
  { value: 2, label: "Quarta" },
  { value: 3, label: "Quinta" },
  { value: 4, label: "Sexta" },
  { value: 5, label: "Sábado" },
  { value: 6, label: "Domingo" },
]

const labelStyle = {
  display: "block" as const,
  font: "var(--text-role-label)",
  letterSpacing: "var(--ls-label)",
  textTransform: "uppercase" as const,
  color: "var(--text-muted)",
  marginBottom: 6,
}

const metaTextStyle = {
  font: "var(--fw-regular) var(--fs-caption)/1 var(--font-sans)",
  color: "var(--text-muted)",
}

export function PostsPage() {
  const { logout } = useAuthStore()
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingPost, setEditingPost] = useState<Post | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)

  const { data: postsData, isLoading } = useQuery({
    queryKey: ["posts"],
    queryFn: () => postsApi.list(),
  })
  // Carrega antes da abertura do modal: uma conexão já testada não fica
  // momentaneamente parecendo indisponível no compositor.
  const { data: credentials } = useQuery({
    queryKey: ["credentials"],
    queryFn: () => credentialsApi.list(),
    staleTime: 30_000,
  })

  const posts = postsData?.data ?? []

  const onAuthError = useCallback(
    (err: Error) => {
      if (err.message.includes("401") || err.message === "Não autenticado") {
        logout()
        router.navigate({ to: "/login" })
      }
    },
    [logout],
  )

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
      publishNow: boolean
    }): Promise<NetworkResult[]> => {
      const draftMedia = []
      try {
        for (const file of data.files) draftMedia.push(await postsApi.uploadDraftMedia(file))
        const payload = {
          compositions: data.networks.map((network) => ({ network, texts: data.textsByNetwork[network] ?? [] })),
          product_ids: data.product_ids,
          draft_media_ids: draftMedia.map((draft) => draft.id),
          schedule: data.schedule,
        }
        // O preview compartilha o mesmo planejador do batch; a criação continua
        // a autoridade final para evitar divergência entre o aviso e o envio.
        await postsApi.preview(payload)
        const result: PostBatchResult = await postsApi.createBatch(payload)
        if (data.publishNow) {
          await Promise.all(result.created.map((created) => postsApi.publishNow(created.post_id)))
        }
        return [
          ...result.created.map((created) => ({ network: created.network, ok: true })),
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
          return failed === 0 ? "Post criado" : failed === list.length ? null : `Post criado em ${list.length - failed} de ${list.length} redes`
        },
        error: "Não foi possível criar o post",
      },
    },
    onSuccess: (results, data) => {
      queryClient.invalidateQueries({ queryKey: ["posts"] })
      if (data.publishNow) refreshPublishResult()
      if (results.every((r) => r.ok)) setModalOpen(false)
    },
    onError: onAuthError,
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, texts, product_ids }: { id: number; texts: string[]; product_ids: number[] }) =>
      postsApi.update(id, { texts, product_ids }),
    meta: { toast: { pending: "Salvando post…", success: "Post atualizado", error: "Não foi possível salvar o post" } },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["posts"] })
      setModalOpen(false)
      setEditingPost(null)
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => postsApi.delete(id),
    meta: { toast: { pending: "Removendo post…", success: "Post removido", error: "Não foi possível remover o post" } },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["posts"] })
      setDeleteConfirm(null)
    },
    onError: onAuthError,
  })

  // A publicação roda no scheduler depois do 200: recarrega a lista
  // algumas vezes pra mostrar o resultado real (last_result).
  const refreshPublishResult = () => {
    for (const ms of [5000, 15000, 40000]) {
      setTimeout(() => queryClient.invalidateQueries({ queryKey: ["posts"] }), ms)
    }
  }

  const publishMutation = useMutation({
    mutationFn: (id: number) => postsApi.publishNow(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["posts"] })
      refreshPublishResult()
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
      publishNow: boolean,
    ) => {
      if (editingPost) {
        const texts = textsByNetwork[editingPost.network ?? "threads"] ?? []
        updateMutation.mutate({ id: editingPost.id, texts, product_ids: productIds })
      } else {
        createMutation.mutate({ textsByNetwork, product_ids: productIds, schedule, networks, files, publishNow })
      }
    },
    [editingPost, createMutation, updateMutation],
  )

  if (isLoading) {
    return (
      <PageSkeleton variant="table" titleWidth="140px" subtitleWidth="280px" action toolbar columns={3} />
    )
  }

  const groups = groupPosts(posts)

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap-column)" }}>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <div>
          <h1 style={{ font: "var(--text-role-hero)", color: "var(--text-display)", margin: 0 }}>Posts</h1>
          <p style={{ color: "var(--text-muted)", marginTop: 4, font: "var(--text-role-body)" }}>
            Criação de post (com thread multi-parte) com copy manual ou gerado por IA, agendado
            ou publicado na hora.{" "}
            <span style={{ fontSize: "var(--fs-caption)" }}>(mídia/anexo ainda pelo painel Flask)</span>
          </p>
        </div>
        <Button
          variant="primary"
          icon="plus"
          onClick={() => {
            setEditingPost(null)
            createMutation.reset()
            setModalOpen(true)
          }}
        >
          Novo post
        </Button>
      </div>

      {posts.length === 0 ? (
        <Panel surface="dark">
          <div style={{ padding: 48, textAlign: "center", color: "var(--text-muted)", font: "var(--text-role-body)" }}>
            Nenhum post criado.
          </div>
        </Panel>
      ) : (
        <Panel surface="dark">
          <PanelHeader title="Posts" />
          {posts.map((post, index) => (
            <div key={post.id}>
              {index > 0 && <Divider />}
              <div
                onClick={() => {
                  setEditingPost(post)
                  setModalOpen(true)
                }}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "space-between",
                  gap: 16,
                  padding: "12px 16px",
                  cursor: "pointer",
                }}
              >
                <div style={{ minWidth: 0, flex: 1 }}>
                  <p
                    style={{
                      margin: 0,
                      font: "var(--text-role-body)",
                      color: "var(--text-body)",
                      whiteSpace: "pre-wrap",
                      overflow: "hidden",
                      display: "-webkit-box",
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: "vertical",
                    }}
                  >
                    {post.text}
                  </p>
                  {post.products.length > 0 && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
                      {post.products.map((p) => (
                        <Badge key={p.id} tone="outline">
                          {p.name}
                        </Badge>
                      ))}
                    </div>
                  )}
                  <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 8, flexWrap: "wrap" }}>
                    <Badge tone="outline">
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
                        <NetworkLogo network={post.network ?? "threads"} size={12} />
                        {NETWORK_RULES[post.network ?? "threads"].label}
                      </span>
                    </Badge>
                    {groups.has(post.id) && (
                      <Badge tone="glass">
                        Grupo · {groups.get(post.id)!.size} redes
                      </Badge>
                    )}
                    <span style={metaTextStyle}>{new Date(post.created_at).toLocaleString("pt-BR")}</span>
                    {post.scheduled && (
                      <StatusBadge tone="positive" icon="clock">
                        Agendado
                      </StatusBadge>
                    )}
                    {post.last_result?.status === "published" && (
                      <StatusBadge tone="positive" icon="check-circle-2">
                        Publicado{post.last_result.at ? ` em ${new Date(post.last_result.at).toLocaleString("pt-BR")}` : ""}
                      </StatusBadge>
                    )}
                    {post.last_result?.status === "failed" && (
                      <StatusBadge icon="x-circle" style={{ color: "var(--negative)" }}>
                        Falhou
                      </StatusBadge>
                    )}
                    {!!post.parts_count && post.parts_count > 1 && (
                      <span style={metaTextStyle}>{post.parts_count} partes</span>
                    )}
                  </div>
                  {post.last_result?.status === "failed" && post.last_result.error && (
                    <p style={{ ...metaTextStyle, color: "var(--negative)", marginTop: 8 }}>
                      Última tentativa: {post.last_result.error}
                    </p>
                  )}
                  {publishMutation.isError && publishMutation.variables === post.id && (
                    <p style={{ ...metaTextStyle, color: "var(--negative)", marginTop: 8 }}>
                      {publishMutation.error.message}
                    </p>
                  )}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 4, flex: "0 0 auto" }}>
                  {post.scheduled && (
                    <IconButton
                      icon="send"
                      label="Publicar agora"
                      tone="plain"
                      size={32}
                      className={
                        publishMutation.isPending && publishMutation.variables === post.id ? "animate-spin" : ""
                      }
                      onClick={(e) => {
                        e.stopPropagation()
                        if (publishMutation.isPending) return
                        publishMutation.mutate(post.id)
                      }}
                    />
                  )}
                  <IconButton
                    icon="trash-2"
                    label="Remover post"
                    tone="plain"
                    size={32}
                    onClick={(e) => {
                      e.stopPropagation()
                      setDeleteConfirm(post.id)
                    }}
                  />
                </div>
              </div>
            </div>
          ))}
        </Panel>
      )}

      {modalOpen && (
        <PostModal
          post={editingPost}
          onClose={() => {
            setModalOpen(false)
            setEditingPost(null)
          }}
          onSave={handleSave}
          loading={createMutation.isPending || updateMutation.isPending}
          error={createMutation.error?.message ?? updateMutation.error?.message}
          results={createMutation.data}
          credentials={credentials}
          onClear={() => createMutation.reset()}
        />
      )}

      <Modal open={deleteConfirm != null} onClose={() => setDeleteConfirm(null)} title="Confirmar remoção" width={400}>
        <p style={{ font: "var(--text-role-body)", color: "var(--text-muted)", marginTop: 0, marginBottom: 20 }}>
          Tem certeza que deseja remover este post? Esta ação não pode ser desfeita.
        </p>
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
          <Button variant="ghost" onClick={() => setDeleteConfirm(null)}>
            Cancelar
          </Button>
          <Button
            variant="send"
            disabled={deleteMutation.isPending}
            onClick={() => deleteConfirm != null && deleteMutation.mutate(deleteConfirm)}
          >
            {deleteMutation.isPending ? "Removendo..." : "Remover"}
          </Button>
        </div>
      </Modal>
    </div>
  )
}

// ── Modal de criação/edição ─────────────────────────────────────────────────────

interface PostModalProps {
  post: Post | null
  onClose: () => void
  onSave: (
    textsByNetwork: Partial<Record<PostNetwork, string[]>>,
    productIds: number[],
    schedule: PostSchedule,
    networks: PostNetwork[],
    files: File[],
    publishNow: boolean,
  ) => void
  loading: boolean
  error?: string
  /** Resultado por rede do último envio (só falhas mantêm o modal aberto). */
  results?: NetworkResult[]
  credentials?: Awaited<ReturnType<typeof credentialsApi.list>>
  onClear: () => void
}

type WhenOption = "now" | "date" | "cron"

function PostModal({ post, onClose, onSave, loading, error, results, credentials, onClear }: PostModalProps) {
  const queryClient = useQueryClient()
  const [texts, setTexts] = useState<string[]>(
    post?.texts && post.texts.length > 0 ? post.texts : [""],
  )
  // Textos das abas além da principal (texts[0]), por chave de faixa de
  // limite (planVariants). Sem entrada = começa igual ao texto principal.
  const [variantTexts, setVariantTexts] = useState<Record<string, string>>({})
  const [persona, setPersona] = useState("casual")
  const [networks, setNetworks] = useState<PostNetwork[]>(post ? [post.network ?? "threads"] : [])
  const [selectedProductIds, setSelectedProductIds] = useState<number[]>(
    post?.products.map((p) => p.id) ?? [],
  )
  const [when, setWhen] = useState<WhenOption>("now")
  // Data/hora são texto pt-BR (dd/mm/aaaa, hh:mm); runDay/runTime/cronTime são
  // o valor já validado (ISO / HH:MM) ou "" se o texto está incompleto/inválido.
  const [runDayText, setRunDayText] = useState(() => isoToBr(nowInSaoPaulo().day))
  const [runTimeText, setRunTimeText] = useState(() => nowInSaoPaulo().time)
  const [cronTimeText, setCronTimeText] = useState("09:00")
  const runDay = parseDate(runDayText) ?? ""
  const runTime = parseTime(runTimeText) ?? ""
  const cronTime = parseTime(cronTimeText) ?? ""
  const [cronDays, setCronDays] = useState<number[]>([0])
  const [pendingFiles, setPendingFiles] = useState<{ file: File; info: MediaInfo }[]>([])
  const [trayOpen, setTrayOpen] = useState(false)
  const [pickMessage, setPickMessage] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  // Redes que já deram certo no último envio saem da seleção: reenviar só
  // repete as que falharam, sem duplicar post.
  const [handledResults, setHandledResults] = useState<NetworkResult[] | undefined>(undefined)
  if (results && results !== handledResults) {
    setHandledResults(results)
    setNetworks((prev) => prev.filter((n) => !results.some((r) => r.network === n && r.ok)))
  }

  const { data: productsData } = useQuery({
    queryKey: ["products", ""],
    queryFn: () => productsApi.list(),
  })
  const products = productsData?.data ?? []

  // Sem chave de IA própria não há o que chamar (não existe chave global):
  // em vez do botão, atalho pra Credenciais.
  const { data: aiStatus } = useQuery({
    queryKey: ["credentials", "ai"],
    queryFn: () => aiCredentialsApi.list(),
  })
  const hasAiKey = aiStatus ? aiStatus.active !== null : true

  const generateMutation = useMutation({
    mutationFn: (productId: number) => postsApi.generateCopy(productId, persona, networks),
    onSuccess: (res) => {
      setTexts((prev) => [res.text, ...prev.slice(1)])
      const rest = (res.variants ?? []).slice(1)
      setVariantTexts((prev) => ({ ...prev, ...Object.fromEntries(rest.map((v) => [v.key, v.text])) }))
    },
  })

  // upload/remoção de mídia num post já existente (edição) rodam na
  // hora — o post_id já existe. Num post novo, os arquivos ficam em
  // pendingFiles e sobem só depois que o post é criado (ver PostsPage).
  const addMediaMutation = useMutation({
    mutationFn: (file: File) => postsApi.uploadMedia(post!.id, file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["posts"] }),
  })

  const deleteMediaMutation = useMutation({
    mutationFn: (mediaId: number) => postsApi.deleteMedia(post!.id, mediaId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["posts"] }),
  })

  const toggleProduct = (id: number) => {
    setSelectedProductIds((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id],
    )
  }

  const setPartText = (index: number, value: string) => {
    setTexts((prev) => prev.map((t, i) => (i === index ? value : t)))
  }

  const addPart = () => setTexts((prev) => [...prev, ""])
  const removePart = (index: number) => setTexts((prev) => prev.filter((_, i) => i !== index))
  const clearComposer = () => {
    const now = nowInSaoPaulo()
    setTexts([""])
    setVariantTexts({})
    setNetworks([])
    setSelectedProductIds([])
    setPendingFiles([])
    setTrayOpen(false)
    setWhen("now")
    setRunDayText(isoToBr(now.day))
    setRunTimeText(now.time)
    setCronTimeText("09:00")
    setPickMessage(null)
    setCronDays([0])
    onClear()
  }

  const buildSchedule = (): PostSchedule => {
    if (when === "cron") {
      return { trigger: "cron", time: cronTime, days_of_week: cronDays }
    }
    // "Agora" = rede de segurança de 5 min: o post é disparado explicitamente
    // logo após o envio da mídia (ver createMutation), sem duplicar.
    const runAt =
      when === "now" ? new Date(Date.now() + NOW_SAFETY_DELAY_MS) : (scheduledAt ?? new Date(NaN))
    return { trigger: "date", run_date: runAt.toISOString() }
  }

  const trimmedTexts = texts.map((t) => t.trim()).filter(Boolean)
  const activeNetworks = networks.filter((n) => !isNetworkDisabled(n))

  // Data específica: dia + hora em America/Sao_Paulo; precisa ser futura.
  const scheduledAt = runDay && runTime ? new Date(`${runDay}T${runTime}:00${SP_OFFSET}`) : null
  const INVALID_TIME = "Hora inválida. Use hh:mm (24 horas)."
  const dateError =
    when === "cron"
      ? (cronTime ? null : INVALID_TIME)
      : when !== "date"
        ? null
        : !runDay
          ? "Data inválida. Use dd/mm/aaaa."
          : !scheduledAt
            ? INVALID_TIME
            : !(scheduledAt.getTime() > Date.now())
              ? "Essa data/hora já passou (horário de Brasília)."
              : null

  // Conjunto mínimo de textos pras redes marcadas: abas só com 2+ faixas.
  const plans = planVariants(activeNetworks)
  const hasTabs = !post && plans.length > 1
  const variantValue = (i: number) => (i === 0 ? texts[0] : (variantTexts[plans[i].key] ?? texts[0]))
  const setVariantValue = (i: number, value: string) =>
    i === 0 ? setPartText(0, value) : setVariantTexts((prev) => ({ ...prev, [plans[i].key]: value }))

  // Parte 1 que cada rede publica. Rede ainda não marcada que formaria uma
  // faixa nova ganharia a própria aba: o texto dela não bloqueia marcá-la.
  const headFor = (n: PostNetwork): string => {
    const selected = networks.includes(n)
    const p = selected ? plans : planVariants([...networks, n])
    const i = p.findIndex((v) => v.networks.includes(n))
    if (post || p.length < 2 || i <= 0) return texts[0]
    return variantTexts[p[i].key] ?? (selected ? texts[0] : "")
  }
  const textsFor = (n: PostNetwork) => [headFor(n), ...texts.slice(1)].map((t) => t.trim()).filter(Boolean)

  // Validação por rede em tempo real (lib/networkLimits.ts), cada uma com o seu texto.
  const media: MediaInfo[] = post
    ? post.medias.map((m) => ({ name: m.file_name, size: m.size, kind: m.type === "VIDEO" ? "video" : mediaKind(m.file_name) }))
    : pendingFiles.map((p) => p.info)
  // Seletor: máximo absoluto por tipo entre as redes marcadas.
  const limits = pickLimits(activeNetworks.map((n) => NETWORK_RULES[n]))
  const draftFor = (n: PostNetwork) => {
    const t = textsFor(n)
    return { texts: t.length ? t : [""], media, productCount: selectedProductIds.length }
  }
  // Na aba: só o que o TEXTO causa (erros com o texto menos erros sem ele).
  const variantIssues = plans.map((plan, i) =>
    plan.networks.flatMap((n) => {
      const check = (text: string) =>
        validateForNetwork(n, { texts: [text], media: [], productCount: 1 }).filter((x) => x.level === "error")
      const base = new Set(check("").map((x) => x.message))
      return check(variantValue(i).trim()).filter((x) => !base.has(x.message))
    }),
  )
  const compositionPlans = Object.fromEntries(
    PICKER_NETWORKS.map((n) => [n, planMediaComposition(n, draftFor(n))]),
  ) as Record<PostNetwork, ReturnType<typeof planMediaComposition>>
  // Post novo: a rede só é cobrada pelo que ela realmente recebe (mídia adaptada).
  const issues = Object.fromEntries(
    PICKER_NETWORKS.map((n) => [
      n,
      validateForNetwork(n, post ? draftFor(n) : { ...draftFor(n), media: compositionPlans[n].media }),
    ]),
  ) as Record<PostNetwork, Issue[]>
  const states = Object.fromEntries(
    PICKER_NETWORKS.map((n) => {
      const status = credentials?.[n]
      const loaded = credentials !== undefined
      const functional = status?.state === "ok"
      const connectionReason = !loaded
        ? "verificando conexão"
        : functional
          ? undefined
          : status?.state === "disconnected"
            ? "conecte em Credenciais"
            : status?.status_text ?? "teste a conexão em Credenciais"
      const plan = compositionPlans[n]
      // Conta do X sem media.write: avisa antes do primeiro upload (o servidor também bloqueia).
      const xNoMedia =
        n === "x" && plan.media.length > 0 && status?.missing_scopes?.includes("media.write")
          ? [{ key: "x_media_scope", level: "error" as const, message: "Reconecte o X para liberar imagens" }]
          : []
      const errors = xNoMedia.length > 0 ? xNoMedia : plan.mode === "blocked"
        ? issues[n].filter((issue) => issue.level === "error").concat(
          issues[n].some((issue) => issue.message === plan.blockedReason)
            ? []
            : plan.blockedReason ? [{ key: "composition", level: "error" as const, message: plan.blockedReason }] : [],
        )
        : []
      return [n, { connected: loaded ? functional : undefined, connectionReason, errors }]
    }),
  ) as Record<PostNetwork, NetworkState>
  const deliverableNetworks = activeNetworks.filter((n) => compositionPlans[n].mode !== "blocked")
  const trayItems = pendingFiles.flatMap((p, index) => (p.info.kind === "video" ? [] : [{ file: p.file, index }]))
  const showTray = !post && (trayItems.length >= 2 || trayOpen)
  const trayNotes = trayItems.length < 2 ? [] : activeNetworks.flatMap((n) => {
    const plan = compositionPlans[n]
    if (plan.mode === "blocked") return [`${NETWORK_RULES[n].label}: bloqueada`]
    if (plan.mode === "text_only") return [`${NETWORK_RULES[n].label}: só texto`]
    if (plan.dropped.length) return [`${NETWORK_RULES[n].label}: recebe ${plan.media.length} de ${media.length}`]
    return []
  })

  const toggleNetwork = (n: PostNetwork) => {
    if (isNetworkDisabled(n)) return
    setNetworks((prev) => (prev.includes(n) ? prev.filter((x) => x !== n) : [...prev, n]))
  }

  const canSubmit =
    !loading &&
    trimmedTexts.length > 0 &&
    // Bloqueadas continuam marcadas (em vermelho, com motivo); basta uma entregável.
    deliverableNetworks.length > 0 &&
    deliverableNetworks.every((n) => textsFor(n).length > 0) &&
    deliverableNetworks.every((n) => states[n].connected === true) &&
    !dateError

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    onSave(
      Object.fromEntries(activeNetworks.map((n) => [n, textsFor(n)])),
      selectedProductIds,
      buildSchedule(),
      activeNetworks,
      pendingFiles.map((p) => p.file),
      when === "now",
    )
  }

  return (
    <Modal open onClose={onClose} title={post ? "Editar post" : "Novo post"} width={560}>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div>
          <span style={labelStyle}>{post ? "Rede social" : "Redes sociais * (uma ou mais)"}</span>
          <NetworkPicker selected={activeNetworks} states={states} onToggle={toggleNetwork} readOnly={!!post} />
        </div>

        <div>
          <span style={labelStyle}>Produtos</span>
          <div
            style={{
              maxHeight: 140,
              overflowY: "auto",
              border: "1px solid var(--border-hairline)",
              borderRadius: "var(--r-md)",
              background: "var(--surface-inset)",
              padding: 8,
              display: "flex",
              flexDirection: "column",
              gap: 2,
            }}
          >
            {products.length === 0 && (
              <p style={{ ...metaTextStyle, padding: "2px 4px" }}>Nenhum produto cadastrado ainda.</p>
            )}
            {products.map((product: Product) => (
              <label
                key={product.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "4px 6px",
                  borderRadius: "var(--r-sm)",
                  cursor: "pointer",
                  font: "var(--text-role-body)",
                  color: "var(--text-body)",
                }}
              >
                <input
                  type="checkbox"
                  checked={selectedProductIds.includes(product.id)}
                  onChange={() => toggleProduct(product.id)}
                  style={{ accentColor: "var(--sky-400)", width: 15, height: 15 }}
                />
                {product.name}
              </label>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "flex-end", gap: 8, flexWrap: "wrap" }}>
          <Select
            label="Persona da IA"
            value={persona}
            onChange={(e) => setPersona(e.target.value)}
            options={PERSONAS}
            width={200}
          />
          {hasAiKey ? (
            <Button
              type="button"
              variant="secondary"
              icon={generateMutation.isPending ? "loader-2" : "sparkles"}
              disabled={selectedProductIds.length === 0 || generateMutation.isPending}
              onClick={() => generateMutation.mutate(selectedProductIds[0])}
            >
              {generateMutation.isPending ? "Gerando..." : "Gerar texto com IA"}
            </Button>
          ) : (
            <Button
              type="button"
              variant="secondary"
              icon="sparkles"
              onClick={() => router.navigate({ to: "/credentials" })}
            >
              Cadastre sua chave de IA em Credenciais
            </Button>
          )}
        </div>
        {generateMutation.isError && (
          <p style={{ ...metaTextStyle, color: "var(--negative)" }}>{generateMutation.error.message}</p>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {texts.map((partText, index) =>
            index === 0 && hasTabs ? (
              <div key={index} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <span style={{ ...labelStyle, marginBottom: 0 }}>Texto do post *</span>
                <TextVariantTabs
                  plans={plans}
                  values={plans.map((_, i) => variantValue(i))}
                  onChange={setVariantValue}
                  issues={variantIssues}
                />
              </div>
            ) : (
            <div key={index} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ ...labelStyle, marginBottom: 0 }}>
                  {index === 0 ? "Texto do post *" : `Parte ${index + 1} (resposta em thread)`}
                </span>
                {texts.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removePart(index)}
                    style={{
                      background: "none",
                      border: "none",
                      padding: 0,
                      color: "var(--red-300)",
                      font: "var(--fw-medium) var(--fs-caption)/1 var(--font-sans)",
                      cursor: "pointer",
                    }}
                  >
                    Remover parte
                  </button>
                )}
              </div>
              <Textarea
                value={partText}
                onChange={(e) => setPartText(index, e.target.value)}
                required={index === 0}
                rows={index === 0 ? 6 : 3}
              />
            </div>
            ),
          )}
          <Button type="button" variant="ghost" icon="plus" onClick={addPart} style={{ alignSelf: "flex-start", padding: 0 }}>
            Adicionar parte (thread)
          </Button>
        </div>

        <div>
          <span style={labelStyle}>Mídia (imagem/vídeo)</span>
          {post && post.medias.length > 0 && (
            <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 6, marginBottom: 8 }}>
              {post.medias.map((media) => (
                <li
                  key={media.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 8,
                    padding: "6px 10px",
                    borderRadius: "var(--r-sm)",
                    background: "var(--surface-inset)",
                    font: "var(--fw-regular) var(--fs-caption)/1 var(--font-sans)",
                    color: "var(--text-body)",
                  }}
                >
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {media.file_name}
                  </span>
                  <button
                    type="button"
                    onClick={() => deleteMediaMutation.mutate(media.id)}
                    disabled={deleteMediaMutation.isPending}
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--red-300)",
                      cursor: "pointer",
                      font: "inherit",
                      flex: "0 0 auto",
                      opacity: deleteMediaMutation.isPending ? 0.5 : 1,
                    }}
                  >
                    Remover
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "8px 12px",
              borderRadius: "var(--r-md)",
              background: "var(--surface-inset)",
              border: "1px solid var(--border-hairline)",
            }}
          >
            {/* Input nativo escondido: o navegador mostraria "Choose File" em inglês. */}
            <input
              ref={fileInputRef}
              type="file"
              hidden
              accept={limits.exts.map((e) => `.${e}`).join(",")}
              multiple={!post}
              onChange={(e) => {
                const picked = Array.from(e.target.files ?? [])
                e.target.value = ""
                if (picked.length === 0) return
                const { accepted, ignored, overLimit } = filterPicked(picked, media.map((m) => m.kind), limits)
                setPickMessage(pickNotice({ ignored, overLimit }))
                if (accepted.length === 0) return
                if (post) {
                  addMediaMutation.mutate(accepted[0])
                } else {
                  // Promise.all mantém a ordem escolhida no seletor.
                  Promise.all(accepted.map(async (file) => ({ file, info: await readMediaInfo(file) }))).then((added) =>
                    setPendingFiles((prev) => [...prev, ...added]),
                  )
                }
              }}
            />
            <Button type="button" variant="ghost" onClick={() => fileInputRef.current?.click()}>
              Escolher arquivos
            </Button>
            <span style={metaTextStyle}>
              {post || pendingFiles.length === 0
                ? "Nenhum arquivo escolhido"
                : `${pendingFiles.length} ${pendingFiles.length === 1 ? "arquivo" : "arquivos"}`}
            </span>
          </div>
          {pickMessage && (
            <p role="status" style={{ ...metaTextStyle, color: "var(--amber-300)", marginTop: 6 }}>
              {pickMessage}
            </p>
          )}
          {showTray && (
            <MediaTray
              items={trayItems}
              limit={Number.isFinite(limits.max.image) ? limits.max.image : undefined}
              notes={trayNotes}
              onMove={(from, to) => setPendingFiles((prev) => moveItem(prev, from, to))}
              onRemove={(index) => setPendingFiles((prev) => prev.filter((_, i) => i !== index))}
            />
          )}
          {!post && !showTray && pendingFiles.some((p) => p.info.kind !== "video") && (
            <Button type="button" variant="ghost" onClick={() => setTrayOpen(true)} style={{ alignSelf: "flex-start", padding: 0, marginTop: 6 }}>
              Montar carrossel/álbum
            </Button>
          )}
          {!post && pendingFiles.some((p) => !showTray || p.info.kind === "video") && (
            <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
              {pendingFiles.map(({ file, info }, index) => !showTray || info.kind === "video" ? (
                <li
                  key={index}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 8,
                    padding: "6px 10px",
                    borderRadius: "var(--r-sm)",
                    background: "var(--surface-inset)",
                    font: "var(--fw-regular) var(--fs-caption)/1 var(--font-sans)",
                    color: "var(--text-body)",
                  }}
                >
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {file.name}
                    <span style={{ color: "var(--text-muted)" }}>
                      {" "}· {(file.size / (1024 * 1024)).toFixed(1)} MB
                      {info.width ? ` · ${info.width}×${info.height}` : ""}
                      {info.durationSec != null ? ` · ${Math.round(info.durationSec)} s` : ""}
                    </span>
                  </span>
                  <button
                    type="button"
                    onClick={() => setPendingFiles((prev) => prev.filter((_, i) => i !== index))}
                    style={{ background: "none", border: "none", color: "var(--red-300)", cursor: "pointer", font: "inherit", flex: "0 0 auto" }}
                  >
                    Remover
                  </button>
                </li>
              ) : null)}
            </ul>
          )}
          {addMediaMutation.isError && (
            <p style={{ ...metaTextStyle, color: "var(--negative)", marginTop: 6 }}>
              {addMediaMutation.error.message}
            </p>
          )}
        </div>

        <NetworkLimitsPanel
          selected={activeNetworks}
          textFor={(n) => textsFor(n)[0] ?? ""}
          mediaCount={(n) => (post ? media.length : compositionPlans[n].media.length)}
          issues={issues}
        />

        {!post && <MediaSummary networks={activeNetworks} plans={compositionPlans} />}

        {!post && (
          <Button type="button" variant="ghost" icon="x" onClick={clearComposer} style={{ alignSelf: "flex-start" }}>
            Limpar post
          </Button>
        )}

        {!post && (
          <div>
            <span style={labelStyle}>Quando publicar? *</span>
            <div style={{ marginBottom: 12 }}>
              <SegmentedToggle
                options={[
                  { value: "now", label: "Agora" },
                  { value: "date", label: "Agendar" },
                  { value: "cron", label: "Recorrente" },
                ]}
                value={when}
                onChange={(value) => setWhen(value as WhenOption)}
                fullWidth
              />
            </div>

            {when === "date" && (
              <div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12 }}>
                  <TextInput
                    label="Dia"
                    value={runDayText}
                    placeholder="dd/mm/aaaa"
                    inputMode="numeric"
                    onChange={(e) => setRunDayText(maskDate(e.target.value))}
                    required
                  />
                  <TextInput
                    label="Hora"
                    value={runTimeText}
                    placeholder="hh:mm"
                    inputMode="numeric"
                    onChange={(e) => setRunTimeText(maskTime(e.target.value))}
                    required
                  />
                </div>
                <p role="status" style={{ ...metaTextStyle, marginTop: 6, color: dateError ? "var(--negative)" : "var(--text-muted)" }}>
                  {dateError ?? "Horário de Brasília (America/Sao_Paulo)."}
                </p>
              </div>
            )}

            {when === "cron" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                  <span style={{ ...labelStyle, marginBottom: 0 }}>Dias da semana</span>
                  <button
                    type="button"
                    onClick={() => setCronDays((days) => (days.length === WEEKDAYS.length ? [0] : WEEKDAYS.map((day) => day.value)))}
                    style={{ background: "none", border: "none", padding: 0, color: "var(--accent)", cursor: "pointer", font: "var(--text-role-caption)" }}
                  >
                    {cronDays.length === WEEKDAYS.length ? "Somente segunda" : "Semana inteira"}
                  </button>
                </div>
                <div role="group" aria-label="Dias recorrentes" style={{ display: "grid", gridTemplateColumns: "repeat(7, minmax(0, 1fr))", gap: 6 }}>
                  {WEEKDAYS.map((day) => {
                    const selected = cronDays.includes(day.value)
                    return (
                      <button
                        key={day.value}
                        type="button"
                        aria-pressed={selected}
                        title={day.label}
                        onClick={() => setCronDays((days) => selected ? (days.length === 1 ? days : days.filter((value) => value !== day.value)) : [...days, day.value].sort((a, b) => a - b))}
                        style={{ minHeight: 36, borderRadius: "var(--r-sm)", border: `1px solid ${selected ? "var(--accent)" : "var(--border-hairline)"}`, background: selected ? "var(--accent-tint)" : "var(--surface-inset)", color: selected ? "var(--accent)" : "var(--text-body)", cursor: "pointer", font: "var(--text-role-caption)" }}
                      >
                        {day.label.slice(0, 3)}
                      </button>
                    )
                  })}
                </div>
                <TextInput
                  label="Hora"
                  value={cronTimeText}
                  placeholder="hh:mm"
                  inputMode="numeric"
                  onChange={(e) => setCronTimeText(maskTime(e.target.value))}
                />
                {dateError && (
                  <p role="status" style={{ ...metaTextStyle, color: "var(--negative)" }}>
                    {dateError}
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {error && <p style={{ ...metaTextStyle, color: "var(--negative)" }}>{error}</p>}

        {!post && results && results.length > 0 && (
          <ul aria-live="polite" style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 4 }}>
            {results.map((r) => (
              <li
                key={r.network}
                style={{ ...metaTextStyle, lineHeight: 1.4, color: r.ok ? "var(--text-body)" : "var(--negative)" }}
              >
                {NETWORK_RULES[r.network].label}: {r.ok ? "criado ✓" : `falhou — ${r.error}`}
              </li>
            ))}
            <li style={{ ...metaTextStyle, lineHeight: 1.4 }}>
              As redes que deram certo foram desmarcadas; corrija e envie de novo só as que falharam.
            </li>
          </ul>
        )}

        {!post && activeNetworks.length === 0 && (
          <p style={{ ...metaTextStyle, margin: 0 }}>Escolha ao menos uma rede para publicar.</p>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, paddingTop: 4 }}>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" disabled={!canSubmit}>
            {loading ? "Salvando..." : post ? "Salvar" : activeNetworks.length > 1 ? `Criar em ${activeNetworks.length} redes` : "Criar"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
