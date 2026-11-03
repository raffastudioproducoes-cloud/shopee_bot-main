import { useMutation, useQueryClient, useInfiniteQuery } from "@tanstack/react-query"
import { useState, useCallback, useEffect } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import { postsApi, type Post, type PostNetwork } from "../api/posts"
import { formatUtcTimestampBrasilia } from "../lib/ptBrDateTime"
import { NETWORK_RULES } from "../lib/networkLimits"
import { NetworkLogo } from "../components/posts/NetworkPicker"
import { useProfileStore } from "../stores/profileStore"
import { formDraftKey } from "../lib/formDraftStorage"
import { useAutosavedDraft } from "../hooks/useAutosavedDraft"
import { Panel, PanelHeader, Divider } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { IconButton } from "../components/ui/IconButton"
import { Badge } from "../components/ui/Badge"
import { StatusBadge } from "../components/ui/StatusBadge"
import { Modal } from "../components/ui/Modal"
import { TextInput } from "../components/ui/TextInput"
import { PageSkeleton } from "../components/ui/Skeleton"
import { PostDetailsModal } from "../components/posts/PostDetailsModal"
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


export function PostsPage() {
  const { logout } = useAuthStore()
  const queryClient = useQueryClient()
  const activeProfileId = useProfileStore((state) => state.activeProfileId)
  const [detailsPost, setDetailsPost] = useState<Post | null>(null)
  const searchQuery = usePostsSearchStore((state) => state.query)
  const clearSearch = usePostsSearchStore((state) => state.clear)
  const setSearchQuery = usePostsSearchStore((state) => state.setQuery)
  const accountId = useAuthStore((state) => state.user?.id)
  useAutosavedDraft(formDraftKey(accountId, "posts-search", activeProfileId), { query: searchQuery }, (saved) => {
    setSearchQuery(typeof saved?.query === "string" ? saved.query : "")
  })
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)
  const [reconcilePostId, setReconcilePostId] = useState<number | null>(null)
  const [reconcileSourceJobId, setReconcileSourceJobId] = useState<string | null>(null)
  const [notPublishedOnThreads, setNotPublishedOnThreads] = useState(false)
  const [evidenceUrl, setEvidenceUrl] = useState("")
  const [confirmedOnThreads, setConfirmedOnThreads] = useState(false)
  const [reportedRemoved, setReportedRemoved] = useState(false)

  const { data: postsPages, isLoading, isError: postsLoadError, hasNextPage, fetchNextPage, isFetchingNextPage } = useInfiniteQuery({
    queryKey: ["posts", activeProfileId],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => postsApi.list({ cursor: pageParam, limit: 100 }),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    refetchInterval: (query) => query.state.data?.pages?.some((page) =>
      page.data.some((post) => post.scheduled && (
        post.schedule_trigger === "cron" ||
        !post.last_result?.status || post.last_result.status === "running" || post.last_result.status === "retry_pending"
      ))
    ) ? 30_000 : false,
  })
  const posts = postsPages?.pages.flatMap((page) => page.data) ?? []
  const visiblePosts = searchQuery.trim() ? posts.filter((post) => matchesPost(post, searchQuery)) : posts
  useEffect(() => {
    if (searchQuery.trim() && hasNextPage && !isFetchingNextPage && !postsLoadError) void fetchNextPage()
  }, [searchQuery, hasNextPage, isFetchingNextPage, postsLoadError, fetchNextPage, posts.length])

  const onAuthError = useCallback(
    (err: Error) => {
      if (err.message.includes("401") || err.message === "Não autenticado") {
        logout()
        router.navigate({ to: "/login" })
      }
    },
    [logout],
  )

  const reconcileMutation = useMutation({
    mutationFn: ({ id, url, removed }: { id: number; url: string; removed: boolean }) =>
      postsApi.reconcile(id, removed ? { reported_removed: true } : { permalink: url }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["posts"] })
      setReconcilePostId(null)
      setEvidenceUrl("")
      setConfirmedOnThreads(false)
      setReportedRemoved(false)
      setNotPublishedOnThreads(false)
      setReconcileSourceJobId(null)
    },
    onError: onAuthError,
  })

  const retryUnknownMutation = useMutation({
    mutationFn: ({ id, sourceJobId }: { id: number; sourceJobId: string }) =>
      postsApi.retryUnknown(id, sourceJobId),
    meta: { toast: { pending: "Registrando reenvio…", success: "Reenvio colocado na fila", error: "Não foi possível reenviar o post" } },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["posts"] })
      refreshPublishResult()
      setReconcilePostId(null)
      setReconcileSourceJobId(null)
      setNotPublishedOnThreads(false)
      setConfirmedOnThreads(false)
      setReportedRemoved(false)
      setEvidenceUrl("")
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => postsApi.delete(id),
    meta: { toast: { pending: "Removendo post…", success: "Post removido", error: "Não foi possível remover o post" } },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["posts"] })
      setDeleteConfirm(null)
    },
    onError: onAuthError,
  })

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

  const groups = groupPosts(posts)
  const networksByGroup = new Map<number, PostNetwork[]>()
  for (const item of posts) {
    const key = groups.get(item.id)?.key
    if (key == null) continue
    const networks = networksByGroup.get(key) ?? []
    const network = item.network ?? "threads"
    if (!networks.includes(network)) networks.push(network)
    networksByGroup.set(key, networks)
  }
  const detailsGroupKey = detailsPost ? groups.get(detailsPost.id)?.key : undefined
  const detailGroupNetworks: PostNetwork[] = detailsPost
    ? [...new Set(posts.filter((p) => detailsGroupKey != null ? groups.get(p.id)?.key === detailsGroupKey : p.id === detailsPost.id).map((p) => p.network ?? "threads"))]
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

      {postsLoadError && <p role="alert" style={{ color: "var(--negative)" }}>Não foi possível carregar o histórico.</p>}
      {searchQuery.trim() && (
        <p role="status" style={{ color: "var(--text-muted)", display: "flex", alignItems: "center", gap: 12 }}>
          {visiblePosts.length} resultado(s). {hasNextPage ? "Pesquisando também em posts antigos..." : "Histórico consultado."}
          <Button variant="ghost" size="sm" onClick={clearSearch}>Limpar busca</Button>
        </p>
      )}
      {!searchQuery.trim() && posts.length === 0 ? (
        <Panel surface="dark">
          <div className="csp-s-0317">
            Nenhum post criado.
          </div>
        </Panel>
      ) : (
        <Panel surface="dark" className="posts-list-panel">
          <PanelHeader title="Posts" />
          {visiblePosts.map((post, index) => (
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
                      <StatusBadge tone="negative" icon="x-circle">Falhou</StatusBadge>
                    )}
                  </div>
                  <div
                    className="post-list-timestamps"
                    style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: "4px 14px", marginTop: 6, font: "var(--fw-regular) var(--fs-caption)/1.4 var(--font-sans)", color: "var(--text-muted)" }}
                  >
                    <span>Criado: {formatUtcTimestampBrasilia(post.created_at).replace(/:\d{2}$/, "")}</span>
                    {post.last_published_at && <span>Última publicação: {formatUtcTimestampBrasilia(post.last_published_at).replace(/:\d{2}$/, "")}</span>}
                    {post.last_result?.at && <span>Última execução: {formatUtcTimestampBrasilia(post.last_result.at).replace(/:\d{2}$/, "")}</span>}
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
                  {post.last_result?.status === "unknown" && post.network === "threads" && (
                    <Button variant="ghost" size="sm" icon="shield-check" onClick={(e) => {
                      e.stopPropagation()
                      setReconcilePostId(post.id)
                      setReconcileSourceJobId(post.last_result?.job_id ?? null)
                      setNotPublishedOnThreads(false)
                      setEvidenceUrl("")
                      setConfirmedOnThreads(false)
                      setReportedRemoved(false)
                      reconcileMutation.reset()
                      retryUnknownMutation.reset()
                    }}>
                      Conferir post
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
          {hasNextPage && !searchQuery.trim() && (
            <div style={{ padding: 16, display: "flex", justifyContent: "center" }}>
              <Button variant="ghost" disabled={isFetchingNextPage} onClick={() => void fetchNextPage()}>
                {isFetchingNextPage ? "Carregando..." : "Carregar mais posts"}
              </Button>
            </div>
          )}
          {isFetchingNextPage && searchQuery.trim() && <p role="status" style={{ padding: 16 }}>Consultando publicações anteriores...</p>}
        </Panel>
      )}

      {detailsPost && (
        <PostDetailsModal
          post={detailsPost}
          groupNetworks={detailGroupNetworks}
          onClose={() => setDetailsPost(null)}
        />
      )}

      <Modal open={reconcilePostId != null} onClose={() => { if (!reconcileMutation.isPending && !retryUnknownMutation.isPending) setReconcilePostId(null) }} title="Conferir publicação no Threads" width={510}>
        <p className="csp-s-0319">
          O agendamento iniciou, mas o sistema não recebeu a confirmação. Antes de decidir, confira a conta correta no Threads.
        </p>
        <label className="csp-s-0320">
          <input type="checkbox" checked={reportedRemoved} disabled={reconcileMutation.isPending || retryUnknownMutation.isPending}
            onChange={(event) => {
              setReportedRemoved(event.target.checked)
              setNotPublishedOnThreads(false)
              setEvidenceUrl("")
              setConfirmedOnThreads(false)
            }} />
          A postagem apareceu no Threads, mas já foi removida e não tenho mais o link.
        </label>
        <label className="csp-s-0320">
          <input type="checkbox" checked={notPublishedOnThreads} disabled={reconcileMutation.isPending || retryUnknownMutation.isPending}
            onChange={(event) => {
              setNotPublishedOnThreads(event.target.checked)
              setReportedRemoved(false)
              setEvidenceUrl("")
              setConfirmedOnThreads(false)
            }} />
          Verifiquei que a postagem não apareceu no Threads e quero reenviá-la.
        </label>
        {!reportedRemoved && !notPublishedOnThreads && (
          <TextInput label="Link direto da publicação no Threads" type="url"
            placeholder="https://www.threads.net/@perfil/post/..."
            value={evidenceUrl} onChange={(event) => setEvidenceUrl(event.target.value)} />
        )}
        {notPublishedOnThreads && (
          <p className="csp-s-0322" role="alert">
            Atenção: não é possível comprovar automaticamente a ausência do post. Se ele já estiver publicado ou ainda em processamento, o reenvio pode criar uma duplicata. Será criada uma única nova tentativa, sem apagar o histórico anterior.
          </p>
        )}
        {notPublishedOnThreads && !reconcileSourceJobId && (
          <p className="csp-s-0322" role="alert">Não foi possível identificar a execução. Atualize a lista antes de reenviar.</p>
        )}
        <label className="csp-s-0321">
          <input type="checkbox" checked={confirmedOnThreads} disabled={reconcileMutation.isPending || retryUnknownMutation.isPending}
            onChange={(event) => setConfirmedOnThreads(event.target.checked)} />
          {notPublishedOnThreads
            ? "Conferi o perfil correto no Threads, não encontrei a postagem e assumo o risco de eventual duplicação."
            : reportedRemoved
              ? "Declaro que vi esta publicação no Threads antes de removê-la. Não tenho link ou prova verificável; isto será registrado somente como meu relato."
              : "Eu conferi no Threads que este post foi realmente publicado. Entendo que isto é uma confirmação manual."}
        </label>
        {reconcileMutation.isError && (
          <p role="alert" className="csp-s-0322">{reconcileMutation.error.message}</p>
        )}
        {retryUnknownMutation.isError && (
          <p role="alert" className="csp-s-0322">{retryUnknownMutation.error.message}</p>
        )}
        <div className="csp-s-0323">
          <Button variant="ghost" disabled={reconcileMutation.isPending || retryUnknownMutation.isPending}
            onClick={() => setReconcilePostId(null)}>Cancelar</Button>
          <Button variant="mint" loading={reconcileMutation.isPending || retryUnknownMutation.isPending}
            disabled={!confirmedOnThreads || (!notPublishedOnThreads && !reportedRemoved && !evidenceUrl.trim()) ||
              (notPublishedOnThreads && !reconcileSourceJobId)}
            onClick={() => {
              if (reconcilePostId == null) return
              if (notPublishedOnThreads) {
                if (reconcileSourceJobId) retryUnknownMutation.mutate({ id: reconcilePostId, sourceJobId: reconcileSourceJobId })
              } else {
                reconcileMutation.mutate({ id: reconcilePostId, url: evidenceUrl.trim(), removed: reportedRemoved })
              }
            }}>
            {notPublishedOnThreads ? "Reenviar post" : "Registrar confirmação"}
          </Button>
        </div>
      </Modal>

      <Modal open={deleteConfirm != null} onClose={() => setDeleteConfirm(null)} title="Confirmar remoção" width={400}>
        <p className="csp-s-0324">
          Tem certeza que deseja remover este post? Esta ação não pode ser desfeita.
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

