// Extrapolação: não existe no design system original (ver readme.md → Caveats: "dropdowns").
// Decisão de design: wrapper estilizado sobre <select> nativo, não um listbox customizado —
// mantém navegação por teclado e leitor de tela de graça, e o app não tem volume de opções
// (4-7 itens) que justifique reimplementar um popup. `appearance: none` remove a seta do
// browser; um Icon (chevron-right rotacionado 90°) cobre o fechamento visual no estilo do
// resto do sistema. O popup aberto continua sendo desenhado pelo SO/browser — aceitável,
// é o mesmo comportamento que qualquer <select> nativo tem em qualquer produto.
// Motivado por: PostsPage (persona da IA, rede social, dia da semana do agendamento
// recorrente) e UsersPage (nível de acesso ADMIN/USER).
import { useState } from "react"
import type { ChangeEvent, CSSProperties, ReactNode } from "react"
import { Icon } from "./Icon"

export interface SelectOption {
  value: string
  label: string
}

export interface SelectProps {
  label?: string
  value?: string
  onChange?: (e: ChangeEvent<HTMLSelectElement>) => void
  /** Use `options` for a plain value/label list, or pass raw <option> children. */
  options?: SelectOption[]
  children?: ReactNode
  disabled?: boolean
  required?: boolean
  name?: string
  width?: number | string
  className?: string
  style?: CSSProperties
}

/** Styled wrapper over the native <select> — see the extrapolation note above. */
export function Select({
  label,
  value,
  onChange,
  options,
  children,
  disabled,
  required,
  name,
  width = "100%",
  className = "",
  style,
}: SelectProps) {
  const [hot, setHot] = useState(false)
  const [focused, setFocused] = useState(false)
  const active = hot || focused
  return (
    <label className={className} style={{ display: "block", width, ...style }}>
      {label ? (
        <span
          style={{
            display: "block",
            font: "var(--text-role-label)",
            letterSpacing: "var(--ls-label)",
            textTransform: "uppercase",
            color: "var(--text-muted)",
            marginBottom: 6,
          }}
        >
          {label}
        </span>
      ) : null}
      <span style={{ position: "relative", display: "block" }}>
        <select
          name={name}
          value={value}
          onChange={onChange}
          disabled={disabled}
          required={required}
          onMouseEnter={() => setHot(true)}
          onMouseLeave={() => setHot(false)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          style={{
            width: "100%",
            height: 40,
            padding: "0 36px 0 14px",
            borderRadius: "var(--r-md)",
            background: "var(--surface-inset)",
            border: `1px solid ${active ? "var(--border-strong)" : "var(--border-hairline)"}`,
            color: "var(--text-body)",
            font: "var(--text-role-body)",
            outline: "none",
            appearance: "none",
            transition: "var(--t-hover)",
            cursor: disabled ? "not-allowed" : "pointer",
            opacity: disabled ? 0.5 : 1,
          }}
        >
          {options ? options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>) : children}
        </select>
        <Icon
          name="chevron-right"
          size={14}
          style={{
            position: "absolute",
            right: 12,
            top: "50%",
            transform: "translateY(-50%) rotate(90deg)",
            color: "var(--text-muted)",
            pointerEvents: "none",
          }}
        />
      </span>
    </label>
  )
}
