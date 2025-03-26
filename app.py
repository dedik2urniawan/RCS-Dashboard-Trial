import streamlit as st
import auth
import upload_data
import dashboard_balita_gizi
import dashboard_balita_kia
import dashboard_ibuhamil
import dashboard_remaja
import dashboard_eppgbm
import rcs_calc  # Impor modul RCS Calculator
import pmt_pkmk  # Impor modul PMT & PKMK
import composite_analysis  # Impor modul Composite Analysis
import rest_api  # Impor modul API Integrasi
import time

# Konfigurasi halaman
st.set_page_config(page_title="Dashboard RCS", layout="wide")

# Fungsi utama aplikasi
def main():
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
        st.sidebar.write(f"**Role:** {st.session_state['role']}")

        # Menu navigasi sidebar dengan ikon
        st.sidebar.header("🔍 Navigasi")
        menu_options = [
            "📊 Dashboard Overview",
            "🍼 Indikator Balita",
            "🤰 Indikator Ibu Hamil",
            "👧 Indikator Remaja Putri",
            "📋 EPPGBM",
            "🧮 RCS Calculator",
            "🍽️ Analisis PMT & PKMK",
            "📈 Analisis Composite",
            "🌐 API Integrasi"
        ]

        # Tambahkan menu "Upload Data" hanya untuk admin_dinkes
        if st.session_state["role"] == "admin_dinkes":
            menu_options.append("📂 Upload Data")

        menu = st.sidebar.radio("Pilih Menu:", menu_options, index=0)

        # Logika untuk menampilkan halaman berdasarkan menu yang dipilih
        if menu == "📊 Dashboard Overview":
            # Subheader dengan ikon
            st.subheader("📊 Dashboard Overview: Latar Belakang dan Tujuan Sistem")

            # Blok informasi dengan gaya serupa seperti EPPGBM
            st.markdown("""
                <div style="background-color: #F9F9F9; padding: 20px; border-radius: 10px; border-left: 6px solid #1976D2; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                    <p style="font-size: 16px; color: #333; line-height: 1.6; font-family: Arial, sans-serif;">
                        Selamat datang di <strong>Dashboard RCS</strong>! Sistem ini dikembangkan oleh tim Dinas Kesehatan Kabupaten Malang untuk mendukung analisis data gizi masyarakat secara terpadu. Dashboard ini menyediakan gambaran umum dan analisis mendalam tentang status gizi di berbagai kelompok masyarakat, termasuk balita, ibu hamil, dan remaja putri, dengan cakupan data dari 39 Puskesmas dan 390 desa di Kabupaten Malang.
                    </p>
                    <p style="font-size: 16px; color: #333; line-height: 1.6; font-family: Arial, sans-serif;">
                        Dashboard RCS mengintegrasikan data dari berbagai sumber, termasuk <strong>SIGIZI-KESGA</strong> dan laporan berbasis masyarakat seperti Posyandu. Data dikumpulkan secara berkala (Februari dan Agustus setiap tahun) melalui proses verifikasi bertahap untuk memastikan akurasi dan konsistensi. Sistem ini juga dilengkapi dengan alat analisis lanjutan seperti <strong>RCS Calculator</strong> dan <strong>Analisis Composite</strong>, yang memungkinkan deteksi tren, distribusi data, dan evaluasi program gizi secara otomatis.
                    </p>
                    <p style="font-size: 16px; color: #333; line-height: 1.6; font-family: Arial, sans-serif;">
                        Tujuan utama Dashboard RCS adalah mendukung pengambil keputusan di tingkat lokal untuk merancang intervensi gizi yang lebih efektif. Dengan fitur visualisasi real-time dan aksesibilitas melalui perangkat mobile maupun desktop, dashboard ini menjadi alat strategis untuk memantau, mengevaluasi, dan meningkatkan program kesehatan masyarakat di Kabupaten Malang. Pilih menu di sidebar untuk melihat analisis lebih lanjut.
                    </p>
                </div>
            """, unsafe_allow_html=True)

        elif menu == "🍼 Indikator Balita":
            sub_menu = st.sidebar.radio(
                "➡️ Pilih Sub-Menu Balita",
                ["📉 Dashboard Balita Gizi", "🩺 Dashboard Balita KIA"]
            )
            if sub_menu == "📉 Dashboard Balita Gizi":
                dashboard_balita_gizi.show_dashboard()
            elif sub_menu == "🩺 Dashboard Balita KIA":
                dashboard_balita_kia.show_dashboard()

        elif menu == "🤰 Indikator Ibu Hamil":
            dashboard_ibuhamil.show_dashboard()

        elif menu == "👧 Indikator Remaja Putri":
            dashboard_remaja.show_dashboard()

        elif menu == "📋 EPPGBM":
            if st.session_state["role"] in ["admin_dinkes", "admin_puskesmas"]:
                dashboard_eppgbm.show_dashboard()
            else:
                st.warning("🚫 Anda tidak memiliki akses ke EPPGBM.")

        elif menu == "🧮 RCS Calculator":
            sub_menu_rcs = st.sidebar.selectbox(
                "➡️ Pilih Versi RCS Calculator",
                ["RCS Calc versi 1.0.0", "RCS Calc versi 1.0.1"],
                key="rcs_submenu"
            )
            rcs_calc.show_rcs_calculator(sub_menu_rcs)

        elif menu == "🍽️ Analisis PMT & PKMK":
            pmt_pkmk.show_dashboard()

        elif menu == "📈 Analisis Composite":
            composite_analysis.show_dashboard()

        elif menu == "🌐 API Integrasi":
            rest_api.show_dashboard()

        elif menu == "📂 Upload Data" and st.session_state["role"] == "admin_dinkes":
            upload_data.show_upload_page()

        # Tombol logout di bagian paling bawah
        st.sidebar.markdown("---")
        auth.logout()

# Jalankan aplikasi
if __name__ == "__main__":
    main()