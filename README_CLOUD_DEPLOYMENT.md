# Cloud deployment and daily entry release

## What this release adds
- Browser-based daily production, inventory and finance forms.
- Writes go to Supabase using the signed-in user's JWT; RLS controls access.
- Production role: production and inventory entry.
- Accounts role: finance entry.
- Management/admin: all three entry areas and management dashboard.
- Existing synthetic records remain in Supabase and appear in the dashboard.

## 1. Apply the write-policy migration
In Supabase Dashboard > SQL Editor, run `database/enable_daily_entry.sql` once.
This grants only SELECT/INSERT/UPDATE on the three daily tables to authenticated users, with role/organization/plant checks in RLS. It does not grant DELETE.

## 2. Test locally (optional)
The app uses only `SUPABASE_URL` and `SUPABASE_ANON_KEY` for normal user operations. It does not need the service-role/secret key.

## 3. Deploy without keeping your PC online
1. Create a GitHub repository. Keep it private while this is a customer POC.
2. Upload the project files to the repository root. Do not upload `.env`, `.venv`, `__pycache__`, or any service-role/secret key.
3. Open https://share.streamlit.io and connect GitHub.
4. Create app, select repository and branch, set main file to `app.py`.
5. In Advanced settings > Secrets, enter:

```toml
SUPABASE_URL = "https://YOUR_PROJECT_ID.supabase.co"
SUPABASE_ANON_KEY = "YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY"
```

6. Deploy. Once deployed, the Streamlit app runs in the cloud. Your computer can be shut down; customers access the app URL from desktop or mobile browsers.
7. Sign in using each test account and verify that only the correct entry forms and data are visible.

## 4. Important POC limitations
- This is a functional POC, not a production-certified ERP. Validate units, business rules, approvals, audit trail, backup/restore, retention, and tenant isolation before real operational or audited financial data is entered.
- Streamlit Community Cloud is a convenient POC host, not a guaranteed production SLA. It currently hosts apps in the US; the Supabase database remains in the Mumbai region. Review latency, data residency, support, and commercial requirements before production rollout.
- The app's data-entry pages support direct insert/update; no delete workflow is exposed.
- Finance entries are separate transactions. A unique reference is generated when a voucher/invoice reference is not supplied.
- Existing imported CSV records are synthetic. Do not interpret them as actual plant data.
