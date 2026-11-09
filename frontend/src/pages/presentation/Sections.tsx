import { motion, useScroll, useTransform } from "motion/react"
import { ArrowRight, ArrowUpRight, ShieldCheck } from "lucide-react"
import { useRef } from "react"
import { benefits, faq } from "./content"
import { Eyebrow, Highlight, LoginLink, Reveal } from "./shared"

function Parallax({ children, speed = 80, className }: { children: React.ReactNode; speed?: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] })
  const y = useTransform(scrollYProgress, [0, 1], [speed, -speed])
  return <motion.div ref={ref} style={{ y }} className={className}>{children}</motion.div>
}

export function BenefitsSection() {
  return (
    <section id="beneficios" className="mx-auto max-w-7xl px-6 py-32">
      <Reveal>
        <Eyebrow>05 / O que muda na sua rotina</Eyebrow>
        <h2 className="mt-4 max-w-3xl font-ao-display text-3xl font-bold md:text-5xl">Não se trata de postar mais. Trata-se de trabalhar melhor.</h2>
        <p className="mt-4 max-w-2xl text-ao-muted-fg">O valor está em reduzir o vai e vem entre tarefas e trazer organização ao processo que você já executa como afiliado.</p>
      </Reveal>
      <div className="mt-14 grid gap-6 md:grid-cols-3">
        {benefits.map((b, i) => (
          <Parallax key={b.number} speed={30 + i * 30}>
            <Reveal delay={i * 0.12} className="h-full rounded-2xl border border-ao-border bg-ao-card p-6 shadow-ao-elegant">
              <span className="font-ao-display text-4xl font-bold text-ao-primary/40">{b.number}</span>
              <h3 className="mt-4 font-ao-display text-xl font-semibold">{b.title}</h3>
              <p className="mt-3 text-sm text-ao-muted-fg">{b.text}</p>
              <span className="mt-6 inline-block rounded-full border border-ao-border px-3 py-1 text-[11px] text-ao-primary">{b.tag}</span>
            </Reveal>
          </Parallax>
        ))}
      </div>
    </section>
  )
}

export function FutureSection() {
  return (
    <section id="recursos" className="mx-auto max-w-7xl px-6 py-32">
      <Reveal>
        <Eyebrow>06 / A próxima órbita</Eyebrow>
        <h2 className="mt-4 max-w-3xl font-ao-display text-3xl font-bold md:text-5xl">A ferramenta de hoje. <Highlight>A evolução que estamos construindo.</Highlight></h2>
        <p className="mt-4 max-w-2xl text-ao-muted-fg">O Auto Orbital nasceu para organizar a divulgação de afiliados. Nossa visão é avançar para um fluxo mais inteligente e automatizado, sem esconder o que ainda está em desenvolvimento.</p>
      </Reveal>
      <div className="mt-14 grid gap-6 lg:grid-cols-3">
        <Reveal className="rounded-2xl border border-ao-primary/40 bg-ao-card p-6 shadow-ao-glow lg:col-span-2">
          <span className="text-[11px] uppercase tracking-widest text-ao-primary">Em desenvolvimento</span>
          <h3 className="mt-3 font-ao-display text-2xl font-semibold">Piloto Automático Orbital</h3>
          <p className="mt-3 text-sm text-ao-muted-fg">Visão futura de coleta de oportunidades, análise, criação assistida por IA e publicação com critérios, limites e controles definidos pelo afiliado.</p>
          <div className="mt-5 flex flex-wrap gap-2">
            {["Coleta", "Análise", "Conteúdo", "Publicação"].map((t, i) => (
              <motion.span key={t} initial={{ opacity: 0, scale: 0.5 }} whileInView={{ opacity: 1, scale: 1 }} viewport={{ once: true }} transition={{ delay: 0.3 + i * 0.12 }} className="rounded-full bg-ao-muted px-3 py-1 text-xs">{t}</motion.span>
            ))}
          </div>
          <p className="mt-5 text-xs text-ao-muted-fg">Não disponível nesta fase. Depende de estudo técnico, custos e autorizações.</p>
        </Reveal>
        <Reveal delay={0.15} className="rounded-2xl border border-ao-border bg-ao-card p-6">
          <span className="text-[11px] uppercase tracking-widest text-ao-primary">Em estudo</span>
          <h3 className="mt-3 font-ao-display text-xl font-semibold">Uma plataforma. Diferentes programas de afiliados.</h3>
          <p className="mt-3 text-sm text-ao-muted-fg">A Shopee é a primeira integração de catálogo. Outras lojas poderão entrar conforme a viabilidade técnica e as permissões de cada programa.</p>
          <p className="mt-4 text-xs">Shopee <strong>Integração inicial</strong> · Outros programas <strong>Expansão planejada</strong></p>
        </Reveal>
        <Reveal delay={0.25} className="rounded-2xl border border-ao-border bg-ao-card p-6 lg:col-span-3">
          <span className="text-[11px] uppercase tracking-widest text-ao-primary">Cobertura em evolução</span>
          <h3 className="mt-3 font-ao-display text-xl font-semibold">Entender o que acontece depois de publicar.</h3>
          <p className="mt-3 text-sm text-ao-muted-fg">Histórico e acompanhamento já fazem parte do produto. A expansão de análises depende dos dados oficiais disponibilizados pelas redes.</p>
        </Reveal>
      </div>
    </section>
  )
}

