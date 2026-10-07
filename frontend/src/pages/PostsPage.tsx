import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, useCallback } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import { postsApi, type Post, type PostSchedule, type PostNetwork } from "../api/posts"
import { productsApi, type Product } from "../api/products"
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

// Ver buildSchedule: run_date de segurança do "Agora" (disparado de fato
// assim que a mídia termina de subir).
const NOW_SAFETY_DELAY_MS = 5 * 60 * 1000

const PERSONAS = [
  { value: "casual", label: "Casual" },
  { value: "profissional", label: "Profissional" },
  { value: "divertido", label: "Divertido" },
  { value: "persuasivo", label: "Persuasivo" },
]

// Mesmo mapa network -> func do backend (api/routers/posts.py). Só
// Threads publica de verdade hoje — as outras 4 já roteiam pro
// scheduler certo, mas o wrapper de publicação ainda não existe
// (ver NETWORK_FUNC_MAP). Kwai fica de fora, sem API pública ainda.
const NETWORKS: { value: PostNetwork; label: string }[] = [
  { value: "threads", label: "Threads" },
  { value: "x", label: "X (Twitter)" },
  { value: "facebook", label: "Facebook" },
  { value: "instagram", label: "Instagram" },
  { value: "tiktok", label: "TikTok" },
]

const WEEKDAYS = [
  { value: 0, label: "Domingo" },
  { value: 1, label: "Segunda" },
  { value: 2, label: "Terça" },
  { value: 3, label: "Quarta" },
  { value: 4, label: "Quinta" },
  { value: 5, label: "Sexta" },
  { value: 6, label: "Sábado" },
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
    mutationFn: async (data: {
      texts: string[]
      product_ids: number[]
      schedule: PostSchedule
      network: PostNetwork
      files: File[]
      publishNow: boolean
    }) => {
      const created = await postsApi.create({
        texts: data.texts,
        product_ids: data.product_ids,
        schedule: data.schedule,
        network: data.network,
      })
      for (const file of data.files) {
        await postsApi.uploadMedia(created.id, file)
      }
      // "Agora": o job foi criado com run_date de segurança no futuro; só
      // dispara depois que a mídia já está no servidor.
      if (data.publishNow) await postsApi.publishNow(created.id)
      return created
    },
    onSuccess: (_created, data) => {
      queryClient.invalidateQueries({ queryKey: ["posts"] })
      if (data.publishNow) refreshPublishResult()
      setModalOpen(false)
    },
    onError: onAuthError,
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, texts, product_ids }: { id: number; texts: string[]; product_ids: number[] }) =>
      postsApi.update(id, { texts, product_ids }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["posts"] })
      setModalOpen(false)
      setEditingPost(null)
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => postsApi.delete(id),
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
      texts: string[],
      productIds: number[],
      schedule: PostSchedule,
      network: PostNetwork,
      files: File[],
      publishNow: boolean,
    ) => {
      if (editingPost) {
        updateMutation.mutate({ id: editingPost.id, texts, product_ids: productIds })
      } else {
        createMutation.mutate({ texts, product_ids: productIds, schedule, network, files, publishNow })
      }
    },
    [editingPost, createMutation, updateMutation],
  )

  if (isLoading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: 256,
          color: "var(--text-muted)",
        }}
      >
        Carregando...
      </div>
    )
  }

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
          error={createMutation.error?.message}
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
    texts: string[],
    productIds: number[],
    schedule: PostSchedule,
    network: PostNetwork,
    files: File[],
    publishNow: boolean,
  ) => void
  loading: boolean
  error?: string
}

type WhenOption = "now" | "date" | "cron"

