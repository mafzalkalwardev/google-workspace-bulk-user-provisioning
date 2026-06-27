"""Google Workspace Bulk User Provisioning — Streamlit UI."""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from services.google_admin import GoogleAdminProvisioner
from services.browser_upload import bulk_upload_via_browser
from utils.generate_users import (
    FIXED_TEMP_PASSWORD,
    generate_users,
    save_user_exports,
    users_to_bulk_upload_df,
    users_to_export_df,
)

ROOT = Path(__file__).resolve().parent
EXPORTS_DIR = ROOT / "exports"

st.set_page_config(
    page_title="Google Workspace Bulk Provisioning",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    .main-header { font-size: 2rem; font-weight: 700; margin-bottom: 0.25rem; }
    .sub-header { color: #5f6368; margin-bottom: 1.5rem; }
    .security-note {
        background: #fef7e0; border-left: 4px solid #f9ab00;
        padding: 1rem 1.25rem; border-radius: 0 8px 8px 0; margin: 1rem 0;
    }
    .success-box {
        background: #e6f4ea; border-left: 4px solid #1e8e3e;
        padding: 1rem 1.25rem; border-radius: 0 8px 8px 0;
    }
    div[data-testid="stSidebar"] { background-color: #f8f9fa; }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def init_session_state() -> None:
    defaults = {
        "generated_users": None,
        "bulk_path": None,
        "export_path": None,
        "report_path": None,
        "provision_results": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def df_for_display(df: pd.DataFrame, show_passwords: bool) -> pd.DataFrame:
    display = df.copy()
    if not show_passwords:
        for col in display.columns:
            if "password" in col.lower():
                display[col] = "••••••••••••"
    return display


def download_button_for_df(label: str, df: pd.DataFrame, filename: str, key: str) -> None:
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, encoding="utf-8-sig")
    st.download_button(
        label=label,
        data=buffer.getvalue(),
        file_name=filename,
        mime="text/csv",
        key=key,
        use_container_width=True,
    )


init_session_state()

with st.sidebar:
    st.title("Workspace Provisioning")
    st.caption("Secure bulk user creation for **getinmarketing.site**")
    st.divider()
    st.markdown("**Official methods only**")
    st.markdown(
        "- CSV bulk upload\n"
        "- Admin SDK Directory API\n\n"
        "No browser automation, login, or 2SV enrollment."
    )
    st.divider()
    show_passwords = st.toggle("Show passwords", value=False)

st.markdown('<p class="main-header">Google Workspace Bulk User Provisioning</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">Generate British-style users, export Google-compatible CSV, '
    "or provision via Admin SDK.</p>",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="security-note">'
    "<strong>Security:</strong> This app does <em>not</em> automate Admin Console clicks, "
    "user sign-in, 2-Step Verification, or app passwords. "
    "Enforce 2SV from Admin Console; users enroll themselves."
    "</div>",
    unsafe_allow_html=True,
)

tab_generate, tab_upload, tab_browser, tab_api, tab_docs = st.tabs(
    ["Generate Users", "Bulk Upload Guide", "Browser Upload", "Admin SDK", "Security & 2SV"]
)

with tab_generate:
    col_form, col_preview = st.columns([1, 1.2], gap="large")

    with col_form:
        st.subheader("Configuration")
        with st.form("user_generation_form"):
            domain = st.text_input("Domain", value="getinmarketing.site")
            number_of_users = st.number_input("Number of users", min_value=1, max_value=5000, value=300)
            password_mode_label = st.radio(
                "Password mode",
                options=["Fixed temporary password", "Random strong password"],
                index=0,
            )
            password_mode = "fixed" if password_mode_label.startswith("Fixed") else "random"
            fixed_password = FIXED_TEMP_PASSWORD
            if password_mode == "fixed":
                fixed_password = st.text_input("Fixed password", value=FIXED_TEMP_PASSWORD)
            username_format = st.selectbox(
                "Username format",
                options=[
                    ("firstname.lastname", "firstname.lastname (e.g. jack.smith)"),
                    ("firstinitiallastname", "firstinitiallastname (e.g. jsmith)"),
                    ("firstname123", "firstname123 (e.g. jack, jack1)"),
                ],
                format_func=lambda x: x[1],
            )[0]
            org_unit_path = st.text_input("Org unit path", value="/")
            change_password_at_next_login = st.checkbox("Force password change on first login", value=True)
            random_seed = st.number_input("Random seed (0 = random each run)", min_value=0, value=0)
            submitted = st.form_submit_button("Generate users", type="primary", use_container_width=True)

        if submitted:
            try:
                seed = None if random_seed == 0 else int(random_seed)
                users = generate_users(
                    domain=domain.strip().lower(),
                    count=int(number_of_users),
                    password_mode=password_mode,
                    username_format=username_format,
                    org_unit_path=org_unit_path,
                    change_password_at_next_login=change_password_at_next_login,
                    fixed_password=fixed_password,
                    seed=seed,
                )
                bulk_path, export_path = save_user_exports(users, EXPORTS_DIR)
                st.session_state.generated_users = users
                st.session_state.bulk_path = bulk_path
                st.session_state.export_path = export_path
                st.session_state.provision_results = None
                st.session_state.report_path = None
                st.success(f"Generated {len(users)} users successfully.")
            except Exception as exc:
                st.error(str(exc))

    with col_preview:
        st.subheader("Preview & Export")
        users = st.session_state.generated_users
        if not users:
            st.info("Configure options and click **Generate users**.")
        else:
            export_df = users_to_export_df(users)
            bulk_df = users_to_bulk_upload_df(users)
            c1, c2, c3 = st.columns(3)
            c1.metric("Users", len(users))
            c2.metric("Domain", users[0].primary_email.split("@")[1])
            c3.metric("Org unit", users[0].org_unit_path)
            st.dataframe(df_for_display(export_df, show_passwords), use_container_width=True, height=360, hide_index=True)
            d1, d2 = st.columns(2)
            with d1:
                download_button_for_df("Download workspace_users.csv", export_df, "workspace_users.csv", "dl_export")
            with d2:
                download_button_for_df("Download bulk upload CSV", bulk_df, "workspace_users_bulk_upload.csv", "dl_bulk")
            if st.session_state.export_path:
                st.caption(f"Saved to `exports/` folder locally.")

with tab_upload:
    st.subheader("Bulk upload via Google Admin Console")
    st.markdown(
        """
1. Sign in to [Google Admin Console](https://admin.google.com) as **admin@getinmarketing.site**.
2. Go to **Directory → Users** and click **Bulk update users** at the top of the page.
   If you do not see it, open **More options** and look for **Bulk update users**.
3. Upload **`workspace_users_bulk_upload.csv`** from the `exports/` folder.
4. Review preview, fix validation errors, confirm upload.
5. Keep **`workspace_users.csv`** as your master credential record (store securely).

**Bulk upload columns:** First Name, Last Name, Email Address, Password, Org Unit Path, Change Password at Next Sign-In.
        """
    )
    if st.session_state.bulk_path and Path(st.session_state.bulk_path).exists():
        st.markdown(f'<div class="success-box">Latest file: <code>{st.session_state.bulk_path}</code></div>', unsafe_allow_html=True)

with tab_browser:
    st.subheader("Automated bulk upload (browser)")
    st.markdown(
        """
Use Playwright to open Google Admin Console, attach your CSV, and submit the bulk upload.
A Chrome window opens on your machine — sign in as super admin if prompted, then the script continues automatically.

**Requires:** Google Chrome installed locally.
        """
    )
    default_csv = EXPORTS_DIR / "workspace_users_bulk_upload.csv"
    bulk_csv_path = st.text_input("Bulk upload CSV path", value=str(default_csv))
    if st.button("Run browser bulk upload", type="primary"):
        csv_path = Path(bulk_csv_path)
        if not csv_path.is_file():
            st.error(f"CSV not found: {csv_path}")
        else:
            with st.spinner("Opening Chrome and uploading CSV. Complete Google sign-in if prompted..."):
                result = bulk_upload_via_browser(csv_path, headless=False)
            if result.success:
                st.success(result.message)
            else:
                st.error(result.message)
            if result.screenshot_path and result.screenshot_path.exists():
                st.image(str(result.screenshot_path), caption="Upload result screenshot")
                st.caption(f"Saved to `{result.screenshot_path}`")

with tab_api:
    st.subheader("Provision via Admin SDK")
    provisioner = GoogleAdminProvisioner()
    config_errors = provisioner.validate_config()
    if config_errors:
        st.warning("Admin SDK not configured:\n\n- " + "\n- ".join(config_errors))
    else:
        st.success(f"Ready: **{provisioner.admin_email}**")
    users = st.session_state.generated_users
    if not users:
        st.info("Generate users first on the **Generate Users** tab.")
    elif st.button("Create users via Admin SDK", type="primary", disabled=bool(config_errors)):
        progress = st.progress(0)
        log_area = st.empty()
        results = []
        try:
            for index, user in enumerate(users, start=1):
                result = provisioner.create_user(user)
                results.append(result)
                progress.progress(index / len(users), text=f"{index}/{len(users)}")
                icon = "OK" if result.success else "FAIL"
                msg = f"{icon} {user.primary_email}"
                if result.error_message:
                    msg += f" — {result.error_message}"
                log_area.write(msg)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = provisioner.export_report(results, EXPORTS_DIR / f"provisioning_report_{ts}.csv")
            st.session_state.provision_results = results
            st.session_state.report_path = report_path
            created = sum(1 for r in results if r.success)
            st.success(f"Done: {created} created, {len(results) - created} failed.")
        except Exception as exc:
            st.error(str(exc))
    if st.session_state.report_path:
        report_df = pd.read_csv(st.session_state.report_path)
        st.dataframe(report_df, use_container_width=True, height=300, hide_index=True)
        download_button_for_df("Download report", report_df, Path(st.session_state.report_path).name, "dl_report")

with tab_docs:
    st.subheader("Security & 2-Step Verification")
    st.markdown(
        """
### Enforce 2SV (admin)

1. Admin Console → **Security → Authentication → 2-step verification**
2. Select OU or domain → turn enforcement **On** (use a grace period for new users)

### User self-enrollment

Users sign in, change password, then enable 2SV at [myaccount.google.com/security](https://myaccount.google.com/security).
They create app passwords themselves if needed.

### Why no Selenium / login automation

Automating Admin Console, user login, 2SV, or app passwords violates security best practices,
exposes credentials in scripts/logs, and conflicts with Google's Terms of Service.

### Protect exports

- Never commit `.env` or CSV files with passwords
- Use encrypted storage; delete after users are onboarded
        """
    )

st.caption("Official CSV & Admin SDK methods only · Credentials stay on your machine.")
