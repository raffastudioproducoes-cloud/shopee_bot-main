import { useState } from "react"
import { Panel, PanelHeader } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { Icon } from "../components/ui/Icon"
import { SegmentedToggle, type SegmentedOption } from "../components/ui/SegmentedToggle"

const SUPPORT_EMAIL = "contato.raffasp@gmail.com"
const SUPPORT_CNPJ = "63.621.332/0001-03"

type HelpTab = "shopee" | "primeiros-passos" | "modulos" | "faq" | "lgpd"

const TABS: SegmentedOption[] = [
  { value: "shopee", label: "Tutorial Shopee", icon: "key-round" },
  { value: "primeiros-passos", label: "Primeiros Passos", icon: "sparkles" },
  { value: "modulos", label: "Guia dos Módulos", icon: "layout-grid" },
  { value: "faq", label: "FAQ", icon: "message-square" },
  { value: "lgpd", label: "Proteção de Dados", icon: "lock" },
]

// Lê ?tab=shopee (ou #shopee) na montagem pra permitir deep-link a partir do
// botão "?" no card da Shopee em CredentialsPage. Padrão de rota (query
// param) escolhido por não exigir mudança no router.tsx (rota única
// "/ajuda", aba selecionada no client).
function readInitialTab(): HelpTab {
  const fromQuery = new URLSearchParams(window.location.search).get("tab")
  const fromHash = window.location.hash.replace("#", "")
  const candidate = fromQuery || fromHash
  return TABS.some((t) => t.value === candidate) ? (candidate as HelpTab) : "primeiros-passos"
}

const STEPS: { title: string; text: string }[] = [
  { title: "Faça login", text: "Entre com seu e-mail e senha na tela inicial." },
  {
    title: "Conecte suas credenciais",
    text:
      "Na aba Credenciais, conecte a Shopee (obrigatória) com App ID e Secret gerados no Portal de Afiliados — use o botão \"?\" no card da Shopee pra ver o tutorial. As redes sociais (Threads, X, Facebook, Instagram, TikTok) conectam com um clique via OAuth. Kwai ainda está \"em breve\".",
  },
  {
    title: "Cadastre produtos",
    text:
      "Em Produtos, cadastre manualmente ou use a aba \"Pesquisa Avançada\" pra importar produtos direto do catálogo real da Shopee.",
  },
  { title: "Organize em Listas", text: "Agrupe os produtos que você cadastrou em Listas pra usar nos seus posts." },
  {
    title: "Crie Posts",
    text: "Monte threads com mídia, agende a publicação e gere a copy com IA se quiser ajuda no texto.",
  },
  { title: "Acompanhe em Logs", text: "Veja o histórico de publicações e o que foi feito em cada uma." },
  {
    title: "Faça backup quando quiser",
    text: "Use o botão de exportar backup na barra superior pra baixar todos os seus dados em JSON.",
  },
]

const MODULES: { icon: string; title: string; text: string }[] = [
  { icon: "house", title: "Dashboard", text: "Visão geral da sua conta: resumo de produtos, listas e posts recentes." },
  {
    icon: "briefcase",
    title: "Produtos",
    text: "Cadastre produtos manualmente ou importe direto do catálogo da Shopee pela aba Pesquisa Avançada.",
  },
  { icon: "sliders-horizontal", title: "Listas", text: "Organize seus produtos em grupos pra usar na hora de criar posts." },
  {
    icon: "file-text",
    title: "Posts",
    text: "Crie threads com mídia, agende publicações e gere copy com IA.",
  },
  {
    icon: "key-round",
    title: "Credenciais",
    text: "Conecte a Shopee (App ID/Secret) e as redes sociais (OAuth com um clique).",
  },
  { icon: "users", title: "Usuários", text: "Gerencie os usuários da conta. Disponível apenas para administradores." },
  { icon: "help-circle", title: "Ajuda & FAQ", text: "Esta página: tutoriais, primeiros passos, dúvidas frequentes e dados." },
  { icon: "scroll-text", title: "Logs", text: "Histórico e auditoria das publicações e ações da conta. Disponível apenas para administradores." },
]

