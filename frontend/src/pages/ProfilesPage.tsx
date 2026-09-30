import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useRef, useState } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import { usersApi, type AppUser, type UserAccess } from "../api/users"
import { profilesApi, type Profile } from "../api/profiles"
import { Panel } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { IconButton } from "../components/ui/IconButton"
import { Badge } from "../components/ui/Badge"
import { Modal } from "../components/ui/Modal"
import { TextInput } from "../components/ui/TextInput"
import { Select } from "../components/ui/Select"
import { TimelineListCard } from "../components/ui/TimelineListCard"
import { Icon } from "../components/ui/Icon"

const planTierLabel: Record<Profile["plan_tier"], string> = {
  free: "Free",
  plus: "Plus",
  premium: "Premium",
}
const planTierTone: Record<Profile["plan_tier"], "neutral" | "outline" | "mint"> = {
  free: "neutral",
  plus: "outline",
  premium: "mint",
}
const kindLabel: Record<Profile["kind"], string> = {
  principal: "Principal",
  secundario: "Secundário",
}

export function ProfilesPage() {
  const { user, logout } = useAuthStore()
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<AppUser | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const [profileModalOpen, setProfileModalOpen] = useState(false)
  const [avatarError, setAvatarError] = useState<string | null>(null)
  const avatarInputs = useRef<Record<string, HTMLInputElement | null>>({})

  const { data: profiles = [] } = useQuery({
    queryKey: ["profiles"],
    queryFn: () => profilesApi.list(),
  })

  const invalidateProfiles = () => queryClient.invalidateQueries({ queryKey: ["profiles"] })

  const createProfileMutation = useMutation({
    mutationFn: profilesApi.create,
    onSuccess: () => {
      invalidateProfiles()
      setProfileModalOpen(false)
    },
  })

  const activateMutation = useMutation({
    mutationFn: (id: string) => profilesApi.activate(id),
    onSuccess: () => {
      window.location.reload()
    },
  })

  const uploadAvatarMutation = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => profilesApi.uploadAvatar(id, file),
    onSuccess: () => {
      setAvatarError(null)
      invalidateProfiles()
    },
    onError: (err: Error) => setAvatarError(err.message),
  })

  const handleAvatarChange = (profileId: string, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ""
    if (!file) return
    uploadAvatarMutation.mutate({ id: profileId, file })
  }

  const { data, isLoading, error } = useQuery({
    queryKey: ["users"],
    queryFn: () => usersApi.list(),
    enabled: user?.access === "ADMIN",
  })

  const onAuthError = (err: Error) => {
    if (err.message.includes("401") || err.message === "Não autenticado") {
      logout()
      router.navigate({ to: "/login" })
    }
  }

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["users"] })

  const createMutation = useMutation({
    mutationFn: usersApi.create,
    onSuccess: () => {
      invalidate()
      setModalOpen(false)
    },
    onError: onAuthError,
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, username, access }: { id: string; username: string; access: UserAccess }) =>
      usersApi.update(id, { username, access }),
    onSuccess: () => {
      invalidate()
      setModalOpen(false)
      setEditingUser(null)
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => usersApi.delete(id),
    onSuccess: () => {
      invalidate()
      setDeleteConfirm(null)
    },
    onError: onAuthError,
  })

  const users = data?.data ?? []

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap-column)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ font: "var(--text-role-hero)", color: "var(--text-display)", margin: 0 }}>Perfis</h1>
          <p style={{ color: "var(--text-muted)", marginTop: 4 }}>Perfis de uso da conta.</p>
        </div>
        <Button
          variant="primary"
          icon="plus"
          disabled={profiles.length >= 3}
          title={profiles.length >= 3 ? "Limite de 3 perfis atingido" : undefined}
          onClick={() => setProfileModalOpen(true)}
        >
          Novo perfil
        </Button>
      </div>

      {avatarError && (
        <div style={{ color: "var(--negative-ink)", font: "var(--fw-medium) var(--fs-body)/1.3 var(--font-sans)" }}>
          {avatarError}
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
          gap: 16,
        }}
      >
        {profiles.map((profile) => (
          <Panel
            key={profile.id}
            style={{ padding: 16, cursor: "pointer" }}
            onClick={() => activateMutation.mutate(profile.id)}
            role="button"
            tabIndex={0}
            aria-label={`Ativar perfil ${profile.nome}`}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault()
                activateMutation.mutate(profile.id)
              }
            }}
          >
            <div style={{ position: "relative" }}>
              <img
                src={profile.avatar_url ?? "/avatar-placeholder.png"}
                alt={profile.nome}
                style={{ width: "100%", aspectRatio: "1 / 1", objectFit: "cover", borderRadius: "var(--r-lg)" }}
              />
              <input
                ref={(el) => {
                  avatarInputs.current[profile.id] = el
                }}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                style={{ display: "none" }}
                onClick={(e) => e.stopPropagation()}
                onChange={(e) => handleAvatarChange(profile.id, e)}
              />
              <IconButton
                icon="camera"
                label="Alterar avatar"
                tone="plain"
                size={30}
                style={{ position: "absolute", bottom: 4, right: 4, background: "var(--surface-inset)" }}
                onClick={(e) => {
                  e.stopPropagation()
                  avatarInputs.current[profile.id]?.click()
                }}
              />
            </div>
            <div style={{ marginTop: 8, fontWeight: 600 }}>{profile.nome}</div>
            <div style={{ fontSize: 13, color: "var(--text-muted)" }}>{profile.email}</div>
            <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
              <Badge tone={planTierTone[profile.plan_tier]}>{planTierLabel[profile.plan_tier]}</Badge>
              <Badge tone={profile.kind === "principal" ? "mint" : "neutral"}>{kindLabel[profile.kind]}</Badge>
            </div>
          </Panel>
        ))}
      </div>

      {profileModalOpen && (
        <ProfileModal
          onClose={() => setProfileModalOpen(false)}
          onCreate={(data) => createProfileMutation.mutate(data)}
          loading={createProfileMutation.isPending}
        />
      )}

      {user?.access !== "ADMIN" ? (
        <div style={{ textAlign: "center", padding: "48px 0", color: "var(--text-muted)" }}>
          Você não tem acesso à administração de contas de login.
        </div>
      ) : (
        <>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
            <div>
              <h1 style={{ font: "var(--text-role-hero)", color: "var(--text-display)", margin: 0 }}>Contas de login</h1>
              <p style={{ color: "var(--text-muted)", marginTop: 4 }}>Administração de acesso.</p>
            </div>
            <Button
              variant="primary"
              icon="plus"
              onClick={() => {
                setEditingUser(null)
                setModalOpen(true)
              }}
            >
              Novo usuário
            </Button>
          </div>

          {error && (
            <div
              style={{
                padding: "12px 16px",
                borderRadius: "var(--r-md)",
                font: "var(--fw-medium) var(--fs-body)/1.3 var(--font-sans)",
                background: "var(--negative-on-glass)",
                color: "var(--negative-ink)",
              }}
            >
              {error.message}
            </div>
          )}

          {isLoading ? (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 256, color: "var(--text-muted)" }}>
              Carregando...
            </div>
          ) : users.length === 0 ? (
            <Panel surface="dark" style={{ padding: "48px 16px", textAlign: "center" }}>
              <p style={{ color: "var(--text-muted)", font: "var(--text-role-body)", margin: 0 }}>Nenhum usuário cadastrado.</p>
            </Panel>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {users.map((u) => (
                <TimelineListCard
                  key={u.id}
                  title={u.username}
                  subtitle={`Criado em ${new Date(u.created_at).toLocaleDateString("pt-BR")}`}
                  thumbnail={
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        justifyContent: "center",
                        width: 40,
                        height: 40,
                        borderRadius: "var(--r-md)",
                        background: "var(--surface-inset)",
                        color: "var(--text-muted)",
                        flexShrink: 0,
                      }}
                    >
                      <Icon name="user" size={18} />
                    </span>
                  }
                  badge={<Badge tone={u.access === "ADMIN" ? "mint" : "neutral"}>{u.access}</Badge>}
                  actions={
                    <>
                      <IconButton
                        icon="pencil"
                        label="Editar"
                        tone="plain"
                        size={30}
                        onClick={() => {
                          setEditingUser(u)
                          setModalOpen(true)
                        }}
                      />
                      <IconButton
                        icon="trash-2"
                        label="Remover"
                        tone="plain"
                        size={30}
                        onClick={() => setDeleteConfirm(u.id)}
                        style={{ color: "var(--red-300)" }}
                      />
                    </>
                  }
                  stats={[
                    { icon: "hash", label: "ID", value: u.id.slice(0, 8) },
                    { icon: "users", label: "Acesso", value: u.access },
                    { icon: "calendar", label: "Criado em", value: new Date(u.created_at).toLocaleDateString("pt-BR") },
                    {
                      icon: "calendar",
                      label: "Atualizado",
                      value: u.updated_at ? new Date(u.updated_at).toLocaleDateString("pt-BR") : "—",
                    },
                  ]}
                  sections={[
                    { label: "Usuário", category: u.id, content: u.username },
                    { label: "Acesso", category: "Permissão", content: <Badge tone={u.access === "ADMIN" ? "mint" : "neutral"}>{u.access}</Badge> },
                    { label: "Criado em", category: "Data", content: new Date(u.created_at).toLocaleString("pt-BR") },
                    {
                      label: "Atualizado em",
                      category: "Data",
                      content: u.updated_at ? new Date(u.updated_at).toLocaleString("pt-BR") : "Nunca atualizado",
                    },
                  ]}
                />
              ))}
            </div>
          )}

          {modalOpen && (
            <UserModal
              user={editingUser}
              onClose={() => {
                setModalOpen(false)
                setEditingUser(null)
              }}
              onCreate={(data) => createMutation.mutate(data)}
              onUpdate={(id, username, access) => updateMutation.mutate({ id, username, access })}
              loading={createMutation.isPending || updateMutation.isPending}
            />
          )}

          <Modal open={deleteConfirm != null} onClose={() => setDeleteConfirm(null)} title="Confirmar remoção" width={400}>
            <p style={{ color: "var(--text-muted)", font: "var(--text-role-body)", marginTop: 0 }}>
              Tem certeza que deseja remover este usuário? Esta ação não pode ser desfeita.
            </p>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <Button variant="ghost" onClick={() => setDeleteConfirm(null)}>
                Cancelar
              </Button>
              <Button
                variant="primary"
                disabled={deleteMutation.isPending}
                onClick={() => deleteConfirm && deleteMutation.mutate(deleteConfirm)}
                style={{ background: "var(--red-300)" }}
              >
                {deleteMutation.isPending ? "Removendo..." : "Remover"}
              </Button>
            </div>
          </Modal>
        </>
      )}
    </div>
  )
}

