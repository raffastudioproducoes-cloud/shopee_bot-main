import { Button } from "../ui/Button"
import { Select } from "../ui/Select"

/** A mesma seleção de tom e ação de IA de Criar Post e Personalizar Produto. */
export const AI_COPY_PERSONAS = [
  { value: "casual", label: "Casual" },
  { value: "profissional", label: "Profissional" },
  { value: "divertido", label: "Divertido" },
  { value: "persuasivo", label: "Persuasivo" },
]

interface AiCopyControlsProps {
  persona: string
  onPersonaChange: (value: string) => void
  onGenerate: () => void
  hasAiKey: boolean
  disabled?: boolean
  isPending?: boolean
  missingKeyLabel?: string
}

/** Reutilizado sem armazenar nem expor a chave de IA no navegador. */
export function AiCopyControls({
  persona, onPersonaChange, onGenerate, hasAiKey,
  disabled = false, isPending = false, missingKeyLabel = "IA temporariamente indisponível",
}: AiCopyControlsProps) {
  return (
    <>
      <Select
        label="Persona da IA"
        value={persona}
        onChange={(event) => onPersonaChange(event.target.value)}
        options={AI_COPY_PERSONAS}
        width={200}
      />
      {hasAiKey ? (
        <Button
          type="button"
          variant="secondary"
          icon={isPending ? "loader-2" : "sparkles"}
          disabled={disabled || isPending}
          onClick={onGenerate}
        >
          {isPending ? "Gerando..." : "Gerar texto com IA"}
        </Button>
      ) : (
        <Button
          type="button"
          variant="secondary"
          icon="sparkles"
          disabled
        >
          {missingKeyLabel}
        </Button>
      )}
    </>
  )
}
