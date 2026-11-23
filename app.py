from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from src.auth import login, logout, restore_session

load_dotenv()
st.set_page_config(
    page_title="Rice Ethanol Intelligence",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {padding-top:1.1rem;padding-bottom:2rem;max-width:1500px;}
      [data-testid="stMetric"] {background:var(--secondary-background-color);border:1px solid rgba(128,128,128,.18);padding:12px 14px;border-radius:12px;}
      [data-testid="stSidebar"] {border-right:1px solid rgba(128,128,128,.15);}
      @media(max-width:640px) {
        .block-container {padding-left:.75rem;padding-right:.75rem;}
        [data-testid="stMetric"] {padding:8px;}
        [data-testid="stMetricValue"] {font-size:1.2rem;}
        h1 {font-size:1.55rem !important;}
        h2 {font-size:1.3rem !important;}
      }
    </style>
    """,
    unsafe_allow_html=True,
)

FINANCE_CATEGORIES = {
    "Ethanol sales": "ethanol_sales",
    "Byproduct sales": "byproduct_sales",
    "Feedstock cost": "feedstock_cost",
    "Utilities cost": "utilities_cost",
    "Labor cost": "labor_cost",
    "Maintenance cost": "maintenance_cost",
    "Other cost": "other_cost",
}


def show_login() -> None:
    st.markdown("<div style='max-width:520px;margin:5vh auto 0;'>", unsafe_allow_html=True)
    st.caption("PLANT OPERATIONS PLATFORM")
    st.title("🏭 Rice Ethanol Intelligence")
    st.write("Sign in to enter daily plant data or review performance.")
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="name@company.com")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
    if submitted:
        if not email.strip() or not password:
            st.error("Enter both email and password.")
        else:
            try:
                client, auth_data = login(email, password)
                st.session_state["supabase"] = client
                st.session_state["auth"] = auth_data
                st.rerun()
            except Exception as exc:
                st.error(f"Unable to sign in: {exc}")
    st.markdown("</div>", unsafe_allow_html=True)
    st.caption("Access is provisioned by your organization administrator.")


def require_login() -> None:
    if not st.session_state.get("auth"):
        show_login()
        st.stop()
    if "supabase" not in st.session_state and not restore_session():
        show_login()
        st.stop()



def get_profile_context(client, profile: dict) -> tuple[list[dict], dict, str]:
    # Fetch organization name using the authenticated user's organization ID
    org_response = (
        client.table("organizations")
        .select("organization_id, organization_name")
        .eq("organization_id", profile["organization_id"])
        .single()
        .execute()
    )

    organization_name = org_response.data["organization_name"]

    # Fetch plants belonging to this organization
    response = (
        client.table("plants")
        .select("plant_id, plant_name, capacity_klpd, timezone")
        .eq("organization_id", profile["organization_id"])
        .order("plant_name")
        .execute()
    )

    plants = response.data or []

    if profile["role"] not in {"management", "admin"}:
        plants = [
            p for p in plants
            if p["plant_id"] == profile.get("plant_id")
        ]

    if not plants:
        raise RuntimeError(
            "No plant is assigned or visible to this account. "
            "Contact your administrator."
        )

    if profile["role"] in {"management", "admin"}:
        selected_name = st.session_state.get("selected_plant_name")
        selected = next(
            (p for p in plants if p["plant_name"] == selected_name),
            plants[0]
        )

        names = [p["plant_name"] for p in plants]
        chosen = st.sidebar.selectbox(
            "Plant",
            names,
            index=names.index(selected["plant_name"])
        )

        st.session_state["selected_plant_name"] = chosen
        selected = next(p for p in plants if p["plant_name"] == chosen)

    else:
        selected = plants[0]

    return plants, selected, organization_name


def fetch_rows(client, table: str, date_col: str, plant_id: str) -> pd.DataFrame:
    rows: list[dict] = []
    page_size, offset = 1000, 0
    while True:
        result = (
            client.table(table)
            .select("*")
            .eq("plant_id", plant_id)
            .order(date_col)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = result.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame[date_col] = pd.to_datetime(frame[date_col], errors="coerce")
    return frame


def clean_display_data(frame: pd.DataFrame) -> pd.DataFrame:
    """Remove internal identifiers from customer-facing tables."""
    if frame.empty:
        return frame

    internal_columns = [
        "organization_id",
        "plant_id",
        "production_id",
        "inventory_id",
        "finance_id",
    ]

    return frame.drop(
        columns=[
            col for col in internal_columns
            if col in frame.columns
        ],
        errors="ignore"
    )

def safe_number(value: float, label: str) -> float:
    number = float(value)
    if number < 0:
        raise ValueError(f"{label} cannot be negative.")
    return number


def render_production_form(client, profile: dict, plant: dict) -> None:
    st.subheader("Daily production entry")
    st.caption("Submit one production summary per plant per operating date. Saving again for the same date updates that day's record.")
    with st.form("production_entry", clear_on_submit=False):
        operating_date = st.date_input("Operating date", value=date.today(), key="prod_date")
        mode_label = st.selectbox("Process mode", ["Continuous", "Batch", "Hybrid"])
        a, b, c = st.columns(3)
        capacity = a.number_input("Plant capacity (KLPD)", min_value=0.0, value=float(plant["capacity_klpd"]), step=1.0)
        target = b.number_input("Ethanol target (KL)", min_value=0.0, value=95.0, step=1.0)
        ethanol = c.number_input("Ethanol produced (KL)", min_value=0.0, step=0.1, format="%.3f")
        a, b = st.columns(2)
        rice = a.number_input("Rice consumed (MT)", min_value=0.0, step=0.1, format="%.3f")
        maize = b.number_input("Maize consumed (MT)", min_value=0.0, step=0.1, format="%.3f")
        a, b, c = st.columns(3)
        ddgs = a.number_input("DDGS produced (MT)", min_value=0.0, step=0.1, format="%.3f")
        co2 = b.number_input("CO₂ produced (MT)", min_value=0.0, step=0.1, format="%.3f")
        electricity = c.number_input("Electricity (kWh)", min_value=0.0, step=100.0)
        a, b = st.columns(2)
        steam = a.number_input("Steam (MT)", min_value=0.0, step=1.0)
        water = b.number_input("Water (m³)", min_value=0.0, step=10.0)
        submitted = st.form_submit_button("Save production record", type="primary", use_container_width=True)
    if submitted:
        if capacity <= 0:
            st.error("Plant capacity must be greater than zero.")
            return
        payload = {
            "organization_id": profile["organization_id"],
            "plant_id": plant["plant_id"],
            "operating_date": operating_date.isoformat(),
            "process_mode": mode_label.lower(),
            "capacity_klpd": safe_number(capacity, "Capacity"),
            "target_kl": safe_number(target, "Target"),
            "ethanol_kl": safe_number(ethanol, "Ethanol produced"),
            "rice_mt": safe_number(rice, "Rice consumed"),
            "maize_mt": safe_number(maize, "Maize consumed"),
            "ddgs_mt": safe_number(ddgs, "DDGS produced"),
            "co2_mt": safe_number(co2, "CO₂ produced"),
            "electricity_kwh": safe_number(electricity, "Electricity"),
            "steam_mt": safe_number(steam, "Steam"),
            "water_m3": safe_number(water, "Water"),
        }
        try:
            client.table("daily_production").upsert(payload, on_conflict="plant_id,operating_date").execute()
            st.success("Production record saved. The dashboard will use the updated value on refresh.")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not save production record: {exc}")


def render_inventory_form(client, profile: dict, plant: dict) -> None:
    st.subheader("Daily inventory entry")
    st.caption("One material balance per plant, date and material. Saving the same combination updates the existing balance.")
    with st.form("inventory_entry", clear_on_submit=False):
        operating_date = st.date_input("Inventory date", value=date.today(), key="inv_date")
        material = st.text_input("Material", placeholder="e.g. Broken rice, maize, ethanol")
        uom = st.selectbox("Unit of measure", ["MT", "KL", "L", "m³", "kWh", "Nos"])
        a, b, c = st.columns(3)
        receipt = a.number_input("Receipt quantity", min_value=0.0, step=1.0, format="%.3f")
        consumed = b.number_input("Consumption quantity", min_value=0.0, step=1.0, format="%.3f")
        closing = c.number_input("Closing balance", min_value=0.0, step=1.0, format="%.3f")
        submitted = st.form_submit_button("Save inventory record", type="primary", use_container_width=True)
    if submitted:
        if not material.strip():
            st.error("Enter a material name.")
            return
        payload = {
            "organization_id": profile["organization_id"],
            "plant_id": plant["plant_id"],
            "operating_date": operating_date.isoformat(),
            "material": material.strip(),
            "uom": uom,
            "receipt_qty": safe_number(receipt, "Receipt quantity"),
            "consumption_qty": safe_number(consumed, "Consumption quantity"),
            "closing_qty": safe_number(closing, "Closing balance"),
        }
        try:
            client.table("daily_inventory").upsert(payload, on_conflict="plant_id,operating_date,material").execute()
            st.success("Inventory record saved.")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not save inventory record: {exc}")


def render_finance_form(client, profile: dict, plant: dict) -> None:
    st.subheader("Daily finance entry")
    st.caption("Each submission is stored as a separate financial transaction. Add a reference if you have a voucher or invoice number.")
    with st.form("finance_entry", clear_on_submit=False):
        entry_date = st.date_input("Transaction date", value=date.today(), key="fin_date")
        category_label = st.selectbox("Transaction category", list(FINANCE_CATEGORIES))
        amount = st.number_input("Amount (INR)", min_value=0.0, step=1000.0, format="%.2f")
        reference = st.text_input("Voucher / invoice reference (optional)")
        submitted = st.form_submit_button("Save finance transaction", type="primary", use_container_width=True)
    if submitted:
        if amount <= 0:
            st.error("Enter an amount greater than zero.")
            return
        payload = {
            "organization_id": profile["organization_id"],
            "plant_id": plant["plant_id"],
            "entry_date": entry_date.isoformat(),
            "category": FINANCE_CATEGORIES[category_label],
            "amount_inr": safe_number(amount, "Amount"),
            "source_system": "manual",
            "external_reference": reference.strip() or f"manual-{uuid4()}",
        }
        try:
            client.table("daily_finance").insert(payload).execute()
            st.success("Finance transaction saved.")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not save finance transaction: {exc}")


def render_data_entry(client, profile: dict, plant: dict) -> None:
    role = profile["role"]
    st.title("Daily plant data entry")
    st.caption(
        f"Organization: {st.session_state['organization_name']} "
        f"· Plant: {plant['plant_name']} "
        f"· Capacity: {plant['capacity_klpd']:g} KLPD"
    )
    if role in {"production", "management", "admin"}:
        prod_tab, inv_tab = st.tabs(["Production", "Inventory"])
        with prod_tab:
            render_production_form(client, profile, plant)
        with inv_tab:
            render_inventory_form(client, profile, plant)
    if role in {"accounts", "management", "admin"}:
        render_finance_form(client, profile, plant)
    st.info("Records are saved directly to the Supabase cloud database. The dashboard reads the saved records when refreshed.")


def render_dashboard(client, profile: dict, plant: dict) -> None:
    role = profile["role"]
    st.title("🏭 Rice Ethanol Intelligence")

    st.markdown(
        f"**Organization:** {st.session_state['organization_name']}  "
        f"| **Plant:** {plant['plant_name']}  "
        f"| **Capacity:** {plant['capacity_klpd']:g} KLPD"
    )

    st.caption("Live database-backed view")
    if st.button("Refresh dashboard data", use_container_width=False):
        st.rerun()
    try:
        production = pd.DataFrame()
        inventory = pd.DataFrame()
        finance = pd.DataFrame()
        if role in {"management", "production", "admin"}:
            production = fetch_rows(client, "daily_production", "operating_date", plant["plant_id"])
            inventory = fetch_rows(client, "daily_inventory", "operating_date", plant["plant_id"])
        if role in {"management", "accounts", "admin"}:
            finance = fetch_rows(client, "daily_finance", "entry_date", plant["plant_id"])
    except Exception as exc:
        st.error(f"Unable to load cloud data: {exc}")
        st.stop()

    # Remove internal IDs from customer-facing dashboard tables
    production = clean_display_data(production)
    inventory = clean_display_data(inventory)
    finance = clean_display_data(finance)

    dates = []
    for frame, col in ((production, "operating_date"), (inventory, "operating_date"), (finance, "entry_date")):
        if not frame.empty:
            dates.extend(frame[col].dropna().dt.date.tolist())
    if not dates:
        st.info("No records have been entered yet. Open Daily data entry to add the first operating-day records.")
        return

    default_start, default_end = min(dates), max(dates)
    date_range = st.date_input("Reporting period", value=(default_start, default_end), key="dashboard_range")
    if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
        st.info("Select a start date and end date.")
        return
    start, end = date_range
    if start > end:
        st.error("Start date must be before end date.")
        return
    p = production[(production.operating_date.dt.date >= start) & (production.operating_date.dt.date <= end)].copy() if not production.empty else production
    f = finance[(finance.entry_date.dt.date >= start) & (finance.entry_date.dt.date <= end)].copy() if not finance.empty else finance
    inv = inventory[inventory.operating_date.dt.date <= end].copy() if not inventory.empty else inventory

    if role in {"management", "admin"}:
        st.subheader("Management overview")
        ethanol = float(p["ethanol_kl"].sum()) if not p.empty else 0.0
        capacity = float(p["capacity_klpd"].sum()) if not p.empty else 0.0
        grain = float(p["rice_mt"].sum() + p["maize_mt"].sum()) if not p.empty else 0.0
        revenue = float(f.loc[f.category.isin(["ethanol_sales", "byproduct_sales"]), "amount_inr"].sum()) if not f.empty else 0.0
        cost = float(f.loc[~f.category.isin(["ethanol_sales", "byproduct_sales"]), "amount_inr"].sum()) if not f.empty else 0.0
        a, b, c, d = st.columns(4)
        a.metric("Ethanol produced", f"{ethanol:,.1f} KL")
        b.metric("Capacity utilization", f"{ethanol / capacity * 100:.1f}%" if capacity else "—")
        c.metric("Blended yield", f"{ethanol * 1000 / grain:.1f} L/MT" if grain else "—")
        d.metric("Net operating balance", f"₹{revenue - cost:,.0f}")

    if role == "production":
        st.subheader("Production overview")
        ethanol = float(p["ethanol_kl"].sum()) if not p.empty else 0.0
        capacity = float(p["capacity_klpd"].sum()) if not p.empty else 0.0
        grain = float(p["rice_mt"].sum() + p["maize_mt"].sum()) if not p.empty else 0.0
        a, b, c = st.columns(3)
        a.metric("Ethanol produced", f"{ethanol:,.1f} KL")
        b.metric("Capacity utilization", f"{ethanol / capacity * 100:.1f}%" if capacity else "—")
        c.metric("Blended yield", f"{ethanol * 1000 / grain:.1f} L/MT" if grain else "—")

    if role in {"management", "production", "admin"}:
        st.subheader("Production trends")
        if p.empty:
            st.info("No production records in this reporting period.")
        else:
            chart = p.melt(id_vars="operating_date", value_vars=["ethanol_kl", "target_kl"], var_name="Metric", value_name="KL")
            st.plotly_chart(px.line(chart, x="operating_date", y="KL", color="Metric", title="Ethanol output vs target"), use_container_width=True)
            left, right = st.columns(2)
            with left:
                st.plotly_chart(px.bar(p, x="operating_date", y=["rice_mt", "maize_mt"], title="Feedstock consumption (MT)"), use_container_width=True)
            with right:
                st.dataframe(p.sort_values("operating_date", ascending=False), use_container_width=True, hide_index=True)
        st.subheader("Latest inventory balances")
        if inv.empty:
            st.info("No inventory records available.")
        else:
            latest = inv.sort_values("operating_date").groupby("material").tail(1)
            st.dataframe(latest[["operating_date", "material", "closing_qty", "uom"]].sort_values("material"), use_container_width=True, hide_index=True)

    if role in {"management", "accounts", "admin"}:
        st.subheader("Financial overview")
        if f.empty:
            st.info("No finance records in this reporting period.")
        else:
            revenue = float(f.loc[f.category.isin(["ethanol_sales", "byproduct_sales"]), "amount_inr"].sum())
            costs = float(f.loc[~f.category.isin(["ethanol_sales", "byproduct_sales"]), "amount_inr"].sum())
            a, b, c = st.columns(3)
            a.metric("Revenue", f"₹{revenue:,.0f}")
            b.metric("Operating costs", f"₹{costs:,.0f}")
            c.metric("Net balance", f"₹{revenue - costs:,.0f}")
            st.plotly_chart(px.bar(f.groupby("category", as_index=False)["amount_inr"].sum(), x="category", y="amount_inr", title="Financial categories (INR)"), use_container_width=True)
            st.dataframe(f.sort_values("entry_date", ascending=False), use_container_width=True, hide_index=True)

    st.caption("Data is read directly from Supabase. Existing historical sample records are synthetic POC data.")


def main() -> None:
    require_login()
    auth = st.session_state["auth"]
    profile = auth["profile"]
    client = st.session_state["supabase"]
    st.sidebar.markdown("### Rice Ethanol Intelligence")
    st.sidebar.caption(f"{profile.get('display_name') or auth.get('email')} · {profile['role'].replace('_', ' ').title()}")
    if st.sidebar.button("Sign out", use_container_width=True):
        logout()
        st.rerun()
    try:
        _, plant, organization_name = get_profile_context(client, profile)
        st.session_state["organization_name"] = organization_name
    except Exception as exc:
        st.error(f"Unable to load assigned plant: {exc}")
        st.stop()
    allowed_pages = ["Dashboard"]
    if profile["role"] in {"production", "management", "accounts", "admin"}:
        allowed_pages.append("Daily data entry")
    page = st.sidebar.radio("Navigate", allowed_pages)
    if page == "Daily data entry":
        render_data_entry(client, profile, plant)
    else:
        render_dashboard(client, profile, plant)


if __name__ == "__main__":
    main()
