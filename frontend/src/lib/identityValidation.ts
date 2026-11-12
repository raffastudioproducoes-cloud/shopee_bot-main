import { validCpf } from "./cpf"
import { MIN_PASSWORD_LEN, validatePassword } from "./password"

/** Espelha o servidor (api/routers/supabase_auth.py): e-mail com domínio e TLD de letras. */
const EMAIL_RE = /^[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)*\.[A-Za-z]{2,}$/

export function validEmail(value: string): boolean {
  const email = value.trim()
  return email.length <= 254 && EMAIL_RE.test(email)
}

/** Mesmas regras do servidor: nome e sobrenome com 2+ letras, sem números. */
export function fullNameProblem(value: string): string | null {
  const name = value.trim().replace(/\s+/g, " ")
  if (!name) return null
  if (/\d/.test(name)) return "O nome não pode conter números."
  const parts = name.split(" ")
  if (name.length < 5 || parts.length < 2 || parts.some((p) => p.length < 2)) return "Informe nome e sobrenome completos."
  return null
}

export function cpfProblem(value: string): string | null {
  const digits = value.replace(/\D/g, "")
  if (!digits) return null
  if (digits.length < 11) return `Faltam ${11 - digits.length} dígito(s) no CPF.`
  return validCpf(value) ? null : "CPF inválido: confira os números."
}

export function emailProblem(value: string): string | null {
  if (!value.trim()) return null
  return validEmail(value) ? null : "Informe um e-mail válido, como nome@exemplo.com."
}

export function passwordProblem(value: string): string | null {
  if (!value) return null
  return validatePassword(value)
}

export const PASSWORD_HINT = `Mínimo de ${MIN_PASSWORD_LEN} caracteres.`
