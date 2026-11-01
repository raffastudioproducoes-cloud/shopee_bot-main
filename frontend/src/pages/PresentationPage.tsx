import { useEffect, useState } from 'react'
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Copy,
  Globe2,
  History,
  Layers3,
  ListChecks,
  LockKeyhole,
  Menu,
  Orbit,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  X,
  Zap,
} from 'lucide-react'
import './PresentationPage.css'

type DemoStep = 'produtos' | 'listas' | 'editor' | 'agenda' | 'historico'

const steps: { id: DemoStep; name: string; label: string; hint: string }[] = [
  { id: 'produtos', name: 'Produtos', label: 'Encontre a oportunidade', hint: 'Pesquise e selecione produtos de uma loja integrada.' },
  { id: 'listas', name: 'Listas', label: 'Organize suas escolhas', hint: 'Separe os produtos que pretende divulgar.' },
  { id: 'editor', name: 'Editor', label: 'Prepare o conteúdo', hint: 'Escreva sua mensagem e use a assistência de IA quando configurada.' },
  { id: 'agenda', name: 'Agendamento', label: 'Defina o momento', hint: 'Escolha redes, datas e horários conforme as permissões disponíveis.' },
  { id: 'historico', name: 'Histórico', label: 'Acompanhe a execução', hint: 'Consulte o que foi programado, enviado ou precisa de atenção.' },
]

const networkNames = ['Facebook', 'Instagram', 'Threads', 'TikTok', 'X']

const faqs = [
  {
    q: 'Preciso publicar manualmente em cada rede?',
    a: 'O Auto Orbital reúne a preparação e o agendamento em um fluxo centralizado. A publicação depende das redes conectadas, do formato de cada conteúdo e das autorizações concedidas por cada plataforma.',
  },
  {
    q: 'Funciona com qualquer programa de afiliados?',
    a: 'A Shopee é a primeira integração de catálogo. A expansão para outros programas está em estudo e depende de APIs, permissões e viabilidade técnica. O Auto Orbital não promete compatibilidade universal neste momento.',
  },
  {
    q: 'Minha rede social fica protegida?',
    a: 'A conexão das redes compatíveis usa os mecanismos de autorização oferecidos pelos provedores. Cada integração pode solicitar permissões específicas, e a disponibilidade depende da aprovação e das regras de cada rede.',
  },
  {
    q: 'A inteligência artificial já faz tudo sozinha?',
    a: 'Hoje existem recursos de assistência à criação de textos sujeitos à configuração. A coleta, seleção, criação e publicação totalmente autônomas fazem parte da visão em desenvolvimento, ainda não disponível.',
  },
  {
    q: 'Já posso contratar um plano?',
    a: 'Ainda não. Os planos, limites e preços estão em definição, considerando custos, integrações e recursos que estarão disponíveis na comercialização.',
  },
]

function Status({ children, tone = 'current' }: { children: string; tone?: 'current' | 'planned' | 'conditional' }) {
  return <span className={'ao-lp-status ao-lp-status--' + tone}>{children}</span>
}

function SectionHeading({ eyebrow, title, children }: { eyebrow: string; title: string; children: React.ReactNode }) {
  return (
    <div className="ao-lp-section-heading">
      <span className="ao-lp-eyebrow"><span className="ao-lp-eyebrow-line" />{eyebrow}</span>
      <h2>{title}</h2>
      <p>{children}</p>
    </div>
  )
}

