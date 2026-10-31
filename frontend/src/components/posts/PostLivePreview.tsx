import { useEffect, useState } from "react"
import {
  Bookmark, ChevronLeft, ChevronRight, Eye, Heart, MessageCircle,
  MoreHorizontal, Music2, Play, Repeat2, Share2, X,
} from "lucide-react"
import type { Product } from "../../api/products"
import type { PostMedia, PostNetwork } from "../../api/posts"
import type { MediaInfo } from "../../lib/networkLimits"
import { planMediaComposition } from "../../lib/mediaComposition"
import { NetworkLogo, PICKER_NETWORKS } from "./NetworkPicker"
import "./postLivePreview.css"

interface FileSelection { file: File; info: MediaInfo }
interface PreviewMedia { key: string; name: string; url: string; kind: "image" | "video" }
type PreviewNetwork = PostNetwork | "kwai"
const PREVIEW_NETWORKS: PreviewNetwork[] = [...PICKER_NETWORKS, "kwai"]
const NAMES: Record<PreviewNetwork, string> = {
  threads: "Threads", x: "X", facebook: "Facebook", instagram: "Instagram",
  tiktok: "TikTok", kwai: "Kwai",
}
const DEMO_HANDLE = "@seu_perfil"

interface PostLivePreviewProps {
  networks: PostNetwork[]
  textFor: (network: PostNetwork) => string[]
  files: FileSelection[]
  productPhotos: Product[]
  products: Product[]
  existingMedia?: PostMedia[]
  onClose: () => void
}

function PreviewActions({ vertical = false, facebook = false }: { vertical?: boolean; facebook?: boolean }) {
  return <div className={"post-preview-actions" + (vertical ? " is-vertical" : "")} aria-label="Controles ilustrativos da rede social">
    <span><Heart size={20} aria-hidden="true" />{facebook ? "Curtir" : ""}</span>
    <span><MessageCircle size={20} aria-hidden="true" />{facebook ? "Comentar" : ""}</span>
    {!facebook && <span><Repeat2 size={19} aria-hidden="true" /></span>}
    <span><Share2 size={19} aria-hidden="true" />{facebook ? "Compartilhar" : ""}</span>
    {!vertical && !facebook && <span className="post-preview-bookmark"><Bookmark size={19} aria-hidden="true" /></span>}
  </div>
}

function PreviewMediaBlock({ item, vertical, instagram, index, count, previous, next }: {
  item?: PreviewMedia; vertical?: boolean; instagram?: boolean; index: number; count: number;
  previous: () => void; next: () => void;
}) {
  return <div className={"post-preview-media" + (vertical ? " is-portrait" : instagram ? " is-instagram" : "")}>
    {!item && <div className="post-preview-empty-media">
      <Eye size={28} aria-hidden="true" />
      <span>Adicione uma foto ou vídeo para visualizar aqui</span>
    </div>}
    {item?.kind === "image" && <img src={item.url} alt={"Prévia da imagem " + item.name}
      loading="lazy" referrerPolicy="no-referrer" />}
    {item?.kind === "video" && <video src={item.url} controls playsInline preload="metadata"
      aria-label={"Prévia do vídeo " + item.name} />}
    {item?.kind === "video" && <span className="post-preview-video-badge"><Play size={12} aria-hidden="true" /> Vídeo</span>}
    {count > 1 && <div className="post-preview-carousel-controls">
      <button type="button" aria-label="Mídia anterior" onClick={previous}><ChevronLeft size={18} /></button>
      <span>{index + 1} / {count}</span>
      <button type="button" aria-label="Próxima mídia" onClick={next}><ChevronRight size={18} /></button>
    </div>}
  </div>
}

