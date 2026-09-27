// Extrapolação: não existe no design system original (ver readme.md → Caveats:
// "text inputs beyond search"). Estilo inferido do SearchField (mesmo fundo
// var(--surface-inset), mesma borda hairline -> border-strong no hover/focus) mas
// retangular (var(--r-md)) em vez de pill — um campo de texto solto num formulário
// maior não usa pill no resto do sistema — com label acima no estilo Eyebrow.
// Motivado por: ProductsPage (nome, ID Shopee, links, comissão, preço — text/url/number),
// PostsPage (agendamento — datetime-local/time), CredentialsPage (APP ID/secret/token —
// text/password), ListasPage e UsersPage (nome/usuário/senha).
import { useState } from "react"
import type { ChangeEvent, CSSProperties, InputHTMLAttributes } from "react"

export interface TextInputProps {
  label?: string
  value?: string
  onChange?: (e: ChangeEvent<HTMLInputElement>) => void
  type?: InputHTMLAttributes<HTMLInputElement>["type"]
  placeholder?: string
  required?: boolean
  disabled?: boolean
  name?: string
  autoComplete?: string
  min?: string | number
  max?: string | number
  step?: string | number
  width?: number | string
  className?: string
  style?: CSSProperties
  inputStyle?: CSSProperties
}

/** Retangular text field with an Eyebrow-style label above it. */
export function TextInput({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
  required,
  disabled,
  name,
  autoComplete,
  min,
  max,
  step,
  width = "100%",
  className = "",
  style,
  inputStyle,
}: TextInputProps) {
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
      <input
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        disabled={disabled}
        autoComplete={autoComplete}
        min={min}
        max={max}
        step={step}
        onMouseEnter={() => setHot(true)}
        onMouseLeave={() => setHot(false)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          width: "100%",
          height: 40,
          padding: "0 14px",
          borderRadius: "var(--r-md)",
          background: "var(--surface-inset)",
          border: `1px solid ${active ? "var(--border-strong)" : "var(--border-hairline)"}`,
          color: "var(--text-body)",
          font: "var(--text-role-body)",
          outline: "none",
          transition: "var(--t-hover)",
          opacity: disabled ? 0.5 : 1,
          cursor: disabled ? "not-allowed" : "text",
          ...inputStyle,
        }}
      />
    </label>
  )
}
