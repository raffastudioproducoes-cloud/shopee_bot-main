// Aba "Limites das redes" da Ajuda. Informativa, visível a todos os papéis.
import { NetworkLogo, PICKER_NETWORKS } from "../posts/NetworkPicker"
import { NETWORK_RULES } from "../../lib/networkLimits"
import {
  CONSULTADO_EM,
  NETWORK_HELP,
  imageSummary,
  linksSummary,
  mediaSummary,
  ruleRows,
  textSummary,
  videoSummary,
} from "../../lib/networkHelp"

const body = "var(--text-role-body)"
const small = "var(--fw-regular) var(--fs-caption)/1.5 var(--font-sans)"
const strong = "var(--fw-semibold) var(--fs-body)/1.3 var(--font-sans)"
const cardStyle = {
  padding: 14,
  borderRadius: "var(--r-md)",
  background: "var(--panel-glass-quiet)",
  border: "1px solid var(--border-card)",
} as const

function Unconfirmed() {
  return <strong className="csp-s-0010"> (não confirmado)</strong>
}

function Intro() {
  return (
    <div style={{ ...cardStyle, display: "flex", flexDirection: "column", gap: 6 }}>
      <p style={{ margin: 0, font: body, color: "var(--text-muted)" }}>
        <strong className="csp-s-0011">Consultado em {CONSULTADO_EM}</strong> nas documentações oficiais de cada rede.
        Esses limites mudam: se algo divergir, vale a fonte oficial (link em cada card).
      </p>
      <p style={{ margin: 0, font: body, color: "var(--text-muted)" }}>
        O criador de post usa exatamente estes limites para bloquear redes incompatíveis com o seu texto e a sua mídia.
      </p>
      <p style={{ margin: 0, font: body, color: "var(--text-muted)" }}>
        Se as redes marcadas têm limites de texto diferentes (ex.: X com 280 e Instagram com 2.200), a caixa "Texto do post" ganha abas:
        um texto por faixa de limite, e cada rede publica o texto da sua aba. O "Gerar texto com IA" já preenche todas as abas de uma vez.
      </p>
    </div>
  )
}

function CompareTable() {
  return (
    <section aria-labelledby="limits-compare">
      <h3 id="limits-compare" style={{ margin: "0 0 8px", font: strong, color: "var(--text-body)" }}>
        Comparativo
      </h3>
      <div className="csp-s-0012" tabIndex={0} role="region" aria-label="Tabela comparativa de limites (role para o lado)">
        <table className="csp-s-0013">
          <thead>
            <tr>
              {["Rede", "Texto", "Links e tags", "Mídia", "Imagem", "Vídeo"].map((h) => (
                <th key={h} scope="col" className="csp-named-th">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {PICKER_NETWORKS.map((n) => {
              const r = NETWORK_RULES[n]
              return (
                <tr key={n} className="csp-named-row-border">
                  <th scope="row" className="csp-named-th">
                    {r.label}
                  </th>
                  <td className="csp-named-td">
                    {textSummary(r)}
                    {r.unverified.includes("maxChars") && <Unconfirmed />}
                  </td>
                  <td className="csp-named-td">{linksSummary(r)}</td>
                  <td className="csp-named-td">{mediaSummary(r)}</td>
                  <td className="csp-named-td">{imageSummary(r)}</td>
                  <td className="csp-named-td">
                    {videoSummary(r)}
                    {r.unverified.some((k) => k.startsWith("video")) && <Unconfirmed />}
                  </td>
                </tr>
              )
            })}
            <tr className="csp-named-row-border">
              <th scope="row" className="csp-named-th">
                Kwai
              </th>
              <td className="csp-named-td" colSpan={5}>
                Em breve.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  )
}

function NetworkCard({ n }: { n: (typeof PICKER_NETWORKS)[number] }) {
  const help = NETWORK_HELP[n]
  const label = NETWORK_RULES[n].label
  const id = `limits-${n}`
  return (
    <section aria-labelledby={id} style={{ ...cardStyle, display: "flex", flexDirection: "column", gap: 10, minWidth: 0 }}>
      <h3 id={id} style={{ margin: 0, display: "flex", alignItems: "center", gap: 8, font: strong, color: "var(--text-body)" }}>
        <NetworkLogo network={n} />
        {label}
      </h3>
      <div className="csp-s-0014">
        <table className="csp-s-0015">
          <caption className="csp-named-sr-only">Limites do {label}</caption>
          <tbody>
            {[...ruleRows(n), ...help.facts].map((row) => (
              <tr key={row.label} className="csp-named-row-border">
                <th scope="row" style={{ ...th, width: "38%", font: small, color: "var(--text-body)" }}>
                  {row.label}
                </th>
                <td style={{ ...td, font: small }}>
                  {row.value}
                  {row.unconfirmed && <Unconfirmed />}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div>
        <p className="csp-named-subtitle">Dicas</p>
        <ul style={{ margin: 0, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 4, color: "var(--text-muted)", font: small }}>
          {help.tips.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
      </div>
      <div>
        <p className="csp-named-subtitle">Fontes (consultadas em {CONSULTADO_EM})</p>
        <ul style={{ margin: 0, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 4, font: small }}>
          {help.sources.map((s) => (
            <li key={s.url}>
              <a href={s.url} target="_blank" rel="noopener noreferrer" className="csp-s-0016">
                {s.label}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

export function NetworkLimitsHelp() {
  return (
    <div className="csp-s-0017">
      <Intro />
      <CompareTable />
      <div className="csp-s-0018">
        {PICKER_NETWORKS.map((n) => (
          <NetworkCard key={n} n={n} />
        ))}
        <section aria-labelledby="limits-kwai" style={{ ...cardStyle, minWidth: 0 }}>
          <h3 id="limits-kwai" style={{ margin: 0, display: "flex", alignItems: "center", gap: 8, font: strong, color: "var(--text-body)" }}>
            <NetworkLogo network="kwai" />
            Kwai
          </h3>
          <p style={{ margin: "8px 0 0", font: small, color: "var(--text-muted)" }}>
            Em breve. Ainda não há API pública de postagem, então não há limites a documentar.
          </p>
        </section>
      </div>
    </div>
  )
}
