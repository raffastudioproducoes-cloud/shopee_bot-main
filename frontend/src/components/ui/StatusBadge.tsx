// Extrapolação: não existe no design system original (ver readme.md → Caveats: no equivalente
// direto pra "status" — o mais perto é DeltaChip, que é sobre variação numérica, não estado).
// Fino wrapper sobre Badge.tsx (já portado): tone="mint" para positivo/ativo, tone="neutral"
// para o padrão. Sem tone de erro: nenhuma das 5 páginas hoje mostra um estado de falha nesse
// formato de badge (CredentialsPage só tem conectado/desconectado; UsersPage só ADMIN/USER;
// PostsPage usa Badge "neutral" simples pra "Agendado") — adicionar tone="negative"
// (var(--red-300) / var(--negative-ink)) em Badge.tsx quando alguma página precisar.
// Motivado por: CredentialsPage (Conectado/Desconectado em 7 cards de rede) e UsersPage
// (badge de nível de acesso ADMIN/USER).
import type { ReactNode, CSSProperties } from "react"
import { Badge } from "./Badge"
import { Icon } from "./Icon"

export interface StatusBadgeProps {
  children?: ReactNode
  /** positive = conectado/ativo (mint). neutral = desconectado/padrão. */
  tone?: "positive" | "neutral"
  /** Lucide icon name mostrado antes do texto — ex. "check-circle-2" / "x-circle". */
  icon?: string
  className?: string
  style?: CSSProperties
}

/** Pill status label — "Conectado"/"Desconectado", "ADMIN"/"USER". */
export function StatusBadge({ children, tone = "neutral", icon, className = "", style }: StatusBadgeProps) {
  return (
    <Badge tone={tone === "positive" ? "mint" : "neutral"} className={className} style={{ gap: 6, ...style }}>
      {icon ? <Icon name={icon} size={13} /> : null}
      {children}
    </Badge>
  )
}