const FAQ_ITEMS: { question: string; answer: string }[] = [
  {
    question: "Meus dados ficam seguros?",
    answer:
      "Sua senha é armazenada com hash bcrypt — nem o próprio sistema consegue ver a senha em texto puro. Os tokens de OAuth das redes sociais são cifrados com Fernet no servidor. E o banco de dados usa Row Level Security (RLS), que bloqueia qualquer acesso direto fora da API oficial.",
  },
  {
    question: "Como conecto minha conta da Shopee?",
    answer:
      "Gere seu App ID e Secret no Portal de Afiliados da Shopee e cole no card \"Shopee\" da aba Credenciais. Se tiver dúvida no passo a passo, clique no botão \"?\" ao lado do link do Portal de Afiliados pra ver o tutorial completo.",
  },
  {
    question: "Por que às vezes preciso reconectar uma rede social?",
    answer:
      "Tokens de OAuth (Threads, X, Facebook, Instagram, TikTok) expiram periodicamente por regra da própria plataforma — isso é normal. Quando expirar, basta clicar em \"Reconectar\" no card da rede em Credenciais.",
  },
  {
    question: "Posso fazer backup dos meus dados?",
    answer:
      "Sim. Use o botão de exportar backup na barra superior do painel — ele baixa um arquivo JSON com todos os seus dados e um checksum de integridade, e pode ser restaurado depois pelo botão de restaurar backup ao lado.",
  },
  {
    question: "Posso excluir minha conta?",
    answer:
      "Sim, também na barra superior. É preciso confirmar sua senha atual, e a ação apaga permanentemente sua conta e todos os dados associados — não tem como desfazer.",
  },
  {
    question: "O que é a Pesquisa Avançada?",
    answer:
      "É uma aba dentro de Produtos que busca no catálogo real da Shopee, permitindo importar um produto encontrado direto pra sua lista, sem digitar os dados manualmente.",
  },
  {
    question: "Preciso conectar todas as redes sociais?",
    answer:
      "Não. A Shopee é a única credencial obrigatória (é dela que vêm os produtos). As redes sociais são opcionais — conecte só as que você usa pra publicar.",
  },
  {
    question: "Por que o Kwai aparece como \"em breve\"?",
    answer:
      "O Kwai ainda não tem API pública de postagem disponível. Assim que isso mudar, o card fica disponível pra todo mundo.",
  },
]

