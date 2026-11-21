-- Permanently designate and protect the original TutorInn First Admin.
ALTER TABLE public.user_accounts
    ADD COLUMN IF NOT EXISTS is_first_admin boolean NOT NULL DEFAULT false;

WITH first_existing_admin AS (
    SELECT id
    FROM public.user_accounts
    WHERE lower(role) = 'admin'
    ORDER BY id ASC
    LIMIT 1
)
UPDATE public.user_accounts AS accounts
SET is_first_admin = true
FROM first_existing_admin
WHERE accounts.id = first_existing_admin.id;

CREATE UNIQUE INDEX IF NOT EXISTS uq_user_accounts_first_admin
    ON public.user_accounts (is_first_admin)
    WHERE is_first_admin IS TRUE;

CREATE OR REPLACE FUNCTION public.tutorinn_protect_first_admin()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.is_first_admin IS TRUE THEN
        IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'The designated First Admin account cannot be deleted';
        END IF;
        IF NEW.is_first_admin IS NOT TRUE
           OR NEW.role <> 'admin'
           OR NEW.status <> 'active' THEN
            RAISE EXCEPTION 'The designated First Admin account cannot be demoted or disabled';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_protect_first_admin ON public.user_accounts;
CREATE TRIGGER trg_protect_first_admin
BEFORE UPDATE OF is_first_admin, role, status OR DELETE
ON public.user_accounts
FOR EACH ROW
EXECUTE FUNCTION public.tutorinn_protect_first_admin();

REVOKE ALL PRIVILEGES ON TABLE public.user_accounts FROM PUBLIC, anon, authenticated;
