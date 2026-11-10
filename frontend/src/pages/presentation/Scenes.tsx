import { AnimatePresence, motion, useMotionValueEvent, useTransform, type MotionValue } from "motion/react"
import { useRef, useState } from "react"
import { flowSteps, networks, productSteps, progressToStep, routineTasks, weekDays, type NetworkTask } from "./content"
import { DemoPanel } from "./ProductDemo"
import { demoProducts, formatDemoPrice } from "./demoProducts"
import { Eyebrow, Highlight, ProductThumb, SceneTag, useSceneProgress } from "./shared"

/* ---------- Cena 01: o caos da divulgação manual ---------- */

const chaosPositions = [
  { x: -340, y: -170, r: -12 },
  { x: 320, y: -190, r: 9 },
  { x: -380, y: 150, r: 7 },
  { x: 350, y: 170, r: -10 },
  { x: 0, y: 260, r: 4 },
]

function NetworkCard({ task, index, progress }: { task: NetworkTask; index: number; progress: MotionValue<number> }) {
  const start = 0.1 + index * 0.13
  const range = [start, start + 0.18]
  const target = chaosPositions[index] ?? { x: 0, y: 0, r: 0 }
  const x = useTransform(progress, range, [0, target.x])
  const y = useTransform(progress, range, [0, target.y])
  const rotate = useTransform(progress, range, [0, target.r])
  const opacity = useTransform(progress, [start, start + 0.06], [0, 1])
  const scale = useTransform(progress, range, [0.4, 1])
  return (
    <motion.div style={{ x, y, rotate, opacity, scale }} className="absolute w-44 rounded-xl border border-ao-border bg-ao-card p-4 shadow-ao-elegant md:w-52">
      <p className="font-ao-display font-semibold">{task.name}</p>
      <div className="mt-2 flex justify-between text-xs text-ao-muted-fg">
        <span>{task.action}</span>
        <span className="text-ao-primary">{index + 1} / 5</span>
      </div>
    </motion.div>
  )
}

export function ChallengeScene() {
  const ref = useRef<HTMLElement>(null)
  const p = useSceneProgress(ref)
  const coreScale = useTransform(p, [0, 0.8], [1, 0.85])
  const shake = useTransform(p, [0.75, 0.8, 0.85, 0.9], [0, -6, 6, 0])
  return (
    <section id="desafio" ref={ref} className="relative h-[320vh]">
      <div className="sticky top-0 flex h-screen flex-col overflow-hidden">
        <div className="mx-auto w-full max-w-7xl px-6 pt-24">
          <Eyebrow>01 / O desafio</Eyebrow>
          <h2 className="mt-4 max-w-3xl font-ao-display text-3xl font-bold md:text-5xl">Uma oportunidade. Cinco abas. O mesmo trabalho repetido.</h2>
          <p className="mt-4 max-w-2xl text-ao-muted-fg">A rotina de divulgação pode se tornar um labirinto: copiar, adaptar, trocar de aplicativo, conferir horários e começar tudo outra vez.</p>
        </div>
        <div className="relative flex flex-1 scale-[0.6] items-center justify-center md:scale-100">
          {networks.map((task, i) => (
            <NetworkCard key={task.name} task={task} index={i} progress={p} />
          ))}
          <motion.div style={{ scale: coreScale, x: shake }} className="relative z-10 rounded-2xl border border-ao-primary/60 bg-ao-card px-8 py-6 text-center shadow-ao-glow">
            <div className="flex items-center gap-3 text-left">
              <ProductThumb src={demoProducts[0]!.image} name={demoProducts[0]!.name} className="h-14 w-14" />
              <div>
                <p className="max-w-[11rem] font-ao-display text-sm font-bold leading-tight">{demoProducts[0]!.name}</p>
                <p className="mt-1 text-xs text-ao-muted-fg">Uma oportunidade encontrada · {formatDemoPrice(demoProducts[0]!)}</p>
              </div>
            </div>
          </motion.div>
        </div>
        <div className="mx-auto w-full max-w-7xl px-6 pb-8">
          <SceneTag scene="Cena 01" title="O caos da divulgação manual" note="Animação Scroll World" />
        </div>
      </div>
    </section>
  )
}

/* ---------- 02: o acúmulo ---------- */

function DayColumn({ day, index, progress }: { day: string; index: number; progress: MotionValue<number> }) {
  const count = useTransform(progress, [0.1, 0.85], [0, 4 + index])
  const [visible, setVisible] = useState(0)
  useMotionValueEvent(count, "change", (v) => setVisible(Math.round(v)))
  return (
    <div className="flex min-h-[220px] flex-col-reverse gap-1.5 rounded-lg border border-ao-border bg-ao-bg/40 p-2">
      <AnimatePresence>
        {Array.from({ length: visible }).map((_, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: -60, rotate: (i % 2 ? 1 : -1) * 8 }}
            animate={{ opacity: 1, y: 0, rotate: (i % 3) - 1 }}
            exit={{ opacity: 0, y: -30 }}
            className={`h-5 rounded ${i % 3 === 0 ? "bg-ao-primary/70" : i % 3 === 1 ? "bg-ao-accent/60" : "bg-ao-muted"}`}
          />
        ))}
      </AnimatePresence>
      <span className="mt-auto pb-1 text-center text-[10px] font-semibold tracking-widest text-ao-muted-fg">{day}</span>
    </div>
  )
}

