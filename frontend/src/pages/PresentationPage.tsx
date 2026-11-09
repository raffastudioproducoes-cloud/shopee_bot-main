import { lazy, Suspense } from "react"

// A apresentação usa animações por scroll (biblioteca `motion`). Carregada sob demanda: quem
// entra direto no painel não baixa esse código. A rota "/" continua apontando para este componente.
const PresentationBody = lazy(() => import("./presentation/PresentationBody"))

export default function PresentationPage() {
  return (
    <Suspense fallback={<div role="status" aria-label="Carregando" className="min-h-screen bg-[#0b1020]" />}>
      <PresentationBody />
    </Suspense>
  )
}
