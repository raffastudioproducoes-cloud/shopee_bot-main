import type { SiteLang } from "../../lib/siteLang"
import { LoginLink } from "./shared"

// Seção institucional bilíngue da página pública: o que é o app, para quem, recursos,
// como a conexão das contas funciona e quais permissões pedimos (revisão Meta/TikTok/X).

export const SUPPORT_EMAIL = "contato.raffasp@gmail.com"

interface Permission { network: string; scopes: string; why: string }

interface InfoText {
  eyebrow: string
  title: string
  intro: string
  audienceTitle: string
  audience: string
  featuresTitle: string
  features: string[]
  connectTitle: string
  connect: string[]
  permissionsTitle: string
  permissionsIntro: string
  permissions: Permission[]
  publicTitle: string
  publicText: string
  cta: string
  legalTitle: string
}

export const appInfo: Record<SiteLang, InfoText> = {
  pt: {
    eyebrow: "Sobre o Auto Orbital",
    title: "O que é o Auto Orbital",
    intro: "O Auto Orbital é um aplicativo web (SaaS) da Raffa Studio Produções que ajuda afiliados e criadores de conteúdo a preparar, agendar e publicar posts nas suas próprias contas de redes sociais, a partir de um único painel.",
    audienceTitle: "Para quem é",
    audience: "Afiliados da Shopee, criadores de conteúdo e pequenos negócios que divulgam produtos nas redes sociais. Qualquer pessoa maior de 18 anos pode criar uma conta.",
    featuresTitle: "Funcionalidades",
    features: [
      "Agendar e publicar posts em Threads, Instagram, Facebook (Páginas), TikTok e X.",
      "Publicar agora ou em data e hora escolhidas, com texto e mídia editáveis antes do envio.",
      "Ver as métricas de cada post publicado pelo app (visualizações, curtidas, comentários, compartilhamentos) no Threads, Instagram e Facebook.",
      "Montar campanhas a partir de listas de produtos, com agenda por dia e por rede.",
      "Buscar produtos da Shopee pela API oficial de afiliados e organizar listas.",
    ],
    connectTitle: "Como funciona a conexão das contas",
    connect: [
      "Cada rede é conectada pelo próprio usuário, na página Credenciais, pelo login oficial da rede (OAuth). O usuário vê a tela da rede, revisa as permissões e decide se autoriza.",
      "Os tokens de acesso ficam cifrados no servidor e nunca são exibidos no navegador.",
      "O app só publica no perfil do próprio usuário e apenas o conteúdo que ele criou e mandou publicar ou agendou.",
      "O usuário pode desconectar qualquer rede a qualquer momento em Credenciais, ou remover o app nas configurações da própria rede.",
    ],
    permissionsTitle: "Permissões que pedimos e para quê",
    permissionsIntro: "Pedimos apenas as permissões necessárias para publicar e mostrar as métricas dos posts do próprio usuário.",
    permissions: [
      { network: "Instagram (Meta)", scopes: "instagram_basic, instagram_content_publish, instagram_manage_insights, pages_show_list, pages_read_engagement", why: "Identificar a conta profissional do Instagram ligada à Página, publicar os posts do usuário e ler as métricas desses posts." },
      { network: "Facebook (Meta)", scopes: "pages_show_list, pages_read_engagement, pages_manage_posts, read_insights", why: "Listar as Páginas que o usuário administra, publicar na Página escolhida e ler as métricas desses posts." },
      { network: "Threads (Meta)", scopes: "threads_basic, threads_content_publish, threads_manage_insights", why: "Identificar o perfil, publicar os posts do usuário e ler as métricas desses posts." },
      { network: "TikTok", scopes: "user.info.basic, video.publish, video.upload", why: "Identificar a conta conectada (nome de exibição) e enviar o vídeo que o usuário escolheu publicar no próprio perfil." },
      { network: "X", scopes: "tweet.read, tweet.write, users.read, media.write, offline.access", why: "Identificar a conta, publicar os posts e mídias do usuário e manter a conexão ativa sem novo login a cada envio." },
    ],
    publicTitle: "Aberto ao público",
    publicText: "O Auto Orbital é um produto público, aberto a qualquer afiliado ou criador que crie uma conta. Não é uma ferramenta interna nem de uso pessoal.",
    cta: "Entrar ou criar conta",
    legalTitle: "Documentos e contato",
  },
  en: {
    eyebrow: "About Auto Orbital",
    title: "What is Auto Orbital",
    intro: "Auto Orbital is a web app (SaaS) by Raffa Studio Produções that helps affiliates and content creators prepare, schedule and publish posts on their own social media accounts from a single dashboard.",
    audienceTitle: "Who it is for",
    audience: "Shopee affiliates, content creators and small businesses that promote products on social media. Anyone aged 18 or over can create an account.",
    featuresTitle: "Features",
    features: [
      "Schedule and publish posts to Threads, Instagram, Facebook (Pages), TikTok and X.",
      "Publish now or at a chosen date and time, with text and media editable before sending.",
      "See metrics for each post published through the app (views, likes, comments, shares) on Threads, Instagram and Facebook.",
      "Build campaigns from product lists, with a schedule per day and per network.",
      "Search Shopee products through the official affiliate API and organize them in lists.",
    ],
    connectTitle: "How account connection works",
    connect: [
      "Users connect each network themselves on the Credentials page through the network's official login (OAuth). They see the network's own screen, review the permissions and decide whether to authorize.",
      "Access tokens are stored encrypted on the server and are never shown in the browser.",
      "The app only publishes to the user's own profile, and only content the user created and chose to publish or schedule.",
      "Users can disconnect any network at any time on the Credentials page, or remove the app in the network's own settings.",
    ],
    permissionsTitle: "Permissions we request and why",
    permissionsIntro: "We only request the permissions needed to publish and to show metrics for the user's own posts.",
    permissions: [
      { network: "Instagram (Meta)", scopes: "instagram_basic, instagram_content_publish, instagram_manage_insights, pages_show_list, pages_read_engagement", why: "Identify the Instagram professional account linked to the Page, publish the user's posts and read metrics for those posts." },
      { network: "Facebook (Meta)", scopes: "pages_show_list, pages_read_engagement, pages_manage_posts, read_insights", why: "List the Pages the user manages, publish to the chosen Page and read metrics for those posts." },
      { network: "Threads (Meta)", scopes: "threads_basic, threads_content_publish, threads_manage_insights", why: "Identify the profile, publish the user's posts and read metrics for those posts." },
      { network: "TikTok", scopes: "user.info.basic, video.publish, video.upload", why: "Identify the connected account (display name) and send the video the user chose to publish to their own profile." },
      { network: "X", scopes: "tweet.read, tweet.write, users.read, media.write, offline.access", why: "Identify the account, publish the user's posts and media, and keep the connection active without a new login for every post." },
    ],
    publicTitle: "Open to the public",
    publicText: "Auto Orbital is a public product, open to any affiliate or creator who signs up. It is not an internal or personal-use tool.",
    cta: "Sign in or create an account",
    legalTitle: "Documents and contact",
  },
}

