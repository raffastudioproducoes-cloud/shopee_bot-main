import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from "@tanstack/react-query"
import { useState, useEffect, useRef } from "react"
import { Eye } from "lucide-react"
import { useAuthStore } from "../../stores/authStore"
import { router } from "../../router"
import { postsApi, type Post, type PostSchedule, type PostNetwork } from "../../api/posts"
import { credentialsApi, aiCredentialsApi } from "../../api/credentials"
import {
  NETWORK_RULES,
  isNetworkDisabled,
  mediaKind,
  planVariants,
  readMediaInfo,
  validateForNetwork,
  type Issue,
  type MediaInfo,
} from "../../lib/networkLimits"
import { TextVariantTabs } from "./TextVariantTabs"
import { MediaSummary } from "./MediaSummary"
import { MediaTray } from "./MediaTray"
import { PostLivePreview } from "./PostLivePreview"
import { planMediaComposition } from "../../lib/mediaComposition"
import { filterPicked, pickLimits, pickNotice } from "../../lib/mediaAdapt"
import { moveItem } from "../../lib/mediaTray"
import {
  NetworkLimitsPanel,
  NetworkPicker,
  PICKER_NETWORKS,
  type NetworkState,
} from "./NetworkPicker"
import { productsApi, type Product } from "../../api/products"
import { listsApi } from "../../api/lists"
import { useProfileStore } from "../../stores/profileStore"
import { formDraftKey, clearFormDraft } from "../../lib/formDraftStorage"
import { useAutosavedDraft } from "../../hooks/useAutosavedDraft"
import { PostProductPicker } from "./PostProductPicker"
import { PostTimePicker } from "./PostTimePicker"
import { Button } from "../ui/Button"
import { IconButton } from "../ui/IconButton"
import { Textarea } from "../ui/Textarea"
import { Select } from "../ui/Select"
import { SegmentedToggle } from "../ui/SegmentedToggle"

// Ver buildSchedule: run_date de segurança do "Agora" (disparado de fato
// assim que a mídia termina de subir).
const NOW_SAFETY_DELAY_MS = 5 * 60 * 1000

const PERSONAS = [
  { value: "casual", label: "Casual" },
  { value: "profissional", label: "Profissional" },
  { value: "divertido", label: "Divertido" },
  { value: "persuasivo", label: "Persuasivo" },
]

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


export interface NetworkResult {
  network: PostNetwork
  ok: boolean
  error?: string
  postId?: number
  warning?: string
}


// Editor independente: componente de conteúdo, sem camada modal.

export interface PostComposerProps {
  post: Post | null
  onClose: () => void
  onSave: (
    textsByNetwork: Partial<Record<PostNetwork, string[]>>,
    productIds: number[],
    schedule: PostSchedule,
    networks: PostNetwork[],
    files: File[],
    productImageIds: number[],
    publishNow: boolean,
  ) => void
  loading: boolean
  error?: string
  /** Resultado por rede do último envio (só falhas mantêm o modal aberto). */
  results?: NetworkResult[]
  credentials?: Awaited<ReturnType<typeof credentialsApi.list>>
  onClear: () => void
}

type WhenOption = "now" | "cron"

