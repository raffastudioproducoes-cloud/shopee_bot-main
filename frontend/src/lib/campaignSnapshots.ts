import type { Product } from "../api/lists"
import type { PostNetwork } from "../api/posts"

/** Rascunho local da campanha. Não representa um post agendado nem uma mídia importada. */
export interface CampaignItemSnapshot {
  title: string
  copy: string
  affiliateLink: string
  networks: PostNetwork[]
  networkCopies: Partial<Record<PostNetwork, string>>
  useShopeeImage: boolean
}

type SnapshotProduct = Pick<Product, "id" | "name" | "description" | "image" | "commission_link">
type SnapshotMap = Record<number, CampaignItemSnapshot>
const NETWORKS: readonly PostNetwork[] = ["threads", "x", "facebook", "instagram", "tiktok"]
const MAX_TEXT = 10000

function record(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown> : {}
}

function textOr(value: unknown, fallback: string, max = MAX_TEXT): string {
  return typeof value === "string" ? value.slice(0, max) : fallback
}

/** Captura campos do produto uma vez, sem editar a lista-fonte nem outro produto. */
export function createCampaignSnapshot(product: SnapshotProduct): CampaignItemSnapshot {
  return {
    title: product.name,
    copy: product.description?.trim() ?? "",
    affiliateLink: product.commission_link ?? "",
    networks: [],
    networkCopies: {},
    useShopeeImage: Boolean(product.image),
  }
}

/** Reidrata rascunho versionado/legado: IDs estranhos e redes desconhecidas são descartados. */
export function reconcileCampaignSnapshots(
  products: readonly SnapshotProduct[],
  persisted: unknown,
): SnapshotMap {
  const saved = record(persisted)
  const result: SnapshotMap = {}
  for (const product of products) {
    const base = createCampaignSnapshot(product)
    const raw = record(saved[String(product.id)])
    const networks = Array.isArray(raw.networks)
      ? [...new Set(raw.networks)].filter((network): network is PostNetwork => NETWORKS.includes(network as PostNetwork))
      : base.networks
    const copies = record(raw.networkCopies)
    const networkCopies: CampaignItemSnapshot["networkCopies"] = {}
    for (const network of NETWORKS) {
      if (typeof copies[network] === "string") networkCopies[network] = textOr(copies[network], "")
    }
    result[product.id] = {
      title: textOr(raw.title, base.title, 300),
      copy: textOr(raw.copy, base.copy),
      affiliateLink: textOr(raw.affiliateLink, base.affiliateLink, 2048),
      networks,
      networkCopies,
      useShopeeImage: Boolean(product.image) &&
        (typeof raw.useShopeeImage === "boolean" ? raw.useShopeeImage : base.useShopeeImage),
    }
  }
  return result
}

/** Uma alteração nunca sobrescreve o snapshot de outro produto. */
export function patchCampaignSnapshot(
  snapshots: Readonly<SnapshotMap>,
  productId: number,
  changes: Partial<CampaignItemSnapshot>,
): SnapshotMap {
  if (!snapshots[productId]) return { ...snapshots }
  return { ...snapshots, [productId]: { ...snapshots[productId], ...changes } }
}
