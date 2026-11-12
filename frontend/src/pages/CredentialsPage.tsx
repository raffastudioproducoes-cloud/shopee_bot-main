import { formatInstant } from "../lib/userTimeZone"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { createContext, useContext, useEffect, useState, type ReactNode } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import {
  credentialsApi,
  shopeeAffiliateApi,
  type SimpleNetwork,
  type CredentialStatusWithLight,
} from "../api/credentials"
import { Panel } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { Skeleton, SkeletonCard, SkeletonRegion } from "../components/ui/Skeleton"
import { TextInput } from "../components/ui/TextInput"
import { StatusBadge } from "../components/ui/StatusBadge"
import { ConnectionLight } from "../components/ui/ConnectionLight"
import { Icon } from "../components/ui/Icon"
import { Modal } from "../components/ui/Modal"
import { isNetworkDisabled } from "../lib/networkLimits"
import { groupCredentialCards } from "../lib/credentialSections"
import { shopeeVideoApi, type ShopeeVideoStatus } from "../api/shopeeVideo"
import { CREDENTIAL_BRAND_LOGOS, FUTURE_CREDENTIAL_PLATFORMS, type CredentialTab } from "../lib/credentialPlatforms"

// Nenhum card USER recebe App ID/Secret. Shopee é ID de afiliado; redes
// sociais usam OAuth. Shopee Vídeo usa OAuth de criador afiliado.

// Grade de 2 colunas que colapsa pra 1 em telas estreitas (mesmo efeito do
// antigo `grid-cols-1 sm:grid-cols-2`, sem depender de breakpoint Tailwind).
type OAuthNetwork = "threads" | "x" | "facebook" | "tiktok" | "instagram" | "shopee-video"

const OAUTH_CONSENT: Record<OAuthNetwork, { label: string; details: string }> = {
  threads: { label: "Threads", details: "sua identidade no Threads e autorização para publicar posts em seu nome" },
  x: { label: "X", details: "sua identidade no X e autorização para publicar posts em seu nome" },
  facebook: { label: "Facebook", details: "a Página que você administra e autorização para publicar nela em seu nome" },
  tiktok: { label: "TikTok", details: "sua identidade no TikTok e autorização para publicar conteúdo em seu nome" },
  instagram: { label: "Instagram", details: "sua conta Business/Creator e autorização para publicar conteúdo em seu nome" },
  "shopee-video": { label: "Shopee Vídeo", details: "sua conta de criador afiliado e autorização para gerenciar vídeos e produtos vinculados" },
}

