import type { PostNetwork } from "../api/posts"
import { NETWORK_RULES, type MediaInfo, type PostDraft, validateForNetwork } from "./networkLimits"

export type MediaCompositionMode = "none" | "single_image" | "carousel" | "video" | "text_only" | "blocked"

export interface MediaCompositionPlan {
  network: PostNetwork
  mode: MediaCompositionMode
  media: MediaInfo[]
  textVariant: string[]
  warnings: string[]
  blockedReason?: string
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
  const issues = validateForNetwork(network, draft)
  const errorIssues = issues.filter((issue) => issue.level === "error")
  const errors = errorIssues.map((issue) => issue.message)
  const warnings = issues.filter((issue) => issue.level === "warn").map((issue) => issue.message)

  if (errors.length) {
    const hasTextError = errorIssues.some((issue) => TEXT_ERROR_KEYS.has(issue.key))
    if (!hasTextError && NETWORK_RULES[network].supportsTextOnly) {
      return { network, mode: "text_only", media: [], textVariant: draft.texts, warnings: [...errors, ...warnings] }
    }
    return { network, mode: "blocked", media: [], textVariant: draft.texts, warnings: [...errors, ...warnings], blockedReason: errors[0] }
  }

  const media = [...draft.media]
  const mode: MediaCompositionMode = media.length === 0
    ? "none"
    : media.length === 1 && media[0].kind === "video"
      ? "video"
      : media.length === 1 ? "single_image" : "carousel"
  if (!NETWORK_RULES[network].deliveredModes.includes(mode)) {
    const message = undeliveredMessage(network, mode)
    if (NETWORK_RULES[network].supportsTextOnly) {
      return { network, mode: "text_only", media: [], textVariant: draft.texts, warnings: [...warnings, message] }
    }
    return { network, mode: "blocked", media: [], textVariant: draft.texts, warnings: [...warnings, message], blockedReason: message }
  }

  return { network, mode, media, textVariant: draft.texts, warnings }
}
