import { createRootRoute, createRoute, createRouter, Outlet } from "@tanstack/react-router"
import LoginPage from "./pages/LoginPage"
import DashboardPage from "./pages/DashboardPage"
import { PanelPage } from "./pages/PanelPage"
import { ProductsPage } from "./pages/ProductsPage"
import { ListasPage } from "./pages/ListasPage"

const rootRoute = createRootRoute({
  component: () => <Outlet />,
})

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  component: LoginPage,
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

const routeTree = rootRoute.addChildren([
  loginRoute,
  panelRoute.addChildren([dashboardRoute, productsRoute, listsRoute]),
])

export const router = createRouter({ routeTree })

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}
