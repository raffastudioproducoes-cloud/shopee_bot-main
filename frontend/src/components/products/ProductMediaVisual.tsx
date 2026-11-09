import { useState } from "react"
import type { ProductMedia } from "../../api/products"
import { Icon } from "../ui/Icon"
import "./productMediaVisual.css"

/** Thumbnail of a previously stored asset. Videos use a real server-side JPG frame. */
export function ProductMediaVisual({ item, className = "", onPlay }: {
  item: ProductMedia
  className?: string
  onPlay?: () => void
}) {
  const [failed, setFailed] = useState(false)
  const [ready, setReady] = useState(false)
  const source = item.media_type === "VIDEO" ? item.thumbnail_url : item.preview_url
  return (
    <div className={`product-media-visual ${className}`}>
      {!ready && !failed && <span className="product-media-visual__skeleton" aria-hidden="true" />}
      {failed || !source ? (
        <span className="product-media-visual__fallback">
          <Icon name={item.media_type === "VIDEO" ? "film" : "image"} size={22} />
          <small>{item.media_type === "VIDEO" ? "Vídeo salvo" : "Imagem indisponível"}</small>
        </span>
      ) : (
        <img src={source} alt={item.media_type === "VIDEO" ? `Miniatura do vídeo ${item.file_name}` : item.file_name}
          loading="lazy" onLoad={() => setReady(true)} onError={() => setFailed(true)} />
      )}
      {item.media_type === "VIDEO" && (
        onPlay ? (
          <button type="button" className="product-media-visual__play" onClick={onPlay}
            aria-label={`Reproduzir ${item.file_name}`}><Icon name="play" size={18} /></button>
        ) : <span className="product-media-visual__play product-media-visual__play--decorative" aria-hidden="true">
          <Icon name="play" size={18} />
        </span>
      )}
    </div>
  )
}
