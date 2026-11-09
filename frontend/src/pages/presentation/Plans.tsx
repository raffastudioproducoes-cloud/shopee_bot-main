import { AnimatePresence, motion, useMotionValueEvent, useSpring, useTransform } from "motion/react"
import { CalendarDays, Clock, FolderOpen, Lock, LockOpen, Package, Repeat, Send, Users } from "lucide-react"
import { useEffect, useRef, useState, type ReactNode } from "react"
import { formatCount, plans, progressToStep, type PlanInfo } from "./content"
import { Eyebrow, Highlight, useSceneProgress } from "./shared"

/* Contador que "rola" até o valor do plano ativo — transmite crescimento. */
function Counter({ value }: { value: number }) {
  const spring = useSpring(value, { stiffness: 90, damping: 20 })
  const text = useTransform(spring, (v) => formatCount(v))
  useEffect(() => spring.set(value), [spring, value])
  return <motion.span>{text}</motion.span>
}

function Card({ icon, title, note, children, locked = false }: { icon: ReactNode; title: string; note: string; children: ReactNode; locked?: boolean }) {
  return (
    <motion.div layout className={`relative overflow-hidden rounded-2xl border bg-ao-card p-4 shadow-ao-elegant transition-colors duration-500 ${locked ? "border-ao-border opacity-70" : "border-ao-primary/30"}`}>
      <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-ao-muted-fg">
        <span className="text-ao-primary">{icon}</span>{title}
      </div>
      <div className="mt-3">{children}</div>
      <p className="mt-3 text-[11px] text-ao-muted-fg">{note}</p>
    </motion.div>
  )
}

/* Produtos: barra de catálogo enchendo proporcionalmente ao teto Premium. */
function ProductsCard({ plan }: { plan: PlanInfo }) {
  return (
    <Card icon={<Package className="h-4 w-4" />} title="Catálogo" note="Produtos salvos, compartilhados por toda a conta.">
      <p className="font-ao-display text-3xl font-bold"><Counter value={plan.products} /></p>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-ao-muted">
        <motion.div className="h-full rounded-full bg-ao-primary" animate={{ width: `${(plan.products / 2000) * 100}%` }} transition={{ type: "spring", stiffness: 70, damping: 18 }} />
      </div>
    </Card>
  )
}

/* Listas: pastas empilhando conforme o limite. */
function ListsCard({ plan }: { plan: PlanInfo }) {
  const folders = Math.round(plan.lists / 10)
  return (
    <Card icon={<FolderOpen className="h-4 w-4" />} title="Listas" note="Por perfil, para continuar de onde parou.">
      <p className="font-ao-display text-3xl font-bold"><Counter value={plan.lists} /></p>
      <div className="mt-3 flex h-6 items-end gap-1">
        {Array.from({ length: 10 }).map((_, i) => (
          <motion.span key={i} className="w-full rounded-sm bg-ao-accent/70" animate={{ height: i < folders ? `${40 + (i % 3) * 20}%` : "8%", opacity: i < folders ? 1 : 0.25 }} transition={{ delay: i * 0.04 }} />
        ))}
      </div>
    </Card>
  )
}

/* Perfis: avatares entrando na órbita da conta. */
function ProfilesCard({ plan }: { plan: PlanInfo }) {
  return (
    <Card icon={<Users className="h-4 w-4" />} title="Perfis" note={plan.profiles === 1 ? "Apenas o perfil principal." : `1 principal + ${plan.profiles - 1} secundários, cada um com suas redes.`}>
      <p className="font-ao-display text-3xl font-bold"><Counter value={plan.profiles} /> <span className="text-sm font-normal text-ao-muted-fg">no total</span></p>
      <div className="mt-3 flex gap-2">
        {Array.from({ length: 5 }).map((_, i) => {
          const on = i < plan.profiles
          return (
            <motion.span key={i} animate={{ scale: on ? 1 : 0.7, opacity: on ? 1 : 0.3 }} transition={{ type: "spring", stiffness: 300, damping: 15, delay: i * 0.08 }}
              className={`grid h-8 w-8 place-items-center rounded-full border text-[10px] font-bold ${on ? (i === 0 ? "border-ao-primary bg-ao-primary text-ao-on-primary" : "border-ao-primary/60 bg-ao-primary/15 text-ao-primary") : "border-dashed border-ao-border"}`}>
              {on ? (i === 0 ? "P" : i) : ""}
            </motion.span>
          )
        })}
      </div>
    </Card>
  )
}

