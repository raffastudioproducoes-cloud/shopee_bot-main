import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import type { Post, PostNetwork } from "../../api/posts"
import { postsApi } from "../../api/posts"
import { NETWORK_RULES } from "../../lib/networkLimits"
import { DEFAULT_TIME_ZONE, formatUtcTimestamp, withTimeZone } from "../../lib/userTimeZone"
import { useProfileStore } from "../../stores/profileStore"
import { useAuthStore } from "../../stores/authStore"
import { Modal } from "../ui/Modal"
import { Badge } from "../ui/Badge"
import { StatusBadge } from "../ui/StatusBadge"
import { NetworkLogo } from "./NetworkPicker"
import { postKind, scheduleLines } from "./postPresentation"
import { FutureRevisionEditor } from "./FutureRevisionEditor"

type Props = { post: Post; groupNetworks: PostNetwork[]; onClose: () => void }
const sectionStyle = { display: "grid", gap: 8, padding: "14px 0", borderBottom: "1px solid var(--border-hairline)" } as const
const headingStyle = { margin: 0, color: "var(--text-muted)", font: "var(--text-role-label)", letterSpacing: "var(--ls-label)", textTransform: "uppercase" } as const
const LAST_RESULT_LABEL: Record<string, string> = {
  published: "Publicado", failed: "Falhou", running: "Em andamento",
  unknown: "Sem confirmação", retry_pending: "Nova tentativa pendente",
  manual_confirmed: "Confirmado manualmente", reported_removed: "Informado como removido",
}
const DAYS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
const SLOT_TONE = {
  programado: "neutral", "em execução": "info", postado: "positive",
  erro: "negative", "erro parcial": "negative", "sem confirmação": "warning",
} as const
const valueStyle = { margin: 0, color: "var(--text-body)", whiteSpace: "pre-wrap", overflowWrap: "anywhere" } as const

