import { useEffect, useState } from "react"
import { useAuthStore } from "../../stores/authStore"
import { formDraftKey } from "../../lib/formDraftStorage"
import { useAutosavedDraft } from "../../hooks/useAutosavedDraft"
import type { Profile, ProfileInput } from "../../api/profiles"
import { Modal } from "../ui/Modal"
import { TextInput } from "../ui/TextInput"
import { Button } from "../ui/Button"
import { Avatar } from "./Avatar"

interface ProfileFormModalProps {
  /** Perfil em edição; ausente = criação. */
  profile?: Profile
  onClose: () => void
  onSubmit: (data: ProfileInput, avatar?: File) => void
  loading: boolean
  error?: string | null
}

const MAX_AVATAR_BYTES = 5 * 1024 * 1024
const ACCEPTED_AVATARS = new Set(["image/jpeg", "image/png", "image/webp"])

export function ProfileFormModal({ profile, onClose, onSubmit, loading, error }: ProfileFormModalProps) {
  const [nome, setNome] = useState(profile?.nome ?? "")
  const [avatar, setAvatar] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [fileError, setFileError] = useState("")
  const userId = useAuthStore((state) => state.user?.id)
  const key = formDraftKey(userId, profile ? `profile-edit:${profile.id}` : "profile-create", null, false)

  // Apenas nome no rascunho: não duplicamos e-mail/endereço/telefone da conta.
  useAutosavedDraft(key, { nome }, (saved) => {
    setNome(typeof saved?.nome === "string" ? saved.nome : (profile?.nome ?? ""))
  })

  useEffect(() => {
    if (!avatar) { setPreview(null); return }
    const url = URL.createObjectURL(avatar)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [avatar])

  const onFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ""
    if (!file) return
    if (!ACCEPTED_AVATARS.has(file.type) || file.size > MAX_AVATAR_BYTES) {
      setFileError("Use uma foto JPG, PNG ou WebP com até 5 MB.")
      setAvatar(null)
      return
    }
    setFileError("")
    setAvatar(file)
  }

  return (
    <Modal open onClose={onClose} title={profile ? "Editar perfil" : "Novo perfil"} width={400}>
      <form onSubmit={(event) => {
        event.preventDefault()
        onSubmit({ nome: nome.trim() }, avatar ?? undefined)
      }} className="csp-s-0098">
        <TextInput label="Nome do perfil *" value={nome} onChange={(event) => setNome(event.target.value)} required maxLength={100} />
        <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <Avatar name={nome || "Perfil"} src={preview || profile?.avatar_url} size={84} radius="var(--r-lg)" />
          <label style={{ display: "grid", gap: 6, color: "var(--text-muted)", fontSize: 13 }}>
            Foto do perfil (opcional)
            <input type="file" accept="image/png,image/jpeg,image/webp" onChange={onFileChange}
              aria-label="Foto do perfil" />
          </label>
        </div>
        {fileError && <p role="alert" className="csp-s-0099">{fileError}</p>}
        {error && <p role="alert" className="csp-s-0099">{error}</p>}
        <p style={{ font: "var(--text-role-body)", color: "var(--text-muted)" }}>
          Toque no card do perfil para usá-lo. Nome e foto identificam cada perfil; os dados pessoais ficam na conta.
        </p>
        <div className="csp-s-0100">
          <Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button type="submit" variant="primary" disabled={loading || !nome.trim() || Boolean(fileError)}>
            {loading ? "Salvando..." : profile ? "Salvar" : "Criar"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
