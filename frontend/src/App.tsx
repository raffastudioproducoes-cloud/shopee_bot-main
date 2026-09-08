import { TanStackRouterDevtools } from "@tanstack/react-router-devtools"
import { RouterProvider, createRouter, Route, Outlet } from "@tanstack/react-router"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useAuthStore } from "./stores/authStore"
import { useEffect } from "react"

// ── Query Client ────────────────────────────────────────────────────────────────

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

// ── Rotas ───────────────────────────────────────────────────────────────────────

const loginRoute = Route.create({
  get pathname() {
    return "/login"
  },
  component: () => import("./pages/LoginPage.tsx").then((m) => m.default),
})

const panelRoute = Route.create({
  get pathname() {
    return "/"
  },
  component: () => import("./pages/PanelPage.tsx").then((m) => m.PanelPage),
  validateSearch: () => ({}), // sem query params por enquanto
  beforeLoad: ({ context }) => {
    // Se não tiver token, redireciona para login
    if (!context?.authStore?.accessToken) {
      throw new Response(null, {
        status: 302,
        headers: { Location: "/login" },
      })
    }
  },
})

const rootRoute = Route.create({
  get pathname() {
    return "/"
  },
  component: () => {
    const { accessToken, loading } = useAuthStore()

    // Se estiver carregando, mostra spinner
    if (loading) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-surface">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-on-surface-variant border-t-accent" />
        </div>
      )
    }

    // Se não tiver token, redireciona para login
    if (!accessToken) {
      window.location.href = "/login"
      return null
    }

    return <Outlet />
  },
  children: [panelRoute, loginRoute],
})

// ── Router ──────────────────────────────────────────────────────────────────────

export const router = createRouter({
  routeTree: rootRoute,
  context: {
    authStore: undefined as unknown as ReturnType<typeof useAuthStore>,
  },
})

// ── App ─────────────────────────────────────────────────────────────────────────

export function App() {
  const { accessToken, setAuth } = useAuthStore()

  // Carrega o token do cookie via API no mount
  useEffect(() => {
    if (!accessToken) {
      fetch("/api/auth/me", { credentials: "include" })
        .then((r) => {
          if (r.ok) return r.json()
          throw new Error("Não autenticado")
        })
        .then((data) => {
          setAuth({ accessToken: data.access_token, user: data.user })
        })
        .catch(() => {
          setAuth({ accessToken: null, user: null })
          window.location.href = "/login"
        })
    }
  }, [])

  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} context={{ authStore: useAuthStore() }} />
      <TanStackRouterDevtools router={router} />
    </QueryClientProvider>
  )
}
