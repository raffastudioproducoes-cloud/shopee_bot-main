import { useState } from "react"
import { RegionConsent } from "../components/profiles/RegionConsent"
import { AcquisitionConsent } from "../components/profiles/AcquisitionConsent"
import { BackupSection } from "../components/profiles/BackupSection"
import type { FormEvent } from "react"
import { Panel } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { TextInput } from "../components/ui/TextInput"
import { api, ApiError } from "../lib/api"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import { MIN_PASSWORD_LEN as MIN_LEN, MAX_PASSWORD_BYTES as MAX_BYTES, passwordBytes, validatePassword } from "../lib/password"

type Status = { kind: "idle" | "saving" } | { kind: "done" } | { kind: "error"; message: string }

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 403) return "Senha atual incorreta."
    if (err.status === 400 || err.status === 422) return `A nova senha deve ter ${MIN_LEN} caracteres ou mais e no máximo ${MAX_BYTES} bytes.`
    if (err.status === 429) return "Muitas tentativas. Aguarde um minuto e tente de novo."
  }
  return "Não foi possível trocar a senha. Tente novamente."
}

export function SettingsPage() {
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const { logout } = useAuthStore()
  const [status, setStatus] = useState<Status>({ kind: "idle" })

  const newBytes = passwordBytes(newPassword)
  const newLenOk = validatePassword(newPassword) === null
  const tooManyBytes = newBytes > MAX_BYTES
  const canSubmit = currentPassword.length > 0 && newLenOk && status.kind !== "saving"

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    if (newPassword !== confirmPassword) {
      setStatus({ kind: "error", message: "As senhas não coincidem." })
      return
    }
    setStatus({ kind: "saving" })
    try {
      await api.put("/settings/password", {
        current_password: currentPassword,
        new_password: newPassword,
      })
      setStatus({ kind: "done" })
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        logout()
        router.navigate({ to: "/login" })
        return
      }
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
            label={`Nova senha (mínimo ${MIN_LEN} caracteres, máximo ${MAX_BYTES} bytes)`}
            type="password"
            autoComplete="new-password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
          <TextInput
            label="Confirmar nova senha"
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
          {tooManyBytes && (
            <p role="alert" style={{ margin: 0, color: "var(--negative-on-glass)" }}>
              A senha excede {MAX_BYTES} bytes ({newBytes}). Emojis e acentos ocupam mais de 1 byte; use uma senha mais curta.
            </p>
          )}
          <Button type="submit" disabled={!canSubmit} loading={status.kind === "saving"}>
            Salvar nova senha
          </Button>
          {status.kind === "done" && (
            <p role="status" style={{ margin: 0, color: "var(--text-body)" }}>
              Senha atualizada.
            </p>
          )}
          {status.kind === "error" && (
            <p role="alert" style={{ margin: 0, color: "var(--negative-on-glass)" }}>
              {status.message}
            </p>
          )}
        </form>
      </Panel>
      <section><h2>Privacidade e localização</h2><RegionConsent /><AcquisitionConsent /></section>
      <BackupSection />
    </div>
  )
}
