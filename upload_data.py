import streamlit as st
import pandas as pd
import sqlite3

# Fungsi untuk menyimpan data ke database
def save_to_db(df, table_name, db_path="rcs_data.db"):
    try:
        conn = sqlite3.connect(db_path)
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        conn.close()
        st.success(f"✅ Data berhasil disimpan ke tabel: {table_name}")
    except Exception as e:
        st.error(f"❌ Gagal menyimpan data: {e}")

# Fungsi untuk mengunggah file
def upload_file(indicator_name, table_name):
    st.subheader(f"📥 Unggah Data - {indicator_name}")
    
    with st.expander("📖 **Petunjuk Unggah Data**", expanded=True):
        st.markdown("""
        1️⃣ **Ambil data dari laporan SIGIZI** di menu *Laporan Daftar Entry*.  
        2️⃣ **Untuk Balita**, ada 2 dataset:
           - 📊 Daftar Entry - **Gizi**  
           - 📄 Daftar Entry - **KIA**  
        3️⃣ Untuk **Ibu Hamil**, **Remaja Putri**, **Bulan Timbang**, dan **Anak Prasekolah**, gunakan file dari *Daftar Entry* sesuai indikator.  
        4️⃣ **Cara Unggah:**  
           - Pilih jenis dataset.  
           - Unduh template yang disediakan.  
           - Salin data dari SIGIZI ke template.  
           - Unggah file template ke sistem ini.  

        ⚠️ **Catatan:**  
        - Pastikan kolom sesuai template.  
        - File harus berformat **.xlsx**.  
        - File kosong atau format salah akan ditolak.  
        """)

        template_links = {
            "🍼 Indikator Balita Gizi": "https://drive.google.com/uc?export=download&id=1b7oZ1fFmohtWHaXXZw_Hq-rLrpkaj8Xb",
            "📊 Indikator Balita KIA": "https://drive.google.com/uc?export=download&id=1PRdfrD0bopOmMlHDST6n1sxHUZVbRRlC",
            "🤰 Indikator Ibu Hamil": "https://drive.google.com/uc?export=download&id=1lWKK2gIuQ1tyMBZDxwpoikJKG1UWXuQd",
            "👧 Indikator Remaja Putri": "https://drive.google.com/uc?export=download&id=1pDkTxdqv2VXZCQjXqlOWtH3zFAFPW0IA",
            "📈 EPPGBM": "https://drive.google.com/uc?export=download&id=1Rp5qkD0m0Mpd0Kop3T_UtfnRSzZ8mgmR",
            "🗂️ Dataset Desa (Referensi)": "https://drive.google.com/uc?export=download&id=1Cyh8qRXi1nOB4crFgQd4TIqPbUMoZyFw",
            "📅 Bulan Timbang (Puskesmas)": "https://drive.google.com/uc?export=download&id=1ExampleBultimTemplate",  # Ganti dengan link asli
            "📅 Bulan Timbang (Kelurahan)": "https://drive.google.com/uc?export=download&id=1ExampleBultimKelurahanTemplate",  # Ganti dengan link asli
            "🏫 Dataset Anak Prasekolah": "https://drive.google.com/uc?export=download&id=1ExampleAprasTemplate"  # Ganti dengan link asli
        }

        template_url = template_links.get(indicator_name)
        if template_url:
            st.markdown(f"[📥 **Unduh Template {indicator_name}**]({template_url})", unsafe_allow_html=True)
        else:
            st.info("🔔 Tidak ada template untuk indikator ini.")

    uploaded_file = st.file_uploader(
        f"📂 Unggah file Excel untuk {indicator_name}", 
        type=["xlsx"], 
        key=table_name
    )

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            if df.empty:
                st.warning("⚠️ File kosong atau format tidak sesuai.")
                return

            db_path = "data_eppgbm.db" if table_name == "data_eppgbm" else "rcs_data.db"
            save_to_db(df, table_name, db_path)
            st.success(f"✅ Data {indicator_name} berhasil diunggah!")
            st.dataframe(df.head())
        except Exception as e:
            st.error(f"❌ Gagal unggah: {e}")

# Halaman utama untuk unggah data
def show_upload_page():
    st.title("🚀 Unggah Data RCS")

    data_options = {
        "🍼 Indikator Balita Gizi": "data_balita_gizi",
        "📊 Indikator Balita KIA": "data_balita_kia",
        "🤰 Indikator Ibu Hamil": "data_ibuhamil",
        "👧 Indikator Remaja Putri": "data_remaja",
        "📈 EPPGBM": "data_eppgbm",
        "🗂️ Dataset Desa (Referensi)": "dataset_desa",
        "📅 Bulan Timbang (Puskesmas)": "data_bultim",
        "📅 Bulan Timbang (Kelurahan)": "data_bultim_kelurahan",
        "🏫 Dataset Anak Prasekolah": "dataset_apras"  # Opsi baru untuk Anak Prasekolah
    }

    selected_data = st.selectbox("🔍 Pilih Jenis Data untuk Unggah", list(data_options.keys()))

    if selected_data:
        upload_file(selected_data, data_options[selected_data])

if __name__ == "__main__":
    show_upload_page()