/* Enviar agora: envios decolando dentro de uma hora. */
function SendNowCard({ plan }: { plan: PlanInfo }) {
  return (
    <Card icon={<Send className="h-4 w-4" />} title="Enviar agora" note="Cada rede de destino conta como 1 postagem.">
      <p className="font-ao-display text-3xl font-bold"><Counter value={plan.postsPerHour} /> <span className="text-sm font-normal text-ao-muted-fg">por hora</span></p>
      <div className="mt-3 flex h-8 items-end gap-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <motion.span key={`${plan.id}-${i}`} className={`h-3 w-3 rounded-full ${i < plan.postsPerHour ? "bg-ao-primary" : "bg-ao-muted"}`}
            animate={i < plan.postsPerHour ? { y: [0, -18, 0] } : { y: 0 }}
            transition={i < plan.postsPerHour ? { duration: 1.4, repeat: Infinity, delay: i * 0.25, ease: "easeInOut" } : {}} />
        ))}
      </div>
    </Card>
  )
}

/* Recorrente: 7 dias da semana com horários se acendendo por dia. */
function RecurringCard({ plan }: { plan: PlanInfo }) {
  return (
    <Card icon={<Repeat className="h-4 w-4" />} title="Recorrente" note="Até 7 dias da semana, com horários fixos.">
      <p className="font-ao-display text-3xl font-bold"><Counter value={plan.recurringSlots} /> <span className="text-sm font-normal text-ao-muted-fg">{plan.recurringSlots === 1 ? "horário/dia" : "horários/dia"}</span></p>
      <div className="mt-3 grid grid-cols-7 gap-1">
        {["D", "S", "T", "Q", "Q", "S", "S"].map((d, col) => (
          <div key={col} className="flex flex-col items-center gap-0.5">
            {Array.from({ length: 5 }).map((_, row) => (
              <motion.span key={row} className="h-1.5 w-full rounded-full" animate={{ backgroundColor: row < plan.recurringSlots ? "var(--color-ao-primary)" : "var(--color-ao-muted)" }} transition={{ delay: (col + row) * 0.03 }} />
            ))}
            <span className="text-[9px] text-ao-muted-fg">{d}</span>
          </div>
        ))}
      </div>
    </Card>
  )
}

/* Campanhas: calendário de 30 dias preenchendo a janela permitida. */
function CampaignsCard({ plan }: { plan: PlanInfo }) {
  const c = plan.campaign
  return (
    <Card icon={<CalendarDays className="h-4 w-4" />} title="Campanhas" locked={!c} note={c ? `Até ${c.postsPerDay} postagens/dia · ${c.active} campanhas ativas por perfil.` : "Recurso visível, liberado a partir do Pro."}>
      <p className="font-ao-display text-3xl font-bold">{c ? <><Counter value={c.maxDays} /> <span className="text-sm font-normal text-ao-muted-fg">dias</span></> : <span className="inline-flex items-center gap-2 text-xl text-ao-muted-fg"><Lock className="h-5 w-5" /> Sem acesso</span>}</p>
      <div className="mt-3 grid grid-cols-[repeat(15,minmax(0,1fr))] gap-1">
        {Array.from({ length: 30 }).map((_, i) => (
          <motion.span key={i} className="aspect-square rounded-[3px]" animate={{ backgroundColor: c && i < c.maxDays ? "var(--color-ao-primary)" : "var(--color-ao-muted)", scale: c && i < c.maxDays ? 1 : 0.8 }} transition={{ delay: i * 0.015 }} />
        ))}
      </div>
    </Card>
  )
}

