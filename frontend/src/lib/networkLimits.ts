// Regras de publicação por rede — tabela ÚNICA do front. Espelhada em
// api/network_limits.py (o servidor recusa o que passar daqui); mudou um
// número aqui, mude lá também (tests/api/test_network_limits.py cobre o lado
// servidor).
//
// Fontes oficiais consultadas em 2026-10-07:
//  threads:   https://developers.facebook.com/docs/threads/posts
//             https://developers.facebook.com/docs/threads/overview
//  x:         https://docs.x.com/resources/fundamentals/counting-characters
//             https://docs.x.com/x-api/posts/create-post  (4 fotos OU 1 GIF OU 1 vídeo)
//             https://docs.x.com/x-api/media/quickstart/media-upload-chunked (tamanhos)
//  facebook:  https://developers.facebook.com/docs/graph-api/reference/page/photos (4 MB, formatos)
//             https://developers.facebook.com/docs/video-api/guides/reels-publishing (vídeo 3–90 s)
//  instagram: https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media
//  tiktok:    https://developers.tiktok.com/doc/content-posting-api-reference-direct-post (título 2200)
//             https://developers.tiktok.com/doc/content-posting-api-media-transfer-guide (vídeo)
//
// `unverified` lista as chaves que NÃO estão na doc oficial (ou cuja doc
// cobre outro formato): violá-las vira aviso suave, não bloqueio.

import type { PostNetwork } from "../api/posts"

export type MediaKind = "image" | "gif" | "video"
export type DeliveredMediaMode = "none" | "single_image" | "carousel" | "video" | "text_only"

export interface MediaInfo {
  name: string
  size: number
  kind: MediaKind
  width?: number
  height?: number
  durationSec?: number
}

export interface NetworkRule {
  label: string
  maxChars: number
  /** A API permite publicar texto sem arquivo de mídia. */
  supportsTextOnly: boolean
  /** Modos que o publicador deste aplicativo realmente entrega hoje. */
  deliveredModes: DeliveredMediaMode[]
  /** "weighted" = contagem do X (URL = 23, emoji/CJK = 2); "utf16" = TikTok. */
  charCount: "codepoints" | "weighted" | "utf16"
  /** true = cada parte vira resposta (thread); senão só a 1ª parte sai. */
  threadParts: boolean
  maxLinks?: number
  maxHashtags?: number
  maxMentions?: number
  maxMedia?: number
  maxImages?: number
  maxGifs?: number
  maxVideos?: number
  allowMix?: boolean
  /** "media-or-product": a foto do produto supre (publicador do Instagram). */
  requiresMedia?: "media-or-product" | "video"
  exts: string[]
  maxBytes: Partial<Record<MediaKind, number>>
  videoMinSec?: number
  videoMaxSec?: number
  videoMinSide?: number
  videoMaxSide?: number
  imageAspect?: [number, number]
  videoAspect?: [number, number]
  unverified: string[]
}

const MB = 1024 * 1024
const GB = 1024 * MB

