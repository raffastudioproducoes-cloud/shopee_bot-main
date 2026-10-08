// Extrapolação: não existe no design system original (ver readme.md → Caveats:
// "text inputs beyond search"). Mesmo visual do TextInput.tsx (fundo var(--surface-inset),
// borda hairline -> border-strong, radius var(--r-md), label em estilo Eyebrow) aplicado a
// um <textarea>. Motivado por PostsPage: texto do post e cada parte de thread (`post.texts`).
import { useState } from "react"
import type { ChangeEvent, CSSProperties } from "react"

export interface TextareaProps {
  label?: string
  value?: string
  onChange?: (e: ChangeEvent<HTMLTextAreaElement>) => void
  placeholder?: string
  required?: boolean
  disabled?: boolean
  name?: string
  rows?: number
  width?: number | string
  className?: string
  style?: CSSProperties
  textareaStyle?: CSSProperties
  /** Nome acessível quando não há `label` visível. */
  ariaLabel?: string
}

/** Multi-line text field, same surface treatment as TextInput. */
export function Textarea({
  label,
  value,
  onChange,
  placeholder,
  required,
  disabled,
  name,
  rows = 4,
  width = "100%",
  className = "",
  style,
  textareaStyle,
  ariaLabel,
}: TextareaProps) {
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
      <textarea
        name={name}
        aria-label={ariaLabel}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        disabled={disabled}
        rows={rows}
        onMouseEnter={() => setHot(true)}
        onMouseLeave={() => setHot(false)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          width: "100%",
          padding: "10px 14px",
          borderRadius: "var(--r-md)",
          background: "var(--surface-inset)",
          border: `1px solid ${active ? "var(--border-strong)" : "var(--border-hairline)"}`,
          color: "var(--text-body)",
          font: "var(--text-role-body)",
          outline: "none",
          resize: "vertical",
          transition: "var(--t-hover)",
          opacity: disabled ? 0.5 : 1,
          cursor: disabled ? "not-allowed" : "text",
          ...textareaStyle,
        }}
      />
    </label>
  )
}
