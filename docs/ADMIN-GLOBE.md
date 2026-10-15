# Globo de localização agregado — implementação local

O painel de visão geral tem um globo com projeção esférica ortográfica, rotação por arraste/toque/setas, zoom por botões e teclado, seleção de país e foco em regiões. O mapa de continentes usa 5.032 pontos derivados da base Natural Earth 110m, de domínio público. O asset é local; não há tiles, geolocalização, SDK de rastreamento ou chamadas externas no globo.

Fonte: https://www.naturalearthdata.com/about/terms-of-use/ e https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson . A amostragem simplifica a cartografia; não representa fronteiras precisas ou limites estaduais.

## Estado atual

O modo real não contém pontos: país/UF e presença não são coletados atualmente. A demonstração exige ação explícita, tem números fictícios e aviso permanente. Possui Brasil (RJ/SP/MG/BA), Portugal, Estados Unidos, Japão e Austrália para testar o globo e a seleção. Não existe correspondência entre os pontos demonstrativos e clientes.

As regiões disponíveis nesta primeira versão cartográfica são limitadas; códigos não mapeados devem permanecer fora dos pontos, com aviso. O globo não infere localização a partir de nome, perfil ou registros de IP existentes. Um ponto é um agregado regional, não uma pessoa, cadastro individual ou endereço.

## Semântica das luzes

- Acesa/ciano: contas atuais com atividade recente no momento da coleta. Não é prova de conexão permanente.
- Apagada/cinza: contas atuais sem sinal recente. Não confirma logout.
- Vermelha: contagem histórica agregada de exclusões. Não preserva a identidade de quem excluiu a conta.

Cadastros atuais são atividade recente + sem atividade recente. Exclusões ficam separadas e precisam de período definido. A seleção de país soma somente as regiões-folha representadas, sem duplicar subtotal nacional e estadual. O futuro produtor de dados deve garantir essa exclusividade.

## Integração pendente

O tipo opcional `AdminMetrics.geography` prepara o consumidor visual: `status`, `updated_at` e `regions` com código regional e contagens `online`, `offline`, `deleted`. O backend atual não publica esse campo. O consumidor usa apenas o estado `available`, e só conhece as posições aproximadas do cadastro cartográfico local.

Antes de ligar dados reais: definir fonte autorizada de país/UF, criar agregador server-side com validação, retenção e grupos mínimos; incluir contas sem localização em cobertura separada; instrumentar presença com expiração e eventos explícitos de logout/exclusão; manter a exclusão sem vínculo de identidade; definir período histórico e supressão de grupos pequenos/complementares. Não habilitar coleta precisa de GPS/IP nem guardar histórico individual de trajetos para alimentar este painel.

Estas etapas não foram ativadas nesta entrega. Nenhuma migração, credencial, recurso externo, commit ou push foi feito para o globo.