function DemoVisual({ active }: { active: DemoStep }) {
  return (
    <div className="ao-lp-app-preview" aria-label="Demonstração ilustrativa do fluxo Auto Orbital">
      <div className="ao-lp-app-rail" aria-hidden="true">
        <span className="ao-lp-rail-mark"><Orbit size={19} /></span>
        <Search size={18} />
        <Layers3 size={18} />
        <ListChecks size={18} />
        <Send size={18} />
        <History size={18} />
      </div>
      <div className="ao-lp-app-content">
        <div className="ao-lp-app-top">
          <span>Auto Orbital <span className="ao-lp-app-slash">/</span> Demonstração</span>
          <span className="ao-lp-app-avatar">AO</span>
        </div>
        <div className="ao-lp-app-caption"><span className="ao-lp-app-dot" /> Fluxo ilustrativo — sem dados reais</div>
        {active === 'produtos' && (
          <div className="ao-lp-preview-stage">
            <div className="ao-lp-app-title">Descubra oportunidades<span>01 / 05</span></div>
            <div className="ao-lp-fake-search"><Search size={16} /> Busque produtos no catálogo conectado <span>Buscar</span></div>
            <div className="ao-lp-fake-products">
              <div className="ao-lp-fake-product"><div className="ao-lp-product-placeholder ao-lp-product-placeholder--one"><span /></div><div><strong>Produto de demonstração</strong><small>Catálogo inicial · Shopee</small></div><CheckCircle2 size={19} /></div>
              <div className="ao-lp-fake-product ao-lp-fake-product--quiet"><div className="ao-lp-product-placeholder ao-lp-product-placeholder--two"><span /></div><div><strong>Outra oportunidade</strong><small>Organize sua seleção</small></div><span className="ao-lp-add-icon">+</span></div>
            </div>
          </div>
        )}
        {active === 'listas' && (
          <div className="ao-lp-preview-stage">
            <div className="ao-lp-app-title">Tudo no seu lugar<span>02 / 05</span></div>
            <div className="ao-lp-fake-list"><div className="ao-lp-fake-list-top"><Layers3 size={19} /><strong>Lista de oportunidades</strong><span>3 itens</span></div><div className="ao-lp-mini-line" /><div className="ao-lp-mini-line ao-lp-mini-line--mid" /><div className="ao-lp-mini-line ao-lp-mini-line--short" /></div>
            <div className="ao-lp-app-helper"><Check size={15} /> Produtos organizados para a próxima divulgação.</div>
          </div>
        )}
        {active === 'editor' && (
          <div className="ao-lp-preview-stage">
            <div className="ao-lp-app-title">Sua mensagem, seu tom<span>03 / 05</span></div>
            <div className="ao-lp-fake-editor"><span>Texto da publicação</span><strong>Uma oportunidade merece uma boa apresentação.</strong><div className="ao-lp-mini-line" /><div className="ao-lp-mini-line ao-lp-mini-line--mid" /><div className="ao-lp-mini-line ao-lp-mini-line--short" /><span className="ao-lp-fake-ai"><Sparkles size={14} /> Assistência de IA · quando configurada</span></div>
          </div>
        )}
        {active === 'agenda' && (
          <div className="ao-lp-preview-stage">
            <div className="ao-lp-app-title">Planeje a divulgação<span>04 / 05</span></div>
            <div className="ao-lp-fake-platforms"><span>Threads</span><span>Facebook</span><span>Instagram</span></div>
            <div className="ao-lp-fake-schedule"><div><CalendarDays size={18} /><span>Escolha uma data</span></div><div><Clock3 size={18} /><span>Defina o horário</span></div></div>
            <div className="ao-lp-app-helper"><Check size={15} /> Sujeito a conexões e permissões da rede.</div>
          </div>
        )}
        {active === 'historico' && (
          <div className="ao-lp-preview-stage">
            <div className="ao-lp-app-title">Visibilidade do processo<span>05 / 05</span></div>
            <div className="ao-lp-fake-history"><span><CheckCircle2 size={18} /> Publicação concluída</span><small>Exemplo ilustrativo</small></div>
            <div className="ao-lp-fake-history"><span><Clock3 size={18} /> Agendamento futuro</span><small>Exemplo ilustrativo</small></div>
            <div className="ao-lp-fake-history"><span><History size={18} /> Histórico centralizado</span><small>Exemplo ilustrativo</small></div>
          </div>
        )}
        <div className="ao-lp-app-bottom">Interface demonstrativa inspirada no fluxo real · não é uma conta ativa</div>
      </div>
    </div>
  )
}