// ── Modal de criação de perfil ──────────────────────────────────────────────────

interface ProfileModalProps {
  onClose: () => void
  onCreate: (data: { nome: string; email: string; telefone?: string; endereco?: string }) => void
  loading: boolean
}

function ProfileModal({ onClose, onCreate, loading }: ProfileModalProps) {
  const [nome, setNome] = useState("")
  const [email, setEmail] = useState("")
  const [telefone, setTelefone] = useState("")
  const [endereco, setEndereco] = useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onCreate({
      nome,
      email,
      telefone: telefone.trim() || undefined,
      endereco: endereco.trim() || undefined,
    })
  }

  return (
    <Modal open onClose={onClose} title="Novo perfil" width={400}>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <TextInput label="Nome *" value={nome} onChange={(e) => setNome(e.target.value)} required />
        <TextInput label="E-mail *" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <TextInput label="Telefone" value={telefone} onChange={(e) => setTelefone(e.target.value)} />
        <TextInput label="Endereço" value={endereco} onChange={(e) => setEndereco(e.target.value)} />

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" disabled={loading || !nome.trim() || !email.trim()}>
            {loading ? "Salvando..." : "Criar"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

// ── Modal de criação/edição ─────────────────────────────────────────────────────

interface UserModalProps {
  user: AppUser | null
  onClose: () => void
  onCreate: (data: { username: string; password: string; access: UserAccess }) => void
  onUpdate: (id: string, username: string, access: UserAccess) => void
  loading: boolean
}

function UserModal({ user, onClose, onCreate, onUpdate, loading }: UserModalProps) {
  const [username, setUsername] = useState(user?.username ?? "")
  const [password, setPassword] = useState("")
  const [access, setAccess] = useState<UserAccess>(user?.access ?? "USER")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (user) {
      onUpdate(user.id, username, access)
    } else {
      onCreate({ username, password, access })
    }
  }

  return (
    <Modal open onClose={onClose} title={user ? "Editar usuário" : "Novo usuário"} width={400}>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <TextInput
          label="Usuário *"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />

        {!user && (
          <TextInput
            label="Senha inicial *"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="new-password"
          />
        )}

        <Select
          label="Acesso"
          value={access}
          onChange={(e) => setAccess(e.target.value as UserAccess)}
          options={[
            { value: "USER", label: "USER" },
            { value: "ADMIN", label: "ADMIN" },
          ]}
        />

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={loading || !username.trim() || (!user && !password.trim())}
          >
            {loading ? "Salvando..." : user ? "Salvar" : "Criar"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
