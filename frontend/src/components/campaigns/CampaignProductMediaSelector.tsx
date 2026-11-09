import { useQuery } from "@tanstack/react-query"
import { productsApi } from "../../api/products"
import type { CampaignMediaRecord } from "../../api/campaigns"
import type { PostNetwork } from "../../api/posts"
import { planMediaComposition } from "../../lib/mediaComposition"
import { mediaKind, NETWORK_RULES, type MediaInfo } from "../../lib/networkLimits"
import { ProductMediaVisual } from "../products/ProductMediaVisual"
import "./campaignProductMediaSelector.css"

/** A campaign chooses existing product assets; no file input or upload is offered. */
export function CampaignProductMediaSelector({ productId, shopeeImage, useShopeeImage, selectedIds,
  networks, texts, affiliateLink, legacyMedia = [],
  onShopeeChange, onSelectedChange, disabled = false,
}: {
  productId: number
  shopeeImage: string | null
  useShopeeImage: boolean
  selectedIds: string[]
  networks: PostNetwork[]
  texts: Partial<Record<PostNetwork, string>>
  affiliateLink: string
  legacyMedia?: CampaignMediaRecord[]
  onShopeeChange: (checked: boolean) => void
  onSelectedChange: (ids: string[]) => void
  disabled?: boolean
}) {
  const mediaQuery = useQuery({
    queryKey: ["product-media", productId], queryFn: () => productsApi.media(productId),
    staleTime: 4 * 60 * 1000, retry: 1,
  })
  const media = mediaQuery.data?.items ?? []
  const missing = selectedIds.filter((id) => !media.some((item) => item.id === id))
  const shopeeImageSizeQuery = useQuery({
    queryKey: ["campaign-shopee-image-size", productId],
    queryFn: () => productsApi.downloadImage(productId),
    enabled: Boolean(useShopeeImage && shopeeImage),
    staleTime: 4 * 60 * 1000,
    retry: 1,
  })
  const selectedMedia: MediaInfo[] = [
    ...(useShopeeImage && shopeeImage
      ? [{ name: `shopee-${productId}.jpg`, size: shopeeImageSizeQuery.data?.blob.size ?? 0, kind: "image" as const }]
      : []),
    ...media.filter((item) => selectedIds.includes(item.id)).map((item) => ({
      name: item.file_name,
      size: item.size_bytes,
      kind: item.media_type === "VIDEO" ? "video" as const : mediaKind(item.file_name),
    })),
    ...legacyMedia.map((item) => ({
      name: item.file_name,
      size: item.size_bytes,
      kind: item.media_type === "VIDEO" ? "video" as const : mediaKind(item.file_name),
    })),
  ]
  const plansReady = mediaQuery.isSuccess && (!useShopeeImage || !shopeeImage || shopeeImageSizeQuery.isSuccess)
  const plans = networks.map((network) => {
    const body = texts[network] ?? ""
    const finalText = affiliateLink && !body.includes(affiliateLink)
      ? [body.trim(), affiliateLink].filter(Boolean).join("\n")
      : body
    return planMediaComposition(network, {
      texts: [finalText],
      media: selectedMedia,
      productCount: 1,
    })
  })
  return (
    <div className="campaign-saved-media" aria-label="Mídias para a campanha">
      <strong className="campaign-saved-media__title">Mídias para esta publicação</strong>
      <p>Escolha as mídias já salvas no produto. Você pode usar a foto Shopee, arquivos adicionais, ambos ou nenhuma mídia.</p>
      {shopeeImage ? (
        <label className="campaign-saved-media__shopee">
          <input type="checkbox" checked={useShopeeImage} disabled={disabled}
            onChange={(e) => onShopeeChange(e.target.checked)} />
          <img src={shopeeImage} alt="Foto principal da Shopee" loading="lazy" />
          <span>Usar imagem original da Shopee</span>
        </label>
      ) : <small>Este produto não tem imagem original da Shopee.</small>}
      <div className="campaign-saved-media__heading">
        <strong>Imagens e vídeos adicionais</strong>
        {mediaQuery.isSuccess && <small>{media.length} {media.length === 1 ? "arquivo salvo" : "arquivos salvos"}</small>}
      </div>
      {mediaQuery.isPending && <small role="status">Consultando a galeria do produto…</small>}
      {mediaQuery.isError && <p role="alert">Não foi possível carregar a galeria. <button type="button"
        onClick={() => { void mediaQuery.refetch() }}>Tentar novamente</button></p>}
      {mediaQuery.isSuccess && media.length === 0 && <small>Nenhuma mídia adicional foi salva em Produtos.</small>}
      {media.length > 0 && (
        <div className="campaign-saved-media__grid">
          {media.map((item) => (
            <label key={item.id} className={`campaign-saved-media__asset ${selectedIds.includes(item.id) ? "is-selected" : ""}`}>
              <ProductMediaVisual item={item} />
              <span className="campaign-saved-media__asset-name" title={item.file_name}>{item.file_name}</span>
              <span className="campaign-saved-media__asset-check">
                <input type="checkbox" checked={selectedIds.includes(item.id)} disabled={disabled}
                  aria-label={`Usar ${item.media_type === "VIDEO" ? "vídeo" : "imagem"} ${item.file_name}`}
                  onChange={(event) => onSelectedChange(event.target.checked
                    ? [...selectedIds, item.id]
                    : selectedIds.filter((id) => id !== item.id))} />
                {item.media_type === "VIDEO" ? "Vídeo" : "Imagem"}
              </span>
            </label>
          ))}
        </div>
      )}
      {missing.length > 0 && mediaQuery.isSuccess && <p className="campaign-saved-media__warning" role="alert">
        {missing.length} mídia(s) selecionada(s) não estão mais na galeria. Desmarque-as ou selecione outras antes de ativar.
        <button type="button" disabled={disabled}
          onClick={() => onSelectedChange(selectedIds.filter((id) => !missing.includes(id)))}>
          Limpar referências ausentes
        </button>
      </p>}
      {plansReady && plans.length > 0 && (
        <section className="campaign-media-preflight" aria-live="polite" aria-label="Compatibilidade por rede">
          <strong>Compatibilidade das mídias por rede</strong>
          {plans.map((plan) => (
            <div className={`campaign-media-preflight__network${plan.blockedReason ? " is-blocked" : plan.dropped.length || plan.warnings.length ? " has-warning" : ""}`} key={plan.network}>
              <strong>{NETWORK_RULES[plan.network].label}</strong>
              {plan.blockedReason
                ? <p role="alert">Não pode ser publicado: {plan.blockedReason}</p>
                : <p>{plan.mode === "text_only" ? "Será enviado somente o texto."
                  : plan.mode === "none" ? "Sem mídia."
                  : plan.mode === "single_image" ? "Será enviada 1 imagem."
                  : plan.mode === "carousel" ? `Serão enviadas ${plan.media.length} mídias aceitas.`
                  : "Será enviado 1 vídeo."}</p>}
              {plan.dropped.length > 0 && (
                <ul>
                  {plan.dropped.map((entry, index) => (
                    <li key={`${entry.item.name}-${index}`}>{entry.item.name}: {entry.reason}</li>
                  ))}
                </ul>
              )}
              {plan.warnings.filter((warning) => !plan.dropped.some((entry) => warning.includes(entry.reason))).map((warning) => (
                <p key={warning}>{warning}</p>
              ))}
            </div>
          ))}
          <small>Arquivos incompatíveis são excluídos somente da composição desta rede. Os originais em Produtos permanecem intactos. Vídeos de contas TikTok também passam pela validação dinâmica de Creator Info antes do upload externo.</small>
        </section>
      )}
      <small>A seleção vale apenas para esta campanha e não modifica a galeria de Produtos.</small>
    </div>
  )
}
