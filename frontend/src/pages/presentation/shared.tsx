import { Link } from "@tanstack/react-router"
import { motion, useMotionValue, useReducedMotion, useScroll, type MotionValue } from "motion/react"
import type { ReactNode, RefObject } from "react"
import { LOGIN_PATH } from "./content"

/** Progresso do scroll de uma cena; com "reduzir movimento" ativo, retorna a cena já concluída. */
export function useSceneProgress(
  ref: RefObject<HTMLElement | null>,
  offset: ["start start", "end end"] | ["start start", "end start"] = ["start start", "end end"],
): MotionValue<number> {
  const { scrollYProgress } = useScroll({ target: ref, offset })
  const finished = useMotionValue(1)
  const reduce = useReducedMotion()
  return reduce ? finished : scrollYProgress
}

export function Reveal({ children, delay = 0, className }: { children: ReactNode; delay?: number; className?: string }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 60, rotateX: 18, filter: "blur(8px)" }}
      whileInView={{ opacity: 1, y: 0, rotateX: 0, filter: "blur(0px)" }}
      viewport={{ once: true, margin: "-15% 0px" }}
      transition={{ duration: 0.9, delay, ease: [0.16, 1, 0.3, 1] }}
      style={{ transformPerspective: 1000 }}
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
