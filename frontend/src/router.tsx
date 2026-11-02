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
import { CreatePostPage } from "./pages/CreatePostPage"
import { PostsAutomationPage } from "./pages/PostsAutomationPage"
import { CredentialsPage } from "./pages/CredentialsPage"
import { ProfilesPage } from "./pages/ProfilesPage"
import { HelpPage } from "./pages/HelpPage"
import { SettingsPage } from "./pages/SettingsPage"
import { TermsPage } from "./pages/legal/TermsPage"
import { PrivacyPolicyPage } from "./pages/legal/PrivacyPolicyPage"
import { DataCollectedPage } from "./pages/legal/DataCollectedPage"
import { PageSkeleton, type PageSkeletonVariant } from "./components/ui/Skeleton"
import { OrbitalLoader } from "./components/ui/OrbitalLoader"
import { AdminLayout } from "./pages/AdminLayout"
import { isAdminVisitingSite } from "./lib/adminSiteFlag"

const AdminOverviewPage = lazy(() => import("./pages/AdminOverviewPage"))
const UsersPage = lazy(() => import("./pages/UsersPage"))
const LogsPage = lazy(() => import("./pages/LogsPage"))
const AdminCredentialsPage = lazy(() => import("./pages/AdminCredentialsPage"))
const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"))
const OrbitalPilotPage = lazy(() => import("./pages/OrbitalPilotPage"))

async function requireAdmin() {
  let user

  try {
    user = await authApi.me()
  } catch {
    useAuthStore.getState().logout()
    throw redirect({ to: "/login" })
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
      authStore.login("", user)
    } else {
      authStore.setUser(user)
    }
    authStore.setRoleVerified(true)

    if (user.access === "ADMIN" && !isAdminVisitingSite()) {
      throw redirect({ to: "/admin/overview" })
    }
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
  component: TermsPage,
})

const dataCollectedRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/dados-coletados',
  component: DataCollectedPage,
})

const privacyRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/privacidade",
  component: PrivacyPolicyPage,
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
  beforeLoad: () => {
    const { isAuthenticated, user } = useAuthStore.getState()
    if (isAuthenticated && user?.access === "ADMIN" && !isAdminVisitingSite()) {
      throw redirect({ to: "/admin/overview" })
    }
  },
  component: DashboardPage,
})

const productsRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/products",
  component: ProductsPage,
})

const listsRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/lists",
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
  component: CreatePostPage,
})

const postsAutomationRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/automacao-posts",
  component: PostsAutomationPage,
})

const analyticsRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/analytics",
  component: lazyRoute(AnalyticsPage, "table"),
})

const credentialsRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/credentials",
  component: CredentialsPage,
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
  component: HelpPage,
})

const settingsRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/settings",
  component: SettingsPage,
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