function OAuthConsentModal({
  network,
  open,
  busy,
  onClose,
  onContinue,
}: {
  network: OAuthNetwork
  open: boolean
  busy: boolean
  onClose: () => void
  onContinue: () => void
}) {
  const consent = OAUTH_CONSENT[network]
  return (
    <Modal open={open} onClose={onClose} title={`Conectar ${consent.label}`}>
      <div className="csp-s-0188">
        <p className="csp-s-0189">
          Você será levado ao {consent.label} para autorizar esta conexão.
        </p>
        <p className="csp-s-0190">
          O Auto Orbital solicitará {consent.details}. A conexão é vinculada somente ao seu perfil ativo e pode ser removida a qualquer momento em “Desconectar”.
        </p>
        <div className="csp-s-0191">
          <Button type="button" variant="ghost" disabled={busy} onClick={onClose}>Cancelar</Button>
          <Button type="button" variant="primary" disabled={busy} onClick={onContinue}>
            {busy ? "Redirecionando..." : `Continuar para ${consent.label}`}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

// ── Card recolhivel: estado por card em localStorage; recolhido mostra so
// titulo + status (o corpo e escondido por CSS, ver .cred-card em index.css). ──

const COLLAPSE_KEY = "credentials-collapsed:"
const CollapseCtx = createContext<{ collapsed: boolean; toggle: () => void }>({ collapsed: false, toggle: () => {} })

function readCollapsed(id: string): boolean {
  try {
    // Primeiro acesso: card compacto. Respeitar preferência anterior de expansão.
    return localStorage.getItem(COLLAPSE_KEY + id) !== "0"
  } catch {
    return true
  }
}

function BrandLogo({ platform, name }: { platform: string; name: string }) {
  const logos = CREDENTIAL_BRAND_LOGOS[platform] ?? []
  return (
    <span className={`credential-brand credential-brand--${platform}`} aria-hidden="true">
      {logos.map((logo) => (
        <img key={logo} src={`/brand-logos/${logo}`} alt="" width={38} height={38} loading="lazy" />
      ))}
      {!logos.length && <span className="credential-brand__fallback">{name}</span>}
    </span>
  )
}

/** Independente do estado aberto/fechado do card principal. */
function CredentialHelp({ children, title = "Como conectar e usar este serviço" }: { children: ReactNode; title?: string }) {
  return (
    <details className="credential-help">
      <summary><Icon name="circle-help" size={17} /> {title}</summary>
      <div className="credential-help__body">{children}</div>
    </details>
  )
}

function CredPanel({ id, children }: { id: string; children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(() => readCollapsed(id))
  const toggle = () => {
    const next = !collapsed
    setCollapsed(next)
    try {
      localStorage.setItem(COLLAPSE_KEY + id, next ? "1" : "0")
    } catch {
      // sem localStorage: so nao persiste
    }
  }
  return (
    <CollapseCtx.Provider value={{ collapsed, toggle }}>
      <Panel surface="dark" className={collapsed ? "cred-card is-collapsed" : "cred-card"}>
        {children}
      </Panel>
    </CollapseCtx.Provider>
  )
}

function CredHeader({ title, brand, trailing }: { title: string; brand: string; trailing?: ReactNode }) {
  const { collapsed, toggle } = useContext(CollapseCtx)
  return (
    <header className="csp-s-0192">
      <button type="button" className="csp-s-0193" onClick={toggle}
        aria-expanded={!collapsed} aria-label={`${collapsed ? "Expandir" : "Recolher"} ${title}`}>
        <BrandLogo platform={brand} name={title} />
        <span className="csp-s-0194">{title}</span>
        <span className="csp-s-0201">{trailing}</span>
        <Icon name={collapsed ? "chevron-down" : "chevron-up"} size={18} />
      </button>
    </header>
  )
}

const TESTING_POLL_MS = 1500

function anyTesting(map?: Record<string, { state?: string }>): boolean {
  return !!map && Object.values(map).some((s) => s?.state === "testing")
}

// Luz + selo + data do teste, iguais em todos os cards. Em "testing" a luz vira
// um spinner e o selo anuncia "Testando…" (região viva, lida por leitor de tela).
function ConnectionStatus({ status, compact = false }: { status: CredentialStatusWithLight; compact?: boolean }) {
  const testing = status.state === "testing"
  return (
    <>
      {testing ? (
        <Icon name="loader-2" size={14} className="animate-spin" style={{ color: "var(--amber-300)", flexShrink: 0 }} />
      ) : (
        <ConnectionLight state={status.light} />
      )}
      <span role="status" aria-live="polite" className="csp-s-0195">
        <StatusBadge
          tone={compact ? (status.connected ? "positive" : "neutral") : (status.light === "green" ? "positive" : "neutral")}
          icon={testing ? undefined : status.light === "green" ? "check-circle-2" : "x-circle"}
        >
          {compact ? (status.connected ? "Conectado" : "Desconectado") : (status.status_text ?? (status.connected ? "Conectado" : "Desconectado"))}
        </StatusBadge>
      </span>
      {status.checked_at && !testing && !compact && (
        <span className="csp-s-0196">
          Testado em {formatInstant(status.checked_at)}
        </span>
      )}
    </>
  )
}

function ConnectionDetails({ status }: { status: CredentialStatusWithLight }) {
  if (!status.checked_at && !status.check_message && !status.status_text) return null
  return (
    <div className="credentials-connection-details">
      {status.status_text && <span>{status.status_text}</span>}
      {status.checked_at && <span>Último teste: {formatInstant(status.checked_at)}</span>}
      {status.check_message && <span>{status.check_message}</span>}
    </div>
  )
}

const EMPTY_STATUS: CredentialStatusWithLight = {
  connected: false,
  light: "red",
  checked_at: null,
  check_message: null,
}

export function CredentialsPage() {
  const { logout } = useAuthStore()
  const queryClient = useQueryClient()
  const [banner, setBanner] = useState<{ ok: boolean; text: string } | null>(null)
  const [activeTab, setActiveTab] = useState<CredentialTab>("stores")

  const { data: status, isLoading, isError: isStatusError, refetch: refetchStatus } = useQuery({
    queryKey: ["credentials"],
    queryFn: () => credentialsApi.list(),
    // Salvar/reconectar dispara teste automático no backend: enquanto algum
    // card estiver "testando", consulta de novo (o backend encerra o estado
    // sozinho em até ~45 s, então o polling nunca fica infinito).
    refetchInterval: (q) => (anyTesting(q.state.data) ? TESTING_POLL_MS : false),
  })
  const { data: shopeeIdentity } = useQuery({
    queryKey: ["shopee", "affiliate"],
    queryFn: shopeeAffiliateApi.status,
  })
  const { data: shopeeVideoStatus } = useQuery({
    queryKey: ["shopee-video", "status"], queryFn: shopeeVideoApi.status,
  })

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const result = params.get("shopee_video")
    if (!result) return
    setActiveTab("social")
    setBanner(result === "success"
      ? { ok: true, text: "Shopee Vídeo autorizada para este perfil." }
      : { ok: false, text: "Não foi possível autorizar Shopee Vídeo. Tente novamente." })
    params.delete("shopee_video")
    const query = params.toString()
    window.history.replaceState(null, "", window.location.pathname + (query ? `?${query}` : ""))
    void queryClient.invalidateQueries({ queryKey: ["shopee-video", "status"] })
  }, [queryClient])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const threads = params.get("threads")
    if (!threads) return
    setBanner(
      threads === "success"
        ? { ok: true, text: "Threads conectado com sucesso." }
        : { ok: false, text: "Falha ao conectar o Threads. Tente novamente." }
    )
    params.delete("threads")
    const query = params.toString()
    window.history.replaceState(null, "", window.location.pathname + (query ? `?${query}` : ""))
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const tiktok = params.get("tiktok")
    if (!tiktok) return
    setBanner(
      tiktok === "success"
        ? { ok: true, text: "TikTok conectado com sucesso." }
        : { ok: false, text: "Falha ao conectar o TikTok. Tente novamente." }
    )
    params.delete("tiktok")
    const query = params.toString()
    window.history.replaceState(null, "", window.location.pathname + (query ? `?${query}` : ""))
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const instagram = params.get("instagram")
    if (!instagram) return
    setBanner(
      instagram === "success"
        ? { ok: true, text: "Instagram conectado com sucesso." }
        : { ok: false, text: "Falha ao conectar o Instagram. Tente novamente." }
    )
    params.delete("instagram")
    const query = params.toString()
    window.history.replaceState(null, "", window.location.pathname + (query ? `?${query}` : ""))
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const x = params.get("x")
    if (!x) return
    setBanner(
      x === "success"
        ? { ok: true, text: "X conectado com sucesso." }
        : { ok: false, text: "Falha ao conectar o X. Tente novamente." }
    )
    params.delete("x")
    const query = params.toString()
    window.history.replaceState(null, "", window.location.pathname + (query ? `?${query}` : ""))
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const facebook = params.get("facebook")
    if (!facebook) return
    setBanner(
      facebook === "success"
        ? { ok: true, text: "Facebook conectado com sucesso." }
        : { ok: false, text: "Falha ao conectar o Facebook. Tente novamente." }
    )
    params.delete("facebook")
    const query = params.toString()
    window.history.replaceState(null, "", window.location.pathname + (query ? `?${query}` : ""))
  }, [])

  const onAuthError = (err: Error) => {
    if (err.message.includes("401") || err.message === "Não autenticado") {
      logout()
      router.navigate({ to: "/login" })
      return
    }
    // Extrapolação: antes desse fallback, qualquer erro que não fosse 401
    // (ex: 502 do bridge interno na validação da Shopee, 400 de credencial
    // inválida) era descartado em silêncio — o botão voltava de "Salvando..."
    // pra "Salvar" sem nenhum aviso, dando a impressão de que nada aconteceu.
    setBanner({ ok: false, text: err.message || "Erro ao salvar credencial." })
  }

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["credentials"] })

  if (isLoading) {
    return (
      <SkeletonRegion><div className="csp-s-0197"><div><Skeleton width="180px" height={34} /><Skeleton className="skeleton-sub" width="360px" /></div><div className="credentials-card-grid csp-named-card-grid">{[1,2,3,4,5].map(i => <SkeletonCard key={i} />)}</div></div></SkeletonRegion>
    )
  }

  if (!status && isStatusError) {
    return (
      <div className="csp-s-0198">
        <h1 className="csp-s-0199">Credenciais</h1>
        <div role="alert" className="credentials-group__empty">
          Não foi possível consultar o cadastro das credenciais. Tente novamente para visualizar os grupos corretamente.
        </div>
        <div>
          <Button type="button" variant="primary" onClick={() => {
            if (!status) void refetchStatus()
          }}>
            Tentar novamente
          </Button>
        </div>
      </div>
    )
  }

  // O agrupamento considera credenciais cadastradas, mesmo que o último teste
  // esteja vencido, com erro ou em andamento; a luz não define o grupo.
  const cards: { key: string; title: string; category: CredentialTab; connected: boolean; element: ReactNode }[] = [
    {
      key: "facebook",
      title: "Facebook",
      category: "social",
      connected: Boolean(status?.facebook?.connected),
      element: <FacebookCredentialCard key="facebook" status={status?.facebook ?? EMPTY_STATUS}
        onSaved={invalidate} onAuthError={onAuthError} setBanner={setBanner} />,
    },
    {
      key: "instagram",
      title: "Instagram",
      category: "social",
      connected: Boolean(status?.instagram?.connected),
      element: <InstagramCredentialCard key="instagram" status={status?.instagram ?? EMPTY_STATUS}
        onSaved={invalidate} onAuthError={onAuthError} setBanner={setBanner} />,
    },
    {
      key: "kwai",
      title: "Kwai",
      category: "social",
      connected: false,
      element: <KwaiComingSoonCredentialCard key="kwai" />,
    },
    {
      key: "shopee",
      title: "Shopee",
      category: "stores",
      connected: Boolean(status?.shopee?.connected),
      element: <ShopeeAffiliateCredentialCard key="shopee" status={status?.shopee ?? EMPTY_STATUS}
        affiliateId={shopeeIdentity?.affiliate_id ?? null}
        catalogAvailable={shopeeIdentity?.catalog_available ?? false}
        onSaved={() => { invalidate(); void queryClient.invalidateQueries({ queryKey: ["shopee", "affiliate"] }) }}
        onAuthError={onAuthError} setBanner={setBanner} />,
    },
    {
      key: "shopee-video",
      title: "Shopee Vídeo",
      category: "social",
      connected: Boolean(shopeeVideoStatus?.connected),
      element: <ShopeeVideoCredentialCard key="shopee-video" status={shopeeVideoStatus}
        onAuthError={onAuthError} setBanner={setBanner} />,
    },
    {
      key: "threads",
      title: "Threads",
      category: "social",
      connected: Boolean(status?.threads?.connected),
      element: <ThreadsCredentialCard key="threads" status={status?.threads ?? EMPTY_STATUS}
        onSaved={invalidate} onAuthError={onAuthError} setBanner={setBanner} />,
    },
    {
      key: "tiktok",
      title: "TikTok",
      category: "social",
      connected: Boolean(status?.tiktok?.connected),
      element: <TikTokCredentialCard key="tiktok" status={status?.tiktok ?? EMPTY_STATUS}
        onSaved={invalidate} onAuthError={onAuthError} setBanner={setBanner} />,
    },
    {
      key: "x",
      title: "X (Twitter)",
      category: "social",
      connected: Boolean(status?.x?.connected),
      element: <XCredentialCard key="x" status={status?.x ?? EMPTY_STATUS}
        onSaved={invalidate} onAuthError={onAuthError} setBanner={setBanner} />,
    },
    ...FUTURE_CREDENTIAL_PLATFORMS.map((platform) => ({
      key: platform.key,
      title: platform.title,
      category: platform.category,
      connected: false,
      element: <FutureCredentialCard key={platform.key} platform={platform} />,
    })),
  ]
  const grouped = groupCredentialCards(cards.filter((card) => card.category === activeTab))


  return (
    <div className="csp-s-0198">
      <div>
        <h1 className="csp-s-0199">Credenciais</h1>
        <p className="csp-s-0200">Conecte suas lojas e redes para usar seus próprios links de afiliado e publicar conteúdo.</p>
      </div>

      <div className="credentials-intro" role="note">
        <Icon name="info" size={20} />
        <div>
          <strong>Como configurar suas credenciais</strong>
          <p>Em <b>Lojas</b>, informe seu identificador de afiliado quando a integração estiver disponível.
            Em <b>Redes sociais</b>, autorize apenas os perfis em que deseja publicar.
            Abra um card para configurar e expanda “Como conectar” se precisar de ajuda.
            Segredos de API não são exibidos novamente; os IDs públicos de afiliado podem ser consultados e alterados.</p>
        </div>
      </div>

      <div className="credentials-tabs" role="tablist" aria-label="Categorias de credenciais">
        <button type="button" role="tab" id="credentials-tab-stores" aria-controls="credentials-pane" aria-selected={activeTab === "stores"}
          className={activeTab === "stores" ? "is-active" : ""} onClick={() => setActiveTab("stores")}>
          <Icon name="shopping-bag" size={18} /> Lojas <span>{cards.filter(c => c.category === "stores").length}</span>
        </button>
        <button type="button" role="tab" id="credentials-tab-social" aria-controls="credentials-pane" aria-selected={activeTab === "social"}
          className={activeTab === "social" ? "is-active" : ""} onClick={() => setActiveTab("social")}>
          <Icon name="users" size={18} /> Redes sociais <span>{cards.filter(c => c.category === "social").length}</span>
        </button>
      </div>

      {banner && (
        <div
          style={{
            padding: "12px 16px",
            borderRadius: "var(--r-md)",
            font: "var(--fw-medium) var(--fs-body)/1.3 var(--font-sans)",
            background: banner.ok ? "var(--positive-on-glass)" : "var(--negative-on-glass)",
            color: banner.ok ? "var(--positive-ink)" : "var(--negative-ink)",
          }}
        >
          {banner.text}
        </div>
      )}

      {/* Grupos independentes em cada aba; ordem PT-BR em ambos. */}
      <div id="credentials-pane" role="tabpanel" aria-labelledby={`credentials-tab-${activeTab}`} className="credentials-tab-panel">
      {[
        {
          id: "cadastradas",
          title: "Já credenciados",
          description: "Serviços com credenciais ou autorizações cadastradas.",
          cards: grouped.registered,
          empty: "Nenhuma credencial cadastrada. Conecte um serviço na seção abaixo.",
        },
        {
          id: "pendentes",
          title: "Ainda não cadastrados",
          description: "Abra um serviço disponível para conectar ou veja o que vem em breve.",
          cards: grouped.pending,
          empty: "Todos os serviços disponíveis já foram cadastrados.",
        },
      ].map((group) => (
        <section className="credentials-group" aria-labelledby={`credentials-${group.id}`} key={group.id}>
          <div className="credentials-group__header">
            <div>
              <h2 id={`credentials-${group.id}`} className="credentials-group__title">{group.title}</h2>
              <p className="credentials-group__description">{group.description}</p>
            </div>
            <span className="credentials-group__count" title={`${group.cards.length} serviços`}>
              {group.cards.length}
            </span>
          </div>
          {group.cards.length ? (
            <div className="credentials-card-grid csp-named-card-grid">
              {group.cards.map((card) => card.element)}
            </div>
          ) : (
            <p className="credentials-group__empty">{group.empty}</p>
          )}
        </section>
      ))}
      </div>
    </div>
  )
}

