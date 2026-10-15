import { lazy, Suspense, type ComponentType } from "react"
import { createRootRoute, createRoute, createRouter, Outlet, redirect } from "@tanstack/react-router"
import { authApi } from "./api/auth"
import { useAuthStore } from "./stores/authStore"
import LoginPage from "./pages/LoginPage"
import DashboardPage from "./pages/DashboardPage"
import { PanelPage } from "./pages/PanelPage"
import { ProductsPage } from "./pages/ProductsPage"
import { ListasPage } from "./pages/ListasPage"
import { PostsPage } from "./pages/PostsPage"
import { CredentialsPage } from "./pages/CredentialsPage"
import { ProfilesPage } from "./pages/ProfilesPage"
import { HelpPage } from "./pages/HelpPage"
import { SettingsPage } from "./pages/SettingsPage"
import { TermsPage } from "./pages/legal/TermsPage"
import { PrivacyPolicyPage } from "./pages/legal/PrivacyPolicyPage"
import { PageSkeleton, type PageSkeletonVariant } from "./components/ui/Skeleton"
import { OrbitalLoader } from "./components/ui/OrbitalLoader"

const UsersPage = lazy(() => import("./pages/UsersPage"))
const LogsPage = lazy(() => import("./pages/LogsPage"))

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

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  component: LoginPage,
})

// Rotas públicas (sem guard de autenticação, mesmo padrão de /login) exigidas
// pela revisão de app OAuth do X/Meta/TikTok — precisam ser acessíveis sem
// login.
const termsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/termos",
  component: TermsPage,
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
  path: "/",
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

const usersRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/users",
  beforeLoad: requireAdmin,
  component: lazyRoute(UsersPage, "list"),
})

const logsRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/logs",
  beforeLoad: requireAdmin,
  component: lazyRoute(LogsPage, "table"),
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
  loginRoute,
  termsRoute,
  privacyRoute,
  panelRoute.addChildren([
    dashboardRoute,
    productsRoute,
    listsRoute,
    postsRoute,
    credentialsRoute,
    profilesRoute,
    usersRoute,
    logsRoute,
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
