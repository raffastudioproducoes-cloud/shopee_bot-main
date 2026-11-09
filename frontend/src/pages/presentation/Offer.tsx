import { motion } from "motion/react"
import { Check, Minus, Sparkles } from "lucide-react"
import { PlanTag } from "../../components/plans/PlanTag"
import { buildComparison, planOffers, plans, type ComparisonValue } from "./content"
import { Eyebrow, Highlight, LoginLink, Reveal } from "./shared"

/** Célula da comparação: valor aparece com "pulso"; booleanos viram check/traço. */
function Cell({ value, delay }: { value: ComparisonValue; delay: number }) {
  const content =
    value === true ? <Check className="mx-auto h-4 w-4 text-ao-primary" aria-label="Incluído" /> :
    value === false ? <Minus className="mx-auto h-4 w-4 text-ao-muted-fg/50" aria-label="Não incluído" /> :
    <span className="text-ao-fg">{value}</span>
  return (
    <motion.td
      className="px-3 py-3 text-center text-sm"
      initial={{ opacity: 0, scale: 0.6 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true, margin: "-10% 0px" }}
      transition={{ type: "spring", stiffness: 260, damping: 18, delay }}
    >
      {content}
    </motion.td>
  )
}

export function OfferSection() {
  const rows = buildComparison()
  return (
    <section id="valores" className="relative px-6 py-32">
      <div className="mx-auto max-w-6xl">
        <Reveal className="mx-auto max-w-2xl text-center">
          <Eyebrow>08 / Valores</Eyebrow>
          <h2 className="mt-4 font-ao-display text-4xl font-semibold md:text-5xl">
            Escolha a <Highlight>órbita</Highlight> do seu ritmo.
          </h2>
          <p className="mt-4 text-ao-muted-fg">Comece grátis. Os valores do Pro e do Premium são de referência e a contratação ainda não foi aberta.</p>
        </Reveal>

        {/* Cards de valor: entram em leque, como planetas alinhando na órbita */}
        <div className="mt-16 grid gap-6 md:grid-cols-3 [perspective:1200px]">
          {planOffers.map((offer, index) => {
            const plan = plans.find((p) => p.id === offer.id)
            if (!plan) return null
            return (
              <motion.article
                key={offer.id}
                className={`relative flex flex-col rounded-3xl border p-8 backdrop-blur ${offer.highlight ? "border-ao-primary/60 bg-ao-primary/10 shadow-[0_0_60px_-15px_var(--color-ao-primary)]" : "border-ao-border bg-ao-card/60"}`}
                initial={{ opacity: 0, y: 80, rotateY: (index - 1) * -25 }}
                whileInView={{ opacity: 1, y: 0, rotateY: 0 }}
                whileHover={{ y: -8 }}
                viewport={{ once: true, margin: "-15% 0px" }}
                transition={{ duration: 0.9, delay: index * 0.15, ease: [0.16, 1, 0.3, 1] }}
              >
                {offer.highlight && (
                  <span className="absolute -top-3 left-1/2 inline-flex -translate-x-1/2 items-center gap-1 rounded-full bg-ao-primary px-3 py-1 text-xs font-semibold text-ao-on-primary">
                    <Sparkles className="h-3 w-3" /> Mais equilibrado
                  </span>
                )}
                <h3 className="font-ao-display text-2xl font-semibold"><PlanTag tier={plan.id}>{plan.name}</PlanTag></h3>
                <p className="text-sm text-ao-muted-fg">{plan.tagline}</p>
                <motion.p
                  className={`mt-6 font-ao-display font-semibold text-5xl text-ao-fg`}
                  initial={{ opacity: 0, filter: "blur(10px)" }}
                  whileInView={{ opacity: 1, filter: "blur(0px)" }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.8, delay: 0.4 + index * 0.15 }}
                >
                  {offer.priceLabel}
                </motion.p>
                <p className="mt-1 text-xs uppercase tracking-[0.2em] text-ao-muted-fg">{offer.priceNote}</p>
                <ul className="mt-6 flex-1 space-y-2 text-sm">
                  {rows.map((row, rowIndex) => {
                    const value = row.values[plan.id]
                    return (
                      <motion.li
                        key={row.label}
                        className={`flex items-start gap-2 ${value === false ? "text-ao-muted-fg/50 line-through" : ""}`}
                        initial={{ opacity: 0, x: -12 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.5 + index * 0.15 + rowIndex * 0.05 }}
                      >
                        {value === false ? <Minus className="mt-0.5 h-4 w-4 shrink-0" /> : <Check className="mt-0.5 h-4 w-4 shrink-0 text-ao-primary" />}
                        <span>{row.label}{typeof value === "string" ? `: ${value}` : ""}</span>
                      </motion.li>
                    )
                  })}
                </ul>
                <LoginLink className={`mt-8 justify-center text-center ${offer.highlight ? "ao-btn-primary" : "ao-btn-ghost"}`}>
                  {offer.id === "free" ? "Começar grátis" : "Entrar"}
                </LoginLink>
              </motion.article>
            )
          })}
        </div>

        {/* Card comparativo: valores pulsam linha a linha, revelando a escala entre planos */}
        <Reveal className="mt-20">
          <div className="overflow-x-auto rounded-3xl border border-ao-border bg-ao-card/60 p-2 backdrop-blur">
            <table className="w-full min-w-[560px] border-collapse">
              <thead>
                <tr className="text-left text-xs uppercase tracking-[0.2em] text-ao-muted-fg">
                  <th className="px-4 py-4">Diferença entre planos</th>
                  {plans.map((plan) => (
                    <th key={plan.id} className={`px-3 py-4 text-center ${plan.id === "pro" ? "text-ao-primary" : ""}`}>{plan.name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, rowIndex) => (
                  <motion.tr
                    key={row.label}
                    className="border-t border-ao-border/60"
                    initial={{ backgroundColor: "rgba(0,0,0,0)" }}
                    whileHover={{ backgroundColor: "color-mix(in oklab, var(--color-ao-primary) 8%, transparent)" }}
                  >
                    <td className="px-4 py-3 text-sm text-ao-muted-fg">{row.label}</td>
                    {plans.map((plan, planIndex) => (
                      <Cell key={plan.id} value={row.values[plan.id]} delay={rowIndex * 0.08 + planIndex * 0.12} />
                    ))}
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-4 text-center text-xs text-ao-muted-fg">Limites oficiais definidos para o lançamento. Valores mensais de referência; a contratação ainda não foi aberta.</p>
        </Reveal>
      </div>
    </section>
  )
}
