import { MotionConfig, motion, useScroll, useSpring } from "motion/react"
import { ArrowUpRight } from "lucide-react"
import { useEffect } from "react"
import { Hero } from "./Hero"
import { OfferSection } from "./Offer"
import { PlansScene } from "./Plans"
import { BacklogScene, ChallengeScene, ProductScene, TurnScene } from "./Scenes"
import { BenefitsSection, FinalSection, FutureSection, TrustSection } from "./Sections"
import { LoginLink } from "./shared"
import "./presentation.css"

const TITLE = "Auto Orbital — Sua operação de afiliados em uma nova órbita"

export default function PresentationBody() {
  const { scrollYProgress } = useScroll()
  const progress = useSpring(scrollYProgress, { stiffness: 120, damping: 30 })

  useEffect(() => {
    const previous = document.title
    document.title = TITLE
    const meta = document.createElement("meta")
    meta.name = "robots"
    meta.content = "noindex, nofollow"
    meta.dataset.autoOrbitalPreview = "true"
    document.head.appendChild(meta)
    return () => {
      document.title = previous
      meta.remove()
    }
  }, [])

  return (
    <MotionConfig reducedMotion="user">
      <div className="ao-pres" id="topo">
        <a className="ao-skip" href="#conteudo">Pular para o conteúdo</a>
        <motion.div style={{ scaleX: progress }} className="fixed inset-x-0 top-0 z-50 h-0.5 origin-left bg-ao-primary" aria-hidden="true" />
        <header className="fixed inset-x-0 top-0 z-40 border-b border-ao-border bg-ao-bg/70 backdrop-blur">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
            <a href="#topo" aria-label="Auto Orbital — início"><img src="/brand/logo-wordmark.svg" alt="Auto Orbital" className="h-9 w-auto" /></a>
            <nav aria-label="Navegação principal" className="hidden gap-8 text-sm font-semibold text-ao-muted-fg md:flex">
              <a href="#desafio" className="hover:text-ao-fg">O desafio</a>
              <a href="#como-funciona" className="hover:text-ao-fg">Como funciona</a>
              <a href="#recursos" className="hover:text-ao-fg">O futuro</a>
              <a href="#planos" className="hover:text-ao-fg">Planos</a>
              <a href="#valores" className="hover:text-ao-fg">Valores</a>
              <a href="#perguntas" className="hover:text-ao-fg">Dúvidas</a>
            </nav>
            <LoginLink className="ao-btn-ghost ao-btn-ghost--small">Entrar <ArrowUpRight className="h-4 w-4" /></LoginLink>
          </div>
        </header>
        <main id="conteudo">
          <Hero />
          <ChallengeScene />
          <BacklogScene />
          <TurnScene />
          <ProductScene />
          <BenefitsSection />
          <FutureSection />
          <TrustSection />
          <PlansScene />
          <OfferSection />
          <FinalSection />
        </main>
        <footer className="ao-footer text-sm text-ao-muted-fg">
          <div className="ao-footer-inner">
            <a href="#topo" className="inline-flex items-center gap-2 font-ao-display font-bold text-ao-fg"><img src="/brand/logo-mark-static.svg" alt="" className="h-8 w-8" /><img src="/brand/logo-wordmark.svg" alt="Auto Orbital" className="h-6 w-auto" /></a>
            <span>Uma plataforma em evolução para afiliados.</span>
            <nav aria-label="Rodapé">
              <a href="/termos">Termos</a>
              <a href="/privacidade">Privacidade</a>
              <LoginLink>Entrar</LoginLink>
            </nav>
          </div>
        </footer>
      </div>
    </MotionConfig>
  )
}
