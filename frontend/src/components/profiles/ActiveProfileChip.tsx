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
        gap: 9,
        minHeight: 52,
        padding: "0 16px 0 5px",
        borderRadius: 22,
        background: "rgba(255,255,255,.14)",
        boxShadow: "0 9px 18px rgba(0,0,0,.24)",
        color: "var(--text-body)",
        textDecoration: "none",
        font: "var(--fw-medium) var(--fs-body)/1 var(--font-sans)",
      }}
    >
      <Avatar name={activeProfile.nome} src={activeProfile.avatar_url} size={40} />
      <span className="csp-s-0072">
        {activeProfile.nome}
      </span>
    </Link>
  )
}