function PostModal({ post, onClose, onSave, loading, error }: PostModalProps) {
  const queryClient = useQueryClient()
  const [texts, setTexts] = useState<string[]>(
    post?.texts && post.texts.length > 0 ? post.texts : [""],
  )
  const [persona, setPersona] = useState("casual")
  const [network, setNetwork] = useState<PostNetwork>(post?.network ?? "threads")
  const [selectedProductIds, setSelectedProductIds] = useState<number[]>(
    post?.products.map((p) => p.id) ?? [],
  )
  const [when, setWhen] = useState<WhenOption>("now")
  const [runDate, setRunDate] = useState("")
  const [cronTime, setCronTime] = useState("09:00")
  const [cronDay, setCronDay] = useState(1)
  const [pendingFiles, setPendingFiles] = useState<File[]>([])

  const { data: productsData } = useQuery({
    queryKey: ["products", ""],
    queryFn: () => productsApi.list(),
  })
  const products = productsData?.data ?? []

  const generateMutation = useMutation({
    mutationFn: (productId: number) => postsApi.generateCopy(productId, persona),
    onSuccess: (res) => setTexts((prev) => [res.text, ...prev.slice(1)]),
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

  const buildSchedule = (): PostSchedule => {
    if (when === "cron") {
      return { trigger: "cron", time: cronTime, day_of_week: cronDay }
    }
    // "Agora" = rede de segurança de 5 min: o post é disparado explicitamente
    // logo após o envio da mídia (ver createMutation), sem duplicar.
    const runAt =
      when === "now" ? new Date(Date.now() + NOW_SAFETY_DELAY_MS).toISOString() : new Date(runDate).toISOString()
    return { trigger: "date", run_date: runAt }
  }

  const trimmedTexts = texts.map((t) => t.trim()).filter(Boolean)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (trimmedTexts.length === 0) return
    if (when === "date" && !runDate) return
    onSave(trimmedTexts, selectedProductIds, buildSchedule(), network, pendingFiles, when === "now")
  }

  return (
    <Modal open onClose={onClose} title={post ? "Editar post" : "Novo post"} width={560}>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
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
          <Button
            type="button"
            variant="secondary"
            icon={generateMutation.isPending ? "loader-2" : "sparkles"}
            disabled={selectedProductIds.length === 0 || generateMutation.isPending}
            onClick={() => generateMutation.mutate(selectedProductIds[0])}
          >
            {generateMutation.isPending ? "Gerando..." : "Gerar texto com IA"}
          </Button>
        </div>
        {generateMutation.isError && (
          <p style={{ ...metaTextStyle, color: "var(--negative)" }}>{generateMutation.error.message}</p>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {texts.map((partText, index) => (
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
          ))}
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
            <input
              type="file"
              accept=".webp,.jpg,.jpeg,.png,.gif,.mp4"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (!file) return
                if (post) {
                  addMediaMutation.mutate(file)
                } else {
                  setPendingFiles((prev) => [...prev, file])
                }
                e.target.value = ""
              }}
              style={{ font: "var(--fw-regular) var(--fs-caption)/1 var(--font-sans)", color: "var(--text-body)" }}
            />
          </div>
          {!post && pendingFiles.length > 0 && (
            <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
              {pendingFiles.map((file, index) => (
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
                  </span>
                  <button
                    type="button"
                    onClick={() => setPendingFiles((prev) => prev.filter((_, i) => i !== index))}
                    style={{ background: "none", border: "none", color: "var(--red-300)", cursor: "pointer", font: "inherit", flex: "0 0 auto" }}
                  >
                    Remover
                  </button>
                </li>
              ))}
            </ul>
          )}
          {addMediaMutation.isError && (
            <p style={{ ...metaTextStyle, color: "var(--negative)", marginTop: 6 }}>
              {addMediaMutation.error.message}
            </p>
          )}
        </div>

        {!post && (
          <Select
            label="Rede social"
            value={network}
            onChange={(e) => setNetwork(e.target.value as PostNetwork)}
            options={NETWORKS}
          />
        )}

        {!post && (
          <div>
            <span style={labelStyle}>Quando publicar? *</span>
            <div style={{ marginBottom: 12 }}>
              <SegmentedToggle
                options={[
                  { value: "now", label: "Agora" },
                  { value: "date", label: "Data específica" },
                  { value: "cron", label: "Recorrente" },
                ]}
                value={when}
                onChange={(value) => setWhen(value as WhenOption)}
                fullWidth
              />
            </div>

            {when === "date" && (
              <TextInput type="datetime-local" value={runDate} onChange={(e) => setRunDate(e.target.value)} required />
            )}

            {when === "cron" && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <Select
                  value={String(cronDay)}
                  onChange={(e) => setCronDay(Number(e.target.value))}
                  options={WEEKDAYS.map((d) => ({ value: String(d.value), label: d.label }))}
                />
                <TextInput type="time" value={cronTime} onChange={(e) => setCronTime(e.target.value)} />
              </div>
            )}
          </div>
        )}

        {error && <p style={{ ...metaTextStyle, color: "var(--negative)" }}>{error}</p>}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, paddingTop: 4 }}>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" disabled={loading || trimmedTexts.length === 0 || (when === "date" && !runDate)}>
            {loading ? "Salvando..." : post ? "Salvar" : "Criar"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
