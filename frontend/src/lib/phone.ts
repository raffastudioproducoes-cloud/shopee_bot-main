/** DDIs usuais na plataforma; o valor persistido é E.164 (+DDI+número). */
export type PhoneCountry = {
  id: string
  name: string
  dial: string
  maxNational: number
  groups: number[]
}

export const PHONE_COUNTRIES: PhoneCountry[] = [
  { id: "BR", name: "Brasil", dial: "55", maxNational: 11, groups: [2, 5, 4] },
  { id: "US", name: "EUA/Canadá", dial: "1", maxNational: 10, groups: [3, 3, 4] },
  { id: "AO", name: "Angola", dial: "244", maxNational: 9, groups: [3, 3, 3] },
  { id: "AR", name: "Argentina", dial: "54", maxNational: 11, groups: [3, 4, 4] },
  { id: "AU", name: "Austrália", dial: "61", maxNational: 9, groups: [3, 3, 3] },
  { id: "AT", name: "Áustria", dial: "43", maxNational: 12, groups: [3, 3, 3, 3] },
  { id: "BE", name: "Bélgica", dial: "32", maxNational: 9, groups: [3, 3, 3] },
  { id: "BO", name: "Bolívia", dial: "591", maxNational: 8, groups: [4, 4] },
  { id: "CV", name: "Cabo Verde", dial: "238", maxNational: 7, groups: [3, 4] },
  { id: "CL", name: "Chile", dial: "56", maxNational: 9, groups: [1, 4, 4] },
  { id: "CN", name: "China", dial: "86", maxNational: 11, groups: [3, 4, 4] },
  { id: "CO", name: "Colômbia", dial: "57", maxNational: 10, groups: [3, 3, 4] },
  { id: "KR", name: "Coreia do Sul", dial: "82", maxNational: 10, groups: [2, 4, 4] },
  { id: "EC", name: "Equador", dial: "593", maxNational: 9, groups: [2, 3, 4] },
  { id: "ES", name: "Espanha", dial: "34", maxNational: 9, groups: [3, 3, 3] },
  { id: "FR", name: "França", dial: "33", maxNational: 9, groups: [1, 2, 2, 2, 2] },
  { id: "DE", name: "Alemanha", dial: "49", maxNational: 13, groups: [3, 3, 4, 3] },
  { id: "GW", name: "Guiné-Bissau", dial: "245", maxNational: 9, groups: [3, 3, 3] },
  { id: "IN", name: "Índia", dial: "91", maxNational: 10, groups: [5, 5] },
  { id: "IE", name: "Irlanda", dial: "353", maxNational: 9, groups: [2, 3, 4] },
  { id: "IT", name: "Itália", dial: "39", maxNational: 12, groups: [3, 3, 3, 3] },
  { id: "JP", name: "Japão", dial: "81", maxNational: 10, groups: [2, 4, 4] },
  { id: "MX", name: "México", dial: "52", maxNational: 10, groups: [2, 4, 4] },
  { id: "MZ", name: "Moçambique", dial: "258", maxNational: 9, groups: [2, 3, 4] },
  { id: "NL", name: "Países Baixos", dial: "31", maxNational: 9, groups: [2, 3, 4] },
  { id: "PY", name: "Paraguai", dial: "595", maxNational: 9, groups: [3, 3, 3] },
  { id: "PE", name: "Peru", dial: "51", maxNational: 9, groups: [3, 3, 3] },
  { id: "PT", name: "Portugal", dial: "351", maxNational: 9, groups: [3, 3, 3] },
  { id: "GB", name: "Reino Unido", dial: "44", maxNational: 10, groups: [4, 3, 3] },
  { id: "ST", name: "São Tomé e Príncipe", dial: "239", maxNational: 7, groups: [3, 4] },
  { id: "CH", name: "Suíça", dial: "41", maxNational: 9, groups: [2, 3, 2, 2] },
  { id: "TL", name: "Timor-Leste", dial: "670", maxNational: 8, groups: [4, 4] },
  { id: "UY", name: "Uruguai", dial: "598", maxNational: 8, groups: [4, 4] },
  { id: "VE", name: "Venezuela", dial: "58", maxNational: 10, groups: [3, 3, 4] },
]

export const DEFAULT_PHONE_COUNTRY = PHONE_COUNTRIES[0]

export const phoneDigits = (value: string) => value.replace(/\D/g, "")

/** Reconhece valores brasileiros legados sem DDI e números novos em E.164. */
export function parseStoredPhone(value: string): { country: PhoneCountry; national: string } {
  const digits = phoneDigits(value)
  if (!value.trim().startsWith("+")) return { country: DEFAULT_PHONE_COUNTRY, national: digits }
  const country = [...PHONE_COUNTRIES].sort((a, b) => b.dial.length - a.dial.length)
    .find(option => digits.startsWith(option.dial)) ?? DEFAULT_PHONE_COUNTRY
  return { country, national: digits.slice(country.dial.length) }
}

export function internationalPhone(country: PhoneCountry, value: string): string {
  const national = phoneDigits(value).slice(0, country.maxNational)
  return national ? `+${country.dial}${national}` : ""
}

export function maskNationalPhone(country: PhoneCountry, value: string, mobile = false): string {
  const digits = phoneDigits(value).slice(0, country.maxNational)
  if (!digits) return ""
  if (country.id === "BR") {
    if (digits.length <= 2) return `(${digits}`
    const local = digits.slice(2)
    const headLength = mobile || local.length > 8 ? 5 : 4
    const head = local.slice(0, headLength)
    const tail = local.slice(headLength)
    return `(${digits.slice(0, 2)}) ${head}${tail ? `-${tail}` : ""}`
  }
  if (country.id === "US") {
    if (digits.length <= 3) return `(${digits}`
    const prefix = digits.slice(3, 6)
    const suffix = digits.slice(6)
    return `(${digits.slice(0, 3)}) ${prefix}${suffix ? `-${suffix}` : ""}`
  }
  const chunks: string[] = []
  let position = 0
  for (const length of country.groups) {
    if (position >= digits.length) break
    chunks.push(digits.slice(position, position + length))
    position += length
  }
  if (position < digits.length) chunks.push(digits.slice(position))
  return chunks.join(" ")
}
