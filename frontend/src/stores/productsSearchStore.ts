import { create } from "zustand"

interface ProductsSearchState {
  query: string
  setQuery: (query: string) => void
  clear: () => void
}

/** Uma única fonte para a busca da topbar e o filtro de Produtos. */
export const useProductsSearchStore = create<ProductsSearchState>()((set) => ({
  query: "",
  setQuery: (query) => set({ query }),
  clear: () => set({ query: "" }),
}))
