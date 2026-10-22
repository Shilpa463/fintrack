import pandas as pd
import streamlit as st
from supabase import create_client, Client
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
            email = email.strip().lower()
            if not email or "@" not in email:
                st.error("Please enter a valid email address.")
            elif len(password) < 8:
                st.error("Password must have at least 8 characters.")
            elif password != confirm_password:
                st.error("Passwords do not match.")
            else:
                try:
                    result = client.auth.sign_up(
                        {"email": email, "password": password}
                    )
                    if result.session:
                        st.session_state.user = {
                            "id": result.user.id,
                            "email": result.user.email,
                        }
                        st.session_state.supabase_session = result.session
                        st.rerun()
                    else:
                        st.success(
                            "Account created. Check your email to confirm your "
                            "account, then choose Login."
                        )
                except Exception as exc:
                    st.error(f"Could not create account: {exc}")

    else:
        st.subheader("Welcome back")
        with st.form("login_form"):
            email = st.text_input("Email address")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if not email.strip() or not password:
                st.error("Please enter your email and password.")
            else:
                try:
                    result = client.auth.sign_in_with_password(
                        {"email": email.strip().lower(), "password": password}
                    )
                    st.session_state.user = {
                        "id": result.user.id,
                        "email": result.user.email,
                    }
                    st.session_state.supabase_session = result.session
                    st.rerun()
                except Exception:
                    st.error(
                        "Login failed. Check your email and password. If you "
                        "just created an account, confirm your email first."
                    )


def fetch_expenses(client: Client, user_id: str):
    result = (
        client.table("expenses")
        .select("id, user_id, title, amount, category, date, created_at")
        .eq("user_id", user_id)
        .order("date", desc=True)
        .execute()
    )
    return result.data or []


def show_dashboard(client: Client):
    user = get_user()
    user_id = user["id"]

    st.title("💰 FinTrack Dashboard")
    left, right = st.columns([4, 1])
    with left:
        st.write(f"Welcome, **{user.get('email', 'FinTrack user')}**!")
        st.caption("Here is your personal financial overview.")
    with right:
        if st.button("Log out", use_container_width=True):
            clear_login()

    st.divider()
    with st.form("add_expense_form", clear_on_submit=True):
        st.subheader("➕ Add a new expense")
        title = st.text_input("Expense title", max_chars=100)
        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input(
                "Amount (₹)",
                min_value=0.01,
                max_value=100000000.0,
                value=100.0,
                step=10.0,
            )
            category = st.selectbox("Category", CATEGORIES)
        with col2:
            expense_date = st.date_input("Expense date", value=date.today())
        submitted = st.form_submit_button(
            "Add Expense", use_container_width=True
        )

    if submitted:
        if not title.strip():
            st.error("Please enter an expense title.")
        else:
            try:
                client.table("expenses").insert({
                    "user_id": user_id,
                    "title": title.strip(),
                    "amount": float(amount),
                    "category": category,
                    "date": expense_date.isoformat(),
                }).execute()
                st.success("Expense added successfully!")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not add expense: {exc}")

    st.divider()
    st.subheader("📊 Your Expenses")
    try:
        data = fetch_expenses(client, user_id)
    except Exception as exc:
        st.error(f"Unable to load expenses from Supabase: {exc}")
        st.info(
            "Check that the expenses table and its Row Level Security policies "
            "were created in Supabase."
        )
        return

    if not data:
        st.info("No expenses yet. Add your first expense above.")
        return

    df = pd.DataFrame(data)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    total = float(df["amount"].sum())
    month_key = pd.Timestamp.today().strftime("%Y-%m")
    this_month = float(
        df.loc[df["date"].dt.strftime("%Y-%m") == month_key, "amount"].sum()
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Spent", f"₹{total:,.2f}")
    col2.metric("Number of Expenses", len(df))
    col3.metric("This Month", f"₹{this_month:,.2f}")

    chart_col, list_col = st.columns([1, 2])
    with chart_col:
        st.subheader("Spending by Category")
        st.bar_chart(df.groupby("category")["amount"].sum())

    with list_col:
        st.subheader("All Expenses")
        display_df = df[["id", "title", "amount", "category", "date"]].copy()
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
        display_df["amount"] = display_df["amount"].map(
            lambda value: f"₹{value:,.2f}"
        )
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.subheader("🗑️ Delete an Expense")
    options = {
        f"#{row['id']} — {row['title']} (₹{float(row['amount']):,.2f})":
        row["id"]
        for row in data
    }
    with st.form("delete_expense_form"):
        selected = st.selectbox("Choose an expense to delete", list(options))
        confirm = st.checkbox(
            "I confirm that I want to delete this expense."
        )
        delete_submitted = st.form_submit_button("Delete Selected Expense")

    if delete_submitted:
        if not confirm:
            st.warning("Please confirm before deleting.")
        else:
            try:
                client.table("expenses").delete().eq(
                    "id", options[selected]
                ).eq("user_id", user_id).execute()
                st.success("Expense deleted successfully.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not delete expense: {exc}")


def main():
    st.sidebar.title("FinTrack")
    st.sidebar.caption("Personal expense tracker")

    try:
        client = get_supabase_client()
    except Exception:
        st.title("💰 FinTrack")
        st.error(
            "Supabase settings are missing or invalid. In Streamlit Community "
            "Cloud, open your app's Settings → Secrets and check that "
            "SUPABASE_URL and SUPABASE_KEY are set correctly."
        )
        st.code(
            'SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"\n'
            'SUPABASE_KEY = "YOUR-SUPABASE-PUBLISHABLE-KEY"',
            language="toml",
        )
        st.stop()

    if get_user():
        show_dashboard(client)
    else:
        show_auth_page(client)


if __name__ == "__main__":
    main()
