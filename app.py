import streamlit as st
import auth
import upload_data
import dashboard_balita_gizi
import dashboard_balita_kia
import dashboard_ibuhamil
import dashboard_remaja
import dashboard_eppgbm
import time

# Konfigurasi halaman
st.set_page_config(page_title="Dashboard RCS", layout="wide")

# Cek login user
if "username" not in st.session_state:
    auth.show_login()
else:
    # Cek timeout session
    if "last_active" in st.session_state:
        if time.time() - st.session_state["last_active"] > 1800:  # 30 menit timeout
            auth.sign_out()
        else:
            st.session_state["last_active"] = time.time()  # Perbarui waktu aktivitas

    # Sidebar setelah login
    st.sidebar.title(f"👤 Welcome, {st.session_state['username']}")
    st.sidebar.write(f"Role: {st.session_state['role']}")

    # Menu navigasi sidebar
    menu = st.sidebar.radio("🔍 Menu", [
        "Dashboard Overview", 
        "Indikator Balita", 
        "Indikator Ibu Hamil", 
        "Indikator Remaja Putri", 
        "EPPGBM", 
        "Upload Data" if st.session_state["role"] == "admin_dinkes" else ""
    ])

    # Tampilkan tombol logout di bawah menu
    auth.logout()

    # Dashboard Overview
    if menu == "Dashboard Overview":
        st.write("📊 **Dashboard Overview**")

    # Indikator Balita dengan sub-menu
    elif menu == "Indikator Balita":
        sub_menu = st.sidebar.radio("➡️ Pilih Sub-Menu Balita", ["Dashboard Balita Gizi", "Dashboard Balita KIA"])

        if sub_menu == "Dashboard Balita Gizi":
            dashboard_balita_gizi.show_dashboard()

        elif sub_menu == "Dashboard Balita KIA":
            dashboard_balita_kia.show_dashboard()

    elif menu == "Indikator Ibu Hamil":
        dashboard_ibuhamil.show_dashboard()

    elif menu == "Indikator Remaja Putri":
        dashboard_remaja.show_dashboard()

    elif menu == "EPPGBM":
        if st.session_state["role"] in ["admin_dinkes", "admin_puskesmas"]:
            dashboard_eppgbm.show_dashboard()
        else:
            st.warning("🚫 Anda tidak memiliki akses ke EPPGBM.")

    elif menu == "Upload Data" and st.session_state["role"] == "admin_dinkes":
        upload_data.show_upload_page()