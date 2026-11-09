import { Icon } from "../ui/Icon"
import { formatElapsed, useElapsedSeconds } from "../../hooks/useElapsedSeconds"
import "./activationProgress.css"

export type ActivationPhase = "idle" | "saving" | "activating" | "success" | "error"

type StepState = "pending" | "active" | "done" | "error"

/**
 * Andamento da ativação. O servidor não informa a etapa em curso: só as etapas
 * do cliente (registrar e ativar) são reais; as verificações do servidor são
 * exibidas como um bloco único e a barra é indeterminada, sem % fictícia.
 */
export function ActivationProgress({ phase, errorMessage }: {
  phase: ActivationPhase
  errorMessage?: string | null
}) {
  const running = phase === "saving" || phase === "activating"
  const elapsed = useElapsedSeconds(running)
  const [saveStep, serverStep, doneStep]: StepState[] =
    phase === "saving" ? ["active", "pending", "pending"]
      : phase === "activating" ? ["done", "active", "pending"]
        : phase === "success" ? ["done", "done", "done"]
          : phase === "error" ? ["done", "error", "pending"]
            : ["pending", "pending", "pending"]
  if (phase === "idle") return null
  const title = phase === "success" ? "Campanha ativada com sucesso"
    : phase === "error" ? "A ativação não foi concluída"
      : phase === "saving" ? "Registrando a configuração…" : "Ativando no servidor…"
  const hint = running
    ? elapsed >= 60 ? "Está demorando mais que o normal. Continue nesta página: o limite de espera é de 90 segundos."
      : elapsed >= 15 ? "Campanhas com muitas postagens e mídias levam mais tempo. Não feche a página."
        : null
    : null
  return (
    <div className={`activation-progress activation-progress--${phase}`}>
      <div className="activation-progress__head">
        <strong role="status" aria-live="polite">{title}</strong>
        {(running || phase === "success") &&
          <span className="activation-progress__time" aria-live="off">
            Tempo: <b>{formatElapsed(elapsed)}</b>
          </span>}
      </div>
      <div className="activation-progress__track" role="progressbar"
        aria-label="Andamento da ativação da campanha"
        aria-valuemin={0} aria-valuemax={100}
        aria-valuenow={phase === "success" ? 100 : undefined}
        aria-busy={running}>
        <span className={phase === "success" ? "is-full" : phase === "error" ? "is-error" : "is-running"} />
      </div>
      <ol className="activation-progress__steps">
        <Step state={saveStep} label="Configuração registrada (revisão e idempotência)" />
        <Step state={serverStep}
          label="Servidor: validando cotas, retendo arquivos no armazenamento privado e confirmando permissões OAuth" />
        <Step state={doneStep} label="Campanha reservada e pronta para executar nos horários previstos" />
      </ol>
      {hint && <p className="activation-progress__hint">{hint}</p>}
      {phase === "error" && errorMessage &&
        <p className="activation-progress__error" role="alert">
          {errorMessage} O rascunho continua salvo e pode ser ativado novamente.
        </p>}
    </div>
  )
}

function Step({ state, label }: { state: StepState; label: string }) {
  return (
    <li className={`is-${state}`}>
      <span className="activation-progress__icon" aria-hidden="true">
        {state === "done" ? <Icon name="check-circle-2" size={16} />
          : state === "active" ? <i className="activation-progress__pulse" />
            : state === "error" ? <Icon name="x-circle" size={16} />
              : <i />}
      </span>
      <span>{label}</span>
    </li>
  )
}
