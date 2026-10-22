
import requests
import pandas as pd
import streamlit as st

API = "http://127.0.0.1:8000"
CATEGORIES = [
    "Food", "Transport", "Bills",
    "Entertainment", "Utilities", "General"
]

st.set_page_config(
    page_title="FinTrack",
    page_icon="💰",
    layout="wide"
)

if "token" not in st.session_state:
    st.session_state.token = None

if "username" not in st.session_state:
    st.session_state.username = None


def api_request(method, path, authenticated=False, **kwargs):
    headers = kwargs.pop("headers", {})

    if authenticated and st.session_state.token:
        headers["Authorization"] = (
            f"Bearer {st.session_state.token}"
        )

    try:
        return requests.request(
            method,
            f"{API}{path}",
            headers=headers,
            timeout=10,
            **kwargs
        )
    except requests.RequestException:
        st.error(
            "Cannot connect to FinTrack API. "
            "Please make sure the backend server is running."
        )
        return None


def logout():
    st.session_state.token = None
    st.session_state.username = None
    st.rerun()


def show_auth_page():
    st.title("💰 FinTrack")
    st.caption("Your money. Your goals. Your control.")

    page = st.radio(
        "Choose an option",
        ["Login", "Create Account"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if page == "Create Account":
        st.subheader("Create your account")
        st.write("Start managing your expenses today.")

        with st.form("register_form"):
            username = st.text_input(
                "Username",
                max_chars=30
            )
            password = st.text_input(
                "Password",
                type="password",
                max_chars=128
            )
            confirm_password = st.text_input(
                "Confirm password",
                type="password",
                max_chars=128
            )

            submitted = st.form_submit_button(
                "Create Account",
                use_container_width=True
            )

        if submitted:
            if len(username.strip()) < 3:
                st.error("Username must have at least 3 characters.")
            elif len(password) < 8:
                st.error("Password must have at least 8 characters.")
            elif password != confirm_password:
                st.error("Passwords do not match.")
            else:
                response = api_request(
                    "POST",
                    "/register",
                    json={
                        "username": username.strip(),
                        "password": password
                    }
                )

                if response is not None:
                    if response.status_code == 201:
                        st.success(
                            "Account created! Select Login to sign in."
                        )
                    else:
                        try:
                            detail = response.json().get(
                                "detail", "Could not create account."
                            )
                        except ValueError:
                            detail = "Could not create account."
                        st.error(str(detail))

    else:
        st.subheader("Welcome back")
        st.write("Log in to view your personal expense dashboard.")

        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input(
                "Password",
                type="password"
            )

            submitted = st.form_submit_button(
                "Login",
                use_container_width=True
            )

        if submitted:
            if not username.strip() or not password:
                st.error("Please enter your username and password.")
            else:
                response = api_request(
                    "POST",
                    "/login",
                    json={
                        "username": username.strip(),
                        "password": password
                    }
                )

                if response is not None:
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.token = result["access_token"]
                        st.session_state.username = result["username"]
                        st.rerun()
                    else:
                        st.error("Incorrect username or password.")


def show_dashboard():
    st.title("💰 FinTrack Dashboard")

    top_left, top_right = st.columns([4, 1])

    with top_left:
        st.write(f"Welcome, **{st.session_state.username}**!")
        st.caption("Here is your personal financial overview.")

    with top_right:
        if st.button("Log out", use_container_width=True):
            logout()

    st.divider()

    with st.form("add_expense_form"):
        st.subheader("➕ Add a new expense")

        title = st.text_input("Expense title")

        col1, col2 = st.columns(2)

        with col1:
            amount = st.number_input(
                "Amount (₹)",
                min_value=0.01,
                max_value=100000000.0,
                value=100.0,
                step=10.0
            )

            category = st.selectbox(
                "Category",
                CATEGORIES
            )

        with col2:
            date = st.date_input("Expense date")

        submitted = st.form_submit_button(
            "Add Expense",
            use_container_width=True
        )

    if submitted:
        if not title.strip():
            st.error("Please enter an expense title.")
        else:
            response = api_request(
                "POST",
                "/expenses",
                authenticated=True,
                json={
                    "title": title.strip(),
                    "amount": amount,
                    "category": category,
                    "date": date.isoformat()
                }
            )

            if response is not None:
                if response.status_code == 201:
                    st.success("Expense added successfully!")
                    st.rerun()
                elif response.status_code == 401:
                    st.session_state.token = None
                    st.session_state.username = None
                    st.error("Your session expired. Please log in again.")
                    st.rerun()
                else:
                    st.error(
                        f"Could not add expense: {response.text}"
                    )

    st.divider()
    st.subheader("📊 Your Expenses")

    response = api_request(
        "GET",
        "/expenses",
        authenticated=True
    )

    if response is None:
        return

    if response.status_code == 401:
        st.session_state.token = None
        st.session_state.username = None
        st.warning("Your session expired. Please log in again.")
        st.rerun()
        return

    if response.status_code != 200:
        st.error("Unable to load expenses.")
        return

    data = response.json()

    if not data:
        st.info("No expenses yet. Add your first expense above.")
        return

    df = pd.DataFrame(data)
    total = float(df["amount"].sum())

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Spent", f"₹{total:,.2f}")

    with col2:
        st.metric("Number of Expenses", len(df))

    with col3:
        st.metric(
            "This Month",
            f"₹{df.loc[df['date'].str[:7] == pd.Timestamp.today().strftime('%Y-%m'), 'amount'].sum():,.2f}"
        )

    chart_col, list_col = st.columns([1, 2])

    with chart_col:
        st.subheader("Spending by Category")
        category_totals = df.groupby("category")["amount"].sum()
        st.bar_chart(category_totals)

    with list_col:
        st.subheader("All Expenses")

        display_df = df[
            ["id", "title", "amount", "category", "date"]
        ].copy()

        display_df["amount"] = display_df["amount"].map(
            lambda value: f"₹{value:,.2f}"
        )

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

    st.subheader("🗑️ Delete an Expense")

    expense_options = {
        f"#{row['id']} — {row['title']} (₹{row['amount']:,.2f})":
        row["id"]
        for row in data
    }

    with st.form("delete_expense_form"):
        selected = st.selectbox(
            "Choose an expense to delete",
            list(expense_options.keys())
        )

        confirm = st.checkbox(
            "I confirm that I want to delete this expense."
        )

        delete_submitted = st.form_submit_button(
            "Delete Selected Expense"
        )

    if delete_submitted:
        if not confirm:
            st.warning("Please confirm before deleting.")
        else:
            expense_id = expense_options[selected]

            delete_response = api_request(
                "DELETE",
                f"/expenses/{expense_id}",
                authenticated=True
            )

            if delete_response is not None:
                if delete_response.status_code == 204:
                    st.success("Expense deleted successfully.")
                    st.rerun()
                elif delete_response.status_code == 401:
                    st.session_state.token = None
                    st.session_state.username = None
                    st.warning("Your session expired. Please log in again.")
                    st.rerun()
                else:
                    st.error(
                        f"Could not delete expense: "
                        f"{delete_response.text}"
                    )


if st.session_state.token:
    show_dashboard()
else:
    show_auth_page()
