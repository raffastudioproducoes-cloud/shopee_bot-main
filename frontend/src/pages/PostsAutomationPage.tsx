import { Icon } from "../components/ui/Icon"
import { Panel } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { Skeleton } from "../components/ui/Skeleton"
import { PlanBadge, UpgradeInfo } from "../components/plans/PlanSummary"
import { usePlanUsage } from "../hooks/usePlanUsage"

/** Vitrine informativa: não existe executor, toggle ou ativação. */
export function PostsAutomationPage() {
  const query = usePlanUsage()
  const plan = query.isError ? undefined : query.data
  return <div className="csp-s-0314">
    <h1 className="csp-s-0315">Automação de posts</h1>
    <Panel padding={24} aria-label="Disponibilidade da automação">
      <Icon name="workflow" size={30} /><PlanBadge />
      {query.isPending && query.fetchStatus === "fetching" ? <Skeleton width="100%" height={52} /> :
        <div role="status">
          <h2>{!plan ? "Disponibilidade do plano indisponível" : plan.automation_entitled
            ? "Em breve — habilitado pelo plano, funcionalidade ainda indisponível"
            : "Automação prevista para o plano Premium"}</h2>
          <p>Esta é uma apresentação do recurso futuro. Nenhuma configuração, coleta ou publicação automática é iniciada aqui.</p>
          {plan && !plan.automation_entitled && <p>Recurso não incluído no seu plano atual. Mesmo no Premium, a automação ainda não está operacional.</p>}
        </div>}
      {query.isError && <Button variant="secondary" onClick={() => void query.refetch()}>Consultar novamente</Button>}
      <UpgradeInfo feature="Automação" />
    </Panel>
  </div>
}
