import { useRef, useState } from "react"
import { useNavigate } from "@tanstack/react-router"
import { useAuthStore } from "../../stores/authStore"
import { usersApi, type BackupData } from "../../api/users"
import { ApiError } from "../../lib/api"
import { Panel } from "../ui/Panel"
import { Button } from "../ui/Button"
import { Modal } from "../ui/Modal"
import { TextInput } from "../ui/TextInput"
import { StatusMessage } from "../StatusMessage"
import { ConfirmModal } from "./ConfirmModal"

/** Card "Backup e dados": exportar, restaurar e excluir a própria conta. */
export function BackupSection() {
  const navigate = useNavigate()
  const { logout } = useAuthStore()
  const restoreInputRef = useRef<HTMLInputElement>(null)
  const [feedback, setFeedback] = useState<{ kind: "error" | "success"; text: string } | null>(null)
  const [pendingRestore, setPendingRestore] = useState<File | null>(null)
  const [restoring, setRestoring] = useState(false)
  const [deleteAccountOpen, setDeleteAccountOpen] = useState(false)

  const handleExportBackup = async () => {
    try {
      const backup = await usersApi.exportBackup()
      const blob = new Blob([JSON.stringify(backup, null, 2)], { type: "application/json" })
      const url = URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = url
      link.download = `backup-${backup.exported_at.slice(0, 10)}.json`
      link.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setFeedback({ kind: "error", text: err instanceof ApiError ? err.message : "Não foi possível exportar o backup." })
    }
  }

  const handleRestoreFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ""
    if (file) setPendingRestore(file)
  }

  const confirmRestore = async () => {
    if (!pendingRestore) return
    setRestoring(true)
    try {
      const data = JSON.parse(await pendingRestore.text()) as BackupData
      const result = await usersApi.restoreBackup(data)
      setFeedback({ kind: "success", text: result.msg })
    } catch (err) {
      setFeedback({ kind: "error", text: err instanceof ApiError ? err.message : "Arquivo de backup inválido ou corrompido." })
    } finally {
      setRestoring(false)
      setPendingRestore(null)
    }
  }

  return (
    <section aria-labelledby="backup-title" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div>
        <h2 id="backup-title" style={{ font: "var(--text-role-hero)", color: "var(--text-display)", margin: 0 }}>Backup e dados</h2>
        <p style={{ color: "var(--text-muted)", marginTop: 4 }}>Baixe uma cópia dos seus dados, restaure um arquivo ou exclua sua conta.</p>
      </div>

      {feedback && (
        <StatusMessage kind={feedback.kind} onDismiss={() => setFeedback(null)}>
          {feedback.text}
        </StatusMessage>
      )}

      <Panel surface="dark" style={{ padding: 16, display: "flex", gap: 12, flexWrap: "wrap" }}>
        <Button variant="secondary" icon="download" onClick={handleExportBackup}>
          Exportar backup
        </Button>
        <Button variant="secondary" icon="upload" onClick={() => restoreInputRef.current?.click()}>
          Restaurar backup
        </Button>
        <input ref={restoreInputRef} type="file" accept="application/json" onChange={handleRestoreFileChange} style={{ display: "none" }} />
        <Button variant="secondary" icon="trash-2" onClick={() => setDeleteAccountOpen(true)} style={{ color: "var(--red-300)" }}>
          Excluir minha conta e dados
        </Button>
        <p style={{ flexBasis: "100%", margin: 0, color: "var(--text-muted)", fontSize: 13 }}>
          Restaurar adiciona produtos, listas e posts do arquivo à conta, sem apagar nada. Excluir a conta apaga
          permanentemente credenciais, produtos, listas e posts (pede sua senha).
        </p>
      </Panel>

      {pendingRestore && (
        <ConfirmModal
          title="Restaurar backup"
          confirmLabel="Restaurar"
          busyLabel="Restaurando..."
          loading={restoring}
          onConfirm={confirmRestore}
          onClose={() => setPendingRestore(null)}
        >
          Restaurar este backup vai adicionar os produtos, listas e posts do arquivo à sua conta (não substitui nem apaga nada existente). Continuar?
        </ConfirmModal>
      )}

      {deleteAccountOpen && (
        <DeleteAccountModal
          onClose={() => setDeleteAccountOpen(false)}
          onDeleted={() => {
            logout()
            navigate({ to: "/login" })
          }}
        />
      )}
    </section>
  )
}

// ── Modal de autoexclusão de conta (LGPD/direito ao esquecimento) ──────────────

interface DeleteAccountModalProps {
  onClose: () => void
  onDeleted: () => void
}

function DeleteAccountModal({ onClose, onDeleted }: DeleteAccountModalProps) {
  const [password, setPassword] = useState("")
  const [confirmed, setConfirmed] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await usersApi.deleteSelf(password)
      onDeleted()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Não foi possível excluir a conta.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal open onClose={onClose} title="Excluir minha conta" width={420}>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <p style={{ color: "var(--negative-ink)", font: "var(--text-role-body)", margin: 0 }}>
          Esta ação é irreversível: sua conta e todos os dados associados (credenciais, produtos,
          listas, posts) serão apagados permanentemente.
        </p>

        <TextInput
          label="Confirme sua senha atual *"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
        />

        <label style={{ display: "flex", alignItems: "center", gap: 8, font: "var(--text-role-body)", color: "var(--text-muted)" }}>
          <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />
          Tenho certeza que quero excluir minha conta e meus dados permanentemente.
        </label>

        {error && <p role="alert" style={{ color: "var(--negative-ink)", margin: 0 }}>{error}</p>}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={loading || !password.trim() || !confirmed}
            style={{ background: "var(--red-300)" }}
          >
            {loading ? "Excluindo..." : "Excluir conta"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
