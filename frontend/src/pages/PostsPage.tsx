import { useMutation, useQueryClient, useInfiniteQuery } from "@tanstack/react-query"
import { useState, useCallback, useEffect } from "react"
import { useSearch } from "@tanstack/react-router"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import { scheduleUndoableDelete, useHiddenIds } from "../lib/undoableDelete"
import { postsApi, type Post, type PostNetwork } from "../api/posts"
import { formatUtcTimestamp } from "../lib/userTimeZone"
import { NETWORK_RULES } from "../lib/networkLimits"
import { NetworkLogo } from "../components/posts/NetworkPicker"
import { useProfileStore } from "../stores/profileStore"
import { formDraftKey } from "../lib/formDraftStorage"
import { POSTS_FETCH_LIMIT, POSTS_PER_PAGE, canAdvancePostHistory, paginatePostHistory, postsRefreshInterval } from "../lib/postHistoryPagination"
import { useAutosavedDraft } from "../hooks/useAutosavedDraft"
import { Panel, PanelHeader, Divider } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { IconButton } from "../components/ui/IconButton"
import { Badge } from "../components/ui/Badge"
import { StatusBadge } from "../components/ui/StatusBadge"
import { Modal } from "../components/ui/Modal"
import { PageSkeleton } from "../components/ui/Skeleton"
import { PostDetailsModal } from "../components/posts/PostDetailsModal"
import { ConfirmPublicationModal, RetryFailedModal } from "../components/posts/PublicationDecisionModals"
import { STATUS_FILTERS, EMPTY_STATUS_MESSAGE, countPostsByStatus, parseStatusFilter, postStatusGroup, type PostStatusFilter } from "../lib/postStatusFilter"
import { usePostsSearchStore } from "../stores/postsSearchStore"
import { compactScheduleSummary, matchesPost, postKind, recurringInProgress, scheduleLines } from "../components/posts/postPresentation"

// Somente group_id explícito identifica um envio multi-rede.
// Texto, produto e timestamp iguais nunca unem posts independentes, nem
// mesmo nos registros antigos sem group_id.
function groupPosts(posts: Post[]): Map<number, { key: number; size: number }> {
  const byId = new Map<string, Post[]>()
  for (const post of posts) {
    if (!post.group_id) continue
    const group = byId.get(post.group_id) ?? []
    group.push(post)
    byId.set(post.group_id, group)
  }
  const result = new Map<number, { key: number; size: number }>()
  for (const group of byId.values()) {
    if (group.length < 2) continue
    const key = Math.min(...group.map((post) => post.id))
    for (const post of group) result.set(post.id, { key, size: group.length })
  }
  return result
}


const metaTextStyle = {
  font: "var(--fw-regular) var(--fs-caption)/1 var(--font-sans)",
  color: "var(--text-muted)",
}


type NetworkFilter = "all" | PostNetwork
const NETWORK_NAMES: Record<PostNetwork, string> = { threads: "Threads", x: "X", facebook: "Facebook", instagram: "Instagram", tiktok: "TikTok" }
const NETWORK_FILTERS: NetworkFilter[] = ["all", "threads", "x", "facebook", "instagram", "tiktok"]
const parseNetworkFilter = (value: unknown): NetworkFilter =>
  NETWORK_FILTERS.includes(value as NetworkFilter) ? (value as NetworkFilter) : "all"

const chipStyle = (active: boolean) => ({
  display: "inline-flex", alignItems: "center", gap: 6, minHeight: 36, padding: "0 14px", borderRadius: 999, cursor: "pointer",
  font: "var(--fw-semibold) var(--fs-caption)/1 var(--font-sans)",
  border: `1px solid ${active ? "var(--brand-electric-cyan, #1FD3FD)" : "var(--border-hairline)"}`,
  background: active ? "rgba(31, 211, 253, .14)" : "var(--surface-inset)",
  color: active ? "var(--text-body)" : "var(--text-muted)",
})

// Destaque lateral dos posts que pedem ação (erro ou sem confirmação).
const ATTENTION_ACCENT: Partial<Record<string, string>> = {
  failed: "inset 3px 0 0 var(--negative, #f87171)",
  unknown: "inset 3px 0 0 var(--warning, #fbbf24)",
}

