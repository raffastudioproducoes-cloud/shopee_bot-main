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
        gap: 12,
        minHeight: 70,
        padding: "0 23px 0 8px",
        borderRadius: 26,
        background: "#303440",
        boxShadow: "0 9px 18px rgba(0,0,0,.24)",
        color: "var(--text-body)",
        textDecoration: "none",
        font: "var(--fw-medium) 16px/1 var(--font-sans)",
      }}
    >
      <Avatar name={activeProfile.nome} src={activeProfile.avatar_url} size={48} />
      <span className="csp-s-0072">
        {activeProfile.nome}
      </span>
    </Link>
  )
}
