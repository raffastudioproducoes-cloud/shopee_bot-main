import { INSTAGRAM_REELS_NOTE, type ReelsEligibility } from "../../lib/reelsOptions"
import "./tiktokPublishPanel.css"

type ReelsPublishPanelProps = {
  /** Instagram recebe um vídeo único (sempre Reels, travado). */
  instagram: boolean
  /** Facebook recebe um vídeo único: null = painel sem a linha do Facebook. */
  facebook: { eligibility: ReelsEligibility; checked: boolean; onChange: (value: boolean) => void } | null
}

/** Painel "Publicar como Reels" (modelo: TikTokPublishPanel). */
export function ReelsPublishPanel({ instagram, facebook }: ReelsPublishPanelProps) {
  return (
    <fieldset className="tiktok-panel" aria-label="Publicar como Reels">
      <legend>Publicar como Reels</legend>
      {instagram && (
        <div className="tiktok-panel__field">
          <label><input type="checkbox" checked disabled /> Instagram: Reels</label>
          <small>{INSTAGRAM_REELS_NOTE}</small>
        </div>
      )}
      {facebook && (
        <div className="tiktok-panel__field">
          <label>
            <input type="checkbox" checked={facebook.checked} disabled={!facebook.eligibility.allowed}
              onChange={(event) => facebook.onChange(event.target.checked)} />
            {" "}Facebook: publicar o vídeo como Reels
          </label>
          {facebook.eligibility.reason && <small role="status">{facebook.eligibility.reason}</small>}
          {facebook.checked && facebook.eligibility.warning && (
            <small role="status" className="tiktok-panel__error">{facebook.eligibility.warning}</small>
          )}
          {!facebook.checked && facebook.eligibility.allowed && !facebook.eligibility.reason && (
            <small>Desligado: sai como vídeo comum na Página.</small>
          )}
        </div>
      )}
    </fieldset>
  )
}
