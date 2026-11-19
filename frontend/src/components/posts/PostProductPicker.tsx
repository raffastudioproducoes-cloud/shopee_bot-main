import { useState } from "react"
import type { Product } from "../../api/products"
import type { ProductList } from "../../api/lists"
import { Select } from "../ui/Select"
import "./postProductPicker.css"

type Tab = "products" | "lists"
type SelectableProduct = Pick<Product, "id" | "name" | "image">

interface PostProductPickerProps {
  tab: Tab
  onTabChange: (tab: Tab) => void
  products: SelectableProduct[]
  lists: ProductList[]
  listId: number | null
  onListChange: (id: number | null) => void
  /** Ordem de seleção: as redes de 1 produto recebem o 1º. */
  selectedIds: number[]
  onToggle: (id: number) => void
  /** Maior limite entre as redes marcadas (Shopee Vídeo: 6; demais: 1). */
  limit: number
  onClear?: () => void
  productsLoading: boolean
  productsError: boolean
  listsLoading: boolean
  listsError: boolean
  hasMoreProducts: boolean
  hasMoreLists: boolean
  loadingMoreProducts: boolean
  loadingMoreLists: boolean
  onLoadProducts: () => void
  onLoadLists: () => void
}

/** Tabs da mesma seleção: catálogo é da conta; listas são do perfil ativo.
 * Nunca troca IDs selecionados ao alternar abas ou abrir uma lista. */
export function PostProductPicker({
  tab, onTabChange, products, lists, listId, onListChange,
  selectedIds, onToggle, limit, onClear,
  productsLoading, productsError, listsLoading, listsError,
  hasMoreProducts, hasMoreLists, loadingMoreProducts, loadingMoreLists,
  onLoadProducts, onLoadLists,
}: PostProductPickerProps) {
  const [search, setSearch] = useState("")
  const activeList = lists.find((list) => list.id === listId)
  const shown = tab === "products" ? products : (activeList?.products ?? [])
  // Acima do limite (ex.: desmarcou Shopee Vídeo) continua em checkbox para não apagar a seleção.
  const multiple = limit > 1 || selectedIds.length > 1
  const full = selectedIds.length >= limit
  const filtered = shown.filter((product) =>
    product.name.toLocaleLowerCase("pt-BR").includes(search.trim().toLocaleLowerCase("pt-BR")),
  )
  const loading = tab === "products" ? productsLoading : listsLoading
  const error = tab === "products" ? productsError : listsError
  const hasMore = tab === "products" ? hasMoreProducts : hasMoreLists
  const loadingMore = tab === "products" ? loadingMoreProducts : loadingMoreLists
  const loadMore = tab === "products" ? onLoadProducts : onLoadLists

  const switchTab = (next: Tab) => {
    setSearch("")
    onTabChange(next)
  }

  let emptyText = "Nenhum produto cadastrado na conta."
  if (tab === "lists") {
    emptyText = !activeList ? "Escolha uma lista para ver seus produtos."
      : "Esta lista não tem produtos cadastrados."
  }
  if (search && shown.length) emptyText = "Nenhum produto corresponde à busca."

  return (
    <section className="post-product-picker" aria-label="Produtos vinculados à postagem">
      <div className="post-product-picker-heading">
        <span className="post-product-picker-title">Produtos</span>
        <span className="post-product-picker-count" aria-live="polite">
          {limit > 1 ? `${selectedIds.length} de ${limit} produtos`
            : selectedIds.length > 1 ? `${selectedIds.length} produtos selecionados`
            : selectedIds.length ? "1 produto selecionado" : "Nenhum produto selecionado"}
        </span>
      </div>
      <p className="post-product-picker-hint">
        {limit > 1
          ? `Selecione até ${limit} produtos. A ordem vale: as redes que aceitam 1 produto recebem o 1º.`
          : "Selecione somente um produto por publicação."}
      </p>
      {selectedIds.length > limit && <p className="post-product-picker-hint" role="status">
        {limit === 1 ? "As redes selecionadas usarão só o 1º produto." : `As redes selecionadas usarão só os ${limit} primeiros produtos.`}
      </p>}
      {selectedIds.length > 0 && <button type="button" className="post-product-picker-clear"
        onClick={() => (multiple && onClear ? onClear() : onToggle(selectedIds[0]))}>
        {multiple ? "Remover produtos selecionados" : "Remover produto selecionado"}
      </button>}
      <div className="post-product-picker-tabs" role="group" aria-label="Origem dos produtos">
        <button type="button" aria-pressed={tab === "products"}
          className={tab === "products" ? "is-active" : ""}
          onClick={() => switchTab("products")}>Produtos</button>
        <button type="button" aria-pressed={tab === "lists"}
          className={tab === "lists" ? "is-active" : ""}
          onClick={() => switchTab("lists")}>Listas</button>
      </div>
      {tab === "lists" && (
        <div className="post-product-picker-list-control">
          <Select label="Lista do perfil ativo" value={listId === null ? "" : String(listId)}
            onChange={(event) => { onListChange(event.target.value ? Number(event.target.value) : null); setSearch("") }}>
            <option value="">Escolha uma lista...</option>
            {lists.map((list) => (
              <option key={list.id} value={list.id}>
                {list.name} ({list.product_count ?? list.products?.length ?? 0})
              </option>
            ))}
          </Select>

        </div>
      )}
      {(tab === "products" || activeList) && shown.length > 5 && (
        <input className="post-product-picker-search" type="search"
          value={search} onChange={(event) => setSearch(event.target.value)}
          placeholder="Buscar produto..." aria-label="Buscar produto na seleção" />
      )}
      <div className="post-product-picker-items" role="group" aria-label="Produtos disponíveis">
        {loading && !shown.length ? (
          <p className="post-product-picker-feedback" role="status">Carregando produtos...</p>
        ) : error && !shown.length ? (
          <p className="post-product-picker-feedback" role="alert">
            Não foi possível carregar {tab === "lists" ? "as listas deste perfil" : "os produtos"}.
            Tente abrir esta aba novamente.
          </p>
        ) : filtered.length === 0 ? (
          <p className="post-product-picker-feedback">{emptyText}</p>
        ) : filtered.map((product) => {
          const order = selectedIds.indexOf(product.id) + 1
          return (
            <label className="post-product-picker-item" key={product.id}>
              {multiple
                ? <input type="checkbox" checked={order > 0} disabled={order === 0 && full}
                  onChange={() => onToggle(product.id)} />
                : <input type="radio" name="post-product-single" checked={order > 0}
                  onChange={() => onToggle(product.id)} />}
              <span>{product.name}</span>
              {multiple && order > 0 && <span className="post-product-picker-order"
                aria-label={`${order}º da seleção`}>{order}º</span>}
            </label>
          )
        })}
      </div>
      {hasMore && (
        <button type="button" className="post-product-picker-more"
          disabled={loadingMore} onClick={loadMore}>
          {loadingMore ? "Buscando mais…" : tab === "lists" ? "Carregar mais listas" : "Carregar mais produtos"}
        </button>
      )}
      {tab === "lists" && lists.length === 0 && !listsLoading && !listsError && (
        <p className="post-product-picker-hint">Nenhuma lista encontrada no perfil ativo. Crie listas na página Listas.</p>
      )}
    </section>
  )
}
