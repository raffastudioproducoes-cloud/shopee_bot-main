import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { useNavigate } from "@tanstack/react-router"
import { ApiError } from "../lib/api"
import { validatePassword } from "../lib/password"
import { usersApi, type AppUser, type UserAccess } from "../api/users"
import { Panel } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { IconButton } from "../components/ui/IconButton"
import { Badge } from "../components/ui/Badge"
import { Modal } from "../components/ui/Modal"
import { TextInput } from "../components/ui/TextInput"
import { Select } from "../components/ui/Select"
import { TimelineListCard } from "../components/ui/TimelineListCard"
import { Icon } from "../components/ui/Icon"
import { useAuthStore } from "../stores/authStore"
import { PageSkeleton } from "../components/ui/Skeleton"

export default function UsersPage() {
  const navigate = useNavigate()
  const logout = useAuthStore((state) => state.logout)
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<AppUser | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ["users"],
    queryFn: () => usersApi.list(),
  })

  const onAuthError = (err: Error) => {
    if ((err instanceof ApiError && err.status === 401) || err.message.includes("401") || err.message === "Não autenticado") {
      logout()
      navigate({ to: "/login" })
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
    mutationFn: usersApi.delete,
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
          {(error as Error).message}
        </div>
      )}

      {isLoading ? (
        <PageSkeleton variant="list" />
      ) : users.length === 0 ? (
        <Panel surface="dark" style={{ padding: "48px 16px", textAlign: "center" }}>
          <p style={{ color: "var(--text-muted)", font: "var(--text-role-body)", margin: 0 }}>Nenhum usuário cadastrado.</p>
        </Panel>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {users.map((user) => (
            <TimelineListCard
              key={user.id}
              title={user.username}
              subtitle={`Criado em ${new Date(user.created_at).toLocaleDateString("pt-BR")}`}
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
              badge={<Badge tone={user.access === "ADMIN" ? "mint" : "neutral"}>{user.access}</Badge>}
              actions={
                <>
                  <IconButton
                    icon="pencil"
                    label="Editar"
                    tone="plain"
                    size={30}
                    onClick={() => {
                      setEditingUser(user)
                      setModalOpen(true)
                    }}
                  />
                  <IconButton
                    icon="trash-2"
                    label="Remover"
                    tone="plain"
                    size={30}
                    onClick={() => setDeleteConfirm(user.id)}
                    style={{ color: "var(--red-300)" }}
                  />
                </>
              }
              stats={[
                { icon: "hash", label: "ID", value: user.id.slice(0, 8) },
                { icon: "users", label: "Acesso", value: user.access },
                { icon: "calendar", label: "Criado em", value: new Date(user.created_at).toLocaleDateString("pt-BR") },
                {
                  icon: "calendar",
                  label: "Atualizado",
                  value: user.updated_at ? new Date(user.updated_at).toLocaleDateString("pt-BR") : "—",
                },
              ]}
              sections={[
                { label: "Usuário", category: user.id, content: user.username },
                { label: "Acesso", category: "Permissão", content: <Badge tone={user.access === "ADMIN" ? "mint" : "neutral"}>{user.access}</Badge> },
                { label: "Criado em", category: "Data", content: new Date(user.created_at).toLocaleString("pt-BR") },
                {
                  label: "Atualizado em",
                  category: "Data",
                  content: user.updated_at ? new Date(user.updated_at).toLocaleString("pt-BR") : "Nunca atualizado",
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
    </div>
  )
}

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

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    if (user) {
      onUpdate(user.id, username, access)
      return
    }
    if (!validatePassword(password)) onCreate({ username, password, access })
  }

  return (
    <Modal open onClose={onClose} title={user ? "Editar usuário" : "Novo usuário"} width={400}>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <TextInput label="Usuário *" value={username} onChange={(event) => setUsername(event.target.value)} required />
        {!user && (
          <TextInput
            label="Senha inicial *"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
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
          onChange={(event) => setAccess(event.target.value as UserAccess)}
          options={[
            { value: "USER", label: "USER" },
            { value: "ADMIN", label: "ADMIN" },
          ]}
        />
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button type="submit" variant="primary" disabled={loading || !username.trim() || (!user && (!password.trim() || passwordError !== null))}>
            {loading ? "Salvando..." : user ? "Salvar" : "Criar"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
