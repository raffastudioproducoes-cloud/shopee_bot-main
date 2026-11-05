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
  /** Conteúdo logo após o cabeçalho, antes dos links e indicadores. */
  expandedHeader?: ReactNode
  /** Bloco em largura total, montado somente com o card expandido. */
  expandedFooter?: ReactNode
  /** Mantém os indicadores no topo por padrão; produtos usam o rodapé. */
  statsPlacement?: "top" | "bottom"
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
  expandedHeader,
  expandedFooter,
  statsPlacement = "top",
  defaultOpen = false,
  style,
}: TimelineListCardProps) {
  const [open, setOpen] = useState(defaultOpen)
  const statsContent = stats.length > 0 ? (
    <div
      className="timeline-card-stats"
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(90px, 1fr))",
        gap: 8,
        marginBottom: statsPlacement === "top" ? 20 : 0,
      }}
    >
      {stats.map((stat, index) => (
        <InfoStat key={index} icon={stat.icon} label={stat.label} value={stat.value} />
      ))}
    </div>
  ) : null

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
        <div className="csp-s-0146">
          <div
            title={typeof title === "string" ? title : undefined}
            className="csp-s-0147"
          >
            {title}
          </div>
          {subtitle ? (
            <div
              className="csp-s-0148"
            >
              {subtitle}
            </div>
          ) : null}
        </div>
        {badge}
        {actions ? (
          <div onClick={(e) => e.stopPropagation()} className="csp-s-0149">
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
        <div className="csp-s-0150">
          <Divider style={{ marginBottom: 16 }} />

          {statsPlacement === "top" ? statsContent : null}

          {expandedHeader ? (
            <div style={{ marginBottom: 20 }}>{expandedHeader}</div>
          ) : null}

          {sections.length > 0 ? <div className="csp-s-0151">
            <div
              className="csp-s-0152"
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
                  className="csp-s-0153"
                />
                <div className="csp-s-0154">
                  <div className="csp-s-0155">
                    {section.label}
                  </div>
                  {section.category ? (
                    <div className="csp-s-0156">
                      {section.category}
                    </div>
                  ) : null}
                </div>
                <div className="csp-s-0157">
                  {section.content}
                </div>
              </div>
            ))}
          </div> : null}
          {statsPlacement === "bottom" && statsContent ? (
            <div style={{ marginTop: sections.length > 0 ? 20 : 0 }}>{statsContent}</div>
          ) : null}
          {expandedFooter ? (
            <div style={{ marginTop: 18, paddingTop: 16, borderTop: "1px solid var(--border)" }}>
              {expandedFooter}
            </div>
          ) : null}
        </div>
      ) : null}
    </Panel>
  )
}
