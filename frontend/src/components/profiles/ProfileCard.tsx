import { useEffect, useRef, useState } from "react"
import type { Profile } from "../../api/profiles"
import { Panel } from "../ui/Panel"
import { Button } from "../ui/Button"
import { IconButton } from "../ui/IconButton"
import { Avatar } from "./Avatar"
import "./profileCard.css"

interface ProfileCardProps {
  profile: Profile
  active: boolean
  activating: boolean
  onActivate: () => void
  onEdit: () => void
  onDelete: () => void
  onAvatarFile: (file: File) => void
}

/** A identidade visual é apenas nome/foto; gestão fica num menu discreto. */
export function ProfileCard({ profile, active, activating, onActivate, onEdit, onDelete, onAvatarFile }: ProfileCardProps) {
  const fileRef = useRef<HTMLInputElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    if (!menuOpen) return
    const closeOutside = (event: PointerEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false)
    }
    const closeEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false)
    }
    document.addEventListener("pointerdown", closeOutside)
    document.addEventListener("keydown", closeEscape)
    return () => {
      document.removeEventListener("pointerdown", closeOutside)
      document.removeEventListener("keydown", closeEscape)
    }
  }, [menuOpen])

  return (
    <Panel className="profile-card profile-card--minimal" surface={active ? "glass" : "dark"} overflowHidden={false}
      style={{ outline: active ? "2px solid var(--accent)" : undefined, outlineOffset: -2,
        padding: "16px 48px 16px 16px", zIndex: menuOpen ? 5 : undefined }}>
      <button type="button" className="profile-card__select" disabled={active || activating}
        aria-label={active ? `Perfil ${profile.nome} em uso` : `Ativar perfil ${profile.nome}`}
        aria-current={active ? "true" : undefined} aria-busy={activating}
        onClick={onActivate}>
        <Avatar name={profile.nome} src={profile.avatar_url} size={96} radius="var(--r-lg)" />
        <span className="profile-card__name">{profile.nome}</span>
      </button>

      <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp"
        aria-label={`Escolher foto de ${profile.nome}`} className="profile-card__file"
        tabIndex={-1} onChange={(event) => {
          const file = event.target.files?.[0]
          event.target.value = ""
          if (file) onAvatarFile(file)
        }} />

      <div className="profile-card__menu" ref={menuRef}>
        <IconButton icon="ellipsis" label={`Opções do perfil ${profile.nome}`}
          tone="plain" size={44} aria-expanded={menuOpen} onClick={() => setMenuOpen(value => !value)} />
        {menuOpen && <div className="profile-card__menu-list" role="group" aria-label={`Gerenciar perfil ${profile.nome}`}>
          <Button variant="ghost" size="sm" icon="camera" onClick={() => {
            setMenuOpen(false)
            fileRef.current?.click()
          }}>Alterar foto</Button>
          <Button variant="ghost" size="sm" icon="pencil" onClick={() => {
            setMenuOpen(false)
            onEdit()
          }}>Editar nome</Button>
          {profile.kind !== "principal" && <Button variant="ghost" size="sm" icon="trash-2" onClick={() => {
            setMenuOpen(false)
            onDelete()
          }}>Excluir perfil</Button>}
        </div>}
      </div>
    </Panel>
  )
}
