import { motion } from "motion/react"
import { CalendarClock, Check, ListChecks, Search } from "lucide-react"
import { demoPostText, demoProducts, formatDemoPrice } from "./demoProducts"
import { ProductThumb } from "./shared"

const ease = [0.16, 1, 0.3, 1] as const
const row = (i: number) => ({ initial: { opacity: 0, y: 14 }, animate: { opacity: 1, y: 0 }, transition: { delay: 0.08 * i, duration: 0.4, ease } })

function ProductRow({ index, trailing }: { index: number; trailing?: React.ReactNode }) {
  const product = demoProducts[index]!
  return (
    <div className="flex items-center gap-3">
      <ProductThumb src={product.image} name={product.name} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold">{product.name}</p>
        <p className="text-xs text-ao-muted-fg">{formatDemoPrice(product)}</p>
      </div>
      {trailing}
    </div>
  )
}

/** Conteúdo da demonstração por etapa, com produtos reais do catálogo de exemplo. */
export function DemoPanel({ step }: { step: number }) {
  if (step === 0) {
    return (
      <div>
        <div className="flex items-center gap-2 rounded-lg border border-ao-border bg-ao-bg/40 px-3 py-2 text-sm text-ao-muted-fg">
          <Search className="h-4 w-4" /> Busque produtos no catálogo conectado
        </div>
        <ul className="mt-4 space-y-2">
          {[0, 1, 2].map((i) => (
            <motion.li key={i} {...row(i)} className={`rounded-lg border p-3 ${i === 0 ? "border-ao-primary/60 bg-ao-primary/5" : "border-ao-border"}`}>
              <ProductRow index={i} trailing={<span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${i === 0 ? "bg-ao-primary text-ao-on-primary" : "border border-ao-border text-ao-muted-fg"}`}>{i === 0 ? "Selecionado" : "Adicionar"}</span>} />
            </motion.li>
          ))}
        </ul>
      </div>
    )
  }
  if (step === 1) {
    const lists = [
      { name: "Casa e decoração", items: [2, 3, 4, 5, 6] },
      { name: "Organização da cozinha", items: [1, 7] },
    ]
    return (
      <div className="grid gap-3 sm:grid-cols-2">
        {lists.map((list, li) => (
          <motion.div key={list.name} {...row(li)} className="rounded-xl border border-ao-border p-4">
            <p className="flex items-center gap-2 font-ao-display font-semibold"><ListChecks className="h-4 w-4 text-ao-primary" /> {list.name}</p>
            <p className="mt-1 text-xs text-ao-muted-fg">{list.items.length} produtos</p>
            <div className="mt-3 flex -space-x-3">
              {list.items.map((n) => <span key={n} className="rounded-lg ring-2 ring-ao-card"><ProductThumb src={demoProducts[n]!.image} name={demoProducts[n]!.name} className="h-11 w-11" /></span>)}
            </div>
          </motion.div>
        ))}
      </div>
    )
  }
  if (step === 2) {
    const used = demoPostText.length
    return (
      <div className="rounded-xl border border-ao-border p-4">
        <ProductRow index={1} />
        <motion.p {...row(1)} className="mt-4 rounded-lg bg-ao-bg/40 p-3 text-sm leading-relaxed">{demoPostText}</motion.p>
        <p className="mt-3 flex items-center justify-between text-xs text-ao-muted-fg">
          <span>Threads · texto de exemplo, você edita antes de publicar</span>
          <span className="tabular-nums">{used}/500 caracteres</span>
        </p>
      </div>
    )
  }
  if (step === 3) {
    const slots = [{ n: 1, when: "Seg · 09:00", net: "Threads" }, { n: 0, when: "Ter · 12:30", net: "Instagram" }, { n: 2, when: "Qui · 19:00", net: "Facebook" }]
    return (
      <ul className="space-y-2">
        {slots.map((slot, i) => (
          <motion.li key={slot.n} {...row(i)} className="rounded-lg border border-ao-border p-3">
            <ProductRow index={slot.n} trailing={<span className="flex items-center gap-1.5 whitespace-nowrap text-xs text-ao-primary"><CalendarClock className="h-4 w-4" /> {slot.when} · {slot.net}</span>} />
          </motion.li>
        ))}
      </ul>
    )
  }
  const history = [{ n: 1, label: "Publicado", done: true }, { n: 0, label: "Agendado", done: false }, { n: 2, label: "Agendado", done: false }]
  return (
    <ul className="space-y-2">
      {history.map((item, i) => (
        <motion.li key={item.n} {...row(i)} className="rounded-lg border border-ao-border p-3">
          <ProductRow index={item.n} trailing={
            <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold ${item.done ? "bg-ao-primary text-ao-on-primary" : "border border-ao-border text-ao-muted-fg"}`}>
              {item.done ? <Check className="h-3 w-3" /> : null}{item.label}
            </span>
          } />
        </motion.li>
      ))}
    </ul>
  )
}
