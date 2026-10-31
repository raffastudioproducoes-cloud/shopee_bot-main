# Inventário de componentes (SBOM) - Auto Orbital

Atualização: 31/10/2026. Fonte de verdade: `.github/workflows/sbom.yml`.

## O que foi automatizado

O workflow `SBOM - imagem Docker (CycloneDX)` constrói uma imagem local a partir do `Dockerfile` e do commit atual, sem passar segredos ao build, e gera um inventário **CycloneDX JSON** com Syft. O resultado é armazenado nos **Artifacts do GitHub Actions**, identificado por branch e SHA.

- Disparos: push de dependências/Dockerfile/workflow para `main` ou `staging`, execução manual e agenda semanal.
- Abrir GitHub → Actions → SBOM - imagem Docker → execução → Artifacts.
- Identificar a branch, o commit SHA e verificar a presença de componentes do SO, Python e frontend.
- Evitar publicar relatórios com conteúdo sensível: a imagem é criada sem secrets, mas os nomes de pacotes podem revelar a tecnologia em uso.

**Limite de evidência:** esse inventário reflete uma imagem reconstruída no runner do GitHub com o mesmo Dockerfile/commit, **não necessariamente os mesmos digests ou pacotes do Render**; `--pull` atualiza imagens base. Para atestar a imagem exata em produção é preciso coletar digest e gerar SBOM da **imagem implantada no Render**, ou publicar/promover a mesma imagem por digest em ambos os ambientes.

## Critérios de aceite

- [ ] Primeiro workflow completo, artefato CycloneDX baixável e parseado; conferir imagem e dependências efetivas.
- [ ] Identificar digest da imagem efetiva de produção para associar a SBOM (se Render permitir).
- [ ] Habilitar auditoria de CVEs de SO/Python/Node sobre o inventário e triagem com evidências, sem prometer ausência de vulnerabilidades.
- [ ] Separar ambiente `staging` de dados reais de produção antes de testes destrutivos.
- [x] Workflow criado sem mutação de banco, tokens ou implantação de aplicativo (código versionado).
