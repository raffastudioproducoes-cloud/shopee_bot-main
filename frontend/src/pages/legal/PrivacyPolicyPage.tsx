import { LegalLayout } from './LegalLayout'

/**
 * Política de Privacidade pública (/privacidade) — LGPD (Lei 13.709/2018).
 * Revisão jurídica necessária antes de publicação oficial.
 *
 * Conteúdo redigido a partir do comportamento real do backend, não de texto
 * genérico: api/routers/credentials.py (nunca devolve token/secret ao
 * frontend, delete zera valor sem apagar linha), api/crypto.py (Fernet),
 * api/routers/auth.py (bcrypt + cookie httpOnly/secure/lax) e
 * api/middleware.py (request_logs, desligado por padrão).
 */

export function PrivacyPolicyPage() {
  return (
    <LegalLayout title="Política de Privacidade" updatedAt="30 de outubro de 2026">
      <h2>1. Quem somos</h2>
      <p>
        O Auto Orbital é um painel de automação que ajuda o usuário a publicar conteúdo em
        suas próprias redes sociais. O serviço é operado por{' '}
        <strong>Raffa Studio Produções</strong>{' '}
        (<span className="legal-placeholder">completar: razão social completa e CNPJ</span>,
        endereço <span className="legal-placeholder">completar: endereço do controlador</span>),
        que atua como controladora dos dados pessoais tratados nesta plataforma, nos termos da
        Lei nº 13.709/2018 (Lei Geral de Proteção de Dados Pessoais — LGPD).
      </p>

      <h2>2. Dados que coletamos e como usamos</h2>
      <p>
        Coletamos e tratamos os seguintes dados, estritamente para operar o serviço:
      </p>
      <ul>
        <li>
          <strong>Dados de cadastro:</strong> nome de usuário e senha. A senha nunca é
          armazenada em texto claro — é convertida em hash irreversível (bcrypt) antes de ser
          gravada, e não pode ser recuperada por nós em caso de esquecimento (só redefinida).
        </li>
        <li>
          <strong>Tokens de acesso (OAuth) das redes sociais</strong> que o usuário conectar
          (Threads, Facebook, Instagram, TikTok e X, quando disponível no plano): armazenados
          cifrados no banco de dados (Fernet, criptografia simétrica) e nunca devolvidos ao
          navegador do usuário — o frontend só recebe um indicador de status
          ("conectado"/"desconectado"), nunca o valor do token.
        </li>
        <li>
          <strong>Credencial da API de afiliados da Shopee</strong> (App ID e Secret que o
          próprio usuário cola no painel): armazenada cifrada da mesma forma, validada ao vivo
          contra a API da Shopee antes de ser salva.
        </li>
        <li>
          <strong>Chaves de IA do próprio usuário</strong> (Google Gemini, OpenAI ou
          Anthropic), usadas quando o usuário opta por gerar textos com IA. Cada chave é
          cadastrada e cifrada no próprio usuário; o Auto Orbital não armazena chaves de IA
          de terceiros.
        </li>
        <li>
          <strong>Perfis, produtos e listas:</strong> perfis criados, produtos consultados e
          salvos do catálogo da Shopee, e listas organizadas para uso nos posts.
        </li>
        <li>
          <strong>Conteúdo dos posts:</strong> textos, mídias e produtos associados aos posts
          que o usuário cria e agenda para publicação.
        </li>
        <li>
          <strong>Mídia:</strong> imagens e vídeos submetidos são hospedados no Supabase
          Storage com URL assinada de acesso temporário (1 hora). Rascunhos de mídia expiram
          automaticamente após 24 horas. Mídia legada pode permanecer em ambiente de
          hospedagem antigo até a migração final de mídia.
        </li>
        <li>
          <strong>Dados recebidos de Shopee, Threads, Instagram, Facebook e TikTok:</strong>
          dados de produtos, perfis, mídias e publicações conforme o escopo de permissão
          autorizado na conexão de cada rede.
        </li>
        <li>
          <strong>Logs de requisição (request_logs):</strong> rota acessada, método HTTP,
          código de status, duração, IP de origem e, quando autenticado, usuário.
          Coletados apenas quando o registro de auditoria está explicitamente ativado no
          servidor (variável de ambiente <code>REQUEST_LOGGING_ENABLED=true</code>; desligado
          por padrão), e usados só para depuração técnica de falhas em produção.
        </li>
        <li>
          <strong>Eventos de auditoria (audit_events):</strong> registro imutável de
          alterações sensíveis (preço, exclusão, dado sensível), com quem fez, quando e o
          que era antes/depois.
        </li>
      </ul>
      <p>
        Não coletamos dados de pagamento ou de cartão — o Auto Orbital não processa cobranças
        nem transações financeiras diretamente.
      </p>

      <h2>2.1 Dados técnicos do dispositivo e GPS opcional</h2>
      <p>Ao acessar o site por computador, tablet ou celular, a infraestrutura pode tratar endereço IP, cabeçalhos HTTP, informações técnicas do navegador, caminhos acessados e duração das respostas para operação e segurança. O registro da aplicação depende da configuração de auditoria; o provedor de hospedagem também pode manter logs próprios. Consulte a lista <a href="/dados-coletados">Quais dados utilizamos?</a>.</p>
      <p>O GPS é <strong>inteiramente opcional</strong>. O aceite dos Termos não autoriza localização. Caso o titular habilite a preferência e clique em solicitar a região, o navegador apresenta sua própria permissão. A posição é processada apenas naquele momento no dispositivo para sugerir país/UF, sem envio de latitude ou longitude ao Auto Orbital. A região só é salva após confirmação e consentimento separados. Não há rastreamento em segundo plano, histórico de trajetos ou uso da localização para publicidade. É possível negar, corrigir e revogar em Perfis.</p>
      <p>As estatísticas do mapa mostram apenas regiões com pelo menos três contas voluntárias; grupos menores ficam ocultos. A escolha de origem de aquisição também é voluntária e revogável. O cadastro básico funciona sem GPS.</p>
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
          <strong>Consentimento específico e opcional (inciso I):</strong> para preferências de geolocalização e declaração de região, com revogação independente dos Termos.
        </li>
        <li>
          <strong>Legítimo interesse do controlador (inciso IX):</strong> para os logs de
          requisição, quando ativados, limitados à finalidade de segurança e diagnóstico técnico.
        </li>
        <li>
          <strong>Emprego de dados para fins de segurança:</strong> medidas técnicas de
          proteção (ciframento, hash e controle de acesso) aplicadas aos dados tratados.
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
        <li>
          <strong>Provedores de IA</strong> (Google Gemini, OpenAI e Anthropic) — apenas quando
          o usuário escolhe usar a sua própria chave para gerar textos. As respostas e
          mensagens enviadas a esses provedores são tratadas por estes de acordo com suas
          respectivas políticas de privacidade.
        </li>
        <li>
          <strong>Mídias legadas</strong> (caso ainda ativo no código): hospedagem temporária
          por ambiente Cloudinary, após a qual o Supabase Storage é a única fonte de mídia.
        </li>
      </ul>

      <h2>5. Retenção dos dados</h2>
      <p>
        Os dados de cadastro e conteúdo são mantidos enquanto a conta estiver ativa. Ao
        desconectar uma rede social ou a credencial da Shopee pelo próprio painel, o token/App
        ID/Secret daquela rede é apagado (o campo é zerado) e o status volta para
        "desconectado" — mas o registro correspondente no banco não é excluído automaticamente,
        apenas esvaziado dos valores sensíveis. Para solicitar a exclusão completa da conta e de
        todos os dados associados, use o fluxo descrito na seção 9 ou entre em contato pelo
        e-mail informado na seção 11.
      </p>
      <p>
        Não definimos um prazo fixo de retenção para todos os dados. Quando um prazo específico
        não estiver ainda definido pelo sistema, o controlador definirá e comunicará o prazo de
        retenção antes de armazenar os dados, sempre de acordo com a legislação aplicável.
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
        <li>
          O banco de dados usa Row Level Security (RLS), bloqueando qualquer acesso direto fora
          da API oficial.
        </li>
        <li>
          Acesso aos dados restrito à API oficial; os logs são escritos em modo append-only
          e sanitizados antes de persistir.
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

      <h2>7.1 Consentimentos e transparência</h2>
      <p>Registramos a versão e a data de aceitação dos Termos no cadastro, separadamente da preferência GPS. A permissão do navegador pode ser negada ou retirada nos ajustes do próprio dispositivo. A preferência GPS e a região declarada podem ser apagadas em Perfis. A revogação não prejudica a licitude de tratamentos anteriores.</p>
      <p>A finalidade da localização voluntária é exclusivamente produzir estatísticas regionais agregadas. Para acessar, corrigir, solicitar cópia ou eliminar dados, utilize os controles da conta ou o contato informado nesta Política.</p>
      <h2>8. Cookies</h2>
      <p>
        O Auto Orbital utiliza apenas o essencial de cookies para autenticação: o cookie{' '}
        <strong>access_token</strong> (JWT), que mantém o usuário logado no painel. Esse cookie
        é <strong>httpOnly</strong>, <strong>Secure</strong> e <strong>SameSite=Lax</strong>.
        Não utilizamos cookies de rastreio, analytics, pixels de marketing ou qualquer outro
        cookie não estritamente necessário para a operação do serviço.
      </p>

      <h2>9. Como excluir ou desconectar seus dados</h2>
      <p id="exclusao-de-dados">
        <strong>Exclusão de dados</strong> — saiba como remover suas informações do Auto Orbital:
      </p>
      <ol>
        <li>
          <strong>Desconectar as redes sociais em Credenciais.</strong> No painel, vá até
          Credenciais e clique em "Desconectar" para cada rede conectada (Threads, Facebook,
          Instagram, TikTok e X, quando disponível). Isso remove o token daquela rede do
          servidor; o registro de credencial fica vazio do valor sensível, mas o registro
          permanece para auditoria.
        </li>
        <li>
          <strong>Exportar um backup em Perfis.</strong> Use o botão de exportar backup para
          baixar todos os seus dados em JSON. Isso garante que você possui uma cópia dos dados
          antes de a exclusão definitiva.
        </li>
        <li>
          <strong>Solicitar exclusão da conta.</strong> Entre em contato pelo e-mail
          informado abaixo e solicite a exclusão da sua conta e de todos os dados associados.
          Após a solicitação, um código de confirmação será gerado para acompanhar o status da
          sua solicitação.
        </li>
        <li>
          <strong>Aviso automático da Meta (Facebook/Instagram/Threads):</strong> ao remover
          o aplicativo do Facebook, Instagram ou Threads, a Meta envia automaticamente um aviso
          ao Auto Orbital, e as credenciais e os dados vinculados àquela conta são apagados.
        </li>
        <li>
          <strong>Acompanhar o status</strong> pela aba de exclusão ou pela confirmação enviada
          para o e-mail de contato, usando o código de confirmação recebido.
        </li>
      </ol>

      <h2>10. Menores de idade</h2>
      <p>
        O Auto Orbital não é destinado a menores de idade. Para usar o serviço, você deve ter
        pelo menos 18 anos, ou a maioridade civil aplicável em sua jurisdição. Se for
        identificado que uma conta pertence a menor que a idade mínima, poderemos solicitar a
        exclusão dos dados dessa conta.
      </p>

      <h2>11. Contato e encarregado (DPO)</h2>
      <p>
        Dúvidas sobre esta política ou solicitações relativas aos seus dados pessoais podem ser
        enviadas para: <strong>contato.raffasp@gmail.com</strong>.
      </p>

      <h2>12. Alterações desta política</h2>
      <p>
        Esta política pode ser atualizada para refletir mudanças no serviço ou na legislação
        aplicável. A data no topo desta página indica a versão vigente. Alterações relevantes
        serão comunicadas por e-mail ou aviso no painel.
      </p>
    </LegalLayout>
  )
}
