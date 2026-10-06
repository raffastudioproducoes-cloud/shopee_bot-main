export const MIN_PASSWORD_LEN = 8
export const MAX_PASSWORD_BYTES = 72 // bcrypt trunca em 72 bytes UTF-8, não em caracteres

export function passwordBytes(pw: string): number {
  return new TextEncoder().encode(pw).length
}

/** Espelha o backend: mínimo 8 code points (len() do Python), máximo 72 bytes UTF-8. */
export function validatePassword(pw: string): string | null {
  if (Array.from(pw).length < MIN_PASSWORD_LEN) return `A senha deve ter ao menos ${MIN_PASSWORD_LEN} caracteres.`
  const bytes = passwordBytes(pw)
  if (bytes > MAX_PASSWORD_BYTES) {
    return `A senha excede ${MAX_PASSWORD_BYTES} bytes (${bytes}). Emojis e acentos ocupam mais de 1 byte; use uma senha mais curta.`
  }
  return null
}
