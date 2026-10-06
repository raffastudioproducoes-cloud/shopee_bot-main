import { useRef } from "react"
import type { Profile } from "../../api/profiles"
import { Panel } from "../ui/Panel"
import { Badge } from "../ui/Badge"
import { Button } from "../ui/Button"
import { IconButton } from "../ui/IconButton"
import { Avatar } from "./Avatar"

const planTierLabel: Record<Profile["plan_tier"], string> = { free: "Free", plus: "Plus", premium: "Premium" }
const planTierTone: Record<Profile["plan_tier"], "neutral" | "outline" | "mint"> = {
  free: "neutral",
  plus: "outline",
  premium: "mint",
}
const kindLabel: Record<Profile["kind"], string> = { principal: "Principal", secundario: "Secundário" }

interface ProfileCardProps {
  profile: Profile
  active: boolean
  activating: boolean
  onActivate: () => void
  onEdit: () => void
  onDelete: () => void
  onAvatarFile: (file: File) => void
}

/** Card sem controles aninhados: acao principal e secundarias sao irmas. */
export function ProfileCard({ profile, active, activating, onActivate, onEdit, onDelete, onAvatarFile }: ProfileCardProps) {
  const fileRef = useRef<HTMLInputElement>(null)
  const isPrincipal = profile.kind === "principal"

  return (
    <Panel
      surface={active ? "glass" : "dark"}
      style={{
        padding: 16,
        display: "flex",
        flexDirection: "column",
        gap: 8,
        outline: active ? "2px solid var(--mint-400)" : undefined,
        outlineOffset: -2,
      }}
    >
      <div style={{ position: "relative", width: 96 }}>
        <Avatar name={profile.nome} src={profile.avatar_url} size={96} radius="var(--r-lg)" />
        <input
          ref={fileRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          aria-label={`Escolher foto de ${profile.nome}`}
          tabIndex={-1}
          style={{ display: "none" }}
          onChange={(e) => {
            const file = e.target.files?.[0]
            e.target.value = ""
            if (file) onAvatarFile(file)
          }}
        />
        <IconButton
          icon="camera"
          label={`Alterar foto de ${profile.nome}`}
          tone="plain"
          size={44}
          style={{ position: "absolute", bottom: -8, right: -8, background: "var(--surface-inset)" }}
          onClick={() => fileRef.current?.click()}
        />
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 600 }}>
        {profile.nome}
        {active && <Badge tone="mint">Ativo</Badge>}
      </div>
      <div style={{ fontSize: 13, color: "var(--text-muted)", overflowWrap: "anywhere" }}>{profile.email}</div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <Badge tone={planTierTone[profile.plan_tier]}>{planTierLabel[profile.plan_tier]}</Badge>
        <Badge tone={isPrincipal ? "mint" : "neutral"}>{kindLabel[profile.kind]}</Badge>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: "auto", paddingTop: 8 }}>
        <Button
          variant={active ? "secondary" : "primary"}
          size="sm"
          icon={active ? "check-circle-2" : undefined}
          disabled={active}
          loading={activating}
          onClick={onActivate}
          style={{ flex: 1 }}
          title={active ? "Este perfil já está ativo" : undefined}
        >
          {active ? "Em uso" : "Ativar"}
        </Button>
        <IconButton icon="pencil" label={`Editar perfil ${profile.nome}`} tone="plain" size={44} onClick={onEdit} />
        {!isPrincipal && (
          <IconButton
            icon="trash-2"
            label={`Excluir perfil ${profile.nome}`}
            tone="plain"
            size={44}
            onClick={onDelete}
            style={{ color: "var(--red-300)" }}
          />
        )}
      </div>
    </Panel>
  )
}
