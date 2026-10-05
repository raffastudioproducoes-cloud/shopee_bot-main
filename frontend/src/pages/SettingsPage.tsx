import { useState } from "react"
import type { FormEvent } from "react"
import { Panel } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { TextInput } from "../components/ui/TextInput"
import { api, ApiError } from "../lib/api"

const MIN_LEN = 8
const MAX_LEN = 72

type Status = { kind: "idle" | "saving" } | { kind: "done" } | { kind: "error"; message: string }

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 403) return "Senha atual incorreta."
    if (err.status === 400 || err.status === 422) return `A nova senha deve ter entre ${MIN_LEN} e ${MAX_LEN} caracteres.`
    if (err.status === 429) return "Muitas tentativas. Aguarde um minuto e tente de novo."
  }
  return "Não foi possível trocar a senha. Tente novamente."
}

export function SettingsPage() {
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [status, setStatus] = useState<Status>({ kind: "idle" })

  const newLenOk = newPassword.length >= MIN_LEN && newPassword.length <= MAX_LEN
  const canSubmit = currentPassword.length > 0 && newLenOk && status.kind !== "saving"

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    setStatus({ kind: "saving" })
    try {
      await api.put("/settings/password", {
        current_password: currentPassword,
        new_password: newPassword,
      })
      setStatus({ kind: "done" })
      setCurrentPassword("")
      setNewPassword("")
    } catch (err) {
      setStatus({ kind: "error", message: errorMessage(err) })
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap-column)" }}>
      <div>
        <h1 style={{ font: "var(--text-role-hero)", color: "var(--text-display)", margin: 0 }}>Configurações</h1>
        <p style={{ color: "var(--text-muted)", marginTop: 4 }}>Ajustes da sua conta.</p>
      </div>
      <Panel padding={24} style={{ maxWidth: 420 }}>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <h2 style={{ font: "var(--text-role-title)", margin: 0 }}>Trocar senha</h2>
          <TextInput
            label="Senha atual"
            type="password"
            autoComplete="current-password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
          />
          <TextInput
            label={`Nova senha (${MIN_LEN} a ${MAX_LEN} caracteres)`}
            type="password"
            autoComplete="new-password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
          <Button type="submit" disabled={!canSubmit} loading={status.kind === "saving"}>
            Salvar nova senha
          </Button>
          {status.kind === "done" && (
            <p role="status" style={{ margin: 0, color: "var(--text-body)" }}>
              Senha atualizada.
            </p>
          )}
          {status.kind === "error" && (
            <p role="alert" style={{ margin: 0, color: "var(--negative-ink)" }}>
              {status.message}
            </p>
          )}
        </form>
      </Panel>
    </div>
  )
}
