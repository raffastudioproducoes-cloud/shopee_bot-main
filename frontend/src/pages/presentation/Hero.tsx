import { motion, useTransform } from "motion/react"
import { ArrowDown, ArrowRight, ArrowUpRight, CalendarDays, History, Search, Sparkles } from "lucide-react"
import { useRef } from "react"
import { LoginLink, useSceneProgress } from "./shared"

const titleLines: { text: string; accent?: boolean }[][] = [
  [{ text: "As" }, { text: "oportunidades" }],
  [{ text: "merecem" }, { text: "mais", accent: true }],
  [{ text: "alcance.", accent: true }, { text: "Seu" }],
  [{ text: "tempo" }, { text: "merece" }],
  [{ text: "mais", accent: true }, { text: "liberdade.", accent: true }],
]

const orbitBadges = [
  { label: "Descobrir", Icon: Search, className: "left-[2%] top-[18%]" },
  { label: "Preparar", Icon: Sparkles, className: "right-[4%] top-[8%]" },
  { label: "Planejar", Icon: CalendarDays, className: "right-[0%] bottom-[14%]" },
  { label: "Acompanhar", Icon: History, className: "left-[4%] bottom-[8%]" },
]

export function Hero() {
  const ref = useRef<HTMLElement>(null)
  const p = useSceneProgress(ref, ["start start", "end start"])
  const orbitRotate = useTransform(p, [0, 1], [0, 160])
  const planetScale = useTransform(p, [0, 1], [1, 2.6])
  const planetOpacity = useTransform(p, [0, 0.8], [1, 0])
  const textY = useTransform(p, [0, 1], [0, -220])
  const textOpacity = useTransform(p, [0, 0.6], [1, 0])
  let wordIndex = 0

  return (
    <section ref={ref} className="relative min-h-screen overflow-hidden pt-28" aria-labelledby="ao-hero-title">
      <div className="pointer-events-none absolute inset-0 ao-hero-glow" />
      <div className="relative mx-auto grid max-w-7xl items-center gap-10 px-6 lg:grid-cols-2">
        <motion.div style={{ y: textY, opacity: textOpacity }}>
          <span className="inline-flex items-center gap-2 rounded-full border border-ao-border bg-ao-card/60 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.15em]">
            <span className="h-1.5 w-1.5 rounded-full bg-ao-primary" /> Sua operação de afiliados em uma nova órbita
          </span>
          <h1 id="ao-hero-title" className="mt-8 font-ao-display text-5xl font-bold leading-[0.95] tracking-tight md:text-7xl">
            {titleLines.map((line, li) => (
              <span key={li} className="block">
                {line.map((word) => {
                  const i = wordIndex++
                  return (
                    <motion.span
                      key={word.text + i}
                      className={`mr-[0.25em] inline-block ${word.accent ? "text-ao-primary" : ""}`}
                      initial={{ opacity: 0, y: 40, filter: "blur(10px)" }}
                      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                      transition={{ delay: 0.15 + i * 0.07, duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                    >
                      {word.text}
                    </motion.span>
                  )
                })}
              </span>
            ))}
          </h1>
          <p className="mt-8 max-w-xl text-lg md:text-xl">
            Você já trabalha para encontrar boas oportunidades. Não precisa trabalhar o dobro para divulgá-las.
          </p>
          <p className="mt-4 max-w-xl text-sm text-ao-muted-fg">
            Descubra produtos, organize ideias, prepare conteúdos e acompanhe divulgações em um lugar feito para simplificar sua rotina.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a href="#como-funciona" className="ao-btn-primary">Ver como funciona <ArrowRight className="h-4 w-4" /></a>
            <LoginLink className="ao-btn-ghost">Entrar <ArrowUpRight className="h-4 w-4" /></LoginLink>
          </div>
          <p className="mt-8 text-xs text-ao-muted-fg">Conheça a plataforma em evolução. Sem promessas de resultados garantidos.</p>
        </motion.div>

        <motion.div className="relative mx-auto aspect-square w-full max-w-[560px]" style={{ scale: planetScale, opacity: planetOpacity }}>
          <motion.div className="absolute inset-0" style={{ rotate: orbitRotate }}>
            {[0, 1, 2].map((r) => (
              <div key={r} className="ao-orbit-ring absolute rounded-full" style={{ inset: `${r * 9}%`, transform: `rotateX(${60 + r * 8}deg) rotateZ(${r * 35}deg)` }} />
            ))}
            <div className="absolute left-1/2 top-[6%] h-2 w-2 rounded-full bg-ao-primary shadow-ao-glow" />
            <div className="absolute bottom-[12%] right-[24%] h-1.5 w-1.5 rounded-full bg-ao-accent" />
          </motion.div>
          <div className="ao-planet absolute inset-[24%] flex flex-col items-center justify-center rounded-full">
            <span className="text-xs font-semibold tracking-[0.4em] text-ao-primary">AUTO</span>
            <span className="font-ao-display text-3xl font-bold md:text-4xl">ORBITAL</span>
          </div>
          {orbitBadges.map(({ label, Icon, className }, i) => (
            <motion.div
              key={label}
              className={`absolute ${className} inline-flex items-center gap-2 rounded-xl border border-ao-border bg-ao-card/80 px-4 py-2.5 text-sm font-semibold backdrop-blur`}
              initial={{ opacity: 0, scale: 0.6 }}
              animate={{ opacity: 1, scale: 1, y: [0, -8, 0] }}
              transition={{ delay: 0.8 + i * 0.15, y: { repeat: Infinity, duration: 4 + i, ease: "easeInOut" } }}
            >
              <Icon className="h-4 w-4 text-ao-primary" /> {label}
            </motion.div>
          ))}
        </motion.div>
      </div>
      <a href="#desafio" className="relative mx-auto mt-10 flex w-fit items-center gap-2 pb-10 text-[11px] font-semibold uppercase tracking-[0.25em] text-ao-muted-fg">
        Explore a experiência <ArrowDown className="h-4 w-4 animate-bounce text-ao-primary" />
      </a>
    </section>
  )
}
