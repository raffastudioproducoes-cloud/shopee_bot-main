import { Link } from "@tanstack/react-router"
import { motion, useMotionValue, useReducedMotion, useScroll, useSpring, type MotionValue } from "motion/react"
import { useState, type ReactNode, type RefObject } from "react"
import { LOGIN_PATH } from "./content"

/** Progresso do scroll de uma cena; com "reduzir movimento" ativo, retorna a cena já concluída. */
export function useSceneProgress(
  ref: RefObject<HTMLElement | null>,
  offset: ["start start", "end end"] | ["start start", "end start"] = ["start start", "end end"],
): MotionValue<number> {
  const { scrollYProgress } = useScroll({ target: ref, offset })
  // Mola leve: o movimento acompanha a rolagem sem trancos (rodinha do mouse, toque).
  const smooth = useSpring(scrollYProgress, { stiffness: 110, damping: 28, mass: 0.35, restDelta: 0.0005 })
  const finished = useMotionValue(1)
  const reduce = useReducedMotion()
  return reduce ? finished : smooth
}

export function Reveal({ children, delay = 0, className }: { children: ReactNode; delay?: number; className?: string }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 26, filter: "blur(5px)" }}
      whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, margin: "-12% 0px" }}
      transition={{ duration: 1.1, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  )
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="font-ao-display text-xs font-semibold uppercase tracking-[0.3em] text-ao-primary">{children}</p>
}

export function Highlight({ children }: { children: ReactNode }) {
  return <em className="not-italic text-ao-primary">{children}</em>
}

export function SceneTag({ scene, title, note }: { scene: string; title: string; note: string }) {
  return (
    <div className="flex items-center gap-3 text-[11px] uppercase tracking-[0.2em] text-ao-muted-fg">
      <span className="rounded-full border border-ao-border px-2 py-1 text-ao-primary">{scene}</span>
      <span>{title}</span>
      <span className="hidden opacity-60 md:inline">· {note}</span>
    </div>
  )
}

/** Link para a tela de login dentro do app (sem recarregar a página). */
export function LoginLink({ className, children }: { className?: string; children: ReactNode }) {
  return <Link to={LOGIN_PATH} className={className}>{children}</Link>
}

/** Imagem de produto com reserva: se o CDN falhar ou bloquear, mostra um bloco de cor com a inicial. */
export function ProductThumb({ src, name, className = "h-12 w-12" }: { src: string; name: string; className?: string }) {
  const [failed, setFailed] = useState(false)
  if (failed) {
    return (
      <span aria-hidden="true" className={`${className} inline-flex shrink-0 items-center justify-center rounded-lg bg-ao-muted font-ao-display text-sm font-semibold text-ao-primary`}>
        {name.charAt(0)}
      </span>
    )
  }
  return (
    <img
      src={src}
      alt=""
      loading="lazy"
      decoding="async"
      referrerPolicy="no-referrer"
      onError={() => setFailed(true)}
      className={`${className} shrink-0 rounded-lg bg-ao-muted object-cover`}
    />
  )
}
