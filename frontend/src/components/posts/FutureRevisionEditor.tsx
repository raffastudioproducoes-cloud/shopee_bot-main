import { useEffect, useRef, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import type { Post } from "../../api/posts"
import { postsApi } from "../../api/posts"
import { formatUtcTimestampBrasilia } from "../../lib/ptBrDateTime"

type Props = { post: Post; onClose: () => void }

/**
 * Edita apenas a próxima versão de texto de um post recorrente.
 * Não reescreve posts, mídia, produto, cron nem ocorrências já reivindicadas.
 */
export function FutureRevisionEditor({ post, onClose }: Props) {
  const queryClient = useQueryClient()
  const initialized = useRef(false)
  const [texts, setTexts] = useState<string[]>([])
  const [savedAt, setSavedAt] = useState<string | null>(null)
  const latest = useQuery({
    queryKey: ["post-future-revision", post.id],
    queryFn: () => postsApi.getFutureRevision(post.id),
    retry: false,
  })

  useEffect(() => {
    if (!initialized.current && latest.isSuccess) {
      const current = latest.data.revision?.texts?.length
        ? latest.data.revision.texts
        : post.texts?.length ? post.texts : [post.text]
      setTexts([...current])
      initialized.current = true
    }
  }, [latest.isSuccess, latest.data, post.text, post.texts])

  const save = useMutation({
    mutationFn: () => postsApi.updateFuture(post.id, {
      texts: texts.map((value) => value.trim()),
      product_ids: post.products.map((product) => product.id),
    }),
    onSuccess: async (result) => {
      setSavedAt(result.effective_after)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["post-future-revision", post.id] }),
        queryClient.invalidateQueries({ queryKey: ["post-details"] }),
        queryClient.invalidateQueries({ queryKey: ["posts"] }),
      ])
    },
  })

  const valid = texts.length > 0 && texts.every((text) => text.trim().length > 0)

  return (
    <section aria-label="Editar textos de publicações futuras" style={{ display: "grid", gap: 12, padding: 16, border: "1px solid var(--border-hairline)", borderRadius: "var(--r-md)" }}>
      <h3 style={{ margin: 0 }}>Editar próximos textos do POST #{post.id}</h3>
      <p style={{ margin: 0, color: "var(--text-muted)" }}>
        Somente ocorrências futuras, ainda não reivindicadas e com mais de 30 minutos de antecedência receberão a alteração.
        A ocorrência de 30 minutos exatos ou menos, os envios anteriores e os resultados já publicados permanecem imutáveis.
      </p>
      <p style={{ margin: 0, color: "var(--text-muted)" }}>
        Nesta etapa, fotos, vídeos, produto e horários atuais são preservados. Na criação de novos posts,
        continuam disponíveis a foto Shopee e os uploads de fotos/vídeos do dispositivo.
      </p>
      {latest.isPending && <p role="status">Carregando versão atual dos próximos textos…</p>}
      {latest.isError && <p role="alert" style={{ color: "var(--negative)" }}>Não foi possível carregar a revisão futura. Nenhum dado foi alterado.</p>}
      {latest.isSuccess && (
        <form onSubmit={(event) => { event.preventDefault(); if (valid && !save.isPending) save.mutate() }} style={{ display: "grid", gap: 12 }}>
          {latest.data.revision && <p style={{ margin: 0, color: "var(--text-muted)" }}>
            Revisão anterior confirmada para slots posteriores a {formatUtcTimestampBrasilia(latest.data.revision.effective_after)}.
          </p>}
          {texts.map((text, index) => (
            <div key={index} style={{ display: "grid", gap: 6 }}>
              <label htmlFor={`future-post-${post.id}-part-${index}`}>Texto {index + 1}</label>
              <textarea
                id={`future-post-${post.id}-part-${index}`}
                value={text}
                rows={5}
                maxLength={10000}
                onChange={(event) => setTexts((previous) => previous.map((part, partIndex) => partIndex === index ? event.target.value : part))}
                style={{ width: "100%", resize: "vertical", padding: 12, background: "var(--surface-1)", color: "var(--text-body)", border: "1px solid var(--border-hairline)", borderRadius: "var(--r-sm)" }}
              />
              {texts.length > 1 && (
                <button type="button" onClick={() => setTexts((previous) => previous.filter((_, partIndex) => partIndex !== index))}>
                  Remover esta parte
                </button>
              )}
            </div>
          ))}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button type="button" onClick={() => setTexts((previous) => [...previous, ""])} disabled={texts.length >= 25 || save.isPending}>
              Adicionar parte
            </button>
            <button type="submit" disabled={!valid || save.isPending}>
              {save.isPending ? "Salvando…" : "Salvar para os próximos horários elegíveis"}
            </button>
            <button type="button" onClick={onClose} disabled={save.isPending}>Fechar editor</button>
          </div>
          {save.isError && <p role="alert" style={{ color: "var(--negative)" }}>
            {save.error instanceof Error ? save.error.message : "Não foi possível salvar a revisão."}
          </p>}
          {savedAt && <p role="status" style={{ color: "var(--positive)" }}>
            Revisão registrada. Será usada somente para ocorrências após {formatUtcTimestampBrasilia(savedAt)}.
          </p>}
        </form>
      )}
      {latest.isError && <button type="button" onClick={onClose}>Fechar editor</button>}
    </section>
  )
}
