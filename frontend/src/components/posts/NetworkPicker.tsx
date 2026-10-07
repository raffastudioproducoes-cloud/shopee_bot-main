// Seletor multi-rede do criador de post: botões quadrados com logo (toggle,
// aria-pressed) + painel compacto com os limites das redes marcadas. Regras
// e textos de erro vêm de lib/networkLimits.ts.
import type { ReactNode } from "react"
import type { PostNetwork } from "../../api/posts"
import { NETWORK_RULES, textLength, type Issue } from "../../lib/networkLimits"

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
  /** undefined = status de Credenciais desconhecido (não bloqueia). */
  connected?: boolean
  errors: Issue[]
}

interface SquareProps {
  network: PostNetwork | "kwai"
  label: string
  pressed: boolean
  invalid?: boolean
  disabledReason?: string
  onClick?: () => void
}

function NetworkSquare({ network, label, pressed, invalid, disabledReason, onClick }: SquareProps) {
  const disabled = !!disabledReason
  const border = invalid ? "var(--negative)" : pressed ? "var(--accent)" : "var(--border-hairline)"
  return (
    <button
      type="button"
      aria-pressed={pressed}
      aria-disabled={disabled || undefined}
      aria-label={disabledReason ? `${label} — ${disabledReason}` : label}
      title={disabledReason ?? label}
      onClick={() => !disabled && onClick?.()}
      style={{
        position: "relative",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 6,
        aspectRatio: "1 / 1",
        minHeight: 64,
        padding: 6,
        borderRadius: "var(--r-md)",
        border: `${pressed || invalid ? 2 : 1}px solid ${border}`,
        background: pressed ? "rgba(129,189,250,.14)" : "var(--surface-inset)",
        color: invalid ? "var(--negative)" : pressed ? "var(--accent)" : "var(--text-body)",
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled && !pressed ? 0.45 : 1,
        font: "var(--fw-medium) var(--fs-caption)/1.1 var(--font-sans)",
        transition: "var(--t-hover)",
      }}
    >
      <NetworkLogo network={network} />
      <span style={{ textAlign: "center" }}>{label}</span>
      {network === "kwai" && (
        <span style={{ position: "absolute", top: 4, right: 6, fontSize: 9, color: "var(--text-muted)" }}>em breve</span>
      )}
    </button>
  )
}

interface NetworkPickerProps {
  selected: PostNetwork[]
  states: Record<PostNetwork, NetworkState>
  onToggle: (network: PostNetwork) => void
  /** Edição: a rede do post é fixa. */
  readOnly?: boolean
}

export function NetworkPicker({ selected, states, onToggle, readOnly }: NetworkPickerProps) {
  const disconnected = PICKER_NETWORKS.filter((n) => states[n].connected === false)
  return (
    <div>
      <div
        role="group"
        aria-label="Redes sociais"
        style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(64px, 1fr))", gap: 8 }}
      >
        {PICKER_NETWORKS.map((n) => {
          const pressed = selected.includes(n)
          const st = states[n]
          let reason: string | undefined
          if (readOnly) reason = "a rede de um post existente não muda"
          else if (st.connected === false && !pressed) reason = "conecte em Credenciais"
          else if (st.errors.length > 0 && !pressed) reason = st.errors[0].message
          return (
            <NetworkSquare
              key={n}
              network={n}
              label={NETWORK_RULES[n].label}
              pressed={pressed}
              invalid={pressed && st.errors.length > 0}
              disabledReason={reason}
              onClick={() => onToggle(n)}
            />
          )
        })}
        <NetworkSquare network="kwai" label="Kwai" pressed={false} disabledReason="em breve" />
      </div>
      {!readOnly && disconnected.length > 0 && (
        <p style={{ margin: "8px 0 0", font: "var(--fw-regular) var(--fs-caption)/1.4 var(--font-sans)", color: "var(--text-muted)" }}>
          {disconnected.map((n) => NETWORK_RULES[n].label).join(", ")}: conecte em{" "}
          <a href="/credentials" style={{ color: "var(--accent)" }}>
            Credenciais
          </a>{" "}
          para publicar.
        </p>
      )}
    </div>
  )
}

interface LimitsPanelProps {
  selected: PostNetwork[]
  headText: string
  mediaCount: number
  issues: Record<PostNetwork, Issue[]>
}

const caption = "var(--fw-regular) var(--fs-caption)/1.4 var(--font-sans)"

/** Contadores por rede marcada + motivos. aria-live: avisa leitor de tela. */
export function NetworkLimitsPanel({ selected, headText, mediaCount, issues }: LimitsPanelProps) {
  if (selected.length === 0) return null
  const all = selected.flatMap((n) => issues[n])
  return (
    <div
      aria-live="polite"
      style={{
        border: "1px solid var(--border-hairline)",
        borderRadius: "var(--r-md)",
        background: "var(--surface-inset)",
        padding: "8px 10px",
        display: "flex",
        flexDirection: "column",
        gap: 6,
      }}
    >
      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 14px" }}>
        {selected.map((n) => {
          const rule = NETWORK_RULES[n]
          const used = textLength(rule, headText)
          const maxMedia = rule.maxMedia ?? (rule.maxImages != null ? Math.max(rule.maxImages, rule.maxVideos ?? 0) : undefined)
          const bad = issues[n].some((i) => i.level === "error")
          return (
            <span
              key={n}
              style={{ display: "inline-flex", alignItems: "center", gap: 6, font: caption, color: bad ? "var(--negative)" : "var(--text-body)" }}
            >
              <NetworkLogo network={n} size={14} />
              <span style={{ fontVariantNumeric: "tabular-nums" }}>
                {used}/{rule.maxChars.toLocaleString("pt-BR")}
                {maxMedia != null ? ` · mídia ${mediaCount}/${maxMedia}` : ""}
              </span>
              <span aria-hidden="true">{bad ? "✕" : "✓"}</span>
            </span>
          )
        })}
      </div>
      {all.length > 0 && (
        <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 2 }}>
          {all.map((i, idx) => (
            <li key={idx} style={{ font: caption, color: i.level === "error" ? "var(--negative)" : "var(--amber-300)" }}>
              {i.level === "error" ? "Bloqueado — " : "Aviso — "}
              {i.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