export function BacklogScene() {
  const ref = useRef<HTMLElement>(null)
  const p = useSceneProgress(ref)
  const punch = useTransform(p, [0.7, 0.9], [0, 1])
  const punchScale = useTransform(p, [0.7, 0.9], [0.8, 1])
  return (
    <section id="acumulo" ref={ref} className="relative h-[260vh]">
      <div className="sticky top-0 flex h-screen items-center overflow-hidden">
        <div className="mx-auto grid w-full max-w-7xl items-center gap-12 px-6 lg:grid-cols-2">
          <div>
            <Eyebrow>02 / O acúmulo</Eyebrow>
            <h2 className="mt-4 font-ao-display text-3xl font-bold md:text-5xl">O problema não é uma postagem. São todas as próximas.</h2>
            <p className="mt-4 text-ao-muted-fg">Quando os produtos e os horários se multiplicam, lembrar de cada etapa exige uma atenção que poderia estar dedicada a encontrar novas oportunidades.</p>
            <motion.p style={{ opacity: punch, scale: punchScale }} className="mt-8 origin-left font-ao-display text-xl">
              Uma aba esquecida. Um horário perdido. <strong className="text-ao-primary">Mais uma tarefa na sua cabeça.</strong>
            </motion.p>
          </div>
          <div className="rounded-2xl border border-ao-border bg-ao-card p-5 shadow-ao-elegant">
            <p className="text-sm"><strong className="font-ao-display">Sua rotina de divulgação</strong> <span className="text-ao-muted-fg">visão ilustrativa</span></p>
            <div className="mt-4 grid grid-cols-5 gap-2">
              {weekDays.map((d, i) => <DayColumn key={d} day={d} index={i} progress={p} />)}
            </div>
            <ul className="mt-4 space-y-2 text-sm">
              {routineTasks.map((t) => (
                <li key={t.label} className="flex justify-between rounded-lg bg-ao-bg/40 px-3 py-2">
                  <span>{t.label}</span><span className="text-ao-muted-fg">{t.when}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}

/* ---------- Cena 02: a transformação orbital ---------- */

const scatter = [
  { x: -260, y: -200, r: -25 },
  { x: 240, y: -160, r: 18 },
  { x: -200, y: 190, r: 14 },
  { x: 280, y: 210, r: -20 },
]

function FlowNode({ label, index, progress }: { label: string; index: number; progress: MotionValue<number> }) {
  const s = scatter[index] ?? { x: 0, y: 0, r: 0 }
  const x = useTransform(progress, [0, 0.5], [s.x, 0])
  const y = useTransform(progress, [0, 0.5], [s.y, 0])
  const rotate = useTransform(progress, [0, 0.5], [s.r, 0])
  const glow = useTransform(progress, [0.5 + index * 0.1, 0.6 + index * 0.1], [0.3, 1])
  return (
    <motion.div style={{ x, y, rotate, opacity: glow }} className="relative z-10 rounded-xl border border-ao-primary/50 bg-ao-card px-5 py-3 text-center font-ao-display font-semibold shadow-ao-glow">
      {label}
    </motion.div>
  )
}

export function TurnScene() {
  const ref = useRef<HTMLElement>(null)
  const p = useSceneProgress(ref)
  const line = useTransform(p, [0.45, 0.9], [0, 1])
  const ringRotate = useTransform(p, [0, 1], [-90, 90])
  const ringScale = useTransform(p, [0, 0.5], [2.5, 1])
  return (
    <section id="virada" ref={ref} className="relative h-[280vh]">
      <div className="sticky top-0 flex h-screen flex-col items-center justify-center overflow-hidden px-6 text-center">
        <motion.div style={{ rotate: ringRotate, scale: ringScale }} className="ao-orbit-ring pointer-events-none absolute h-[70vmin] w-[70vmin] rounded-full" />
        <Eyebrow>03 / A virada</Eyebrow>
        <h2 className="mt-4 max-w-3xl font-ao-display text-3xl font-bold md:text-5xl">Menos abas abertas. <Highlight>Mais clareza para avançar.</Highlight></h2>
        <p className="mt-4 max-w-2xl text-ao-muted-fg">Imagine suas oportunidades, conteúdos e programações seguindo um mesmo fluxo. Sem transformar cada nova divulgação em uma lista de tarefas dispersas.</p>
        <div className="relative mt-14 flex flex-col items-center gap-6 md:flex-row md:gap-10">
          <svg className="absolute left-0 top-1/2 hidden h-2 w-full -translate-y-1/2 md:block" preserveAspectRatio="none" viewBox="0 0 100 2" aria-hidden="true">
            <motion.line x1="0" y1="1" x2="100" y2="1" className="stroke-ao-primary" strokeWidth="0.6" style={{ pathLength: line }} />
          </svg>
          {flowSteps.map((s, i) => <FlowNode key={s} label={s} index={i} progress={p} />)}
        </div>
        <div className="absolute bottom-8"><SceneTag scene="Cena 02" title="A transformação orbital" note="Movimento cinematográfico" /></div>
      </div>
    </section>
  )
}

/* ---------- Cena 03: o produto em ação ---------- */

export function ProductScene() {
  const ref = useRef<HTMLElement>(null)
  const p = useSceneProgress(ref)
  const [step, setStep] = useState(0)
  useMotionValueEvent(p, "change", (v) => setStep(progressToStep(v, productSteps.length)))
  const rotateX = useTransform(p, [0, 0.2], [28, 0])
  const rotateY = useTransform(p, [0.2, 0.5, 0.8, 1], [0, -6, 6, 0])
  const scale = useTransform(p, [0, 0.2], [0.8, 1])
  const bar = useTransform(p, [0, 1], ["0%", "100%"])
  const current = productSteps[step] ?? productSteps[0]!

  return (
    <section id="como-funciona" ref={ref} className="relative h-[450vh]">
      <div className="sticky top-0 flex h-screen flex-col justify-center overflow-hidden">
        <div className="mx-auto w-full max-w-7xl px-6">
          <Eyebrow>04 / O produto em ação</Eyebrow>
          <h2 className="mt-3 max-w-3xl font-ao-display text-2xl font-bold md:text-4xl">Do primeiro produto ao último detalhe. Um fluxo mais simples de acompanhar.</h2>
          <p className="mt-2 hidden max-w-2xl text-sm text-ao-muted-fg md:block">Acompanhe uma demonstração ilustrativa das etapas do Auto Orbital. Você continua no controle da seleção, do conteúdo e da programação.</p>
          <div className="mt-6 grid gap-6 lg:grid-cols-[260px_1fr]">
            <ol className="hidden space-y-2 lg:block">
              {productSteps.map((s, i) => (
                <li key={s.number} className={`rounded-xl border px-4 py-3 transition-all duration-500 ${i === step ? "border-ao-primary bg-ao-card shadow-ao-glow" : "border-transparent opacity-50"}`}>
                  <span className="text-xs text-ao-primary">{s.number}</span> <strong className="font-ao-display">{s.title}</strong>
                  <p className="text-xs text-ao-muted-fg">{s.subtitle}</p>
                </li>
              ))}
            </ol>
            <motion.div style={{ rotateX, rotateY, scale, transformPerspective: 1200 }} className="overflow-hidden rounded-2xl border border-ao-border bg-ao-card shadow-ao-elegant">
              <div className="flex items-center justify-between border-b border-ao-border px-5 py-3 text-xs text-ao-muted-fg">
                <span>Auto Orbital / Demonstração</span><span>Fluxo ilustrativo · produtos do catálogo de exemplo</span>
              </div>
              <div className="h-0.5 bg-ao-muted"><motion.div className="h-full bg-ao-primary" style={{ width: bar }} /></div>
              <div className="min-h-[300px] p-6">
                <AnimatePresence mode="wait">
                  <motion.div key={current.number} initial={{ opacity: 0, x: 60, filter: "blur(6px)" }} animate={{ opacity: 1, x: 0, filter: "blur(0px)" }} exit={{ opacity: 0, x: -60, filter: "blur(6px)" }} transition={{ duration: 0.45 }}>
                    <div className="flex items-center justify-between">
                      <p className="font-ao-display text-xl font-semibold">{current.subtitle}</p>
                      <span className="text-xs text-ao-primary">{current.number} / 05</span>
                    </div>
                    <div className="mt-5"><DemoPanel step={step} /></div>
                    <p className="mt-6"><strong className="font-ao-display text-ao-primary">{current.title}</strong> — {current.description}</p>
                  </motion.div>
                </AnimatePresence>
              </div>
              <p className="border-t border-ao-border px-5 py-2 text-[11px] text-ao-muted-fg">Interface demonstrativa com produtos reais de um catálogo de exemplo · horários e status ilustrativos · não é uma conta ativa</p>
            </motion.div>
          </div>
          <div className="mt-6"><SceneTag scene="Cena 03" title="Exploração do painel em etapas" note="Câmera Scroll World" /></div>
        </div>
      </div>
    </section>
  )
}
