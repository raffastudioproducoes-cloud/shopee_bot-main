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
  selectedIds: number[]
  onToggle: (id: number) => void
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
  selectedIds, onToggle,
  productsLoading, productsError, listsLoading, listsError,
  hasMoreProducts, hasMoreLists, loadingMoreProducts, loadingMoreLists,
  onLoadProducts, onLoadLists,
}: PostProductPickerProps) {
  const [search, setSearch] = useState("")
  const activeList = lists.find((list) => list.id === listId)
  const shown = tab === "products" ? products : (activeList?.products ?? [])
  const selected = new Set(selectedIds)
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
          {selectedIds.length ? "1 produto selecionado" : "Nenhum produto selecionado"}
        </span>
      </div>
      <p className="post-product-picker-hint">Selecione somente um produto por publicação.</p>
      {selectedIds.length > 0 && <button type="button" className="post-product-picker-clear" onClick={() => onToggle(selectedIds[0])}>Remover produto selecionado</button>}
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
        ) : filtered.map((product) => (
          <label className="post-product-picker-item" key={product.id}>
            <input type="radio" name="post-product-single" checked={selected.has(product.id)}
              onChange={() => onToggle(product.id)} />
            <span>{product.name}</span>
          </label>
        ))}
      </div>
      {hasMore && (
        <button type="button" className="post-product-picker-more"
          disabled={loadingMore} onClick={loadMore}>
          {loadingMore ? "Carregando..." : tab === "lists" ? "Carregar mais listas" : "Carregar mais produtos"}
        </button>
      )}
      {tab === "lists" && lists.length === 0 && !listsLoading && !listsError && (
        <p className="post-product-picker-hint">Nenhuma lista encontrada no perfil ativo. Crie listas na página Listas.</p>
      )}
    </section>
  )
}