export const NETWORK_RULES: Record<PostNetwork, NetworkRule> = {
  threads: {
    label: "Threads",
    maxChars: 500,
    supportsTextOnly: true,
    deliveredModes: ["none", "single_image", "carousel", "video", "text_only"],
    charCount: "codepoints",
    threadParts: true,
    maxLinks: 5,
    maxHashtags: 1, // "Only one topic tag is allowed per post"
    maxMedia: 20, // carrossel 2–20
    allowMix: true,
    exts: ["jpg", "jpeg", "png", "mp4"],
    maxBytes: { image: 8 * MB, video: 1 * GB },
    videoMaxSec: 300,
    videoMaxSide: 1920,
    unverified: [],
  },
  x: {
    label: "X",
    maxChars: 280,
    supportsTextOnly: true,
    deliveredModes: ["none", "text_only"],
    charCount: "weighted",
    threadParts: true,
    maxImages: 4,
    maxGifs: 1,
    maxVideos: 1,
    allowMix: false,
    exts: ["jpg", "jpeg", "png", "webp", "gif", "mp4"],
    maxBytes: { image: 5 * MB, gif: 15 * MB, video: 8 * GB },
    videoMaxSec: 1200,
    // formatos de imagem: a página de boas práticas de mídia do X devolveu
    // 402 na consulta — não confirmado.
    unverified: ["exts"],
  },
  facebook: {
    label: "Facebook",
    maxChars: 63206,
    supportsTextOnly: true,
    deliveredModes: ["none", "single_image", "carousel", "text_only"],
    charCount: "codepoints",
    threadParts: false,
    // Álbum: só fotos; GIF e vídeo não se misturam a elas (attached_media).
    maxGifs: 1,
    maxVideos: 1,
    allowMix: false,
    exts: ["jpg", "jpeg", "png", "gif", "mp4"],
    maxBytes: { image: 4 * MB, gif: 4 * MB },
    videoMinSec: 3,
    videoMaxSec: 90,
    // 63.206 não aparece na doc da Graph API; 3–90 s é a spec de Reels
    // (vídeo comum no feed pode ser maior).
    unverified: ["maxChars", "videoMinSec", "videoMaxSec"],
  },
  instagram: {
    label: "Instagram",
    maxChars: 2200,
    supportsTextOnly: false,
    deliveredModes: ["single_image"],
    charCount: "codepoints",
    threadParts: false,
    maxHashtags: 30,
    maxMentions: 20,
    maxMedia: 10,
    allowMix: true,
    requiresMedia: "media-or-product",
    exts: ["jpg", "jpeg", "mp4"],
    maxBytes: { image: 8 * MB, video: 300 * MB },
    imageAspect: [0.8, 1.91],
    videoMinSec: 3,
    videoMaxSec: 900,
    videoMaxSide: 1920,
    videoAspect: [0.01, 10],
    unverified: [],
  },
  tiktok: {
    label: "TikTok",
    maxChars: 2200,
    supportsTextOnly: false,
    deliveredModes: ["video"],
    charCount: "utf16",
    threadParts: false,
    // A API aceita fotos (até 35), mas o publicador deste app só envia vídeo.
    maxImages: 0,
    maxGifs: 0,
    maxVideos: 1,
    allowMix: false,
    requiresMedia: "video",
    exts: ["mp4"],
    maxBytes: { video: 4 * GB },
    videoMaxSec: 600, // limite da API; o criador pode ter limite menor
    videoMinSide: 360,
    videoMaxSide: 4096,
    unverified: [],
  },
}

const URL_RE = /https?:\/\/\S+|www\.\S+/gi
const HASHTAG_RE = /#[\p{L}\p{N}_]+/gu
const MENTION_RE = /@[\p{L}\p{N}_.]+/gu

const count = (text: string, re: RegExp) => (text.match(re) ?? []).length

// Pesos do twitter-text (config v3): estas faixas pesam 1, o resto 2.
const X_LIGHT: [number, number][] = [
  [0, 4351],
  [8192, 8205],
  [8208, 8223],
  [8242, 8247],
]

export function textLength(rule: NetworkRule, text: string): number {
  if (rule.charCount === "utf16") return text.length
  if (rule.charCount === "codepoints") return [...text].length
  let total = count(text, URL_RE) * 23
  for (const ch of text.replace(URL_RE, "")) {
    const cp = ch.codePointAt(0)!
    total += X_LIGHT.some(([a, b]) => cp >= a && cp <= b) ? 1 : 2
  }
  return total
}

export function mediaKind(name: string): MediaKind {
  const ext = name.split(".").pop()?.toLowerCase() ?? ""
  return ext === "mp4" ? "video" : ext === "gif" ? "gif" : "image"
}

export interface Issue {
  key: string
  level: "error" | "warn"
  message: string
}