export function TrustSection() {
  return (
    <section id="perguntas" className="mx-auto grid max-w-7xl gap-12 px-6 py-32 lg:grid-cols-2">
      <Reveal>
        <Eyebrow>07 / Confiança primeiro</Eyebrow>
        <h2 className="mt-4 font-ao-display text-3xl font-bold md:text-5xl">Conecte com clareza. Divulgue com consciência.</h2>
        <p className="mt-4 text-ao-muted-fg">As redes sociais têm regras, permissões e formatos diferentes. O Auto Orbital não esconde isso: cada conexão e cada forma de publicação dependem do que o provedor efetivamente autoriza.</p>
        <ul className="mt-6 space-y-3 text-sm">
          {["Autorizações oficiais por rede compatível", "Controles e permissões por conta", "Status de recursos apresentados com transparência"].map((t) => (
            <li key={t} className="flex items-center gap-3"><ShieldCheck className="h-4 w-4 text-ao-primary" />{t}</li>
          ))}
        </ul>
      </Reveal>
      <Reveal delay={0.15}>
        <h3 className="font-ao-display text-2xl font-semibold">Perguntas que importam</h3>
        <div className="mt-4 space-y-2">
          {faq.map((f) => (
            <details key={f.q} className="group rounded-xl border border-ao-border bg-ao-card px-5 py-4">
              <summary className="cursor-pointer list-none font-semibold">{f.q}</summary>
              <p className="mt-3 text-sm text-ao-muted-fg">{f.a}</p>
            </details>
          ))}
        </div>
      </Reveal>
    </section>
  )
}

export function FinalSection() {
  const ref = useRef<HTMLElement>(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end end"] })
  const scale = useTransform(scrollYProgress, [0, 1], [0.4, 1.2])
  return (
    <section id="comecar" ref={ref} className="relative overflow-hidden px-6 py-40 text-center">
      <motion.div style={{ scale }} className="ao-planet pointer-events-none absolute left-1/2 top-1/2 h-[60vmin] w-[60vmin] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-40" />
      <Reveal className="relative">
        <Eyebrow>09 / Sua próxima órbita</Eyebrow>
        <h2 className="mx-auto mt-4 max-w-3xl font-ao-display text-4xl font-bold md:text-6xl">Boas oportunidades merecem <Highlight>uma rotina à altura.</Highlight></h2>
        <p className="mx-auto mt-4 max-w-2xl text-ao-muted-fg">Conheça o que já estamos construindo para transformar a forma como afiliados organizam e divulgam suas oportunidades.</p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <a href="#como-funciona" className="ao-btn-primary">Ver como funciona <ArrowRight className="h-4 w-4" /></a>
          <LoginLink className="ao-btn-ghost">Entrar <ArrowUpRight className="h-4 w-4" /></LoginLink>
        </div>
      </Reveal>
    </section>
  )
}
