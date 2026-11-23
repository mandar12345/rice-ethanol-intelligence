# Rice Ethanol Intelligence — cloud-ready POC

A Streamlit prototype for a hypothetical 100 KLPD multi-grain ethanol plant. All bundled operational figures are synthetic and must not be treated as plant benchmarks.

## What is included

- Supabase email/password login (no hardcoded passwords).
- Role-aware views for Management, Production, Accounts and Admin.
- Supabase PostgreSQL schema with organization/plant structure and initial Row Level Security policies.
- Responsive Streamlit layout for desktop and mobile browsers.
- Synthetic 90-day CSV dashboard data for the initial demonstration.

**Important current boundary:** Authentication and profile/role lookup use Supabase. The dashboard's KPI data still comes from local bundled CSV files. The next integration phase is to import the synthetic records into `daily_production`, `daily_inventory` and `daily_finance`, then change the dashboard queries to Supabase. Do not use real plant financial or production data until that integration and access-control testing are complete.

## 1. Run locally in Windows CMD

```cmd
py -3.13 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` with the Supabase Project URL and publishable/anon key. Never put the `service_role` key in this file or in Streamlit.

Generate sample CSV data if needed:

```cmd
python src\generate_sample_data.py
```

Run:

```cmd
streamlit run app.py
```

## 2. Configure Supabase

1. Create a Supabase project.
2. Open SQL Editor and run `database/schema.sql`.
3. In Authentication > Users, create three users with email/password (one for each role). Use synthetic/test credentials only for the POC.
4. Run the organization and plant insert in `database/bootstrap_example.sql`, capture the returned UUIDs, and insert one `user_profiles` row per Auth user. Set `role` to `management`, `production` or `accounts`.
5. Copy the Project URL and publishable/anon key from Project Settings > API.

A login is accepted only if the matching `user_profiles` row exists and `is_active=true`. The login identifier is currently the user's email address; passwords are managed by Supabase Auth. Do not share one account among multiple people.

## 3. Deploy to Streamlit Community Cloud

1. Create a **private** GitHub repository and push this project.
2. In Streamlit Community Cloud, create an app from that repository, branch and `app.py`.
3. In the app's Settings > Secrets, add:

```toml
SUPABASE_URL = "https://YOUR_PROJECT_ID.supabase.co"
SUPABASE_ANON_KEY = "YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY"
```

4. Deploy and test sign-in separately with each role.

## Security notes

- Never commit `.env`, `secrets.toml`, database passwords, or Supabase `service_role` keys.
- The app uses the Supabase publishable/anon key and the authenticated user's access token for profile lookup; RLS is enabled in the supplied schema.
- The supplied data tables have read-only policies at this stage. Add explicit write policies only after defining which roles may create, edit, approve and delete each type of record.
- Streamlit Community Cloud is suitable for a free POC, not a production SLA. Supabase free projects may pause after inactivity and have quotas/limits.
- This is a starting SaaS foundation, not a completed commercial multi-tenant security certification. Test tenant isolation and role boundaries before loading any real data.

## Next implementation phase

- Import sample CSV rows into Supabase tables.
- Read KPI and chart data from Supabase rather than local CSVs.
- Add controlled data-entry forms, audit events and approval workflows.
- Add password reset, account provisioning, session-expiry handling and tenant-isolation tests.
