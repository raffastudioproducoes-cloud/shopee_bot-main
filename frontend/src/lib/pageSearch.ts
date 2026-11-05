/**
 * Busca textual contextual usada pelos filtros locais de páginas.
 * Produtos salvos preservam a busca paginada do backend (api/product_search.py).
 * Nunca usa campos de outras páginas nem altera o escopo da API.
 */
export type SearchPage = "products" | "posts" | "lists"

export function searchPageForRoute(pathname: string, productsTab: "mine" | "catalog"): SearchPage | null {
  if (pathname === "/products") return productsTab === "mine" ? "products" : null
  if (pathname === "/posts") return "posts"
  if (pathname === "/lists") return "lists"
  return null
}

export function normalizeSearchText(value: string): string {
  return value.normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("pt-BR")
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .replace(/\s+/g, " ").trim()
}

const groupTerms = [
  {
    triggers: ["quarto", "quartos", "dormitorio", "dormitorios"],
    terms: ["cama", "lencol", "colcha", "travesseiro", "fronha", "edredom",
      "cobertor", "colchao", "cabeceira", "guarda roupa", "penteadeira",
      "abajur", "criado mudo", "cortina", "roupa de cama", "organizador"],
  },
  {
    triggers: ["cozinha", "cozinhas"],
    terms: ["fogao", "cooktop", "panela", "frigideira", "air fryer",
      "fritadeira", "talher", "geladeira", "microondas", "liquidificador",
      "batedeira", "cafeteira", "organizador"],
  },
  {
    triggers: ["banheiro", "banheiros", "lavabo"],
    terms: ["chuveiro", "ducha", "box", "vaso sanitario", "toalha", "tapete",
      "saboneteira", "espelho", "porta escova"],
  },
  {
    triggers: ["sala", "salas", "living", "sala de estar"],
    terms: ["sofa", "rack", "painel tv", "mesa de centro", "poltrona",
      "almofada", "cortina", "tapete", "luminaria"],
  },
] as const

const carWashTerms = [
  "lavadora de carro", "lava jato", "lava a jato", "lavadora de alta pressao",
  "lavadora de pressao", "hidrolavadora", "lavadora wap", "wap", "vap",
  "jato de agua",
] as const

/** Alternativas textuais limitadas, sem IA externa nem chamada ao servidor. */
export function contextualSearchTerms(raw: string): string[] {
  const query = normalizeSearchText(raw.slice(0, 100))
  if (!query) return []
  const tokens = new Set(query.split(" "))
  const normalized = new Set<string>([query])
  const carWash = ["wap", "vap", "hidrolavadora"].some((token) => tokens.has(token))
    || query.includes("lava jato") || query.includes("lava a jato")
    || query.includes("alta pressao")
    || (tokens.has("lavadora") && ["carro", "carros", "veiculo", "veiculos", "pressao"].some((token) => tokens.has(token)))
  if (carWash) for (const term of carWashTerms) normalized.add(normalizeSearchText(term))
  for (const group of groupTerms) {
    if (group.triggers.some((trigger) => trigger.includes(" ") ? query.includes(trigger) : tokens.has(trigger))) {
      for (const term of group.terms) normalized.add(normalizeSearchText(term))
    }
  }
  return [...normalized].slice(0, 26)
}

/** A consulta considera apenas os campos que a página chamou explicitamente. */
export function matchesScopedSearch(
  fields: readonly (string | number | null | undefined)[], query: string,
): boolean {
  const terms = contextualSearchTerms(query)
  if (terms.length === 0) return true
  const text = normalizeSearchText(fields.filter((field) => field != null).join(" "))
  if (text.includes(terms[0])) return true
  const queryTokens = terms[0].split(" ").filter((token) => token.length > 1)
  const textTokens = text.split(" ")
  if (queryTokens.length > 1 && queryTokens.every((token) => textTokens.some((word) => word.startsWith(token)))) return true
  return terms.slice(1).some((term) => text.includes(term))
}
