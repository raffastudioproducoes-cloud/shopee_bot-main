/** Validação local de conveniência. O servidor repete a validação obrigatoriamente. */
export function validCpf(input: string): boolean {
  const digits = input.replace(/\D/g, "")
  if (digits.length !== 11 || /^(\d)\1+$/.test(digits)) return false
  for (const length of [9, 10]) {
    const weighted = [...digits.slice(0, length)].reduce((sum, digit, i) => sum + Number(digit) * (length + 1 - i), 0)
    const check = (weighted * 10) % 11
    if ((check > 9 ? 0 : check) !== Number(digits[length])) return false
  }
  return true
}
