import { Link } from "@tanstack/react-router"
import { Avatar } from "./Avatar"
import { useProfiles } from "../../hooks/useProfiles"

/** Perfil ativo na TopBar, com link para /profiles. */
export function ActiveProfileChip() {
  const { activeProfile } = useProfiles()
  if (!activeProfile) return null
  return (
    <Link
      to="/profiles"
      className="active-profile-chip"
      aria-label={`Perfil ativo: ${activeProfile.nome}. Gerenciar perfis`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        minHeight: 44,
        padding: "0 12px 0 4px",
        borderRadius: 999,
        background: "rgba(255,255,255,.14)",
        color: "var(--text-body)",
        textDecoration: "none",
        font: "var(--fw-medium) var(--fs-body)/1 var(--font-sans)",
      }}
    >
      <Avatar name={activeProfile.nome} src={activeProfile.avatar_url} size={36} />
      <span style={{ maxWidth: 140, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {activeProfile.nome}
      </span>
    </Link>
  )
}
