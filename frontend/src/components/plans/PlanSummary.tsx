import { useId, useState } from "react"
import { Badge } from "../ui/Badge"
import { Button } from "../ui/Button"
import { Panel } from "../ui/Panel"
import { Skeleton } from "../ui/Skeleton"
import { usePlanUsage } from "../../hooks/usePlanUsage"
import { accountPlanLabel, resourceAtLimit, usageLabel } from "../../lib/planPresentation"
import type { PlanResource } from "../../api/planUsage"
import "./planSummary.css"

const labels: Record<PlanResource, string> = {
  products: "Produtos · conta", lists: "Listas · perfil", profiles: "Perfis · conta",
  immediate: "Enviar agora · perfil / hora", recurring: "Horários recorrentes · perfil / dia",
}

export function UpgradeInfo({ feature }: { feature?: string }) {
  const [open, setOpen] = useState(false)
  const id = useId()
  return <div className="plan-upgrade">
    <button type="button" className="plan-info-button" aria-expanded={open} aria-controls={id}
      onClick={() => setOpen((value) => !value)}>Conhecer planos e upgrade</button>
    {open && <div id={id} className="plan-info" role="status">
      <strong>{feature ? `${feature}: consulte as opções do plano` : "Planos Free, Pro e Premium"}</strong>
      <p>Contratação e alteração de plano ainda não estão disponíveis. Não há cobrança ou checkout nesta tela.</p>
      <p>Campanhas são previstas para Pro e Premium; automação é prevista para Premium.
        Ativação de campanhas e automação ainda estão indisponíveis em todos os planos.
        Limites das redes, conexão e segurança continuam obrigatórios.</p>
    </div>}
  </div>
}

export function PlanBadge() {
  const query = usePlanUsage()
  return <Badge tone={query.data?.is_admin || query.data?.plan_tier === "premium" ? "mint" : "neutral"}>
    {accountPlanLabel(query.isError ? undefined : query.data)}
  </Badge>
}

export function PlanSummary({ resources = ["products", "lists", "profiles", "immediate", "recurring"] }: {
  resources?: PlanResource[]
}) {
  const query = usePlanUsage()
  const plan = query.isError ? undefined : query.data
  return <Panel className="plan-summary" padding={16} aria-label="Plano e limites da conta">
    <div className="plan-summary-heading"><PlanBadge /><span>Plano da conta · listas e publicações isoladas por perfil</span></div>
    {query.isPending && query.fetchStatus === "fetching"
      ? <div aria-busy="true"><Skeleton width="100%" height={52} /></div>
      : <dl className="plan-usage-grid">
        {resources.map((key) => <div key={key}>
          <dt>{labels[key]}</dt><dd>{usageLabel(plan?.resources[key])}</dd>
          {resourceAtLimit(plan?.resources[key]) && <p className="plan-limit" role="status">
            Limite atingido. Novos cadastros bloqueados; consulta e exclusão continuam disponíveis.
          </p>}
        </div>)}
      </dl>}
    {query.isError && <div role="status">Não foi possível consultar o plano.
      <Button variant="ghost" onClick={() => void query.refetch()}>Tentar novamente</Button></div>}
    {resources.some((key) => key === "immediate" || key === "recurring") &&
      <p>Consumo de envios e recorrência indisponível nesta tela. Cada rede conta uma publicação; a API valida a cota ao criar.</p>}
    {plan?.is_admin && <p>Sem cotas comerciais. Segurança, capacidade física e regras das redes permanecem.</p>}
    <UpgradeInfo />
  </Panel>
}
