import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import { ApiError } from "../lib/api"
import { validatePassword } from "../lib/password"
import { usersApi, type AppUser, type UserAccess } from "../api/users"
import { profilesApi, type Profile, type ProfileInput } from "../api/profiles"
import { PROFILE_LIMIT, useActivateProfile, useProfiles } from "../hooks/useProfiles"
import { Panel } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { IconButton } from "../components/ui/IconButton"
import { Badge } from "../components/ui/Badge"
import { Modal } from "../components/ui/Modal"
import { TextInput } from "../components/ui/TextInput"
import { Select } from "../components/ui/Select"
import { TimelineListCard } from "../components/ui/TimelineListCard"
import { Icon } from "../components/ui/Icon"
import { StatusMessage } from "../components/StatusMessage"
import { ProfileCard } from "../components/profiles/ProfileCard"
import { ProfileFormModal } from "../components/profiles/ProfileFormModal"
import { ConfirmModal } from "../components/profiles/ConfirmModal"
import { BackupSection } from "../components/profiles/BackupSection"

const errMsg = (err: unknown, fallback: string) => (err instanceof Error && err.message ? err.message : fallback)

export function ProfilesPage() {
  const { user, logout } = useAuthStore()
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<AppUser | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const [profileModalOpen, setProfileModalOpen] = useState(false)
  const [editingProfile, setEditingProfile] = useState<Profile | null>(null)
  const [deletingProfile, setDeletingProfile] = useState<Profile | null>(null)
  const [feedback, setFeedback] = useState<{ kind: "error" | "success"; text: string } | null>(null)

  const { profiles, activeProfile, isLoading: profilesLoading, isError: profilesError, refetch: refetchProfiles } = useProfiles()
  const atLimit = profiles.length >= PROFILE_LIMIT

  const invalidateProfiles = () => queryClient.invalidateQueries({ queryKey: ["profiles"] })

  const createProfileMutation = useMutation({
    mutationFn: profilesApi.create,
    onSuccess: () => {
      invalidateProfiles()
      setProfileModalOpen(false)
      setFeedback({ kind: "success", text: "Perfil criado." })
    },
  })

  const updateProfileMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: ProfileInput }) => profilesApi.update(id, data),
    onSuccess: () => {
      invalidateProfiles()
      setEditingProfile(null)
      setFeedback({ kind: "success", text: "Perfil atualizado." })
    },
  })

  const deleteProfileMutation = useMutation({
    mutationFn: (id: string) => profilesApi.delete(id),
    onSuccess: () => {
      invalidateProfiles()
      setDeletingProfile(null)
      setFeedback({ kind: "success", text: "Perfil excluído." })
    },
  })

  const activateMutation = useActivateProfile()

  const handleActivate = (profile: Profile) => {
    setFeedback(null)
    activateMutation.mutate(profile.id, {
      onSuccess: () => setFeedback({ kind: "success", text: `Perfil ${profile.nome} ativado.` }),
      onError: (err) => setFeedback({ kind: "error", text: errMsg(err, "Não foi possível ativar o perfil.") }),
    })
  }

  const uploadAvatarMutation = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => profilesApi.uploadAvatar(id, file),
    onSuccess: () => {
      invalidateProfiles()
      setFeedback({ kind: "success", text: "Foto atualizada." })
    },
    onError: (err) => setFeedback({ kind: "error", text: errMsg(err, "Não foi possível enviar a foto.") }),
  })

  const { data, isLoading, error } = useQuery({
    queryKey: ["users"],
    queryFn: () => usersApi.list(),
    enabled: user?.access === "ADMIN",
  })

  const onAuthError = (err: Error) => {
    if ((err instanceof ApiError && err.status === 401) || err.message.includes("401") || err.message === "Não autenticado") {
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
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
          <Button
            variant="primary"
            icon="plus"
            disabled={atLimit}
            title={atLimit ? `Limite de ${PROFILE_LIMIT} perfis atingido` : undefined}
            onClick={() => {
              createProfileMutation.reset()
              setProfileModalOpen(true)
            }}
          >
            Novo perfil
          </Button>
          {atLimit && (
            <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
              Limite de {PROFILE_LIMIT} perfis atingido. Exclua um perfil secundário para criar outro.
            </span>
          )}
        </div>
      </div>

      {feedback && (
        <StatusMessage kind={feedback.kind} onDismiss={() => setFeedback(null)}>
          {feedback.text}
        </StatusMessage>
      )}

      {profilesLoading ? (
        <div
          role="status"
          aria-label="Carregando perfis"
          style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 16 }}
        >
          {[0, 1, 2].map((i) => (
            <Panel key={i} style={{ height: 240, opacity: 0.5 }} />
          ))}
        </div>
      ) : profilesError ? (
        <Panel style={{ padding: 24, display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <p role="alert" style={{ margin: 0, color: "var(--negative-on-glass)" }}>
            Não foi possível carregar os perfis.
          </p>
          <Button variant="secondary" onClick={() => refetchProfiles()}>
            Tentar novamente
          </Button>
        </Panel>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 16 }}>
          {profiles.map((profile) => (
            <ProfileCard
              key={profile.id}
              profile={profile}
              active={profile.id === activeProfile?.id}
              activating={activateMutation.isPending && activateMutation.variables === profile.id}
              onActivate={() => handleActivate(profile)}
              onEdit={() => {
                updateProfileMutation.reset()
                setEditingProfile(profile)
              }}
              onDelete={() => {
                deleteProfileMutation.reset()
                setDeletingProfile(profile)
              }}
              onAvatarFile={(file) => uploadAvatarMutation.mutate({ id: profile.id, file })}
            />
          ))}
        </div>
      )}

      {profileModalOpen && (
        <ProfileFormModal
          onClose={() => setProfileModalOpen(false)}
          onSubmit={(data) => createProfileMutation.mutate(data)}
          loading={createProfileMutation.isPending}
          error={createProfileMutation.isError ? errMsg(createProfileMutation.error, "Não foi possível criar o perfil.") : null}
        />
      )}

      {editingProfile && (
        <ProfileFormModal
          profile={editingProfile}
          onClose={() => setEditingProfile(null)}
          onSubmit={(data) => updateProfileMutation.mutate({ id: editingProfile.id, data })}
          loading={updateProfileMutation.isPending}
          error={updateProfileMutation.isError ? errMsg(updateProfileMutation.error, "Não foi possível salvar o perfil.") : null}
        />
      )}

      {deletingProfile && (
        <ConfirmModal
          title="Excluir perfil"
          confirmLabel="Excluir"
          busyLabel="Excluindo..."
          loading={deleteProfileMutation.isPending}
          error={deleteProfileMutation.isError ? errMsg(deleteProfileMutation.error, "Não foi possível excluir o perfil.") : null}
          onConfirm={() => deleteProfileMutation.mutate(deletingProfile.id)}
          onClose={() => setDeletingProfile(null)}
        >
          Excluir o perfil <strong>{deletingProfile.nome}</strong>? Esta ação não pode ser desfeita.
        </ConfirmModal>
      )}

      <BackupSection />

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
              role="alert"
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
              apiError={createMutation.error instanceof ApiError && createMutation.error.status !== 401 ? createMutation.error.message : null}
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

// ── Modal de criação/edição ─────────────────────────────────────────────────────

interface UserModalProps {
  user: AppUser | null
  onClose: () => void
  onCreate: (data: { username: string; password: string; access: UserAccess }) => void
  onUpdate: (id: string, username: string, access: UserAccess) => void
  loading: boolean
  apiError?: string | null
}

function UserModal({ user, onClose, onCreate, onUpdate, loading, apiError }: UserModalProps) {
  const [username, setUsername] = useState(user?.username ?? "")
  const [password, setPassword] = useState("")
  const [access, setAccess] = useState<UserAccess>(user?.access ?? "USER")

  const passwordError = !user && password ? validatePassword(password) : null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (user) {
      onUpdate(user.id, username, access)
    } else {
      if (validatePassword(password)) return
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

        {(passwordError || apiError) && (
          <p role="alert" style={{ margin: 0, color: "var(--negative-on-glass)" }}>
            {passwordError ?? apiError}
          </p>
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
            disabled={loading || !username.trim() || (!user && (!password.trim() || passwordError !== null))}
          >
            {loading ? "Salvando..." : user ? "Salvar" : "Criar"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
