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
            .login-container {
                display: flex;
                justify-content: center;
                align-items: center;
                height: 80vh;
            }
            .login-box {
                width: 320px;
                padding: 20px;
                border-radius: 10px;
                background: #ffffff;
                box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
                text-align: center;
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
        with st.form(key="login_form"):
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            st.markdown("### 🔑 Login Dashboard RCS")
            username = st.text_input("Nama Pengguna", key="username_input")
            password = st.text_input("Kata Sandi", type="password", key="password_input")
            
            # Tombol login
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
                        st.session_state["last_active"] = time.time()  # Set waktu aktivitas terakhir
                        st.rerun()
                    else:
                        st.error("❌ Nama pengguna atau kata sandi salah!", icon="🚨")

            st.markdown('</div>', unsafe_allow_html=True)

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