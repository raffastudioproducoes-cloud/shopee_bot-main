// Regras da tela "Publicar no TikTok" (TikTok Content Sharing Guidelines,
// https://developers.tiktok.com/doc/content-sharing-guidelines). Sem React:
// testável em Node. O backend (api/tiktok_options.py) repete as mesmas regras.

export type TikTokPrivacy = 'PUBLIC_TO_EVERYONE' | 'MUTUAL_FOLLOW_FRIENDS' | 'FOLLOWER_OF_CREATOR' | 'SELF_ONLY'
export type TikTokMode = 'direct' | 'draft'

export interface TikTokCreatorInfo {
  creator_nickname: string
  creator_username: string
  creator_avatar_url: string
  privacy_level_options: TikTokPrivacy[]
  comment_disabled: boolean
  duet_disabled: boolean
  stitch_disabled: boolean
  max_video_post_duration_sec: number | null
  can_post: boolean
  cannot_post_reason: string | null
}

/** Estado da tela. Privacidade começa vazia: a guideline proíbe valor padrão. */
export interface TikTokChoice {
  mode: TikTokMode
  privacy: TikTokPrivacy | ''
  allowComment: boolean
  allowDuet: boolean
  allowStitch: boolean
  commercial: boolean
  brandOrganic: boolean
  brandContent: boolean
  isAigc: boolean
}

/** Corpo enviado à API (TikTokPostOptions no backend). */
export interface TikTokOptionsPayload {
  mode: TikTokMode
  privacy_level?: TikTokPrivacy
  allow_comment?: boolean
  allow_duet?: boolean
  allow_stitch?: boolean
  commercial_content?: boolean
  brand_organic?: boolean
  brand_content?: boolean
  is_aigc?: boolean
  consent: true
}

export const TIKTOK_TITLE_MAX = 2200

export const PRIVACY_LABELS: Record<TikTokPrivacy, string> = {
  PUBLIC_TO_EVERYONE: 'Todos',
  MUTUAL_FOLLOW_FRIENDS: 'Amigos (seguidores que você segue de volta)',
  FOLLOWER_OF_CREATOR: 'Seguidores',
  SELF_ONLY: 'Somente eu',
}

export const MUSIC_USAGE_URL = 'https://www.tiktok.com/legal/page/global/music-usage-confirmation/en'
export const BRANDED_CONTENT_POLICY_URL = 'https://www.tiktok.com/legal/page/global/bc-policy/en'

// Textos da guideline, traduzidos para PT-BR mantendo o sentido exato.
export const COMMERCIAL_REQUIRED_HINT = 'Você precisa indicar se o seu conteúdo promove você, um terceiro ou ambos.'
export const BRANDED_PRIVATE_HINT = 'A visibilidade de conteúdo de marca não pode ser definida como privada.'
export const PROCESSING_NOTICE = 'Depois de publicar, o TikTok pode levar alguns minutos para processar o vídeo e ele aparecer no seu perfil.'
export const DRAFT_NOTICE = 'O vídeo vai para a caixa de entrada do app TikTok. Abra a notificação no app para editar, escolher privacidade e divulgação e publicar. A legenda não é enviada nesse modo: copie-a para colar no app.'

export function emptyTikTokChoice(): TikTokChoice {
  return {
    mode: 'direct', privacy: '', allowComment: false, allowDuet: false, allowStitch: false,
    commercial: false, brandOrganic: false, brandContent: false, isAigc: false,
  }
}

/** Atualização imutável que já aplica as dependências da guideline. */
export function updateTikTokChoice(choice: TikTokChoice, patch: Partial<TikTokChoice>): TikTokChoice {
  const next = { ...choice, ...patch }
  if (!next.commercial) return { ...next, brandOrganic: false, brandContent: false }
  return next
}