export function PostComposer({ post, onClose, onSave, loading, error, results, credentials, onClear }: PostComposerProps) {
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
    post?.products.slice(0, 1).map((p) => p.id) ?? [],
  )
  const [productTab, setProductTab] = useState<"products" | "lists">("products")
  const [productListId, setProductListId] = useState<number | null>(null)
  const activeProfileId = useProfileStore((state) => state.activeProfileId)
  const accountId = useAuthStore((state) => state.user?.id)
  const [when, setWhen] = useState<WhenOption>("now")
  const [cronTimes, setCronTimes] = useState(["09:00"])
  const cronTime = cronTimes[0]
  const [cronDays, setCronDays] = useState<number[]>([0])
  const [pendingFiles, setPendingFiles] = useState<{ file: File; info: MediaInfo }[]>([])
  const [trayOpen, setTrayOpen] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [useShopeeImages, setUseShopeeImages] = useState(false)
  const [aiAutoContinuation, setAiAutoContinuation] = useState(false)
  const [aiAdjustmentNotice, setAiAdjustmentNotice] = useState<string | null>(null)
  const aiProductRef = useRef<number | null>(null)
  const [pickMessage, setPickMessage] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  // Redes que já deram certo no último envio saem da seleção: reenviar só
  // repete as que falharam, sem duplicar post.
  const [handledResults, setHandledResults] = useState<NetworkResult[] | undefined>(undefined)
  // Rascunho apenas no navegador, isolado por conta/perfil. Nunca salva File.
  const postDraftKey = !post ? formDraftKey(accountId, "post-create", activeProfileId) : null
  useAutosavedDraft(postDraftKey, {
    texts, variantTexts, persona, networks, selectedProductIds, productTab,
    productListId, when, cronTimes, cronDays, useShopeeImages, previewOpen,
    pendingFileNames: pendingFiles.map(({ file }) => file.name),
  }, (saved) => {
    const draft = saved && typeof saved === "object" ? saved : null
    setTexts(Array.isArray(draft?.texts) && draft.texts.length > 0
      ? draft.texts.slice(0, 10).filter((part): part is string => typeof part === "string")
      : [""])
    setVariantTexts(draft?.variantTexts && typeof draft.variantTexts === "object"
      ? Object.fromEntries(Object.entries(draft.variantTexts).filter((entry) => typeof entry[1] === "string"))
      : {})
    setPersona(typeof draft?.persona === "string" ? draft.persona : "casual")
    setNetworks(Array.isArray(draft?.networks)
      ? draft.networks.filter((net): net is PostNetwork => typeof net === "string" && net in NETWORK_RULES)
      : [])
    setSelectedProductIds(Array.isArray(draft?.selectedProductIds)
      ? draft.selectedProductIds.filter((id): id is number => typeof id === "number" && Number.isInteger(id)).slice(0, 1)
      : [])
    setProductTab(draft?.productTab === "lists" ? "lists" : "products")
    setProductListId(typeof draft?.productListId === "number" ? draft.productListId : null)
    setWhen(draft?.when === "cron" ? "cron" : "now")
    setCronTimes(Array.isArray(draft?.cronTimes) && draft.cronTimes.length > 0
      ? draft.cronTimes.filter((t): t is string => typeof t === "string" && /^([01]\d|2[0-3]):[0-5]\d$/.test(t)).slice(0, 5)
      : ["09:00"])
    setCronDays(Array.isArray(draft?.cronDays)
      ? draft.cronDays.filter((day): day is number => Number.isInteger(day) && day >= 0 && day <= 6)
      : [0])
    setUseShopeeImages(draft?.useShopeeImages === true)
    setPreviewOpen(draft?.previewOpen === true)
    setPendingFiles([])
    setTrayOpen(false)
    setAiAutoContinuation(false) // nunca chamar uma IA paga automaticamente após recarregar
    aiProductRef.current = null
    setPickMessage(Array.isArray(draft?.pendingFileNames) && draft.pendingFileNames.length
      ? "Rascunho recuperado. Selecione novamente os arquivos locais de imagem/vídeo; o navegador não permite recuperá-los automaticamente."
      : null)
  })

  if (results && results !== handledResults) {
    setHandledResults(results)
    setNetworks((prev) => prev.filter((n) => !results.some((r) => r.network === n && r.ok)))
  }

  // Catálogo compartilhado pela conta; listas limitadas ao perfil ativo.
  // As respostas incluem os produtos da lista e evitam perder referências
  // selecionadas quando a foto ainda não está na primeira página do catálogo.
  const productPages = useInfiniteQuery({
    queryKey: ["products", "post-composer", accountId],
    initialPageParam: 1,
    queryFn: ({ pageParam }) => productsApi.list({ page: pageParam, page_size: 100 }),
    getNextPageParam: (lastPage, allPages) =>
      lastPage.data.length === 100 ? allPages.length + 1 : undefined,
  })
  const listPages = useInfiniteQuery({
    queryKey: ["lists", "post-composer", accountId, activeProfileId],
    initialPageParam: "",
    queryFn: ({ pageParam }) => listsApi.list({ cursor: pageParam || undefined, limit: 50 }),
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    enabled: productTab === "lists",
  })
  const products = productPages.data?.pages.flatMap((page) => page.data) ?? []
  const lists = listPages.data?.pages.flatMap((page) => page.data) ?? []
  const productIndex = new Map<number, Pick<Product, "id" | "name" | "image">>()
  for (const original of post?.products ?? []) productIndex.set(original.id, original)
  for (const list of lists) {
    for (const product of list.products ?? []) productIndex.set(product.id, product)
  }
  for (const product of products) productIndex.set(product.id, product)
  const selectedProducts = selectedProductIds.flatMap((id) => {
    const product = productIndex.get(id)
    return product ? [product] : []
  })
  const importablePhotos = !post && useShopeeImages ? selectedProducts.filter((p) => !!p.image) : []
  // Prova de capacidade sob demanda: não confundir URLs extras com mídias
  // já importadas/validadas no Storage. Mantém a foto principal e uploads.
  const galleryProbe = useQuery({
    queryKey: ["shopee-gallery-probe", accountId, activeProfileId, selectedProductIds[0]],
    queryFn: () => productsApi.probeShopeeGallery(selectedProductIds[0]!),
    enabled: !!accountId && !!activeProfileId && !!selectedProductIds[0] && useShopeeImages && !post,
    staleTime: 60_000,
    retry: false,
  })

  // Sem chave de IA própria não há o que chamar (não existe chave global):
  // em vez do botão, atalho pra Credenciais.
  const { data: aiStatus } = useQuery({
    queryKey: ["credentials", "ai"],
    queryFn: () => aiCredentialsApi.list(),
  })
  const hasAiKey = aiStatus ? aiStatus.active !== null : true
  const schedulerQuery = useQuery({
    queryKey: ["posts", "scheduler-status"],
    queryFn: postsApi.schedulerStatus,
    enabled: !post,
    staleTime: 10_000,
    refetchInterval: 30_000,
    retry: false,
  })
  const schedulerAvailable = !!post || (
    !schedulerQuery.isError && schedulerQuery.data?.available === true
  )

  const generateMutation = useMutation({
    mutationFn: (request: {
      productId: number; partCount: number; mode: "full" | "append";
      existingTexts?: string[]; snapshot?: string[]
    }) => postsApi.generateCopy(request.productId, persona, networks, {
      partCount: request.partCount, mode: request.mode, existingTexts: request.existingTexts,
    }),
    onSuccess: (res, request) => {
      if (request.mode === "append") {
        // Never overwrite edits the user typed while the background AI ran.
        setTexts((prev) => {
          if (request.snapshot?.some((text, index) => prev[index] !== text)) return prev
          return prev.map((current, index) =>
            index >= res.start_index && !current.trim()
              ? (res.parts[index - res.start_index] ?? current) : current,
          )
        })
        return
      }
      setTexts((prev) => prev.map((current, index) => res.parts[index] ?? current))
      const rest = (res.variants ?? []).slice(1)
      setVariantTexts(Object.fromEntries(rest.map((v) => [v.key, v.text])))
      const adjusted = (res.variants ?? []).filter((v) => v.adjusted)
      setAiAdjustmentNotice(adjusted.length
        ? `A IA excedeu os limites em ${adjusted.map((v) => v.networks.join(", ")).join(", ")}. O texto foi reduzido, as hashtags excedentes foram removidas e o link do produto preservado. Revise cada aba antes de publicar.`
        : null)
      aiProductRef.current = request.productId
      setAiAutoContinuation(true)
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
    setSelectedProductIds((prev) => prev.includes(id) ? [] : [id])
  }

  const setPartText = (index: number, value: string) => {
    setAiAdjustmentNotice(null)
    setTexts((prev) => prev.map((t, i) => (i === index ? value : t)))
  }

  const addPart = () => setTexts((prev) => prev.length >= 10 ? prev : [...prev, ""])
  const removePart = (index: number) => {
    setTexts((prev) => prev.length <= 1 ? prev : prev.filter((_, i) => i !== index))
    if (index === 0) {
      setVariantTexts({})
      setAiAutoContinuation(false)
    }
  }
  const clearComposer = () => {
    clearFormDraft(postDraftKey)
    setTexts([""])
    setVariantTexts({})
    setNetworks([])
    setSelectedProductIds([])
    setProductTab("products")
    setProductListId(null)
    setPendingFiles([])
    setTrayOpen(false)
    setUseShopeeImages(false)
    setAiAutoContinuation(false)
    setAiAdjustmentNotice(null)
    aiProductRef.current = null
    setWhen("now")
    setCronTimes(["09:00"])
    setPickMessage(null)
    setCronDays([0])
    onClear()
  }

  const buildSchedule = (): PostSchedule => {
    if (when === "cron") {
      return { trigger: "cron", time: cronTime, times: cronTimes, days_of_week: cronDays }
    }
    // "Agora" = rede de segurança de 5 min: o post é disparado explicitamente
    // logo após o envio da mídia (ver createMutation), sem duplicar.
    return { trigger: "date", run_date: new Date(Date.now() + NOW_SAFETY_DELAY_MS).toISOString() }
  }

  const trimmedTexts = texts.map((t) => t.trim()).filter(Boolean)
  const activeNetworks = networks.filter((n) => !isNetworkDisabled(n))

  const dateError = when === "cron" && (
    cronDays.length === 0 || !cronTimes.length ||
    !cronTimes.every((time) => /^([01]\d|2[0-3]):[0-5]\d$/.test(time)) ||
    new Set(cronTimes).size !== cronTimes.length
  ) ? "Escolha dias e até cinco horários diferentes no formato 24h." : null

  // Uma versão por rede selecionada; as abas aparecem quando há 2+ redes.
  const plans = planVariants(activeNetworks)
  const hasTabs = !post && plans.length > 1
  const variantValue = (i: number) => (i === 0 ? texts[0] : (variantTexts[plans[i].key] ?? texts[0]))
  const setVariantValue = (i: number, value: string) => {
    setAiAdjustmentNotice(null)
    if (i === 0) setPartText(0, value)
    else setVariantTexts((prev) => ({ ...prev, [plans[i].key]: value }))
  }

  // Parte principal específica da rede, preservando edições manuais.
  const headFor = (n: PostNetwork): string => {
    const selected = networks.includes(n)
    const p = selected ? plans : planVariants([...networks, n])
    const i = p.findIndex((v) => v.networks.includes(n))
    if (post || p.length < 2 || i <= 0) return texts[0]
    return variantTexts[p[i].key] ?? (selected ? texts[0] : "")
  }
  const textsFor = (n: PostNetwork) => [headFor(n), ...texts.slice(1)].map((t) => t.trim()).filter(Boolean)

  // If the user opens more parts after using AI, batch all new empty parts
  // into one continuation request. Debounce prevents ten rapid clicks from
  // creating ten paid API requests. Existing/manual text is never overwritten.
  const networkKey = activeNetworks.join(",")
  useEffect(() => {
    if (!aiAutoContinuation || !hasAiKey ||
        generateMutation.isPending || generateMutation.isError ||
        aiProductRef.current !== selectedProductIds[0] || !texts[0]?.trim()) return

    const firstBlank = texts.findIndex((t, index) => index > 0 && !t.trim())
    if (firstBlank < 0) return
    const threadNetwork = activeNetworks.find((n) => NETWORK_RULES[n].threadParts)
    const head = threadNetwork ? headFor(threadNetwork) : texts[0]
    const existing = [head, ...texts.slice(1, firstBlank)]
    if (existing.some((t) => !t.trim())) return

    const timer = window.setTimeout(() => generateMutation.mutate({
      productId: selectedProductIds[0],
      partCount: texts.length,
      mode: "append",
      existingTexts: existing,
      snapshot: texts.slice(0, firstBlank),
    }), 700)
    return () => window.clearTimeout(timer)
    // headFor is derived from texts, variantTexts and networkKey.
  }, [texts, variantTexts, networkKey, persona, selectedProductIds, aiAutoContinuation,
    hasAiKey, generateMutation.isPending, generateMutation.isError])

  // Validação por rede em tempo real (lib/networkLimits.ts), cada uma com o seu texto.
  const media: MediaInfo[] = post
    ? post.medias.map((m) => ({ name: m.file_name, size: m.size, kind: m.type === "VIDEO" ? "video" : mediaKind(m.file_name) }))
    : [...pendingFiles.map((p) => p.info), ...importablePhotos.map((p) => ({ name: "shopee-" + p.id + ".jpg", size: 1, kind: "image" as const }))]
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
    setAiAdjustmentNotice(null)
  }

  const canSubmit = post
    ? !loading && !generateMutation.isPending && trimmedTexts.length > 0 &&
      activeNetworks.length === 1 && !issues[activeNetworks[0]]?.some((issue) => issue.level === "error")
    : !loading &&
      !generateMutation.isPending &&
      schedulerAvailable &&
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
      importablePhotos.map((p) => p.id),
      when === "now",
    )
  }

  return (
    <section
      className="post-composer-page"
      aria-label={post ? "Editar post" : "Criar POST"}
      style={{
        width: "100%",
        maxWidth: previewOpen ? 1200 : 900,
        margin: "0 auto",
        padding: "clamp(16px, 3vw, 28px)",
        background: "var(--surface-raised, #111827)",
        border: "1px solid var(--border-subtle, #253043)",
        borderRadius: "var(--r-card, 20px)",
      }}
    >
      <div className="post-composer-title" style={{
        display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12,
        marginBottom: 22,
      }}>
        <h2 style={{ margin: 0, font: "var(--text-role-heading)" }}>
          {post ? "Editar post" : "Novo post"}
        </h2>
        <button type="button" className="post-preview-toggle" aria-pressed={previewOpen}
          onClick={() => setPreviewOpen((open) => !open)}><Eye size={16} aria-hidden="true" />
          {previewOpen ? "Ocultar prévia" : "Visualizar"}</button>
      </div>
      <div className={"post-composer-layout" + (previewOpen ? " is-preview-open" : "")}>
      <form className="post-composer-form" onSubmit={handleSubmit}>
        <div>
          <span className="csp-named-label">{post ? "Rede social" : "Redes sociais * (uma ou mais)"}</span>
          <NetworkPicker selected={activeNetworks} states={states} onToggle={toggleNetwork} readOnly={!!post} />
        </div>

        <PostProductPicker
          tab={productTab} onTabChange={setProductTab}
          products={products} lists={lists} listId={productListId}
          onListChange={setProductListId}
          selectedIds={selectedProductIds}
          onToggle={toggleProduct}
          productsLoading={productPages.isPending} productsError={productPages.isError}
          listsLoading={listPages.isPending} listsError={listPages.isError}
          hasMoreProducts={productPages.hasNextPage} hasMoreLists={listPages.hasNextPage}
          loadingMoreProducts={productPages.isFetchingNextPage}
          loadingMoreLists={listPages.isFetchingNextPage}
          onLoadProducts={() => { void productPages.fetchNextPage() }}
          onLoadLists={() => { void listPages.fetchNextPage() }}
        />

        {!post && selectedProducts.length > 0 && <div className="post-composer-shopee-media">
          <label><input type="checkbox" checked={useShopeeImages}
            onChange={(event) => setUseShopeeImages(event.target.checked)} />
            <span>Usar fotos dos produtos Shopee na publicação</span></label>
          <p>As fotos cadastradas serão copiadas para o armazenamento privado ao criar o post. Vídeos da Shopee só ficam disponíveis após o envio de um arquivo de vídeo.</p>
          {useShopeeImages && importablePhotos.length === 0 && <p role="status">Nenhum produto selecionado possui foto cadastrada.</p>}
          {useShopeeImages && galleryProbe.isFetching && <p role="status">Verificando fotos adicionais pela API oficial da Shopee...</p>}
          {useShopeeImages && galleryProbe.isError && <p role="status">
            Não foi possível verificar fotos extras agora. A imagem principal e o upload de arquivos continuam disponíveis.
          </p>}
          {useShopeeImages && galleryProbe.data && <div aria-label="Diagnóstico de fotos Shopee">
            <p role="status">{galleryProbe.data.message}</p>
            {galleryProbe.data.image_urls.length > 1 && <>
              <p style={metaTextStyle}>Prévia informativa: as fotos adicionais ainda não são importadas neste envio. Use os seus arquivos locais enquanto a seleção automática é validada.</p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {galleryProbe.data.image_urls.map((url, index) => (
                  <img key={url} src={url} alt={`Foto Shopee ${index + 1} (prévia)`}
                    loading="lazy" style={{ width: 72, height: 72, objectFit: "cover", borderRadius: 8 }} />
                ))}
              </div>
            </>}
          </div>}
        </div>}

        <div>
          <span className="csp-named-label">Mídia (imagem/vídeo)</span>
          {post && post.medias.length > 0 && (
            <ul className="csp-s-0332">
              {post.medias.map((media) => (
                <li
                  key={media.id}
                  className="csp-s-0333"
                >
                  <span className="csp-s-0334">
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
            className="csp-s-0335"
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
            <span className="csp-named-meta">
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
            <ul className="csp-s-0336">
              {pendingFiles.map(({ file, info }, index) => !showTray || info.kind === "video" ? (
                <li
                  key={index}
                  className="csp-s-0337"
                >
                  <span className="csp-s-0338">
                    {file.name}
                    <span className="csp-s-0339">
                      {" "}· {(file.size / (1024 * 1024)).toFixed(1)} MB
                      {info.width ? ` · ${info.width}×${info.height}` : ""}
                      {info.durationSec != null ? ` · ${Math.round(info.durationSec)} s` : ""}
                    </span>
                  </span>
                  <button
                    type="button"
                    onClick={() => setPendingFiles((prev) => prev.filter((_, i) => i !== index))}
                    className="csp-s-0340"
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

        <div className="csp-s-0326">
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
              disabled={selectedProductIds.length === 0 || activeNetworks.length === 0 || generateMutation.isPending}
              onClick={() => generateMutation.mutate({
                productId: selectedProductIds[0], partCount: texts.length, mode: "full",
              })}
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
        {aiAdjustmentNotice && <p role="status" style={{ ...metaTextStyle, color: "var(--amber-300)" }}>{aiAdjustmentNotice}</p>}
        {!post && selectedProductIds.length > 0 && activeNetworks.length === 0 && (
          <p style={metaTextStyle}>Selecione pelo menos uma rede para a IA adaptar todas as descrições.</p>
        )}

        <div className="csp-s-0327">
          {texts.map((partText, index) =>
            index === 0 && hasTabs ? (
              <div key={index} className="csp-s-0328">
                <span style={{ ...labelStyle, marginBottom: 0 }}>Texto do post *</span>
                <TextVariantTabs
                  plans={plans}
                  values={plans.map((_, i) => variantValue(i))}
                  onChange={setVariantValue}
                  issues={variantIssues}
                />
              </div>
            ) : (
            <div key={index} className="csp-s-0329">
              <div className="csp-s-0330">
                <span style={{ ...labelStyle, marginBottom: 0 }}>
                  {index === 0 ? "Texto do post *" : `Parte ${index + 1} (resposta em thread)`}
                </span>
                {texts.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removePart(index)}
                    className="csp-s-0331"
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
          <Button type="button" variant="ghost" icon="plus" onClick={addPart}
            disabled={texts.length >= 10} style={{ alignSelf: "flex-start", padding: 0 }}>
            Adicionar parte (thread) · {texts.length}/10
          </Button>
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
            <span className="csp-named-label">Quando publicar? *</span>
            <div className="csp-s-0341">
              <SegmentedToggle
                options={[
                  { value: "now", label: "Agora" },
                  { value: "cron", label: "Recorrente" },
                ]}
                value={when}
                onChange={(value) => setWhen(value as WhenOption)}
                fullWidth
              />
            </div>

            {!post && schedulerQuery.isPending && (
              <p role="status" style={{ ...metaTextStyle, marginTop: 8 }}>
                Conferindo disponibilidade do agendador...
              </p>
            )}
            {!post && !schedulerQuery.isPending && !schedulerAvailable && (
              <p role="alert" style={{ ...metaTextStyle, color: "var(--negative)", marginTop: 8 }}>
                {schedulerQuery.data?.message ?? "Não foi possível consultar o agendador. Tente novamente em instantes; seu rascunho permanece salvo."}
              </p>
            )}

            {when === "cron" && (
              <div className="csp-s-0343">
                <div className="csp-s-0344">
                  <span style={{ ...labelStyle, marginBottom: 0 }}>Dias da semana</span>
                  <button
                    type="button"
                    onClick={() => setCronDays((days) => (days.length === WEEKDAYS.length ? [0] : WEEKDAYS.map((day) => day.value)))}
                    className="csp-s-0345"
                  >
                    {cronDays.length === WEEKDAYS.length ? "Somente segunda" : "Semana inteira"}
                  </button>
                </div>
                <div role="group" aria-label="Dias recorrentes" className="csp-s-0346">
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
                {cronTimes.map((time, index) => (
                  <div key={index} className="csp-s-0347">
                    <div className="csp-s-0342">
                      <PostTimePicker
                        label={`Horário ${index + 1}`}
                        value={time}
                        onChange={(next) => setCronTimes((times) => times.map((value, i) => i === index ? next : value))}
                      />
                    </div>
                    {index > 0 && <IconButton icon="trash-2" label={`Remover horário ${index + 1}`} onClick={() => setCronTimes((times) => times.filter((_, i) => i !== index))} />}
                  </div>
                ))}
                {cronTimes.length < 5 && <Button type="button" variant="ghost" icon="plus" onClick={() => setCronTimes((times) => [...times, ["09:00", "12:00", "15:00", "18:00", "21:00", "10:00"].find((value) => !times.includes(value)) ?? "00:00"])} style={{ alignSelf: "flex-start" }}>Adicionar horário</Button>}
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
          <ul aria-live="polite" className="csp-s-0348">
            {results.map((r) => (
              <li
                key={r.network}
                style={{ ...metaTextStyle, lineHeight: 1.4, color: r.ok ? "var(--text-body)" : "var(--negative)" }}
              >
                {NETWORK_RULES[r.network].label}: {r.ok ? `criado #${r.postId ?? "—"} ✓${r.warning ? ` — ${r.warning}` : ""}` : `falhou — ${r.error}`}
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

        <div className="csp-s-0349">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" disabled={!canSubmit}>
            {loading ? "Salvando..." : post ? "Salvar" : activeNetworks.length > 1 ? `Criar em ${activeNetworks.length} redes` : "Criar"}
          </Button>
        </div>
      </form>
      {previewOpen && <PostLivePreview networks={activeNetworks} textFor={textsFor}
        files={pendingFiles} productPhotos={importablePhotos} products={selectedProducts}
        existingMedia={post?.medias} onClose={() => setPreviewOpen(false)} />}
      </div>
    </section>
  )
}
