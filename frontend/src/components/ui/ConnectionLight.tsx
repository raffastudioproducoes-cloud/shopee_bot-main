// Extrapolação: não existe no design system original — pedido pelo usuário
// junto com o botão "Testar conexão" (ver CredentialsPage.tsx). Ponto
// luminoso com glow neon sutil, visível pra QUALQUER usuário (admin ou não)
// — só o botão que dispara o teste é admin-only, a luz em si não é.
//
// green: testado e funcionando. yellow: testado e encontrou um problema
// (API incorreta, instável, falta autorizar OAuth). red: nunca testado
// ainda, ou sem credencial salva. Reaproveita as cores já existentes
// (mint/amber/red) — nenhuma cor nova no tema.
import type { CSSProperties } from "react"

export type ConnectionLightState = "green" | "yellow" | "red"

const COLORS: Record<ConnectionLightState, string> = {
  green: "var(--mint-400)",
  yellow: "var(--amber-300)",
  red: "var(--red-300)",
}

const LABELS: Record<ConnectionLightState, string> = {
  green: "Conectado",
  yellow: "Conexão instável ou credencial incorreta",
  red: "Desconectado",
}

export interface ConnectionLightProps {
  state: ConnectionLightState
  /** Sobrescreve o texto do title (ex: mensagem real do último teste). */
  title?: string
  style?: CSSProperties
}

export function ConnectionLight({ state, title, style }: ConnectionLightProps) {
  const color = COLORS[state]
  return (
    <span
      role="img"
      aria-label={title ?? LABELS[state]}
      title={title ?? LABELS[state]}
      style={{
        display: "inline-block",
        width: 9,
        height: 9,
        borderRadius: "50%",
        background: color,
        boxShadow: `0 0 4px 1px ${color}, 0 0 1px 0 ${color}`,
        flexShrink: 0,
        ...style,
      }}
    />
  )
}
