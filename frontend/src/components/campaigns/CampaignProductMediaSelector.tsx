import { useQuery } from "@tanstack/react-query"
import { productsApi } from "../../api/products"
import { ProductMediaVisual } from "../products/ProductMediaVisual"
import "./campaignProductMediaSelector.css"

/** A campaign chooses existing product assets; no file input or upload is offered. */
export function CampaignProductMediaSelector({ productId, shopeeImage, useShopeeImage, selectedIds,
  onShopeeChange, onSelectedChange, disabled = false,
}: {
  productId: number
  shopeeImage: string | null
  useShopeeImage: boolean
  selectedIds: string[]
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
      <small>A seleção vale apenas para esta campanha e não modifica a galeria de Produtos.</small>
    </div>
  )
}