interface LegalLink { href: string; label: string }

export function legalLinks(lang: SiteLang): LegalLink[] {
  return lang === "en"
    ? [
        { href: "/termos?lang=en", label: "Terms of Service" },
        { href: "/privacidade?lang=en", label: "Privacy Policy" },
        { href: "/exclusao-de-dados?lang=en", label: "Data deletion" },
        { href: "/dados-coletados?lang=en", label: "Data we collect" },
        { href: `mailto:${SUPPORT_EMAIL}`, label: "Contact / Support" },
      ]
    : [
        { href: "/termos?lang=pt", label: "Termos de Uso" },
        { href: "/privacidade?lang=pt", label: "Privacidade" },
        { href: "/exclusao-de-dados?lang=pt", label: "Exclusão de dados" },
        { href: "/dados-coletados?lang=pt", label: "Dados coletados" },
        { href: `mailto:${SUPPORT_EMAIL}`, label: "Contato / Suporte" },
      ]
}

const card = "rounded-2xl border border-ao-border bg-ao-card/60 p-6"
const heading = "font-ao-display text-xl font-semibold text-ao-fg"

export function AppInfoSection({ lang, first = false }: { lang: SiteLang; first?: boolean }) {
  const t = appInfo[lang]
  return (
    <section id="sobre" aria-labelledby="ao-about-title" className={`mx-auto max-w-7xl px-6 ${first ? "pb-24 pt-12 md:pt-36" : "py-24"}`} lang={lang === "en" ? "en" : "pt-BR"}>
      <p className="font-ao-display text-xs font-semibold uppercase tracking-[0.3em] text-ao-primary">{t.eyebrow}</p>
      <h2 id="ao-about-title" className="mt-4 font-ao-display text-4xl font-bold tracking-tight md:text-5xl">{t.title}</h2>
      <p className="mt-6 max-w-3xl text-lg">{t.intro}</p>

      <div className="mt-12 grid gap-6 md:grid-cols-2">
        <div className={card}>
          <h3 className={heading}>{t.audienceTitle}</h3>
          <p className="mt-3 text-ao-muted-fg">{t.audience}</p>
          <h3 className={`${heading} mt-6`}>{t.publicTitle}</h3>
          <p className="mt-3 text-ao-muted-fg">{t.publicText}</p>
        </div>
        <div className={card}>
          <h3 className={heading}>{t.featuresTitle}</h3>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-ao-muted-fg">
            {t.features.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
      </div>

      <div className={`${card} mt-6`}>
        <h3 className={heading}>{t.connectTitle}</h3>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-ao-muted-fg">
          {t.connect.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </div>

      <div className={`${card} mt-6`}>
        <h3 className={heading}>{t.permissionsTitle}</h3>
        <p className="mt-3 text-ao-muted-fg">{t.permissionsIntro}</p>
        <dl className="mt-4 divide-y divide-ao-border">
          {t.permissions.map((p) => (
            <div key={p.network} className="grid gap-1 py-4 md:grid-cols-[12rem_1fr] md:gap-6">
              <dt className="font-semibold text-ao-fg">{p.network}</dt>
              <dd>
                <code className="break-words text-sm text-ao-primary">{p.scopes}</code>
                <p className="mt-1 text-sm text-ao-muted-fg">{p.why}</p>
              </dd>
            </div>
          ))}
        </dl>
      </div>

      <div className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-3">
        <LoginLink className="ao-btn-primary">{t.cta}</LoginLink>
        <nav aria-label={t.legalTitle} className="flex flex-wrap gap-x-5 gap-y-2 text-sm font-semibold">
          {legalLinks(lang).map((l) => <a key={l.href} href={l.href} className="underline underline-offset-4 hover:text-ao-primary">{l.label}</a>)}
        </nav>
      </div>
    </section>
  )
}
