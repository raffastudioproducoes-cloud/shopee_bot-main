import type { PostNetwork } from "../../api/posts"
import { buildAdminDiagnosticSections } from "../../lib/credentialPlatforms"
import { isNetworkDisabled } from "../../lib/networkLimits"
import { PICKER_NETWORKS, type NetworkState } from "../posts/NetworkPicker"

const SOCIAL_CHANNELS = buildAdminDiagnosticSections().social

function isPublishingNetwork(key: string): key is PostNetwork {
  return PICKER_NETWORKS.includes(key as PostNetwork)
}

interface Props {
  selected: readonly PostNetwork[]
  states: Record<PostNetwork, NetworkState>
  onToggle: (network: PostNetwork, checked: boolean) => void
  scope: string
}

/** Seleção compacta por produto: 9 redes visíveis, apenas rede operacional e conectada é marcável. */
export function CampaignNetworkCheckboxes({ selected, states, onToggle, scope }: Props) {
  return (
    <div className="campaign-network-options" role="group" aria-label="Redes para este produto">
      {SOCIAL_CHANNELS.map(({ key, title, availability }) => {
        const supported = isPublishingNetwork(key)
        const state = supported ? states[key] : undefined
        const disabledByPlatform = supported ? isNetworkDisabled(key) : undefined
        const ready = availability === "active" && supported && !disabledByPlatform && state?.connected === true
        const checked = supported && selected.includes(key)
        const reason = availability === "planned" || !supported ? "Em breve"
          : disabledByPlatform ? "Indisponível"
          : state?.connected === undefined ? "Verificando conexão"
          : !state.connected ? "Não conectada" : "Conectada"
        // Uma seleção antiga pode perder o OAuth. Permitir apenas DESMARCAR,
        // jamais ativar novamente uma rede sem conexão válida.
        const inputDisabled = !ready && !checked
        return (
          <label key={key} className={`campaign-network-option${!ready ? " is-disabled" : ""}`}
            title={disabledByPlatform || (!ready ? state?.connectionReason || reason : undefined)}>
            <input type="checkbox" name={`${scope}-networks`} value={key}
              checked={checked} disabled={inputDisabled}
              aria-label={ready ? title : `${title} — ${reason}`}
              onChange={(event) => {
                if (supported && (ready || !event.currentTarget.checked)) onToggle(key, event.currentTarget.checked)
              }} />
            <span>{title}</span>
          </label>
        )
      })}
    </div>
  )
}