export function PostLivePreview({
  networks, textFor, files, productPhotos, products, existingMedia = [], onClose,
}: PostLivePreviewProps) {
  const [network, setNetwork] = useState<PreviewNetwork>(networks[0] ?? "instagram")
  const [mediaIndex, setMediaIndex] = useState(0)
  const [local, setLocal] = useState<PreviewMedia[]>([])

  useEffect(() => {
    const urls = files.map(({ file, info }, index) => ({
      key: "file-" + index, name: info.name,
      url: URL.createObjectURL(file), kind: info.kind === "video" ? "video" as const : "image" as const,
    }))
    setLocal(urls)
    return () => urls.forEach((item) => URL.revokeObjectURL(item.url))
  }, [files])

  useEffect(() => {
    if (networks.length && !networks.includes(network as PostNetwork)) setNetwork(networks[0])
  }, [networks, network])

  const productMedia: PreviewMedia[] = productPhotos.filter((p) => p.image).map((p) => ({
    key: "product-" + p.id, name: "shopee-" + p.id + ".jpg",
    url: p.image!, kind: "image",
  }))
  const media = [...local, ...productMedia]
  const info = [
    ...files.map(({ info: fileInfo }) => fileInfo),
    ...productMedia.map((m) => ({ name: m.name, size: 1, kind: "image" as const })),
  ]
  const plan = network === "kwai" ? null : planMediaComposition(network, {
    texts: textFor(network), media: info, productCount: products.length,
  })
  const allowedNames = new Set(plan?.media.map((m) => m.name) ?? [])
  const visibleMedia = network === "kwai" ? media : media.filter((m) => allowedNames.has(m.name))
  const chosenIndex = Math.min(mediaIndex, Math.max(0, visibleMedia.length - 1))
  const chosen = visibleMedia[chosenIndex]
  const caption = network === "kwai" ? (networks[0] ? textFor(networks[0])[0] : "")
    : (textFor(network)[0] ?? "")
  const text = caption.trim() || "Seu texto aparecerá aqui conforme você preencher o editor."
  const isVideo = chosen?.kind === "video"
  const isVertical = network === "tiktok" || network === "kwai" || (network === "instagram" && isVideo)
  const showProductName = products.length > 0

  return <aside className="post-live-preview" aria-label="Pré-visualização da publicação">
    <header className="post-preview-heading">
      <div><strong>Visualização da postagem</strong><span>Simulação · atualiza enquanto você edita</span></div>
      <button type="button" aria-label="Fechar visualização" onClick={onClose}><X size={20} /></button>
    </header>
    <div className="post-preview-tabs" role="tablist" aria-label="Prévia por rede social">
      {PREVIEW_NETWORKS.map((item) => <button key={item} type="button" role="tab"
        aria-selected={network === item} className={network === item ? "is-selected" : ""}
        onClick={() => { setNetwork(item); setMediaIndex(0) }}>
        <NetworkLogo network={item} size={18} />
        <span>{NAMES[item]}</span>
      </button>)}
    </div>
    <div className="post-preview-stage">
      <div className="post-preview-stage-top">
        <span><NetworkLogo network={network} size={16} /> {NAMES[network]} · {isVertical ? "Vídeo vertical" : "Feed"}</span>
        {network !== "kwai" && !networks.includes(network) && <small>Rede não selecionada</small>}
        {network === "kwai" && <small>Publicação ainda indisponível</small>}
      </div>
      <div className={"post-preview-social is-" + network + (isVertical ? " is-video-layout" : "")}>
        {isVertical ? <>
          <div className="post-preview-vertical-player">
            <PreviewMediaBlock item={chosen} index={chosenIndex} count={visibleMedia.length}
              previous={() => setMediaIndex((chosenIndex + visibleMedia.length - 1) % visibleMedia.length)}
              next={() => setMediaIndex((chosenIndex + 1) % visibleMedia.length)} vertical />
            <div className="post-preview-vertical-overlay">
              <strong>{DEMO_HANDLE}</strong>
              <p>{text}</p>
              {isVideo && <span><Music2 size={14} aria-hidden="true" /> Som original</span>}
            </div>
            <PreviewActions vertical />
          </div>
        </> : <>
          <div className="post-preview-author">
            <span className="post-preview-avatar" aria-hidden="true">AO</span>
            <div><strong>{network === "facebook" ? "Sua Página" : DEMO_HANDLE}</strong>
              <small>{network === "facebook" ? "Agora · Público" : "Agora"}</small></div>
            <MoreHorizontal size={19} aria-hidden="true" />
          </div>
          {(network === "threads" || network === "x" || network === "facebook") &&
            <p className="post-preview-caption is-before">{text}</p>}
          {(visibleMedia.length > 0 || network === "instagram") &&
            <PreviewMediaBlock item={chosen} index={chosenIndex} count={visibleMedia.length}
              previous={() => setMediaIndex((chosenIndex + visibleMedia.length - 1) % visibleMedia.length)}
              next={() => setMediaIndex((chosenIndex + 1) % visibleMedia.length)} instagram={network === "instagram"} />}
          <PreviewActions facebook={network === "facebook"} />
          {network === "instagram" &&
            <p className="post-preview-caption is-after"><strong>{DEMO_HANDLE}</strong> {text}</p>}
          {network === "facebook" && <div className="post-preview-comment-row">Escreva um comentário…</div>}
          {network === "threads" && <div className="post-preview-reply-row">Responder ao post…</div>}
          {network === "x" && <div className="post-preview-reply-row">Postar sua resposta</div>}
        </>}
      </div>
      {plan?.mode === "blocked" && <p className="post-preview-warning" role="status">
        Esta composição não poderá ser publicada em {NAMES[network]}: {plan.blockedReason}
      </p>}
      {plan?.mode === "text_only" && media.length > 0 && <p className="post-preview-warning" role="status">
        Esta rede publicará apenas o texto: as mídias atuais não são compatíveis.
      </p>}
      {existingMedia.length > 0 && media.length === 0 && <p className="post-preview-note">
        Mídia já salva neste post: {existingMedia.map((m) => m.file_name).join(", ")}. A miniatura não está disponível nesta edição.
      </p>}
      {showProductName && <p className="post-preview-note">
        Produto vinculado: {products.map((p) => p.name).join(", ")}. O nome só aparece na postagem se estiver no texto.
      </p>}
      <p className="post-preview-disclaimer">
        Prévia aproximada. Interfaces e recortes variam por dispositivo e podem mudar nas redes.
        Ícones de interação são ilustrativos; a mídia enviada segue as regras de cada plataforma.
      </p>
    </div>
  </aside>
}
