// Extrapolação: não existe no design system original (ver readme.md → Caveats:
// "text inputs beyond search"). Estilo inferido do SearchField (mesmo fundo
// var(--surface-inset), mesma borda hairline -> border-strong no hover/focus) mas
// retangular (var(--r-md)) em vez de pill — um campo de texto solto num formulário
// maior não usa pill no resto do sistema — com label acima no estilo Eyebrow.
// Motivado por: ProductsPage (nome, ID Shopee, links, comissão, preço — text/url/number),
// PostsPage (agendamento — datetime-local/time), CredentialsPage (APP ID/secret/token —
// text/password), ListasPage e UsersPage (nome/usuário/senha).
import { useId, useState } from "react"
import type { ChangeEvent, CSSProperties, InputHTMLAttributes } from "react"
import { Icon } from "./Icon"
import "./motion.css"
import "./fieldMessage.css"

/** Só data/hora ficam com o rótulo sempre no alto; campos com placeholder (ex.: CPF) mantêm o rótulo dentro até o foco, como os demais. Tipos cujo campo nativo já mostra algo (data/hora): o rótulo fica sempre no alto. */
const ALWAYS_UP_TYPES = new Set(["date", "datetime-local", "time", "month", "week", "color", "file"])

export interface TextInputProps {
  label?: string
  value?: string
  onChange?: (e: ChangeEvent<HTMLInputElement>) => void
  type?: InputHTMLAttributes<HTMLInputElement>["type"]
  placeholder?: string
  required?: boolean
  minLength?: number
  maxLength?: number
  disabled?: boolean
  name?: string
  autoComplete?: string
  min?: string | number
  max?: string | number
  step?: string | number
  inputMode?: InputHTMLAttributes<HTMLInputElement>["inputMode"]
  pattern?: string
  title?: string
  width?: number | string
  className?: string
  style?: CSSProperties
  inputStyle?: CSSProperties
  /** Lucide icon name (kebab-case), rendered inside the field on the left. */
  icon?: string
  /** Mensagem de erro do campo (mostrada abaixo, em vermelho). */
  error?: string | null
  /** Ajuda fixa abaixo do campo (ex.: regra de preenchimento). */
  hint?: string
  onBlur?: () => void
}

/** Retangular text field with an Eyebrow-style label above it. */
export function TextInput({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
  required,
  minLength,
  maxLength,
  disabled,
  name,
  autoComplete,
  min,
  max,
  step,
  inputMode,
  pattern,
  title,
  width = "100%",
  className = "",
  style,
  inputStyle,
  icon,
  error,
  hint,
  onBlur,
}: TextInputProps) {
  const msgId = useId()
  const [hot, setHot] = useState(false)
  const [focused, setFocused] = useState(false)
  const [revealed, setRevealed] = useState(false)
  const active = hot || focused
  // Extrapolação: toggle "mostrar senha" pro type="password" — aplicado aqui (em vez
  // de replicado campo a campo, como era feito antes só na LoginPage) pra cobrir de
  // uma vez todos os campos de senha do app (login, criar conta, trocar senha,
  // credenciais, usuários).
  const isPassword = type === "password"
  const inputType = isPassword ? (revealed ? "text" : "password") : type
  return (
    <label className={className} style={{ display: "block", width, ...style }}>
      <div className={`ao-float${label ? "" : " ao-float-bare"}${icon ? " has-icon" : ""}${ALWAYS_UP_TYPES.has(type) ? " is-up" : ""}`}>
        {icon ? (
          <span
            className="csp-s-0144"
          >
            <Icon name={icon} size={16} />
          </span>
        ) : null}
        <input
          name={name}
          type={inputType}
          value={value}
          onChange={onChange}
          placeholder={label ? (placeholder ?? " ") : placeholder}
          required={required}
          minLength={minLength}
          maxLength={maxLength}
          disabled={disabled}
          autoComplete={autoComplete}
          min={min}
          max={max}
          step={step}
          inputMode={inputMode}
          pattern={pattern}
          title={title}
          onMouseEnter={() => setHot(true)}
          onMouseLeave={() => setHot(false)}
          onFocus={() => setFocused(true)}
          onBlur={() => { setFocused(false); onBlur?.() }}
          aria-invalid={error ? true : undefined}
          aria-describedby={error || hint ? msgId : undefined}
          className="ao-input"
          style={{
            width: "100%",
            height: label ? 48 : 40,
            padding: label ? `16px ${isPassword ? 40 : 14}px 0 ${icon ? 40 : 14}px` : `0 ${isPassword ? 40 : 14}px 0 ${icon ? 40 : 14}px`,
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
        {label ? <span className="ao-float-label">{label}</span> : null}
        {isPassword ? (
          <button
            type="button"
            onClick={() => setRevealed((v) => !v)}
            disabled={disabled}
            aria-label={revealed ? "Ocultar senha" : "Mostrar senha"}
            style={{
              position: "absolute",
              right: 8,
              top: "50%",
              transform: "translateY(-50%)",
              display: "inline-flex",
              background: "none",
              border: "none",
              color: "var(--text-muted)",
              cursor: disabled ? "not-allowed" : "pointer",
              padding: 4,
            }}
          >
            <Icon name={revealed ? "eye-off" : "eye"} size={18} />
          </button>
        ) : null}
      </div>
      {error ? <small id={msgId} role="alert" className="ao-field-msg ao-field-msg--error">{error}</small>
        : hint ? <small id={msgId} className="ao-field-msg">{hint}</small> : null}
    </label>
  )
}
