import { lazy, Suspense, type ComponentType } from "react"
import { createRootRoute, createRoute, createRouter, Outlet, redirect } from "@tanstack/react-router"
import { authApi } from "./api/auth"
import { ApiError } from "./lib/api"
import { useAuthStore } from "./stores/authStore"
import LoginPage from "./pages/LoginPage"
import PresentationPage from "./pages/PresentationPage"
import DashboardPage from "./pages/DashboardPage"
import { PanelPage } from "./pages/PanelPage"
import { ProductsPage } from "./pages/ProductsPage"
import { ListasPage } from "./pages/ListasPage"
import { PostsPage } from "./pages/PostsPage"
import { ProfilesPage } from "./pages/ProfilesPage"
import { PageSkeleton, type PageSkeletonVariant } from "./components/ui/Skeleton"
import { OrbitalLoader } from "./components/ui/OrbitalLoader"
import { AdminLayout } from "./pages/AdminLayout"
import { creationSearch } from "./lib/creationIntent"

// Páginas secundárias e pesadas carregam sob demanda (peso do bundle inicial).
const HelpPage = lazy(() => import("./pages/HelpPage").then((m) => ({ default: m.HelpPage })))
const SettingsPage = lazy(() => import("./pages/SettingsPage").then((m) => ({ default: m.SettingsPage })))
const PostsAutomationPage = lazy(() => import("./pages/PostsAutomationPage").then((m) => ({ default: m.PostsAutomationPage })))
const CredentialsPage = lazy(() => import("./pages/CredentialsPage").then((m) => ({ default: m.CredentialsPage })))
const CreatePostPage = lazy(() => import("./pages/CreatePostPage").then((m) => ({ default: m.CreatePostPage })))
const TermsPage = lazy(() => import("./pages/legal/TermsPage").then((m) => ({ default: m.TermsPage })))
const PrivacyPolicyPage = lazy(() => import("./pages/legal/PrivacyPolicyPage").then((m) => ({ default: m.PrivacyPolicyPage })))
const DataCollectedPage = lazy(() => import("./pages/legal/DataCollectedPage").then((m) => ({ default: m.DataCollectedPage })))
const AdminOverviewPage = lazy(() => import("./pages/AdminOverviewPage"))
const UsersPage = lazy(() => import("./pages/UsersPage"))
const LogsPage = lazy(() => import("./pages/LogsPage"))
const AdminCredentialsPage = lazy(() => import("./pages/AdminCredentialsPage"))
const OrbitalPilotPage = lazy(() => import("./pages/OrbitalPilotPage"))

async function requireAdmin() {
  let user

  try {
    user = await authApi.me()
  } catch (error) {
    // Falha transitória não é expiração da sessão: mantenha o estado
    // e deixe o roteador mostrar erro recuperável sem revelar a área admin.
    if (error instanceof ApiError && error.status === 401) {
      useAuthStore.getState().logout()
      throw redirect({ to: "/login" })
    }
    throw error
  }

  const authStore = useAuthStore.getState()
  authStore.setUser(user)
  authStore.setRoleVerified(true)

  if (user.access !== "ADMIN") {
    throw redirect({ to: "/" })
  }
}

const lazyRoute = (Page: ComponentType, variant: PageSkeletonVariant) => () => (
  <Suspense fallback={<PageSkeleton variant={variant} />}><Page /></Suspense>
)

const rootRoute = createRootRoute({
  component: () => <Suspense fallback={<PageSkeleton variant="detail" />}><Outlet /></Suspense>,
  pendingComponent: () => <OrbitalLoader fullScreen size="lg" />,
})

// A raiz é uma entrada pública: só o backend pode confirmar uma sessão existente.
const landingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  beforeLoad: async () => {
    let user
    try {
      user = await authApi.me()
    } catch (error) {
      // Cookie expirado não é autenticação. Em falha transitória mostramos
      // apenas a landing pública e deixamos as rotas privadas protegidas.
      if (error instanceof ApiError && error.status === 401) {
        useAuthStore.getState().logout()
      }
      return
    }

    const authStore = useAuthStore.getState()
    if (!authStore.isAuthenticated || authStore.user?.id !== user.id) {
      authStore.login(user)
    } else {
      authStore.setUser(user)
    }
    authStore.setRoleVerified(true)

    throw redirect({ to: "/app" })
  },
  component: PresentationPage,
})

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  component: LoginPage,
})

