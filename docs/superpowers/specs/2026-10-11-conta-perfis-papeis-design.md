# Design - Conta, perfis e papéis de acesso

> Origem: decisão de Rafa em 2026-10-11.
> Estado: arquitetura aprovada em conversa; este documento registra o contrato
> antes de qualquer alteração de código.

## Objetivo

Uma conta representa uma pessoa ou empresa. Ela inicia com um perfil principal
e pode ter no máximo dois perfis adicionais, totalizando três operações de
publicação. Cada perfil representa uma marca, loja ou identidade social
independente, como `Minha Casa Minha Vida` e `Rio Decor`.

## Posse dos dados

### Compartilhados pela conta (`user_id`)

- credencial da Shopee;
- chave e configuração do assistente de IA;
- catálogo de produtos salvos.

Esses recursos são cadastrados uma vez. Ao ativar um perfil novo, a pessoa vê
automaticamente a mesma Shopee, a mesma IA e os mesmos produtos sem copiar
segredos ou duplicar catálogo.

### Isolados por perfil (`user_id` + `profile_id`)

- conexões OAuth e credenciais de Threads, X, Facebook, Instagram, TikTok e
  Kwai;
- status e testes dessas conexões;
- listas de produtos;
- posts, variações de texto, mídia e composição por rede;
- agendamentos, tentativas, resultados, notificações e preferências de
  publicação.

Uma lista pertence somente ao perfil que a criou, mas pode referenciar produtos
do catálogo compartilhado da mesma conta. Um perfil jamais pode acessar dados
isolados de outro perfil, mesmo quando ambos pertencem ao mesmo usuário.

## Papéis

### USER

- usa Dashboard, Produtos, Listas, Posts, Credenciais, Configurações, Ajuda e
  Perfis;
- cria, edita, ativa e exclui somente os próprios perfis, respeitando o limite
  total de três;
- informa Shopee e IA manualmente para a conta;
- conecta cada rede social por OAuth no perfil ativo;
- nunca recebe formulário, rota navegável, dica visual ou mensagem sobre
  administração técnica, tokens sociais, Client ID, Client Secret, portais de
  desenvolvedor, diagnóstico bruto ou logs internos;
- vê erro tratado no fluxo em que ocorreu, sem detalhes técnicos ou tela de
  logs.

### ADMIN

- recebe todas as funções de USER;
- recebe módulos administrativos carregados sob demanda: gestão de contas e
  permissões, logs técnicos, diagnósticos e overrides manuais de credenciais
  sociais para as contas de desenvolvimento;
- os overrides continuam escopados pelo usuário e perfil selecionado; eles não
  transformam uma credencial global do app em conexão de outro usuário.

## Segurança e carregamento

1. O frontend obtém o papel atual de uma sessão autenticada antes de decidir
   quais módulos podem ser carregados.
2. Rotas e módulos administrativos ficam em chunks dinâmicos e não são
   importados para uma sessão USER. `/profiles` continua comum; gestão de
   usuários deve sair dela para rota administrativa própria.
3. Navegação, links, rótulos e estados vazios não revelam funções
   administrativas a USER. Uma URL administrativa digitada manualmente retorna
   para uma tela comum, sem explicar que há uma área restrita.
4. O navegador não é fronteira de segurança. Cada endpoint administrativo
   exige papel ADMIN no backend e valida o escopo `user_id` e `profile_id`.
   Alterar DOM, localStorage ou JavaScript não concede acesso.
5. A sessão revalida o papel no bootstrap e após mudança administrativa. Papel
   persistido localmente serve apenas para experiência visual, nunca para
   autorizar uma chamada ao servidor.

## Migração segura

- A migração é aditiva e reversível por backup: dados existentes continuam no
  perfil principal.
- Shopee, IA e produtos existentes são consolidados para a posse da conta sem
  duplicar valores sensíveis. Se linhas antigas divergirem, a migração falha
  fechada e registra o conflito para decisão administrativa, sem escolher uma
  chave silenciosamente.
- As referências de listas e posts continuam válidas: listas permanecem por
  perfil e passam a validar que o produto pertence ao mesmo `user_id`.
- Exclusão de perfil remove ou arquiva apenas seus recursos isolados; nunca
  remove Shopee, IA ou produtos compartilhados da conta.

## Critérios de aceite

1. Uma conta nova tem um perfil principal e não consegue criar mais de dois
   adicionais, inclusive sob requisições concorrentes.
2. Um produto, Shopee ou IA criado no perfil principal aparece ao alternar para
   qualquer perfil da mesma conta.
3. Lista, rede social, mídia, post, job e resultado criados no perfil A não
   aparecem no perfil B.
4. USER não baixa módulos de usuários/logs/overrides e não vê mensagens sobre
   administração; requisições diretas aos endpoints ADMIN retornam 403 sem
   dados.
5. ADMIN acessa os módulos administrativos após validação do papel pelo
   servidor.
6. A suíte cobre escopo de conta, escopo de perfil, migração, troca de perfil,
   alteração de papel e tentativa de acesso manual.
