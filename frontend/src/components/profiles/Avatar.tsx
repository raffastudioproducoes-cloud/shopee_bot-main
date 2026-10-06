import type { CSSProperties } from "react"

export interface AvatarProps {
  name: string
  src?: string | null
  size?: number
  radius?: string
}

/** Foto do perfil, ou iniciais quando nao ha avatar. */
export function Avatar({ name, src, size = 36, radius = "50%" }: AvatarProps) {
  const base: CSSProperties = {
    width: size,
    height: size,
    borderRadius: radius,
    flexShrink: 0,
    border: "1px solid var(--border-hairline)",
  }
  if (src) {
    return <img src={src} alt={`Foto de ${name}`} style={{ ...base, objectFit: "cover", display: "block" }} />
  }
  const initials = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("")
  return (
    <span
      role="img"
      aria-label={`Avatar de ${name}`}
      style={{
        ...base,
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--surface-inset)",
        color: "var(--text-muted)",
        font: `var(--fw-semibold) ${Math.round(size / 3)}px/1 var(--font-sans)`,
      }}
    >
      {initials || "?"}
    </span>
  )
}
