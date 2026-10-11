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

export function planMediaComposition(network: PostNetwork, draft: PostDraft): MediaCompositionPlan {
  const issues = validateForNetwork(network, draft)
  const errors = issues.filter((issue) => issue.level === "error").map((issue) => issue.message)
  const warnings = issues.filter((issue) => issue.level === "warn").map((issue) => issue.message)

  if (errors.length) {
    if (NETWORK_RULES[network].supportsTextOnly) {
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
  return { network, mode, media, textVariant: draft.texts, warnings }
}
