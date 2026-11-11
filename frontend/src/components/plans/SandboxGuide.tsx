import "./planCheckout.css"

/** Cartões fictícios do sandbox do Asaas (documentação "Testando pagamento com cartão de crédito", lida em 11/11/2026). */
const TEST_CARDS = [
  { brand: "Visa", number: "4539 6560 4839 2220" },
  { brand: "Mastercard", number: "5263 8372 5327 8275" },
  { brand: "American Express", number: "3471 756966 23141" },
  { brand: "Discover", number: "6011 6650 7493 0565" },
]

/** Só aparece quando o servidor informa que a cobrança está no sandbox; em produção não é exibido. */
export function SandboxGuide() {
  return (
    <section className="plan-checkout plan-sandbox" aria-labelledby="plan-sandbox-title">
      <h2 id="plan-sandbox-title">Ambiente de teste: nada é cobrado de verdade</h2>
      <p>Este é o ambiente de homologação. Use apenas dados fictícios; nunca digite um cartão real aqui.</p>
      <div className="plan-sandbox__cols">
        <div>
          <h3>Cartão de crédito</h3>
          <table>
            <thead><tr><th scope="col">Bandeira</th><th scope="col">Número de teste</th></tr></thead>
            <tbody>{TEST_CARDS.map((c) => <tr key={c.brand}><td>{c.brand}</td><td><code>{c.number}</code></td></tr>)}</tbody>
          </table>
          <p>Validade: qualquer data futura. Código de segurança: qualquer número (3 dígitos; 4 na American Express).
            Titular: nome fictício. CPF e endereço: use dados fictícios.</p>
        </div>
        <div>
          <h3>Pix (Pix Automático)</h3>
          <p>Escolha Pix para gerar o QR Code aqui mesmo. No teste não há banco pagando: simule o pagamento da
            cobrança Pix pelo painel do Asaas Sandbox. Depois que o Asaas avisar o site, o plano muda (pode levar
            alguns minutos). Se o Asaas Sandbox não liberar o Pix Automático nesta conta, o motivo aparece na tela.</p>
        </div>
      </div>
      <p className="plan-checkout__fine">Dados de teste conforme a documentação do Asaas; se o Asaas os alterar, vale a
        documentação deles.</p>
    </section>
  )
}
