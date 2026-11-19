import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { postsApi, type Post, type PostNetwork } from "../../api/posts"
import { Modal } from "../ui/Modal"
import { Button } from "../ui/Button"
import { TextInput } from "../ui/TextInput"

const NETWORK_NAMES: Record<PostNetwork, string> = { threads: "Threads", x: "X", facebook: "Facebook", instagram: "Instagram", tiktok: "TikTok", shopee_video: "Shopee Vídeo" }

type Choice = "published" | "removed" | "not_published"

type DecisionProps = { post: Post; onClose: () => void; onDone: () => void; onAuthError: (err: Error) => void }

/**
 * Conferência manual de um post "Sem confirmação" (qualquer rede).
 * Nada é reenviado aqui: "Não foi publicado" só libera o botão Reenviar.
 */
export function ConfirmPublicationModal({ post, onClose, onDone, onAuthError }: DecisionProps) {
  const network = post.network ?? "threads"
  const name = NETWORK_NAMES[network]
  const isThreads = network === "threads"
  const jobId = post.last_result?.job_id ?? null
  const [choice, setChoice] = useState<Choice | null>(null)
  const [link, setLink] = useState("")
  const [acknowledged, setAcknowledged] = useState(false)

  const decide = useMutation({
    mutationFn: () => {
      if (choice === "removed") return postsApi.reconcile(post.id, { reported_removed: true })
      if (choice === "published" && isThreads) return postsApi.reconcile(post.id, { permalink: link.trim() })
      return postsApi.resolveUnknown(post.id, {
        sourceJobId: jobId ?? "", outcome: choice === "published" ? "published" : "not_published",
        permalink: link.trim() || undefined,
      })
    },
    meta: { toast: { pending: "Registrando sua conferência…", success: "Conferência registrada", error: "Não foi possível registrar" } },
    onSuccess: onDone,
    onError: onAuthError,
  })

  const pick = (next: Choice) => {
    setChoice(next)
    setAcknowledged(false)
    setLink("")
  }
  const needsLink = choice === "published" && isThreads
  const canSubmit = choice != null && acknowledged && (!needsLink || link.trim().length > 0) &&
    (choice === "removed" || isThreads && choice === "published" || !!jobId)
  const ackText =
    choice === "published" ? `Conferi no ${name} que este post foi realmente publicado. Nada será reenviado.` :
    choice === "removed" ? "Declaro que vi esta publicação no Threads antes de removê-la. Fica registrado só como meu relato." :
    `Conferi o perfil correto no ${name} e o post não está lá. Ele ficará como "Falhou" e eu decido se reenvio.`

  return (
    <Modal open onClose={() => { if (!decide.isPending) onClose() }} title={`Conferir publicação no ${name}`} width={520}>
      <p className="csp-s-0319">
        A publicação começou, mas o {name} não confirmou o resultado. Para não duplicar o post, o sistema não reenvia sozinho.
        Abra a conta correta no {name}, confira e diga o que aconteceu.
      </p>
      <div role="radiogroup" aria-label="Resultado da conferência">
        <label className="csp-s-0320">
          <input type="radio" name="publication-decision" checked={choice === "published"} disabled={decide.isPending}
            onChange={() => pick("published")} />
          Confirmo que foi publicado
        </label>
        {isThreads && (
          <label className="csp-s-0320">
            <input type="radio" name="publication-decision" checked={choice === "removed"} disabled={decide.isPending}
              onChange={() => pick("removed")} />
            Foi publicado, mas já removi e não tenho mais o link
          </label>
        )}
        <label className="csp-s-0320">
          <input type="radio" name="publication-decision" checked={choice === "not_published"} disabled={decide.isPending}
            onChange={() => pick("not_published")} />
          Não foi publicado
        </label>
      </div>
      {choice === "published" && (
        <TextInput label={isThreads ? "Link direto da publicação no Threads" : `Link da publicação no ${name} (opcional)`}
          type="url" placeholder="https://..." value={link} onChange={(event) => setLink(event.target.value)} />
      )}
      {choice === "not_published" && (
        <p className="csp-s-0319">
          Depois de registrar, use <strong>Reenviar</strong> no post quando quiser publicar de novo. Se o post aparecer mais tarde
          (a rede às vezes demora), um reenvio criaria uma duplicata.
        </p>
      )}
      {choice !== "removed" && choice != null && !jobId && !(isThreads && choice === "published") && (
        <p className="csp-s-0322" role="alert">Não foi possível identificar a execução. Atualize a lista e tente de novo.</p>
      )}
      {choice != null && (
        <label className="csp-s-0321">
          <input type="checkbox" checked={acknowledged} disabled={decide.isPending}
            onChange={(event) => setAcknowledged(event.target.checked)} />
          {ackText}
        </label>
      )}
      {decide.isError && <p role="alert" className="csp-s-0322">{decide.error.message}</p>}
      <div className="csp-s-0323">
        <Button variant="ghost" disabled={decide.isPending} onClick={onClose}>Cancelar</Button>
        <Button variant="mint" loading={decide.isPending} disabled={!canSubmit} onClick={() => decide.mutate()}>
          Registrar conferência
        </Button>
      </div>
    </Modal>
  )
}

/** Reenvio manual de um post que falhou (nada foi publicado). Cria uma única nova tentativa. */
export function RetryFailedModal({ post, onClose, onDone, onAuthError }: DecisionProps) {
  const name = NETWORK_NAMES[post.network ?? "threads"]
  const jobId = post.last_result?.job_id ?? null
  const [acknowledged, setAcknowledged] = useState(false)
  const retry = useMutation({
    mutationFn: () => postsApi.retryFailed(post.id, jobId ?? ""),
    meta: { toast: { pending: "Colocando o reenvio na fila…", success: "Reenvio colocado na fila", error: "Não foi possível reenviar o post" } },
    onSuccess: onDone,
    onError: onAuthError,
  })
  return (
    <Modal open onClose={() => { if (!retry.isPending) onClose() }} title={`Reenviar post no ${name}`} width={480}>
      <p className="csp-s-0319">
        A última tentativa falhou antes de publicar. O reenvio cria uma única nova tentativa, mantém o histórico da falha
        e não consome cota de novo.
      </p>
      {post.last_result?.error && <p className="csp-s-0319">Motivo: {post.last_result.error}</p>}
      <label className="csp-s-0321">
        <input type="checkbox" checked={acknowledged} disabled={retry.isPending}
          onChange={(event) => setAcknowledged(event.target.checked)} />
        Conferi no {name} e o post não está publicado.
      </label>
      {retry.isError && <p role="alert" className="csp-s-0322">{retry.error.message}</p>}
      <div className="csp-s-0323">
        <Button variant="ghost" disabled={retry.isPending} onClick={onClose}>Cancelar</Button>
        <Button variant="mint" loading={retry.isPending} disabled={!acknowledged || !jobId} onClick={() => retry.mutate()}>
          Reenviar post
        </Button>
      </div>
    </Modal>
  )
}
