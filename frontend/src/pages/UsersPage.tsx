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
import { SearchField } from "../components/ui/SearchField"
import { Avatar } from "../components/profiles/Avatar"
import { useAuthStore } from "../stores/authStore"
import { PageSkeleton } from "../components/ui/Skeleton"

export default function UsersPage() {
  const navigate = useNavigate()
  const logout = useAuthStore((state) => state.logout)
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<AppUser | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [accessFilter, setAccessFilter] = useState("ALL")

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
  const visibleUsers = users.filter(user => (accessFilter === "ALL" || user.access === accessFilter) && user.username.toLocaleLowerCase("pt-BR").includes(search.trim().toLocaleLowerCase("pt-BR")))
  const summary = [
    { label: "Contas nesta página", value: users.length },
    { label: "Administradores", value: users.filter(user => user.access === "ADMIN").length },
    { label: "Usuários", value: users.filter(user => user.access === "USER").length },
    { label: "Atualizadas", value: users.filter(user => user.updated_at).length },
  ]

  return (
    <div className="csp-s-0390">
      <div className="admin-page-heading">
        <div>
          <h1>Contas de login</h1>
          <p className="csp-s-0391">Contas e permissões de acesso ao aplicativo.</p>
        </div>
        <div className="admin-account-search" role="search" aria-label="Buscar contas nesta página"><SearchField value={search} onChange={event => setSearch(event.target.value)} placeholder="Buscar contas nesta página" width="100%" size={36} /></div>
      </div>

      {error && (
        <div
          role="alert"
          className="csp-s-0392"
        >
          {(error as Error).message}
        </div>
      )}

      <div className="admin-summary" aria-label="Resumo das contas desta página">
        {summary.map(item => <Panel key={item.label} surface="dark"><div className="admin-summary-stat"><strong data-stat-value={true}>{isLoading ? "—" : String(item.value)}</strong><span>{item.label}</span></div></Panel>)}
      </div>

      <div className="admin-user-toolbar">
        <div className="admin-role-filters" role="group" aria-label="Filtrar acesso nesta página">
          {[["ALL", "Todos"], ["ADMIN", "Administradores"], ["USER", "Usuários"]].map(([value, label]) => <button type="button" key={value} aria-pressed={accessFilter === value} onClick={() => setAccessFilter(value)}>{label}</button>)}
        </div>
        <Button variant="primary" icon="plus" onClick={() => { setEditingUser(null); setModalOpen(true) }}>Novo usuário</Button>
      </div>

      {isLoading ? (
        <PageSkeleton variant="list" heading={false} />
      ) : visibleUsers.length === 0 ? (
        <Panel surface="dark" style={{ padding: "48px 16px", textAlign: "center" }}>
          <p className="csp-s-0393">{users.length ? "Nenhuma conta corresponde ao filtro nesta página." : "Nenhum usuário cadastrado."}</p>
        </Panel>
      ) : (
        <div className="admin-user-grid">
          {visibleUsers.map(user => (
            <Panel key={user.id} surface="dark">
              <article className="admin-user-card">
                <div className="admin-user-heading">
                  <div><h2>{user.username}</h2><small>{user.access === "ADMIN" ? "Acesso administrativo" : "Acesso ao aplicativo"}</small></div>
                  <Avatar name={user.username} size={32} />
                </div>
                <p className="admin-user-details">
                  <span>Criado em {new Date(user.created_at).toLocaleDateString("pt-BR")}</span>
                  <span>{user.updated_at ? `Atualizado em ${new Date(user.updated_at).toLocaleDateString("pt-BR")}` : "Sem alterações registradas"}</span>
                </p>
                <div className="admin-user-actions">
                  <Badge tone={user.access === "ADMIN" ? "mint" : "neutral"}>{user.access === "ADMIN" ? "Administrador" : "Usuário"}</Badge>
                  <div>
                    <IconButton icon="pencil" label={`Editar ${user.username}`} tone="plain" onClick={() => { setEditingUser(user); setModalOpen(true) }} />
                    <IconButton icon="trash-2" label={`Remover ${user.username}`} tone="plain" onClick={() => setDeleteConfirm(user.id)} style={{ color: "var(--negative)" }} />
                  </div>
                </div>
              </article>
            </Panel>
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

      <Modal open={deleteConfirm != null} onClose={() => setDeleteConfirm(null)} title="Confirmar remoção" width={400} className="admin-dialog">
        <p className="csp-s-0394">
          Tem certeza que deseja remover este usuário? Esta ação não pode ser desfeita.
        </p>
        <div className="csp-s-0395">
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
    <Modal open onClose={onClose} title={user ? "Editar usuário" : "Novo usuário"} width={400} className="admin-dialog">
      <form onSubmit={handleSubmit} className="csp-s-0396">
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
          <p role="alert" className="csp-s-0397">
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
        <div className="csp-s-0398">
          <Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button type="submit" variant="primary" disabled={loading || !username.trim() || (!user && (!password.trim() || passwordError !== null))}>
            {loading ? "Salvando..." : user ? "Salvar" : "Criar"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
