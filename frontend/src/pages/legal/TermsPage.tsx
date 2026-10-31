import { LegalLayout } from './LegalLayout'

/**
 * Termos de Serviço/Uso públicos (/termos).
 * Revisão jurídica necessária antes de publicação oficial.
 */

export function TermsPage() {
  return (
    <LegalLayout title="Termos de Serviço" updatedAt="30 de outubro de 2026">
      <h2>1. Aceitação dos termos</h2>
      <p>
        Ao criar uma conta ou usar o Auto Orbital ("nós", "plataforma", "serviço"), você
        concorda com estes Termos de Serviço e com a nossa{' '}
        <a href="/privacidade" style={{ color: 'var(--accent)' }}>
          Política de Privacidade
        </a>
        . Se você não concorda com algum ponto, não utilize o serviço.
      </p>

      <h2>2. Descrição do serviço</h2>
      <p>
        O Auto Orbital é uma ferramenta de automação que permite ao usuário agendar e
        publicar conteúdo nas redes sociais conectadas, pelo próprio usuário. O serviço
        inclui: (i) consultar produtos da Shopee e gerar links de afiliado; (ii) conectar
        contas em redes sociais (Threads, Facebook, Instagram, TikTok e X, quando
        disponível no plano) via autorização OAuth; e (iii) criar, agendar e publicar
        conteúdo nessas redes em nome do usuário, incluindo texto gerado com apoio de
        inteligência artificial quando o usuário optar por essa funcionalidade.
      </p>

      <h2>3. Elegibilidade e cadastro</h2>
      <ul>
        <li>Você deve ter pelo menos 18 anos (ou a maioridade civil aplicável em seu país) para usar o serviço.</li>
        <li>Você deve fornecer informações verdadeiras no cadastro e mantê-las atualizadas.</li>
        <li>Você é responsável por manter a confidencialidade da sua senha e por toda atividade realizada com sua conta.</li>
      </ul>

      <h2>3.1 Localização e consentimento opcional</h2>
      <p>Para criar uma conta é necessário tomar ciência da Política de Privacidade e aceitar os Termos de Uso vigentes. Essa aceitação é registrada com sua versão e data. Ela não substitui permissões específicas para recursos opcionais.</p>
      <p>O uso da localização por GPS é facultativo e não condiciona o cadastro nem as funcionalidades essenciais. A plataforma somente solicita acesso ao navegador quando o titular habilita a opção e aciona o botão de localizar. Com consentimento específico e autorização do navegador, uma única localização aproximada com coordenadas arredondadas poderá ser salva e mostrada ao administrador para planejar a expansão comercial. Não há monitoramento contínuo. É possível revogar e excluir os dados em Configurações.</p>
      <p>Leia também <a href="/dados-coletados">quais dados do dispositivo podem ser tratados</a>.</p>
      <h2>4. Responsabilidades do usuário</h2>
      <p>Ao usar o Auto Orbital, você concorda em:</p>
      <ul>
        <li>Não utilizar o serviço para enviar spam, conteúdo enganoso, ilegal ou que viole direitos de terceiros;</li>
        <li>
          Respeitar os Termos de Uso e as políticas de cada rede social que você conectar
          (Threads, Facebook, Instagram, TikTok e X, quando disponível no plano) — a
          conexão via OAuth não isenta você das regras da própria rede;
        </li>
        <li>
          Responder integralmente pelo conteúdo que publicar através da plataforma — o
          Auto Orbital é uma ferramenta de automação e publicação, não um editor ou
          curador do conteúdo criado pelo usuário;
        </li>
        <li>
          Seguir os limites de mídia e formato de cada rede (por exemplo, vídeo em MP4;
          não houve suporte a .mov) e aos demais requisitos de qualidade da plataforma.
        </li>
        <li>Não tentar acessar contas, dados ou credenciais de outros usuários, nem burlar mecanismos de segurança do serviço.</li>
      </ul>

      <h2>5. Integrações de terceiros</h2>
      <p>
        O funcionamento do Auto Orbital depende de APIs de terceiros (Shopee, X, Meta/Facebook,
        Instagram, TikTok). Não temos controle sobre a disponibilidade, mudanças de política,
        limites de taxa ou interrupções dessas APIs, e não garantimos que a publicação ou consulta
        de dados funcionará ininterruptamente. A revogação de autorização OAuth por parte da rede
        social, ou a suspensão da conta do usuário nela, pode impedir o funcionamento da integração
        correspondente sem que isso constitua falha do nosso serviço.
      </p>

      <h2>6. Publicação automática e agendamento</h2>
      <p>
        As publicações são enviadas apenas de acordo com a configuração do usuário.
        Não publicamos nenhum conteúdo sem a autorização explícita do usuário por meio
        dos controles de agendamento disponíveis no painel. O agendamento aceita data e
        hora específicas ou recorrência de 1 a 7 dias.
      </p>

      <h2>7. Limitação de responsabilidade</h2>
      <p>
        O Auto Orbital é fornecido "como está". Não garantimos resultado de vendas, engajamento
        ou desempenho de publicações feitas através da plataforma. Na máxima extensão permitida
        pela lei, não nos responsabilizamos por perdas de receita, oportunidades de negócio, ou
        danos indiretos decorrentes do uso do serviço, de indisponibilidade das APIs de terceiros
        integradas, ou de ações tomadas pelas redes sociais sobre a conta do usuário.
      </p>

      <h2>8. Propriedade intelectual</h2>
      <p>
        O código, marca e interface do Auto Orbital pertencem à Raffa Studio Produções. O
        conteúdo que você cria e publica através da plataforma (textos, imagens, agendamentos)
        permanece de sua titularidade/responsabilidade.
      </p>

      <h2>9. Suspensão e encerramento de conta</h2>
      <p>
        Podemos suspender ou encerrar o acesso de uma conta que viole estes termos, que seja usada
        para atividade fraudulenta, abusiva ou ilegal, ou mediante solicitação do próprio usuário.
        Você pode solicitar o encerramento da sua conta e a exclusão dos seus dados a qualquer
        momento pelo contato indicado na Política de Privacidade.
      </p>

      <h2>10. Alterações nestes termos</h2>
      <p>
        Podemos atualizar estes Termos de Serviço periodicamente para refletir mudanças no
        serviço ou na legislação aplicável. A data no topo desta página indica a versão vigente. O
        uso continuado do serviço após uma alteração publicada representa aceitação dos novos
        termos.
      </p>

      <h2>11. Legislação aplicável e foro</h2>
      <p>
        Estes termos são regidos pelas leis da República Federativa do Brasil. Fica eleito o foro
        do domicílio do controlador para dirimir eventuais controvérsias decorrentes destes
        termos, ressalvado foro de eleição do consumidor quando aplicável por lei.
      </p>

      <h2>12. Contato</h2>
      <p>
        Dúvidas sobre estes termos podem ser enviadas para: <strong>contato.raffasp@gmail.com</strong>.
      </p>
    </LegalLayout>
  )
}