// ── Status compacto. Testes manuais ficam exclusivamente no painel ADMIN. ──

function CredentialTrailing({
  status,
}: {
  network: SimpleNetwork | "threads"
  label: string
  status: CredentialStatusWithLight
  onSaved: () => void
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
}) {
  return <ConnectionStatus status={status} compact />
}

// ── Identidade de afiliado Shopee, sem formulário de chave API ──────────────

function ShopeeAffiliateCredentialCard({
  status, affiliateId, catalogAvailable, onSaved, onAuthError, setBanner,
}: {
  status: CredentialStatusWithLight
  affiliateId: string | null
  catalogAvailable: boolean
  onSaved: () => void
  onAuthError: (error: Error) => void
  setBanner: (banner: { ok: boolean; text: string } | null) => void
}) {
  const [value, setValue] = useState("")
  useEffect(() => { if (affiliateId) setValue(affiliateId) }, [affiliateId])
  const save = useMutation({
    mutationFn: () => shopeeAffiliateApi.save(value.trim()),
    onSuccess: () => {
      setBanner({ ok: true, text: "ID de afiliado salvo. Os próximos links do catálogo usarão sua identificação." })
      onSaved()
    },
    onError: onAuthError,
  })
  const remove = useMutation({
    mutationFn: shopeeAffiliateApi.delete,
    onSuccess: () => {
      setValue("")
      setBanner({ ok: true, text: "ID de afiliado removido. Novos links não serão gerados até configurar outro ID." })
      onSaved()
    },
    onError: onAuthError,
  })
  return (
    <CredPanel id="Shopee">
      <CredHeader title="Shopee" brand="shopee" trailing={<ConnectionStatus status={status} compact />} />
      <ConnectionDetails status={status} />
      <CredentialHelp title="Onde encontrar meu ID e como funcionam os links?">
        <p className="csp-s-0203">
          O Auto Orbital fornece a API de busca. Você só precisa informar seu ID de Afiliado Shopee
          para que os links gerados usem a sua identificação, sem compartilhar App ID ou Secret.
        </p>
        <p className="csp-s-0203">
          {catalogAvailable ? "Catálogo da plataforma disponível." : "Catálogo da plataforma indisponível no momento."}
          {" "}O ID informado não é uma autorização OAuth; a comissão depende das regras da Shopee.
        </p>
        <a href="https://affiliate.shopee.com.br/account_setting" target="_blank" rel="noreferrer" className="csp-s-0206">
          Onde encontrar meu ID de afiliado na Shopee ↗
        </a>
      </CredentialHelp>
      <form className="csp-s-0204" onSubmit={(event) => { event.preventDefault(); save.mutate() }}>
        <TextInput
          label="ID do afiliado (ou link completo com o ID)"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Digite seu ID numérico de afiliado"
          required
        />
        <div className="csp-s-0208">
          {status.connected && <Button type="button" variant="ghost" disabled={remove.isPending}
            onClick={() => remove.mutate()}>{remove.isPending ? "Removendo..." : "Desconectar"}</Button>}
          <Button type="submit" variant="primary" disabled={save.isPending || !value.trim()}>
            {save.isPending ? "Salvando..." : "Salvar ID"}
          </Button>
        </div>
      </form>
    </CredPanel>
  )
}

