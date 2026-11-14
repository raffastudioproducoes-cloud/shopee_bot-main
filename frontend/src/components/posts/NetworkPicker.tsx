// Seleção social compacta e reutilizada por Publicação única e Campanha por lista.
// Os ícones SVG permanecem apenas nos indicadores de limite de mídia/texto.
import type { ReactNode } from "react"
import type { PostNetwork } from "../../api/posts"
import { NETWORK_RULES, isNetworkDisabled, textLength, type Issue } from "../../lib/networkLimits"
import { buildAdminDiagnosticSections } from "../../lib/credentialPlatforms"
import "./NetworkPicker.css"

// Logos simplificadas, monocromáticas (currentColor) — sem asset externo.
const LOGOS: Record<PostNetwork | "kwai", ReactNode> = {
  threads: (
    <path d="M16.5 11.2c-.4-2.6-2.2-3.9-4.6-3.9-2.6 0-4.4 1.8-4.4 4.6s1.8 4.7 4.3 4.7c2 0 3.4-1.1 3.4-2.9 0-1.6-1.3-2.6-3.3-2.6-1.6 0-2.7.7-2.7 1.8M12 21c-5 0-8.5-3.5-8.5-9S7 3 12 3c4.2 0 7 2.2 8 5.8" />
  ),
  x: <path d="M4 4l16 16M20 4L4 20" />,
  facebook: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M13.5 21v-8h2.5M13.5 13h-3M13.5 21v-9.5c0-1.7.9-2.5 2.5-2.5h1" />
    </>
  ),
  instagram: (
    <>
      <rect x="3.5" y="3.5" width="17" height="17" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17.2" cy="6.8" r=".6" fill="currentColor" />
    </>
  ),
  tiktok: <path d="M13.5 3v11.5a3.5 3.5 0 1 1-3.5-3.5M13.5 3c.3 2.6 2 4.4 5 4.6" />,
  kwai: (
    <>
      <rect x="3" y="6" width="13" height="12" rx="3" />
      <path d="M16 10.5l5-3v9l-5-3" />
    </>
  ),
}

export function NetworkLogo({ network, size = 22 }: { network: PostNetwork | "kwai"; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {LOGOS[network]}
    </svg>
  )
}

export const PICKER_NETWORKS: PostNetwork[] = ["threads", "x", "facebook", "instagram", "tiktok"]

export interface NetworkState {
  /** undefined = verificação ainda carregando; true = último teste real foi ok. */
  connected?: boolean
  /** Diagnóstico curto, sem segredo, vindo do estado real da credencial. */
  connectionReason?: string
  errors: Issue[]
}

const SOCIAL_CHANNELS = buildAdminDiagnosticSections().social

function isPublishingNetwork(key: string): key is PostNetwork {
  return PICKER_NETWORKS.includes(key as PostNetwork)
}

interface NetworkPickerProps {
  selected: PostNetwork[]
  states: Record<PostNetwork, NetworkState>
  onToggle: (network: PostNetwork) => void
  /** Edição: a rede do post é fixa. */
  readOnly?: boolean
}

export function NetworkPicker({ selected, states, onToggle, readOnly }: NetworkPickerProps) {
  return (
    <div className="compact-network-picker" role="group" aria-label="Redes sociais">
      {SOCIAL_CHANNELS.map(({ key, title, availability }) => {
        const supported = isPublishingNetwork(key)
        const state = supported ? states[key] : undefined
        const unavailable = supported ? isNetworkDisabled(key) : undefined
        const ready = availability === "active" && supported && !unavailable && state?.connected === true
        const checked = supported && selected.includes(key)
        const reason = availability === "planned" || !supported ? "Em breve"
          : unavailable ? "Indisponível"
          : state?.connected === undefined ? "Verificando conexão"
          : !state.connected ? "Não conectada" : "Conectada"
        // Permitir remover escolhas legadas sem OAuth; jamais selecionar uma rede indisponível.
        const disabled = Boolean(readOnly) || (!ready && !checked)
        return (
          <label key={key}
            className={`compact-network-option${!ready || readOnly ? " is-disabled" : ""}${checked && state?.errors.length ? " has-errors" : ""}`}
            title={readOnly ? "A rede de um post existente não muda" : unavailable || (!ready ? state?.connectionReason || reason : undefined)}>
            <input type="checkbox" checked={checked} disabled={disabled} value={key}
              aria-label={ready ? title : `${title} — ${reason}`}
              onChange={(event) => {
                if (supported && !readOnly && (ready || !event.currentTarget.checked)) onToggle(key)
              }} />
            <span>{title}</span>
          </label>
        )
      })}
    </div>
  )
}

interface LimitsPanelProps {
  selected: PostNetwork[]
  /** Texto (parte 1) que vai pra cada rede: com abas, cada grupo tem o seu. */
  textFor: (network: PostNetwork) => string
  /** Mídias que a rede realmente recebe. */
  mediaCount: (network: PostNetwork) => number
  issues: Record<PostNetwork, Issue[]>
}

const caption = "var(--fw-regular) var(--fs-caption)/1.4 var(--font-sans)"

/** Contadores por rede marcada + motivos. aria-live: avisa leitor de tela. */
export function NetworkLimitsPanel({ selected, textFor, mediaCount, issues }: LimitsPanelProps) {
  if (selected.length === 0) return null
  const all = selected.flatMap((n) => issues[n])
  return (
    <div
      aria-live="polite"
      className="csp-s-0031"
    >
      <div className="csp-s-0032">
        {selected.map((n) => {
          const rule = NETWORK_RULES[n]
          const used = textLength(rule, textFor(n))
          const maxMedia = rule.maxMedia ?? (rule.maxImages != null ? Math.max(rule.maxImages, rule.maxVideos ?? 0) : undefined)
          const bad = issues[n].some((i) => i.level === "error")
          return (
            <span
              key={n}
              style={{ display: "inline-flex", alignItems: "center", gap: 6, font: caption, color: bad ? "var(--negative)" : "var(--text-body)" }}
            >
              <NetworkLogo network={n} size={14} />
              <span className="csp-s-0033">
                {used}/{rule.maxChars.toLocaleString("pt-BR")}
                {maxMedia != null ? ` · mídia ${mediaCount(n)}/${maxMedia}` : ""}
              </span>
              <span aria-hidden="true">{bad ? "✕" : "✓"}</span>
            </span>
          )
        })}
      </div>
      {all.length > 0 && (
        <details style={{ font: caption, color: "var(--text-muted)" }}>
          <summary className="csp-s-0034">
            Ver detalhes ({all.length} {all.length === 1 ? "aviso" : "avisos"})
          </summary>
          <ul className="csp-s-0035">
            {all.map((i, idx) => (
              <li key={idx} style={{ font: caption, color: i.level === "error" ? "var(--negative)" : "var(--amber-300)" }}>
                {i.level === "error" ? "Erro — " : "Aviso — "}
                {i.message}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}
