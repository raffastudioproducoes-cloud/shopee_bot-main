import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useRef, useState } from "react"
import { productsApi, type ProductMedia } from "../../api/products"
import { Button } from "../ui/Button"

const MAX_FILE_BYTES = 50 * 1024 * 1024

export function ProductMediaManager({ productId }: { productId: number }) {
  const queryClient = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [removingId, setRemovingId] = useState<string | null>(null)
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")

  const queryKey = ["product-media", productId] as const
  const mediaQuery = useQuery({
    queryKey,
    queryFn: () => productsApi.media(productId),
    staleTime: 4 * 60 * 1000,
  })
  const items = mediaQuery.data?.items ?? []
  const images = items.filter((item) => item.media_type === "IMAGE")
  const videos = items.filter((item) => item.media_type === "VIDEO")

  const handleUpload = async (files: FileList | null) => {
    if (!files?.length || uploading) return
    setError("")
    setMessage("")
    setUploading(true)
    try {
      let imageCount = images.length
      let videoCount = videos.length
      for (const file of Array.from(files)) {
        const isVideo = file.type === "video/mp4" || file.name.toLowerCase().endsWith(".mp4")
        const isImage = /^(image\/(jpeg|png|gif|webp))$/.test(file.type)
        if (!isVideo && !isImage) throw new Error("Aceitamos imagens JPG/PNG/GIF/WebP e vídeos MP4.")
        if (file.size > MAX_FILE_BYTES) throw new Error("Cada arquivo deve ter até 50 MB.")
        if (isVideo ? videoCount >= 2 : imageCount >= 5) {
          throw new Error(isVideo ? "O limite de 2 vídeos foi atingido." : "O limite de 5 imagens foi atingido.")
        }
        await productsApi.uploadMedia(productId, file)
        if (isVideo) videoCount++
        else imageCount++
        await queryClient.invalidateQueries({ queryKey })
      }
      setMessage("Mídia salva no produto. Ela permanece disponível quando você voltar.")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível enviar a mídia.")
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ""
      await queryClient.invalidateQueries({ queryKey })
    }
  }

  const handleRemove = async (item: ProductMedia) => {
    if (!window.confirm(`Remover "${item.file_name}" deste produto?`)) return
    setRemovingId(item.id)
    setError("")
    setMessage("")
    try {
      await productsApi.deleteMedia(productId, item.id)
      await queryClient.invalidateQueries({ queryKey })
      setMessage("Arquivo removido da galeria.")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível remover o arquivo.")
    } finally {
      setRemovingId(null)
    }
  }

  return (
    <section aria-label="Galeria do produto" style={{ marginTop: 18 }}>
      <h3 style={{ fontSize: 16, marginBottom: 4 }}>Imagens e vídeos do produto</h3>
      <p style={{ color: "var(--text-muted)", fontSize: 13, margin: "0 0 12px" }}>
        Até 5 imagens adicionais ({images.length}/5) e 2 vídeos ({videos.length}/2), além da imagem Shopee.
      </p>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept="image/jpeg,image/png,image/gif,image/webp,video/mp4"
        disabled={uploading || (images.length >= 5 && videos.length >= 2)}
        aria-label="Selecionar imagens ou vídeos do computador ou celular"
        onChange={(event) => { void handleUpload(event.target.files) }}
        style={{ display: "none" }}
      />
      <Button
        type="button"
        variant="secondary"
        icon="upload"
        loading={uploading}
        disabled={uploading || (images.length >= 5 && videos.length >= 2)}
        onClick={() => inputRef.current?.click()}
        style={{ marginBottom: 10 }}
      >
        {uploading ? "Enviando arquivos…" : "Selecionar imagens ou vídeos"}
      </Button>
      <p style={{ color: "var(--text-muted)", fontSize: 12, margin: "0 0 8px" }}>
        JPG, PNG, GIF, WebP ou MP4, até 50 MB por arquivo. O envio salva os arquivos imediatamente.
      </p>
      {uploading && <p aria-live="polite" style={{ fontSize: 13 }}>Enviando e validando mídia…</p>}
      {mediaQuery.isLoading && <p style={{ fontSize: 13 }}>Carregando galeria…</p>}
      {mediaQuery.isError && <p role="alert" style={{ color: "#fb7185", fontSize: 13 }}>Falha ao abrir a galeria.</p>}
      {error && <p role="alert" style={{ color: "#fb7185", fontSize: 13 }}>{error}</p>}
      {message && <p role="status" style={{ color: "#83dfad", fontSize: 13 }}>{message}</p>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(110px, 1fr))", gap: 10, marginTop: 10 }}>
        {items.map((item) => (
          <div key={item.id} style={{ minWidth: 0, padding: 8, borderRadius: 12, border: "1px solid var(--border)", overflow: "hidden" }}>
            {item.media_type === "VIDEO" ? (
              <video src={item.preview_url} controls preload="metadata" style={{ width: "100%", height: 76, objectFit: "cover", borderRadius: 8 }} />
            ) : (
              <img src={item.preview_url} alt={item.file_name} loading="lazy" style={{ width: "100%", height: 76, objectFit: "cover", borderRadius: 8 }} />
            )}
            <div title={item.file_name} style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginTop: 5, fontSize: 11 }}>{item.file_name}</div>
            <button type="button" disabled={uploading || removingId === item.id} onClick={() => { void handleRemove(item) }}
              aria-label={`Remover ${item.file_name}`}
              style={{ width: "100%", marginTop: 6, borderRadius: 8, padding: "6px 4px", border: "1px solid var(--border)", background: "transparent", color: "var(--text-secondary)", cursor: "pointer", fontSize: 12 }}>
              {removingId === item.id ? "Removendo…" : "Remover"}
            </button>
          </div>
        ))}
      </div>
    </section>
  )
}