export function HelpPage() {
  const [tab, setTab] = useState<HelpTab>(readInitialTab)
  const [openFaq, setOpenFaq] = useState<number | null>(0)

  const copyEmail = () => {
    navigator.clipboard.writeText(SUPPORT_EMAIL)
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap-column)" }}>
      <div>
        <h1 style={{ font: "var(--text-role-hero)", color: "var(--text-display)", margin: 0 }}>Ajuda & FAQ</h1>
        <p style={{ color: "var(--text-muted)", marginTop: 4 }}>
          Guias, tutoriais e respostas rápidas sobre o Shopee Auto Vendas.
        </p>
      </div>

      <div style={{ maxWidth: "100%", overflowX: "auto", WebkitOverflowScrolling: "touch" }}>
        <SegmentedToggle options={TABS} value={tab} onChange={(v) => setTab(v as HelpTab)} fullWidth={false} />
      </div>

      <Panel surface="dark">
        <PanelHeader title={TABS.find((t) => t.value === tab)?.label ?? ""} />
        <div style={{ padding: "0 16px 16px" }}>
          {tab === "shopee" && (
            <p style={{ margin: 0, color: "var(--text-muted)", font: "var(--text-role-body)" }}>
              Em breve: passo a passo com prints de como gerar seu App ID e Secret na Shopee.
            </p>
          )}
          {tab === "primeiros-passos" && (
            <ol style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 16 }}>
              {STEPS.map((step, i) => (
                <li key={step.title} style={{ display: "flex", gap: 12 }}>
                  <span
                    style={{
                      flexShrink: 0,
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      width: 26,
                      height: 26,
                      borderRadius: "var(--r-pill)",
                      background: "var(--panel-glass-quiet)",
                      color: "var(--text-body)",
                      font: "var(--fw-semibold) var(--fs-small)/1 var(--font-sans)",
                    }}
                  >
                    {i + 1}
                  </span>
                  <div>
                    <p style={{ margin: 0, font: "var(--fw-semibold) var(--fs-body)/1.4 var(--font-sans)", color: "var(--text-body)" }}>
                      {step.title}
                    </p>
                    <p style={{ margin: "2px 0 0", color: "var(--text-muted)", font: "var(--text-role-body)" }}>{step.text}</p>
                  </div>
                </li>
              ))}
            </ol>
          )}
          {tab === "modulos" && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 260px), 1fr))",
                gap: 12,
              }}
            >
              {MODULES.map((mod) => (
                <div
                  key={mod.title}
                  style={{
                    display: "flex",
                    gap: 12,
                    padding: 14,
                    borderRadius: "var(--r-md)",
                    background: "var(--panel-glass-quiet)",
                    border: "1px solid var(--border-card)",
                  }}
                >
                  <Icon name={mod.icon} size={20} />
                  <div>
                    <p style={{ margin: 0, font: "var(--fw-semibold) var(--fs-body)/1.3 var(--font-sans)", color: "var(--text-body)" }}>
                      {mod.title}
                    </p>
                    <p style={{ margin: "2px 0 0", color: "var(--text-muted)", font: "var(--text-role-body)" }}>{mod.text}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
          {tab === "faq" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {FAQ_ITEMS.map((item, i) => {
                const open = openFaq === i
                return (
                  <div key={item.question} style={{ borderRadius: "var(--r-md)", background: "var(--panel-glass-quiet)", overflow: "hidden" }}>
                    <button
                      type="button"
                      onClick={() => setOpenFaq(open ? null : i)}
                      aria-expanded={open}
                      style={{
                        width: "100%",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: 10,
                        padding: "12px 14px",
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        textAlign: "left",
                        font: "var(--fw-semibold) var(--fs-body)/1.3 var(--font-sans)",
                        color: "var(--text-body)",
                      }}
                    >
                      {item.question}
                      <Icon name="chevron-down" size={18} style={{ flexShrink: 0, transform: open ? "rotate(180deg)" : "none", transition: "transform var(--dur-fast) var(--ease-standard)" }} />
                    </button>
                    {open && (
                      <p style={{ margin: 0, padding: "0 14px 14px", color: "var(--text-muted)", font: "var(--text-role-body)" }}>
                        {item.answer}
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          )}
          {tab === "lgpd" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <p style={{ margin: 0, color: "var(--text-muted)", font: "var(--text-role-body)" }}>
                O que o Shopee Auto Vendas realmente faz com seus dados:
              </p>
              <ul style={{ margin: 0, padding: "0 0 0 18px", display: "flex", flexDirection: "column", gap: 8, color: "var(--text-muted)", font: "var(--text-role-body)" }}>
                <li>Sua senha é armazenada com hash bcrypt — irreversível, nem o próprio sistema consegue ver a senha em texto puro.</li>
                <li>Os tokens de OAuth das redes sociais são cifrados com Fernet no servidor, com chave de criptografia própria. Isso não é zero-knowledge: o servidor detém a chave.</li>
                <li>O banco de dados (Supabase) usa Row Level Security (RLS), bloqueando qualquer acesso direto fora da API oficial.</li>
                <li>Direito à portabilidade: você pode exportar um backup de todos os seus dados a qualquer momento, pelo botão na barra superior.</li>
                <li>Direito à exclusão: você pode apagar sua conta e seus dados quando quiser, ação própria e irreversível, também pela barra superior.</li>
              </ul>
            </div>
          )}
        </div>
      </Panel>

      <Panel surface="dark">
        <div
          style={{
            padding: 16,
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
          }}
        >
          <div>
            <p style={{ margin: 0, font: "var(--fw-semibold) var(--fs-body)/1.3 var(--font-sans)", color: "var(--text-body)" }}>
              {SUPPORT_EMAIL}
            </p>
            <p style={{ margin: "2px 0 0", color: "var(--text-muted)", font: "var(--text-role-body)" }}>
              Desenvolvido por Raffa Studio Produções — Empresa registrada desde 2026.
              <br />
              CNPJ {SUPPORT_CNPJ}
            </p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <Button type="button" variant="ghost" icon="link-2" onClick={copyEmail}>
              Copiar e-mail
            </Button>
            <a
              href={`mailto:${SUPPORT_EMAIL}`}
              style={{
                display: "inline-flex",
                alignItems: "center",
                height: 38,
                padding: "0 16px",
                borderRadius: "var(--r-md)",
                background: "#E8F1FB",
                color: "var(--black)",
                font: "var(--fw-semibold) var(--fs-body)/1 var(--font-sans)",
                textDecoration: "none",
              }}
            >
              Enviar mensagem
            </a>
          </div>
        </div>
      </Panel>
    </div>
  )
}