/** Visualização de publicação existente: sem formulário, edição ou mutação. */
export function PostDetailsModal({ post, groupNetworks, onClose }: Props) {
  const [editingFuture, setEditingFuture] = useState(false)
  const activeProfileId = useProfileStore((state) => state.activeProfileId)
  const isAdmin = useAuthStore((state) => state.user?.access === "ADMIN")
  const { data, isFetching, isError } = useQuery({
    queryKey: ["post-details", activeProfileId, post.id], queryFn: () => postsApi.get(post.id), staleTime: 0, refetchInterval: 30_000,
  })
  const details = data ?? post
  const parts = details.texts?.length ? details.texts : [details.text]
  const networks = groupNetworks.length ? groupNetworks : [details.network ?? "threads"]
  const schedule = scheduleLines(details)
  const lastPublished = details.last_published_at ? formatUtcTimestamp(details.last_published_at) : null
  const lastAttempt = details.last_result?.at ? formatUtcTimestamp(details.last_result.at) : null
  const slots = details.schedule_slots ?? []
  const failedAt = lastAttempt ?? "horário não informado"
  const postSummary = details.text.trim().slice(0, 65) + (details.text.length > 65 ? "…" : "")
  return (
    <Modal open onClose={onClose} title="Detalhes da publicação" width={760}>
      <div style={{ display: "grid", gap: 0 }}>
        <p aria-label={`ID do post: ${details.id}`} style={{ margin: "0 0 6px", color: "var(--text-muted)", font: "var(--text-role-caption)" }}>Post #{details.id}</p>
        <p style={{ margin: "0 0 8px", color: "var(--text-muted)" }}>O histórico e as publicações realizadas são somente leitura.</p>
        {details.scheduled && !details.publish_immediately && !isError && (
          <div style={{ display: "grid", gap: 8, marginBottom: 16 }}>
            <button type="button" disabled={isFetching} onClick={() => setEditingFuture((current) => !current)}>
              {editingFuture ? "Ocultar edição futura" : "Editar textos dos próximos posts"}
            </button>
            {editingFuture && <FutureRevisionEditor key={details.id} post={details} onClose={() => setEditingFuture(false)} />}
          </div>
        )}
        {isFetching && <p role="status" style={{ margin: 0, color: "var(--text-muted)" }}>Carregando informações atualizadas...</p>}
        {isError && <p role="alert" style={{ margin: 0, color: "var(--negative)" }}>Não foi possível atualizar os detalhes. Exibindo as informações da lista.</p>}
        <section style={sectionStyle}>
          <h3 style={headingStyle}>Rede social e tipo de envio</h3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {networks.map((network) => <Badge key={network} tone="outline"><span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><NetworkLogo network={network} size={14} />{NETWORK_RULES[network].label}</span></Badge>)}
            <Badge tone="glass">{postKind(details)}</Badge>
          </div>
          {networks.length > 1 && <p style={valueStyle}>Este envio pertence a um grupo com {networks.length} redes. Os dados abaixo são da publicação selecionada ({NETWORK_RULES[details.network ?? "threads"].label}).</p>}
        </section>
        <section style={sectionStyle}>
          <h3 style={headingStyle}>Texto completo {parts.length > 1 ? "— " + parts.length + " partes" : ""}</h3>
          {parts.map((part, index) => <div key={index} style={{ border: "1px solid var(--border-hairline)", borderRadius: "var(--r-md)", padding: 12 }}>
            {parts.length > 1 && <p style={{ ...headingStyle, marginBottom: 8 }}>Parte {index + 1} de {parts.length}</p>}
            <p style={valueStyle}>{part || "Sem texto nesta parte."}</p>
          </div>)}
        </section>
        <section style={sectionStyle}>
          <h3 style={headingStyle}>Produtos vinculados</h3>
          {details.products.length ? details.products.map((product) => (
            <div key={product.id} style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}>
              {product.image && <img src={product.image} alt="" loading="lazy" style={{ width: 46, height: 46, objectFit: "cover", borderRadius: "var(--r-sm)", flexShrink: 0 }} />}
              <span style={valueStyle}>{product.name}</span>
            </div>
          )) : <p style={valueStyle}>Nenhum produto vinculado.</p>}
        </section>
        <section style={sectionStyle}>
          <h3 style={headingStyle}>Mídias vinculadas</h3>
          {details.medias.length ? (
            <ul style={{ margin: 0, paddingLeft: 20, display: "grid", gap: 6 }}>
              {details.medias.map((media) => <li key={media.id} style={valueStyle}>{media.type === "VIDEO" ? "Vídeo" : "Imagem"}: {media.file_name}</li>)}
            </ul>
          ) : <p style={valueStyle}>Nenhuma mídia vinculada.</p>}
        </section>
        <section style={sectionStyle}>
          <h3 style={headingStyle}>Datas e horários</h3>
          <p style={valueStyle}>Criado em: {formatUtcTimestamp(details.created_at)}</p>
          {details.updated_at && <p style={valueStyle}>Última atualização: {formatUtcTimestamp(details.updated_at)}</p>}
          <p style={valueStyle}>Modalidade: {postKind(details)}</p>
          {slots.length > 0 ? (
            <div style={{ display: "grid", gap: 6 }} aria-label="Resultado por dia e horário">
              {slots.map((slot, index) => (
                <div key={index} style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: "6px 12px", padding: "7px 10px", border: "1px solid var(--border-hairline)", borderRadius: "var(--r-sm)" }}>
                  <span style={{ ...valueStyle, minWidth: 142, fontVariantNumeric: "tabular-nums" }}>
                    {slot.day_of_week === null ? formatUtcTimestamp(slot.time) : `${DAYS[slot.day_of_week] ?? "Dia"} · ${withTimeZone(slot.time, slot.timezone ?? DEFAULT_TIME_ZONE)}`}
                  </span>
                  <StatusBadge tone={SLOT_TONE[slot.status] ?? "neutral"} style={{ fontSize: 11, padding: "2px 7px", opacity: .85 }}>
                    {slot.status === "erro" ? "Erro" : slot.status === "erro parcial" ? "Erro parcial" : slot.status === "postado" ? "Postado" : slot.status === "programado" ? "Programado" : slot.status}
                  </StatusBadge>
                  {slot.last_at && <span style={{ color: "var(--text-muted)", fontSize: 12 }}>Última tentativa: {formatUtcTimestamp(slot.last_at)}</span>}
                  {isAdmin && slot.error && (
                    <details style={{ flexBasis: "100%", minWidth: 0 }}>
                      <summary style={{ color: "var(--text-muted)", cursor: "pointer", fontSize: 11 }}>Ver diagnóstico</summary>
                      <p style={{ ...valueStyle, color: "var(--negative)", fontSize: 12, marginTop: 6 }}>{slot.error}</p>
                    </details>
                  )}
                </div>
              ))}
            </div>
          ) : schedule.length ? (
            <ul style={{ margin: 0, paddingLeft: 20, display: "grid", gap: 6 }}>
              {schedule.map((line, index) => <li key={index} style={valueStyle}>{line}</li>)}
            </ul>
          ) : <p style={valueStyle}>{postKind(details) === "Imediato" ? "Envio criado para publicação imediata." : "Nenhum horário detalhado retornado pela API."}</p>}
          <p style={valueStyle}>Última postagem: {lastPublished ?? "Nenhuma publicação confirmada."}</p>
          <p style={{ ...valueStyle, color: "var(--text-muted)" }}>Última execução: {lastAttempt ?? "Ainda sem registro."}</p>
        </section>
        <section style={{ ...sectionStyle, borderBottom: 0 }}>
          <h3 style={headingStyle}>Resultado da última execução</h3>
          <p style={valueStyle}>Estado: {details.last_result?.partial_failure ? "Falha parcial — conferir na rede" : LAST_RESULT_LABEL[details.last_result?.status ?? ""] ?? "Pendente"}</p>
          {(details.last_result?.status === "failed" || details.last_result?.partial_failure) && !isAdmin ? (
            <p role="status" style={{ ...valueStyle, color: "var(--negative)" }}>
              {details.last_result?.partial_failure ? "Falha parcial" : "Falha"} na publicação de “{postSummary}” em {failedAt}.
              {details.last_result?.partial_failure && " Uma parte pode ter sido enviada; confira na rede antes de tentar novamente."}
            </p>
          ) : details.last_result?.error ? (
            <p role="status" style={{ ...valueStyle, color: "var(--text-muted)" }}>{details.last_result.error}</p>
          ) : null}
          {details.last_result?.proof_url && <a href={details.last_result.proof_url} target="_blank" rel="noopener noreferrer">Ver publicação confirmada</a>}
        </section>
      </div>
    </Modal>
  )
}
