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
import { Skeleton, SkeletonText } from "./Skeleton"

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
    <div ref={containerRef} className="csp-s-0116">
      <IconButton
        icon="bell"
        label="Notificações"
        tone="glass"
        badge={unread}
        active={open}
        onClick={() => setOpen((v) => !v)}
      />

      {open && (
        <div className="csp-s-0117">
          <Panel surface="dark" overflowHidden={false} style={{ maxHeight: 420, display: "flex", flexDirection: "column" }}>
            <PanelHeader title="Notificações" />
            <Divider />
            <div className="csp-s-0118">
              {isLoading ? (
                <div role="status" aria-busy="true" className="csp-s-0119" aria-label="Carregando notificações">
                  {[0, 1, 2].map((i) => <div key={i} className="csp-s-0120"><Skeleton width={16} height={16} radius="var(--r-pill)" /><SkeletonText lines={2} /></div>)}
                </div>
              ) : error ? (
                <p className="csp-s-0121">
                  Erro ao carregar notificações.
                </p>
              ) : notifications.length === 0 ? (
                <p className="csp-s-0122">
                  Nenhuma notificação por enquanto.
                </p>
              ) : (
                notifications.map((n: Notification) => {
                  const { name, color } = iconForType(n.type)
                  return (
                    <div
                      key={n.id}
                      className="csp-s-0123"
                    >
                      <span style={{ color, flexShrink: 0, marginTop: 2 }}>
                        <Icon name={name} size={16} />
                      </span>
                      <div className="csp-s-0124">
                        <p className="csp-s-0125">
                          {n.description || n.type || "Atividade registrada"}
                        </p>
                        <p className="csp-s-0126">
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
