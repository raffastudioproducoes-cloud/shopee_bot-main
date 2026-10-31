/**
 * Fontes e assuntos das métricas administrativas.
 *
 * A primeira etiqueta identifica a origem dos dados; as seguintes descrevem
 * o domínio. Nunca use etiquetas de fonte para sugerir disponibilidade:
 * os estados da API são mostrados separadamente.
 */
const TAGS = {
  supabase: { label: 'Supabase', tone: 'supabase' },
  render: { label: 'Render', tone: 'render' },
  app: { label: 'Aplicação', tone: 'app' },
  clients: { label: 'Clientes', tone: 'clients' },
  scheduler: { label: 'Scheduler', tone: 'scheduler' },
  database: { label: 'Banco', tone: 'neutral' },
  capacity: { label: 'Capacidade', tone: 'neutral' },
  traffic: { label: 'Tráfego', tone: 'neutral' },
  plans: { label: 'Planos', tone: 'neutral' },
  history: { label: 'Histórico', tone: 'neutral' },
  logs: { label: 'Logs', tone: 'neutral' },
  performance: { label: 'Desempenho', tone: 'neutral' },
  publishing: { label: 'Publicações', tone: 'neutral' },
  retention: { label: 'Retenção', tone: 'neutral' },
  consumption: { label: 'Consumo', tone: 'neutral' },
  diagnosis: { label: 'Diagnóstico', tone: 'neutral' },
  coverage: { label: 'Cobertura', tone: 'neutral' },
  comparison: { label: 'Comparação', tone: 'neutral' },
  geography: { label: 'Localização', tone: 'neutral' },
  no_data: { label: 'Sem coleta', tone: 'warning' },
  demo: { label: 'Demonstração', tone: 'warning' },
} as const

export type CardTag = keyof typeof TAGS

/** Etiquetas compactas, sem interações e com rótulos legíveis por leitores de tela. */
export function CardTags({ tags }: { tags: readonly CardTag[] }) {
  return (
    <div className="admin-card-tags" aria-label="Fonte e categoria dos indicadores">
      {tags.map(tag => (
        <span key={tag} className={`admin-card-tag admin-card-tag--${TAGS[tag].tone}`}>
          {TAGS[tag].label}
        </span>
      ))}
    </div>
  )
}
