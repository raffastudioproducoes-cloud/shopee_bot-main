import { COMPANY } from '../../lib/company'

/** Bloco "Identificação do controlador" das páginas legais (Termos e Privacidade), em PT e EN. */
export function CompanyIdentification({ lang, doc }: { lang: 'pt' | 'en'; doc: 'terms' | 'privacy' }) {
  if (lang === 'en') {
    return (
      <>
        <h2>1.1 Controller identification</h2>
        <ul>
          <li><strong>Business name:</strong> {COMPANY.legalName} (individual microentrepreneur, MEI)</li>
          <li><strong>Trade name:</strong> {COMPANY.tradeName}</li>
          <li><strong>CNPJ (Brazilian company registry):</strong> {COMPANY.cnpj}</li>
          <li><strong>Business address:</strong> {COMPANY.addressEn}</li>
          <li><strong>Contact:</strong> {COMPANY.email}</li>
        </ul>
        <p>
          {doc === 'privacy'
            ? <>The company above is the controller of personal data under art. 5, VI of the LGPD. Data subjects can exercise their rights through the contact email above.</>
            : <>The company above is the supplier of the service and the controller of personal data under art. 5, VI of the LGPD (see the Privacy Policy).</>}
        </p>
      </>
    )
  }
  return (
    <>
      <h2>1.1 Identificação do controlador</h2>
      <ul>
        <li><strong>Nome empresarial:</strong> {COMPANY.legalName} (microempreendedor individual, MEI)</li>
        <li><strong>Nome fantasia:</strong> {COMPANY.tradeName}</li>
        <li><strong>CNPJ:</strong> {COMPANY.cnpj}</li>
        <li><strong>Endereço comercial:</strong> {COMPANY.address}</li>
        <li><strong>Contato:</strong> {COMPANY.email}</li>
      </ul>
      <p>
        {doc === 'privacy'
          ? <>A empresa acima é a controladora dos dados pessoais, nos termos do art. 5º, VI, da LGPD. O titular pode exercer seus direitos pelo e-mail de contato acima.</>
          : <>A empresa acima é a fornecedora do serviço e controladora dos dados pessoais, nos termos do art. 5º, VI, da LGPD (veja a Política de Privacidade).</>}
      </p>
    </>
  )
}
