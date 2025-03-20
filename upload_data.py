import streamlit as st
import pandas as pd
import sqlite3

# 🔒 Fungsi simpan ke database dengan parameter db_path
def save_to_db(df, table_name, db_path="rcs_data.db"):
    try:
        conn = sqlite3.connect(db_path)
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        conn.close()
        st.success(f"✅ Data berhasil disimpan di tabel: {table_name} dalam {db_path}")
    except Exception as e:
        st.error(f"❌ Error saat menyimpan ke database: {e}")

# 📤 Fungsi upload file dengan logika database khusus
def upload_file(indicator_name, table_name):
    st.subheader(f"📥 Upload Data - {indicator_name}")
    
    # 📄 Instruksi teknis upload data
    with st.expander("📖 **Instruksi Teknis Upload Data**", expanded=True):
        st.markdown("""
        1️⃣ **Dataset diambil dari hasil export laporan SIGIZI** pada menu *Laporan Daftar Entry*.  
        2️⃣ **Indikator Balita** memiliki **2 dataset**:
           - 📊 Daftar Entry - **Gizi**  
           - 📄 Daftar Entry - **KIA**  
        3️⃣ Untuk **Indikator Ibu Hamil** & **Remaja Putri**, gunakan file dari hasil export *Daftar Entry* sesuai indikatornya.  
        4️⃣ **Langkah Upload:**  
           - Pilih jenis dataset sesuai indikator yang ingin dianalisis.  
           - Download template yang telah disediakan.  
           - Salin (copy) data dari file export SIGIZI ke dalam template.  
           - Upload file template ke sistem ini.  

        ⚠️ **Catatan:**  
        - Pastikan kolom variabel sesuai dengan template.  
        - Format file wajib **.xlsx**.  
        - Data kosong atau format tidak sesuai akan ditolak.  
        """)

        # 🎯 Tombol download template
        template_links = {
            "🍼 Indikator Balita Gizi": "https://drive.google.com/uc?export=download&id=1b7oZ1fFmohtWHaXXZw_Hq-rLrpkaj8Xb",
            "📊 Indikator Balita KIA": "https://drive.google.com/uc?export=download&id=1PRdfrD0bopOmMlHDST6n1sxHUZVbRRlC",
            "🤰 Indikator Ibu Hamil": "https://drive.google.com/uc?export=download&id=1lWKK2gIuQ1tyMBZDxwpoikJKG1UWXuQd",
            "👧 Indikator Remaja Putri": "https://drive.google.com/uc?export=download&id=1pDkTxdqv2VXZCQjXqlOWtH3zFAFPW0IA",
            "📈 EPPGBM": "https://drive.google.com/uc?export=download&id=1Rp5qkD0m0Mpd0Kop3T_UtfnRSzZ8mgmR",
            "🗂️ Dataset Desa (Referensi)": "https://drive.google.com/uc?export=download&id=1Cyh8qRXi1nOB4crFgQd4TIqPbUMoZyFw"
        }

        template_url = template_links.get(indicator_name)
        if template_url:
            st.markdown(f"[📥 **Download Template {indicator_name}**]({template_url})", unsafe_allow_html=True)
        else:
            st.info("🔔 Tidak ada template khusus untuk indikator ini.")

    # 📂 Upload file
    uploaded_file = st.file_uploader(
        f"📂 Upload file Excel untuk {indicator_name}", 
        type=["xlsx"], 
        key=table_name
    )

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            if df.empty:
                st.warning("⚠️ File kosong atau format tidak sesuai.")
                return

            # Tentukan database berdasarkan indikator
            db_path = "data_eppgbm.db" if table_name == "data_eppgbm" else "rcs_data.db"
            save_to_db(df, table_name, db_path)
            st.success(f"✅ Data {indicator_name} berhasil di-upload!")
            st.dataframe(df.head())
        except Exception as e:
            st.error(f"❌ Error saat upload: {e}")

# 🚀 Halaman utama upload
def show_upload_page():
    st.title("🚀 Upload Data RCS")

    data_options = {
        "🍼 Indikator Balita Gizi": "data_balita_gizi",
        "📊 Indikator Balita KIA": "data_balita_kia",
        "🤰 Indikator Ibu Hamil": "data_ibuhamil",
        "👧 Indikator Remaja Putri": "data_remaja",
        "📈 EPPGBM": "data_eppgbm",
        "🗂️ Dataset Desa (Referensi)": "dataset_desa"
    }

    selected_data = st.selectbox("🔍 Pilih Jenis Data untuk Upload", list(data_options.keys()))

    if selected_data:
        upload_file(selected_data, data_options[selected_data])

# Jalankan aplikasi
if __name__ == "__main__":
    show_upload_page()