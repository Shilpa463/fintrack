import pandas as pd
import streamlit as st
from supabase import create_client, Clien
from datetime import date

st.set_page_config(
    page_title="FinTrack",
    page_icon="💰",
    layout="wide",
)

CATEGORIES = [
    "Food", "Transport", "Bills",
    "Entertainment", "Utilities", "General",
]

# Configure these in Streamlit Community Cloud:
# App -> Settings -> Secrets
@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def clear_login():
    for key in ("supabase_session", "user", "access_token"):
        st.session_state.pop(key, None)
    st.rerun()


def get_user():
    return st.session_state.get("user")


def show_auth_page(client: Client):
    st.title("💰 FinTrack")
    st.caption("Your money. Your goals. Your control.")
    st.write("Sign in with your email address, or create a new account.")

    page = st.radio(
        "Choose an option",
        ["Login", "Create Account"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if page == "Create Account":
        st.subheader("Create your account")
        with st.form("register_form"):
            email = st.text_input("Email address")
            password = st.text_input("Password", type="password", max_chars=128)
            confirm_password = st.text_input(
                "Confirm password", type="password", max_chars=128
            )
            submitted = st.form_submit_button(
                "Create Account", use_container_width=True
            )

                if submitted:
            if not email.strip() or not password:
                st.error("Please enter your email and password.")
            else:
                try:
                    result = client.auth.sign_in_with_password(
                        {
                            "email": email.strip().lower(),
                            "password": password,
                        }
                    )
                    st.session_state.user = {
                        "id": result.user.id,
                        "email": result.user.email,
                    }
                    st.session_state.supabase_session = result.session
                    st.rerun()
                except Exception:
                    st.error(
                        "Login failed. Check your email and password. "
                        "Confirm your email first if required."
                    )
    else:
        st.subheader("Welcome back")
        with st.form("login_form"):
            email = st.text_input("Email address")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if not email.strip() or not password:
