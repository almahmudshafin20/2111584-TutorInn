-- Recorded in the production migration ledger as fix_first_admin_delete_return.
-- Restored verbatim so repo history matches the ledger. Production's function body is this version.
CREATE OR REPLACE FUNCTION public.tutorinn_protect_first_admin()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    IF OLD.is_first_admin IS TRUE THEN
        IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION
                'The designated First Admin account cannot be deleted';
        END IF;

        IF NEW.is_first_admin IS NOT TRUE
           OR NEW.role <> 'admin'
           OR NEW.status <> 'active' THEN
            RAISE EXCEPTION
                'The designated First Admin account cannot be demoted or disabled';
        END IF;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;

    RETURN NEW;
END;
$function$;
