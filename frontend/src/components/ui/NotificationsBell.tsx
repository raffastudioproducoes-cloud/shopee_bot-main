// Extrapolação: sino do TopBar era só decoração até agora (ícone sem onClick,
// bolinha de "não lido" fixa via prop default `unread = true`) — ver
// TopBar.tsx e api/routers/notifications.py. Este componente é autocontido
// (busca, dropdown, fechar ao clicar fora) pra poder ser injetado no lugar do
// sino padrão via a prop `bell` do TopBar sem duplicar o botão.
import { useEffect, useRef, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { notificationsApi, type Notification } from "../../api/notifications"
import { useNotificationsStore } from "../../stores/notificationsStore"
import { IconButton } from "./IconButton"
import { Panel, PanelHeader, Divider } from "./Panel"
import { Icon } from "./Icon"

function iconForType(type: string | null): { name: string; color: string } {
  if (type?.endsWith("_success")) return { name: "check-circle-2", color: "var(--positive-ink)" }
  if (type?.endsWith("_failure")) return { name: "x-circle", color: "var(--negative-ink)" }
  return { name: "circle-dot", color: "var(--text-muted)" }
}

export function NotificationsBell() {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const lastSeenAt = useNotificationsStore((s) => s.lastSeenAt)
  const markSeen = useNotificationsStore((s) => s.markSeen)

  const { data, isLoading, error } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => notificationsApi.list({ limit: 20 }),
    refetchInterval: 60_000,
  })

  const notifications = data?.data ?? []
  const unread = lastSeenAt
    ? notifications.some((n) => n.created_at > lastSeenAt)
    : notifications.length > 0

  useEffect(() => {
    if (!open) return
    markSeen(new Date().toISOString())
  }, [open, markSeen])

  useEffect(() => {
    if (!open) return
    const onPointerDown = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener("mousedown", onPointerDown)
    return () => document.removeEventListener("mousedown", onPointerDown)
  }, [open])

  return (
    <div ref={containerRef} style={{ position: "relative", display: "inline-flex" }}>
      <IconButton
        icon="bell"
        label="Notificações"
        tone="glass"
        badge={unread}
        active={open}
        onClick={() => setOpen((v) => !v)}
      />

      {open && (
        <div style={{ position: "absolute", top: "calc(100% + 8px)", right: 0, zIndex: 40, width: "min(340px, calc(100vw - 24px))" }}>
          <Panel surface="dark" overflowHidden={false} style={{ maxHeight: 420, display: "flex", flexDirection: "column" }}>
            <PanelHeader title="Notificações" />
            <Divider />
            <div style={{ overflowY: "auto", padding: "4px 0" }}>
              {isLoading ? (
                <p style={{ padding: 16, color: "var(--text-muted)", font: "var(--text-role-body)" }}>Carregando...</p>
              ) : error ? (
                <p style={{ padding: 16, color: "var(--negative)", font: "var(--text-role-body)" }}>
                  Erro ao carregar notificações.
                </p>
              ) : notifications.length === 0 ? (
                <p style={{ padding: 16, color: "var(--text-muted)", font: "var(--text-role-body)" }}>
                  Nenhuma notificação por enquanto.
                </p>
              ) : (
                notifications.map((n: Notification) => {
                  const { name, color } = iconForType(n.type)
                  return (
                    <div
                      key={n.id}
                      style={{
                        display: "flex",
                        gap: 10,
                        alignItems: "flex-start",
                        padding: "10px 16px",
                        borderBottom: "1px solid var(--border-card)",
                      }}
                    >
                      <span style={{ color, flexShrink: 0, marginTop: 2 }}>
                        <Icon name={name} size={16} />
                      </span>
                      <div style={{ minWidth: 0 }}>
                        <p style={{ margin: 0, color: "var(--text-body)", font: "var(--text-role-body)" }}>
                          {n.description || n.type || "Atividade registrada"}
                        </p>
                        <p style={{ margin: "2px 0 0", color: "var(--text-muted)", font: "var(--text-role-label)" }}>
                          {new Date(n.created_at).toLocaleString("pt-BR")}
                        </p>
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </Panel>
        </div>
      )}
    </div>
  )
}
