import {
  BRANDED_CONTENT_POLICY_URL,
  DRAFT_NOTICE,
  MUSIC_USAGE_URL,
  PRIVACY_LABELS,
  PROCESSING_NOTICE,
  TIKTOK_TITLE_MAX,
  brandContentDisabledReason,
  commercialLabelNotice,
  declarationKind,
  interactionDisabled,
  privacyOptionDisabledReason,
  updateTikTokChoice,
  type TikTokChoice,
  type TikTokCreatorInfo,
  type TikTokPrivacy,
} from "../../lib/tiktokSharing"
import "./tiktokPublishPanel.css"

type TikTokPublishPanelProps = {
  choice: TikTokChoice
  onChange: (next: TikTokChoice) => void
  creator?: TikTokCreatorInfo
  isLoading: boolean
  errorMessage?: string | null
  onRetry: () => void
  /** Título/legenda editável enviado ao TikTok (Direct Post). */
  title?: { value: string; onChange: (value: string) => void }
  /** Prévia do vídeo que será enviado. */
  video?: { src: string; isPoster: boolean } | null
}

/** Painel "Publicar no TikTok" exigido pelas Content Sharing Guidelines. */
export function TikTokPublishPanel({
  choice, onChange, creator, isLoading, errorMessage, onRetry, title, video,
}: TikTokPublishPanelProps) {
  const set = (patch: Partial<TikTokChoice>) => onChange(updateTikTokChoice(choice, patch))
  const direct = choice.mode === "direct"
  const labelNotice = commercialLabelNotice(choice)
  const brandedDisabled = brandContentDisabledReason(choice)
  const onlySelfPrivacy = creator?.privacy_level_options.length === 1 && creator.privacy_level_options[0] === "SELF_ONLY"

  return (
    <fieldset className="tiktok-panel" aria-label="Publicar no TikTok">
      <legend>TikTok</legend>

      <div className="tiktok-panel__account" role="status">
        {isLoading && <span>Consultando a conta TikTok…</span>}
        {errorMessage && <span className="tiktok-panel__error">{errorMessage}
          {" "}<button type="button" onClick={onRetry}>Tentar de novo</button></span>}
        {creator && <span>Publicando na conta <strong>{creator.creator_nickname || creator.creator_username}</strong>
          {creator.creator_username && creator.creator_nickname ? ` (@${creator.creator_username})` : ""}</span>}
        {creator && !creator.can_post && <span className="tiktok-panel__error">
          {creator.cannot_post_reason ?? "Esta conta TikTok não pode publicar agora. Tente mais tarde."}</span>}
      </div>

      <div className="tiktok-panel__modes" role="radiogroup" aria-label="Como enviar ao TikTok">
        <label><input type="radio" name="tiktok-mode" checked={direct}
          onChange={() => set({ mode: "direct" })} /> Publicar direto no perfil</label>
        <label><input type="radio" name="tiktok-mode" checked={!direct}
          onChange={() => set({ mode: "draft" })} /> Enviar para rascunhos do TikTok</label>
      </div>

      {video && <div className="tiktok-panel__preview">
        {video.isPoster
          ? <img src={video.src} alt="Prévia do vídeo que será enviado ao TikTok" />
          : <video src={video.src} controls muted playsInline aria-label="Prévia do vídeo que será enviado ao TikTok" />}
      </div>}

      {direct && title && <label className="tiktok-panel__field">
        <span>Título / legenda do TikTok</span>
        <textarea value={title.value} maxLength={TIKTOK_TITLE_MAX} rows={3}
          onChange={(event) => title.onChange(event.target.value)} />
        <small>{title.value.length}/{TIKTOK_TITLE_MAX}</small>
      </label>}

      {direct ? <>
        <label className="tiktok-panel__field">
          <span>Quem pode ver este vídeo *</span>
          <select value={choice.privacy} required disabled={!creator}
            onChange={(event) => set({ privacy: event.target.value as TikTokPrivacy | "" })}>
            <option value="" disabled>Selecione</option>
            {(creator?.privacy_level_options ?? []).map((option) => {
              const reason = privacyOptionDisabledReason(choice, option)
              return <option key={option} value={option} disabled={Boolean(reason)} title={reason ?? undefined}>
                {PRIVACY_LABELS[option]}</option>
            })}
          </select>
          {onlySelfPrivacy && <small>Enquanto o app não for auditado pelo TikTok, a conta só permite publicar como “Somente eu”.</small>}
          {choice.commercial && choice.brandContent && <small>{privacyOptionDisabledReason(choice, "SELF_ONLY")}</small>}
        </label>

        <fieldset className="tiktok-panel__group">
          <legend>Permitir que os usuários</legend>
          {([["comment", "allowComment", "Comentem"], ["duet", "allowDuet", "Façam Duet"], ["stitch", "allowStitch", "Façam Stitch"]] as const)
            .map(([key, field, label]) => {
              const disabled = interactionDisabled(creator, key)
              return <label key={key} className={disabled ? "is-disabled" : undefined}
                title={disabled && creator ? "Desativado nas configurações da sua conta TikTok." : undefined}>
                <input type="checkbox" checked={choice[field] && !disabled} disabled={disabled}
                  onChange={(event) => set({ [field]: event.target.checked } as Partial<TikTokChoice>)} /> {label}
              </label>
            })}
        </fieldset>

        <fieldset className="tiktok-panel__group">
          <legend>Divulgação de conteúdo</legend>
          <label className="tiktok-panel__switch">
            <input type="checkbox" role="switch" checked={choice.commercial}
              onChange={(event) => set({ commercial: event.target.checked })} />
            Divulgar conteúdo comercial
          </label>
          <small>Ative se este vídeo promove você, uma marca, um produto ou serviço em troca de algo de valor (por exemplo, comissão de afiliado).</small>
          {choice.commercial && <>
            <label>
              <input type="checkbox" checked={choice.brandOrganic}
                onChange={(event) => set({ brandOrganic: event.target.checked })} /> Sua marca
              <small> Você promove a si mesmo ou o seu próprio negócio.</small>
            </label>
            <label className={brandedDisabled ? "is-disabled" : undefined} title={brandedDisabled ?? undefined}>
              <input type="checkbox" checked={choice.brandContent} disabled={Boolean(brandedDisabled)}
                onChange={(event) => set({ brandContent: event.target.checked })} /> Conteúdo de marca
              <small> Você promove outra marca ou terceiro (parceria paga).</small>
            </label>
            {brandedDisabled && <small>{brandedDisabled}</small>}
            {!choice.brandOrganic && !choice.brandContent &&
              <small role="status" className="tiktok-panel__error">Você precisa indicar se o seu conteúdo promove você, um terceiro ou ambos.</small>}
            {labelNotice && <small role="status">{labelNotice}</small>}
          </>}
        </fieldset>

        <label>
          <input type="checkbox" checked={choice.isAigc} onChange={(event) => set({ isAigc: event.target.checked })} />
          {" "}Conteúdo gerado por IA (o TikTok marcará o vídeo como gerado por IA)
        </label>
      </> : <p className="tiktok-panel__note">{DRAFT_NOTICE}</p>}
    </fieldset>
  )
}

/** Declaração e aviso exibidos logo antes do botão de enviar. */
export function TikTokDeclaration({ choice }: { choice: TikTokChoice }) {
  if (choice.mode === "draft") {
    return <p className="tiktok-declaration">Ao enviar, o vídeo vai para os rascunhos do seu app TikTok, onde você finaliza e publica.</p>
  }
  const music = <a href={MUSIC_USAGE_URL} target="_blank" rel="noopener noreferrer">Confirmação de Uso de Música</a>
  return (
    <div className="tiktok-declaration">
      {declarationKind(choice) === "branded"
        ? <p>Ao publicar, você concorda com a <a href={BRANDED_CONTENT_POLICY_URL} target="_blank" rel="noopener noreferrer">Política de Conteúdo de Marca</a> e a {music} do TikTok.</p>
        : <p>Ao publicar, você concorda com a {music} do TikTok.</p>}
      <p>{PROCESSING_NOTICE}</p>
    </div>
  )
}
