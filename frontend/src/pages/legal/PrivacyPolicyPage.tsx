import { LegalLayout } from './LegalLayout'

/**
 * Política de Privacidade pública (/privacidade) — LGPD (Lei 13.709/2018).
 *
 * Conteúdo redigido a partir do comportamento real do backend, não de texto
 * genérico: ver api/routers/credentials.py (nunca devolve token/secret ao
 * frontend, delete zera valor sem apagar linha), api/crypto.py (Fernet),
 * api/routers/auth.py (bcrypt + cookie httpOnly/secure/lax) e
 * api/middleware.py (request_logs, desligado por padrão).
 */
export function PrivacyPolicyPage() {
  return (
    <LegalLayout title="Política de Privacidade" updatedAt="28 de setembro de 2026">
      <h2>1. Quem somos</h2>
      <p>
        O ShopeeAutoVendas é um painel de automação que ajuda o usuário a divulgar produtos da
        Shopee em suas próprias redes sociais. O serviço é operado por{' '}
        <strong>Raffa Studio Produções</strong>{' '}
        (<span className="legal-placeholder">completar: razão social completa e CNPJ</span>,
        endereço <span className="legal-placeholder">completar: endereço do controlador</span>),
        que atua como controladora dos dados pessoais tratados nesta plataforma, nos termos da Lei
        nº 13.709/2018 (Lei Geral de Proteção de Dados Pessoais — LGPD).
      </p>

      <h2>2. Quais dados coletamos</h2>
      <p>Coletamos e tratamos os seguintes dados, estritamente para operar o serviço:</p>
      <ul>
        <li>
          <strong>Dados de cadastro:</strong> nome de usuário e senha. A senha nunca é armazenada
          em texto claro — é convertida em hash irreversível (bcrypt) antes de ser gravada, e não
          pode ser recuperada por nós em caso de esquecimento (só redefinida).
        </li>
        <li>
          <strong>Tokens de acesso (OAuth) das redes sociais</strong> que o usuário conectar (X,
          Facebook, Instagram, TikTok, Threads): armazenados cifrados no banco de dados (Fernet,
          criptografia simétrica) e nunca devolvidos ao navegador do usuário — o frontend só
          recebe um indicador de status ("conectado"/"desconectado"), nunca o valor do token.
        </li>
        <li>
          <strong>Credencial da API de afiliados da Shopee</strong> (App ID e Secret que o próprio
          usuário cola no painel): armazenada cifrada da mesma forma, validada ao vivo contra a
          API da Shopee antes de ser salva.
        </li>
        <li>
          <strong>Dados de produtos da Shopee</strong> que o usuário consulta e salva no painel
          (nome, preço, imagem, link de afiliado) para fins de divulgação.
        </li>
        <li>
          <strong>Conteúdo dos posts</strong> que o usuário cria e agenda para publicação nas
          redes conectadas.
        </li>
        <li>
          <strong>Logs de requisição</strong> (rota acessada, método HTTP, código de status,
          duração, IP de origem e, quando autenticado, usuário) — coletados apenas quando o
          registro de auditoria está explicitamente ativado no servidor
          (variável de ambiente <code>REQUEST_LOGGING_ENABLED=true</code>; desligado por padrão),
          e usados só para depuração técnica de falhas em produção.
        </li>
      </ul>
      <p>
        Não coletamos dados de pagamento ou de cartão — o ShopeeAutoVendas não processa cobranças
        nem transações financeiras diretamente.
      </p>

      <h2>3. Base legal (LGPD)</h2>
      <p>O tratamento desses dados se apoia nas seguintes bases legais do art. 7º da LGPD:</p>
      <ul>
        <li>
          <strong>Execução de contrato (inciso V):</strong> para usuário/senha e o funcionamento
          básico da conta e do painel.
        </li>
        <li>
          <strong>Consentimento do titular (inciso I):</strong> para a conexão de cada rede social
          e para a credencial da Shopee — nada é conectado sem uma ação explícita do usuário
          autorizando aquele escopo específico (fluxo OAuth) ou colando aquela credencial.
        </li>
        <li>
          <strong>Legítimo interesse do controlador (inciso IX):</strong> para os logs de
          requisição, quando ativados, limitados à finalidade de segurança e diagnóstico técnico.
        </li>
      </ul>

      <h2>4. Com quem compartilhamos os dados</h2>
      <p>Não vendemos dados pessoais a terceiros. Os dados são compartilhados apenas com:</p>
      <ul>
        <li>
          <strong>As próprias redes sociais conectadas</strong> (X, Facebook, Instagram, TikTok,
          Threads/Meta) — na medida do escopo de permissão que o usuário autorizou no momento da
          conexão, para permitir a publicação de conteúdo em nome dele.
        </li>
        <li>
          <strong>Shopee</strong> — via API oficial de afiliados, para consultar produtos e gerar
          links de afiliado.
        </li>
        <li>
          <strong>Provedores de infraestrutura</strong> que operam como operadores de dados (art.
          5º, VII, LGPD) a nosso mando: banco de dados hospedado no Supabase e aplicação hospedada
          no Render. Esses provedores não usam os dados para finalidade própria.
        </li>
      </ul>

      <h2>5. Retenção e exclusão</h2>
      <p>
        Os dados de cadastro e conteúdo são mantidos enquanto a conta estiver ativa. Ao
        desconectar uma rede social ou a credencial da Shopee pelo próprio painel, o token/App
        ID/Secret daquela rede é apagado (o campo é zerado) e o status volta para
        "desconectado" — mas o registro correspondente no banco não é excluído automaticamente,
        apenas esvaziado dos valores sensíveis. Para solicitar a exclusão completa da conta e de
        todos os dados associados, entre em contato pelo e-mail informado na seção 8.
      </p>

      <h2>6. Segurança</h2>
      <ul>
        <li>Tokens OAuth e credenciais de terceiros são cifrados em repouso (Fernet).</li>
        <li>Senhas são armazenadas apenas como hash bcrypt, nunca em texto claro.</li>
        <li>Toda comunicação com o painel é feita via HTTPS.</li>
        <li>
          A sessão do usuário é mantida por cookie <strong>httpOnly</strong>, marcado como{' '}
          <strong>Secure</strong> e com política <strong>SameSite=Lax</strong> — não é acessível
          via JavaScript no navegador, o que reduz a superfície de roubo de sessão.
        </li>
      </ul>

      <h2>7. Direitos do titular</h2>
      <p>Nos termos dos arts. 9º e 18 da LGPD, o titular dos dados pode solicitar a qualquer momento:</p>
      <ul>
        <li>Confirmação de que tratamos seus dados e acesso a eles;</li>
        <li>Correção de dados incompletos, inexatos ou desatualizados;</li>
        <li>Exclusão dos dados tratados com base em consentimento;</li>
        <li>Revogação do consentimento dado a qualquer rede social conectada (basta desconectá-la no painel, ou solicitar por e-mail);</li>
        <li>Portabilidade dos dados a outro fornecedor, mediante requisição expressa;</li>
        <li>Informação sobre com quem seus dados são compartilhados.</li>
      </ul>
      <p>Essas solicitações podem ser feitas pelo canal de contato indicado abaixo.</p>

      <h2>8. Contato e encarregado (DPO)</h2>
      <p>
        Dúvidas sobre esta política ou solicitações relativas aos seus dados pessoais podem ser
        enviadas para: <strong>contato.raffasp@gmail.com</strong>.
      </p>

      <h2>9. Alterações desta política</h2>
      <p>
        Esta política pode ser atualizada para refletir mudanças no serviço ou na legislação
        aplicável. A data no topo desta página indica a versão vigente. Alterações relevantes
        serão comunicadas por e-mail ou aviso no painel.
      </p>
    </LegalLayout>
  )
}
