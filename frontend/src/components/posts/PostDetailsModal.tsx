import { useQuery } from "@tanstack/react-query"
import type { Post, PostNetwork } from "../../api/posts"
import { postsApi } from "../../api/posts"
import { NETWORK_RULES } from "../../lib/networkLimits"
import { formatUtcTimestampBrasilia } from "../../lib/ptBrDateTime"
import { useProfileStore } from "../../stores/profileStore"
import { Modal } from "../ui/Modal"
import { Badge } from "../ui/Badge"
import { NetworkLogo } from "./NetworkPicker"
import { lastPublishedLabel, postKind, scheduleLines } from "./postPresentation"

type Props = { post: Post; groupNetworks: PostNetwork[]; onClose: () => void }
const sectionStyle = { display: "grid", gap: 8, padding: "14px 0", borderBottom: "1px solid var(--border-hairline)" } as const
const headingStyle = { margin: 0, color: "var(--text-muted)", font: "var(--text-role-label)", letterSpacing: "var(--ls-label)", textTransform: "uppercase" } as const
const valueStyle = { margin: 0, color: "var(--text-body)", whiteSpace: "pre-wrap", overflowWrap: "anywhere" } as const

/** Visualização de publicação existente: sem formulário, edição ou mutação. */
export function PostDetailsModal({ post, groupNetworks, onClose }: Props) {
  const activeProfileId = useProfileStore((state) => state.activeProfileId)
  const { data, isFetching, isError } = useQuery({
    queryKey: ["post-details", activeProfileId, post.id], queryFn: () => postsApi.get(post.id), staleTime: 0,
  })
  const details = data ?? post
  const parts = details.texts?.length ? details.texts : [details.text]
  const networks = groupNetworks.length ? groupNetworks : [details.network ?? "threads"]
  const schedule = scheduleLines(details)
  const lastAt = lastPublishedLabel(details)
  return (
    <Modal open onClose={onClose} title="Detalhes da publicação" width={760}>
      <div style={{ display: "grid", gap: 0 }}>
        <p style={{ margin: "0 0 8px", color: "var(--text-muted)" }}>Somente leitura — esta publicação não pode ser alterada aqui.</p>
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
          <p style={valueStyle}>Criado em: {formatUtcTimestampBrasilia(details.created_at)}</p>
          {details.updated_at && <p style={valueStyle}>Última atualização: {formatUtcTimestampBrasilia(details.updated_at)}</p>}
          <p style={valueStyle}>Modalidade: {postKind(details)}</p>
          {schedule.length ? (
            <ul style={{ margin: 0, paddingLeft: 20, display: "grid", gap: 6 }}>
              {schedule.map((line, index) => <li key={index} style={valueStyle}>{line}</li>)}
            </ul>
          ) : <p style={valueStyle}>{postKind(details) === "Imediato" ? "Envio criado para publicação imediata." : "Nenhum horário detalhado retornado pela API."}</p>}
          <p style={valueStyle}>Última execução: {lastAt ?? "Ainda sem registro de execução."}</p>
        </section>
        <section style={{ ...sectionStyle, borderBottom: 0 }}>
          <h3 style={headingStyle}>Resultado da última execução</h3>
          <p style={valueStyle}>Estado: {details.last_result?.status ?? "Pendente"}</p>
          {details.last_result?.error && <p role="status" style={{ ...valueStyle, color: "var(--text-muted)" }}>{details.last_result.error}</p>}
          {details.last_result?.proof_url && <a href={details.last_result.proof_url} target="_blank" rel="noopener noreferrer">Ver publicação confirmada</a>}
        </section>
      </div>
    </Modal>
  )
}