// Endereço público estável para compartilhar a landing, inclusive com sessão ativa.
const presentationRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/presentation",
  component: PresentationPage,
})

// Compatibilidade com o link de prévia anterior.
const orbitalPilotRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/presentation/pilot",
  component: lazyRoute(OrbitalPilotPage, "detail"),
})

const legacyPresentationRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/apresentacao",
  beforeLoad: () => { throw redirect({ to: "/presentation", replace: true }) },
})

// Rotas públicas (sem guard de autenticação, mesmo padrão de /login) exigidas
// pela revisão de app OAuth do X/Meta/TikTok — precisam ser acessíveis sem
// login.
const termsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/termos",
  component: lazyRoute(TermsPage, "detail"),
})

const dataCollectedRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/dados-coletados',
  component: lazyRoute(DataCollectedPage, "detail"),
})

const privacyRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/privacidade",
  component: lazyRoute(PrivacyPolicyPage, "detail"),
})

// Layout route (no URL segment): renders the sidebar shell around every
// authenticated page. PanelPage itself checks isAuthenticated and redirects.
const panelRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: "panel",
  component: PanelPage,
})

const dashboardRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/app",
  component: DashboardPage,
})

const productsRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/products",
  validateSearch: creationSearch,
  component: ProductsPage,
})

const listsRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/lists",
  validateSearch: creationSearch,
  component: ListasPage,
})

const postsRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/posts",
  component: PostsPage,
})

const createPostRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/posts/criar",
  component: lazyRoute(CreatePostPage, "detail"),
})

const postsAutomationRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/automacao-posts",
  component: lazyRoute(PostsAutomationPage, "detail"),
})

// A análise de redes passou para baixo do dashboard. A rota antiga continua valendo para links salvos.
const analyticsRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/analytics",
  beforeLoad: () => { throw redirect({ to: "/app", hash: "analises" }) },
})

const credentialsRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/credentials",
  component: lazyRoute(CredentialsPage, "detail"),
})

const profilesRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/profiles",
  component: ProfilesPage,
})

const adminRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/admin",
  beforeLoad: requireAdmin,
  component: AdminLayout,
})

const adminIndexRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "/",
  beforeLoad: () => { throw redirect({ to: "/admin/overview" }) },
})

const adminOverviewRoute = createRoute({ getParentRoute: () => adminRoute, path: "overview", component: lazyRoute(AdminOverviewPage, "detail") })

const usersRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "users",
  component: lazyRoute(UsersPage, "list"),
})

const logsRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "logs",
  component: lazyRoute(LogsPage, "table"),
})

const adminCredentialsRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "credentials",
  component: lazyRoute(AdminCredentialsPage, "detail"),
})

const helpRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/ajuda",
  component: lazyRoute(HelpPage, "detail"),
})

const settingsRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/settings",
  component: lazyRoute(SettingsPage, "detail"),
})

const routeTree = rootRoute.addChildren([
  landingRoute,
  loginRoute,
  presentationRoute,
  orbitalPilotRoute,
  legacyPresentationRoute,
  termsRoute,
  privacyRoute,
  dataCollectedRoute,
  adminRoute.addChildren([adminIndexRoute, adminOverviewRoute, usersRoute, logsRoute, adminCredentialsRoute]),
  panelRoute.addChildren([
    dashboardRoute,
    productsRoute,
    listsRoute,
    postsRoute,
    createPostRoute,
    postsAutomationRoute,
    analyticsRoute,
    credentialsRoute,
    profilesRoute,
    helpRoute,
    settingsRoute,
  ]),
])

export const router = createRouter({ routeTree })

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

