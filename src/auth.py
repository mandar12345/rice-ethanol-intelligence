"""Supabase email/password authentication for the Streamlit POC."""
from __future__ import annotations
import os
import streamlit as st
from supabase import Client, create_client


def _setting(name: str) -> str | None:
    try:
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name)


def get_supabase_client() -> Client:
    url = _setting("SUPABASE_URL")
    key = _setting("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError(
            "Supabase is not configured. Add SUPABASE_URL and SUPABASE_ANON_KEY "
            "to .env locally or Streamlit app Secrets in the cloud."
        )
    return create_client(url, key)


def _profile_for_user(client: Client, user_id: str) -> dict:
    result = (
        client.table("user_profiles")
        .select("user_id, display_name, role, organization_id, plant_id, is_active")
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    profile = result.data
    if not profile:
        raise RuntimeError(
            "Your login is valid, but no user profile is assigned. Ask the POC administrator to configure user_profiles."
        )
    if not profile.get("is_active", False):
        raise RuntimeError("This account is inactive. Contact the POC administrator.")
    if profile.get("role") not in {"management", "production", "accounts", "admin"}:
        raise RuntimeError("Your account has an invalid role. Contact the POC administrator.")
    return profile


def login(email: str, password: str) -> tuple[Client, dict]:
    client = get_supabase_client()
    auth_response = client.auth.sign_in_with_password({"email": email.strip(), "password": password})
    if not auth_response.user:
        raise RuntimeError("Login failed. Check your email and password.")
    profile = _profile_for_user(client, auth_response.user.id)
    return client, {
        "user_id": auth_response.user.id,
        "email": auth_response.user.email,
        "access_token": auth_response.session.access_token if auth_response.session else None,
        "refresh_token": auth_response.session.refresh_token if auth_response.session else None,
        "profile": profile,
    }


def restore_session() -> bool:
    """Rebuild the Supabase client and restore the user's RLS token after reruns."""
    auth = st.session_state.get("auth")
    if not auth or not auth.get("access_token"):
        return False
    try:
        client = get_supabase_client()
        # Refresh token is stored only in Streamlit server-side session state.
        refresh_token = auth.get("refresh_token")
        if refresh_token:
            client.auth.set_session(auth["access_token"], refresh_token)
        else:
            client.postgrest.auth(auth["access_token"])
        st.session_state["supabase"] = client
        return True
    except Exception:
        st.session_state.pop("auth", None)
        st.session_state.pop("supabase", None)
        return False


def logout() -> None:
    client = st.session_state.get("supabase")
    if client:
        try:
            client.auth.sign_out()
        except Exception:
            pass
    for key in ("auth", "supabase"):
        st.session_state.pop(key, None)
