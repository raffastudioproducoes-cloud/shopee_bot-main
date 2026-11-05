import { create } from "zustand"

/** Estado exclusivo do campo de busca da rota /lists. */
interface ListsSearchState {
  query: string
  setQuery: (query: string) => void
  clear: () => void
}

export const useListsSearchStore = create<ListsSearchState>()((set) => ({
  query: "",
  setQuery: (query) => set({ query }),
  clear: () => set({ query: "" }),
}))
