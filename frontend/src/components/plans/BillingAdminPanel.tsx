import { useMutation, useQuery } from "@tanstack/react-query"
import { billingAdminApi } from "../../api/billingAdmin"
import { Button } from "../ui/Button"
import "./planCheckout.css"

const ok = (value: boolean) => (value ? "Configurado" : "Falta configurar")

export function BillingAdminPanel() {
  const status = useQuery({ queryKey: ["billing-admin-status"], queryFn: billingAdminApi.status, retry: false })
  const register = useMutation({
    mutationFn: billingAdminApi.registerWebhook,
    onSuccess: () => { void status.refetch() },
  })
  const s = status.data
  const hook = s?.webhook
  return (
    <div className="billing-admin" aria-labelledby="billing-admin-title">
      <h3 id="billing-admin-title">Asaas</h3>
      {status.isPending ? <p>Consultando…</p> : status.isError ? <p role="status">Não foi possível consultar.</p> : s && (
        <dl className="billing-admin__grid">
          <dt>Ambiente</dt><dd>{s.environment === "sandbox" ? "Sandbox (testes)" : "Produção"}</dd>
          <dt>Chave de API</dt><dd>{ok(s.api_key_configured)}</dd>
          <dt>Token do webhook</dt><dd>{ok(s.webhook_token_configured)}</dd>
          {s.environment === "sandbox" && <><dt>Contas de teste</dt><dd>{s.sandbox_testers}</dd></>}
          <dt>Webhook no Asaas</dt>
          <dd>{!hook ? "Não registrado" : hook.error ? hook.error
            : hook.interrupted ? "Registrado, mas a fila está pausada" : hook.enabled ? "Registrado e ativo" : "Registrado, desativado"}</dd>
        </dl>
      )}
      <Button disabled={!s?.api_key_configured || !s?.webhook_token_configured || register.isPending}
        onClick={() => register.mutate()}>
        {register.isPending ? "Registrando…" : hook && !hook.error ? "Atualizar webhook no Asaas" : "Registrar webhook no Asaas"}
      </Button>
      {register.isSuccess && <p role="status">Webhook {register.data.updated ? "atualizado" : "registrado"} com {register.data.events} eventos.</p>}
      {register.error && <p className="plan-checkout__error" role="alert">{register.error.message}</p>}
      {s && <p className="plan-checkout__fine">Endereço: {s.webhook_url}</p>}
    </div>
  )
}
