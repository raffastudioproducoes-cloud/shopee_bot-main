import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useRef, useState } from "react"
import { productsApi, type ProductMedia } from "../../api/products"
import { Button } from "../ui/Button"
import { ProductMediaVisual } from "./ProductMediaVisual"
import "./productMediaManager.css"

const MAX_FILE_BYTES = 50 * 1024 * 1024
const RING_CIRCUMFERENCE = 2 * Math.PI * 40
type UploadPhase = "idle" | "sending" | "processing" | "success" | "error"

function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60)
  const remainder = String(seconds % 60).padStart(2, "0")
  return `${String(minutes).padStart(2, "0")}:${remainder}`
}

function processingNotice(seconds: number): string {
  if (seconds >= 120) return "O servidor ainda não confirmou a gravação. Se houver falha, confira a galeria antes de tentar novamente."
  if (seconds >= 60) return "O processamento está levando mais tempo que o habitual. Mantenha esta janela aberta."
  if (seconds >= 30) return "O servidor continua validando e preparando a mídia. Aguarde a confirmação."
  if (seconds >= 15) return "Arquivo recebido. A resposta do servidor ainda está pendente."
  return "Transferência concluída; aguardando validação, processamento e gravação segura."
}

export function ProductMediaManager({ productId }: { productId: number }) {
  const queryClient = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [activeFile, setActiveFile] = useState("")
  const [phase, setPhase] = useState<UploadPhase>("idle")
  const [processingStartedAt, setProcessingStartedAt] = useState<number | null>(null)
  const [processingSeconds, setProcessingSeconds] = useState(0)
  const [removingId, setRemovingId] = useState<string | null>(null)
  const [playingId, setPlayingId] = useState<string | null>(null)
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

  useEffect(() => {
    if (phase !== "processing" || processingStartedAt === null) return
    const updateElapsed = () => setProcessingSeconds(Math.max(0, Math.floor((Date.now() - processingStartedAt) / 1000)))
    updateElapsed()
    const interval = window.setInterval(updateElapsed, 1000)
    return () => window.clearInterval(interval)
  }, [phase, processingStartedAt])

  useEffect(() => {
    if (phase !== "success") return
    const timeout = window.setTimeout(() => setPhase("idle"), 2400)
    return () => window.clearTimeout(timeout)
  }, [phase])

  const uploadNotice = phase === "processing" ? processingNotice(processingSeconds)
    : phase === "sending" ? "Porcentagem real dos bytes enviados. A validação no servidor acontece depois."
      : phase === "success" ? "Mídia confirmada e salva na galeria do produto."
        : "A gravação não foi confirmada. Confira a galeria antes de reenviar, caso a transferência tenha terminado."

  const handleUpload = async (files: FileList | null) => {
    if (!files?.length || uploading) return
    const selected = Array.from(files)
    const totalBytes = Math.max(1, selected.reduce((sum, file) => sum + file.size, 0))
    setError("")
    setMessage("")
    setUploading(true)
    setUploadProgress(0)
    setPhase("sending")
    setProcessingStartedAt(null)
    setProcessingSeconds(0)
    let transferredCurrentFile = false
    try {
      let imageCount = images.length
      let videoCount = videos.length
      let sentBytes = 0
      for (const [index, file] of selected.entries()) {
        setActiveFile(`${index + 1}/${selected.length} · ${file.name}`)
        transferredCurrentFile = false
        setPhase("sending")
        setProcessingStartedAt(null)
        setProcessingSeconds(0)
        const isVideo = file.type === "video/mp4" || file.name.toLowerCase().endsWith(".mp4")
        const isImage = /^(image\/(jpeg|png|gif|webp))$/.test(file.type)
        if (!isVideo && !isImage) throw new Error("Aceitamos imagens JPG/PNG/GIF/WebP e vídeos MP4.")
        if (!file.size) throw new Error("O arquivo está vazio.")
        if (file.size > MAX_FILE_BYTES) throw new Error("Cada arquivo deve ter até 50 MB.")
        if (isVideo ? videoCount >= 2 : imageCount >= 5) {
          throw new Error(isVideo ? "O limite de 2 vídeos foi atingido." : "O limite de 5 imagens foi atingido.")
        }
        await productsApi.uploadMedia(productId, file, (loaded, total) => {
          const fraction = Math.min(1, Math.max(0, loaded / total))
          setUploadProgress(Math.min(100, Math.round(100 * (sentBytes + file.size * fraction) / totalBytes)))
        }, () => {
          transferredCurrentFile = true
          setProcessingStartedAt(Date.now())
          setProcessingSeconds(0)
          setPhase("processing")
        })
        sentBytes += file.size
        setUploadProgress(Math.min(100, Math.round(100 * sentBytes / totalBytes)))
        if (isVideo) videoCount++
        else imageCount++
        await queryClient.invalidateQueries({ queryKey })
      }
      setMessage("Mídia salva no produto. Ela permanece disponível quando você voltar.")
      setPhase("success")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível enviar a mídia.")
      setPhase("error")
      if (!transferredCurrentFile) setProcessingStartedAt(null)
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
    setPhase("idle")
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
      {phase !== "idle" && (
        <div className={`product-media-upload-stage product-media-upload-stage--${phase}`}>
          <div className="product-media-upload-stage__preview">
            {(phase === "sending" || phase === "processing") && <span className="product-media-upload-stage__skeleton" aria-hidden="true" />}
            <div className="product-media-upload-stage__ring" role="progressbar"
              aria-label="Porcentagem de transferência de imagens e vídeos"
              aria-valuemin={0} aria-valuemax={100} aria-valuenow={uploadProgress}>
              <svg viewBox="0 0 100 100" aria-hidden="true">
                <circle className="track" cx="50" cy="50" r="40" />
                <circle className="value" cx="50" cy="50" r="40"
                  strokeDasharray={RING_CIRCUMFERENCE}
                  strokeDashoffset={RING_CIRCUMFERENCE * (1 - uploadProgress / 100)} />
              </svg>
              <strong>{uploadProgress}%</strong>
            </div>
          </div>
          <div className="product-media-upload-stage__details">
            <strong role="status" aria-live="polite">{phase === "processing" ? "Transferido; processando mídia…"
              : phase === "sending" ? "Enviando imagem ou vídeo…"
                : phase === "success" ? "Upload concluído com sucesso" : "Falha no envio ou processamento"}</strong>
            <span>{activeFile}</span>
            {processingStartedAt !== null && <span className="product-media-upload-stage__elapsed" aria-live="off">
              Tempo de processamento: <b>{formatDuration(processingSeconds)}</b>
            </span>}
            {phase === "processing" && (
              <div className="product-media-upload-stage__processing-track" aria-label="Processamento em andamento">
                <span />
              </div>
            )}
            <small role="status" aria-live="polite">{uploadNotice}</small>
            {phase === "error" && error && <small role="alert" className="product-media-upload-stage__error">{error}</small>}
            {phase === "error" && <Button type="button" variant="ghost" size="sm" icon="refresh-cw"
              loading={mediaQuery.isFetching} onClick={() => { void queryClient.invalidateQueries({ queryKey }) }}>
              Atualizar galeria para conferir
            </Button>}
          </div>
        </div>
      )}
      {mediaQuery.isLoading && <p style={{ fontSize: 13 }}>Carregando galeria…</p>}
      {mediaQuery.isError && <p role="alert" style={{ color: "#fb7185", fontSize: 13 }}>Falha ao abrir a galeria.</p>}
      {error && phase !== "error" && <p role="alert" style={{ color: "#fb7185", fontSize: 13 }}>{error}</p>}
      {message && phase !== "success" && <p role="status" style={{ color: "#83dfad", fontSize: 13 }}>{message}</p>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(110px, 1fr))", gap: 10, marginTop: 10 }}>
        {items.map((item) => (
          <div key={item.id} style={{ minWidth: 0, padding: 8, borderRadius: 12, border: "1px solid var(--border)", overflow: "hidden" }}>
            {playingId === item.id && item.media_type === "VIDEO" ? (
              <div className="product-media-card__visual">
                <video src={item.preview_url} controls autoPlay playsInline preload="metadata" />
                <button type="button" className="product-media-card__close" aria-label="Fechar vídeo"
                  onClick={() => setPlayingId(null)}>×</button>
              </div>
            ) : (
              <ProductMediaVisual item={item} className="product-media-card__visual"
                onPlay={item.media_type === "VIDEO" ? () => setPlayingId(item.id) : undefined} />
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
