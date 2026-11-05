import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { productsApi, type ProductMedia } from "../../api/products"
import { Icon } from "../ui/Icon"
import { Modal } from "../ui/Modal"

interface ProductSavedPersonalizationProps {
  productId: number
  description: string | null | undefined
}

/** Visualização somente leitura, montada apenas quando o card do produto é expandido. */
export function ProductSavedPersonalization({ productId, description }: ProductSavedPersonalizationProps) {
  const [selected, setSelected] = useState<ProductMedia | null>(null)
  const mediaQuery = useQuery({
    queryKey: ["product-media", productId],
    queryFn: () => productsApi.media(productId),
    staleTime: 4 * 60 * 1000,
    retry: 1,
  })
  const items = mediaQuery.data?.items ?? []
  const imageCount = items.filter((item) => item.media_type === "IMAGE").length
  const videoCount = items.filter((item) => item.media_type === "VIDEO").length
  const savedCopy = description?.trim()

  return (
    <section aria-label="Personalização salva do produto" style={{ minWidth: 0 }}>
      <h3 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 14px", color: "var(--text-primary)" }}>
        Personalização salva
      </h3>

      <div style={{ padding: 12, border: "1px solid var(--border)", borderRadius: 12, marginBottom: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>
          <Icon name="file-text" size={15} /> Descrição para redes sociais
        </div>
        <p style={{ margin: 0, fontSize: 14, lineHeight: 1.55, whiteSpace: "pre-wrap", overflowWrap: "anywhere", color: savedCopy ? "var(--text-primary)" : "var(--text-muted)" }}>
          {savedCopy || "Nenhuma descrição personalizada foi salva."}
        </p>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 8, marginBottom: 10 }}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 13, fontWeight: 600 }}>
          <Icon name="image" size={16} /> Imagens e vídeos adicionais
        </div>
        {mediaQuery.isSuccess && (
          <span style={{ color: "var(--text-muted)", fontSize: 12 }}>
            {imageCount} {imageCount === 1 ? "imagem" : "imagens"} · {videoCount} {videoCount === 1 ? "vídeo" : "vídeos"}
          </span>
        )}
      </div>

      {mediaQuery.isPending && <p role="status" style={{ margin: "0 0 12px", fontSize: 13, color: "var(--text-muted)" }}>Carregando mídias salvas…</p>}
      {mediaQuery.isError && (
        <div role="alert" style={{ marginBottom: 12, fontSize: 13, color: "var(--text-secondary)" }}>
          Não foi possível carregar as mídias. <button type="button" onClick={() => { void mediaQuery.refetch() }} style={{ color: "var(--text-primary)", textDecoration: "underline", background: "none", border: 0, cursor: "pointer" }}>Tentar novamente</button>
        </div>
      )}
      {mediaQuery.isSuccess && items.length === 0 && (
        <p style={{ margin: 0, fontSize: 13, color: "var(--text-muted)" }}>
          Nenhuma imagem ou vídeo adicional foi enviado. A imagem original da Shopee continua no topo do card.
        </p>
      )}

      {mediaQuery.isSuccess && items.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(100px, 1fr))", gap: 10 }}>
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setSelected(item)}
              aria-label={`${item.media_type === "VIDEO" ? "Assistir vídeo" : "Ampliar imagem"}: ${item.file_name}`}
              title={item.file_name}
              style={{ minWidth: 0, padding: 7, border: "1px solid var(--border)", background: "var(--surface, #0d1420)", color: "var(--text-secondary)", borderRadius: 11, cursor: "pointer", textAlign: "left" }}
            >
              {item.media_type === "VIDEO" ? (
                <div style={{ position: "relative" }}>
                  <video src={item.preview_url} preload="metadata" muted playsInline style={{ display: "block", width: "100%", height: 86, objectFit: "cover", borderRadius: 7, pointerEvents: "none" }} />
                  <span style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", color: "white", pointerEvents: "none" }}><Icon name="eye" size={26} /></span>
                </div>
              ) : (
                <img src={item.preview_url} alt="" loading="lazy" style={{ display: "block", width: "100%", height: 86, objectFit: "cover", borderRadius: 7 }} />
              )}
              <span style={{ display: "block", marginTop: 6, fontSize: 11, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.file_name}</span>
            </button>
          ))}
        </div>
      )}

      <Modal open={selected !== null} onClose={() => setSelected(null)} title={selected?.file_name || "Prévia da mídia"} width={720}>
        {selected?.media_type === "VIDEO" ? (
          <video key={selected.id} src={selected.preview_url} controls playsInline preload="metadata" style={{ display: "block", maxWidth: "100%", width: "100%", maxHeight: "70vh", borderRadius: 10 }} />
        ) : selected ? (
          <img src={selected.preview_url} alt={selected.file_name} style={{ display: "block", maxWidth: "100%", width: "100%", maxHeight: "70vh", objectFit: "contain", borderRadius: 10 }} />
        ) : null}
      </Modal>
    </section>
  )
}
