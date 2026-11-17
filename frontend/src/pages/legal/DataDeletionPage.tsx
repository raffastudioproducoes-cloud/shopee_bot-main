import { LegalLayout } from './LegalLayout'

// Página pública de instruções de exclusão de dados (/exclusao-de-dados), usada como
// "Data deletion instructions URL" na Meta e citada na revisão do TikTok.

const EMAIL = 'contato.raffasp@gmail.com'
const MAILTO_PT = `mailto:${EMAIL}?subject=${encodeURIComponent('Exclusão de dados - Auto Orbital')}`
const MAILTO_EN = `mailto:${EMAIL}?subject=${encodeURIComponent('Data deletion - Auto Orbital')}`

function DataDeletionPt() {
  return (
    <>
      <p>Você pode desconectar suas redes sociais e pedir a exclusão da sua conta e dos seus dados do Auto Orbital a qualquer momento. Não é preciso estar logado para ler estas instruções.</p>

      <h2>1. Desconectar uma rede social</h2>
      <ol>
        <li>Entre no Auto Orbital e abra <strong>Credenciais</strong> no menu.</li>
        <li>No cartão da rede (Threads, Instagram, Facebook, TikTok ou X), clique em <strong>Desconectar</strong>.</li>
        <li>O token daquela rede é apagado do nosso servidor na hora e o app deixa de publicar nela.</li>
      </ol>

      <h2>2. Remover o app direto na rede</h2>
      <ul>
        <li><strong>Facebook e Instagram:</strong> Configurações e privacidade → Configurações → Apps e sites (ou Integrações empresariais) → Auto Orbital → Remover. Ao remover, você pode marcar a opção de excluir as atividades/dados; a Meta nos avisa automaticamente e apagamos as credenciais e os dados vinculados àquela conta.</li>
        <li><strong>Threads:</strong> Configurações → Conta → Sites e apps → Auto Orbital → Remover. A Meta também nos avisa automaticamente.</li>
        <li><strong>TikTok:</strong> Configurações e privacidade → Segurança e permissões → Apps e serviços → Auto Orbital → Remover acesso.</li>
        <li><strong>X:</strong> Configurações → Segurança e acesso à conta → Apps e sessões → Apps conectados → Auto Orbital → Revogar permissões.</li>
      </ul>

      <h2>3. Excluir a conta e todos os dados</h2>
      <ol>
        <li>(Opcional) Em <strong>Configurações → Backup e dados</strong>, clique em <strong>Exportar backup</strong> para guardar uma cópia em JSON.</li>
        <li>Na mesma seção, clique em <strong>Excluir minha conta e dados</strong> e confirme com sua senha.</li>
        <li>Se o painel avisar que a exclusão ainda não está disponível, ou se você não consegue entrar, envie um e-mail para <a href={MAILTO_PT}><strong>{EMAIL}</strong></a> a partir do e-mail da sua conta, com o assunto "Exclusão de dados - Auto Orbital".</li>
        <li>Confirmamos o pedido e concluímos a exclusão em até 15 dias, informando por e-mail. São apagados: perfil e cadastro, credenciais e tokens das redes, produtos, listas, posts, mídias e métricas. Guardamos apenas o que a lei obriga (por exemplo, registros de pagamento e fiscais) e os eventos de auditoria imutáveis.</li>
      </ol>

      <h2>4. Pedidos automáticos da Meta</h2>
      <p>Quando você remove o app no Facebook, Instagram ou Threads, a Meta envia um pedido assinado para os endereços abaixo. Nós apagamos as credenciais vinculadas àquela conta e devolvemos à Meta um código de confirmação e um link onde é possível acompanhar o status do pedido.</p>
      <ul>
        <li>Exclusão de dados (Facebook/Instagram): <code>https://shopee-bot-fj0w.onrender.com/api/meta/data-deletion</code></li>
        <li>Desautorização (Facebook/Instagram): <code>https://shopee-bot-fj0w.onrender.com/api/meta/deauthorize</code></li>
        <li>Threads: <code>/api/threads/delete</code> e <code>/api/threads/uninstall</code></li>
      </ul>

      <h2>5. Contato</h2>
      <p>Dúvidas sobre seus dados: <a href={MAILTO_PT}>{EMAIL}</a>. Veja também a <a href="/privacidade">Política de Privacidade</a> e a página <a href="/dados-coletados">Dados coletados</a>.</p>
    </>
  )
}

