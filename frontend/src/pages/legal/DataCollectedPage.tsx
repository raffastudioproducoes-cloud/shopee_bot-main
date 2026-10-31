import { LegalLayout } from './LegalLayout'

export function DataCollectedPage() {
  return <LegalLayout title="Quais dados o Auto Orbital utiliza?" updatedAt="30 de outubro de 2026">
    <p>Este inventário descreve os dados que o site e suas integrações podem tratar ao abrir no computador, tablet ou celular. Nem todos os dados são coletados em todas as sessões.</p>
    <h2>1. Identificação e conta</h2>
    <ul><li>Nome de usuário, senha protegida por hash e perfis cadastrados, incluindo dados preenchidos voluntariamente.</li><li>Aceite dos Termos (versão e data) e preferências opcionais de região, GPS e origem do cadastro, com possibilidade de revogação.</li></ul>
    <h2>2. Navegador, dispositivo e rede</h2>
    <ul><li>Endereço IP, caminho da requisição, método, resposta e tempo de processamento podem constar de registros técnicos da aplicação, da hospedagem ou dos serviços de segurança.</li><li>Navegador, sistema operacional e características técnicas podem integrar cabeçalhos padrão HTTP observados pela infraestrutura. O aplicativo não usa uma funcionalidade própria de impressão digital do dispositivo para identificar pessoas.</li><li>Cookie essencial de sessão para autenticação; a aplicação também pode manter preferências de interface localmente no navegador.</li></ul>
    <h2>3. Localização (opcional)</h2>
    <p>O navegador pode oferecer GPS ou outra fonte de geolocalização do dispositivo, apenas após sua autorização e um clique para consultar a posição. Coordenadas são usadas temporariamente para sugerir uma região e não são enviadas nem armazenadas pelo Auto Orbital. O usuário confirma ou altera a região antes de salvá-la. Não há monitoramento de deslocamentos em segundo plano nem coleta automática contínua. Bloquear o GPS não restringe a conta.</p>
    <h2>4. Conteúdos e serviços conectados</h2>
    <ul><li>Posts, mídias, agendamentos, produtos e listas criados; resultados de publicação e estatísticas permitidas pelas plataformas.</li><li>Tokens e chaves de serviços externos autorizados pelo usuário, protegidos no servidor.</li><li>Eventos de segurança, auditoria, erros técnicos e atividade necessários para funcionamento e diagnóstico.</li></ul>
    <h2>5. Dados que não pedimos automaticamente</h2>
    <p>O site não precisa de acesso à câmera, microfone, contatos, arquivos pessoais, mensagens privadas, Bluetooth ou localização precisa contínua. Arquivos e mídias só são recebidos quando enviados voluntariamente. Recursos de terceiros podem possuir políticas próprias.</p>
    <h2>6. Gerenciamento e direitos</h2>
    <p>Consulte <a href="/privacidade">Privacidade</a> para bases legais, destinatários, retenção, exclusão e contato. Gerencie GPS, localização regional e origem informada na página <a href="/profiles">Perfis</a>. Para solicitar acesso, correção ou eliminação de dados, contate contato.raffasp@gmail.com.</p>
  </LegalLayout>
}
