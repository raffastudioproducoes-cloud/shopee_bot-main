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
      className="csp-s-0109"
    >
      <span
        className="csp-s-0110"
      >
        <Icon name={icon} size={15} />
      </span>
      <span
        className="csp-s-0111"
      >
        {value}
      </span>
      <span
        className="csp-s-0112"
      >
        {label}
      </span>
    </div>
  )
}
