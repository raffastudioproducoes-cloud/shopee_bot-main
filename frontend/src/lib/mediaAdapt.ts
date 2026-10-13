// Adaptação de mídia por rede (espelho de adapt_media em api/network_limits.py)
// e limites do seletor de arquivos. Só importa tipos: roda também no node --test.
import type { MediaInfo, MediaKind, NetworkRule } from "./networkLimits"

type Item = Pick<MediaInfo, "name" | "size" | "kind">
type AdaptRule = Pick<
  NetworkRule,
  "exts" | "maxBytes" | "deliveredModes" | "maxImages" | "maxGifs" | "maxVideos" | "maxMedia" | "allowMix"
>

export interface Dropped<T> {
  item: T
  reason: string
}

const MB = 1024 * 1024
const GB = 1024 * MB
const KIND_LABEL: Record<MediaKind, string> = { image: "imagem", gif: "GIF", video: "vídeo" }
const GROUP_PRIORITY: MediaKind[] = ["image", "video", "gif"]
const fmtBytes = (b: number) => (b >= GB ? `${b / GB} GB` : `${Math.round(b / MB)} MB`)
const extOf = (name: string) => name.split(".").pop()?.toLowerCase() ?? ""
// Mesma regra de mediaKind (networkLimits.ts), sem importar valor para rodar no node.
const kindOfExt = (ext: string): MediaKind => (ext === "mp4" ? "video" : ext === "gif" ? "gif" : "image")
const kindCap = (rule: AdaptRule, kind: MediaKind) =>
  kind === "image" ? rule.maxImages : kind === "gif" ? rule.maxGifs : rule.maxVideos

export function adaptMedia<T extends Item>(rule: AdaptRule, items: readonly T[]): { kept: T[]; dropped: Dropped<T>[] } {
  const gone = new Map<number, string>()
  let ok: number[] = []
  items.forEach((m, i) => {
    const maxB = rule.maxBytes[m.kind]
    if (!rule.exts.includes(extOf(m.name))) gone.set(i, "formato não aceito")
    else if (kindCap(rule, m.kind) === 0) gone.set(i, `não aceita ${KIND_LABEL[m.kind]}`)
    else if (maxB != null && m.size > maxB) gone.set(i, `tamanho acima de ${fmtBytes(maxB)}`)
    else ok.push(i)
  })

  if (rule.allowMix === false && ok.length) {
    const present = new Set(ok.map((i) => items[i].kind))
    const group = GROUP_PRIORITY.find((k) => present.has(k))!
    for (const i of ok) {
      if (items[i].kind !== group) gone.set(i, `não mistura ${KIND_LABEL[items[i].kind]} com ${KIND_LABEL[group]}`)
    }
    ok = ok.filter((i) => items[i].kind === group)
  }

  let kept: number[] = []
  const counts: Partial<Record<MediaKind, number>> = {}
  for (const i of ok) {
    const kind = items[i].kind
    const cap = kindCap(rule, kind)
    if (cap != null && (counts[kind] ?? 0) >= cap) gone.set(i, `limite de ${cap} ${KIND_LABEL[kind]}(s)`)
    else if (rule.maxMedia != null && kept.length >= rule.maxMedia) gone.set(i, `limite de ${rule.maxMedia} mídias`)
    else {
      kept.push(i)
      counts[kind] = (counts[kind] ?? 0) + 1
    }
  }

  if (kept.length > 1 && !rule.deliveredModes.includes("carousel")) {
    for (const i of kept.slice(1)) gone.set(i, "só 1 mídia por post neste aplicativo")
    kept = kept.slice(0, 1)
  }
  if (kept.length === 1 && items[kept[0]].kind === "video" && !rule.deliveredModes.includes("video")) {
    gone.set(kept[0], "vídeo não é entregue por este aplicativo")
    kept = []
  }

  const dropped = [...gone.entries()].sort((a, b) => a[0] - b[0]).map(([i, reason]) => ({ item: items[i], reason }))
  return { kept: kept.map((i) => items[i]), dropped }
}

