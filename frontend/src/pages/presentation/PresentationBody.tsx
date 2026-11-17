import { MotionConfig, motion, useScroll, useSpring } from "motion/react"
import { ArrowUpRight } from "lucide-react"
import { useEffect } from "react"
import { useSiteLang } from "../../lib/siteLang"
import { AppInfoSection, legalLinks } from "./AppInfoSection"
import { Hero } from "./Hero"
import { OfferSection } from "./Offer"
import { PlansScene } from "./Plans"
import { BacklogScene, ChallengeScene, ProductScene, TurnScene } from "./Scenes"
import { BenefitsSection, FinalSection, FutureSection, TrustSection } from "./Sections"
import { LoginLink } from "./shared"
import { COMPANY } from "../../lib/company"
import "./presentation.css"

const META = {
  pt: {
    title: "Auto Orbital — Agende e publique posts de afiliado nas suas redes",
    description: "Auto Orbital: app web para afiliados Shopee e criadores agendarem e publicarem posts em Threads, Instagram, Facebook, TikTok e X, com métricas por post.",
  },
  en: {
    title: "Auto Orbital — Schedule and publish affiliate posts to your social accounts",
    description: "Auto Orbital: web app for Shopee affiliates and creators to schedule and publish posts to Threads, Instagram, Facebook, TikTok and X, with per-post metrics.",
  },
} as const

export default function PresentationBody() {
  const { scrollYProgress } = useScroll()
  const progress = useSpring(scrollYProgress, { stiffness: 120, damping: 30 })

  const [lang, setLang] = useSiteLang()
  const links = legalLinks(lang)

  // Título e descrição acompanham o idioma escolhido; a página é pública e indexável
  // (o staging continua fora dos buscadores pelo X-Robots-Tag do servidor).
  useEffect(() => {
    const previous = document.title
    const meta = document.querySelector<HTMLMetaElement>('meta[name="description"]')
    const previousDescription = meta?.content
    document.title = META[lang].title
    if (meta) meta.content = META[lang].description
    return () => {
      document.title = previous
      if (meta && previousDescription !== undefined) meta.content = previousDescription
    }
  }, [lang])

  return (
    <MotionConfig reducedMotion="user">
      <div className="ao-pres" id="topo">
        <a className="ao-skip" href="#conteudo">Pular para o conteúdo</a>
        <motion.div style={{ scaleX: progress }} className="fixed inset-x-0 top-0 z-50 h-0.5 origin-left bg-ao-primary" aria-hidden="true" />
        <header className="sticky inset-x-0 top-0 z-40 md:fixed border-b border-ao-border bg-ao-bg/70 backdrop-blur">
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
            <div className="flex items-center gap-3">
              <div role="group" aria-label="Idioma / Language" className="flex overflow-hidden rounded-lg border border-ao-border text-xs font-semibold">
                <button type="button" onClick={() => setLang("pt")} aria-pressed={lang === "pt"} className={`px-2 py-1 ${lang === "pt" ? "bg-ao-primary text-ao-on-primary" : "text-ao-muted-fg"}`}>PT</button>
                <button type="button" onClick={() => setLang("en")} aria-pressed={lang === "en"} className={`px-2 py-1 ${lang === "en" ? "bg-ao-primary text-ao-on-primary" : "text-ao-muted-fg"}`}>EN</button>
              </div>
              <LoginLink className="ao-btn-ghost ao-btn-ghost--small">{lang === "en" ? "Sign in" : "Entrar"} <ArrowUpRight className="h-4 w-4" /></LoginLink>
            </div>
          </div>
          {/* Links legais sempre visíveis, sem abrir menu (exigência da revisão TikTok/Meta). */}
          <nav aria-label={lang === "en" ? "Legal" : "Documentos legais"} className="mx-auto flex max-w-7xl flex-wrap gap-x-4 gap-y-1 px-6 pb-2 text-xs text-ao-muted-fg">
            <a href="#sobre" className="hover:text-ao-fg">{lang === "en" ? "About" : "Sobre"}</a>
            {links.map((l) => <a key={l.href} href={l.href} className="hover:text-ao-fg">{l.label}</a>)}
          </nav>
        </header>
        <main id="conteudo">
          {/* Em inglês o revisor vê primeiro a explicação do app; o restante da apresentação é em português. */}
          {lang === "en" ? <><AppInfoSection lang={lang} first /><Hero /></> : <><Hero /><AppInfoSection lang={lang} /></>}
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
            <span>{lang === "en" ? "© 2026 Raffa Studio Produções. A web app for affiliates and creators." : "© 2026 Raffa Studio Produções. Uma plataforma para afiliados e criadores."}</span>
            <span>{COMPANY.footerLine}</span>
            <nav aria-label="Rodapé">
              <a href="/termos">{lang === "en" ? "Terms" : "Termos"}</a>
              <a href="/privacidade">{lang === "en" ? "Privacy" : "Privacidade"}</a>
              {links.slice(2).map((l) => <a key={l.href} href={l.href}>{l.label}</a>)}
              <LoginLink>{lang === "en" ? "Sign in / Sign up" : "Entrar / Criar conta"}</LoginLink>
            </nav>
          </div>
        </footer>
      </div>
    </MotionConfig>
  )
}
