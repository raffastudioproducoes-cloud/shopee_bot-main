import { create } from "zustand"

interface ProductsSearchState {
  query: string
  activeTab: "mine" | "catalog"
  setQuery: (query: string) => void
  setActiveTab: (tab: "mine" | "catalog") => void
  clear: () => void
}

/** Uma única fonte para a busca da topbar e o filtro de Produtos. */
export const useProductsSearchStore = create<ProductsSearchState>()((set) => ({
  query: "",
  activeTab: "mine",
  setQuery: (query) => set({ query }),
  setActiveTab: (activeTab) => set({ activeTab }),
  clear: () => set({ query: "" }),
}))
