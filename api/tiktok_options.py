"""Escolhas do usuário para publicar no TikTok (Content Sharing Guidelines).

Fonte única de validação para a API (criação de post, campanha) e para o
scheduler (momento do envio). Nada aqui chama a rede.

Regras oficiais (https://developers.tiktok.com/doc/content-sharing-guidelines,
consultadas em 17/11/2026):
- privacidade escolhida manualmente entre `privacy_level_options` do
  creator_info, sem valor padrão;
- Permitir comentários/Duet/Stitch desmarcados por padrão (desmarcado =
  não permitir, ou seja, `disable_* = true`); desabilitados quando o
  creator_info indicar;
- divulgação de conteúdo comercial desligada por padrão; ligada exige
  "Sua marca" (`brand_organic_toggle`) e/ou "Conteúdo de marca"
  (`brand_content_toggle`); conteúdo de marca não pode ser `SELF_ONLY`;
- nada é enviado sem consentimento expresso do usuário.

Modo "draft" usa o endpoint de rascunho (inbox, escopo video.upload): o
usuário finaliza privacidade, divulgação e legenda no app do TikTok, então
essas escolhas não existem aqui.
"""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

PRIVACY_LEVELS = (
    "PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR", "SELF_ONLY",
)
PrivacyLevel = Literal[PRIVACY_LEVELS]

RECONFIRM_MESSAGE = (
    "Reconfirme as opções do TikTok (privacidade, interações e divulgação "
    "comercial) antes de publicar. Nada foi enviado ao TikTok."
)
BRANDED_PRIVATE_MESSAGE = "A visibilidade de conteúdo de marca não pode ser privada."
COMMERCIAL_REQUIRED_MESSAGE = (
    "Você precisa indicar se o conteúdo promove você, um terceiro ou ambos."
)


class TikTokPostOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["direct", "draft"]
    privacy_level: PrivacyLevel | None = None
    allow_comment: bool = False
    allow_duet: bool = False
    allow_stitch: bool = False
    commercial_content: bool = False
    brand_organic: bool = False  # "Sua marca" -> rótulo "Promotional content"
    brand_content: bool = False  # "Conteúdo de marca" -> rótulo "Paid partnership"
    is_aigc: bool = False
    consent: bool = False
    # Gravado pelo servidor ao salvar (stored_options); o cliente não decide.
    confirmed_at: str | None = None

    @model_validator(mode="after")
    def _guideline_rules(self):
        if self.consent is not True:
            raise ValueError("Confirme a declaração do TikTok antes de publicar ou agendar.")
        if self.mode == "draft":
            if (self.privacy_level or self.allow_comment or self.allow_duet or self.allow_stitch
                    or self.commercial_content or self.brand_organic or self.brand_content
                    or self.is_aigc):
                raise ValueError(
                    "No envio para rascunhos, privacidade, interações e divulgação "
                    "são definidas pelo próprio usuário no app do TikTok."
                )
            return self
        if not self.privacy_level:
            raise ValueError("Escolha quem pode ver o vídeo no TikTok.")
        if self.commercial_content and not (self.brand_organic or self.brand_content):
            raise ValueError(COMMERCIAL_REQUIRED_MESSAGE)
        if not self.commercial_content and (self.brand_organic or self.brand_content):
            raise ValueError("Ative 'Divulgar conteúdo comercial' para marcar Sua marca ou Conteúdo de marca.")
        if self.brand_content and self.privacy_level == "SELF_ONLY":
            raise ValueError(BRANDED_PRIVATE_MESSAGE)
        return self


def stored_options(options: TikTokPostOptions) -> dict:
    """JSON gravado no post: a escolha exata e quando o usuário a confirmou."""
    return {**options.model_dump(), "confirmed_at": datetime.now(timezone.utc).isoformat()}


def require_campaign_choices(items) -> None:
    """Cada item de campanha com TikTok precisa das escolhas explícitas."""
    for item in items:
        networks = item.get("networks") if isinstance(item, dict) else item.networks
        if "tiktok" not in (networks or []):
            continue
        raw = item.get("tiktok") if isinstance(item, dict) else item.tiktok
        parse_stored(raw.model_dump() if isinstance(raw, BaseModel) else raw)


def parse_stored(raw) -> TikTokPostOptions:
    """Lê o JSON gravado; ausente ou inválido nunca vira valor inventado."""
    if not isinstance(raw, dict):
        raise ValueError(RECONFIRM_MESSAGE)
    try:
        return TikTokPostOptions.model_validate(raw)
    except ValidationError:
        raise ValueError(RECONFIRM_MESSAGE) from None


def check_against_creator(options: TikTokPostOptions, creator: dict) -> None:
    """Confere a escolha com o creator_info atual (ValueError em português)."""
    if options.mode != "direct":
        return
    allowed = creator.get("privacy_level_options") or []
    if options.privacy_level not in allowed:
        raise ValueError(
            "A privacidade escolhida não está disponível para esta conta TikTok agora. "
            "Reabra as opções do TikTok e escolha novamente."
        )
    for allow, flag, label in (
        (options.allow_comment, "comment_disabled", "comentários"),
        (options.allow_duet, "duet_disabled", "Duet"),
        (options.allow_stitch, "stitch_disabled", "Stitch"),
    ):
        if allow and creator.get(flag):
            raise ValueError(f"A conta TikTok desativou {label} nas configurações do app.")


def direct_post_info(options: TikTokPostOptions, title: str, creator: dict) -> dict:
    """post_info do /v2/post/publish/video/init/ com exatamente o que o usuário
    escolheu; uma interação que o criador desligou depois segue desligada."""
    return {
        "title": title or "",
        "privacy_level": options.privacy_level,
        "disable_comment": not options.allow_comment or bool(creator.get("comment_disabled")),
        "disable_duet": not options.allow_duet or bool(creator.get("duet_disabled")),
        "disable_stitch": not options.allow_stitch or bool(creator.get("stitch_disabled")),
        "brand_content_toggle": options.brand_content,
        "brand_organic_toggle": options.brand_organic,
        "is_aigc": options.is_aigc,
    }
