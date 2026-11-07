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
  disabled?: boolean
  scope: string
  /** Indica quando uma rede aparece apenas em parte dos produtos. */
  partial?: readonly PostNetwork[]
}

/** As nove redes cadastradas aparecem sempre; somente publicação ativa + OAuth testado habilitam seleção. */
export function CampaignNetworkCheckboxes({ selected, states, onToggle, disabled = false, scope, partial = [] }: Props) {
  return (
    <div className="campaign-network-options" role="group" aria-label="Redes sociais da campanha">
      {SOCIAL_CHANNELS.map(({ key, title, availability }) => {
        const supported = isPublishingNetwork(key)
        const state = supported ? states[key] : undefined
        const disabledByPlatform = supported ? isNetworkDisabled(key) : undefined
        const ready = availability === "active" && supported && !disabledByPlatform && state?.connected === true
        const checked = supported && selected.includes(key)
        const partlySelected = supported && partial.includes(key)
        const reason = availability === "planned" || !supported ? "Em breve"
          : disabledByPlatform ? "Indisponível"
          : state?.connected === undefined ? "Verificando conexão"
          : !state.connected ? "Não conectada" : "Conectada"
        // Uma seleção antiga pode perder o OAuth. Permitir apenas DESMARCAR,
        // jamais ativar novamente uma rede sem conexão válida.
        const inputDisabled = disabled || (!ready && !checked)
        return (
          <label key={key} className={`campaign-network-option${!ready || disabled ? " is-disabled" : ""}`}
            title={disabledByPlatform || (!ready ? state?.connectionReason || reason : undefined)}>
            <input type="checkbox" name={`${scope}-networks`} value={key}
              checked={checked} disabled={inputDisabled}
              onChange={(event) => {
                if (supported && (ready || !event.currentTarget.checked)) onToggle(key, event.currentTarget.checked)
              }} />
            <img src={`/brand-logos/${key === "shopee-video" ? "shopee" : key}.svg`}
              aria-hidden="true" alt="" loading="lazy" />
            <span className="campaign-network-option-content">
              <span>{title}</span>
              <small>{partlySelected ? "Em alguns produtos" : reason}</small>
            </span>
          </label>
        )
      })}
    </div>
  )
}
