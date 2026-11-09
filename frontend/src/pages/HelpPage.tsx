import { useState } from "react"
import { Panel, PanelHeader } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { Icon } from "../components/ui/Icon"
import { NetworkLimitsHelp } from "../components/help/NetworkLimitsHelp"
import { SegmentedToggle, type SegmentedOption } from "../components/ui/SegmentedToggle"

const SUPPORT_EMAIL = "contato.raffasp@gmail.com"
const SUPPORT_CNPJ = "63.621.332/0001-03"

type HelpTab = "shopee" | "primeiros-passos" | "modulos" | "faq" | "limites" | "lgpd"

const TABS: SegmentedOption[] = [
  { value: "shopee", label: "Tutorial Shopee", icon: "key-round" },
  { value: "primeiros-passos", label: "Primeiros Passos", icon: "sparkles" },
  { value: "modulos", label: "Guia dos Módulos", icon: "layout-grid" },
  { value: "faq", label: "FAQ", icon: "message-square" },
  { value: "limites", label: "Limites das redes", icon: "sliders-horizontal" },
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
  { title: "Crie sua conta e faça login", text: "Escolha um nome de usuário e senha, leia os Termos e a Política de Privacidade e conclua o cadastro. O GPS é opcional; negar não impede o acesso." },
  { title: "Configure seu perfil", text: "Em Perfis, confira seu perfil principal e crie perfis adicionais. Em Configurações, gerencie localização, região declarada, origem do cadastro, backup e exclusão de conta." },
  { title: "Conecte somente o que usar", text: "Abra Credenciais para conectar a Shopee e as redes desejadas. Algumas integrações precisam de aprovação da plataforma, permissões específicas ou credenciais de desenvolvedor. Uma conexão válida não garante autorização para todos os recursos." },
  { title: "Cadastre e organize produtos", text: "Em Produtos, inclua itens manualmente ou consulte a Pesquisa Avançada quando a integração Shopee estiver autorizada. Use Listas para reunir produtos por campanha, nicho ou ocasião." },
  { title: "Prepare sua publicação", text: "Abra Posts, escolha o perfil e a rede conectada, revise texto, links, mídias e informações do produto. Recursos de IA são auxiliares: confira preços, condições e afirmações antes de publicar." },
  { title: "Publique agora ou agende", text: "Defina data e hora de Brasília. O serviço registra a tarefa e tenta executá-la no horário, mas depende da disponibilidade do servidor e da API da rede. Agendamento não é garantia de entrega." },
  { title: "Acompanhe o resultado", text: "Consulte o status em Posts e as Análises disponíveis. Se uma publicação ficar sem confirmação, confira a própria rede antes de tentar de novo para evitar duplicações." },
  { title: "Proteja suas informações", text: "Gerencie conexões em Credenciais e dados pessoais em Configurações, consulte Dados coletados e exporte backup quando necessário. Para privacidade, use o contato de suporte." },
]

const MODULES: { icon: string; title: string; text: string }[] = [
  { icon: "house", title: "Dashboard", text: "Resumo da operação e atalhos para produtos, listas e publicações. Os números dependem dos registros do perfil ativo." },
  { icon: "briefcase", title: "Produtos", text: "Catálogo manual ou conectado à Shopee; os resultados da pesquisa dependem de credenciais, permissões e disponibilidade da API." },
  { icon: "sliders-horizontal", title: "Listas", text: "Coleções para organizar produtos e campanhas. Uma lista não publica automaticamente o conteúdo." },
  { icon: "file-text", title: "Posts", text: "Editor, mídias, agendamentos, estados de execução e conciliação manual quando uma rede recebeu o post, mas a confirmação não retornou." },
  { icon: "chart-no-axes-combined", title: "Análises", text: "Resultados de envio e indicadores permitidos pelas redes. Traço significa indisponível ou não coletado, não necessariamente zero. As métricas de Página do Facebook não equivalem a visualizações individuais de posts." },
  { icon: "key-round", title: "Credenciais", text: "Conexão e reconexão de serviços por OAuth ou chaves apropriadas. Permissões específicas podem depender de análise das plataformas." },
  { icon: "users", title: "Perfis", text: "Perfis de uso, foto, seleção do perfil ativo e limites da conta." },
  { icon: "lock", title: "Configurações e privacidade", text: "Senha, localização GPS coletada uma vez, região declarada, origem do cadastro, backup, restauração e exclusão da própria conta." },
  { icon: "shield-check", title: "Administração", text: "Exclusivo a administradores: visão geral, saúde de filas, uso do banco, desempenho, custos estimados e agregados de clientes; métricas ausentes não devem ser interpretadas como zero." },
]