const KIND_LABEL: Record<MediaKind, string> = { image: "imagem", gif: "GIF", video: "vídeo" }
const fmtBytes = (b: number) => (b >= GB ? `${b / GB} GB` : `${Math.round(b / MB)} MB`)

export interface PostDraft {
  texts: string[]
  media: MediaInfo[]
  productCount: number
}

export function validateForNetwork(network: PostNetwork, draft: PostDraft): Issue[] {
  const rule = NETWORK_RULES[network]
  const issues: Issue[] = []
  const add = (key: string, message: string) => {
    const soft = rule.unverified.includes(key)
    issues.push({
      key,
      level: soft ? "warn" : "error",
      message: `${rule.label}: ${message}${soft ? " (limite não confirmado)" : ""}`,
    })
  }

  const texts = rule.threadParts ? draft.texts : draft.texts.slice(0, 1)
  texts.forEach((text, i) => {
    const where = texts.length > 1 ? ` na parte ${i + 1}` : ""
    const len = textLength(rule, text)
    if (len > rule.maxChars) add("maxChars", `texto máx. ${rule.maxChars} caracteres${where} (você tem ${len})`)
    const links = count(text, URL_RE)
    if (rule.maxLinks != null && links > rule.maxLinks) add("maxLinks", `máx. ${rule.maxLinks} links${where} (você tem ${links})`)
    const tags = count(text, HASHTAG_RE)
    if (rule.maxHashtags != null && tags > rule.maxHashtags) add("maxHashtags", `máx. ${rule.maxHashtags} hashtag(s)${where} (você tem ${tags})`)
    const mentions = count(text, MENTION_RE)
    if (rule.maxMentions != null && mentions > rule.maxMentions) add("maxMentions", `máx. ${rule.maxMentions} @menções${where} (você tem ${mentions})`)
  })
  if (!rule.threadParts && draft.texts.length > 1) {
    issues.push({ key: "threadParts", level: "warn", message: `${rule.label}: só a 1ª parte é publicada (sem thread)` })
  }

  const media = draft.media
  const byKind = (k: MediaKind) => media.filter((m) => m.kind === k).length
  if (rule.requiresMedia === "video" && byKind("video") === 0) add("requiresMedia", "exige 1 vídeo (.mp4)")
  if (rule.requiresMedia === "media-or-product" && media.length === 0 && draft.productCount === 0) {
    add("requiresMedia", "exige imagem/vídeo (ou um produto com foto)")
  }
  if (rule.maxMedia != null && media.length > rule.maxMedia) add("maxMedia", `máx. ${rule.maxMedia} mídias (você tem ${media.length})`)
  const caps: [MediaKind, number | undefined][] = [
    ["image", rule.maxImages],
    ["gif", rule.maxGifs],
    ["video", rule.maxVideos],
  ]
  for (const [k, max] of caps) {
    const n = byKind(k)
    if (max != null && n > max) {
      add(`max_${k}`, max === 0 ? `não aceita ${KIND_LABEL[k]}` : `máx. ${max} ${KIND_LABEL[k]}(s) (você tem ${n})`)
    }
  }
  if (rule.allowMix === false && new Set(media.map((m) => m.kind)).size > 1) {
    add("allowMix", "não mistura imagem, GIF e vídeo no mesmo post")
  }

  for (const m of media) {
    const ext = m.name.split(".").pop()?.toLowerCase() ?? ""
    if (!rule.exts.includes(ext)) {
      add("exts", `não aceita .${ext} (${m.name}); use ${rule.exts.map((e) => "." + e).join(", ")}`)
      continue
    }
    const maxB = rule.maxBytes[m.kind]
    if (maxB != null && m.size > maxB) add("maxBytes", `${m.name} passa de ${fmtBytes(maxB)}`)
    if (m.kind === "video" && m.durationSec != null) {
      const d = Math.round(m.durationSec)
      if (rule.videoMaxSec != null && m.durationSec > rule.videoMaxSec) add("videoMaxSec", `vídeo máx. ${rule.videoMaxSec} s (o seu tem ${d} s)`)
      if (rule.videoMinSec != null && m.durationSec < rule.videoMinSec) add("videoMinSec", `vídeo mín. ${rule.videoMinSec} s (o seu tem ${d} s)`)
    }
    if (m.width && m.height) {
      const dims = `${m.width}×${m.height}`
      if (m.kind === "video" && rule.videoMaxSide != null && Math.max(m.width, m.height) > rule.videoMaxSide) {
        add("videoMaxSide", `vídeo máx. ${rule.videoMaxSide}px (o seu tem ${dims})`)
      }
      if (m.kind === "video" && rule.videoMinSide != null && Math.min(m.width, m.height) < rule.videoMinSide) {
        add("videoMinSide", `vídeo mín. ${rule.videoMinSide}px (o seu tem ${dims})`)
      }
      const aspect = m.width / m.height
      const range = m.kind === "video" ? rule.videoAspect : rule.imageAspect
      if (range && (aspect < range[0] || aspect > range[1])) {
        add(
          m.kind === "video" ? "videoAspect" : "imageAspect",
          `proporção de ${m.name} fora de ${range[0]}:1 a ${range[1]}:1 (atual ${aspect.toFixed(2)}:1)`,
        )
      }
    }
  }
  return issues
}

