-- Apply once in Supabase SQL Editor after the initial schema is installed.
-- Enables authenticated, role-scoped INSERT/UPDATE for daily customer entry.
-- No DELETE permission is granted by this migration.

GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.daily_production TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.daily_inventory TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.daily_finance TO authenticated;

-- Production: production, management and admin can create/update production rows.
DROP POLICY IF EXISTS production_insert_role ON public.daily_production;
CREATE POLICY production_insert_role
ON public.daily_production FOR INSERT TO authenticated
WITH CHECK (
    organization_id = public.current_org_id()
    AND public.current_user_role() IN ('admin', 'management', 'production')
    AND (
        public.current_user_role() IN ('admin', 'management')
        OR (public.current_plant_id() IS NOT NULL AND plant_id = public.current_plant_id())
    )
);

DROP POLICY IF EXISTS production_update_role ON public.daily_production;
CREATE POLICY production_update_role
ON public.daily_production FOR UPDATE TO authenticated
USING (
    organization_id = public.current_org_id()
    AND public.current_user_role() IN ('admin', 'management', 'production')
    AND (
        public.current_user_role() IN ('admin', 'management')
        OR (public.current_plant_id() IS NOT NULL AND plant_id = public.current_plant_id())
    )
)
WITH CHECK (
    organization_id = public.current_org_id()
    AND public.current_user_role() IN ('admin', 'management', 'production')
    AND (
        public.current_user_role() IN ('admin', 'management')
        OR (public.current_plant_id() IS NOT NULL AND plant_id = public.current_plant_id())
    )
);

-- Inventory: production, management and admin can create/update inventory rows.
DROP POLICY IF EXISTS inventory_insert_role ON public.daily_inventory;
CREATE POLICY inventory_insert_role
ON public.daily_inventory FOR INSERT TO authenticated
WITH CHECK (
    organization_id = public.current_org_id()
    AND public.current_user_role() IN ('admin', 'management', 'production')
    AND (
        public.current_user_role() IN ('admin', 'management')
        OR (public.current_plant_id() IS NOT NULL AND plant_id = public.current_plant_id())
    )
);

DROP POLICY IF EXISTS inventory_update_role ON public.daily_inventory;
CREATE POLICY inventory_update_role
ON public.daily_inventory FOR UPDATE TO authenticated
USING (
    organization_id = public.current_org_id()
    AND public.current_user_role() IN ('admin', 'management', 'production')
    AND (
        public.current_user_role() IN ('admin', 'management')
        OR (public.current_plant_id() IS NOT NULL AND plant_id = public.current_plant_id())
    )
)
WITH CHECK (
    organization_id = public.current_org_id()
    AND public.current_user_role() IN ('admin', 'management', 'production')
    AND (
        public.current_user_role() IN ('admin', 'management')
        OR (public.current_plant_id() IS NOT NULL AND plant_id = public.current_plant_id())
    )
);

-- Finance: accounts, management and admin can create/update finance rows.
DROP POLICY IF EXISTS finance_insert_role ON public.daily_finance;
CREATE POLICY finance_insert_role
ON public.daily_finance FOR INSERT TO authenticated
WITH CHECK (
    organization_id = public.current_org_id()
    AND public.current_user_role() IN ('admin', 'management', 'accounts')
    AND (
        public.current_user_role() IN ('admin', 'management')
        OR (public.current_plant_id() IS NOT NULL AND plant_id = public.current_plant_id())
    )
);

DROP POLICY IF EXISTS finance_update_role ON public.daily_finance;
CREATE POLICY finance_update_role
ON public.daily_finance FOR UPDATE TO authenticated
USING (
    organization_id = public.current_org_id()
    AND public.current_user_role() IN ('admin', 'management', 'accounts')
    AND (
        public.current_user_role() IN ('admin', 'management')
        OR (public.current_plant_id() IS NOT NULL AND plant_id = public.current_plant_id())
    )
)
WITH CHECK (
    organization_id = public.current_org_id()
    AND public.current_user_role() IN ('admin', 'management', 'accounts')
    AND (
        public.current_user_role() IN ('admin', 'management')
        OR (public.current_plant_id() IS NOT NULL AND plant_id = public.current_plant_id())
    )
);
