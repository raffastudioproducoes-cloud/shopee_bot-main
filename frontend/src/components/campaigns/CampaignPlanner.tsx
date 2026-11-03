import { useMemo, useState } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { useAuthStore } from "../../stores/authStore"
import { useProfileStore } from "../../stores/profileStore"
import { listsApi, type Product } from "../../api/lists"
import { campaignsApi, type CampaignPreviewRequest } from "../../api/campaigns"
import { credentialsApi } from "../../api/credentials"
import type { PostNetwork } from "../../api/posts"
import { NETWORK_RULES } from "../../lib/networkLimits"
import { NetworkPicker, PICKER_NETWORKS, type NetworkState } from "../posts/NetworkPicker"
import { reconcileCampaignSnapshots, patchCampaignSnapshot, type CampaignItemSnapshot } from "../../lib/campaignSnapshots"
import { formDraftKey } from "../../lib/formDraftStorage"
import { useAutosavedDraft } from "../../hooks/useAutosavedDraft"
import { TextInput } from "../ui/TextInput"
import { Button } from "../ui/Button"
import "./campaignPlanner.css"

const weekdays = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

interface CampaignDraft {
  listId: number | null
  itemIds: number[]
  startDate: string
  endDate: string
  days: number[]
  startTime: string
  endTime: string
  interval: string
  itemSnapshots: Record<number, CampaignItemSnapshot>
}

function initialDraft(): CampaignDraft {
  return {
    listId: null, itemIds: [], startDate: "", endDate: "",
    days: [0, 1, 2, 3, 4], startTime: "09:00", endTime: "18:00",
    interval: "180", itemSnapshots: {},
  }
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
  const userId = useAuthStore((state) => state.user?.id)
  const profileId = useProfileStore((state) => state.activeProfileId)
  const [draft, setDraft] = useState<CampaignDraft>(initialDraft)
  const [editingProductId, setEditingProductId] = useState<number | null>(null)
  const draftKey = formDraftKey(userId, "campaign-preview", profileId)

  useAutosavedDraft<CampaignDraft>(draftKey, draft, (saved) => {
    setDraft(saved && Array.isArray(saved.itemIds) && Array.isArray(saved.days)
      ? { ...initialDraft(), ...saved, itemSnapshots: saved.itemSnapshots ?? {} } : initialDraft())
    setEditingProductId(null)
  })

  const { data: listsResponse, isLoading, error: listsError } = useQuery({
    queryKey: ["lists", profileId, "campaign-preview"],
    queryFn: () => listsApi.list({ limit: 100 }),
    enabled: Boolean(profileId),
  })
  const lists = listsResponse?.data ?? []
  const selectedList = lists.find((list) => list.id === draft.listId)
  const products = selectedList?.products ?? []
  const snapshots = useMemo(
    () => reconcileCampaignSnapshots(products, draft.itemSnapshots),
    [products, draft.itemSnapshots],
  )
  const networkStates = useMemo(() => Object.fromEntries(
    PICKER_NETWORKS.map((network) => {
      const credential = credentials?.[network]
      const connected = credential?.state === "ok"
      const connectionReason = credentials === undefined ? "verificando conexão"
        : connected ? undefined
        : credential?.state === "disconnected" ? "conecte em Credenciais"
        : credential?.status_text ?? "teste a conexão em Credenciais"
      return [network, { connected: credentials === undefined ? undefined : connected,
        connectionReason, errors: [] }]
    }),
  ) as Record<PostNetwork, NetworkState>, [credentials])
  const previewMutation = useMutation({ mutationFn: campaignsApi.preview })

  const payload = useMemo<CampaignPreviewRequest | null>(() => {
    if (!draft.listId || draft.itemIds.length === 0 || !draft.startDate || !draft.endDate ||
        draft.days.length === 0 || !draft.startTime || !draft.endTime ||
        !Number.isInteger(Number(draft.interval)) || Number(draft.interval) < 1) return null
    return {
      list_id: draft.listId,
      item_ids: draft.itemIds,
      start_date: draft.startDate,
      end_date: draft.endDate,
      weekdays: [...draft.days].sort(),
      start_time: draft.startTime,
      end_time: draft.endTime,
      interval_minutes: Number(draft.interval),
    }
  }, [draft])

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
          <p>Organize a sequência de produtos e visualize os horários antes de ativar uma campanha.</p>
        </div>
        <span className="campaign-readonly-badge">Prévia · sem ativação</span>
      </div>

      <div className="campaign-grid">
        <div className="campaign-controls">
          <section className="campaign-section">
            <h3>01. Produtos</h3>
            <p>Escolha uma lista, ajuste a ordem e prepare textos, links e redes de cada produto.</p>
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
                setEditingProductId(null)

              }}
              disabled={!profileId || isLoading}
            >
              <option value="">Selecione uma lista</option>
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
                            <small>Fotos e vídeos do PC/celular continuam disponíveis na publicação única.
                              O anexo persistente por produto da campanha será integrado antes da ativação.</small>
                          </div>
                        </div>
                      )}
                    </li>
                  )
                })}
              </ol>
            )}
          </section>

          <section className="campaign-section">
            <h3>02. Período e frequência</h3>
            <p>Até 30 dias corridos, incluindo o primeiro e o último dia. Horário de Brasília.</p>
            <div className="campaign-pair">
              <TextInput label="Data inicial" type="date" value={draft.startDate}
                onChange={(event) => update("startDate", event.target.value)} />
              <TextInput label="Data final" type="date" value={draft.endDate}
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
              <TextInput label="Intervalo (min)" type="number" min={1} max={1440} step={1}
                value={draft.interval} onChange={(event) => update("interval", event.target.value)} />
            </div>
          </section>

          <div className="campaign-actions">
            <Button variant="primary" icon="calendar-search"
              disabled={!payload || !selectedList || previewMutation.isPending}
              loading={previewMutation.isPending}
              onClick={() => payload && previewMutation.mutate(payload)}>
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
            <strong>Ativação será uma etapa separada</strong>
            <p>Antes do disparo serão necessários limites por plano e rede, revisão até 30 minutos antes e validação anti-spam no servidor.</p>
          </div>
        </aside>
      </div>
    </section>
  )
}
