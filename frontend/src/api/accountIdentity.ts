import { api } from "../lib/api"

export type AccountIdentity = {
  full_name: string | null
  cpf_registered: boolean
  email: string | null
  age: number | null
  mobile_phone: string | null
  recovery_email: string | null
  contact_phone: string | null
  address_line: string | null
  address_number: string | null
  address_complement: string | null
  neighborhood: string | null
  city: string | null
  state: string | null
  cep: string | null
  purchase_readiness: { ready: boolean; missing: string[] }
}

export type AccountIdentitySave = Partial<Omit<AccountIdentity, "cpf_registered" | "email" | "purchase_readiness">> & {
  cpf?: string
}

export const accountIdentityApi = {
  get: () => api.get<AccountIdentity>("/users/me/identity"),
  save: (value: AccountIdentitySave) => api.put<AccountIdentity>("/users/me/identity", value),
  purchaseReadiness: () => api.get<AccountIdentity["purchase_readiness"]>("/users/me/purchase-readiness"),
}
