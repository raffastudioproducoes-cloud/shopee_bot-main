// Textos de ajuda por rede (aba "Limites das redes"). Os NÚMEROS vêm de
// NETWORK_RULES (networkLimits.ts); aqui ficam só fontes, requisitos e dicas,
// todos tirados da documentação oficial consultada em CONSULTADO_EM.
import type { PostNetwork } from "../api/posts"
import { NETWORK_RULES, type NetworkRule } from "./networkLimits"

export const CONSULTADO_EM = "07/10/2026"

export interface HelpSource {
  label: string
  url: string
}
export interface HelpFact {
  label: string
  value: string
  /** true = a doc oficial não confirma. */
  unconfirmed?: boolean
}
export interface NetworkHelp {
  facts: HelpFact[]
  tips: string[]
  sources: HelpSource[]
}

export const NETWORK_HELP: Record<PostNetwork, NetworkHelp> = {
  threads: {
    facts: [
      { label: "Posts por dia (API)", value: "até 250 em 24 h; um carrossel conta como 1" },
      { label: "Carrossel", value: "de 2 a 20 itens (imagens, vídeos ou mistura)" },
      { label: "Imagem", value: "largura de 320 a 1440 px, proporção até 10:1, sRGB" },
      { label: "Vídeo", value: "Somente MP4 neste app; H.264 ou HEVC, 23 a 60 fps, 9:16 recomendado" },
    ],
    tips: [
      "Mais de 5 links no mesmo post faz o Threads recusar a publicação.",
      "Só uma tag de tópico (#) por post vale; a primeira é a usada.",
      "Emojis contam pelo tamanho em bytes UTF-8, então um texto com muitos emojis pode estourar os 500 antes do esperado.",
    ],
    sources: [
      { label: "Threads API — Publicar posts", url: "https://developers.facebook.com/docs/threads/posts" },
      { label: "Threads API — Visão geral", url: "https://developers.facebook.com/docs/threads/overview" },
    ],
  },
  x: {
    facts: [
      { label: "Mídia por post", value: "4 fotos OU 1 GIF OU 1 vídeo (não mistura)" },
      { label: "Vídeo (conta comum)", value: "até 20 min e 8 GB; contas Premium têm limites maiores" },
      { label: "Formatos de imagem", value: "página oficial de formatos não pôde ser consultada", unconfirmed: true },
      { label: "Quota de posts da API", value: "não informada nas páginas consultadas", unconfirmed: true },
    ],
    tips: [
      "O X conta cada link como 23 caracteres, não importa o tamanho dele.",
      "Emojis e caracteres japoneses, chineses e coreanos valem 2.",
      "Vídeo maior que o limite da conta que publica é recusado na hora do post.",
    ],
    sources: [
      { label: "X — Contagem de caracteres", url: "https://docs.x.com/resources/fundamentals/counting-characters" },
      { label: "X API — Criar post", url: "https://docs.x.com/x-api/posts/create-post" },
      { label: "X API — Upload de mídia", url: "https://docs.x.com/x-api/media/quickstart/media-upload-chunked" },
    ],
  },
  facebook: {
    facts: [
      { label: "Fotos aceitas pela API", value: "JPEG, BMP, PNG, GIF e TIFF" },
      { label: "Reels (Página)", value: "9:16, 1080×1920 recomendado (mín. 540×960), 3 a 90 s, 24 a 60 fps, MP4 recomendado" },
      { label: "Reels por dia (API)", value: "até 30 em 24 h" },
      { label: "Tamanho e duração de vídeo comum", value: "não informados nas páginas consultadas", unconfirmed: true },
    ],
    tips: [
      "O limite de 63.206 caracteres não aparece na documentação oficial da API: trate como não confirmado.",
      "Fotos PNG acima de 1 MB podem ficar pixeladas; prefira JPEG.",
      "A faixa de 3 a 90 s é a de Reels; por isso o app só avisa, não bloqueia.",
    ],
    sources: [
      { label: "Graph API — Fotos da Página", url: "https://developers.facebook.com/docs/graph-api/reference/page/photos" },
      { label: "Facebook — Publicar Reels", url: "https://developers.facebook.com/docs/video-api/guides/reels-publishing" },
    ],
  },
  instagram: {
    facts: [
      { label: "Conta", value: "profissional (a doc não detalha Business ou Creator)" },
      { label: "Posts por dia (API)", value: "a doc cita 100 em uma página e 50 em outra: confirme o limite atual da conta", unconfirmed: true },
      { label: "Carrossel", value: "até 10 itens; legenda só no post, não nos itens" },
      { label: "Imagem", value: "somente JPEG, largura de 320 a 1440 px, sRGB" },
      { label: "Vídeo (Reels)", value: "Somente MP4 neste app; H.264 ou HEVC, 23 a 60 fps, 9:16 recomendado" },
    ],
    tips: [
      "O Instagram não publica sem imagem ou vídeo; por isso o criador de post exige mídia ou um produto com foto.",
      "PNG não é aceito: converta para JPEG.",
      "A mídia precisa estar numa URL pública na hora da publicação.",
    ],
    sources: [
      { label: "Instagram — Publicação de conteúdo", url: "https://developers.facebook.com/docs/instagram-platform/content-publishing" },
      { label: "Instagram — Referência de mídia", url: "https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media" },
    ],
  },
  tiktok: {
    facts: [
      { label: "Posts por dia (API)", value: "cerca de 15 por conta de criador (varia por criador)" },
      { label: "Vídeo", value: "Somente MP4 neste app; H.264 recomendado; 23 a 60 fps" },
      { label: "Fotos (API)", value: "WebP ou JPEG, até 20 MB (este app publica só vídeo)" },
      { label: "Limite da legenda", value: "2200 vem da referência da API; as diretrizes não citam número", unconfirmed: true },
    ],
    tips: [
      "App sem auditoria do TikTok: todo conteúdo fica privado (só você vê) e no máximo 5 usuários postam por dia. Para postar público, o app precisa ser auditado.",
      "A duração máxima real depende da conta do criador e pode ser menor que 10 min.",
      "O app usa 10 min (600 s), o limite do envio de vídeo por upload.",
    ],
    sources: [
      { label: "TikTok — Direct Post (referência)", url: "https://developers.tiktok.com/doc/content-posting-api-reference-direct-post" },
      { label: "TikTok — Guia de envio de mídia", url: "https://developers.tiktok.com/doc/content-posting-api-media-transfer-guide" },
      { label: "TikTok — Diretrizes de publicação", url: "https://developers.tiktok.com/doc/content-sharing-guidelines" },
      { label: "TikTok — Primeiros passos", url: "https://developers.tiktok.com/doc/content-posting-api-get-started" },
    ],
  },
}

