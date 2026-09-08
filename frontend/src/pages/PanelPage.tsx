import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { useAuthStore } from "../stores/authStore";
import { router } from "../router";

// ── Painel: métricas + posts recentes + atividades ──────────────────────────

interface RecentPost {
  id: number;
  text: string;
  has_scheduler: boolean;
  run_date: string | null;
  time: string | null;
  children: number | null;
  status: string;
}

interface RecentActivity {
  id: number;
  metadata: Record<string, unknown> | null;
  created_at: string;
  activity_type_id: number | null;
}

interface PanelMetrics {
  products_count: number;
  posts_count: number;
  product_lists_count: number;
  recent_posts: RecentPost[];
  recent_activities: RecentActivity[];
}

export function PanelPage() {
  const { accessToken, logout } = useAuthStore();

  const { data, isLoading, error } = useQuery<PanelMetrics>({
    queryKey: ["panel"],
    queryFn: async () => {
      const res = await fetch("/api/panel", {
        credentials: "include",
      });
      if (!res.ok) {
        if (res.status === 401) {
          logout();
          throw new Error("Não autenticado");
        }
        throw new Error("Falha ao buscar dados do painel");
      }
      return res.json();
    },
  });

  useEffect(() => {
    if (error?.message === "Não autenticado") {
      router.navigate({ to: "/login" });
    }
  }, [error]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-surface p-6">
        <div className="max-w-6xl mx-auto">
          <div className="animate-pulse space-y-4">
            <div className="h-8 w-48 bg-surface-container rounded" />
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-32 bg-surface-container rounded" />
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-surface p-6">
        <div className="max-w-6xl mx-auto text-center py-12">
          <p className="text-on-surface-variant">Erro ao carregar o painel.</p>
          <button
            onClick={() => router.navigate({ to: "/login" })}
            className="mt-4 px-4 py-2 rounded bg-accent text-on-accent"
          >
            Voltar ao login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <header className="mb-8">
          <h1 className="text-2xl font-display text-on-surface">Painel</h1>
          <p className="text-body-sm text-on-surface-variant mt-1">
            Visão geral da sua automação.
          </p>
        </header>

        {/* Métricas */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <MetricCard
            label="Produtos cadastrados"
            value={data.products_count}
            icon="inventory_2"
          />
          <MetricCard
            label="Postagens criadas"
            value={data.posts_count}
            icon="post_add"
          />
          <MetricCard
            label="Listas de produtos"
            value={data.product_lists_count}
            icon="list_alt"
          />
        </div>

        {/* Posts recentes + Atividades */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Posts recentes */}
          <div className="bg-surface-container rounded-lg p-6">
            <h2 className="font-display text-headline-md text-on-surface mb-4">
              Postagens recentes
            </h2>
            {data.recent_posts.length === 0 ? (
              <p className="text-on-surface-variant text-sm py-4 text-center">
                Nenhuma postagem ainda.
              </p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {data.recent_posts.map((post) => (
                  <div
                    key={post.id}
                    className="p-4 rounded-lg border border-white/5 hover:bg-white/[0.03] transition-colors"
                  >
                    <h3 className="text-body-md text-on-surface font-medium truncate">
                      {post.text}
                    </h3>
                    <div className="flex items-center gap-3 mt-2 text-xs text-on-surface-variant">
                      {post.has_scheduler && post.run_date ? (
                        <span className="flex items-center gap-1">
                          <CalendarIcon />
                          {post.run_date}
                        </span>
                      ) : (
                        <span className="flex items-center gap-1">
                          <EditNoteIcon />
                          Rascunho
                        </span>
                      )}
                      {post.children ? (
                        <span>+{post.children} na thread</span>
                      ) : null}
                    </div>
                    <span
                      className={`inline-block mt-2 px-2 py-1 rounded text-[10px] font-bold tracking-wider ${
                        post.status === "AGENDADO"
                          ? "text-accent bg-accent/10"
                          : "text-on-surface-variant bg-white/5"
                      }`}
                    >
                      {post.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Atividades recentes */}
          <div className="bg-surface-container rounded-lg p-6">
            <h2 className="font-display text-headline-md text-on-surface mb-4">
              Atividades recentes
            </h2>
            {data.recent_activities.length === 0 ? (
              <p className="text-on-surface-variant text-sm py-4 text-center">
                Nenhuma atividade registrada.
              </p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {data.recent_activities.map((activity) => (
                  <div
                    key={activity.id}
                    className="p-4 rounded-lg border border-white/5 hover:bg-white/[0.03] transition-colors"
                  >
                    <p className="text-body-sm text-on-surface">
                      {activity.metadata ? JSON.stringify(activity.metadata) : "(sem metadados)"}
                    </p>
                    <p className="text-xs text-on-surface-variant mt-1">
                      {new Date(activity.created_at).toLocaleString("pt-BR")}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Componentes auxiliares ────────────────────────────────────────────────────

function MetricCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: number;
  icon: string;
}) {
  return (
    <div className="bento-card dot-grid p-6 flex flex-col justify-between reveal-up">
      <div className="w-10 h-10 rounded-full bg-surface-container-high flex items-center justify-center mb-4">
        <InlineSvgIcon name={icon} />
      </div>
      <h3 className="text-label-caps text-on-surface-variant mb-1">{label}</h3>
      <p className="font-mono text-4xl text-on-surface">{value}</p>
    </div>
  );
}

// ── Ícone SVG inline (substitui material-symbols-outlined) ────────────────────

function InlineSvgIcon({ name }: { name: string }) {
  const icons: Record<string, string> = {
    inventory_2: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><path d="M3 3h18v18H3V3zm2 2v14h14V5H5zm2 2h10v2H7V7zm0 4h10v2H7v-2zm0 4h6v2H7v-2z"/></svg>`,
    post_add: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><path d="M3 3h18v18H3V3zm2 2v14h14V5H5zm3 5h4v2h-4V10zm0 4h4v2h-4v-2z"/></svg>`,
    list_alt: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><path d="M3 3h18v18H3V3zm2 2v14h14V5H5zm2 2h3v2h-3V7zm0 4h3v2h-3v-2zm-4 4h3v2H7v-2zm0-4h3v2H7V7z"/></svg>`,
    schedule: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><path d="M3 3h18v18H3V3zm2 2v14h14V5H5zm2 2h2v2H7V7zm0 4h8v2H7v-2zm0 4h6v2H7v-2z"/></svg>`,
    edit_note: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><path d="M3 3h18v18H3V3zm2 2v14h14V5H5zm2 2h2v2H7V7zm0 4h2v2H7v-2zm0 4h2v2H7v-2z"/></svg>`,
    arrow_forward: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><path d="M3 3h18v18H3V3zm2 2v14h14V5H5zm2 2h2v2H7V7zm0 4h8v2H7v-2z"/></svg>`,
    calendar: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><path d="M3 3h18v18H3V3zm2 2v14h14V5H5zm2 2h2v2H7V7zm0 4h8v2H7v-2zm0 4h6v2H7v-2z"/></svg>`,
  };

  return (
    <span
      className="inline-block"
      dangerouslySetInnerHTML={{ __html: icons[name] || "" }}
    />
  );
}

// ícones reutilizáveis
function CalendarIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      width="16"
      height="16"
      className="inline-block"
    >
      <path d="M3 3h18v18H3V3zm2 2v14h14V5H5zm2 2h2v2H7V7zm0 4h8v2H7v-2zm0 4h6v2H7v-2z" />
    </svg>
  );
}

function EditNoteIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      width="16"
      height="16"
      className="inline-block"
    >
      <path d="M3 3h18v18H3V3zm2 2v14h14V5H5zm2 2h2v2H7V7zm0 4h2v2H7v-2zm0 4h2v2H7v-2z" />
    </svg>
  );
}
