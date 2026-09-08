import { createRouter, Outlet, Route } from "@tanstack/react-router"
import { useState, useEffect } from "react"
import { useAuthStore } from "./stores/authStore"

// ── Rotas ──────────────────────────────────────────────────────────────────────

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
  preValidation: ({ context }) => {
    // Se não tiver token, redireciona para login
    if (!context?.authStore?.accessToken) {
      throw new Error("redirect:/login")
    }
  },
})

const rootRoute = Route.create({
  get pathname() {
    return "/"
  },
  component: () => {
    // Componente raiz que lê authStore via context
    return (
      <AuthProvider>
        <Outlet />
      </AuthProvider>
    )
  },
})

// ── Router ─────────────────────────────────────────────────────────────────────

export const router = createRouter({
  routeTree: rootRoute,
  context: {
    authStore: undefined as undefined | ReturnType<typeof useAuthStore>,
  },
})

function AuthProvider({ children }: { children: React.ReactNode }) {
  const auth = useAuthStore()
  return <>{children}</>
}
