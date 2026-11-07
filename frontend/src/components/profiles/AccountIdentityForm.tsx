import { useEffect, useState } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { useAuthStore } from "../../stores/authStore"
import { accountIdentityApi, type AccountIdentity, type AccountIdentitySave } from "../../api/accountIdentity"
import { validCpf } from "../../lib/cpf"
import { Button } from "../ui/Button"
import { TextInput } from "../ui/TextInput"
import "./accountIdentityForm.css"

type FormFields = {
  full_name: string; cpf: string; age: string; mobile_phone: string
  recovery_email: string; contact_phone: string; address_line: string
  address_number: string; address_complement: string; neighborhood: string
  city: string; state: string; cep: string
}

const empty: FormFields = {
  full_name: "", cpf: "", age: "", mobile_phone: "", recovery_email: "",
  contact_phone: "", address_line: "", address_number: "", address_complement: "",
  neighborhood: "", city: "", state: "", cep: "",
}

function toForm(data: AccountIdentity): FormFields {
  return { ...empty, ...Object.fromEntries(Object.keys(empty).filter(key => key !== "cpf").map(key => [
    key, String(data[key as keyof AccountIdentity] ?? ""),
  ])) } as FormFields
}

export function AccountIdentityForm() {
  const userId = useAuthStore(state => state.user?.id)
  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ["account-identity", userId], queryFn: accountIdentityApi.get, enabled: Boolean(userId),
  })
  const [form, setForm] = useState<FormFields>(empty)
  const [feedback, setFeedback] = useState("")
  useEffect(() => { if (data) setForm(toForm(data)) }, [data])
  const save = useMutation({ mutationFn: accountIdentityApi.save, onSuccess: result => {
    setForm(toForm(result))
    setFeedback("Dados cadastrais salvos com segurança.")
    void refetch()
  } })
  const change = (key: keyof FormFields, value: string) => {
    setFeedback("")
    setForm(prev => ({ ...prev, [key]: value }))
  }
  const cpfProblem = Boolean(form.cpf.trim()) && !validCpf(form.cpf)
  const missingCpf = !data?.cpf_registered && !form.cpf.trim()

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    if (cpfProblem || missingCpf || !form.full_name.trim()) return
    const payload: AccountIdentitySave = {
      full_name: form.full_name.trim(),
      age: form.age ? Number(form.age) : null,
      mobile_phone: form.mobile_phone || null,
      recovery_email: form.recovery_email || null,
      contact_phone: form.contact_phone || null,
      address_line: form.address_line || null,
      address_number: form.address_number || null,
      address_complement: form.address_complement || null,
      neighborhood: form.neighborhood || null,
      city: form.city || null,
      state: form.state || null,
      cep: form.cep || null,
    }
    if (form.cpf.trim()) payload.cpf = form.cpf
    save.mutate(payload)
  }

  return <section className="account-identity" aria-label="Dados cadastrais do titular">
    <div className="account-identity__header">
      <div><h2>Dados cadastrais da conta</h2>
        <p>Informações do titular, editáveis neste perfil principal. Não são compartilhadas com os perfis secundários.</p></div>
      {data && <span className={data.purchase_readiness.ready ? "account-identity__ready" : "account-identity__pending"}>
        {data.purchase_readiness.ready ? "Cadastro pronto para contratar" : "Cadastro para contratação incompleto"}
      </span>}
    </div>
    {isPending && <p role="status">Consultando seus dados cadastrais...</p>}
    {isError && <div role="alert">Não foi possível carregar seus dados. <Button type="button" variant="ghost" onClick={() => void refetch()}>Tentar novamente</Button></div>}
    {data && <form onSubmit={handleSubmit}>
      <div className="account-identity__grid">
        <TextInput label="Nome e sobrenome *" required maxLength={150} autoComplete="name" value={form.full_name} onChange={e => change("full_name", e.target.value)} />
        <div><TextInput label={data.cpf_registered ? "CPF (já cadastrado; preencher somente para alterar)" : "CPF *"}
          required={!data.cpf_registered} maxLength={18} inputMode="numeric" autoComplete="off" value={form.cpf} onChange={e => change("cpf", e.target.value)} placeholder={data.cpf_registered ? "Protegido •••.•••.•••-••" : "000.000.000-00"} />
          {cpfProblem && <small role="alert" className="account-identity__error">CPF inválido.</small>}
        </div>
        <TextInput label="E-mail de acesso * (confirmado no cadastro)" type="email" disabled value={data.email ?? "Não cadastrado"} />
        <TextInput label="Celular * para contratar plano" type="tel" inputMode="tel" autoComplete="tel" maxLength={24} value={form.mobile_phone} onChange={e => change("mobile_phone", e.target.value)} placeholder="(21) 99999-9999" />
        <TextInput label="Idade (opcional)" type="number" min={0} max={120} value={form.age} onChange={e => change("age", e.target.value)} />
        <TextInput label="E-mail alternativo de recuperação (opcional)" type="email" maxLength={254} autoComplete="off" value={form.recovery_email} onChange={e => change("recovery_email", e.target.value)} />
        <TextInput label="Telefone de contato (opcional)" type="tel" maxLength={24} value={form.contact_phone} onChange={e => change("contact_phone", e.target.value)} />
        <TextInput label="CEP (opcional)" inputMode="numeric" maxLength={10} autoComplete="postal-code" value={form.cep} onChange={e => change("cep", e.target.value)} />
        <TextInput label="Endereço — rua/avenida (opcional)" autoComplete="address-line1" maxLength={180} value={form.address_line} onChange={e => change("address_line", e.target.value)} />
        <TextInput label="Número (opcional)" maxLength={25} value={form.address_number} onChange={e => change("address_number", e.target.value)} />
        <TextInput label="Complemento (opcional)" autoComplete="address-line2" maxLength={120} value={form.address_complement} onChange={e => change("address_complement", e.target.value)} />
        <TextInput label="Bairro (opcional)" maxLength={100} value={form.neighborhood} onChange={e => change("neighborhood", e.target.value)} />
        <TextInput label="Cidade (opcional)" maxLength={100} autoComplete="address-level2" value={form.city} onChange={e => change("city", e.target.value)} />
        <TextInput label="Estado — UF (opcional)" maxLength={2} autoComplete="address-level1" value={form.state} onChange={e => change("state", e.target.value)} />
      </div>
      <p className="account-identity__note">* Nome, CPF e e-mail são exigidos no cadastro. O celular é necessário para contratar. Os demais campos são opcionais. O e-mail alternativo é só contato por enquanto: a recuperação da senha continua pelo e-mail principal confirmado, até a verificação do alternativo. Nenhuma cobrança ocorre aqui.</p>
      {data.purchase_readiness.missing.length > 0 && <p role="status" className="account-identity__pending">Para contratar futuramente: {data.purchase_readiness.missing.join(", ")}.</p>}
      {save.isError && <p role="alert" className="account-identity__error">{save.error instanceof Error ? save.error.message : "Não foi possível salvar."}</p>}
      {feedback && <p role="status" className="account-identity__ready">{feedback}</p>}
      <div className="account-identity__actions"><Button type="submit" variant="primary" disabled={save.isPending || cpfProblem || missingCpf}>
        {save.isPending ? "Salvando..." : "Salvar dados cadastrais"}
      </Button></div>
    </form>}
  </section>
}
