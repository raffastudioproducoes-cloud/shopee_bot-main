// Extrapolação: não existe no design system original. Layout pedido pelo
// usuário a partir de um print de referência (card de cotação de frete: tiles
// de estatística no topo + timeline vertical com seções tipo Shipper/Vehicle/
// Pickup/Delivery/Carrier). Reaproveita só as variáveis de cor/tipografia/
// espaçamento já existentes no app — nenhuma cor nova.
//
// Recolhido por padrão (cabeçalho compacto); expande ao clicar mostrando os
// InfoStat no topo e a timeline de seções. Usado em ProductsPage, ListasPage
// e UsersPage no lugar da tabela/linha de Panel que existia antes.
import { useState } from "react"
import type { ReactNode, CSSProperties } from "react"
import { Icon } from "./Icon"
import { Panel, Divider } from "./Panel"
import { InfoStat } from "./InfoStat"

export interface TimelineStat {
  icon: string
  label: string
  value: ReactNode
}

export interface TimelineSection {
  /** Título da seção, ex: "Produto", "Preço". */
  label: string
  /** Subtítulo pequeno abaixo do label, ex: "Individual", "1 car". */
  category?: string
  content: ReactNode
}

export interface TimelineListCardProps {
  title: ReactNode
  /** Linha secundária ao lado do título, sempre visível (recolhido ou não). */
  subtitle?: ReactNode
  /** Miniatura opcional à esquerda do título (ex: imagem do produto). */
  thumbnail?: ReactNode
  /** Pill no canto superior direito do cabeçalho (ex: Badge de categoria/acesso). */
  badge?: ReactNode
  stats: TimelineStat[]
  sections: TimelineSection[]
  /** Botões de ação (editar/remover), ficam entre o badge e o chevron. */
  actions?: ReactNode
  defaultOpen?: boolean
  style?: CSSProperties
}

export function TimelineListCard({
  title,
  subtitle,
  thumbnail,
  badge,
  stats,
  sections,
  actions,
  defaultOpen = false,
  style,
}: TimelineListCardProps) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <Panel surface="dark" className="timeline-list-card" style={{ padding: 0, ...style }}>
      <div
        className="timeline-card-heading"
        onClick={() => setOpen((v) => !v)}
        role="button"
        aria-expanded={open}
        style={{
          display: "flex",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 12,
          padding: 16,
          cursor: "pointer",
        }}
      >
        {thumbnail}
        {/* flex-basis 160px: em telas estreitas badge/ações quebram para a linha de
            baixo em vez de espremer o título; título mostra até 2 linhas. */}
        <div style={{ minWidth: 0, flex: "1 1 160px" }}>
          <div
            title={typeof title === "string" ? title : undefined}
            style={{
              font: "var(--text-role-title)",
              color: "var(--text-display)",
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
              overflowWrap: "anywhere",
            }}
          >
            {title}
          </div>
          {subtitle ? (
            <div
              style={{
                font: "var(--fs-small)/1.4 var(--font-sans)",
                color: "var(--text-muted)",
                marginTop: 2,
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {subtitle}
            </div>
          ) : null}
        </div>
        {badge}
        {actions ? (
          <div onClick={(e) => e.stopPropagation()} style={{ display: "flex", alignItems: "center", gap: 2, flexShrink: 0 }}>
            {actions}
          </div>
        ) : null}
        <span
          style={{
            display: "inline-flex",
            color: "var(--text-muted)",
            flexShrink: 0,
            transform: open ? "rotate(180deg)" : "none",
            transition: "transform var(--dur-fast, .15s) var(--ease-standard, ease)",
          }}
        >
          <Icon name="chevron-down" size={18} />
        </span>
      </div>

      {open ? (
        <div style={{ padding: "0 16px 16px" }}>
          <Divider style={{ marginBottom: 16 }} />

          {stats.length > 0 ? (
            <div
              className="timeline-card-stats"
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(90px, 1fr))",
                gap: 8,
                marginBottom: 20,
              }}
            >
              {stats.map((s, i) => (
                <InfoStat key={i} icon={s.icon} label={s.label} value={s.value} />
              ))}
            </div>
          ) : null}

          <div style={{ position: "relative" }}>
            <div
              style={{
                position: "absolute",
                left: 5,
                top: 5,
                bottom: 5,
                width: 1,
                background: "var(--border-hairline)",
              }}
            />
            {sections.map((section, i) => (
              <div
                key={i}
                className="timeline-card-section"
                style={{
                  position: "relative",
                  display: "flex",
                  gap: 16,
                  paddingLeft: 24,
                  paddingBottom: i === sections.length - 1 ? 0 : 16,
                }}
              >
                <span
                  style={{
                    position: "absolute",
                    left: 1,
                    top: 5,
                    width: 9,
                    height: 9,
                    borderRadius: "50%",
                    background: "var(--sky-400)",
                    boxShadow: "0 0 0 3px var(--surface-card)",
                  }}
                />
                <div style={{ width: 130, flexShrink: 0 }}>
                  <div style={{ font: "var(--fw-medium) var(--fs-body)/1.3 var(--font-sans)", color: "var(--text-display)" }}>
                    {section.label}
                  </div>
                  {section.category ? (
                    <div style={{ font: "var(--fs-caption)/1.3 var(--font-sans)", color: "var(--text-muted)" }}>
                      {section.category}
                    </div>
                  ) : null}
                </div>
                <div style={{ flex: 1, minWidth: 0, font: "var(--text-role-body)", color: "var(--text-body)" }}>
                  {section.content}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </Panel>
  )
}