/** Lê duração/dimensões no navegador (sem upload). Falhou = sem metadados. */
export function readMediaInfo(file: File): Promise<MediaInfo> {
  const base: MediaInfo = { name: file.name, size: file.size, kind: mediaKind(file.name) }
  const url = URL.createObjectURL(file)
  const done = (extra: Partial<MediaInfo>) => {
    URL.revokeObjectURL(url)
    return { ...base, ...extra }
  }
  return new Promise((resolve) => {
    if (base.kind === "video") {
      const v = document.createElement("video")
      v.preload = "metadata"
      v.onloadedmetadata = () => resolve(done({ durationSec: v.duration, width: v.videoWidth, height: v.videoHeight }))
      v.onerror = () => resolve(done({}))
      v.src = url
    } else {
      const img = new Image()
      img.onload = () => resolve(done({ width: img.naturalWidth, height: img.naturalHeight }))
      img.onerror = () => resolve(done({}))
      img.src = url
    }
  })
}

// ── Textos por faixa de limite (espelho de api/text_variants.py) ─────────────
// Conjunto MÍNIMO de textos que atende as redes marcadas: redes com o mesmo
// limite efetivo compartilham um texto; cada faixa diferente ganha o seu.

/** Teto de uma copy de vendas: o Facebook aceita 63 mil, não precisa. */
export const PRACTICAL_MAX_CHARS = 2200

export interface TextVariantPlan {
  /** Mesmo `key` que o backend devolve em /posts/generate-copy. */
  key: string
  maxChars: number
  networks: PostNetwork[]
}

const NETWORK_ORDER = Object.keys(NETWORK_RULES) as PostNetwork[]

export function planVariants(networks: PostNetwork[]): TextVariantPlan[] {
  const byLimit = new Map<number, PostNetwork[]>()
  for (const n of NETWORK_ORDER.filter((x) => networks.includes(x))) {
    const limit = Math.min(NETWORK_RULES[n].maxChars, PRACTICAL_MAX_CHARS)
    byLimit.set(limit, [...(byLimit.get(limit) ?? []), n])
  }
  return [...byLimit.entries()]
    .sort((a, b) => b[0] - a[0])
    .map(([maxChars, nets]) => ({ key: String(maxChars), maxChars, networks: nets }))
}

/** Nome da aba: "Texto longo" / "médio" / "curto" (4+ faixas: numeradas). */
export function variantTitle(index: number, total: number): string {
  if (total === 2) return index === 0 ? "Texto longo" : "Texto curto"
  if (total === 3) return ["Texto longo", "Texto médio", "Texto curto"][index]
  return `Texto ${index + 1}`
}