export const dropReasons = (dropped: readonly Dropped<unknown>[]) => [...new Set(dropped.map((d) => d.reason))].join("; ")

/** "3 fotos", "1 foto e 1 vídeo", "1 GIF". */
export function describeKept(kept: readonly Pick<Item, "kind">[]): string {
  const n = (k: MediaKind) => kept.filter((m) => m.kind === k).length
  const parts = [
    n("image") && `${n("image")} ${n("image") === 1 ? "foto" : "fotos"}`,
    n("gif") && `${n("gif")} ${n("gif") === 1 ? "GIF" : "GIFs"}`,
    n("video") && `${n("video")} ${n("video") === 1 ? "vídeo" : "vídeos"}`,
  ].filter(Boolean)
  return parts.join(" e ")
}

// ── Seletor de arquivos ──────────────────────────────────────────────────────
// ponytail: rede sem teto declarado (ex.: álbum do Facebook) usa este teto prático.
const DEFAULT_PICK_CAP = 20
const ALL_EXTS = ["webp", "jpg", "jpeg", "png", "gif", "mp4"]

export interface PickLimits {
  /** Extensões que alguma rede marcada aceita. */
  exts: string[]
  /** Máximo absoluto por tipo entre as redes marcadas (Infinity = sem redes). */
  max: Record<MediaKind, number>
}

function capacity(rule: AdaptRule, kind: MediaKind): number {
  if (!rule.exts.some((e) => kindOfExt(e) === kind)) return 0
  if (kind === "video" && !rule.deliveredModes.includes("video")) return 0
  const cap = kindCap(rule, kind) ?? rule.maxMedia ?? DEFAULT_PICK_CAP
  return kind !== "video" && !rule.deliveredModes.includes("carousel") ? Math.min(cap, 1) : cap
}

export function pickLimits(rules: readonly AdaptRule[]): PickLimits {
  if (rules.length === 0) return { exts: ALL_EXTS, max: { image: Infinity, gif: Infinity, video: Infinity } }
  const max = (kind: MediaKind) => Math.max(...rules.map((r) => capacity(r, kind)))
  const limits = { image: max("image"), gif: max("gif"), video: max("video") }
  const exts = ALL_EXTS.filter((e) => limits[kindOfExt(e)] > 0 && rules.some((r) => r.exts.includes(e)))
  return { exts, max: limits }
}

/** Separa o que entra do que nenhuma rede aceita (`ignored`) e do que passa do limite (`overLimit`). */
export function filterPicked<F extends { name: string }>(
  files: readonly F[],
  existingKinds: readonly MediaKind[],
  limits: PickLimits,
): { accepted: F[]; ignored: number; overLimit: number } {
  const counts: Record<MediaKind, number> = { image: 0, gif: 0, video: 0 }
  for (const k of existingKinds) counts[k] += 1
  const accepted: F[] = []
  let ignored = 0
  let overLimit = 0
  for (const file of files) {
    const ext = extOf(file.name)
    const kind = kindOfExt(ext)
    if (!limits.exts.includes(ext)) ignored += 1
    else if (counts[kind] >= limits.max[kind]) overLimit += 1
    else {
      counts[kind] += 1
      accepted.push(file)
    }
  }
  return { accepted, ignored, overLimit }
}

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`

export function pickNotice({ ignored, overLimit }: { ignored: number; overLimit: number }): string | null {
  const parts = [
    ignored && `${plural(ignored, "arquivo ignorado", "arquivos ignorados")}: formato não aceito por nenhuma rede selecionada`,
    overLimit && `${plural(overLimit, "arquivo", "arquivos")} acima do limite das redes selecionadas`,
  ].filter(Boolean)
  return parts.length ? parts.join(" · ") : null
}
