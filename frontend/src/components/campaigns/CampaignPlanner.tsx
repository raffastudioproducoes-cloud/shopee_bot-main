import { useMemo, useState } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { useAuthStore } from "../../stores/authStore"
import { useProfileStore } from "../../stores/profileStore"
import { listsApi, type Product } from "../../api/lists"
import { campaignsApi, type CampaignPreviewRequest, type CampaignDraftSaveRequest, type CampaignDraftRecord } from "../../api/campaigns"
import { credentialsApi } from "../../api/credentials"
import type { PostNetwork } from "../../api/posts"
import { NETWORK_RULES } from "../../lib/networkLimits"
import { NetworkPicker, PICKER_NETWORKS, type NetworkState } from "../posts/NetworkPicker"
import { reconcileCampaignSnapshots, patchCampaignSnapshot, type CampaignItemSnapshot } from "../../lib/campaignSnapshots"
import { formDraftKey } from "../../lib/formDraftStorage"
import { useAutosavedDraft } from "../../hooks/useAutosavedDraft"
import { usePlanUsage } from "../../hooks/usePlanUsage"
import { campaignUiCaps } from "../../lib/planPresentation"
import { UpgradeInfo } from "../plans/PlanSummary"
import { TextInput } from "../ui/TextInput"
import { Button } from "../ui/Button"
import "./campaignPlanner.css"

const weekdays = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

interface CampaignDraft {
  name: string
  listId: number | null
  itemIds: number[]
  startDate: string
  endDate: string
  days: number[]
  startTime: string
  endTime: string
  postsPerDay: string
  itemSnapshots: Record<number, CampaignItemSnapshot>
}

function initialDraft(): CampaignDraft {
  return {
    name: "", listId: null, itemIds: [], startDate: "", endDate: "",
    days: [0, 1, 2, 3, 4], startTime: "09:00", endTime: "18:00",
    postsPerDay: "1", itemSnapshots: {},
  }
}

/** Conversão somente na leitura para rascunhos da versão antiga. */
function legacyPostsPerDay(start: string, end: string, intervalMinutes: number | undefined): number {
  if (!intervalMinutes || intervalMinutes < 1) return 4
  const toMinutes = (value: string) => {
    const [hours, minutes, seconds = "0"] = value.split(":")
    return Number(hours) * 60 + Number(minutes) + Number(seconds) / 60
  }
  const span = toMinutes(end) - toMinutes(start)
  if (!Number.isFinite(span) || span < 0) return 4
  return Math.min(15, Math.max(1, Math.floor(span / intervalMinutes) + 1))
}

function formatLocal(iso: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Sao_Paulo", weekday: "short", day: "2-digit",
    month: "2-digit", hour: "2-digit", minute: "2-digit",
  }).format(new Date(iso))
}

function productName(products: Product[], id: number, snapshots: Record<number, CampaignItemSnapshot>): string {
  return snapshots[id]?.title || products.find((product) => product.id === id)?.name || "Produto " + id
}