const MB = 1024 * 1024
const GB = 1024 * MB
const fmtBytes = (b: number) => (b >= GB ? `${b / GB} GB` : `${Math.round(b / MB)} MB`)
const num = (v: number) => v.toLocaleString("pt-BR")
const dur = (s: number) => (s >= 120 && s % 60 === 0 ? `${s / 60} min` : `${s} s`)
const NONE = "não informado"

export function textSummary(r: NetworkRule): string {
  const how = r.charCount === "weighted" ? " (contagem do X)" : r.charCount === "utf16" ? " (UTF-16)" : ""
  return `${num(r.maxChars)} caracteres${how}${r.threadParts ? " por parte" : ""}`
}

export function linksSummary(r: NetworkRule): string {
  const p: string[] = []
  if (r.maxLinks != null) p.push(`${r.maxLinks} links`)
  if (r.maxHashtags != null) p.push(r.maxHashtags === 1 ? "1 tag de tópico" : `${r.maxHashtags} hashtags`)
  if (r.maxMentions != null) p.push(`${r.maxMentions} @menções`)
  return p.length ? `até ${p.join(", ")}` : NONE
}

export function mediaSummary(r: NetworkRule): string {
  const p: string[] = []
  if (r.requiresMedia === "video") p.push("exige 1 vídeo")
  else if (r.requiresMedia === "media-or-product") p.push("exige mídia")
  if (r.maxMedia != null) p.push(`até ${r.maxMedia} itens`)
  else if (r.maxImages || r.maxGifs) {
    p.push(`${r.maxImages} fotos OU ${r.maxGifs} GIF OU ${r.maxVideos} vídeo${r.allowMix === false ? ", sem misturar" : ""}`)
  }
  return p.length ? p.join("; ") : NONE
}

export function imageSummary(r: NetworkRule): string {
  const p: string[] = []
  if (r.maxBytes.image != null) p.push(`até ${fmtBytes(r.maxBytes.image)}`)
  if (r.maxBytes.gif != null && r.maxBytes.gif !== r.maxBytes.image) p.push(`GIF até ${fmtBytes(r.maxBytes.gif)}`)
  if (r.imageAspect) p.push("proporção 4:5 a 1.91:1")
  return p.length ? p.join("; ") : NONE
}

export function videoSummary(r: NetworkRule): string {
  const p: string[] = []
  if (r.maxBytes.video != null) p.push(`até ${fmtBytes(r.maxBytes.video)}`)
  if (r.videoMinSec != null && r.videoMaxSec != null) p.push(`${dur(r.videoMinSec)} a ${dur(r.videoMaxSec)}`)
  else if (r.videoMaxSec != null) p.push(`até ${dur(r.videoMaxSec)}`)
  if (r.videoMinSide != null && r.videoMaxSide != null) p.push(`lado de ${r.videoMinSide} a ${num(r.videoMaxSide)} px`)
  else if (r.videoMaxSide != null) p.push(`largura até ${num(r.videoMaxSide)} px`)
  return p.length ? p.join("; ") : NONE
}

export interface RuleRow {
  label: string
  value: string
  unconfirmed?: boolean
}

/** Linhas do card, derivadas da tabela única (a ajuda não diverge do validador). */
export function ruleRows(net: PostNetwork): RuleRow[] {
  const r = NETWORK_RULES[net]
  const u = (...k: string[]) => k.some((x) => r.unverified.includes(x))
  return [
    { label: "Texto", value: textSummary(r), unconfirmed: u("maxChars") },
    { label: "Links, tags e menções", value: linksSummary(r) },
    { label: "Quantidade de mídia", value: mediaSummary(r) },
    { label: "Formatos aceitos pelo app", value: r.exts.map((e) => "." + e).join(" "), unconfirmed: u("exts") },
    { label: "Imagem", value: imageSummary(r) },
    { label: "Vídeo", value: videoSummary(r), unconfirmed: u("videoMinSec", "videoMaxSec") },
  ]
}
