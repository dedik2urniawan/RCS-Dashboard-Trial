import streamlit as st
import sqlite3
import time

# ----------------------------- #
# 📌 Fungsi untuk Cek User di Database
# ----------------------------- #
def check_user(username, password):
    try:
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT password, role FROM users WHERE username=?", (username,))
        result = cursor.fetchone()
        conn.close()

        if result and password == result[0]:
            return result[1]
        return None
    except Exception as e:
        st.error(f"⚠️ Terjadi kesalahan dalam autentikasi: {e}")
        return None

# ----------------------------- #
# 🏷️ Fungsi untuk Menampilkan Form Login
# ----------------------------- #
def show_login():
    # Styling CSS dengan efek tombol yang diperbarui
    st.markdown("""
        <style>
            .main {
                margin-top: 0 !important;
                padding-top: 0 !important;
                }
            .login-container {
                display: flex;
                justify-content: center;
                align-items: flex-start;
                height: 100vh;
                margin-top: 0;
            }
            .login-box {
                width: 320px;
                padding: 20px;
                border-radius: 10px;
                background: #ffffff;
                box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
                text-align: center;
                margin-top: 0;
            }
            .stTextInput>div>div>input {
                width: 100% !important;
                padding: 10px;
                border-radius: 5px;
                border: 1px solid #ddd;
            }
            .stButton>button {
                width: 100%;
                background: linear-gradient(45deg, #28a745, #34d058); /* Gradien awal */
                color: white !important;
                padding: 10px;
                border-radius: 5px;
                border: none;
                font-size: 16px;
                transition: all 0.3s ease; /* Transisi halus untuk semua efek */
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); /* Bayangan awal */
            }
            .stButton>button:hover {
                background: linear-gradient(45deg, #218838, #2ecc71); /* Gradien saat hover */
                transform: scale(1.05); /* Sedikit membesar */
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2); /* Bayangan lebih tajam */
                cursor: pointer; /* Tanda tangan saat hover */
            }
            .logout-button button {
                background: linear-gradient(45deg, #dc3545, #ff4040); /* Gradien merah untuk logout */
                color: white !important;
            }
            .logout-button button:hover {
                background: linear-gradient(45deg, #c82333, #e74c3c); /* Gradien merah lebih gelap saat hover */
                transform: scale(1.05);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            }
            /* Styling untuk checkbox logout */
            .stCheckbox label {
                color: #666; /* Warna default teks */
                font-size: 14px;
                transition: color 0.3s ease; /* Transisi halus untuk warna */
            }
            .stCheckbox input:checked + label {
                color: #dc3545 !important; /* Warna merah saat dicentang */
                animation: wiggle 0.5s ease; /* Animasi wiggle saat dicentang */
            }
            @keyframes wiggle {
                0% { transform: translateX(0); }
                25% { transform: translateX(-3px); }
                50% { transform: translateX(3px); }
                75% { transform: translateX(-3px); }
                100% { transform: translateX(0); }
            }
            .footer {
                text-align: center;
                font-size: 14px;
                margin-top: 15px;
                color: #666;
            }
        </style>
    """, unsafe_allow_html=True)

    # Redirect jika sudah login
    if "authenticated" in st.session_state and st.session_state["authenticated"]:
        st.success(f"✅ Selamat datang, {st.session_state['username']}!")
        return

    # Tampilkan pesan logout jika ada
    if "logout_message" in st.session_state:
        st.success(st.session_state["logout_message"])
        del st.session_state["logout_message"]  # Hapus pesan setelah ditampilkan

    # Layout kolom agar form login berada di tengah
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        placeholder = st.empty()
        with placeholder.form(key="login_form"):
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            st.markdown("### 🔑 Login Dashboard RCS")
            username = st.text_input("Nama Pengguna", key="username_input")
            password = st.text_input("Kata Sandi", type="password", key="password_input")
            submit_button = st.form_submit_button("🔒 Masuk")
            if submit_button:
                with st.spinner('🔄 Sedang memeriksa kredensial...'):
                    time.sleep(1)
                    role = check_user(username, password)
                    if role:
                        st.success('✅ Berhasil masuk!')
                        st.balloons()
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = username
                        st.session_state["role"] = role
                        st.session_state["last_active"] = time.time()
                        st.rerun()
                    else:
                        st.error("❌ Nama pengguna atau kata sandi salah!", icon="🚨")
            st.markdown('</div>', unsafe_allow_html=True)

    # Tambahkan informasi Log Version sebelum footer
        with st.expander("📜 Log Version Dashboard RCS (R-Calculator SIGMA)", expanded=False):
            st.markdown("""
                <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
                
                ### 📜 Log Version Dashboard RCS

                Berikut adalah riwayat pengembangan sistem Dashboard RCS untuk memotret Kinerja Program Kesehatan Gizi, Keluarga dan Komunitas & Layanan Primer, yang mencakup berbagai modul untuk mendukung analisis data gizi dan kesehatan masyarakat. Setiap versi mencerminkan peningkatan fitur, perbaikan performa, dan rencana pengembangan masa depan.

                #### Version 1.0.0 (Initial Release, 15 Januari 2025)
                - **Modul Login dan Security Data (Fix):** Implementasi autentikasi pengguna dengan enkripsi data menggunakan algoritma keamanan tinggi untuk memastikan akses yang aman dan melindungi data sensitif pengguna.
                - **Modul Dashboard Balita Gizi (Fix):** Pengembangan dashboard awal untuk analisis gizi balita, mencakup metrik prevalensi stunting, wasting, dan underweight, dengan visualisasi interaktif menggunakan Plotly.

                #### Version 1.1.0 (Update, 1 Februari 2025)
                - **Modul Dashboard Balita KIA (Fix):** Penambahan dashboard untuk Kesehatan Ibu dan Anak (KIA), dengan fokus pada imunisasi, pemeriksaan berkala, dan monitoring perkembangan balita, dilengkapi dengan fitur filter berdasarkan puskesmas dan kelurahan.

                #### Version 1.2.0 (Update, 15 Februari 2025)
                - **Modul Dashboard Ibu Hamil (Fix):** Pengembangan dashboard untuk ibu hamil, mencakup analisis anemia, suplementasi gizi (MMS dan TTD), serta Kurang Energi Kronis (KEK), dengan metrik yang mendukung pengambilan keputusan berbasis data.

                #### Version 1.3.0 (Update, 1 Maret 2025)
                - **Modul Dashboard Remaja Putri (Fix):** Dashboard untuk remaja putri, dengan fokus pada monitoring gizi, prevalensi anemia, dan edukasi kesehatan reproduksi, untuk mendukung program pencegahan anemia pada kelompok usia produktif.

                #### Version 1.4.0 (Update, 10 Maret 2025)
                - **Modul Analisis Bulan Timbang (EPPGBM) (Fix):** Analisis Evaluasi Pertumbuhan dan Perkembangan Balita dan Ibu (EPPGBM) dengan metrik bulanan untuk tracking tren gizi, dilengkapi dengan fitur visualisasi tren waktu untuk analisis longitudinal.

                #### Version 1.5.0 (Update, 10 Maret 2025)
                - **Modul Analisis PMT & PKMK (On Progress):** Modul untuk analisis Pemberian Makanan Tambahan (PMT) dan Pemantauan Konsumsi Makanan Keluarga (PKMK), sedang dalam tahap pengembangan untuk mendukung intervensi gizi berbasis keluarga dengan pendekatan data-driven.

                #### Version 1.6.0 (Planned, Q2 2025)
                - **Modul API (Next):** Pengembangan API berbasis REST untuk integrasi data dengan sistem eksternal, memungkinkan interoperabilitas dan akses data real-time untuk mendukung kolaborasi antar platform.

                #### Version 1.7.0 (Planned, Q3 2025)
                - **Modul Machine Learning Stunting (Next):** Implementasi model machine learning untuk prediksi risiko stunting berbasis data antropometri, gizi, dan sosial-ekonomi, menggunakan algoritma seperti Random Forest dan Neural Network untuk mendukung intervensi dini dan kebijakan berbasis data.

                #### Catatan Developer:
                Sistem ini dikembangkan dengan pendekatan data science untuk mendukung analisis kesehatan masyarakat yang akurat dan actionable. Setiap modul dirancang dengan prinsip user-centered design, memastikan kemudahan penggunaan bagi petugas kesehatan dan pengambil kebijakan. Rencana pengembangan ke depan akan terus berfokus pada integrasi teknologi AI dan interoperabilitas data untuk mendukung pencapaian target Sustainable Development Goals (SDGs) terkait kesehatan dan gizi.

                </div>
            """, unsafe_allow_html=True)
    # Footer
        st.markdown('<p class="footer">made with ❤️ by <a href="mailto:dedik2urniawan@gmail.com">dedik2urniawan@gmail.com</a></p>', unsafe_allow_html=True)

# ----------------------------- #
# 🔓 Fungsi Logout
# ----------------------------- #
def logout():
    if "authenticated" in st.session_state and st.session_state["authenticated"]:
        st.sidebar.markdown('<div class="logout-button">', unsafe_allow_html=True)
        if "show_confirm" not in st.session_state:
            st.session_state["show_confirm"] = False
        
        if st.sidebar.button("🔓 Logout"):
            st.session_state["show_confirm"] = True
        
        if st.session_state["show_confirm"]:
            confirm = st.sidebar.checkbox("Apakah Anda yakin ingin logout?", key="logout_confirm")
            if confirm:
                sign_out()
                st.session_state["show_confirm"] = False  # Reset setelah logout
        
        st.sidebar.markdown('</div>', unsafe_allow_html=True)

def sign_out():
    # Simpan pesan sukses sebelum menghapus session
    st.session_state["logout_message"] = "✅ Anda telah berhasil keluar."
    # Hapus hanya kunci yang relevan
    keys_to_remove = ["authenticated", "username", "role", "last_active", "show_confirm"]
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]
    # Rerun untuk memuat ulang halaman
    st.rerun()