// Consentimento separado do cadastro. Uma única posição aproximada é usada para expansão comercial.
type FaqItem = { category: string; question: string; answer: string }
const FAQ_ITEMS: FaqItem[] = [
  { category: "Privacidade e segurança", question: "Quando o site solicita GPS e para que serve?", answer: "No primeiro acesso após o cadastro, aparece um popup explicando que o Auto Orbital solicita sua localização uma única vez para analisar as regiões onde há clientes e orientar a expansão comercial. Você pode recusar. Se permitir, o navegador pergunta separadamente; salvamos apenas uma posição aproximada, arredondada a cerca de 1 km, com data e precisão estimada. O administrador poderá visualizar sua localização aproximada individualmente. Não existe coleta repetida ou rastreamento em segundo plano. Em Configurações é possível retirar a autorização e excluir o ponto." },
  { category: "Privacidade e segurança", question: "O GPS é obrigatório para usar o serviço?", answer: "Não. O aviso é apresentado, mas compartilhar a localização é opcional. Recusar não impede o uso dos recursos essenciais. O consentimento para GPS é independente dos Termos de Uso." },
  { category: "Sobre a plataforma", question: "O que é o Auto Orbital e para quem ele serve?", answer: "É uma plataforma para organizar produtos e campanhas de afiliados, preparar textos e mídias, conectar contas sociais e gerenciar publicações em um mesmo ambiente. Ajuda a reduzir tarefas manuais, mas não substitui a análise do conteúdo nem garante vendas, alcance ou aprovação das redes. As funções disponíveis variam conforme a integração e o plano." },
  { category: "Sobre a plataforma", question: "Preciso instalar um aplicativo ou posso usar no celular?", answer: "O Auto Orbital funciona pelo navegador do computador, tablet ou celular. É necessário acesso à internet e um navegador atualizado. A disponibilidade de alguns recursos, como seleção de arquivos e geolocalização, depende do próprio navegador e das permissões concedidas." },
  { category: "Sobre a plataforma", question: "Preciso ter uma loja ou ser afiliado para começar?", answer: "Você pode conhecer o painel e organizar conteúdo sem conectar todas as plataformas. Para consultar produtos de afiliados da Shopee e trabalhar com links do programa, é necessário ter acesso autorizado às credenciais correspondentes; os requisitos de participação são definidos pela Shopee." },
  { category: "Cadastro e perfis", question: "Qual a diferença entre conta e perfil?", answer: "A conta identifica quem acessa o Auto Orbital e controla autenticação e permissões. Os perfis organizam o trabalho dentro dessa conta. Antes de editar, agendar ou conectar uma rede, confirme o perfil ativo para não associar uma publicação à operação errada." },
  { category: "Cadastro e perfis", question: "Por que preciso aceitar os Termos? Também sou obrigado a ativar o GPS?", answer: "A criação de conta exige leitura e aceitação dos Termos de Uso vigentes, registrada com data e versão. A localização é separada e opcional. A plataforma não consulta o GPS automaticamente no cadastro e não condiciona as funcionalidades essenciais à autorização de localização." },
  { category: "Cadastro e perfis", question: "Como uso o GPS e por que minha região pode não aparecer no mapa?", answer: "No primeiro acesso, o aviso de localização permite uma única consulta ao navegador. Se você concordar, o ponto aproximado poderá aparecer individualmente no globo do administrador, mesmo quando houver apenas um cliente. Em Configurações você pode escolher país/UF manualmente, sem novo GPS. As contagens agregadas por região só aparecem quando houver ao menos três contas." },
  { category: "Cadastro e perfis", question: "Como corrijo ou retiro minha localização e a origem do cadastro?", answer: "Em Configurações, você pode excluir a localização pontual autorizada, alterar ou apagar sua região declarada e sua origem de cadastro. Ao excluir o ponto, a plataforma não consulta o GPS novamente. Para atualizar sua cidade, apenas altere manualmente a região; também é possível retirar a permissão do navegador no dispositivo." },
  { category: "Credenciais", question: "Como conecto minha conta da Shopee?", answer: "Acesse Credenciais, localize a integração Shopee e confira os campos solicitados. Obtenha as credenciais autorizadas no Portal de Afiliados ou ambiente de desenvolvedores correspondente à sua conta, copie com atenção e teste a conexão. Nunca envie seu App Secret a terceiros ou por mensagens de suporte. Se a plataforma rejeitar a autenticação, verifique a habilitação da API, permissões e validade das chaves." },
  { category: "Credenciais", question: "Por que uma rede social pede reconexão?", answer: "Tokens e autorizações podem expirar, ser revogados pelo titular, perder permissões ou ficar inválidos após mudanças da plataforma. Abra Credenciais e use o fluxo de reconexão. Se o erro persistir, verifique se o perfil ou Página correta foi autorizado e se a funcionalidade está liberada na API." },
  { category: "Credenciais", question: "Por que Facebook, Instagram ou Threads podem recusar o acesso?", answer: "A Meta diferencia acesso básico de permissões avançadas, que podem exigir análise do aplicativo e tipo de conta elegível. Algumas leituras de métricas também dependem de dados existentes. Uma credencial conectada não significa que todos os endpoints estejam autorizados. Veja a mensagem de erro e não compartilhe tokens em capturas de tela." },
  { category: "Credenciais", question: "As redes disponíveis publicam todas da mesma forma?", answer: "Não. Cada rede determina formatos de mídia, limites de texto, escopos de API, taxas, permissões e tipos de conta aceitos. Algumas integrações podem estar em teste, restritas ou indisponíveis. Sempre verifique a indicação de disponibilidade no card da rede e faça uma publicação de teste antes de agendar campanhas importantes." },
  { category: "Publicações", question: "Quais são as regras da Shopee Vídeo e o Auto Orbital já publica nela?", answer: "A Shopee informa duração de 3 a 60 segundos, permite vincular até 6 produtos e exige que o produto seja associado diretamente ao vídeo para que a comissão aplicável seja contabilizada. A publicação é feita pelo aplicativo Shopee. O Auto Orbital ainda não possui motor de upload/publicação Shopee Vídeo; a página Ajuda > Limites das redes apresenta as regras conhecidas e o estado real da integração. Não use links na legenda como substituto do vínculo do produto." },
  { category: "Produtos e conteúdo", question: "O que é a Pesquisa Avançada de produtos?", answer: "É o recurso de consulta de catálogo da Shopee dentro de Produtos, quando a integração e a autorização correspondentes estão funcionando. Os dados retornados dependem da API e podem mudar. Confira preço, disponibilidade, comissão e link antes de anunciar; o Auto Orbital não controla o estoque da loja." },
  { category: "Produtos e conteúdo", question: "Como uso Listas e posso reutilizar um produto?", answer: "Use Listas para agrupar os produtos cadastrados por nicho, campanha ou tema. Isso facilita encontrar itens na criação do post, sem obrigar você a redigitar tudo. Antes de reutilizar uma oferta, revise as informações, pois preços e condições podem ter mudado." },
  { category: "Produtos e conteúdo", question: "A inteligência artificial publica ou garante que o texto esteja correto?", answer: "Os recursos de geração de texto são apoio à redação. Você é responsável por revisar alegações comerciais, preços, links de afiliado, ortografia, direitos sobre mídias e regras de cada rede. O texto sugerido não comprova características do produto nem substitui verificação das fontes." },
  { category: "Publicações", question: "Como funciona o agendamento e qual fuso horário devo usar?", answer: "Selecione o perfil e a rede, prepare o conteúdo e defina a data e o horário apresentados em Brasília. O backend registra a tarefa e tenta executá-la quando chegar o momento. O horário efetivo pode variar conforme disponibilidade do servidor, rede social, limites de API e tentativas de execução." },
  { category: "Publicações", question: "Qual a diferença entre Agendado, Publicado, Falhou e Sem confirmação?", answer: "Agendado significa tarefa registrada, ainda não concluída. Publicado indica confirmação de sucesso registrada pelo sistema. Falhou indica erro conhecido. Sem confirmação significa que a execução começou, mas não houve prova conclusiva do resultado; o conteúdo pode ter chegado à rede. Confira a plataforma de destino antes de reenviar." },
  { category: "Publicações", question: "Uma postagem apareceu na rede, mas o painel não confirmou. O que faço?", answer: "Primeiro verifique se o conteúdo realmente está no perfil correto, sem reenviar automaticamente. Em Posts, use Conferir post para registrar uma publicação verificada com link quando disponível. Se você a viu e depois apagou, existe uma declaração específica sem link: o sistema preserva o erro original e informa que é um relato do titular, não confirmação automática da rede." },
  { category: "Publicações", question: "Posso garantir que um post nunca será duplicado?", answer: "O serviço possui mecanismos para reduzir reenvios e distinguir execuções incertas. Contudo, respostas atrasadas, quedas durante um envio e limites das APIs podem impedir confirmação imediata. Por isso o fluxo de conciliação pede que o usuário consulte a rede antes de qualquer nova tentativa." },
  { category: "Publicações", question: "Por que uma publicação pode demorar ou não sair?", answer: "Causas possíveis incluem credencial vencida, permissão insuficiente, mídia incompatível, limite da rede, serviço indisponível, falha no agendador ou interrupção do servidor. Confira o status em Posts, a conexão em Credenciais e os avisos de erro. Evite clicar repetidamente em Publicar durante uma instabilidade." },
  { category: "Análises", question: "Por que vejo traços no lugar de curtidas, visualizações ou cliques?", answer: "Um traço significa que a métrica não está disponível ou não foi coletada; não deve ser interpretado como zero. Cada plataforma oferece indicadores diferentes e alguns exigem permissões adicionais. O painel separa resultados de envio de dados de audiência, que podem ter atualização atrasada ou não estar habilitados." },
  { category: "Análises", question: "O número de visualizações do Facebook representa cada post?", answer: "Nem sempre. Quando o painel apresenta visualizações da Página, a métrica pode representar resultados agregados retornados pela Graph API, não a soma das visualizações individuais de cada publicação. Observe a descrição junto ao indicador e o período consultado para não comparar medidas diferentes." },
  { category: "Planos e custos", question: "Os planos Free, Plus e Premium já representam pagamentos confirmados?", answer: "Não. A distribuição exibida na área administrativa descreve planos cadastrados. Enquanto a cobrança não estiver integrada e conciliada, não é correto tratar um plano selecionado como pagamento recebido. Recursos, limites e preços devem ser conferidos na oferta atual antes de contratar." },
  { category: "Planos e custos", question: "O painel administrativo mostra custos reais do Render e do Supabase?", answer: "O painel acompanha consumo e desempenho nos limites das fontes habilitadas. Um orçamento em reais pode ser informado pelo operador para obter estimativas e rateios, que não são faturas nem custo individual efetivo. Para custo real por cliente são necessários dados de faturamento e atribuição de recursos." },
  { category: "Privacidade e segurança", question: "Como meus dados e minhas credenciais são protegidos?", answer: "O sistema utiliza hash para senhas, criptografia de credenciais e controles de acesso no backend. Isso reduz riscos, mas nenhum serviço conectado à internet garante segurança absoluta. Use senha forte, proteja sua sessão, mantenha seu navegador atualizado e nunca compartilhe tokens, senhas ou segredos de integração." },
  { category: "Privacidade e segurança", question: "Quais dados do computador, tablet ou celular são tratados?", answer: "O site pode processar dados da conta e logs técnicos de acesso, além do conteúdo que você criar. Navegador e hospedagem também podem tratar IP e cabeçalhos técnicos. Se você permitir no aviso do primeiro acesso, salvamos uma única localização aproximada com data e precisão estimada, removível em Configurações. Consulte Dados coletados." },
  { category: "Privacidade e segurança", question: "Posso exportar meus dados? E excluir minha conta?", answer: "O sistema oferece opções de backup e exclusão de conta. Consulte os controles disponíveis para seu perfil e revise o conteúdo do arquivo exportado: integrações externas e certos registros operacionais podem não integrar o backup. A exclusão pode ser irreversível, enquanto alguns registros podem precisar ser conservados pelo prazo necessário para obrigações legais e segurança." },
  { category: "Privacidade e segurança", question: "Onde consulto Termos, Política de Privacidade e meus direitos LGPD?", answer: "As páginas públicas /termos, /privacidade e /dados-coletados descrevem regras, finalidades, possíveis categorias de dados e controles do titular. Para dúvidas, pedidos de acesso, correção ou eliminação que não estejam disponíveis no próprio site, utilize o contato de suporte apresentado abaixo." },
  { category: "Suporte", question: "Como relato um problema de login ou publicação?", answer: "Informe a área do sistema, rede social, horário aproximado em Brasília, texto da mensagem de erro e passos que levaram ao problema. Se possível, inclua uma captura com informações pessoais ocultadas. Nunca envie senha, cookie de sessão, App Secret ou token OAuth; o suporte não precisa desses segredos para iniciar a análise." },
  { category: "Suporte", question: "O que é considerado falha do Auto Orbital ou da rede conectada?", answer: "Erros de autenticação e validação podem ocorrer tanto na aplicação quanto no serviço externo. O código de resposta, o horário, o estado da fila e a permissão associada ajudam a diagnosticar. Um envio concluído com atraso não comprova disponibilidade contínua, assim como uma falha da API externa não significa necessariamente defeito no agendador." },
]

