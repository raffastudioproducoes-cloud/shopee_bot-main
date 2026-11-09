import { useEffect, useState } from "react"

/** Segundos reais decorridos enquanto `running`; congela o último valor ao parar. */
export function useElapsedSeconds(running: boolean): number {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    if (!running) return
    const startedAt = Date.now()
    setSeconds(0)
    const timer = window.setInterval(
      () => setSeconds(Math.floor((Date.now() - startedAt) / 1000)), 500)
    return () => window.clearInterval(timer)
  }, [running])
  return seconds
}

export function formatElapsed(total: number): string {
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
}
