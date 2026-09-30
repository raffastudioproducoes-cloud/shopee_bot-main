import { createRootRoute, createRoute, createRouter, Outlet } from "@tanstack/react-router"
import LoginPage from "./pages/LoginPage"
import DashboardPage from "./pages/DashboardPage"
import { PanelPage } from "./pages/PanelPage"
import { ProductsPage } from "./pages/ProductsPage"
import { ListasPage } from "./pages/ListasPage"
import { PostsPage } from "./pages/PostsPage"
import { CredentialsPage } from "./pages/CredentialsPage"
import { UsersPage } from "./pages/UsersPage"
import { LogsPage } from "./pages/LogsPage"
import { HelpPage } from "./pages/HelpPage"
import { TermsPage } from "./pages/legal/TermsPage"
import { PrivacyPolicyPage } from "./pages/legal/PrivacyPolicyPage"

const rootRoute = createRootRoute({
  component: () => <Outlet />,
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

const usersRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/users",
  component: UsersPage,
})

const logsRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/logs",
  component: LogsPage,
})

const helpRoute = createRoute({
  getParentRoute: () => panelRoute,
  path: "/ajuda",
  component: HelpPage,
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
    usersRoute,
    logsRoute,
    helpRoute,
  ]),
])

export const router = createRouter({ routeTree })

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}
