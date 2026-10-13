// Resumo de mídia por rede (lib/mediaComposition.ts): 1 linha por rede dizendo o
// que ela recebe; o detalhe técnico fica num <details> recolhido.
import type { PostNetwork } from "../../api/posts"
import { describeKept, dropReasons } from "../../lib/mediaAdapt"
import type { MediaCompositionPlan } from "../../lib/mediaComposition"
import { NETWORK_RULES } from "../../lib/networkLimits"
import { NetworkLogo } from "./NetworkPicker"

interface Props {
  networks: PostNetwork[]
  plans: Record<PostNetwork, MediaCompositionPlan>
}

const caption = "var(--fw-regular) var(--fs-caption)/1.4 var(--font-sans)"

/** Texto curto da linha da rede. */
export function summaryLine(p: MediaCompositionPlan): string {
  const total = p.media.length + p.dropped.length
  if (p.mode === "blocked") return `não enviada — ${p.blockedReason ?? "nada compatível"}`
  if (p.mode === "text_only") return `só texto — ${(p.dropped.length ? dropReasons(p.dropped) : p.warnings[0]) ?? "sem mídia compatível"}`
  if (p.mode === "none") return "só texto"
  const adapted = p.dropped.length ? ` · ${p.media.length} de ${total} mídias` : ""
  return `recebe: ${describeKept(p.media)}${adapted}`
}

export function MediaSummary({ networks, plans }: Props) {
  const rows = networks.map((n) => plans[n])
  if (rows.length === 0 || rows.every((p) => p.mode === "none")) return null
  const detailed = rows.filter((p) => p.dropped.length > 0 || p.warnings.length > 0)

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <span style={{ font: caption, color: "var(--text-muted)" }}>Mídia por rede</span>
      <ul aria-live="polite" style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 4 }}>
        {rows.map((p) => (
          <li
            key={p.network}
            style={{ display: "flex", alignItems: "center", gap: 6, font: caption, color: p.mode === "blocked" ? "var(--negative)" : "var(--text-body)" }}
          >
            <NetworkLogo network={p.network} size={14} />
            <strong style={{ fontWeight: "var(--fw-medium)" }}>{NETWORK_RULES[p.network].label}</strong>
            <span>— {summaryLine(p)}</span>
          </li>
        ))}
      </ul>
      {detailed.length > 0 && (
        <details style={{ font: caption, color: "var(--text-muted)" }}>
          <summary style={{ cursor: "pointer" }}>Ver detalhes</summary>
          <ul style={{ margin: "6px 0 0", padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 2 }}>
            {detailed.flatMap((p) => [
              ...p.dropped.map((d, i) => (
                <li key={`${p.network}-d${i}`}>
                  {NETWORK_RULES[p.network].label}: {d.item.name} não enviado ({d.reason})
                </li>
              )),
              ...p.warnings.map((w, i) => <li key={`${p.network}-w${i}`}>{w}</li>),
            ])}
          </ul>
        </details>
      )}
    </div>
  )
}
