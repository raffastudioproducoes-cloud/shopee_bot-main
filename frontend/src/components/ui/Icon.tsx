import type { CSSProperties, ComponentType } from "react"
import {
  ArrowUpRight,
  ArrowDownRight,
  ChevronRight,
  Bell,
  Search,
  MessageSquare,
  House,
  Briefcase,
  CircleDot,
  SlidersHorizontal,
  Maximize2,
  FileText,
  KeyRound,
  Users,
  LogOut,
  X,
  CheckCircle2,
  XCircle,
  Plus,
  Pencil,
  Trash2,
  Loader2,
  Sparkles,
  Send,
  Clock,
  Eye,
  EyeOff,
  User,
  Lock,
  Image,
  Hash,
  Calendar,
  DollarSign,
  Percent,
  Package,
  Link2,
  ChevronDown,
  List,
  Grid3x3,
  LayoutGrid,
  ScrollText,
  HelpCircle,
  type LucideProps,
} from "lucide-react"

/** Lucide line icon. Maps a kebab-case name (e.g. "arrow-up-right") to the
 *  matching lucide-react component. Explicit map (not `import *`) so the
 *  bundle only ships the icons this app actually uses. */
export interface IconProps {
  /** Lucide icon name in kebab-case, e.g. "arrow-up-right". */
  name: string
  /** Box size in px. 16 for inline meta, 20 default, 24 for rail/tiles. */
  size?: number
  /** Lucide stroke weight. The MiT set draws at 1.75. */
  strokeWidth?: number
  className?: string
  style?: CSSProperties
}

const ICONS: Record<string, ComponentType<LucideProps>> = {
  "arrow-up-right": ArrowUpRight,
  "arrow-down-right": ArrowDownRight,
  "chevron-right": ChevronRight,
  bell: Bell,
  search: Search,
  "message-square": MessageSquare,
  house: House,
  briefcase: Briefcase,
  "circle-dot": CircleDot,
  "sliders-horizontal": SlidersHorizontal,
  "maximize-2": Maximize2,
  "file-text": FileText,
  "key-round": KeyRound,
  users: Users,
  "log-out": LogOut,
  // Extrapolação: adicionados para o close button do Modal (IconButton icon="x") e o
  // StatusBadge (ver Modal.tsx / StatusBadge.tsx) — não fazem parte do mapa original.
  x: X,
  "check-circle-2": CheckCircle2,
  "x-circle": XCircle,
  // Extrapolação: adicionados para ProductsPage/ListasPage (novo item, editar, remover)
  // — não fazem parte do mapa original.
  plus: Plus,
  pencil: Pencil,
  "trash-2": Trash2,
  // Extrapolação: adicionados para PostsPage.tsx (publicar agora, gerar texto com IA,
  // spinners de loading, badge "Agendado") — não fazem parte do mapa original.
  "loader-2": Loader2,
  sparkles: Sparkles,
  send: Send,
  clock: Clock,
  // Extrapolação: adicionados para LoginPage.tsx (toggle mostrar/ocultar senha)
  // — não fazem parte do mapa original.
  eye: Eye,
  "eye-off": EyeOff,
  // Extrapolação: adicionados para LoginPage.tsx (split-screen: ícones nos campos
  // e placeholder do painel de imagem) — não fazem parte do mapa original.
  user: User,
  lock: Lock,
  image: Image,
  // Extrapolação: adicionados para TimelineListCard.tsx (redesign de
  // Produtos/Listas/Usuários em cards com timeline expansível) — não fazem
  // parte do mapa original.
  hash: Hash,
  calendar: Calendar,
  "dollar-sign": DollarSign,
  percent: Percent,
  package: Package,
  "link-2": Link2,
  "chevron-down": ChevronDown,
  // Extrapolação: adicionados para o seletor de visualização (lista/grade) do
  // ProductsPage.tsx (padrão Windows Explorer) — não fazem parte do mapa original.
  list: List,
  "grid-3x3": Grid3x3,
  "layout-grid": LayoutGrid,
  // Extrapolação: adicionado para o nav item de LogsPage.tsx (página de
  // auditoria admin-only) — não faz parte do mapa original.
  "scroll-text": ScrollText,
  // Extrapolação: adicionado para o nav item de HelpPage.tsx (Ajuda & FAQ)
  // — não faz parte do mapa original.
  "help-circle": HelpCircle,
}

export function Icon({ name, size = 20, strokeWidth = 1.75, className = "", style }: IconProps) {
  const LucideIcon = ICONS[name]
  if (!LucideIcon) return null
  return (
    <LucideIcon
      size={size}
      strokeWidth={strokeWidth}
      className={className}
      style={{ display: "inline-flex", flex: "0 0 auto", ...style }}
      aria-hidden="true"
    />
  )
}
