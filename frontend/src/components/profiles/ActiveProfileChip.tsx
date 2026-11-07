import type { CSSProperties } from "react"
import { Link } from "@tanstack/react-router"
import { Avatar } from "./Avatar"
import { Skeleton } from "../ui/Skeleton"
import { useProfiles } from "../../hooks/useProfiles"

/** A mesma geometria serve ao perfil real e ao placeholder de carregamento. */
const chipStyle: CSSProperties = {
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
}

/** Perfil ativo na TopBar, com link para /profiles. */
export function ActiveProfileChip() {
  const { activeProfile, isPending } = useProfiles()

  // Reserva o espaço do cartão frontal antes de o perfil chegar. Nunca exibe
  // uma etiqueta de plano solta sobre os botões durante o carregamento.
  if (!activeProfile) {
    if (!isPending) return null
    return (
      <span className="active-profile-chip active-profile-chip--loading"
        style={chipStyle} role="status" aria-label="Carregando perfil" aria-busy="true">
        <Skeleton className="active-profile-loading-avatar" width={48} height={48} radius="50%" />
        <Skeleton className="active-profile-loading-name" width={95} height={16} radius={8} />
      </span>
    )
  }
  return (
    <Link
      to="/profiles"
      className="active-profile-chip"
      aria-label={`Perfil ativo: ${activeProfile.nome}. Gerenciar perfis`}
      style={chipStyle}
    >
      <Avatar name={activeProfile.nome} src={activeProfile.avatar_url} size={48} />
      <span className="csp-s-0072">
        {activeProfile.nome}
      </span>
    </Link>
  )
}
