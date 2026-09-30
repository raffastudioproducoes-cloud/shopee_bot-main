import { useState } from "react"
import { Panel, PanelHeader } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { SegmentedToggle, type SegmentedOption } from "../components/ui/SegmentedToggle"

const SUPPORT_EMAIL = "raffastudioproducoes@gmail.com"

type HelpTab = "shopee" | "primeiros-passos" | "faq"

const TABS: SegmentedOption[] = [
  { value: "shopee", label: "Tutorial Shopee", icon: "key-round" },
  { value: "primeiros-passos", label: "Primeiros Passos", icon: "sparkles" },
  { value: "faq", label: "FAQ", icon: "message-square" },
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

export function HelpPage() {
  const [tab, setTab] = useState<HelpTab>(readInitialTab)

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

      <SegmentedToggle options={TABS} value={tab} onChange={(v) => setTab(v as HelpTab)} fullWidth={false} />

      <Panel surface="dark">
        <PanelHeader title={TABS.find((t) => t.value === tab)?.label ?? ""} />
        <div style={{ padding: "0 16px 16px" }}>
          {tab === "shopee" && (
            <p style={{ margin: 0, color: "var(--text-muted)", font: "var(--text-role-body)" }}>
              Em breve: passo a passo com prints de como gerar seu App ID e Secret na Shopee.
            </p>
          )}
          {tab === "primeiros-passos" && (
            <p style={{ margin: 0, color: "var(--text-muted)", font: "var(--text-role-body)" }}>
              Em breve.
            </p>
          )}
          {tab === "faq" && (
            <p style={{ margin: 0, color: "var(--text-muted)", font: "var(--text-role-body)" }}>
              Em breve.
            </p>
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
