-- F4E: cobrir FKs de slots e manifestos para consulta/expurgo por conta.
-- Tabelas vazias no primeiro deploy; nenhuma mudança de dados ou de quota.
BEGIN;
SET LOCAL lock_timeout = '5s';

CREATE INDEX campaign_network_slots_product_fk_f4e_idx
  ON public.campaign_network_slots_f4e(product_id);
CREATE INDEX campaign_network_slots_profile_fk_f4e_idx
  ON public.campaign_network_slots_f4e(profile_id);
CREATE INDEX campaign_reservation_assets_product_fk_f4e_idx
  ON public.campaign_reservation_assets_f4e(product_id);
CREATE INDEX campaign_reservation_assets_profile_fk_f4e_idx
  ON public.campaign_reservation_assets_f4e(profile_id);
CREATE INDEX campaign_reservation_assets_user_fk_f4e_idx
  ON public.campaign_reservation_assets_f4e(user_id);

COMMIT;