function KwaiComingSoonCredentialCard() {
  return (
    <CredPanel id="Kwai">
      <CredHeader title="Kwai" brand="kwai" trailing={<StatusBadge tone="warning">Em breve</StatusBadge>} />
      <div className="csp-s-0202">
        <CredentialHelp><p className="csp-s-0203">Em breve — a ligação com Kwai ainda não está disponível.</p></CredentialHelp>
      </div>
    </CredPanel>
  )
}

// Shopee Vídeo: OAuth auth_type=user, separado da Affiliate GraphQL.
function ShopeeVideoCredentialCard({ status, onAuthError, setBanner }: {
  status?: ShopeeVideoStatus
  onAuthError: (error: Error) => void
  setBanner: (value: { ok: boolean; text: string } | null) => void
}) {
  const [consentOpen, setConsentOpen] = useState(false)
  const queryClient = useQueryClient()
  const authorize = useMutation({
    mutationFn: shopeeVideoApi.authorize,
    onSuccess: ({ url }) => { window.location.assign(url) },
    onError: onAuthError,
  })
  const disconnect = useMutation({
    mutationFn: shopeeVideoApi.disconnect,
    onSuccess: () => {
      setBanner({ ok: true, text: "Conta Shopee Vídeo desconectada deste perfil no Auto Orbital." })
      void queryClient.invalidateQueries({ queryKey: ["shopee-video", "status"] })
    },
    onError: onAuthError,
  })
  const refresh = useMutation({
    mutationFn: shopeeVideoApi.refresh,
    onSuccess: () => {
      setBanner({ ok: true, text: "A autorização Shopee Vídeo foi renovada." })
      void queryClient.invalidateQueries({ queryKey: ["shopee-video", "status"] })
    },
    onError: onAuthError,
  })
  return (
    <CredPanel id="Shopee Vídeo">
      <CredHeader
        title="Shopee Vídeo"
        brand="shopee-video"
        trailing={
          <div className="csp-s-0201">
            <ConnectionLight state={status?.connected ? "green" : "yellow"}
              title={status?.connected ? "OAuth autorizado" : "Autorização ainda não concluída"} />
            <StatusBadge tone={status?.connected ? "positive" : "warning"}>
              {status?.connected ? "Autorizado" : status?.configured ? "Pronto para conectar" : "Configuração pendente"}
            </StatusBadge>
          </div>
        }
      />
      <div className="csp-s-0202">
        <CredentialHelp><p className="csp-s-0203">
            Conecte sua conta de criador afiliado pelo OAuth oficial da Shopee.
            A autorização vale somente para este perfil. A publicação de vídeos
            reais permanece indisponível até a homologação do fluxo completo.
        </p></CredentialHelp>
        {status?.connected && <p role="status">
          Autorização recebida{status.token_valid ? ", token vigente" : ", token expirado"}.
          {status.sandbox ? " Ambiente de testes." : " Ambiente oficial."}
        </p>}
        {status?.connected && !status.token_valid && <Button type="button" variant="secondary"
          loading={refresh.isPending} disabled={refresh.isPending}
          onClick={() => refresh.mutate()}>Renovar acesso</Button>}
        {status?.connected && <Button type="button" variant="ghost" disabled={disconnect.isPending}
          onClick={() => disconnect.mutate()}>Desconectar deste perfil</Button>}
        <Button type="button" variant="primary" disabled={!status?.configured || authorize.isPending}
          onClick={() => setConsentOpen(true)}>
          {status?.connected ? "Reconectar Shopee Vídeo" : "Conectar Shopee Vídeo"}
        </Button>
        <OAuthConsentModal network="shopee-video" open={consentOpen} busy={authorize.isPending}
          onClose={() => setConsentOpen(false)} onContinue={() => authorize.mutate()} />
      </div>
    </CredPanel>
  )
}

