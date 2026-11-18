import { useMutation, useQuery } from "@tanstack/react-query"
import { billingAdminApi, type BillingAdminStatus } from "../../api/billingAdmin"
import { Button } from "../ui/Button"
import "./planCheckout.css"

const ok = (value: boolean) => (value ? "Configurado" : "Falta configurar")
const ENV_NAMES = { sandbox: "Sandbox (testes)", production: "Produção" } as const

/** Variáveis do Render que faltam para registrar o webhook (só nomes, nunca valores). */
function missingWebhookVars(s: Pick<BillingAdminStatus, "api_key_configured" | "webhook_token_configured">): string[] {
  return [
    ...(s.api_key_configured ? [] : ["ASAAS_API_KEY"]),
    ...(s.webhook_token_configured ? [] : ["ASAAS_WEBHOOK_TOKEN"]),
  ]
}

export function BillingAdminPanel() {
  const status = useQuery({ queryKey: ["billing-admin-status"], queryFn: billingAdminApi.status, retry: false })
  const register = useMutation({
    mutationFn: billingAdminApi.registerWebhook,
    onSuccess: () => { void status.refetch() },
  })
  const s = status.data
  const hook = s?.webhook
  const missing = s ? missingWebhookVars(s) : []
  return (
    <div className="billing-admin" aria-labelledby="billing-admin-title">
      <h3 id="billing-admin-title">Asaas</h3>
      {status.isPending ? <p>Consultando…</p> : status.isError ? <p role="status">Não foi possível consultar.</p> : s && (
        <dl className="billing-admin__grid">
          <dt>Ambiente</dt><dd>{s.environment ? ENV_NAMES[s.environment] : "Não configurado"}</dd>
          <dt>Chave de API</dt><dd>{ok(s.api_key_configured)}</dd>
          <dt>Token do webhook</dt><dd>{ok(s.webhook_token_configured)}</dd>
          {s.environment === "sandbox" && <><dt>Contas de teste</dt><dd>{s.sandbox_testers}</dd></>}
          <dt>Webhook no Asaas</dt>
          <dd>{!hook ? "Não registrado" : hook.error ? hook.error
            : hook.interrupted ? "Registrado, mas a fila está pausada" : hook.enabled ? "Registrado e ativo" : "Registrado, desativado"}</dd>
        </dl>
      )}
      {s?.environment_mismatch && s.key_environment && <p className="plan-checkout__error" role="alert">
        A chave de API é de {ENV_NAMES[s.key_environment]}, mas ASAAS_API_URL aponta para {ENV_NAMES[s.api_url_environment]}.
        Corrija no Render: a contratação fica fechada até lá.</p>}
      <Button disabled={missing.length > 0 || register.isPending}
        onClick={() => register.mutate()}>
        {register.isPending ? "Registrando…" : hook && !hook.error ? "Atualizar webhook no Asaas" : "Registrar webhook no Asaas"}
      </Button>
      {s && missing.length > 0 && <p className="plan-checkout__note" role="status">
        Defina ASAAS_API_KEY e ASAAS_WEBHOOK_TOKEN no Render para habilitar o webhook. Falta: {missing.join(" e ")}.
        {" "}ASAAS_API_URL aponta para {ENV_NAMES[s.api_url_environment]}
        {s.api_url_environment === "sandbox" ? " (padrão quando a variável não está definida; em produção use https://api.asaas.com/v3)." : "."}</p>}
      {register.isSuccess && <p role="status">Webhook {register.data.updated ? "atualizado" : "registrado"} com {register.data.events} eventos.</p>}
      {register.error && <p className="plan-checkout__error" role="alert">{register.error.message}</p>}
      {s && <p className="plan-checkout__fine">Endereço: {s.webhook_url}</p>}
    </div>
  )
}
