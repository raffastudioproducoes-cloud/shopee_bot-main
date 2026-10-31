import { useState } from "react"
import type { Profile, ProfileInput } from "../../api/profiles"
import { Modal } from "../ui/Modal"
import { TextInput } from "../ui/TextInput"
import { Button } from "../ui/Button"

interface ProfileFormModalProps {
  /** Perfil em edicao; ausente = criacao. */
  profile?: Profile
  onClose: () => void
  onSubmit: (data: ProfileInput) => void
  loading: boolean
  error?: string | null
}

export function ProfileFormModal({ profile, onClose, onSubmit, loading, error }: ProfileFormModalProps) {
  const [nome, setNome] = useState(profile?.nome ?? "")
  const [email, setEmail] = useState(profile?.email ?? "")
  const [telefone, setTelefone] = useState(profile?.telefone ?? "")
  const [endereco, setEndereco] = useState(profile?.endereco ?? "")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      nome,
      email,
      telefone: telefone.trim() || undefined,
      endereco: endereco.trim() || undefined,
    })
  }

  return (
    <Modal open onClose={onClose} title={profile ? "Editar perfil" : "Novo perfil"} width={400}>
      <form onSubmit={handleSubmit} className="csp-s-0098">
        <TextInput label="Nome *" value={nome} onChange={(e) => setNome(e.target.value)} required />
        <TextInput label="E-mail *" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <TextInput label="Telefone" value={telefone} onChange={(e) => setTelefone(e.target.value)} />
        <TextInput label="Endereço" value={endereco} onChange={(e) => setEndereco(e.target.value)} />

        {error && (
          <p role="alert" className="csp-s-0099">
            {error}
          </p>
        )}

        <div className="csp-s-0100">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" disabled={loading || !nome.trim() || !email.trim()}>
            {loading ? "Salvando..." : profile ? "Salvar" : "Criar"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
