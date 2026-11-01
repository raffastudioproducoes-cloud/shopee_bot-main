import { create } from "zustand"

interface PostsSearchState {
  query: string
  setQuery: (query: string) => void
  clear: () => void
}

export const usePostsSearchStore = create<PostsSearchState>()((set) => ({
  query: "",
  setQuery: (query) => set({ query }),
  clear: () => set({ query: "" }),
}))