function countPostsByNetwork(posts: Post[]): Record<PostNetwork, number> {
  const counts: Record<PostNetwork, number> = { threads: 0, x: 0, facebook: 0, instagram: 0, tiktok: 0 }
  for (const post of posts) counts[post.network ?? "threads"] += 1
  return counts
}

export function PostsPage() {
  const { logout } = useAuthStore()
  const queryClient = useQueryClient()
  const activeProfileId = useProfileStore((state) => state.activeProfileId)
  const [detailsPost, setDetailsPost] = useState<Post | null>(null)
  const [historyPage, setHistoryPage] = useState(1)
  const searchQuery = usePostsSearchStore((state) => state.query)
  const clearSearch = usePostsSearchStore((state) => state.clear)
  const setSearchQuery = usePostsSearchStore((state) => state.setQuery)
  const accountId = useAuthStore((state) => state.user?.id)
  useAutosavedDraft(formDraftKey(accountId, "posts-search", activeProfileId), { query: searchQuery }, (saved) => {
    setSearchQuery(typeof saved?.query === "string" ? saved.query : "")
  })
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)
  const [confirmPost, setConfirmPost] = useState<Post | null>(null)
  const [retryPost, setRetryPost] = useState<Post | null>(null)

  // Filtros ficam na URL (?status=&rede=): dá para compartilhar e voltar sem perder.
  const urlSearch = useSearch({ strict: false }) as Record<string, unknown>
  const statusFilter = parseStatusFilter(urlSearch.status)
  const networkFilter = parseNetworkFilter(urlSearch.rede)
  const setFilters = (next: { status?: PostStatusFilter; rede?: NetworkFilter }) => {
    const status = next.status ?? statusFilter
    const rede = next.rede ?? networkFilter
    void router.navigate({
      to: "/posts",
      search: { ...(status !== "all" ? { status } : {}), ...(rede !== "all" ? { rede } : {}) },
      replace: true,
    })
  }
  const setStatusFilter = (status: PostStatusFilter) => setFilters({ status })
  const setNetworkFilter = (rede: NetworkFilter) => setFilters({ rede })
  const hasStatusFilter = statusFilter !== "all"

  const allPostsQuery = useInfiniteQuery({
    queryKey: ["posts", activeProfileId],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => postsApi.list({ cursor: pageParam, limit: POSTS_FETCH_LIMIT }),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    refetchInterval: (query) => postsRefreshInterval(query.state.data?.pages?.flatMap((page) => page.data) ?? []),
  })
  // Com filtro de status, o SERVIDOR filtra (o status vem da fila, não de uma coluna).
  const statusPostsQuery = useInfiniteQuery({
    queryKey: ["posts", activeProfileId, "status", statusFilter],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => postsApi.list({ cursor: pageParam, limit: POSTS_FETCH_LIMIT, status: statusFilter }),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    enabled: hasStatusFilter,
    refetchInterval: (query) => postsRefreshInterval(query.state.data?.pages?.flatMap((page) => page.data) ?? []),
  })
  const activeQuery = hasStatusFilter ? statusPostsQuery : allPostsQuery
  const { hasNextPage, fetchNextPage, isFetchingNextPage } = activeQuery
  const postsLoadError = activeQuery.isError
  const isLoading = allPostsQuery.isLoading || (hasStatusFilter && statusPostsQuery.isLoading)
  const hiddenPostIds = useHiddenIds("posts")
  const visibleOnly = (pages?: { data: Post[] }[]) =>
    (pages?.flatMap((page) => page.data) ?? []).filter((post) => !hiddenPostIds.has(String(post.id)))
  const allPosts = visibleOnly(allPostsQuery.data?.pages)
  const posts = hasStatusFilter ? visibleOnly(statusPostsQuery.data?.pages) : allPosts
  const hasActiveSearch = searchQuery.trim().length > 0
  const hasNetworkFilter = networkFilter !== "all"
  const hasActiveFilter = hasActiveSearch || hasNetworkFilter || hasStatusFilter
  const searchedPosts = hasActiveSearch ? posts.filter((post) => matchesPost(post, searchQuery)) : posts
  const visiblePosts = hasNetworkFilter ? searchedPosts.filter((post) => (post.network ?? "threads") === networkFilter) : searchedPosts
  // Contadores sobre o histórico já carregado; "+" quando há posts antigos ainda não lidos.
  const networkCounts = countPostsByNetwork(allPosts)
  const statusCounts = countPostsByStatus(hasNetworkFilter ? allPosts.filter((post) => (post.network ?? "threads") === networkFilter) : allPosts)
  const countSuffix = allPostsQuery.hasNextPage ? "+" : ""
  const pagination = paginatePostHistory(visiblePosts, historyPage)
  const canNextHistoryPage = !postsLoadError && canAdvancePostHistory(
    pagination.page, pagination.loadedPages, !!hasNextPage, hasActiveFilter,
  )

  useEffect(() => setHistoryPage(1), [searchQuery, activeProfileId, networkFilter, statusFilter])

  const goToNextHistoryPage = () => {
    if (pagination.page < pagination.loadedPages) {
      setHistoryPage(pagination.page + 1)
    } else if (!hasActiveFilter && hasNextPage && !isFetchingNextPage && !postsLoadError) {
      void fetchNextPage().then((result) => {
        const nextPostCount = result.data?.pages.reduce((count, page) => count + page.data.length, 0) ?? posts.length
        if (nextPostCount > pagination.page * POSTS_PER_PAGE) setHistoryPage(pagination.page + 1)
      })
    }
  }
  useEffect(() => {
    if ((searchQuery.trim() || networkFilter !== "all" || statusFilter !== "all") && hasNextPage && !isFetchingNextPage && !postsLoadError) void fetchNextPage()
  }, [searchQuery, networkFilter, statusFilter, hasNextPage, isFetchingNextPage, postsLoadError, fetchNextPage, posts.length])

  const onAuthError = useCallback(
    (err: Error) => {
      if (err.message.includes("401") || err.message === "Não autenticado") {
        logout()
        router.navigate({ to: "/login" })
      }
    },
    [logout],
  )

  const onDecisionDone = () => {
    queryClient.invalidateQueries({ queryKey: ["posts"] })
    refreshPublishResult()
    setConfirmPost(null)
    setRetryPost(null)
  }

  // Exclusão com "Desfazer": o post some na hora e só é apagado no servidor após 7 s.
  const deleteMutation = {
    isPending: false,
    mutate: (id: number) => {
      setDeleteConfirm(null)
      scheduleUndoableDelete({
        kind: "posts",
        id,
        message: "Post removido",
        errorMessage: "Não foi possível remover o post",
        run: (keepalive) => postsApi.delete(id, keepalive),
        onSettled: () => queryClient.invalidateQueries({ queryKey: ["posts"] }),
      })
    },
  }

  // A publicação roda no scheduler depois do 200: recarrega a lista
  // algumas vezes pra mostrar o resultado real (last_result).
  const refreshPublishResult = () => {
    for (const ms of [5000, 15000, 40000]) {
      setTimeout(() => queryClient.invalidateQueries({ queryKey: ["posts"] }), ms)
    }
  }

  const publishMutation = useMutation({
    mutationFn: (id: number) => postsApi.publishNow(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["posts"] })
      refreshPublishResult()
    },
    onError: onAuthError,
  })

  if (isLoading) {
    return (
      <PageSkeleton variant="table" titleWidth="140px" subtitleWidth="280px" action toolbar columns={3} />
    )
  }

  // Grupo multi-rede vem do histórico completo carregado (o filtro de status pode esconder irmãos).
  const knownPosts = [...new Map([...allPosts, ...posts].map((post) => [post.id, post])).values()]
  const groups = groupPosts(knownPosts)
  const networksByGroup = new Map<number, PostNetwork[]>()
  for (const item of knownPosts) {
    const key = groups.get(item.id)?.key
    if (key == null) continue
    const networks = networksByGroup.get(key) ?? []
    const network = item.network ?? "threads"
    if (!networks.includes(network)) networks.push(network)
    networksByGroup.set(key, networks)
  }
  const detailsGroupKey = detailsPost ? groups.get(detailsPost.id)?.key : undefined
  const detailGroupNetworks: PostNetwork[] = detailsPost
    ? [...new Set(knownPosts.filter((p) => detailsGroupKey != null ? groups.get(p.id)?.key === detailsGroupKey : p.id === detailsPost.id).map((p) => p.network ?? "threads"))]
    : []

  return (
    <div className="csp-s-0314">
      <div
        className="posts-page-header"
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <div>
          <h1 className="csp-s-0315">Posts</h1>
          <p className="csp-s-0316">
            Consulte o histórico, os resultados e os detalhes de cada publicação.
          </p>
        </div>
      </div>

      {allPosts.length > 0 && (
        <div role="group" aria-label="Filtrar posts por rede social" className="posts-network-filter" style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {NETWORK_FILTERS.filter((key) => key === "all" || networkCounts[key] > 0 || key === networkFilter).map((key) => {
            const active = networkFilter === key
            const count = key === "all" ? allPosts.length : networkCounts[key]
            return (
              <button key={key} type="button" aria-pressed={active} onClick={() => setNetworkFilter(key)} className="ao-lift" style={chipStyle(active)}>
                {key !== "all" && <NetworkLogo network={key} size={16} />}
                {key === "all" ? "Todas as redes" : NETWORK_NAMES[key]}
                <span style={{ opacity: 0.7 }}>{count}{countSuffix}</span>
              </button>
            )
          })}
        </div>
      )}
      {allPosts.length > 0 && (
        <div role="group" aria-label="Filtrar posts por status" className="posts-status-filter" style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {STATUS_FILTERS.filter(({ key }) => key === "all" || key === "attention" || statusCounts[key] > 0 || key === statusFilter).map(({ key, label }) => {
            const active = statusFilter === key
            const alert = key === "attention" && statusCounts.attention > 0
            return (
              <button key={key} type="button" aria-pressed={active} onClick={() => setStatusFilter(key)} className="ao-lift"
                style={{ ...chipStyle(active), ...(alert && !active ? { borderColor: "var(--warning, #fbbf24)", color: "var(--text-body)" } : {}) }}>
                {label}
                <span style={{ opacity: 0.7 }}>{statusCounts[key]}{countSuffix}</span>
              </button>
            )
          })}
        </div>
      )}
      {postsLoadError && <p role="alert" style={{ color: "var(--negative)" }}>Não foi possível carregar o histórico.</p>}
      {hasActiveFilter && (
        <p role="status" style={{ color: "var(--text-muted)", display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          {visiblePosts.length} resultado(s){hasNetworkFilter ? ` em ${NETWORK_NAMES[networkFilter as PostNetwork]}` : ""}{hasStatusFilter ? ` · ${STATUS_FILTERS.find(({ key }) => key === statusFilter)?.label}` : ""}. {hasNextPage ? "Pesquisando também em posts antigos..." : "Histórico consultado."}
          {hasActiveSearch && <Button variant="ghost" size="sm" onClick={clearSearch}>Limpar busca</Button>}
          {hasNetworkFilter && <Button variant="ghost" size="sm" onClick={() => setNetworkFilter("all")}>Limpar filtro de rede</Button>}
          {hasStatusFilter && <Button variant="ghost" size="sm" onClick={() => setStatusFilter("all")}>Limpar filtro de status</Button>}
        </p>
      )}
      {!searchQuery.trim() && allPosts.length === 0 && !allPostsQuery.hasNextPage ? (
        <Panel surface="dark">
          <div className="csp-s-0317">
            Nenhum post criado.
          </div>
        </Panel>
      ) : (
        <Panel surface="dark" className="posts-list-panel">
          <PanelHeader title="Posts" />
          {visiblePosts.length === 0 && !searchQuery.trim() && (
            <p role="status" style={{ padding: "0 16px 16px", color: "var(--text-muted)" }}>
              {hasNextPage || isFetchingNextPage ? "Procurando em publicações anteriores..." : EMPTY_STATUS_MESSAGE[statusFilter]}
            </p>
          )}
          {pagination.items.map((post, index) => (
            <div key={post.id}>
              {index > 0 && <Divider />}
              <div
                className="post-list-item"
                role="button"
                tabIndex={0}
                aria-label="Visualizar detalhes da publicação"
                onClick={() => setDetailsPost(post)}
                onKeyDown={(event) => {
                  if (event.target === event.currentTarget && (event.key === "Enter" || event.key === " ")) {
                    event.preventDefault()
                    setDetailsPost(post)
                  }
                }}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "space-between",
                  gap: 16,
                  padding: "10px 16px",
                  cursor: "pointer",
                  boxShadow: ATTENTION_ACCENT[postStatusGroup(post)],
                }}
              >
                <div className="post-list-content" style={{ minWidth: 0, flex: 1 }}>
                  <span className="post-list-id" aria-label={`ID do post: ${post.id}`} style={{ display: "inline-block", font: "var(--text-role-caption)", color: "var(--text-muted)", marginBottom: 4 }}>#{post.id}</span>
                  <p
                    id={`post-text-${post.id}`}
                    className="post-list-copy"
                    title={post.texts?.[0] || post.text}
                    style={{
                      margin: 0,
                      font: "var(--text-role-body)",
                      color: "var(--text-body)",
                      overflow: "hidden",
                      whiteSpace: "nowrap",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {post.texts?.[0] || post.text}
                  </p>
                  <div className="post-list-meta" style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 7, flexWrap: "wrap" }}>
                    {post.products.length > 0 && (
                      <span
                        className="csp-named-meta"
                        title={post.products.map((product) => product.name).join(" · ")}
                        style={{ maxWidth: 340, minWidth: 0, overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis" }}
                      >
                        {post.products[0].name}{post.products.length > 1 ? ` +${post.products.length - 1}` : ""}
                      </span>
                    )}
                    {(groups.has(post.id) ? networksByGroup.get(groups.get(post.id)!.key) ?? [post.network ?? "threads"] : [post.network ?? "threads"]).map((network) => (
                      <Badge tone="outline" key={network}>
                        <span className="csp-s-0318">
                          <NetworkLogo network={network} size={12} />
                          {NETWORK_RULES[network].label}
                        </span>
                      </Badge>
                    ))}
                    <Badge tone="outline">{postKind(post)}</Badge>
                    {recurringInProgress(post) && (
                      <StatusBadge tone="info" icon="refresh-cw">Em andamento</StatusBadge>
                    )}
                    {post.last_result?.status === "retry_pending" && (
                      <StatusBadge tone="info" icon="clock">Reenvio na fila</StatusBadge>
                    )}
                    {post.last_result?.status === "running" && (
                      <StatusBadge tone="info" icon="loader-2">Em execução</StatusBadge>
                    )}
                    {post.last_result?.status === "unknown" && (
                      <StatusBadge tone={post.last_result?.partial_failure ? "negative" : "warning"} icon="alert-triangle">{post.last_result?.partial_failure ? "Falha parcial" : "Sem confirmação"}</StatusBadge>
                    )}
                    {post.last_result?.status === "published" && (
                      <StatusBadge tone="positive" icon="check-circle-2">Publicado</StatusBadge>
                    )}
                    {post.last_result?.status === "manual_confirmed" && (
                      <StatusBadge tone="manual" icon="shield-check">Confirmado por você</StatusBadge>
                    )}
                    {post.last_result?.status === "reported_removed" && (
                      <StatusBadge tone="manual" icon="shield-check">Relatado como publicado e removido</StatusBadge>
                    )}
                    {post.last_result?.status === "failed" && (
                      <StatusBadge tone="negative" icon="x-circle">{post.last_result.manual_not_published ? "Não publicado (conferido)" : "Falhou"}</StatusBadge>
                    )}
                  </div>
                  <div
                    className="post-list-timestamps"
                    style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: "4px 14px", marginTop: 6, font: "var(--fw-regular) var(--fs-caption)/1.4 var(--font-sans)", color: "var(--text-muted)" }}
                  >
                    <span>Criado: {formatUtcTimestamp(post.created_at).replace(/:\d{2}$/, "")}</span>
                    {post.last_published_at && <span>Última publicação: {formatUtcTimestamp(post.last_published_at).replace(/:\d{2}$/, "")}</span>}
                    {post.last_result?.at && <span>Última execução: {formatUtcTimestamp(post.last_result.at).replace(/:\d{2}$/, "")}</span>}
                    {compactScheduleSummary(post) && (
                      <span title={scheduleLines(post).join(" · ")}>{compactScheduleSummary(post)}</span>
                    )}
                    {!!post.parts_count && post.parts_count > 1 && (
                      <span>{post.parts_count} partes</span>
                    )}
                  </div>
                  {publishMutation.isError && publishMutation.variables === post.id && (
                    <p style={{ ...metaTextStyle, color: "var(--negative)", marginTop: 8 }}>
                      {publishMutation.error.message}
                    </p>
                  )}
                </div>
                <div className="post-list-actions" style={{ display: "flex", alignItems: "center", gap: 4, flex: "0 0 auto" }}>
                  {post.last_result?.status === "unknown" && post.publication_origin !== "campaign" && (
                    <Button variant="ghost" size="sm" icon="shield-check" onClick={(e) => {
                      e.stopPropagation()
                      setConfirmPost(post)
                    }}>
                      Conferir post
                    </Button>
                  )}
                  {post.last_result?.status === "failed" && post.last_result.job_id && post.publication_origin !== "campaign" && (
                    <Button variant="ghost" size="sm" icon="refresh-cw" onClick={(e) => {
                      e.stopPropagation()
                      setRetryPost(post)
                    }}>
                      Reenviar
                    </Button>
                  )}
                  {post.scheduled && post.last_result?.status !== "unknown" &&
                    post.last_result?.status !== "reported_removed" &&
                    post.last_result?.status !== "running" &&
                    (post.schedule_trigger === "cron" || !post.last_result?.status) && (
                    <IconButton
                      icon="send"
                      label="Publicar agora"
                      tone="plain"
                      size={32}
                      className={
                        publishMutation.isPending && publishMutation.variables === post.id ? "animate-spin" : ""
                      }
                      onClick={(e) => {
                        e.stopPropagation()
                        if (publishMutation.isPending) return
                        publishMutation.mutate(post.id)
                      }}
                    />
                  )}
                  <IconButton
                    icon="trash-2"
                    label="Remover post"
                    tone="plain"
                    size={32}
                    onClick={(e) => {
                      e.stopPropagation()
                      setDeleteConfirm(post.id)
                    }}
                  />
                </div>
              </div>
            </div>
          ))}
          {visiblePosts.length === 0 && searchQuery.trim() && <p style={{ padding: 16, color: "var(--text-muted)" }}>{hasNextPage ? "Procurando em publicações anteriores..." : "Nenhuma publicação corresponde à busca."}</p>}
          {visiblePosts.length > 0 && (
            <nav
              aria-label="Paginação do histórico de posts"
              style={{
                display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                borderTop: "1px solid rgba(255,255,255,.08)", padding: "4px 12px",
              }}
            >
              <Button variant="ghost" size="sm" icon="chevron-left" aria-label="Página anterior"
                title="Página anterior" disabled={pagination.page <= 1}
                onClick={() => setHistoryPage(pagination.page - 1)} />
              <span aria-live="polite" style={{ minWidth: 70, textAlign: "center", font: "var(--text-role-caption)", color: "var(--text-muted)" }}>
                Página {pagination.page}
              </span>
              <Button variant="ghost" size="sm" icon="chevron-right" aria-label="Próxima página"
                title="Próxima página" disabled={!canNextHistoryPage || isFetchingNextPage}
                onClick={goToNextHistoryPage} />
            </nav>
          )}
          {isFetchingNextPage && (
            <p role="status" style={{ padding: "0 16px 8px", margin: 0, textAlign: "center", color: "var(--text-muted)", font: "var(--text-role-caption)" }}>
              {hasActiveSearch ? "Consultando publicações anteriores..." : "Carregando página..."}
            </p>
          )}
        </Panel>
      )}

      {detailsPost && (
        <PostDetailsModal
          post={detailsPost}
          groupNetworks={detailGroupNetworks}
          onClose={() => setDetailsPost(null)}
        />
      )}

      {confirmPost && (
        <ConfirmPublicationModal post={confirmPost} onClose={() => setConfirmPost(null)} onDone={onDecisionDone} onAuthError={onAuthError} />
      )}
      {retryPost && (
        <RetryFailedModal post={retryPost} onClose={() => setRetryPost(null)} onDone={onDecisionDone} onAuthError={onAuthError} />
      )}

      <Modal open={deleteConfirm != null} onClose={() => setDeleteConfirm(null)} title="Confirmar remoção" width={400}>
        <p className="csp-s-0324">
          Tem certeza que deseja remover este post? Você terá alguns segundos para desfazer.
        </p>
        <div className="csp-s-0325">
          <Button variant="ghost" onClick={() => setDeleteConfirm(null)}>
            Cancelar
          </Button>
          <Button
            variant="send"
            disabled={deleteMutation.isPending}
            onClick={() => deleteConfirm != null && deleteMutation.mutate(deleteConfirm)}
          >
            {deleteMutation.isPending ? "Removendo..." : "Remover"}
          </Button>
        </div>
      </Modal>
    </div>
  )
}

