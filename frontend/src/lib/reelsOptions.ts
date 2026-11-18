// Regras do painel "Publicar como Reels" (Instagram e Facebook). Sem imports de
// propósito: os testes em Node 20 transpilam este arquivo direto
// (tests/reels-options.test.mjs). Espelho no servidor: apis/facebook.py
// (reel_requirements_error) valida de novo antes de chamar a Meta.
//
// Fonte: developers.facebook.com/docs/video-api/guides/reels-publishing
// (conferida em 18/11/2026): 9:16, mínimo 540x960, 3 a 90 s, MP4.

export const REELS_MIN_SEC = 3
export const REELS_MAX_SEC = 90
export const REELS_MIN_WIDTH = 540
export const REELS_MIN_HEIGHT = 960
/** "Vertical" para o padrão ligado: largura/altura até 0,8 (9:16 = 0,5625). */
export const REELS_VERTICAL_MAX_RATIO = 0.8
export const FACEBOOK_REELS_REASON = "Para Reels o vídeo precisa ser vertical 9:16 de 3 a 90 s"
export const INSTAGRAM_REELS_NOTE = "No Instagram, vídeo único sai sempre como Reels (também aparece no feed)."

export interface ReelsVideo {
  width?: number
  height?: number
  durationSec?: number
}

export interface ReelsEligibility {
  /** Pode ligar (o servidor valida de novo antes de enviar). */
  allowed: boolean
  /** Ligado por padrão (vertical e de 3 a 90 s). */
  suggested: boolean
  /** Por que está desligado/bloqueado; null quando ok. */
  reason: string | null
  /** Aviso que não bloqueia (ex.: vertical fora de 9:16). */
  warning: string | null
}

export function isNineBySixteen(width: number, height: number): boolean {
  return height > 0 && Math.abs(width / height - 9 / 16) <= 0.01
}

export function facebookReelsEligibility(video: ReelsVideo | null | undefined): ReelsEligibility {
  const { width, height, durationSec } = video ?? {}
  if (!width || !height || durationSec == null || !Number.isFinite(durationSec)) {
    // Vídeo do produto ou metadados ilegíveis: desligado por padrão, mas pode ligar.
    return {
      allowed: true, suggested: false, warning: null,
      reason: `${FACEBOOK_REELS_REASON}; não deu para ler este vídeo no navegador, o envio confere antes de publicar.`,
    }
  }
  const tooWide = width / height > REELS_VERTICAL_MAX_RATIO
  const badLength = durationSec < REELS_MIN_SEC || durationSec > REELS_MAX_SEC
  if (tooWide || badLength) {
    const detail = `o seu tem ${width}×${height} e ${Math.round(durationSec)} s`
    return { allowed: false, suggested: false, warning: null, reason: `${FACEBOOK_REELS_REASON} (${detail}).` }
  }
  if (width < REELS_MIN_WIDTH || height < REELS_MIN_HEIGHT) {
    return {
      allowed: false, suggested: false, warning: null,
      reason: `Para Reels a resolução mínima é ${REELS_MIN_WIDTH}×${REELS_MIN_HEIGHT} (o seu tem ${width}×${height}).`,
    }
  }
  const warning = isNineBySixteen(width, height)
    ? null
    : `O vídeo (${width}×${height}) não é exatamente 9:16; o Reel pode aparecer com bordas.`
  return { allowed: true, suggested: true, reason: null, warning }
}

/** Escolha efetiva: o usuário manda (se permitido); sem toque, vale o padrão. */
export function facebookReelsValue(touched: boolean | null, eligibility: ReelsEligibility): boolean {
  if (!eligibility.allowed) return false
  return touched ?? eligibility.suggested
}
