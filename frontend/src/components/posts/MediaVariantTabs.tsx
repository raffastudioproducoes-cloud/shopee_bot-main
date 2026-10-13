// Resumo da composição de mídia por rede (lib/mediaComposition.ts). Abas só
// aparecem quando as redes marcadas divergem (ex.: carrossel numa, só texto
// noutra); bloqueadas ficam em vermelho com o motivo, sem sair da seleção.
import { useId, useState } from "react"
import type { PostNetwork } from "../../api/posts"
import { NETWORK_RULES } from "../../lib/networkLimits"
import type { MediaCompositionMode, MediaCompositionPlan } from "../../lib/mediaComposition"
import { NetworkLogo } from "./NetworkPicker"

interface Props {
  networks: PostNetwork[]
  plans: Record<PostNetwork, MediaCompositionPlan>
}

const caption = "var(--fw-regular) var(--fs-caption)/1.4 var(--font-sans)"

const MODE_LABEL: Record<MediaCompositionMode, string> = {
  none: "sem mídia",
  single_image: "imagem única",
  carousel: "carrossel",
  video: "vídeo",
  text_only: "só texto",
  blocked: "não será enviada",
}

const reasonOf = (p: MediaCompositionPlan) => (p.mode === "blocked" ? p.blockedReason : p.warnings[0])

export function MediaVariantTabs({ networks, plans }: Props) {
  const [active, setActive] = useState(0)
  const baseId = useId()
  const rows = networks.map((n) => plans[n])
  if (rows.length === 0 || rows.every((p) => p.mode === "none")) return null

  const groups = [...new Set(rows.map((p) => p.mode))]
  const current = Math.min(active, groups.length - 1)
  const shown = groups.length > 1 ? rows.filter((p) => p.mode === groups[current]) : rows

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <span style={{ font: caption, color: "var(--text-muted)" }}>Mídia por rede</span>
      {groups.length > 1 && (
        <div role="tablist" aria-label="Mídia do post por rede" style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {groups.map((mode, i) => {
            const on = i === current
            const bad = mode === "blocked"
            return (
              <button
                key={mode}
                type="button"
                role="tab"
                id={`${baseId}-tab-${i}`}
                aria-selected={on}
                aria-controls={`${baseId}-panel`}
                onClick={() => setActive(i)}
                style={{
                  flex: "1 1 120px",
                  minHeight: 44,
                  padding: "6px 10px",
                  borderRadius: "var(--r-md)",
                  border: `${on || bad ? 2 : 1}px solid ${bad ? "var(--negative)" : on ? "var(--accent)" : "var(--border-hairline)"}`,
                  background: on ? "rgba(129,189,250,.14)" : "var(--surface-inset)",
                  color: bad ? "var(--negative)" : on ? "var(--accent)" : "var(--text-body)",
                  font: caption,
                  cursor: "pointer",
                }}
              >
                {MODE_LABEL[mode]} ({rows.filter((p) => p.mode === mode).length})
              </button>
            )
          })}
        </div>
      )}
      <ul
        role={groups.length > 1 ? "tabpanel" : undefined}
        id={`${baseId}-panel`}
        aria-live="polite"
        style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 4 }}
      >
        {shown.map((p) => {
          const bad = p.mode === "blocked"
          const reason = reasonOf(p)
          return (
            <li key={p.network} style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6, font: caption, color: bad ? "var(--negative)" : "var(--text-body)" }}>
              <NetworkLogo network={p.network} size={14} />
              <strong style={{ fontWeight: "var(--fw-medium)" }}>{NETWORK_RULES[p.network].label}</strong>
              <span>— {MODE_LABEL[p.mode]}</span>
              {reason && <span style={{ color: bad ? "var(--negative)" : "var(--text-muted)" }}>· {reason}</span>}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
