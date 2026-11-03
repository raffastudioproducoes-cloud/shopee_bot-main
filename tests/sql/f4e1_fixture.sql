-- Somente banco PostgreSQL descartavel da CI, sem dados de clientes.
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN BYPASSRLS;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon,authenticated,service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO anon,authenticated,service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO anon,authenticated,service_role;

CREATE TABLE public.users(id uuid PRIMARY KEY, access text NOT NULL, plan_tier text NOT NULL);
CREATE TABLE public.profiles(id uuid PRIMARY KEY,user_id uuid NOT NULL REFERENCES public.users(id));
CREATE TABLE public.plan_limits(tier text PRIMARY KEY,active_campaigns_per_profile int,campaign_days int,campaign_posts_per_day int);
CREATE TABLE public.product_lists(id integer PRIMARY KEY,user_id uuid NOT NULL REFERENCES public.users(id),profile_id uuid NOT NULL REFERENCES public.profiles(id));
INSERT INTO public.plan_limits VALUES ('free',0,0,0),('pro',2,15,3),('premium',5,30,15);
GRANT USAGE ON SCHEMA public TO service_role,anon,authenticated;
GRANT SELECT,UPDATE ON public.users TO service_role;
GRANT SELECT ON public.profiles,public.product_lists,public.plan_limits TO service_role;
