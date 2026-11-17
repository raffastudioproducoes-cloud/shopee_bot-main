import { CompanyIdentification } from './CompanyIdentification'
import { LegalLayout } from './LegalLayout'
import { PrivacyPolicyEn } from './PrivacyPolicyEn'

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

function PrivacyPolicyPt() {
  return (
    <>
      <h2>1. Quem somos</h2>
      <p>
        O Auto Orbital é um painel de automação que ajuda o usuário a publicar conteúdo em
        suas próprias redes sociais. O serviço é operado por{' '}
        <strong>Raffa Studio Produções</strong> (contato: contato.raffasp@gmail.com), que atua como controladora dos dados pessoais tratados nesta plataforma, nos termos da
        Lei nº 13.709/2018 (Lei Geral de Proteção de Dados Pessoais — LGPD).
      </p>

      <CompanyIdentification lang="pt" doc="privacy" />

      <h2>2. Dados que coletamos e como usamos</h2>
      <p>
        Coletamos e tratamos os seguintes dados, estritamente para operar o serviço:
      </p>
      <ul>
        <li>
          <strong>Dados de cadastro e identificação:</strong> nome completo, CPF, e-mail e
          credencial de acesso. No cadastro por e-mail, a senha é gerenciada pelo Supabase Auth;
          no login Google, pelo próprio provedor. Contas legadas podem ter hash de senha
          bcrypt, nunca senha em texto claro. CPF é cifrado no banco e a interface não
          devolve sua numeração completa.
        </li>
        <li><strong>Dados complementares da conta:</strong> celular necessário para contratar
          planos futuramente; idade, e-mail alternativo, telefone, endereço e CEP são
          opcionais no perfil cadastral. São vinculados à conta, separados dos perfis
          sociais. E-mail alternativo não está habilitado para recuperação até ter
          verificação própria.</li>
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
          <strong>Dados recebidos de Shopee, Threads, Instagram, Facebook, TikTok e X:</strong>
          dados de produtos, perfis, mídias e publicações conforme o escopo de permissão
          autorizado na conexão de cada rede (detalhe na seção 2.3).
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
        <strong>Pagamentos:</strong> a contratação de planos pagos é processada pelo Asaas
        (instituição de pagamento). Para criar a cobrança, enviamos ao Asaas nome, CPF, e-mail
        e celular do titular. Os dados do cartão são digitados na página de pagamento do Asaas
        e não passam nem ficam guardados no Auto Orbital; guardamos apenas o identificador do
        cliente no Asaas, o plano, o valor, a forma de pagamento escolhida (cartão ou Pix) e o
        status da cobrança. Preencher o cadastro não gera nenhuma cobrança.
      </p>

      <h2>2.1 Dados técnicos do dispositivo e GPS opcional</h2>
      <p>Ao acessar o site por computador, tablet ou celular, a infraestrutura pode tratar endereço IP, cabeçalhos HTTP, informações técnicas do navegador, caminhos acessados e duração das respostas para operação e segurança. O registro da aplicação depende da configuração de auditoria; o provedor de hospedagem também pode manter logs próprios. Consulte a lista <a href="/dados-coletados">Quais dados utilizamos?</a>.</p>
      <p>O GPS é <strong>inteiramente opcional</strong>. O aceite dos Termos não autoriza localização. No primeiro acesso, um aviso próprio oferece uma coleta pontual com autorização do navegador. Se permitido, latitude e longitude são arredondadas no dispositivo e enviadas uma única vez, com a data e a precisão estimada. O ponto fica associado à conta e pode ser visto individualmente apenas pelo administrador para análise comercial. A região declarada manualmente é opcional e independente desse ponto. Não há rastreamento em segundo plano, histórico de trajetos ou uso da localização para publicidade. É possível negar, corrigir e revogar em Configurações.</p>
      <p>As contagens agregadas do mapa exigem pelo menos três contas na mesma região declarada; os pontos de GPS autorizados podem ser exibidos individualmente, mesmo com apenas uma conta. A escolha de origem de aquisição também é voluntária e revogável. O cadastro básico funciona sem GPS.</p>
      <h2>2.2 Métricas das publicações e contagem de cliques</h2>
      <p>Para mostrar o desempenho de cada post, guardamos o histórico das métricas que cada rede fornece para as publicações feitas pelo Auto Orbital (visualizações, curtidas, comentários, compartilhamentos). Não coletamos quem curtiu, comentou ou visualizou.</p>
      <p>Nos posts de produto, o link Shopee pode ser trocado por um endereço curto do próprio site (<code>/r/…</code>), que redireciona para o mesmo link de afiliado. Esse redirecionamento registra apenas a <strong>contagem agregada de cliques por link e por dia</strong>; não guardamos endereço IP, navegador, dispositivo ou qualquer dado pessoal de quem clicou. O limite de acessos por endereço é aplicado somente em memória, de forma transitória.</p>
      <h2>2.3 Dados lidos de cada rede social conectada</h2>
      <p>Só lemos dados das contas que o próprio usuário conecta, e só para publicar e mostrar o desempenho dos posts dele. Não lemos mensagens privadas, listas de seguidores nem dados de outras pessoas.</p>
      <ul>
        <li><strong>Instagram (Meta):</strong> identificador da conta profissional e da Página do Facebook vinculada, nome de usuário, mídias publicadas pelo app e métricas desses posts. Permissões: instagram_basic, instagram_content_publish, instagram_manage_insights, pages_show_list, pages_read_engagement.</li>
        <li><strong>Facebook (Meta):</strong> identificador do usuário, lista de Páginas que ele administra (id, nome, token da Página), posts publicados pelo app e métricas desses posts. Permissões: pages_show_list, pages_read_engagement, pages_manage_posts, read_insights.</li>
        <li><strong>Threads (Meta):</strong> identificador do perfil, posts publicados pelo app e métricas desses posts. Permissões: threads_basic, threads_content_publish, threads_manage_insights.</li>
        <li><strong>TikTok:</strong> identificador (open_id) e nome de exibição da conta, opções de publicação da conta (creator_info) e status do vídeo enviado. Hoje não coletamos métricas de posts do TikTok nem do X. Permissões: user.info.basic, video.publish, video.upload.</li>
        <li><strong>X:</strong> identificador e nome de usuário da conta e identificador dos posts e mídias enviados pelo app. Permissões: tweet.read, tweet.write, users.read, media.write, offline.access.</li>
      </ul>
      <p>Os tokens dessas contas ficam cifrados no banco de dados. Os dados recebidos das plataformas da Meta, do TikTok e do X são usados apenas para as finalidades acima, não são vendidos, não são usados para publicidade e não são compartilhados com terceiros fora dos operadores listados na seção 4.</p>

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
          <strong>Asaas</strong> — processamento de pagamentos dos planos pagos, com os dados
          descritos na seção 2.
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
        <strong>Logs de requisição (request_logs):</strong> são apagados automaticamente pelo
        sistema depois de <strong>90 dias</strong>. A exclusão é feita por uma rotina periódica,
        de modo que um registro pode permanecer por algumas horas além desse prazo até a próxima
        execução. Essa rotina não altera os eventos de auditoria (audit_events).
      </p>
      <p>
        Não definimos um prazo fixo de retenção para todos os dados. Quando um prazo específico
        não estiver ainda definido pelo sistema, o controlador definirá e comunicará o prazo de
        retenção antes de armazenar os dados, sempre de acordo com a legislação aplicável.
      </p>

      <p>
        Outros prazos: rascunhos de mídia expiram em 24 horas e links assinados de mídia em 1
        hora; o histórico de métricas dos posts é mantido enquanto a conta existir; após a
        exclusão da conta, os dados da conta são apagados, salvo registros que a lei obriga a
        guardar (por exemplo, pagamentos e dados fiscais) e os eventos de auditoria imutáveis.
        Alguns operadores listados na seção 4 podem tratar dados fora do Brasil (por exemplo,
        nos Estados Unidos), com as salvaguardas próprias de transferência internacional.
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
          Ao criar uma conta ou trocar a senha, verificamos se a senha já apareceu em vazamentos
          públicos usando o serviço Have I Been Pwned por <em>k-anonimato</em>: somente os 5
          primeiros caracteres de um resumo (SHA-1) da senha são enviados, nunca a senha, o
          resumo completo, o e-mail ou qualquer dado da conta.
        </li>
        <li>
          O banco de dados usa Row Level Security (RLS), bloqueando qualquer acesso direto fora
          da API oficial.
        </li>
        <li>
          Acesso aos dados restrito à API oficial; os logs de requisição são sanitizados antes
          de persistir, não são editados depois de gravados e são apagados automaticamente após
          90 dias (seção 5).
        </li>
      </ul>

      <h2>6.1 Localização pontual autorizada</h2>
      <p>Após o primeiro acesso, apresentamos um aviso específico para solicitar localização por GPS ou outros meios disponíveis no dispositivo. A pessoa pode recusar e continuar usando o serviço. Se autorizar, o navegador solicitará acesso e enviaremos uma única localização aproximada, arredondada a cerca de 1 km, associada à conta, com data e precisão estimada. O administrador poderá visualizar individualmente a posição aproximada para análise geográfica e planejamento da expansão comercial. Não há monitoramento contínuo, histórico de deslocamentos, coleta de endereço ou novas consultas automáticas. O ponto pode ser apagado em Configurações, sem impedir o uso do serviço. Após recusa ou revogação, preservamos somente o estado e a data da decisão, sem coordenadas, para não solicitar a posição novamente.</p>
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
      <p>Essas solicitações podem ser feitas pelo canal de contato indicado abaixo. Pessoas no Espaço Econômico Europeu ou no Reino Unido têm também os direitos do GDPR/UK GDPR (acesso, retificação, apagamento, restrição, portabilidade, oposição e reclamação à autoridade de proteção de dados do seu país). Respondemos em até 15 dias.</p>

      <h2>7.1 Consentimentos e transparência</h2>
      <p>Registramos a versão e a data de aceitação dos Termos no cadastro, separadamente da decisão de localização. A permissão do navegador pode ser negada ou retirada nos ajustes do dispositivo. O ponto de GPS, a região declarada e a origem de cadastro podem ser apagados em Configurações. A revogação não prejudica a licitude de tratamentos anteriores.</p>
      <p>A localização autorizada pode ser vista individualmente pelo administrador para planejamento comercial e em estatísticas regionais. Para acessar, corrigir, solicitar cópia ou eliminar dados, utilize os controles da conta ou o contato informado nesta Política.</p>
      <h2>8. Cookies</h2>
      <p>
        O Auto Orbital utiliza apenas o essencial de cookies para autenticação: o cookie{' '}
        <strong>access_token</strong> (JWT), que mantém o usuário logado no painel. Esse cookie
        é <strong>httpOnly</strong>, <strong>Secure</strong> e <strong>SameSite=Lax</strong>.
        Não utilizamos cookies de rastreio, analytics, pixels de marketing ou qualquer outro
        cookie não estritamente necessário para a operação do serviço.
      </p>

      <h2>9. Como excluir ou desconectar seus dados</h2>
      <p>O passo a passo completo também está na página pública <a href="/exclusao-de-dados">Exclusão de dados</a>.</p>
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
          <strong>Exportar um backup em Configurações.</strong> Use o botão de exportar backup para
          baixar todos os seus dados em JSON. Isso garante que você possui uma cópia dos dados
          antes de a exclusão definitiva.
        </li>
        <li>
          <strong>Excluir a conta.</strong> Em Configurações → "Backup e dados" → "Excluir minha
          conta e dados" (pede sua senha; se o painel avisar que a exclusão ainda não está disponível,
          use o e-mail), ou envie um e-mail do endereço da sua conta para
          contato.raffasp@gmail.com pedindo a exclusão. Respondemos em até 15 dias.
        </li>
        <li>
          <strong>Remover o app na própria rede:</strong> nas configurações de apps do Facebook,
          Instagram ou Threads, em "Gerenciar permissões de apps" no TikTok ou em "Apps conectados"
          no X.
        </li>
        <li>
          <strong>Aviso automático da Meta (Facebook/Instagram/Threads):</strong> ao remover
          o aplicativo do Facebook, Instagram ou Threads, a Meta envia automaticamente um aviso
          ao Auto Orbital (endereços <code>/api/meta/deauthorize</code>,{' '}
          <code>/api/meta/data-deletion</code>, <code>/api/threads/uninstall</code> e{' '}
          <code>/api/threads/delete</code>), e as credenciais e os dados vinculados àquela conta
          são apagados. A Meta recebe um código de confirmação e um link de status.
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
    </>
  )
}

export function PrivacyPolicyPage() {
  return (
    <LegalLayout
      title={{ pt: 'Política de Privacidade', en: 'Privacy Policy' }}
      updatedAt={{ pt: '17 de novembro de 2026', en: 'November 17, 2026' }}
    >
      {(lang) => (lang === 'en' ? <PrivacyPolicyEn /> : <PrivacyPolicyPt />)}
    </LegalLayout>
  )
}
