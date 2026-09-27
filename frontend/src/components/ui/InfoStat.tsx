// Extrapolação: não existe no design system original — inferido do print de
// referência (card de cotação com 4 tiles no topo: #, data, distância, preço).
// Reaproveita var(--surface-inset) (mesmo fundo do TextInput) em vez de um
// tom novo, e as mesmas variáveis de tipografia do resto do app.
import type { ReactNode } from "react"
import { Icon } from "./Icon"

export interface InfoStatProps {
  icon: string
  label: string
  value: ReactNode
}

export function InfoStat({ icon, label, value }: InfoStatProps) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 6,
        padding: "12px 8px",
        borderRadius: "var(--r-md)",
        background: "var(--surface-inset)",
        textAlign: "center",
      }}
    >
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          width: 30,
          height: 30,
          borderRadius: "50%",
          background: "rgba(129,189,250,.16)",
          color: "var(--sky-300)",
        }}
      >
        <Icon name={icon} size={15} />
      </span>
      <span
        style={{
          font: "var(--fw-semibold) var(--fs-body)/1.1 var(--font-sans)",
          color: "var(--text-display)",
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
          maxWidth: "100%",
        }}
      >
        {value}
      </span>
      <span
        style={{
          font: "var(--text-role-label)",
          letterSpacing: "var(--ls-label)",
          textTransform: "uppercase",
          color: "var(--text-muted)",
        }}
      >
        {label}
      </span>
    </div>
  )
}
