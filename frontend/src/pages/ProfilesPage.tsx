import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { profilesApi, type Profile, type ProfileInput } from "../api/profiles"
import { PROFILE_LIMIT, useActivateProfile, useProfiles } from "../hooks/useProfiles"
import { Panel } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { StatusMessage } from "../components/StatusMessage"
import { ProfileCard } from "../components/profiles/ProfileCard"
import { ProfileFormModal } from "../components/profiles/ProfileFormModal"
import { ConfirmModal } from "../components/profiles/ConfirmModal"
import { BackupSection } from "../components/profiles/BackupSection"
import { Skeleton, SkeletonAvatar, SkeletonText, SkeletonRegion } from "../components/ui/Skeleton"

const errMsg = (err: unknown, fallback: string) => (err instanceof Error && err.message ? err.message : fallback)

export function ProfilesPage() {
  const queryClient = useQueryClient()
  const [profileModalOpen, setProfileModalOpen] = useState(false)
  const [editingProfile, setEditingProfile] = useState<Profile | null>(null)
  const [deletingProfile, setDeletingProfile] = useState<Profile | null>(null)
  const [feedback, setFeedback] = useState<{ kind: "error" | "success"; text: string } | null>(null)

  const { profiles, activeProfile, isLoading: profilesLoading, isError: profilesError, refetch: refetchProfiles } = useProfiles()
  const atLimit = profiles.length >= PROFILE_LIMIT

  const invalidateProfiles = () => queryClient.invalidateQueries({ queryKey: ["profiles"] })

  const createProfileMutation = useMutation({
    mutationFn: profilesApi.create,
    onSuccess: () => {
      invalidateProfiles()
      setProfileModalOpen(false)
      setFeedback({ kind: "success", text: "Perfil criado." })
    },
  })

  const updateProfileMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: ProfileInput }) => profilesApi.update(id, data),
    onSuccess: () => {
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
      setFeedback({ kind: "success", text: "Perfil excluído." })
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
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap-column)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ font: "var(--text-role-hero)", color: "var(--text-display)", margin: 0 }}>Perfis</h1>
          <p style={{ color: "var(--text-muted)", marginTop: 4 }}>Perfis de uso da conta.</p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
          <Button
            variant="primary"
            icon="plus"
            disabled={atLimit}
            title={atLimit ? `Limite de ${PROFILE_LIMIT} perfis atingido` : undefined}
            onClick={() => {
              createProfileMutation.reset()
              setProfileModalOpen(true)
            }}
          >
            Novo perfil
          </Button>
          {atLimit && (
            <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
              Limite de {PROFILE_LIMIT} perfis atingido. Exclua um perfil secundário para criar outro.
            </span>
          )}
        </div>
      </div>

      {feedback && (
        <StatusMessage kind={feedback.kind} onDismiss={() => setFeedback(null)}>
          {feedback.text}
        </StatusMessage>
      )}

      {profilesLoading ? (
        <SkeletonRegion><div
          style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 16 }}
        >
          {[0, 1, 2].map((i) => (
            <Panel key={i} style={{ height: 240, padding: 16, display: "flex", flexDirection: "column", gap: 16 }}><SkeletonAvatar size={64} /><Skeleton width="70%" height={20} /><SkeletonText lines={2} /><Skeleton width="90px" height={36} /></Panel>
          ))}
        </div></SkeletonRegion>
      ) : profilesError ? (
        <Panel style={{ padding: 24, display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <p role="alert" style={{ margin: 0, color: "var(--negative-on-glass)" }}>
            Não foi possível carregar os perfis.
          </p>
          <Button variant="secondary" onClick={() => refetchProfiles()}>
            Tentar novamente
          </Button>
        </Panel>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 16 }}>
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
          Excluir o perfil <strong>{deletingProfile.nome}</strong>? Esta ação não pode ser desfeita.
        </ConfirmModal>
      )}

      <BackupSection />
    </div>
  )
}
