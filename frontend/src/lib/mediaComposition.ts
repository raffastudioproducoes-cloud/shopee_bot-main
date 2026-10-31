// Espelho de api/media_composition.py: o que cada rede recebe. Mídia que a rede
// não aceita sai do plano (`dropped`) sem bloquear a rede; só vira `blocked`
// quando nada serve e nem texto puro é permitido.
import type { PostNetwork } from "../api/posts"
import { adaptMedia, dropReasons, type Dropped } from "./mediaAdapt"
import { NETWORK_RULES, type MediaInfo, type PostDraft, validateForNetwork } from "./networkLimits"

export type MediaCompositionMode = "none" | "single_image" | "carousel" | "video" | "text_only" | "blocked"

export interface MediaCompositionPlan {
  network: PostNetwork
  mode: MediaCompositionMode
  media: MediaInfo[]
  textVariant: string[]
  warnings: string[]
  blockedReason?: string
  dropped: Dropped<MediaInfo>[]
}

const TEXT_ERROR_KEYS = new Set(["maxChars", "maxLinks", "maxHashtags", "maxMentions"])

function undeliveredMessage(network: PostNetwork, mode: Exclude<MediaCompositionMode, "text_only" | "blocked">): string {
  const names: Record<Exclude<MediaCompositionMode, "text_only" | "blocked">, string> = {
    none: "post sem mídia",
    single_image: "imagem única",
    carousel: "carrossel",
    video: "vídeo",
  }
  return `${NETWORK_RULES[network].label}: ${names[mode]} ainda não é entregue por este aplicativo`
}

export function planMediaComposition(network: PostNetwork, draft: PostDraft): MediaCompositionPlan {
  const rule = NETWORK_RULES[network]
  const publishableTexts = rule.threadParts ? draft.texts : draft.texts.slice(0, 1)
  const { kept, dropped } = adaptMedia(rule, draft.media)
  const issues = validateForNetwork(network, { ...draft, texts: publishableTexts, media: kept })
  const errorIssues = issues.filter((issue) => issue.level === "error")
  const errors = errorIssues.map((issue) => issue.message)
  const warnings = issues.filter((issue) => issue.level === "warn").map((issue) => issue.message)
  if (dropped.length && kept.length) {
    warnings.unshift(`${rule.label}: ${kept.length} de ${draft.media.length} mídias — ${dropReasons(dropped)}`)
  }

  const base = { network, textVariant: publishableTexts, dropped }
  const textOrBlock = (reason: string, notes: string[]): MediaCompositionPlan =>
    rule.supportsTextOnly
      ? { ...base, mode: "text_only", media: [], warnings: [...notes, ...warnings] }
      : { ...base, mode: "blocked", media: [], warnings: [...notes, ...warnings], blockedReason: reason }

  if (errorIssues.some((issue) => TEXT_ERROR_KEYS.has(issue.key))) {
    return { ...base, mode: "blocked", media: [], warnings: [...errors, ...warnings], blockedReason: errors[0] }
  }
  if (draft.media.length && !kept.length) {
    const reason = `${rule.label}: nenhuma mídia aceita (${dropReasons(dropped)})`
    return textOrBlock(reason, [reason])
  }
  if (errors.length) return textOrBlock(errors[0], errors)

  const mode: MediaCompositionMode = kept.length === 0
    ? "none"
    : kept.length === 1 && kept[0].kind === "video"
      ? "video"
      : kept.length === 1 ? "single_image" : "carousel"
  if (!rule.deliveredModes.includes(mode)) {
    const message = undeliveredMessage(network, mode)
    return textOrBlock(message, [message])
  }

  return { ...base, mode, media: kept, warnings }
}
