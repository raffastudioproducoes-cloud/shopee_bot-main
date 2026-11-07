/** Catálogo visual da página de credenciais. Integrações futuras não possuem API. */
export type CredentialTab = "stores" | "social"

export type FuturePlatform = {
  key: string
  title: string
  category: CredentialTab
  detail: string
}

export const FUTURE_CREDENTIAL_PLATFORMS: readonly FuturePlatform[] = [
  { key: "aliexpress", title: "AliExpress", category: "stores", detail: "A integração de afiliados do AliExpress será disponibilizada após homologação." },
  { key: "amazon", title: "Amazon", category: "stores", detail: "A integração ao programa de associados da Amazon está planejada." },
  { key: "americanas", title: "Americanas", category: "stores", detail: "O cadastro de afiliado da Americanas será habilitado futuramente." },
  { key: "awin", title: "Rede Awin", category: "stores", detail: "A integração com a rede de afiliados Awin está planejada." },
  { key: "lomadee", title: "Rede Lomadee", category: "stores", detail: "A integração com a plataforma de afiliados Lomadee está planejada." },
  { key: "magalu", title: "Magazine Luiza", category: "stores", detail: "O cadastro de parceiros do Magazine Luiza será habilitado futuramente." },
  { key: "mercadolivre", title: "Mercado Livre", category: "stores", detail: "O programa de afiliados do Mercado Livre terá integração futura." },
  { key: "natura-avon", title: "Natura e Avon", category: "stores", detail: "Os programas de afiliados de Natura e Avon serão avaliados antes de habilitar conexões." },
  { key: "prospin", title: "Pró Spin", category: "stores", detail: "A integração com o programa de parceiros Pró Spin está planejada." },
  { key: "rakuten", title: "Rede Rakuten", category: "stores", detail: "A integração com os programas da rede Rakuten está planejada." },
  { key: "shein", title: "SHEIN", category: "stores", detail: "O cadastro de afiliados da SHEIN será disponibilizado futuramente." },
  { key: "terabyteshop", title: "TerabyteShop", category: "stores", detail: "A integração com parceiros da TerabyteShop está planejada." },
  { key: "telegram", title: "Telegram", category: "social", detail: "O envio para canais ou grupos no Telegram será habilitado após implementação e homologação." },
  { key: "whatsapp", title: "WhatsApp", category: "social", detail: "A conexão ao WhatsApp depende de uma integração própria e não está disponível nesta página." },
] as const

export const CREDENTIAL_BRAND_LOGOS: Readonly<Record<string, readonly string[]>> = {
  aliexpress: ["aliexpress.svg"], amazon: ["amazon.svg"], americanas: ["americanas.svg"],
  awin: ["awin.svg"], facebook: ["facebook.svg"], instagram: ["instagram.svg"],
  kwai: ["kwai.svg"], lomadee: ["lomadee.svg"], magalu: ["magalu.svg"],
  mercadolivre: ["mercadolivre.svg"], "natura-avon": ["natura.svg", "avon.svg"],
  prospin: ["prospin.png"], rakuten: ["rakuten.svg"], shein: ["shein.svg"],
  shopee: ["shopee.svg"], "shopee-video": ["shopee.svg"],
  telegram: ["telegram.svg"], terabyteshop: ["terabyteshop.png"],
  threads: ["threads.svg"], tiktok: ["tiktok.svg"], whatsapp: ["whatsapp.svg"], x: ["x.svg"],
}

/** O diagnóstico ADMIN inclui toda plataforma catalogada, mas só testa conexões reais.
 * A Shopee (API global) já tem cartão de gerenciamento próprio acima dos resultados.
 */
export type AdminDiagnosticPlatform = {
  key: string
  title: string
  category: CredentialTab
  availability: "active" | "planned"
}

const ACTIVE_SOCIAL_DIAGNOSTICS: readonly { key: string; title: string }[] = [
  { key: "facebook", title: "Facebook" },
  { key: "instagram", title: "Instagram" },
  { key: "kwai", title: "Kwai" },
  { key: "threads", title: "Threads" },
  { key: "tiktok", title: "TikTok" },
  { key: "x", title: "X (Twitter)" },
]

export function buildAdminDiagnosticSections(): Record<CredentialTab, AdminDiagnosticPlatform[]> {
  const platforms: AdminDiagnosticPlatform[] = [
    ...ACTIVE_SOCIAL_DIAGNOSTICS.map(({ key, title }) => ({
      key, title, category: "social" as const, availability: "active" as const,
    })),
    { key: "shopee-video", title: "Shopee Vídeo", category: "social", availability: "planned" },
    ...FUTURE_CREDENTIAL_PLATFORMS.map(({ key, title, category }) => ({
      key, title, category, availability: "planned" as const,
    })),
  ]
  const byTitle = new Intl.Collator("pt-BR", { sensitivity: "base" })
  const sorted = platforms.sort((a, b) => byTitle.compare(a.title, b.title))
  return {
    stores: sorted.filter(platform => platform.category === "stores"),
    social: sorted.filter(platform => platform.category === "social"),
  }
}