export function HelpPage() {
  const [tab, setTab] = useState<HelpTab>(readInitialTab)
  const [openFaq, setOpenFaq] = useState<string | null>(null)
  const [faqSearch, setFaqSearch] = useState("")
  const faqFiltered = FAQ_ITEMS.filter(item => `${item.category} ${item.question} ${item.answer}`.toLocaleLowerCase("pt-BR").includes(faqSearch.trim().toLocaleLowerCase("pt-BR")) )

  const copyEmail = () => {
    navigator.clipboard.writeText(SUPPORT_EMAIL)
  }

  return (
    <div className="csp-s-0238">
      <div>
        <h1 className="csp-s-0239">Ajuda & FAQ</h1>
        <p className="csp-s-0240">
          Entenda os recursos, as limitações das integrações, o funcionamento dos agendamentos e seus direitos de privacidade.
        </p>
      </div>

      <div className="help-mobile-tabs" style={{ maxWidth: "100%", overflowX: "auto", WebkitOverflowScrolling: "touch" }}>
        <SegmentedToggle options={TABS} value={tab} onChange={(v) => setTab(v as HelpTab)} fullWidth={false} />
      </div>

      <Panel surface="dark">
        <PanelHeader title={TABS.find((t) => t.value === tab)?.label ?? ""} />
        <div className="csp-s-0241">
          {tab === "shopee" && (
            <div className="csp-s-0242">
              <p className="csp-s-0243">Para consultar o catálogo de afiliados, você precisa de credenciais autorizadas pela Shopee para a integração usada pelo Auto Orbital. Ter conta de comprador ou vendedor, por si só, não garante acesso às APIs de afiliados.</p>
              <ol className="csp-s-0244">
                <li>Acesse o ambiente oficial de afiliados ou desenvolvedores da Shopee associado à sua conta e confira se o programa e as APIs necessárias estão habilitados.</li>
                <li>Localize as credenciais próprias da integração, como App ID e Secret, seguindo o procedimento disponibilizado pela Shopee para sua modalidade de acesso.</li>
                <li>Abra <a href="/credentials">Credenciais</a> no Auto Orbital, selecione Shopee e preencha somente os campos necessários. Confira caracteres copiados, espaços e ambiente de autenticação.</li>
                <li>Salve e teste a conexão. Se houver recusa, verifique a permissão da API, expiração ou revogação das chaves e a mensagem retornada pela plataforma.</li>
                <li>Após a autenticação, use <a href="/products">Produtos</a> para pesquisar itens elegíveis. Revise links, preços, disponibilidade e regras de divulgação antes de publicar.</li>
              </ol>
              <p className="csp-s-0245"><strong>Segurança:</strong> mantenha App Secret e tokens em sigilo. Não envie essas informações por e-mail ou em capturas de tela. A emissão e aprovação de credenciais são controladas pela Shopee, não pelo Auto Orbital.</p>
              <p className="csp-s-0246">Se a Shopee alterar os nomes dos menus ou as exigências de acesso, siga a documentação oficial vigente e contate o suporte informando apenas o código do erro, sem compartilhar seus segredos.</p>
            </div>
          )}
          {tab === "primeiros-passos" && (
            <ol className="csp-s-0247">
              {STEPS.map((step, i) => (
                <li key={step.title} className="csp-s-0248">
                  <span
                    className="csp-s-0249"
                  >
                    {i + 1}
                  </span>
                  <div>
                    <p className="csp-s-0250">
                      {step.title}
                    </p>
                    <p className="csp-s-0251">{step.text}</p>
                  </div>
                </li>
              ))}
            </ol>
          )}
          {tab === "modulos" && (
            <div
              className="csp-s-0252"
            >
              {MODULES.map((mod) => (
                <div
                  key={mod.title}
                  className="csp-s-0253"
                >
                  <Icon name={mod.icon} size={20} />
                  <div>
                    <p className="csp-s-0254">
                      {mod.title}
                    </p>
                    <p className="csp-s-0255">{mod.text}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
          {tab === "faq" && (
            <div className="csp-s-0256">
              <label htmlFor="faq-search" className="csp-s-0257">Pesquisar perguntas por assunto</label>
              <input id="faq-search" type="search" value={faqSearch} onChange={e=>{setFaqSearch(e.target.value);setOpenFaq(null)}} placeholder="Ex.: agendamento, GPS, publicação, Shopee, segurança" className="csp-s-0258"/>
              <p role="status" className="csp-s-0259">{faqFiltered.length} perguntas encontradas</p>
              {faqFiltered.map((item) => {
                const open = openFaq === item.question
                return (
                  <div key={item.question} className="csp-s-0260">
                    <button
                      type="button"
                      onClick={() => setOpenFaq(open ? null : item.question)}
                      aria-expanded={open}
                      className="csp-s-0261"
                    >
                      <span><small className="csp-s-0262">{item.category}</small>{item.question}</span>
                      <Icon name="chevron-down" size={18} style={{ flexShrink: 0, transform: open ? "rotate(180deg)" : "none", transition: "transform var(--dur-fast) var(--ease-standard)" }} />
                    </button>
                    {open && (
                      <p className="csp-s-0263">
                        {item.answer}
                      </p>
                    )}
                  </div>
                )
              })}
              {faqFiltered.length === 0 && <p role="status" className="csp-s-0264">Nenhuma pergunta corresponde à busca. Tente outra palavra ou contate o suporte.</p>}
              <p className="csp-s-0265">Leia também <a href="/termos">Termos</a>, <a href="/privacidade">Privacidade</a> e <a href="/dados-coletados">Dados coletados</a>.</p>
            </div>
          )}
          {tab === "limites" && <NetworkLimitsHelp />}
          {tab === "lgpd" && (
            <div className="csp-s-0266">
              <p className="csp-s-0267">
                O que o Auto Orbital realmente faz com seus dados:
              </p>
              <ul className="csp-s-0268">
                <li>Sua senha é armazenada com hash bcrypt — irreversível, nem o próprio sistema consegue ver a senha em texto puro.</li>
                <li>Os tokens de OAuth das redes sociais são cifrados com Fernet no servidor, com chave de criptografia própria. Isso não é zero-knowledge: o servidor detém a chave.</li>
                <li>O banco de dados utiliza controles de acesso, permissões de serviço e RLS onde aplicável. O acesso administrativo do servidor exige proteção adicional; nenhum mecanismo isolado substitui a segurança do conjunto.</li>
                <li>Backup: use os recursos de exportação disponíveis na conta. O arquivo pode não incluir tokens, integrações externas ou registros técnicos preservados por obrigações legais.</li>
                <li>Exclusão e revogação: a conta e as preferências podem ser gerenciadas pelos controles disponíveis. Alguns registros podem ser retidos quando houver obrigação legal ou necessidade legítima de segurança.</li>
              </ul>
              <p><a href="/privacidade">Política de Privacidade</a> · <a href="/dados-coletados">Lista dos dados tratados</a> · <a href="/termos">Termos de Uso</a></p>
            </div>
          )}
        </div>
      </Panel>

      <Panel surface="dark">
        <div
          className="csp-s-0269"
        >
          <div>
            <p className="csp-s-0270">
              {SUPPORT_EMAIL}
            </p>
            <p className="csp-s-0271">
              Desenvolvido por Raffa Studio Produções — Empresa registrada desde 2026.
              <br />
              CNPJ {SUPPORT_CNPJ}
            </p>
          </div>
          <div className="csp-s-0272">
            <Button type="button" variant="ghost" icon="link-2" onClick={copyEmail}>
              Copiar e-mail
            </Button>
            <a
              href={`mailto:${SUPPORT_EMAIL}`}
              className="csp-s-0273"
            >
              Enviar mensagem
            </a>
          </div>
        </div>
      </Panel>
    </div>
  )
}