function FutureCredentialCard({ platform }: { platform: (typeof FUTURE_CREDENTIAL_PLATFORMS)[number] }) {
  return (
    <CredPanel id={`future-${platform.key}`}>
      <CredHeader title={platform.title} brand={platform.key} trailing={<StatusBadge tone="warning">Em breve</StatusBadge>} />
      <div className="credential-future-content">
        <CredentialHelp title={`Sobre a integração ${platform.title}`}>
          <p>{platform.detail}</p>
          <p>A conexão será liberada aqui quando estiver pronta. Não é necessário fornecer chaves ou tokens agora.</p>
        </CredentialHelp>
      </div>
    </CredPanel>
  )
}

// ── Card do Threads (OAuth — cola token já emitido) ─────────────────────────────

function ThreadsCredentialCard({
  status,
  onSaved,
  onAuthError,
  setBanner,
}: {
  status: CredentialStatusWithLight
  onSaved: () => void
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
}) {
  const connected = status.connected
  const [consentOpen, setConsentOpen] = useState(false)

  const authorizeMutation = useMutation({
    mutationFn: () => credentialsApi.authorizeThreads(),
    onSuccess: ({ url }) => {
      window.location.href = url
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: () => credentialsApi.deleteThreads(),
    onSuccess: () => {
      setBanner({ ok: true, text: "Threads desconectado." })
      onSaved()
    },
    onError: onAuthError,
  })

  return (
    <CredPanel id="Threads">
      <CredHeader
        title="Threads"
        brand="threads"
        trailing={
          <CredentialTrailing
            network="threads"
            label="Threads"
            status={status}
            onSaved={onSaved}
            onAuthError={onAuthError}
            setBanner={setBanner}
          />
        }
      />
      <ConnectionDetails status={status} />
      <div className="csp-s-0214">
        <CredentialHelp><p className="csp-s-0215">
          Conecte sua conta do Threads com um clique — nenhuma configuração técnica necessária.
        </p></CredentialHelp>

        <div className="csp-s-0216">
          <Button
            type="button"
            variant="primary"
            disabled={authorizeMutation.isPending}
            onClick={() => setConsentOpen(true)}
          >
            {authorizeMutation.isPending ? "Conectando..." : "Conectar Threads"}
          </Button>
          {connected && (
            <Button
              type="button"
              variant="ghost"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
              style={{ color: "var(--red-300)" }}
            >
              {deleteMutation.isPending ? "Removendo..." : "Desconectar"}
            </Button>
          )}
        </div>

      </div>
      <OAuthConsentModal
        network="threads"
        open={consentOpen}
        busy={authorizeMutation.isPending}
        onClose={() => setConsentOpen(false)}
        onContinue={() => authorizeMutation.mutate()}
      />
    </CredPanel>
  )
}

// ── Card do X (App ID/Secret + OAuth 2.0/PKCE) ──────────────────────────────────

function XCredentialCard({
  status,
  onSaved,
  onAuthError,
  setBanner,
}: {
  status: CredentialStatusWithLight
  onSaved: () => void
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
}) {
  const connected = status.connected
  const disabledReason = isNetworkDisabled("x")
  const [consentOpen, setConsentOpen] = useState(false)

  const authorizeMutation = useMutation({
    mutationFn: () => credentialsApi.authorizeX(),
    onSuccess: ({ url }) => {
      window.location.href = url
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: () => credentialsApi.delete("x"),
    onSuccess: () => {
      setBanner({ ok: true, text: "X desconectado." })
      onSaved()
    },
    onError: onAuthError,
  })

  return (
    <CredPanel id="X (Twitter)">
      <CredHeader
        title="X (Twitter)"
        brand="x"
        trailing={
          <CredentialTrailing
            network="x"
            label="X"
            status={status}
            onSaved={onSaved}
            onAuthError={onAuthError}
            setBanner={setBanner}
          />
        }
      />
      <ConnectionDetails status={status} />
      <div className="csp-s-0217">
        <CredentialHelp><p className="csp-s-0218">
          Conecte sua conta do X com um clique — nenhuma configuração técnica necessária.
        </p></CredentialHelp>

        <div className="csp-s-0219">
          <Button
            type="button"
            variant="primary"
            disabled={!!disabledReason || authorizeMutation.isPending}
            onClick={() => setConsentOpen(true)}
          >
            {authorizeMutation.isPending ? "Conectando..." : connected ? "Reconectar X" : "Conectar X"}
          </Button>
          {connected && (
            <Button
              type="button"
              variant="ghost"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
              style={{ color: "var(--red-300)" }}
            >
              {deleteMutation.isPending ? "Removendo..." : "Desconectar"}
            </Button>
          )}
        </div>

        {disabledReason && (
          <p role="status" className="csp-s-0220">
            Plano pago em breve; publicação no X pausada.
          </p>
        )}

        {connected && status.missing_scopes?.includes("media.write") && (
          <p role="alert" className="csp-s-0221">
            Reconecte o X para liberar imagens: esta conexão não tem a permissão de enviar mídia.
          </p>
        )}
      </div>
      <OAuthConsentModal
        network="x"
        open={consentOpen}
        busy={authorizeMutation.isPending}
        onClose={() => setConsentOpen(false)}
        onContinue={() => authorizeMutation.mutate()}
      />
    </CredPanel>
  )
}

// ── Card do Facebook (OAuth de app único — clicar "Conectar Facebook") ──────────

function FacebookCredentialCard({
  status,
  onSaved,
  onAuthError,
  setBanner,
}: {
  status: CredentialStatusWithLight
  onSaved: () => void
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
}) {
  const connected = status.connected
  const [consentOpen, setConsentOpen] = useState(false)

  const authorizeMutation = useMutation({
    mutationFn: () => credentialsApi.authorizeFacebook(),
    onSuccess: ({ url }) => {
      window.location.href = url
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: () => credentialsApi.delete("facebook"),
    onSuccess: () => {
      setBanner({ ok: true, text: "Facebook desconectado." })
      onSaved()
    },
    onError: onAuthError,
  })

  return (
    <CredPanel id="Facebook">
      <CredHeader
        title="Facebook"
        brand="facebook"
        trailing={
          <CredentialTrailing
            network="facebook"
            label="Facebook"
            status={status}
            onSaved={onSaved}
            onAuthError={onAuthError}
            setBanner={setBanner}
          />
        }
      />
      <ConnectionDetails status={status} />
      <div className="csp-s-0222">
        <CredentialHelp><p className="csp-s-0223">
          Conecte a Página do Facebook com um clique — nenhuma configuração técnica necessária.
          Se você administra mais de uma Página, a primeira encontrada é conectada automaticamente.
        </p></CredentialHelp>

        <div className="csp-s-0224">
          <Button
            type="button"
            variant="primary"
            disabled={authorizeMutation.isPending}
            onClick={() => setConsentOpen(true)}
          >
            {authorizeMutation.isPending ? "Conectando..." : connected ? "Reconectar Facebook" : "Conectar Facebook"}
          </Button>
          {connected && (
            <Button
              type="button"
              variant="ghost"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
              style={{ color: "var(--red-300)" }}
            >
              {deleteMutation.isPending ? "Removendo..." : "Desconectar"}
            </Button>
          )}
        </div>

      </div>
      <OAuthConsentModal
        network="facebook"
        open={consentOpen}
        busy={authorizeMutation.isPending}
        onClose={() => setConsentOpen(false)}
        onContinue={() => authorizeMutation.mutate()}
      />
    </CredPanel>
  )
}

// ── Card do TikTok (OAuth de app único — clicar "Conectar TikTok") ──────────────

function TikTokCredentialCard({
  status,
  onSaved,
  onAuthError,
  setBanner,
}: {
  status: CredentialStatusWithLight
  onSaved: () => void
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
}) {
  const connected = status.connected
  const [consentOpen, setConsentOpen] = useState(false)

  const authorizeMutation = useMutation({
    mutationFn: () => credentialsApi.authorizeTiktok(),
    onSuccess: ({ url }) => {
      window.location.href = url
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: () => credentialsApi.delete("tiktok"),
    onSuccess: () => {
      setBanner({ ok: true, text: "TikTok desconectado." })
      onSaved()
    },
    onError: onAuthError,
  })

  return (
    <CredPanel id="TikTok">
      <CredHeader
        title="TikTok"
        brand="tiktok"
        trailing={
          <CredentialTrailing
            network="tiktok"
            label="TikTok"
            status={status}
            onSaved={onSaved}
            onAuthError={onAuthError}
            setBanner={setBanner}
          />
        }
      />
      <ConnectionDetails status={status} />
      <div className="csp-s-0225">
        <CredentialHelp><p className="csp-s-0226">
          Conecte sua conta do TikTok com um clique — nenhuma configuração técnica necessária.
        </p></CredentialHelp>

        <div className="csp-s-0227">
          <Button
            type="button"
            variant="primary"
            disabled={authorizeMutation.isPending}
            onClick={() => setConsentOpen(true)}
          >
            {authorizeMutation.isPending ? "Conectando..." : connected ? "Reconectar TikTok" : "Conectar TikTok"}
          </Button>
          {connected && (
            <Button
              type="button"
              variant="ghost"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
              style={{ color: "var(--red-300)" }}
            >
              {deleteMutation.isPending ? "Removendo..." : "Desconectar"}
            </Button>
          )}
        </div>

      </div>
      <OAuthConsentModal
        network="tiktok"
        open={consentOpen}
        busy={authorizeMutation.isPending}
        onClose={() => setConsentOpen(false)}
        onContinue={() => authorizeMutation.mutate()}
      />
    </CredPanel>
  )
}

// ── Card do Instagram (OAuth de app único via Facebook Login for Business) ─────

function InstagramCredentialCard({
  status,
  onSaved,
  onAuthError,
  setBanner,
}: {
  status: CredentialStatusWithLight
  onSaved: () => void
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
}) {
  const connected = status.connected
  const [consentOpen, setConsentOpen] = useState(false)

  const authorizeMutation = useMutation({
    mutationFn: () => credentialsApi.authorizeInstagram(),
    onSuccess: ({ url }) => {
      window.location.href = url
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: () => credentialsApi.delete("instagram"),
    onSuccess: () => {
      setBanner({ ok: true, text: "Instagram desconectado." })
      onSaved()
    },
    onError: onAuthError,
  })

  return (
    <CredPanel id="Instagram">
      <CredHeader
        title="Instagram"
        brand="instagram"
        trailing={
          <CredentialTrailing
            network="instagram"
            label="Instagram"
            status={status}
            onSaved={onSaved}
            onAuthError={onAuthError}
            setBanner={setBanner}
          />
        }
      />
      <ConnectionDetails status={status} />
      <div className="csp-s-0228">
        <CredentialHelp><p className="csp-s-0229">
          Publicar exige uma conta Business/Creator vinculada a uma Página do Facebook — conecte
          com um clique, nenhuma configuração técnica necessária.
        </p></CredentialHelp>

        <div className="csp-s-0230">
          <Button
            type="button"
            variant="primary"
            disabled={authorizeMutation.isPending}
            onClick={() => setConsentOpen(true)}
          >
            {authorizeMutation.isPending ? "Conectando..." : connected ? "Reconectar Instagram" : "Conectar Instagram"}
          </Button>
          {connected && (
            <Button
              type="button"
              variant="ghost"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
              style={{ color: "var(--red-300)" }}
            >
              {deleteMutation.isPending ? "Removendo..." : "Desconectar"}
            </Button>
          )}
        </div>

      </div>
      <OAuthConsentModal
        network="instagram"
        open={consentOpen}
        busy={authorizeMutation.isPending}
        onClose={() => setConsentOpen(false)}
        onContinue={() => authorizeMutation.mutate()}
      />
    </CredPanel>
  )
}
