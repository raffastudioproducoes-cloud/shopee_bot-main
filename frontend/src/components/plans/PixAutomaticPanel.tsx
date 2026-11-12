import { useEffect, useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { billingApi, type PixAutomaticQr } from "../../api/billing"
import { PERIOD_LABELS, type BillingPeriod } from "../../lib/planIntent"
import { Button } from "../ui/Button"
import "./planCheckout.css"

const day = (iso: string) => new Date(`${iso.slice(0, 10)}T12:00:00`).toLocaleDateString("pt-BR")

/** Só aceita base64 puro para montar a imagem; qualquer outra coisa vira "sem imagem" (o copia e cola continua). */
function qrSrc(b64: string | null): string | null {
  return b64 && /^[A-Za-z0-9+/=]+$/.test(b64) ? `data:image/png;base64,${b64}` : null
}

interface Props { pix: PixAutomaticQr; period: BillingPeriod; onClose: () => void; onRetry: () => void; retrying?: boolean }

const clock = (seconds: number) =>
  `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`

/** Segundos que faltam, contados a partir do momento em que o QR Code chegou ao navegador. */
function useCountdown(totalSeconds: number): number {
  const [end] = useState(() => Date.now() + totalSeconds * 1000)
  const [left, setLeft] = useState(totalSeconds)
  useEffect(() => {
    const tick = () => setLeft(Math.max(0, Math.round((end - Date.now()) / 1000)))
    tick()
    const id = window.setInterval(tick, 1000)
    return () => window.clearInterval(id)
  }, [end])
  return left
}

/** QR Code do Pix Automático: paga o período agora e autoriza o banco a debitar nas próximas datas. */
export function PixAutomaticPanel({ pix, period, onClose, onRetry, retrying = false }: Props) {
  const queryClient = useQueryClient()
  const [copied, setCopied] = useState(false)
  const sub = useQuery({
    queryKey: ["billing-subscription"], queryFn: billingApi.subscription, retry: false,
    refetchInterval: (q) => (q.state.data?.subscription?.status === "active" ? false : 5000),
  })
  const active = sub.data?.subscription?.status === "active"
  useEffect(() => {
    if (active) void queryClient.invalidateQueries({ queryKey: ["plan-usage"] })
  }, [active, queryClient])
  const image = qrSrc(pix.image_base64)
  const left = useCountdown(pix.expires_in_seconds)
  const expired = left === 0

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(pix.payload ?? "")
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  if (active) {
    return (
      <section className="plan-checkout plan-pix" aria-live="polite">
        <p className="plan-checkout__notice plan-checkout__notice--sucesso" role="status">
          Pix confirmado e débito automático autorizado. Seu plano já está liberado.
        </p>
      </section>
    )
  }
  if (expired) {
    return (
      <section className="plan-checkout plan-pix" aria-labelledby="plan-pix-title">
        <h2 id="plan-pix-title">Este QR Code expirou</h2>
        <p>Por segurança, o QR Code vale só por 1 hora. Gere outro para continuar. Nenhuma cobrança foi feita.</p>
        <div className="plan-sub__actions">
          <Button onClick={onRetry} disabled={retrying}>{retrying ? "Gerando…" : "Gerar novo QR Code"}</Button>
          <Button variant="ghost" onClick={onClose}>Fechar</Button>
        </div>
      </section>
    )
  }
  return (
    <section className="plan-checkout plan-pix" aria-labelledby="plan-pix-title">
      <h2 id="plan-pix-title">Pague com Pix Automático</h2>
      <p className={`plan-pix__timer${left <= 300 ? " plan-pix__timer--low" : ""}`} role="timer" aria-live="off">
        Tempo restante para pagar: <strong>{clock(left)}</strong>
      </p>
      <ol>
        <li>Abra o app do seu banco e leia o QR Code (ou use o Pix copia e cola).</li>
        <li>Confirme o pagamento e <strong>autorize o débito automático</strong> quando o banco pedir.</li>
        <li>Pronto: as próximas cobranças saem sozinhas a cada {PERIOD_LABELS[period].toLowerCase()},
          a próxima em <strong>{day(pix.next_charge)}</strong>. Você pode cancelar quando quiser, aqui ou no seu banco.</li>
      </ol>
      <div className="plan-pix__body">
        {image ? <img src={image} alt="QR Code do Pix" width={220} height={220} /> : <p>QR Code indisponível. Use o copia e cola.</p>}
        <div>
          {pix.payload && <>
            <p className="plan-pix__code" tabIndex={0} aria-label="Pix copia e cola">{pix.payload}</p>
            <Button onClick={() => void copy()}>{copied ? "Copiado!" : "Copiar Pix copia e cola"}</Button>
          </>}
          <p className="plan-checkout__fine">O QR Code vale por 1 hora. Se o tempo acabar, é só gerar outro.
            O plano é liberado quando o banco confirma o pagamento e a autorização, o que pode levar alguns minutos.
            Nem todo banco oferece o Pix Automático; se o seu não aceitar, use o cartão.</p>
          <Button variant="ghost" onClick={onClose}>Fechar</Button>
        </div>
      </div>
    </section>
  )
}
