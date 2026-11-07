import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { useAuthStore } from "../stores/authStore"
import { formDraftKey, clearFormDraft } from "../lib/formDraftStorage"
import { profilesApi, type Profile, type ProfileInput } from "../api/profiles"
import { useActivateProfile, useProfiles } from "../hooks/useProfiles"
import { PlanBadge } from "../components/plans/PlanSummary"
import { ResourceQuotaBar } from "../components/plans/ProductQuotaBar"
import { usePlanUsage } from "../hooks/usePlanUsage"
import { router } from "../router"
import { AccountIdentityForm } from "../components/profiles/AccountIdentityForm"
import { Panel } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { StatusMessage } from "../components/StatusMessage"
import { ProfileCard } from "../components/profiles/ProfileCard"
import { ProfileFormModal } from "../components/profiles/ProfileFormModal"
import { ConfirmModal } from "../components/profiles/ConfirmModal"
import { Skeleton, SkeletonAvatar, SkeletonText, SkeletonRegion } from "../components/ui/Skeleton"

const errMsg = (err: unknown, fallback: string) => (err instanceof Error && err.message ? err.message : fallback)

export function ProfilesPage() {
  const queryClient = useQueryClient()
  const userId = useAuthStore((state) => state.user?.id)
  const planQuery = usePlanUsage()
  const [profileModalOpen, setProfileModalOpen] = useState(false)
  const [editingProfile, setEditingProfile] = useState<Profile | null>(null)
  const [deletingProfile, setDeletingProfile] = useState<Profile | null>(null)
  const [feedback, setFeedback] = useState<{ kind: "error" | "success"; text: string } | null>(null)

  const { profiles, activeProfile, isLoading: profilesLoading, isError: profilesError, refetch: refetchProfiles } = useProfiles()
  const { data: quota, isLoading: quotaLoading, isError: quotaError, refetch: refetchQuota } = useQuery({
    queryKey: ["profiles", "quota", userId],
    queryFn: () => profilesApi.quota(),
  })
  const atLimit = !quota || (quota.limit !== null && quota.used >= quota.limit)
  const quotaMessage = quota?.limit === 1
    ? "O plano Free não permite perfis adicionais. Consulte as opções de plano abaixo; alteração ainda indisponível."
    : quota?.limit != null
      ? `Limite de ${quota.limit} perfis do plano atingido. A consulta e a exclusão dos perfis existentes continuam disponíveis.`
      : ""

  const invalidateProfiles = () => {
    void queryClient.invalidateQueries({ queryKey: ["profiles"] })
    void queryClient.invalidateQueries({ queryKey: ["plan-usage"] })
  }

  const createProfileMutation = useMutation({
    mutationFn: profilesApi.create,
    onSuccess: () => {
      clearFormDraft(formDraftKey(userId, "profile-create", null, false))
      invalidateProfiles()
      setProfileModalOpen(false)
      setFeedback({ kind: "success", text: "Perfil criado." })
    },
  })

  const updateProfileMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: ProfileInput }) => profilesApi.update(id, data),
    onSuccess: (_result, variables) => {
      clearFormDraft(formDraftKey(userId, `profile-edit:${variables.id}`, null, false))
      invalidateProfiles()
      setEditingProfile(null)
      setFeedback({ kind: "success", text: "Perfil atualizado." })
    },
  })

  const deleteProfileMutation = useMutation({
    mutationFn: (id: string) => profilesApi.delete(id),
    onSuccess: () => {
      invalidateProfiles()
      setDeletingProfile(null)
      setFeedback({ kind: "success", text: "Perfil removido da conta ativa. Histórico final preservado." })
    },
  })

  const activateMutation = useActivateProfile()

  const handleActivate = (profile: Profile) => {
    setFeedback(null)
    activateMutation.mutate(profile.id, {
      onSuccess: () => setFeedback({ kind: "success", text: `Perfil ${profile.nome} ativado.` }),
      onError: (err) => setFeedback({ kind: "error", text: errMsg(err, "Não foi possível ativar o perfil.") }),
    })
  }

  const uploadAvatarMutation = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => profilesApi.uploadAvatar(id, file),
    onSuccess: () => {
      invalidateProfiles()
      setFeedback({ kind: "success", text: "Foto atualizada." })
    },
    onError: (err) => setFeedback({ kind: "error", text: errMsg(err, "Não foi possível enviar a foto.") }),
  })

  return (
    <div className="csp-s-0372">
      <div className="csp-s-0373">
        <div>
          <h1 className="csp-s-0374">Perfis</h1>
          <p className="csp-s-0375">Perfis de uso da conta.</p>
        </div>
        <div className="csp-s-0376">
          <Button
            variant="primary"
            icon="plus"
            disabled={atLimit || quotaLoading || quotaError}
            title={atLimit && quota ? quotaMessage : quotaError ? "Não foi possível consultar a cota de perfis" : undefined}
            onClick={() => {
              createProfileMutation.reset()
              setProfileModalOpen(true)
            }}
          >
            Novo perfil
          </Button>
          {atLimit && quota && (
            <span className="csp-s-0377">{quotaMessage}</span>
          )}
          {quotaError && (
            <Button variant="secondary" onClick={() => refetchQuota()}>Consultar limite novamente</Button>
          )}
        </div>
      </div>

      <div className="profiles-compact-plan" style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <PlanBadge />
        <div style={{ flex: "1 1 320px", minWidth: 0 }}>
          <ResourceQuotaBar plan={planQuery.data} resource="profiles" loading={planQuery.isPending} error={planQuery.isError}
            onUpgrade={() => void router.navigate({ to: "/settings", hash: "planos" })} />
        </div>
      </div>

      <AccountIdentityForm />

      {feedback && (
        <StatusMessage kind={feedback.kind} onDismiss={() => setFeedback(null)}>
          {feedback.text}
        </StatusMessage>
      )}

      {profilesLoading ? (
        <SkeletonRegion><div
          className="profiles-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 16 }}
        >
          {[0, 1, 2].map((i) => (
            <Panel key={i} style={{ height: 240, padding: 16, display: "flex", flexDirection: "column", gap: 16 }}><SkeletonAvatar size={64} /><Skeleton width="70%" height={20} /><SkeletonText lines={2} /><Skeleton width="90px" height={36} /></Panel>
          ))}
        </div></SkeletonRegion>
      ) : profilesError ? (
        <Panel style={{ padding: 24, display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <p role="alert" className="csp-s-0378">
            Não foi possível carregar os perfis.
          </p>
          <Button variant="secondary" onClick={() => refetchProfiles()}>
            Tentar novamente
          </Button>
        </Panel>
      ) : (
        <div className="profiles-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 16 }}>
          {profiles.map((profile) => (
            <ProfileCard
              key={profile.id}
              profile={profile}
              active={profile.id === activeProfile?.id}
              activating={activateMutation.isPending && activateMutation.variables === profile.id}
              onActivate={() => handleActivate(profile)}
              onEdit={() => {
                updateProfileMutation.reset()
                setEditingProfile(profile)
              }}
              onDelete={() => {
                deleteProfileMutation.reset()
                setDeletingProfile(profile)
              }}
              onAvatarFile={(file) => uploadAvatarMutation.mutate({ id: profile.id, file })}
            />
          ))}
        </div>
      )}

      {profileModalOpen && (
        <ProfileFormModal
          onClose={() => setProfileModalOpen(false)}
          onSubmit={(data) => createProfileMutation.mutate(data)}
          loading={createProfileMutation.isPending}
          error={createProfileMutation.isError ? errMsg(createProfileMutation.error, "Não foi possível criar o perfil.") : null}
        />
      )}

      {editingProfile && (
        <ProfileFormModal
          profile={editingProfile}
          onClose={() => setEditingProfile(null)}
          onSubmit={(data) => updateProfileMutation.mutate({ id: editingProfile.id, data })}
          loading={updateProfileMutation.isPending}
          error={updateProfileMutation.isError ? errMsg(updateProfileMutation.error, "Não foi possível salvar o perfil.") : null}
        />
      )}

      {deletingProfile && (
        <ConfirmModal
          title="Excluir perfil"
          confirmLabel="Excluir"
          busyLabel="Excluindo..."
          loading={deleteProfileMutation.isPending}
          error={deleteProfileMutation.isError ? errMsg(deleteProfileMutation.error, "Não foi possível excluir o perfil.") : null}
          onConfirm={() => deleteProfileMutation.mutate(deletingProfile.id)}
          onClose={() => setDeletingProfile(null)}
        >
          Remover o perfil <strong>{deletingProfile.nome}</strong>? Agendamentos e campanhas pendentes serão cancelados. Publicações já concluídas, falhas e resultados que exigem conciliação continuam no histórico da conta. Esta ação não pode ser desfeita.
        </ConfirmModal>
      )}

    </div>
  )
}