/** Edição local e prévia read-only. Não insere posts, jobs nem campanhas. */
export function CampaignPlanner({ credentials }: {
  credentials?: Awaited<ReturnType<typeof credentialsApi.list>>
}) {
  const planQuery = usePlanUsage()
  const plan = planQuery.isError ? undefined : planQuery.data
  const canEditCampaign = plan?.campaigns_enabled === true
  const caps = campaignUiCaps(plan)
  const userId = useAuthStore((state) => state.user?.id)
  const profileId = useProfileStore((state) => state.activeProfileId)
  const [draft, setDraft] = useState<CampaignDraft>(initialDraft)
  const [editingProductId, setEditingProductId] = useState<number | null>(null)
  const [savedDraftId, setSavedDraftId] = useState<string | null>(null)
  const [savedRevision, setSavedRevision] = useState<number | null>(null)
  const [remoteSelection, setRemoteSelection] = useState("")
  const [deleteConfirmationId, setDeleteConfirmationId] = useState<string | null>(null)
  const [deleteFeedback, setDeleteFeedback] = useState("")
  const [legacyScheduleNotice, setLegacyScheduleNotice] = useState(false)
  const [listOverride, setListOverride] = useState<Awaited<ReturnType<typeof listsApi.get>> | null>(null)
  const [lastSavedSignature, setLastSavedSignature] = useState<string | null>(null)
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null)
  const [historyOffset, setHistoryOffset] = useState(0)
  const [cancelTargetId, setCancelTargetId] = useState<string | null>(null)
  const draftKey = formDraftKey(userId, "campaign-preview", profileId)

  useAutosavedDraft<CampaignDraft>(draftKey, draft, (saved) => {
    if (saved && Array.isArray(saved.itemIds) && Array.isArray(saved.days)) {
      const clean = { ...saved } as CampaignDraft & { interval?: string }
      if (clean.postsPerDay === undefined) {
        clean.postsPerDay = String(legacyPostsPerDay(clean.startTime ?? "09:00", clean.endTime ?? "18:00", Number(clean.interval)))
      }
      delete clean.interval
      setDraft({ ...initialDraft(), ...clean, itemSnapshots: saved.itemSnapshots ?? {} })
    } else {
      setDraft(initialDraft())
    }
    setEditingProductId(null)
    setSavedDraftId(null)
    setSavedRevision(null)
    setRemoteSelection("")
    setDeleteConfirmationId(null)
    setDeleteFeedback("")
    setLegacyScheduleNotice(false)
    setListOverride(null)
    setLastSavedSignature(null)
  })

  const { data: listsResponse, isLoading, error: listsError } = useQuery({
    queryKey: ["lists", profileId, "campaign-preview"],
    queryFn: () => listsApi.list({ limit: 100 }),
    enabled: Boolean(profileId),
  })
  const lists = listsResponse?.data ?? []
  const selectedList = lists.find((list) => list.id === draft.listId)
    ?? (listOverride?.id === draft.listId ? listOverride : undefined)
  const products = selectedList?.products ?? []
  const snapshots = useMemo(
    () => reconcileCampaignSnapshots(products, draft.itemSnapshots),
    [products, draft.itemSnapshots],
  )
  const networkStates = useMemo(() => {
    const states = {} as Record<PostNetwork, NetworkState>
    for (const network of PICKER_NETWORKS) {
      const credential = credentials?.[network]
      const connected = credential?.state === "ok"
      const connectionReason = credentials === undefined ? "verificando conexão"
        : connected ? undefined
        : credential?.state === "disconnected" ? "conecte em Credenciais"
        : credential?.status_text ?? "teste a conexão em Credenciais"
      states[network] = {
        connected: credentials === undefined ? undefined : connected,
        connectionReason,
        errors: [],
      }
    }
    return states
  }, [credentials])
  const previewMutation = useMutation({ mutationFn: campaignsApi.preview })
  const draftsQuery = useQuery({
    queryKey: ["campaign-drafts", userId, profileId],
    queryFn: campaignsApi.listDrafts,
    enabled: Boolean(userId && profileId),
    retry: false,
  })

  const activeQuery = useQuery({
    queryKey: ["campaign-active", userId, profileId],
    queryFn: campaignsApi.listActive,
    enabled: Boolean(userId && profileId),
    retry: false,
    refetchInterval: 30_000,
  })
  const historyQuery = useQuery({
    queryKey: ["campaign-history", userId, profileId, selectedCampaignId, historyOffset],
    queryFn: () => campaignsApi.getHistory(selectedCampaignId!,historyOffset),
    enabled: Boolean(userId && profileId && selectedCampaignId),
    refetchInterval: 30_000,
    retry: false,
  })
  const activateMutation = useMutation({
    mutationFn: ({ id, revision }: { id: string; revision: number }) =>
      campaignsApi.activateDraft(id, revision),
    onSuccess: (record) => {
      setSelectedCampaignId(record.id)
      void activeQuery.refetch()
      void planQuery.refetch()
    },
  })
  const lifecycleMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "pause" | "resume" | "cancel" }) =>
      campaignsApi.changeState(id, action),
    onSuccess: () => {
      setCancelTargetId(null)
      void activeQuery.refetch()
      void historyQuery.refetch()
      void planQuery.refetch()
    },
  })

  const mediaQuery = useQuery({
    queryKey: ["campaign-draft-media", userId, profileId, savedDraftId],
    queryFn: () => campaignsApi.listMedia(savedDraftId!),
    enabled: Boolean(userId && profileId && savedDraftId),
    retry: false,
  })
  const mediaUpload = useMutation({
    mutationFn: async ({ productId, files }: { productId: number; files: File[] }) => {
      if (!canEditCampaign) throw new Error("Campanhas indisponíveis no plano atual.")
      if (!savedDraftId) throw new Error("Salve a campanha antes de enviar arquivos.")
      const uploaded = mediaQuery.data?.data.filter((item) => item.product_id === productId).length ?? 0
      if (uploaded + files.length > 10) throw new Error("Limite de 10 arquivos por produto.")
      for (const file of files) await campaignsApi.uploadMedia(savedDraftId, productId, file)
    },
    onSettled: () => { void mediaQuery.refetch() },
  })
  const mediaDelete = useMutation({
    mutationFn: (id: string) => campaignsApi.deleteMedia(savedDraftId!, id),
    onSettled: () => { void mediaQuery.refetch() },
  })

  const payload = useMemo<CampaignPreviewRequest | null>(() => {
    const inclusiveDays = (Date.parse(draft.endDate) - Date.parse(draft.startDate)) / 86400000 + 1
    if (!canEditCampaign || !Number.isFinite(inclusiveDays) || inclusiveDays < 1 || inclusiveDays > caps.days ||
        !draft.listId || draft.itemIds.length === 0 || !draft.startDate || !draft.endDate ||
        draft.days.length === 0 || !draft.startTime || !draft.endTime ||
        !Number.isInteger(Number(draft.postsPerDay)) || Number(draft.postsPerDay) < 1 ||
        Number(draft.postsPerDay) > caps.posts) return null
    return {
      list_id: draft.listId,
      item_ids: draft.itemIds,
      start_date: draft.startDate,
      end_date: draft.endDate,
      weekdays: [...draft.days].sort(),
      start_time: draft.startTime,
      end_time: draft.endTime,
      posts_per_day: Number(draft.postsPerDay),
    }
  }, [draft, canEditCampaign, caps.days, caps.posts])


  const saveInput = useMemo<CampaignDraftSaveRequest | null>(() => {
    if (!canEditCampaign || ((draft.startDate || draft.endDate) && !payload) ||
        !selectedList || !draft.name.trim() || draft.name.trim().length > 120 || !draft.listId || !draft.itemIds.length ||
        draft.itemIds.length !== products.length ||
        new Set(draft.itemIds).size !== products.length ||
        !draft.itemIds.every((id) => products.some((product) => product.id === id))) return null
    return {
      name: draft.name.trim(),
      list_id: draft.listId,
      items: draft.itemIds.map((id) => ({
        product_id: id,
        title: snapshots[id].title,
        copy: snapshots[id].copy,
        affiliate_link: snapshots[id].affiliateLink,
        networks: snapshots[id].networks,
        network_copies: snapshots[id].networkCopies,
        use_shopee_image: snapshots[id].useShopeeImage,
      })),
      schedule: payload,
    }
  }, [selectedList, products, draft.name, draft.listId, draft.itemIds, snapshots, payload, canEditCampaign])
  const saveSignature = saveInput ? JSON.stringify(saveInput) : ""
  const saveMutation = useMutation({
    mutationFn: async ({ data, id, revision }: {
      data: CampaignDraftSaveRequest; id: string | null; revision: number | null; signature: string
    }) => {
      if (!canEditCampaign) throw new Error("Campanhas indisponíveis no plano atual.")
      return id && revision !== null
        ? campaignsApi.updateDraft(id, { ...data, expected_revision: revision })
        : campaignsApi.createDraft(data)
    },
    onSuccess: (saved, variables) => {
      setSavedDraftId(saved.id)
      setSavedRevision(saved.revision)
      setRemoteSelection(saved.id)
      setLastSavedSignature(variables.signature)
      setLegacyScheduleNotice(false)
      void draftsQuery.refetch()
    },
  })
  const loadMutation = useMutation({
    mutationFn: async (id: string) => {
      const saved = await campaignsApi.getDraft(id)
      if (saved.status !== "draft" || !saved.source_list_id) {
        throw new Error("A lista de origem não está mais disponível para edição.")
      }
      const source = lists.find((item) => item.id === saved.source_list_id)
        ?? await listsApi.get(saved.source_list_id)
      const currentIds = (source.products ?? []).map((product) => product.id)
      const storedIds = saved.items.map((item) => item.product_id)
      if (currentIds.length !== storedIds.length || storedIds.some((id) => !currentIds.includes(id))) {
        throw new Error("A lista mudou desde o salvamento. Não foi carregada para evitar perda de produtos.")
      }
      return { saved, source }
    },
    onSuccess: ({ saved, source }: { saved: CampaignDraftRecord; source: Awaited<ReturnType<typeof listsApi.get>> }) => {
      const schedule = saved.schedule
      const restored = Object.fromEntries(saved.items.map((item) => [item.product_id, {
        title: item.title,
        copy: item.copy,
        affiliateLink: item.affiliate_link,
        networks: item.networks,
        networkCopies: item.network_copies,
        useShopeeImage: item.use_shopee_image,
      }])) as Record<number, CampaignItemSnapshot>
      setListOverride(source)
      setDraft({
        name: saved.campaign_name || saved.source_list_name,
        listId: saved.source_list_id,
        itemIds: saved.items.map((item) => item.product_id),
        itemSnapshots: restored,
        startDate: schedule?.start_date ?? "",
        endDate: schedule?.end_date ?? "",
        days: schedule?.weekdays ?? [0, 1, 2, 3, 4],
        startTime: schedule?.start_time ?? "09:00",
        endTime: schedule?.end_time ?? "18:00",
        postsPerDay: String(schedule?.posts_per_day ?? legacyPostsPerDay(
          schedule?.start_time ?? "09:00", schedule?.end_time ?? "18:00", schedule?.interval_minutes)),
      })
      setSavedDraftId(saved.id)
      setSavedRevision(saved.revision)
      setRemoteSelection(saved.id)
      setLegacyScheduleNotice(Boolean(schedule?.interval_minutes && !schedule.posts_per_day))
      setDeleteConfirmationId(null)
      setDeleteFeedback("")
      setLastSavedSignature(null)
      setEditingProductId(null)
    },
  })

  const deleteDraftMutation = useMutation({
    mutationFn: ({ id, revision }: { id: string; revision: number }) =>
      campaignsApi.deleteDraft(id, revision),
    onSuccess: (_, variables) => {
      if (savedDraftId === variables.id) {
        // A preparação local permanece para salvar como NOVA campanha.
        setSavedDraftId(null)
        setSavedRevision(null)
        setLastSavedSignature(null)
      }
      setRemoteSelection("")
      setDeleteConfirmationId(null)
      setDeleteFeedback("Rascunho salvo e seus anexos excluídos. A preparação local foi mantida.")
      void draftsQuery.refetch()
    },
  })

  const previewIsCurrent = Boolean(payload && previewMutation.data &&
    JSON.stringify(previewMutation.variables) === JSON.stringify(payload))
  const preview = previewIsCurrent ? previewMutation.data : null

  const update = <K extends keyof CampaignDraft,>(field: K, value: CampaignDraft[K]) => {
    setDraft((current) => ({ ...current, [field]: value }))
  }

  const updateSnapshot = (id: number, changes: Partial<CampaignItemSnapshot>) => {
    setDraft((current) => {
      if (!products.some((product) => product.id === id)) return current
      const currentSnapshots = reconcileCampaignSnapshots(products, current.itemSnapshots)
      return { ...current, itemSnapshots: patchCampaignSnapshot(currentSnapshots, id, changes) }
    })
  }

  const moveProduct = (at: number, direction: -1 | 1) => {
    setDraft((current) => {
      const next = [...current.itemIds]
      const target = at + direction
      if (target < 0 || target >= next.length) return current
      ;[next[at], next[target]] = [next[target], next[at]]
      return { ...current, itemIds: next }
    })
  }

  return (
    <section className="campaign-planner" aria-label="Campanha por lista">
      <div className="campaign-intro">
        <div>
          <h2>Campanha por lista</h2>
          <p>Prepare o conteúdo, confirme o período contratado e ative a publicação automática por rede.</p>
        </div>
        <span className="campaign-readonly-badge">{plan?.activation_available ? "Ativação disponível" : "Ativação condicionada ao plano"}</span>
      </div>

      <div className="plan-campaign-lock" role="status">
        {!plan ? "Não foi possível confirmar o plano. Novas prévias e alterações ficam indisponíveis; consulta e exclusão de rascunhos continuam disponíveis."
          : !canEditCampaign ? "Campanhas não incluídas no plano atual. Disponíveis nos planos Pro e Premium."
          : `Até ${caps.days} dias inclusivos e ${caps.posts} publicações por dia. Cada rede conta uma publicação.`}
        {plan && <p>Vagas reservadas: {plan.active_campaigns_count ?? "indisponível"} / {plan.is_admin ? "sem limite comercial" : plan.active_campaigns_limit}.
          Rascunhos não consomem vagas. {plan.campaign_paid_through
            ? "Direitos pagos até " + new Date(plan.campaign_paid_through).toLocaleString("pt-BR") + "."
            : plan.is_admin ? "Conta administrativa." : "Sem período pago confirmado; ativação bloqueada."}</p>}
        {planQuery.isError && <Button variant="secondary" onClick={() => void planQuery.refetch()}>Consultar plano novamente</Button>}
        <UpgradeInfo feature="Campanhas" />
      </div>
      <div className="campaign-grid">
        <div className="campaign-controls">
          <section className="campaign-section">
            <h3>01. Produtos</h3>
            <p>Dê um nome à campanha, escolha a lista, ajuste a ordem e prepare cada produto.</p>
            <label className="campaign-field-label" htmlFor="campaign-name">Nome da campanha</label>
            <input id="campaign-name" className="campaign-select" type="text" maxLength={120}
              value={draft.name} onChange={(event) => update("name", event.target.value)}
              placeholder="Ex.: Ofertas da semana de novembro" />
            <label className="campaign-field-label" htmlFor="campaign-list">Lista de produtos</label>
            <select
              id="campaign-list"
              className="campaign-select"
              value={draft.listId ?? ""}
              onChange={(event) => {
                const id = Number(event.target.value) || null
                const list = lists.find((item) => item.id === id)
                setDraft((current) => ({
                  ...current, listId: id, itemIds: (list?.products ?? []).map((item) => item.id),
                  itemSnapshots: reconcileCampaignSnapshots(list?.products ?? [], {}),
                }))
                setSavedDraftId(null)
                setSavedRevision(null)
                setRemoteSelection("")
                setDeleteConfirmationId(null)
                setLastSavedSignature(null)
                setListOverride(null)
                setEditingProductId(null)

              }}
              disabled={!profileId || isLoading}
            >
              <option value="">Selecione uma lista</option>
              {selectedList && !lists.some((item) => item.id === selectedList.id) &&
                <option value={selectedList.id}>{selectedList.name} (recuperada)</option>}
              {lists.map((list) => <option key={list.id} value={list.id}>{list.name} ({list.product_count})</option>)}
            </select>
            {!profileId && <p className="campaign-status">Selecione um perfil para carregar suas listas.</p>}
            {listsError && <p className="campaign-error">Não foi possível carregar as listas.</p>}
            {listsResponse?.next_cursor && <p className="campaign-status">Exibindo as 100 listas mais recentes.</p>}
            {selectedList && products.length === 0 && <p className="campaign-status">Esta lista não tem produtos. Adicione produtos em Listas.</p>}
            {selectedList && draft.itemIds.length > 0 && (
              <ol className="campaign-products">
                {draft.itemIds.map((id, index) => {
                  const product = products.find((entry) => entry.id === id)
                  const snapshot = snapshots[id]
                  if (!product || !snapshot) return null
                  const editing = editingProductId === id
                  const prepared = Boolean(snapshot.copy.trim() && snapshot.networks.length)
                  return (
                    <li key={id} className="campaign-product">
                      <div className="campaign-product-row">
                        <span className="campaign-product-index">{index + 1}</span>
                        {product.image && <img className="campaign-product-image" src={product.image}
                          loading="lazy" alt="" />}
                        <span className="campaign-product-name">
                          <strong>{snapshot.title || product.name}</strong>
                          <small>{prepared ? "Conteúdo preparado neste navegador" : "Preparação pendente"}</small>
                        </span>
                        <button type="button" className="campaign-edit-button"
                          aria-expanded={editing} aria-controls={`campaign-item-editor-${id}`}
                          onClick={() => setEditingProductId(editing ? null : id)}>
                          {editing ? "Fechar" : "Preparar"}
                        </button>
                        <div className="campaign-reorder">
                          <button type="button" aria-label={"Subir " + product.name}
                            disabled={index === 0} onClick={() => moveProduct(index, -1)}>↑</button>
                          <button type="button" aria-label={"Descer " + product.name}
                            disabled={index === draft.itemIds.length - 1} onClick={() => moveProduct(index, 1)}>↓</button>
                        </div>
                      </div>
                      {editing && (
                        <div className="campaign-item-editor" id={`campaign-item-editor-${id}`}>
                          <p className="campaign-item-hint">
                            As mudanças ficam apenas no rascunho desta campanha; não alteram a lista nem fazem publicações.
                          </p>
                          <label className="campaign-field-label" htmlFor={`campaign-title-${id}`}>Título do produto</label>
                          <input className="campaign-select" id={`campaign-title-${id}`} maxLength={300}
                            value={snapshot.title} onChange={(e) => updateSnapshot(id, { title: e.target.value })} />
                          <label className="campaign-field-label" htmlFor={`campaign-copy-${id}`}>Texto principal</label>
                          <textarea className="campaign-textarea" id={`campaign-copy-${id}`}
                            maxLength={10000} rows={4} value={snapshot.copy}
                            onChange={(e) => updateSnapshot(id, { copy: e.target.value })}
                            placeholder="Escreva a mensagem para este produto." />
                          <label className="campaign-field-label" htmlFor={`campaign-link-${id}`}>Link de afiliado</label>
                          <input className="campaign-select" id={`campaign-link-${id}`} type="url" maxLength={2048}
                            value={snapshot.affiliateLink} onChange={(e) => updateSnapshot(id, { affiliateLink: e.target.value })}
                            placeholder="https://..." />
                          <span className="campaign-field-label">Redes para este produto</span>
                          <NetworkPicker selected={snapshot.networks} states={networkStates}
                            onToggle={(network) => updateSnapshot(id, {
                              networks: snapshot.networks.includes(network)
                                ? snapshot.networks.filter((entry) => entry !== network)
                                : [...snapshot.networks, network],
                            })} />
                          {snapshot.networks.length > 0 && (
                            <div className="campaign-network-copy">
                              {snapshot.networks.map((network) => (
                                <div key={network}>
                                  <label className="campaign-field-label" htmlFor={`campaign-network-${id}-${network}`}>
                                    Texto específico · {NETWORK_RULES[network].label}
                                  </label>
                                  <textarea className="campaign-textarea" id={`campaign-network-${id}-${network}`}
                                    maxLength={10000} rows={3} value={snapshot.networkCopies[network] ?? ""}
                                    placeholder="Deixe em branco para usar o texto principal."
                                    onChange={(e) => updateSnapshot(id, {
                                      networkCopies: { ...snapshot.networkCopies, [network]: e.target.value },
                                    })} />
                                </div>
                              ))}
                            </div>
                          )}
                          <div className="campaign-media-choice">
                            {product.image ? (
                              <label>
                                <input type="checkbox" checked={snapshot.useShopeeImage}
                                  onChange={(e) => updateSnapshot(id, { useShopeeImage: e.target.checked })} />
                                Usar a foto principal da Shopee
                              </label>
                            ) : <p>Este produto não tem foto Shopee registrada.</p>}
                            <div className="campaign-media-upload">
                              <label className="campaign-field-label" htmlFor={`campaign-media-${id}`}>
                                Fotos ou vídeos próprios (PC ou celular)
                              </label>
                              <input id={`campaign-media-${id}`} className="campaign-upload-input"
                                type="file" multiple accept="image/jpeg,image/png,image/webp,image/gif,video/mp4"
                                disabled={!canEditCampaign || !savedDraftId || mediaUpload.isPending || mediaDelete.isPending || deleteDraftMutation.isPending}
                                onChange={(event) => {
                                  const files = Array.from(event.currentTarget.files ?? [])
                                  event.currentTarget.value = ""
                                  if (files.length) mediaUpload.mutate({ productId: id, files })
                                }} />
                              {!savedDraftId && <small>Salve o rascunho com um nome para anexar arquivos permanentes.</small>}
                              <small>Até 10 arquivos por produto, 50 MB por arquivo. O envio não publica posts.</small>
                              {mediaQuery.data?.data.filter((item) => item.product_id === id).map((item) => (
                                <div className="campaign-media-file" key={item.id}>
                                  <span>{item.media_type === "VIDEO" ? "Vídeo" : "Foto"} · {item.file_name}</span>
                                  <button type="button" disabled={mediaDelete.isPending || mediaUpload.isPending}
                                    onClick={() => mediaDelete.mutate(item.id)}
                                    aria-label={`Remover ${item.file_name}`}>Remover</button>
                                </div>
                              ))}
                              {mediaUpload.isPending && <small role="status">Enviando arquivos para armazenamento privado…</small>}
                              {mediaUpload.isError && <p className="campaign-error" role="alert">{mediaUpload.error.message}</p>}
                              {mediaDelete.isError && <p className="campaign-error" role="alert">{mediaDelete.error.message}</p>}
                              {mediaQuery.isError && savedDraftId &&
                                <p className="campaign-error" role="alert">Não foi possível consultar os anexos salvos.</p>}
                            </div>
                          </div>
                        </div>
                      )}
                    </li>
                  )
                })}
              </ol>
            )}
          </section>

          <section className="campaign-section" aria-label="Rascunhos persistidos">
            <h3>Rascunhos da campanha</h3>
            <p>Salve sua preparação para continuar em outro dispositivo. Salvar não cria posts nem ativa publicações.</p>
            <div className="campaign-actions">
              <Button variant="primary" icon="save"
                disabled={!canEditCampaign || !saveInput || saveMutation.isPending || (Boolean(savedDraftId) && lastSavedSignature === saveSignature)}
                loading={saveMutation.isPending}
                onClick={() => saveInput && saveMutation.mutate({
                  data: saveInput, id: savedDraftId, revision: savedRevision, signature: saveSignature,
                })}>
                {savedDraftId ? "Atualizar rascunho" : "Salvar rascunho"}
              </Button>
              {lastSavedSignature === saveSignature && savedDraftId &&
                <p className="campaign-status" role="status">Rascunho salvo no servidor.</p>}
              {saveMutation.isError &&
                <p className="campaign-error" role="alert">
                  {saveMutation.error?.message || "Não foi possível salvar. O rascunho local permanece disponível."}
                </p>}
            </div>
            <label className="campaign-field-label" htmlFor="campaign-saved-draft">Continuar rascunho salvo</label>
            <div className="campaign-draft-restore">
              <select id="campaign-saved-draft" className="campaign-select" value={remoteSelection}
                onChange={(event) => {
                  setRemoteSelection(event.target.value)
                  setDeleteConfirmationId(null)
                  setDeleteFeedback("")
                }}
                disabled={draftsQuery.isLoading || loadMutation.isPending || deleteDraftMutation.isPending}>
                <option value="">Selecione um rascunho</option>
                {(draftsQuery.data?.data ?? []).map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.campaign_name || item.source_list_name} · {new Date(item.updated_at).toLocaleString("pt-BR")}
                  </option>
                ))}
              </select>
              <Button variant="secondary" icon="folder-open"
                disabled={!remoteSelection || loadMutation.isPending || deleteDraftMutation.isPending}
                loading={loadMutation.isPending}
                onClick={() => remoteSelection && loadMutation.mutate(remoteSelection)}>
                Carregar
              </Button>
              <Button variant="send" icon="trash-2"
                disabled={!remoteSelection || saveMutation.isPending || loadMutation.isPending ||
                  mediaUpload.isPending || mediaDelete.isPending || deleteDraftMutation.isPending}
                onClick={() => { setDeleteConfirmationId(remoteSelection); setDeleteFeedback("") }}>
                Excluir
              </Button>
            </div>
            {deleteConfirmationId && deleteConfirmationId === remoteSelection && (
              <div className="campaign-delete-confirmation" role="group" aria-label="Confirmar exclusão de rascunho">
                <p>Excluir definitivamente este rascunho salvo e todos os anexos vinculados? Essa ação não afeta a lista de produtos nem posts já publicados.</p>
                <div className="campaign-delete-actions">
                  <Button variant="ghost" onClick={() => setDeleteConfirmationId(null)}
                    disabled={deleteDraftMutation.isPending}>Cancelar</Button>
                  <Button variant="send" icon="trash-2" loading={deleteDraftMutation.isPending}
                    disabled={deleteDraftMutation.isPending}
                    onClick={() => {
                      const selected = draftsQuery.data?.data.find((item) => item.id === deleteConfirmationId)
                      if (selected) deleteDraftMutation.mutate({ id: selected.id, revision: selected.revision })
                    }}>Confirmar exclusão</Button>
                </div>
              </div>
            )}
            <div className="campaign-actions">
              <Button variant="primary" icon="send"
                disabled={!plan?.activation_available || !savedDraftId || savedRevision === null ||
                  lastSavedSignature !== saveSignature || !saveInput ||
                  activateMutation.isPending || mediaUpload.isPending || mediaDelete.isPending}
                loading={activateMutation.isPending}
                onClick={() => savedDraftId && savedRevision !== null &&
                  activateMutation.mutate({ id: savedDraftId, revision: savedRevision })}>
                Ativar campanha salva
              </Button>
              <small>Ativar reserva vagas e prepara posts para os horários escolhidos. A rede só recebe o conteúdo no horário autorizado.</small>
              {savedDraftId && lastSavedSignature !== saveSignature &&
                <small role="status">Salve as alterações atuais antes de ativar.</small>}
              {activateMutation.isError &&
                <p className="campaign-error" role="alert">{activateMutation.error.message}</p>}
              {activateMutation.isSuccess &&
                <p className="campaign-status" role="status">Campanha ativada. Acompanhe os estados abaixo.</p>}
            </div>
            <div className="campaign-active-list" aria-label="Acompanhamento de campanhas">
              <h4>Campanhas e entregas</h4>
              {activeQuery.isLoading && <p className="campaign-status">Carregando campanhas…</p>}
              {activeQuery.isError && <p className="campaign-error" role="alert">
                Não foi possível consultar as campanhas. <button type="button"
                  onClick={() => void activeQuery.refetch()}>Tentar novamente</button>
              </p>}
              {activeQuery.data?.data.length === 0 && <p className="campaign-status">
                Nenhuma campanha reservada neste perfil.
              </p>}
              {(activeQuery.data?.data ?? []).map((record) => (
                <div className="campaign-product" key={record.id}>
                  <strong>{record.name}</strong>
                  <p className="campaign-status">
                    Estado: {({preparing:"Preparando",active:"Ativa",paused:"Pausada",
                      cancelled:"Cancelada",completed:"Concluída"} as const)[record.lifecycle]}
                    {record.pause_reason === "paid_period_expired" ? " · período pago encerrado" : ""}
                  </p>
                  <p className="campaign-status">
                    {record.progress
                      ? [record.progress.succeeded + " concluídos",record.progress.planned + " planejados",
                          record.progress.running + " em execução",record.progress.failed + " falhas",
                          record.progress.unknown + " incertos",record.progress.cancelled + " cancelados"].join(" · ")
                      : "Contagem indisponível"}
                  </p>
                  <div className="campaign-actions">
                    <Button variant="secondary" onClick={() => { setHistoryOffset(0); setSelectedCampaignId(
                      selectedCampaignId === record.id ? null : record.id) }}>
                      {selectedCampaignId === record.id ? "Fechar histórico" : "Ver histórico por rede"}
                    </Button>
                    {record.lifecycle === "active" &&
                      <Button variant="secondary" disabled={lifecycleMutation.isPending}
                        onClick={() => lifecycleMutation.mutate({ id: record.id, action: "pause" })}>
                        Pausar
                      </Button>}
                    {record.lifecycle === "paused" &&
                      <Button variant="secondary" disabled={lifecycleMutation.isPending}
                        onClick={() => lifecycleMutation.mutate({ id: record.id, action: "resume" })}>
                        Retomar
                      </Button>}
                    {["preparing","active","paused"].includes(record.lifecycle) &&
                      (cancelTargetId === record.id
                        ? <><Button variant="secondary" onClick={() => setCancelTargetId(null)}>
                            Voltar
                          </Button><Button variant="send" disabled={lifecycleMutation.isPending}
                            onClick={() => lifecycleMutation.mutate({ id: record.id, action: "cancel" })}>
                            Confirmar cancelamento
                          </Button></>
                        : <Button variant="send" onClick={() => setCancelTargetId(record.id)}>
                            Cancelar campanha
                          </Button>)}
                  </div>
                  {selectedCampaignId === record.id && (
                    <div className="campaign-slots">
                      {historyQuery.isLoading && <p>Carregando histórico…</p>}
                      {historyQuery.isError && <p className="campaign-error">Histórico indisponível.</p>}
                      <ol>
                        {(historyQuery.data?.data ?? []).map((slot) => (
                          <li key={slot.id}>
                            {slot.network} · produto {slot.product_id} ·
                            {new Date(slot.planned_at).toLocaleString("pt-BR")} · {slot.state}
                            {slot.delivery?.last_error && <small> · {slot.delivery.last_error}</small>}
                          </li>
                        ))}
                      </ol>
                      <div className="campaign-actions">
                        <Button variant="secondary" disabled={historyOffset === 0}
                          onClick={() => setHistoryOffset((offset) => Math.max(0,offset-100))}>Anteriores</Button>
                        <Button variant="secondary" disabled={!historyQuery.data?.has_more}
                          onClick={() => setHistoryOffset((offset) => offset+100)}>Próximas</Button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {lifecycleMutation.isError &&
                <p className="campaign-error" role="alert">{lifecycleMutation.error.message}</p>}
            </div>

            {deleteFeedback && <p className="campaign-status" role="status">{deleteFeedback}</p>}
            {deleteDraftMutation.isError &&
              <p className="campaign-error" role="alert">{deleteDraftMutation.error.message}</p>}
            {draftsQuery.isError &&
              <p className="campaign-error" role="alert">Não foi possível consultar os rascunhos salvos.</p>}
            {loadMutation.isError &&
              <p className="campaign-error" role="alert">{loadMutation.error?.message || "Falha ao carregar."}</p>}
            {loadMutation.isSuccess && !loadMutation.isError &&
              <p className="campaign-status" role="status">Rascunho recuperado. Revise antes de atualizar.</p>}
          </section>

          <section className="campaign-section">
            <h3>02. Período e frequência</h3>
            <p>Limite do plano: {caps.days || "indisponível"} dias corridos, incluindo o primeiro e o último dia. Horário de Brasília.</p>
            <div className="campaign-pair">
              <TextInput label="Data inicial" type="date" value={draft.startDate}
                onChange={(event) => update("startDate", event.target.value)} />
              <TextInput label="Data final" type="date" value={draft.endDate}
                min={draft.startDate || undefined}
                max={draft.startDate && caps.days > 0 && Number.isFinite(Date.parse(draft.startDate))
                  ? new Date(Date.parse(draft.startDate) + (caps.days - 1) * 86400000).toISOString().slice(0, 10) : undefined}
                onChange={(event) => update("endDate", event.target.value)} />
            </div>
            <span className="campaign-field-label">Dias da semana</span>
            <div className="campaign-weekdays">
              {weekdays.map((day, index) => (
                <label key={day} className={draft.days.includes(index) ? "is-on" : ""}>
                  <input type="checkbox" checked={draft.days.includes(index)}
                    onChange={(event) => update("days", event.target.checked
                      ? [...draft.days, index].sort()
                      : draft.days.filter((item) => item !== index))} />
                  {day}
                </label>
              ))}
            </div>
            <div className="campaign-triple">
              <TextInput label="Início" type="time" value={draft.startTime}
                onChange={(event) => update("startTime", event.target.value)} />
              <TextInput label="Fim" type="time" value={draft.endTime}
                onChange={(event) => update("endTime", event.target.value)} />
              <div className="campaign-frequency-field">
                <label className="campaign-field-label" htmlFor="campaign-posts-per-day">Postagens por dia</label>
                <select id="campaign-posts-per-day" className="campaign-select"
                  value={draft.postsPerDay} disabled={!canEditCampaign}
                  onChange={(event) => { update("postsPerDay", event.target.value); setLegacyScheduleNotice(false) }}>
                  {Number(draft.postsPerDay) > caps.posts && <option value={draft.postsPerDay}>{draft.postsPerDay} — excede o plano atual; revise</option>}
                  {Array.from({ length: caps.posts }, (_, index) => index + 1).map((count) => (
                    <option key={count} value={count}>{count} {count === 1 ? "postagem" : "postagens"} por dia</option>
                  ))}
                </select>
              </div>
            </div>
            <p className="campaign-status">As postagens são distribuídas igualmente entre início e fim, nos dias marcados. A prévia não publica conteúdo.</p>
            {legacyScheduleNotice && <p className="campaign-warning" role="status">Frequência antiga convertida de minutos para postagens por dia (máximo de 15). Confira a prévia antes de salvar.</p>}
          </section>

          <div className="campaign-actions">
            <Button variant="primary" icon="calendar-search"
              disabled={!canEditCampaign || !payload || !selectedList || previewMutation.isPending}
              loading={previewMutation.isPending}
              onClick={() => canEditCampaign && payload && previewMutation.mutate(payload)}>
              Calcular prévia
            </Button>
            <p>Esta ação somente consulta o planejamento. Não envia nada às redes sociais.</p>
          </div>
        </div>

        <aside className="campaign-preview" aria-live="polite">
          <div className="campaign-preview-top">
            <h3>Prévia do calendário</h3>
            <span>Brasil · UTC−03</span>
          </div>
          {!preview && !previewMutation.isError && (
            <p className="campaign-placeholder">Escolha uma lista, configure os dias e clique em “Calcular prévia”.</p>
          )}
          {previewMutation.isError && !preview && (
            <p className="campaign-error" role="alert">
              {previewMutation.error?.message || "Não foi possível calcular a prévia."}
            </p>
          )}
          {preview && (
            <>
              <div className="campaign-summary">
                <div><strong>{preview.slot_count}</strong><span>horários</span></div>
                <div><strong>{preview.product_count}</strong><span>produtos</span></div>
                <div><strong>{preview.uncovered_count}</strong><span>sem primeira rodada</span></div>
              </div>
              {preview.uncovered_count > 0 && (
                <p className="campaign-warning">
                  Faltam horários para exibir todos os produtos: {preview.uncovered_item_ids
                    .map((id) => productName(products, id, snapshots)).join(", ")}.
                </p>
              )}
              {preview.slot_count === 0 && (
                <p className="campaign-warning">Nenhum horário combina com os dias selecionados.</p>
              )}
              <ol className="campaign-slots">
                {preview.slots.map((slot) => (
                  <li key={slot.sequence}>
                    <span className="campaign-slot-number">{slot.sequence}</span>
                    <span><strong>{productName(products, slot.product_id, snapshots)}</strong>
                      <small>{formatLocal(slot.scheduled_local)}</small>
                    </span>
                  </li>
                ))}
              </ol>
              {preview.truncated && <p className="campaign-status">Mostrando os primeiros 60 de {preview.slot_count} horários.</p>}
              <p className="campaign-safety-note">{preview.message}</p>
              <p className="campaign-safety-note">A prévia calcula horários e rotação; rascunhos dos itens ainda não serão enviados.</p>
            </>
          )}
          <div className="campaign-next-step">
            <strong>Ativação após salvar</strong>
            <p>Ao ativar, o servidor valida as cotas, retém os arquivos no armazenamento privado e confirma as permissões OAuth. A execução ocorre somente nos horários previstos, com pausa e cancelamento disponíveis.</p>
          </div>
        </aside>
      </div>
    </section>
  )
}
