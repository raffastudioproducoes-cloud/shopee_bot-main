import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import { usersApi, type AppUser, type UserAccess } from "../api/users"
import { Panel } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { IconButton } from "../components/ui/IconButton"
import { Badge } from "../components/ui/Badge"
import { Modal } from "../components/ui/Modal"
import { TextInput } from "../components/ui/TextInput"
import { Select } from "../components/ui/Select"

export function UsersPage() {
  const { user, logout } = useAuthStore()
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<AppUser | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

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

  if (user?.access !== "ADMIN") {
    return (
      <div style={{ textAlign: "center", padding: "48px 0", color: "var(--text-muted)" }}>
        Você não tem acesso a esta página.
      </div>
    )
  }

  if (isLoading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 256, color: "var(--text-muted)" }}>
        Carregando...
      </div>
    )
  }

  const users = data?.data ?? []

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap-column)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ font: "var(--text-role-hero)", color: "var(--text-display)", margin: 0 }}>Usuários</h1>
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

      <Panel surface="dark">
        <table style={{ width: "100%", borderCollapse: "collapse", font: "var(--text-role-body)" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border-hairline)" }}>
              <th
                style={{
                  textAlign: "left",
                  font: "var(--text-role-label)",
                  letterSpacing: "var(--ls-label)",
                  textTransform: "uppercase",
                  color: "var(--text-muted)",
                  padding: "12px 16px",
                }}
              >
                Usuário
              </th>
              <th
                style={{
                  textAlign: "left",
                  font: "var(--text-role-label)",
                  letterSpacing: "var(--ls-label)",
                  textTransform: "uppercase",
                  color: "var(--text-muted)",
                  padding: "12px 16px",
                }}
              >
                Acesso
              </th>
              <th
                style={{
                  textAlign: "right",
                  font: "var(--text-role-label)",
                  letterSpacing: "var(--ls-label)",
                  textTransform: "uppercase",
                  color: "var(--text-muted)",
                  padding: "12px 16px",
                }}
              >
                Ações
              </th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} style={{ borderBottom: "1px solid var(--border-hairline)" }}>
                <td style={{ padding: "12px 16px", color: "var(--text-body)", font: "var(--fw-medium) var(--fs-body)/1.3 var(--font-sans)" }}>
                  {u.username}
                </td>
                <td style={{ padding: "12px 16px" }}>
                  <Badge tone={u.access === "ADMIN" ? "mint" : "neutral"}>{u.access}</Badge>
                </td>
                <td style={{ padding: "12px 16px" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 4 }}>
                    <Button
                      variant="ghost"
                      size="sm"
                      icon="pencil"
                      onClick={() => {
                        setEditingUser(u)
                        setModalOpen(true)
                      }}
                    >
                      Editar
                    </Button>
                    <IconButton
                      icon="trash-2"
                      label="Remover"
                      tone="plain"
                      size={30}
                      onClick={() => setDeleteConfirm(u.id)}
                      style={{ color: "var(--red-300)" }}
                    />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

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
