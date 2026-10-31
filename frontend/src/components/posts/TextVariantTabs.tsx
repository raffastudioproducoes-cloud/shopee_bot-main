// Abas "Texto longo / curto" do criador de post: só aparecem quando as redes
// marcadas não cabem no mesmo texto (lib/networkLimits.ts → planVariants).
// Cada aba: redes que usam o texto, contador vs limite do grupo, textarea e
// os bloqueios só daquele grupo. Padrão WAI-ARIA tabs: setas/Home/End movem
// e ativam a aba (foco visível em index.css).
import { useId, useRef, useState, type KeyboardEvent } from "react"
import { NETWORK_RULES, textLength, variantTitle, type Issue, type TextVariantPlan } from "../../lib/networkLimits"
import { Textarea } from "../ui/Textarea"
import { NetworkLogo } from "./NetworkPicker"

interface Props {
  plans: TextVariantPlan[]
  values: string[]
  onChange: (index: number, value: string) => void
  /** Erros de texto das redes de cada grupo (mesma ordem de `plans`). */
  issues: Issue[][]
}

const caption = "var(--fw-regular) var(--fs-caption)/1.4 var(--font-sans)"

export function TextVariantTabs({ plans, values, onChange, issues }: Props) {
  const [active, setActive] = useState(0)
  const current = Math.min(active, plans.length - 1)
  const baseId = useId()
  const tabs = useRef<(HTMLButtonElement | null)[]>([])

  const select = (i: number) => {
    setActive(i)
    tabs.current[i]?.focus()
  }
  const onKeyDown = (e: KeyboardEvent) => {
    const last = plans.length - 1
    const next =
      e.key === "ArrowRight" ? (current === last ? 0 : current + 1)
      : e.key === "ArrowLeft" ? (current === 0 ? last : current - 1)
      : e.key === "Home" ? 0
      : e.key === "End" ? last
      : null
    if (next == null) return
    e.preventDefault()
    select(next)
  }

  const names = (p: TextVariantPlan) => p.networks.map((n) => NETWORK_RULES[n].label).join(", ")
  const plan = plans[current]
  const text = values[current] ?? ""
  const used = Math.max(...plan.networks.map((n) => textLength(NETWORK_RULES[n], text)))
  const bad = issues[current].length > 0

  return (
    <div className="csp-s-0036">
      <p style={{ margin: 0, font: caption, color: "var(--text-muted)" }}>
        As redes marcadas têm limites diferentes: cada aba é o texto de um grupo de redes.
      </p>
      <div role="tablist" aria-label="Texto do post por rede" onKeyDown={onKeyDown} className="csp-s-0037">
        {plans.map((p, i) => {
          const on = i === current
          const invalid = issues[i].length > 0
          return (
            <button
              key={p.key}
              ref={(el) => {
                tabs.current[i] = el
              }}
              type="button"
              role="tab"
              id={`${baseId}-tab-${i}`}
              aria-selected={on}
              aria-controls={`${baseId}-panel-${i}`}
              tabIndex={on ? 0 : -1}
              onClick={() => setActive(i)}
              style={{
                flex: "1 1 160px",
                minHeight: 44,
                padding: "6px 10px",
                borderRadius: "var(--r-md)",
                border: `${on || invalid ? 2 : 1}px solid ${invalid ? "var(--negative)" : on ? "var(--accent)" : "var(--border-hairline)"}`,
                background: on ? "var(--accent-tint)" : "var(--surface-inset)",
                color: invalid ? "var(--negative)" : on ? "var(--accent)" : "var(--text-body)",
                font: `${on ? "var(--fw-medium)" : "var(--fw-regular)"} var(--fs-caption)/1.3 var(--font-sans)`,
                textAlign: "left",
                cursor: "pointer",
                transition: "var(--t-hover)",
              }}
            >
              {variantTitle(i, plans.length)} — {names(p)}
              {invalid && " · bloqueado"}
            </button>
          )
        })}
      </div>
      <div
        role="tabpanel"
        id={`${baseId}-panel-${current}`}
        aria-labelledby={`${baseId}-tab-${current}`}
        className="csp-s-0038"
      >
        <div className="csp-s-0039">
          <span className="csp-s-0040">
            {plan.networks.map((n) => (
              <span
                key={n}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 5,
                  padding: "2px 8px",
                  borderRadius: "var(--r-pill)",
                  border: "1px solid var(--border-hairline)",
                  font: caption,
                  color: "var(--text-body)",
                }}
              >
                <NetworkLogo network={n} size={12} />
                {NETWORK_RULES[n].label}
              </span>
            ))}
          </span>
          <span style={{ font: caption, fontVariantNumeric: "tabular-nums", color: bad ? "var(--negative)" : "var(--text-muted)" }}>
            {used.toLocaleString("pt-BR")}/{plan.maxChars.toLocaleString("pt-BR")} caracteres
          </span>
        </div>
        <Textarea
          ariaLabel={`${variantTitle(current, plans.length)} — ${names(plan)}`}
          value={text}
          onChange={(e) => onChange(current, e.target.value)}
          required={current === 0}
          rows={current === 0 ? 6 : 4}
        />
        {current > 0 && text === values[0] && (
          <p style={{ margin: 0, font: caption, color: "var(--text-muted)" }}>
            Começa igual ao texto longo: reduza para caber em {names(plan)}.
          </p>
        )}
        {bad && (
          <ul aria-live="polite" className="csp-s-0041">
            {issues[current].map((i, idx) => (
              <li key={idx} style={{ font: caption, color: "var(--negative)" }}>
                Bloqueado — {i.message}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