export function interactionDisabled(creator: TikTokCreatorInfo | undefined, key: 'comment' | 'duet' | 'stitch'): boolean {
  if (!creator) return true
  return key === 'comment' ? creator.comment_disabled : key === 'duet' ? creator.duet_disabled : creator.stitch_disabled
}

/** "Somente eu" fica indisponível com Conteúdo de marca marcado (tooltip da guideline). */
export function privacyOptionDisabledReason(choice: TikTokChoice, option: TikTokPrivacy): string | null {
  return choice.commercial && choice.brandContent && option === 'SELF_ONLY' ? BRANDED_PRIVATE_HINT : null
}

/** Conteúdo de marca fica indisponível com privacidade privada (abordagem 1 da guideline). */
export function brandContentDisabledReason(choice: TikTokChoice): string | null {
  return choice.privacy === 'SELF_ONLY' && !choice.brandContent ? BRANDED_PRIVATE_HINT : null
}

/** Rótulo que o TikTok aplicará ao vídeo, conforme a seleção. */
export function commercialLabelNotice(choice: TikTokChoice): string | null {
  if (!choice.commercial) return null
  if (choice.brandContent) return "Seu vídeo será rotulado como 'Parceria paga'."
  if (choice.brandOrganic) return "Seu vídeo será rotulado como 'Conteúdo promocional'."
  return null
}

/** Qual declaração mostrar antes do botão: só música ou política de marca + música. */
export function declarationKind(choice: TikTokChoice): 'music' | 'branded' {
  return choice.mode === 'direct' && choice.commercial && choice.brandContent ? 'branded' : 'music'
}

/**
 * Motivo para manter o botão de publicar/agendar/ativar desabilitado; null = liberado.
 * Duração em segundos do vídeo local, quando conhecida.
 */
export function tiktokBlockReason(
  choice: TikTokChoice,
  creator: TikTokCreatorInfo | undefined,
  options: { loading?: boolean; error?: string | null; videoDurationSec?: number | null } = {},
): string | null {
  if (options.error) return options.error
  if (options.loading || !creator) return 'Consultando a conta TikTok.'
  if (!creator.can_post) return creator.cannot_post_reason ?? 'Esta conta TikTok não pode publicar agora. Tente mais tarde.'
  if (choice.mode === 'draft') return null
  const max = creator.max_video_post_duration_sec
  if (max && options.videoDurationSec != null && options.videoDurationSec > max) {
    return `O vídeo tem ${Math.round(options.videoDurationSec)} s; esta conta TikTok aceita até ${max} s.`
  }
  if (!choice.privacy) return 'Escolha quem pode ver o vídeo no TikTok.'
  if (!creator.privacy_level_options.includes(choice.privacy)) return 'Esta privacidade não está disponível para a conta TikTok. Escolha outra.'
  if (choice.commercial && !choice.brandOrganic && !choice.brandContent) return COMMERCIAL_REQUIRED_HINT
  if (choice.commercial && choice.brandContent && choice.privacy === 'SELF_ONLY') return BRANDED_PRIVATE_HINT
  if ((choice.allowComment && creator.comment_disabled) || (choice.allowDuet && creator.duet_disabled)
    || (choice.allowStitch && creator.stitch_disabled)) return 'A conta TikTok desativou uma das interações marcadas.'
  return null
}

/** Payload enviado somente no clique explícito em publicar/agendar/ativar. */
export function toTikTokPayload(choice: TikTokChoice): TikTokOptionsPayload {
  if (choice.mode === 'draft') return { mode: 'draft', consent: true }
  return {
    mode: 'direct',
    privacy_level: choice.privacy || undefined,
    allow_comment: choice.allowComment,
    allow_duet: choice.allowDuet,
    allow_stitch: choice.allowStitch,
    commercial_content: choice.commercial,
    brand_organic: choice.commercial && choice.brandOrganic,
    brand_content: choice.commercial && choice.brandContent,
    is_aigc: choice.isAigc,
    consent: true,
  }
}