function DataDeletionEn() {
  return (
    <>
      <p>You can disconnect your social accounts and request deletion of your Auto Orbital account and data at any time. You do not need to be signed in to read these instructions.</p>

      <h2>1. Disconnect a social network</h2>
      <ol>
        <li>Sign in to Auto Orbital and open <strong>Credentials</strong> (Credenciais) in the menu.</li>
        <li>On the network's card (Threads, Instagram, Facebook, TikTok or X), click <strong>Disconnect</strong> (Desconectar).</li>
        <li>That network's token is erased from our server immediately and the app stops publishing to it.</li>
      </ol>

      <h2>2. Remove the app from the network itself</h2>
      <ul>
        <li><strong>Facebook and Instagram:</strong> Settings &amp; privacy → Settings → Apps and websites (or Business integrations) → Auto Orbital → Remove. You can also choose to delete the app's activity/data; Meta notifies us automatically and we erase the credentials and data linked to that account.</li>
        <li><strong>Threads:</strong> Settings → Account → Websites and apps → Auto Orbital → Remove. Meta also notifies us automatically.</li>
        <li><strong>TikTok:</strong> Settings and privacy → Security and permissions → Apps and services → Auto Orbital → Remove access.</li>
        <li><strong>X:</strong> Settings → Security and account access → Apps and sessions → Connected apps → Auto Orbital → Revoke app permissions.</li>
      </ul>

      <h2>3. Delete your account and all data</h2>
      <ol>
        <li>(Optional) In <strong>Settings → Backup e dados</strong>, click <strong>Exportar backup</strong> to keep a JSON copy.</li>
        <li>In the same section, click <strong>Excluir minha conta e dados</strong> (Delete my account and data) and confirm with your password.</li>
        <li>If the dashboard says self-service deletion is not available yet, or you cannot sign in, email <a href={MAILTO_EN}><strong>{EMAIL}</strong></a> from your account email with the subject "Data deletion - Auto Orbital".</li>
        <li>We confirm the request and complete the deletion within 15 days, and let you know by email. We delete: profile and registration, social network credentials and tokens, products, lists, posts, media and metrics. We keep only what the law requires (for example, payment and tax records) and immutable audit events.</li>
      </ol>

      <h2>4. Automatic requests from Meta</h2>
      <p>When you remove the app on Facebook, Instagram or Threads, Meta sends a signed request to the endpoints below. We erase the credentials linked to that account and return to Meta a confirmation code and a link where the request status can be checked.</p>
      <ul>
        <li>Data deletion (Facebook/Instagram): <code>https://shopee-bot-fj0w.onrender.com/api/meta/data-deletion</code></li>
        <li>Deauthorization (Facebook/Instagram): <code>https://shopee-bot-fj0w.onrender.com/api/meta/deauthorize</code></li>
        <li>Threads: <code>/api/threads/delete</code> and <code>/api/threads/uninstall</code></li>
      </ul>

      <h2>5. Contact</h2>
      <p>Questions about your data: <a href={MAILTO_EN}>{EMAIL}</a>. See also the <a href="/privacidade?lang=en">Privacy Policy</a> and <a href="/dados-coletados?lang=en">Data we collect</a>.</p>
    </>
  )
}

export function DataDeletionPage() {
  return (
    <LegalLayout
      title={{ pt: 'Exclusão de dados', en: 'Data deletion' }}
      updatedAt={{ pt: '17 de novembro de 2026', en: 'November 17, 2026' }}
    >
      {(lang) => (lang === 'en' ? <DataDeletionEn /> : <DataDeletionPt />)}
    </LegalLayout>
  )
}