export default function PresentationPage() {
  const [active, setActive] = useState<DemoStep>('produtos')
  const [menuOpen, setMenuOpen] = useState(false)
  const selected = steps.find((step) => step.id === active) ?? steps[0]

  useEffect(() => {
    const previous = document.title
    document.title = 'Auto Orbital — Sua operação de afiliados em uma nova órbita'
    const meta = document.createElement('meta')
    meta.name = 'robots'
    meta.content = 'noindex, nofollow'
    meta.dataset.autoOrbitalPreview = 'true'
    document.head.appendChild(meta)
    return () => {
      document.title = previous
      meta.remove()
    }
  }, [])

  return (
    <div className="ao-lp" id="topo">
      <a className="ao-lp-skip" href="#conteudo">Pular para o conteúdo</a>
      <header className="ao-lp-header">
        <div className="ao-lp-header-inner">
          <a href="#topo" className="ao-lp-brand" aria-label="Auto Orbital — início">
            <img src="/brand/wordmark.png" alt="Auto Orbital" />
          </a>
          <nav className={'ao-lp-nav' + (menuOpen ? ' ao-lp-nav--open' : '')} aria-label="Navegação principal">
            <a onClick={() => setMenuOpen(false)} href="#desafio">O desafio</a>
            <a onClick={() => setMenuOpen(false)} href="#como-funciona">Como funciona</a>
            <a onClick={() => setMenuOpen(false)} href="#recursos">O futuro</a>
            <a onClick={() => setMenuOpen(false)} href="#perguntas">Dúvidas</a>
          </nav>
          <div className="ao-lp-header-actions">
            <a className="ao-lp-enter" href="/login">Entrar <ArrowUpRight size={16} /></a>
            <button className="ao-lp-menu" type="button" aria-expanded={menuOpen} aria-label={menuOpen ? 'Fechar menu' : 'Abrir menu'} onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X size={22} /> : <Menu size={22} />}</button>
          </div>
        </div>
      </header>

      <main id="conteudo">
        <section className="ao-lp-hero" aria-labelledby="ao-lp-hero-title">
          <div className="ao-lp-hero-glow" aria-hidden="true" />
          <div className="ao-lp-container ao-lp-hero-inner">
            <div className="ao-lp-hero-copy">
              <div className="ao-lp-pill"><span /> Sua operação de afiliados em uma nova órbita</div>
              <h1 id="ao-lp-hero-title">As oportunidades merecem <em>mais alcance.</em> Seu tempo merece <em>mais liberdade.</em></h1>
              <p className="ao-lp-hero-lead">Você já trabalha para encontrar boas oportunidades. Não precisa trabalhar o dobro para divulgá-las.</p>
              <p className="ao-lp-hero-sub">Descubra produtos, organize ideias, prepare conteúdos e acompanhe divulgações em um lugar feito para simplificar sua rotina.</p>
              <div className="ao-lp-hero-actions">
                <a className="ao-lp-button ao-lp-button--primary" href="#como-funciona">Ver como funciona <ArrowRight size={19} /></a>
                <a className="ao-lp-button ao-lp-button--ghost" href="/login">Entrar <ArrowUpRight size={18} /></a>
              </div>
              <div className="ao-lp-hero-caption"><span className="ao-lp-caption-line" /> Conheça a plataforma em evolução. Sem promessas de resultados garantidos.</div>
            </div>
            <div className="ao-lp-hero-art" aria-hidden="true">
              <div className="ao-lp-orbit-grid" />
              <div className="ao-lp-orbit-halo ao-lp-orbit-halo--outer" />
              <div className="ao-lp-orbit-halo ao-lp-orbit-halo--inner" />
              <div className="ao-lp-orbit-ring ao-lp-orbit-ring--one" />
              <div className="ao-lp-orbit-ring ao-lp-orbit-ring--two" />
              <div className="ao-lp-orbit-core"><span className="ao-lp-orbit-core-mini">AUTO</span><strong>ORBITAL</strong><span className="ao-lp-orbit-core-mark"><Orbit size={42} strokeWidth={1.2} /></span></div>
              <div className="ao-lp-orbit-satellite ao-lp-orbit-satellite--one"><Search size={17} /><span>Descobrir</span></div>
              <div className="ao-lp-orbit-satellite ao-lp-orbit-satellite--two"><Sparkles size={17} /><span>Preparar</span></div>
              <div className="ao-lp-orbit-satellite ao-lp-orbit-satellite--three"><CalendarDays size={17} /><span>Planejar</span></div>
              <div className="ao-lp-orbit-satellite ao-lp-orbit-satellite--four"><History size={17} /><span>Acompanhar</span></div>
            </div>
          </div>
          <a className="ao-lp-scroll-cue" href="#desafio">Explore a experiência <ArrowDown size={16} /></a>
        </section>

        <section className="ao-lp-section ao-lp-problem" id="desafio">
          <div className="ao-lp-container">
            <SectionHeading eyebrow="01 / O desafio" title="Uma oportunidade. Cinco abas. O mesmo trabalho repetido.">A rotina de divulgação pode se tornar um labirinto: copiar, adaptar, trocar de aplicativo, conferir horários e começar tudo outra vez.</SectionHeading>
            <div className="ao-lp-problem-stage" aria-label="Representação ilustrativa de um produto passando por várias janelas de redes sociais">
              <div className="ao-lp-problem-source"><div className="ao-lp-product-orb"><span><Layers3 size={28} /></span></div><strong>Seu produto</strong><small>Uma oportunidade encontrada</small></div>
              <div className="ao-lp-problem-path" aria-hidden="true"><span /><span /><span /></div>
              <div className="ao-lp-network-stack">
                {networkNames.map((name, index) => <div className="ao-lp-network-window" key={name}><div className="ao-lp-network-window-top"><span className="ao-lp-network-dot" /><span className="ao-lp-network-dot" /><span className="ao-lp-network-dot" /><strong>{name}</strong></div><div className="ao-lp-network-window-body"><Copy size={16} /><span>{index % 2 === 0 ? 'Adaptar e publicar' : 'Revisar e enviar'}</span><small>{index + 1} / 5</small></div></div>)}
              </div>
            </div>
            <div className="ao-lp-story-note"><span className="ao-lp-story-index">CENA 01</span><span>O caos da divulgação manual</span><Status tone="planned">Animação Scroll World em produção futura</Status></div>
          </div>
        </section>

        <section className="ao-lp-section ao-lp-accumulation" id="acumulo">
          <div className="ao-lp-container ao-lp-split">
            <div className="ao-lp-split-copy">
              <SectionHeading eyebrow="02 / O acúmulo" title="O problema não é uma postagem. São todas as próximas.">Quando os produtos e os horários se multiplicam, lembrar de cada etapa exige uma atenção que poderia estar dedicada a encontrar novas oportunidades.</SectionHeading>
              <div className="ao-lp-statement"><span>Uma aba esquecida.</span><span>Um horário perdido.</span><strong>Mais uma tarefa na sua cabeça.</strong></div>
            </div>
            <div className="ao-lp-calendar-art" aria-label="Ilustração de calendário com tarefas e horários">
              <div className="ao-lp-calendar-top"><CalendarDays size={21} /><strong>Sua rotina de divulgação</strong><span>visão ilustrativa</span></div>
              <div className="ao-lp-calendar-days"><span>SEG</span><span>TER</span><span>QUA</span><span>QUI</span><span>SEX</span></div>
              <div className="ao-lp-calendar-grid"><span /><span className="ao-lp-calendar-slot" /><span /><span className="ao-lp-calendar-slot ao-lp-calendar-slot--violet" /><span /><span className="ao-lp-calendar-slot ao-lp-calendar-slot--violet" /><span /><span className="ao-lp-calendar-slot" /><span /><span className="ao-lp-calendar-slot" /></div>
              <div className="ao-lp-calendar-tasks"><div><Clock3 size={16} /><span>Revisar publicações pendentes</span><span>Hoje</span></div><div><Copy size={16} /><span>Adaptar novos conteúdos</span><span>Próximo</span></div><div><Send size={16} /><span>Conferir destinos</span><span>Depois</span></div></div>
            </div>
          </div>
        </section>

        <section className="ao-lp-section ao-lp-turn" id="virada">
          <div className="ao-lp-container ao-lp-turn-inner">
            <div className="ao-lp-turn-beam" aria-hidden="true" />
            <div className="ao-lp-turn-symbol" aria-hidden="true"><span><Orbit size={68} strokeWidth={1.1} /></span></div>
            <span className="ao-lp-eyebrow ao-lp-eyebrow--center">03 / A virada</span>
            <h2>Menos abas abertas.<br /><em>Mais clareza para avançar.</em></h2>
            <p>Imagine suas oportunidades, conteúdos e programações seguindo um mesmo fluxo. Sem transformar cada nova divulgação em uma lista de tarefas dispersas.</p>
            <div className="ao-lp-flow-pills" aria-label="Etapas organizadas"><span>Produto</span><ArrowRight size={19} /><span>Conteúdo</span><ArrowRight size={19} /><span>Agenda</span><ArrowRight size={19} /><span>Acompanhamento</span></div>
            <div className="ao-lp-story-note ao-lp-story-note--center"><span className="ao-lp-story-index">CENA 02</span><span>A transformação orbital</span><Status tone="planned">Movimento cinematográfico futuro</Status></div>
          </div>
        </section>

        <section className="ao-lp-section ao-lp-demo" id="como-funciona">
          <div className="ao-lp-container">
            <SectionHeading eyebrow="04 / O produto em ação" title="Do primeiro produto ao último detalhe. Um fluxo mais simples de acompanhar.">Acompanhe uma demonstração ilustrativa das etapas do Auto Orbital. Você continua no controle da seleção, do conteúdo e da programação.</SectionHeading>
            <div className="ao-lp-demo-layout">
              <div className="ao-lp-demo-steps" role="tablist" aria-label="Etapas da demonstração">
                {steps.map((step, index) => <button key={step.id} type="button" role="tab" id={'ao-lp-tab-' + step.id} aria-controls="ao-lp-demo-panel" aria-selected={active === step.id} className={'ao-lp-demo-step' + (active === step.id ? ' ao-lp-demo-step--active' : '')} onClick={() => setActive(step.id)}><span className="ao-lp-demo-number">0{index + 1}</span><span><strong>{step.name}</strong><small>{step.label}</small></span><ArrowUpRight size={18} /></button>)}
              </div>
              <div className="ao-lp-demo-display" id="ao-lp-demo-panel" role="tabpanel" aria-labelledby={'ao-lp-tab-' + active}>
                <DemoVisual active={active} />
                <div className="ao-lp-demo-explanation"><span className="ao-lp-demo-explanation-icon"><Check size={18} /></span><div><strong>{selected.label}</strong><p>{selected.hint}</p></div></div>
              </div>
            </div>
            <div className="ao-lp-story-note"><span className="ao-lp-story-index">CENA 03</span><span>Exploração do painel em etapas</span><Status tone="planned">Câmera Scroll World futura</Status></div>
          </div>
        </section>

        <section className="ao-lp-section ao-lp-benefits" id="beneficios">
          <div className="ao-lp-container">
            <SectionHeading eyebrow="05 / O que muda na sua rotina" title="Não se trata de postar mais. Trata-se de trabalhar melhor.">O valor está em reduzir o vai e vem entre tarefas e trazer organização ao processo que você já executa como afiliado.</SectionHeading>
            <div className="ao-lp-benefit-grid">
              <article className="ao-lp-benefit-card"><span className="ao-lp-benefit-icon"><Layers3 size={24} /></span><span className="ao-lp-benefit-num">01</span><h3>Organização para continuar de onde parou.</h3><p>Produtos e listas evitam que cada nova publicação comece com uma busca do zero.</p><Status>Recurso existente</Status></article>
              <article className="ao-lp-benefit-card"><span className="ao-lp-benefit-icon"><Sparkles size={24} /></span><span className="ao-lp-benefit-num">02</span><h3>Mais apoio na hora de encontrar as palavras.</h3><p>O editor reúne a preparação de textos e pode contar com assistência de IA configurada.</p><Status tone="conditional">IA depende de configuração</Status></article>
              <article className="ao-lp-benefit-card"><span className="ao-lp-benefit-icon"><CalendarDays size={24} /></span><span className="ao-lp-benefit-num">03</span><h3>Mais intenção, menos improviso.</h3><p>Planeje horários e acompanhe publicações sem depender apenas da memória.</p><Status tone="conditional">Conforme rede e autorização</Status></article>
            </div>
          </div>
        </section>

        <section className="ao-lp-section ao-lp-future" id="recursos">
          <div className="ao-lp-container">
            <div className="ao-lp-future-intro">
              <span className="ao-lp-eyebrow"><span className="ao-lp-eyebrow-line" />06 / A próxima órbita</span>
              <h2>A ferramenta de hoje.<br /><em>A evolução que estamos construindo.</em></h2>
              <p>O Auto Orbital nasceu para organizar a divulgação de afiliados. Nossa visão é avançar para um fluxo mais inteligente e automatizado, sem esconder o que ainda está em desenvolvimento.</p>
            </div>
            <div className="ao-lp-future-grid">
              <article className="ao-lp-future-card ao-lp-future-card--feature"><div className="ao-lp-future-icon"><Zap size={27} /></div><Status tone="planned">Em desenvolvimento</Status><h3>Piloto Automático Orbital</h3><p>Visão futura de coleta de oportunidades, análise, criação assistida por IA e publicação com critérios, limites e controles definidos pelo afiliado.</p><div className="ao-lp-future-process"><span>Coleta</span><ArrowRight size={16} /><span>Análise</span><ArrowRight size={16} /><span>Conteúdo</span><ArrowRight size={16} /><span>Publicação</span></div><small>Não disponível nesta fase. Depende de estudo técnico, custos e autorizações.</small></article>
              <article className="ao-lp-future-card"><div className="ao-lp-future-icon"><Globe2 size={27} /></div><Status tone="planned">Em estudo</Status><h3>Uma plataforma. Diferentes programas de afiliados.</h3><p>A Shopee é a primeira integração de catálogo. Outras lojas poderão entrar conforme a viabilidade técnica e as permissões de cada programa.</p><div className="ao-lp-future-platforms"><span>Shopee <b>Integração inicial</b></span><span>Outros programas <b>Expansão planejada</b></span></div></article>
              <article className="ao-lp-future-card"><div className="ao-lp-future-icon"><History size={27} /></div><Status tone="conditional">Cobertura em evolução</Status><h3>Entender o que acontece depois de publicar.</h3><p>Histórico e acompanhamento já fazem parte do produto. A expansão de análises depende dos dados oficiais disponibilizados pelas redes.</p></article>
            </div>
          </div>
        </section>

        <section className="ao-lp-section ao-lp-trust" id="perguntas">
          <div className="ao-lp-container ao-lp-trust-layout">
            <div className="ao-lp-trust-copy">
              <span className="ao-lp-eyebrow"><span className="ao-lp-eyebrow-line" />07 / Confiança primeiro</span>
              <h2>Conecte com clareza. Divulgue com consciência.</h2>
              <p>As redes sociais têm regras, permissões e formatos diferentes. O Auto Orbital não esconde isso: cada conexão e cada forma de publicação dependem do que o provedor efetivamente autoriza.</p>
              <div className="ao-lp-trust-badges"><div><ShieldCheck size={21} /><span>Autorizações oficiais por rede compatível</span></div><div><LockKeyhole size={21} /><span>Controles e permissões por conta</span></div><div><CheckCircle2 size={21} /><span>Status de recursos apresentados com transparência</span></div></div>
            </div>
            <div className="ao-lp-faq">
              <h3>Perguntas que importam</h3>
              {faqs.map((item) => <details key={item.q}><summary>{item.q}<ChevronDown size={19} /></summary><p>{item.a}</p></details>)}
            </div>
          </div>
        </section>

        <section className="ao-lp-section ao-lp-pricing" id="planos">
          <div className="ao-lp-container">
            <div className="ao-lp-pricing-box">
              <span className="ao-lp-eyebrow ao-lp-eyebrow--center">08 / O próximo passo</span>
              <Status tone="planned">Planos em definição</Status>
              <h2>Primeiro, o valor.<br /><em>Depois, o plano certo.</em></h2>
              <p>Estamos estudando os custos da inteligência artificial, integrações, infraestrutura e volume de publicações para definir planos e cotas sustentáveis.</p>
              <div className="ao-lp-pricing-rule"><span>Sem preço fictício.</span><span>Sem compra antecipada.</span><span>Sem promessas vagas.</span></div>
              <small>O Auto Orbital ainda não iniciou sua comercialização.</small>
            </div>
          </div>
        </section>

        <section className="ao-lp-section ao-lp-final" id="comecar">
          <div className="ao-lp-container ao-lp-final-inner">
            <div className="ao-lp-final-orbit" aria-hidden="true"><Orbit size={110} strokeWidth={0.9} /></div>
            <span className="ao-lp-eyebrow ao-lp-eyebrow--center">09 / Sua próxima órbita</span>
            <h2>Boas oportunidades merecem <em>uma rotina à altura.</em></h2>
            <p>Conheça o que já estamos construindo para transformar a forma como afiliados organizam e divulgam suas oportunidades.</p>
            <div className="ao-lp-final-actions"><a className="ao-lp-button ao-lp-button--primary" href="#como-funciona">Ver como funciona <ArrowRight size={19} /></a><a className="ao-lp-button ao-lp-button--ghost" href="/login">Entrar <ArrowUpRight size={18} /></a></div>
          </div>
        </section>
      </main>

      <footer className="ao-lp-footer"><div className="ao-lp-container ao-lp-footer-inner"><a href="#topo" className="ao-lp-footer-brand"><Orbit size={22} /> AUTO ORBITAL</a><span>Uma plataforma em evolução para afiliados.</span><div><a href="/termos">Termos</a><a href="/privacidade">Privacidade</a><a href="/login">Entrar</a></div></div></footer>
    </div>
  )
}