/* Automação: cadeado que se abre apenas no Premium. */
function AutomationCard({ plan }: { plan: PlanInfo }) {
  return (
    <Card icon={<Clock className="h-4 w-4" />} title="Automação" locked={!plan.automation} note={plan.automation ? "Permitida no Premium, com seus critérios e limites." : "Vitrine visível, com convite para o Premium."}>
      <div className="flex items-center gap-3">
        <AnimatePresence mode="wait">
          <motion.span key={String(plan.automation)} initial={{ rotate: -30, scale: 0.5, opacity: 0 }} animate={{ rotate: 0, scale: 1, opacity: 1 }} exit={{ rotate: 30, scale: 0.5, opacity: 0 }} transition={{ type: "spring", stiffness: 260, damping: 14 }}
            className={`grid h-12 w-12 place-items-center rounded-full ${plan.automation ? "bg-ao-primary text-ao-on-primary shadow-ao-glow" : "bg-ao-muted text-ao-muted-fg"}`}>
            {plan.automation ? <LockOpen className="h-5 w-5" /> : <Lock className="h-5 w-5" />}
          </motion.span>
        </AnimatePresence>
        <p className="font-ao-display text-xl font-bold">{plan.automation ? "Liberada" : "Bloqueada"}</p>
      </div>
    </Card>
  )
}

export function PlansScene() {
  const ref = useRef<HTMLElement>(null)
  const p = useSceneProgress(ref)
  const [index, setIndex] = useState(0)
  useMotionValueEvent(p, "change", (v) => setIndex(progressToStep(v, plans.length)))
  const plan = plans[index] ?? plans[0]!

  return (
    <section id="planos" ref={ref} className="relative lg:h-[320vh]">
      <div className="flex flex-col justify-center overflow-hidden py-24 lg:sticky lg:top-0 lg:h-screen lg:py-0">
        <div className="mx-auto w-full max-w-7xl px-6">
          <Eyebrow>08 / Planos e limites</Eyebrow>
          <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <h2 className="max-w-2xl font-ao-display text-2xl font-bold md:text-4xl">Três órbitas. <Highlight>Cresça no seu ritmo.</Highlight></h2>
            <div role="tablist" aria-label="Planos" className="flex gap-1 rounded-full border border-ao-border bg-ao-card p-1">
              {plans.map((pl, i) => (
                <button key={pl.id} type="button" role="tab" aria-selected={i === index} onClick={() => setIndex(i)} className="relative rounded-full px-5 py-2 text-sm font-semibold">
                  {i === index && <motion.span layoutId="plan-pill" className="absolute inset-0 rounded-full bg-ao-primary" transition={{ type: "spring", stiffness: 300, damping: 28 }} />}
                  <span className={`relative ${i === index ? "text-ao-on-primary" : "text-ao-muted-fg"}`}>{pl.name}</span>
                </button>
              ))}
            </div>
          </div>
          <AnimatePresence mode="wait">
            <motion.p key={plan.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="mt-2 text-sm text-ao-muted-fg">
              <strong className="font-ao-display text-ao-fg">{plan.name}</strong> · {plan.tagline}
            </motion.p>
          </AnimatePresence>
          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <ProductsCard plan={plan} />
            <ListsCard plan={plan} />
            <ProfilesCard plan={plan} />
            <SendNowCard plan={plan} />
            <RecurringCard plan={plan} />
            <div className="sm:col-span-2"><CampaignsCard plan={plan} /></div>
            <AutomationCard plan={plan} />
          </div>
          <p className="mt-5 text-xs text-ao-muted-fg">Limites definidos para o lançamento. Os valores de referência estão na seção Valores — o Auto Orbital ainda não iniciou a comercialização. As regras de cada rede social continuam valendo acima de qualquer plano.</p>
        </div>
      </div>
    </section>
  )
}
