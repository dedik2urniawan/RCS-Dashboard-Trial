import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import os
import datetime
import time
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO

# ----------------------------- #
# 📥 Fungsi untuk Load Data
# ----------------------------- #
@st.cache_data
def load_data():
    """Memuat data dari database SQLite rcs_data.db."""
    try:
        conn = sqlite3.connect("rcs_data.db")
        df = pd.read_sql_query("SELECT * FROM data_ibuhamil", conn)
        desa_df = pd.read_sql_query("SELECT * FROM dataset_desa", conn)
        conn.close()
        # Hapus duplikat jika ada
        df = df.drop_duplicates()
        desa_df = desa_df.drop_duplicates()
        return df, desa_df
    except Exception as e:
        st.error(f"❌ Gagal memuat data: {e}")
        return None, None

# ----------------------------- #
# 🏷️ Fungsi untuk Mendapatkan Waktu Upload Dataset
# ----------------------------- #
def get_last_upload_time():
    """Mengembalikan waktu terakhir modifikasi file database."""
    try:
        file_path = "rcs_data.db"
        if os.path.exists(file_path):
            last_modified_time = os.path.getmtime(file_path)
            return datetime.datetime.fromtimestamp(last_modified_time).strftime("%d %B %Y, %H:%M:%S")
        return "Belum ada data yang diunggah"
    except Exception:
        return "Gagal mendapatkan waktu upload"

# ----------------------------- #
# ✅ Compliance Rate
# ----------------------------- #
def compliance_rate(filtered_df, desa_df, bulan_filter, puskesmas_filter, kelurahan_filter):
    """Menghitung dan menampilkan tingkat kepatuhan pelaporan untuk data ibu hamil."""
    st.header("✅ Compliance Rate")
    desa_terlapor = filtered_df['Kelurahan'].unique()
    total_desa = desa_df.copy()
    
    # Tambahkan info dengan tone akademik, rendering rumus, penjelasan untuk orang awam, dan background biru muda
    with st.expander("📜 Definisi dan Insight Analisis Kelengkapan Laporan Data", expanded=False):
        # Satukan seluruh konten dalam satu markdown dengan div untuk background
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Analisis Indikator

            Berikut adalah definisi operasional, rumus perhitungan, serta analisis insight dari indikator-indikator yang digunakan untuk memantau kelengkapan dan kepatuhan pelaporan data ibu hamil dalam sistem kesehatan masyarakat. Rumus disajikan dalam format matematis untuk kejelasan, dengan penjelasan sederhana untuk memudahkan pemahaman.

            #### 1. Compliance Rate
            - **Definisi Operasional:** Persentase desa atau kelurahan yang telah melaporkan data ibu hamil secara lengkap dalam suatu periode tertentu di wilayah kerja tertentu, dibandingkan dengan total desa atau kelurahan yang seharusnya melapor.  
            - **Rumus Perhitungan:**  
            $$ \\text{Compliance Rate (\\%)} = \\frac{\\text{Jumlah Desa/Kelurahan yang Melapor}}{\\text{Jumlah Total Desa/Kelurahan}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase desa atau kelurahan yang sudah mengirimkan laporan dibandingkan dengan semua desa atau kelurahan yang diharapkan melapor, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan secara bulanan dari basis data puskesmas dan desa melalui sistem pelaporan elektronik atau manual, dengan verifikasi terhadap keberadaan laporan dari setiap kelurahan.  
            - **Insight Analisis:** Tingkat kepatuhan pelaporan yang rendah (di bawah 80%) dapat mengindikasikan adanya hambatan logistik, kurangnya pelatihan petugas, atau akses terbatas ke teknologi pelaporan. Persentase ini penting untuk memastikan kualitas data yang digunakan dalam pengambilan keputusan kebijakan kesehatan. Intervensi yang disarankan meliputi pelatihan rutin untuk petugas kesehatan dan peningkatan infrastruktur teknologi informasi.

            #### 2. Completeness Rate
            - **Definisi Operasional:** Persentase entri data ibu hamil yang memiliki semua kolom kunci terisi secara lengkap dalam suatu periode tertentu di wilayah kerja tertentu, dibandingkan dengan total entri data yang ada.  
            - **Rumus Perhitungan:**  
            $$ \\text{Completeness Rate (\\%)} = \\frac{\\text{Jumlah Entri Data Lengkap}}{\\text{Jumlah Total Entri Data}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase data yang sudah terisi penuh untuk semua kolom penting (seperti jumlah ibu hamil yang diperiksa atau mendapat suplementasi) dibandingkan dengan semua data yang dicatat, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui formulir pelaporan bulanan dari puskesmas, dengan validasi otomatis untuk memastikan semua kolom kunci (misalnya, Jumlah_ibu_hamil_periksa_Hb, Anemia_ringan, dll.) terisi.  
            - **Insight Analisis:** Tingkat kelengkapan data yang rendah (di bawah 90%) dapat mengindikasikan kesalahan pengisian, kurangnya pengawasan, atau kurangnya pemahaman petugas terhadap pentingnya data lengkap. Data yang tidak lengkap dapat menyulitkan analisis epidemiologi dan perencanaan intervensi kesehatan. Peningkatan pelatihan data entry dan penggunaan sistem validasi real-time dapat meningkatkan angka ini.

            </div>
        """, unsafe_allow_html=True)


    # Filter berdasarkan Bulan, Puskesmas, dan Kelurahan
    if bulan_filter != "All":
        bulan_value = int(bulan_filter) if bulan_filter.isdigit() else bulan_filter
        total_desa = total_desa[total_desa['Bulan'] == bulan_value] if 'Bulan' in total_desa.columns and total_desa['Bulan'].dtype in [int, float, str] else total_desa
        filtered_df = filtered_df[filtered_df['Bulan'] == bulan_value] if 'Bulan' in filtered_df.columns and filtered_df['Bulan'].dtype in [int, float, str] else filtered_df
    if puskesmas_filter != "All":
        total_desa = total_desa[total_desa['Puskesmas'] == puskesmas_filter]
        filtered_df = filtered_df[filtered_df['Puskesmas'] == puskesmas_filter]
    if kelurahan_filter != "All":
        total_desa = total_desa[total_desa['Kelurahan'] == kelurahan_filter]
        filtered_df = filtered_df[filtered_df['Kelurahan'] == kelurahan_filter]

    total_desa_count = total_desa['Kelurahan'].nunique()
    desa_lapor_count = len(desa_terlapor)
    compliance_value = (desa_lapor_count / total_desa_count * 100) if total_desa_count else 0

    st.metric(label="Compliance Rate (%)", value=f"{compliance_value:.2f}%")

    # Tentukan iterable untuk bulan berdasarkan kondisi
    if bulan_filter == "All" and 'Bulan' in desa_df.columns:
        bulan_iterable = sorted(desa_df['Bulan'].unique())
    else:
        bulan_iterable = [int(bulan_filter)] if bulan_filter != "All" and bulan_filter.isdigit() else [0]

    # Tabel Compliance Rate per Puskesmas
    compliance_data = []
    for bulan in bulan_iterable:
        for puskesmas in sorted(desa_df['Puskesmas'].unique()):
            # Filter data berdasarkan Bulan dan Puskesmas
            desa_filter = desa_df[(desa_df['Puskesmas'] == puskesmas) & 
                                (desa_df['Bulan'] == bulan if bulan_filter != "All" and 'Bulan' in desa_df.columns else True)]
            filtered_filter = filtered_df[(filtered_df['Puskesmas'] == puskesmas) & 
                                        (filtered_df['Bulan'] == bulan if bulan_filter != "All" and 'Bulan' in filtered_df.columns else True)]

            jumlah_desa = desa_filter['Kelurahan'].nunique()
            jumlah_desa_lapor = filtered_filter['Kelurahan'].nunique()
            compliance_rate_value = (jumlah_desa_lapor / jumlah_desa * 100) if jumlah_desa else 0

            compliance_data.append({
                "Bulan": bulan if bulan_filter == "All" else bulan_filter,
                "Puskesmas": puskesmas,
                "Jumlah Desa": jumlah_desa,
                "Jumlah Desa Lapor": jumlah_desa_lapor,
                "Compliance Rate (%)": f"{compliance_rate_value:.2f}%"
            })

    compliance_df = pd.DataFrame(compliance_data)
    st.subheader("📋 Tabel Compliance Rate per Puskesmas")
    st.dataframe(compliance_df, use_container_width=True)

    # Visualisasi Compliance Rate per Puskesmas
    st.subheader("📊 Visualisasi Compliance Rate per Puskesmas")
    compliance_df["Compliance Rate (%)"] = compliance_df["Compliance Rate (%)"].str.rstrip('%').astype(float)
    fig = px.bar(compliance_df, x="Puskesmas", y="Compliance Rate (%)",
                 text="Compliance Rate (%)", title="📊 Compliance Rate per Puskesmas", color_discrete_sequence=["#00C49F"])
    fig.update_traces(textposition='outside')
    fig.update_layout(xaxis_tickangle=-45, yaxis_title="Compliance Rate (%)", xaxis_title="Puskesmas", yaxis_range=[0, 110], title_x=0.5, height=500)
    st.plotly_chart(fig, key=f"compliance_chart_{bulan_filter}_{puskesmas_filter}_{kelurahan_filter}_{time.time()}", use_container_width=True)

    # Breakdown per Kelurahan jika Puskesmas difilter
    if puskesmas_filter != "All":
        st.subheader(f"📊 Breakdown Compliance Rate di {puskesmas_filter}")
        kelurahan_data = [{"Kelurahan": kel, "Status Laporan": "✅ Lapor" if kel in desa_terlapor else "❌ Tidak Lapor"}
                         for kel in desa_df[desa_df['Puskesmas'] == puskesmas_filter]['Kelurahan'].unique()]
        kelurahan_df = pd.DataFrame(kelurahan_data)
        st.dataframe(kelurahan_df, use_container_width=True)

        fig_kelurahan = px.bar(kelurahan_df, x="Kelurahan", y=kelurahan_df['Status Laporan'].apply(lambda x: 100 if x == "✅ Lapor" else 0),
                              text="Status Laporan", title=f"Compliance Rate di Level Kelurahan - {puskesmas_filter}", color_discrete_sequence=["#FFB347"])
        fig_kelurahan.update_traces(textposition='outside')
        fig_kelurahan.update_layout(xaxis_tickangle=-45, yaxis_title="Compliance Rate (%)", yaxis_range=[0, 110], title_x=0.5, height=500)
        st.plotly_chart(fig_kelurahan, key=f"compliance_breakdown_{puskesmas_filter}_{time.time()}", use_container_width=True)

# ----------------------------- #
# 📋 Completeness Rate
# ----------------------------- #
def completeness_rate(filtered_df, desa_df, bulan_filter, puskesmas_filter, kelurahan_filter):
    """Menghitung dan menampilkan tingkat kelengkapan data untuk data ibu hamil."""
    st.header("📋 Completeness Rate")
    # Tambahkan info dengan tone akademik, rendering rumus, penjelasan untuk orang awam, dan background biru muda
    with st.expander("📜 Definisi dan Insight Analisis Kelengkapan Laporan Data", expanded=False):
        # Satukan seluruh konten dalam satu markdown dengan div untuk background
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Analisis Indikator

            Berikut adalah definisi operasional, rumus perhitungan, serta analisis insight dari indikator-indikator yang digunakan untuk memantau kelengkapan dan kepatuhan pelaporan data ibu hamil dalam sistem kesehatan masyarakat. Rumus disajikan dalam format matematis untuk kejelasan, dengan penjelasan sederhana untuk memudahkan pemahaman.

            #### 1. Compliance Rate
            - **Definisi Operasional:** Persentase desa atau kelurahan yang telah melaporkan data ibu hamil secara lengkap dalam suatu periode tertentu di wilayah kerja tertentu, dibandingkan dengan total desa atau kelurahan yang seharusnya melapor.  
            - **Rumus Perhitungan:**  
            $$ \\text{Compliance Rate (\\%)} = \\frac{\\text{Jumlah Desa/Kelurahan yang Melapor}}{\\text{Jumlah Total Desa/Kelurahan}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase desa atau kelurahan yang sudah mengirimkan laporan dibandingkan dengan semua desa atau kelurahan yang diharapkan melapor, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan secara bulanan dari basis data puskesmas dan desa melalui sistem pelaporan elektronik atau manual, dengan verifikasi terhadap keberadaan laporan dari setiap kelurahan.  
            - **Insight Analisis:** Tingkat kepatuhan pelaporan yang rendah (di bawah 80%) dapat mengindikasikan adanya hambatan logistik, kurangnya pelatihan petugas, atau akses terbatas ke teknologi pelaporan. Persentase ini penting untuk memastikan kualitas data yang digunakan dalam pengambilan keputusan kebijakan kesehatan. Intervensi yang disarankan meliputi pelatihan rutin untuk petugas kesehatan dan peningkatan infrastruktur teknologi informasi.

            #### 2. Completeness Rate
            - **Definisi Operasional:** Persentase entri data ibu hamil yang memiliki semua kolom kunci terisi secara lengkap dalam suatu periode tertentu di wilayah kerja tertentu, dibandingkan dengan total entri data yang ada.  
            - **Rumus Perhitungan:**  
            $$ \\text{Completeness Rate (\\%)} = \\frac{\\text{Jumlah Entri Data Lengkap}}{\\text{Jumlah Total Entri Data}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase data yang sudah terisi penuh untuk semua kolom penting (seperti jumlah ibu hamil yang diperiksa atau mendapat suplementasi) dibandingkan dengan semua data yang dicatat, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui formulir pelaporan bulanan dari puskesmas, dengan validasi otomatis untuk memastikan semua kolom kunci (misalnya, Jumlah_ibu_hamil_periksa_Hb, Anemia_ringan, dll.) terisi.  
            - **Insight Analisis:** Tingkat kelengkapan data yang rendah (di bawah 90%) dapat mengindikasikan kesalahan pengisian, kurangnya pengawasan, atau kurangnya pemahaman petugas terhadap pentingnya data lengkap. Data yang tidak lengkap dapat menyulitkan analisis epidemiologi dan perencanaan intervensi kesehatan. Peningkatan pelatihan data entry dan penggunaan sistem validasi real-time dapat meningkatkan angka ini.

            </div>
        """, unsafe_allow_html=True)

    # Daftar kolom kunci untuk cek kelengkapan
    completeness_columns = [
        "Jumlah_ibu_hamil_periksa_Hb",
        "Anemia_ringan",
        "Anemia_sedang",
        "Anemia_berat",
        "Jumlah_ibu_hamil_anemia",
        "Jumlah_ibu_hamil_anemia_yang_mendapat_TTD_oral",
        "Jumlah_ibu_hamil_anemia_sedang_dan_berat_yang_mendapatkan_tata_laksana_di_tingkat_lanjutan",
        "Jumlah_Sasaran_Ibu_Hamil",
        "Jumlah_ibu_hamil_mendapat_minimal_180_tablet_MMS",
        "Jumlah_ibu_hamil_mendapat_minimal_180_tablet_TTD",
        "Jumlah_ibu_hamil_mengonsumsi_minimal_180_tablet_MMS",
        "Jumlah_ibu_hamil_mengonsumsi_minimal_180_tablet_TTD",
        "Jumlah_ibu_hamil_diukur_LILA_IMT",
        "Jumlah_ibu_hamil_risiko_KEK",
        "Jumlah_ibu_hamil_KEK_mendapat_tambahan_asupan_gizi",
        "Jumlah_ibu_hamil_KEK_mengonsumsi_tambahan_asupan_gizi"
    ]

    # Cek kolom yang hilang di dataset
    missing_cols = [col for col in completeness_columns if col not in filtered_df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di dataset: {missing_cols}")
        return

    # Tambahkan kolom 'Lengkap' untuk mengecek apakah semua kolom kunci terisi
    filtered_df['Lengkap'] = filtered_df[completeness_columns].notna().all(axis=1)

    # Tentukan scope berdasarkan filter
    scope = filtered_df.copy()
    if bulan_filter != "All":
        scope = scope[scope['Bulan'] == int(bulan_filter)] if 'Bulan' in scope.columns and scope['Bulan'].dtype in [int, float, str] else scope
    if puskesmas_filter != "All":
        scope = scope[scope['Puskesmas'] == puskesmas_filter]
    if kelurahan_filter != "All":
        scope = scope[scope['Kelurahan'] == kelurahan_filter]

    # Hitung completeness rate
    lengkap_count = scope['Lengkap'].sum()
    total_entries = scope.shape[0]
    completeness_value = (lengkap_count / total_entries * 100) if total_entries else 0

    st.metric(label="Completeness Rate (%)", value=f"{completeness_value:.2f}%",
              help="Persentase entri dengan semua kolom kunci terisi lengkap.")

    # Tabel Completeness Rate per Puskesmas
    completeness_data = []
    for puskesmas in sorted(desa_df['Puskesmas'].unique()):
        df_pkm = filtered_df[filtered_df['Puskesmas'] == puskesmas]
        if bulan_filter != "All" and 'Bulan' in df_pkm.columns and df_pkm['Bulan'].dtype in [int, float, str]:
            df_pkm = df_pkm[df_pkm['Bulan'] == int(bulan_filter)]
        total_entries_pkm = df_pkm.shape[0]
        lengkap_entries_pkm = df_pkm['Lengkap'].sum()
        rate = (lengkap_entries_pkm / total_entries_pkm * 100) if total_entries_pkm else 0
        completeness_data.append({
            "Puskesmas": puskesmas,
            "Jumlah Entri": total_entries_pkm,
            "Entri Lengkap": lengkap_entries_pkm,
            "Completeness Rate (%)": f"{rate:.2f}%"
        })

    completeness_df = pd.DataFrame(completeness_data)
    st.subheader("📊 Tabel Completeness Rate per Puskesmas")
    st.dataframe(completeness_df, use_container_width=True)

    # Visualisasi Completeness Rate
    st.subheader("📈 Visualisasi Completeness Rate per Puskesmas")
    completeness_df["Completeness Rate (%)"] = completeness_df["Completeness Rate (%)"].str.rstrip('%').astype(float)
    fig_completeness = px.bar(completeness_df, x="Puskesmas", y="Completeness Rate (%)", 
                             text=completeness_df["Completeness Rate (%)"].apply(lambda x: f"{x:.2f}%"),
                             title="📊 Completeness Rate per Puskesmas", 
                             color_discrete_sequence=["#FF6F61"])
    fig_completeness.update_traces(textposition='outside')
    fig_completeness.update_layout(xaxis_tickangle=-45, yaxis_title="Completeness Rate (%)", 
                                  xaxis_title="Puskesmas", yaxis_range=[0, 110], 
                                  title_x=0.5, height=500)
    st.plotly_chart(fig_completeness, key=f"completeness_chart_{bulan_filter}_{puskesmas_filter}_{kelurahan_filter}_{time.time()}", 
                    use_container_width=True)

    # Detail kelengkapan per kolom (opsional)
    if st.checkbox("🔍 Tampilkan Detail Kelengkapan per Kolom"):
        completeness_per_col = filtered_df[completeness_columns].notna().mean() * 100
        st.subheader("📋 Persentase Kelengkapan per Kolom")
        col_data = [{"Kolom": col, "Kelengkapan (%)": f"{val:.2f}%"} 
                   for col, val in completeness_per_col.items()]
        st.dataframe(pd.DataFrame(col_data), use_container_width=True)

# ----------------------------- #
# 🩺 Cakupan Layanan Kesehatan Ibu Hamil Anemia
# ----------------------------- #
def cakupan_layanan_anemia_ibu_hamil(filtered_df, desa_df, periode_filter, puskesmas_filter, kelurahan_filter, periode_type="Bulan"):
    """Menampilkan analisis Cakupan Layanan Kesehatan Ibu Hamil Anemia dengan fitur download laporan."""
    st.header("🩺 Cakupan Layanan Kesehatan Ibu Hamil Anemia")

    # Informasi definisi operasional (tetap sama, disingkat untuk fokus pada logika)
    with st.expander("📜 Definisi Operasional dan Insight Analisis", expanded=False):
        st.markdown("""
            ### 📜 Definisi Operasional dan Analisis Indikator

            Berikut adalah definisi operasional, rumus perhitungan, serta analisis insight dari indikator-indikator yang digunakan untuk memantau cakupan layanan kesehatan ibu hamil dengan anemia. Rumus disajikan dalam format matematis untuk kejelasan, dengan penjelasan sederhana untuk memudahkan pemahaman.

            #### Definisi Anemia Berdasarkan Kadar Hemoglobin (Hb)
            - **Anemia Ringan:** Kadar hemoglobin (Hb) antara 10 hingga 10.9 g/dL.  
            - **Anemia Sedang:** Kadar hemoglobin (Hb) antara 7 hingga 9.9 g/dL.  
            - **Anemia Berat:** Kadar hemoglobin (Hb) kurang dari 7 g/dL.  

            #### 1. Metrik Prevalensi Ibu Hamil Anemia Ringan
            - **Definisi Operasional:** Persentase ibu hamil dengan kadar hemoglobin (Hb) 10–10.9 g/dL dari total ibu hamil yang diperiksa kadar hemoglobinnya dalam suatu periode tertentu di wilayah kerja tertentu.  
            - **Rumus Perhitungan:**  
            $$ \\text{Prevalensi Anemia Ringan (\\%)} = \\frac{\\text{Jumlah Ibu Hamil dengan Anemia Ringan}}{\\text{Jumlah Ibu Hamil yang Diperiksa Hb}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase ibu hamil yang memiliki anemia ringan dari semua ibu hamil yang diperiksa kadar Hb-nya, lalu dikalikan 100 untuk mendapatkan persentase.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui pemeriksaan laboratorium kadar Hb ibu hamil di puskesmas atau fasilitas kesehatan primer lainnya, yang kemudian dilaporkan secara bulanan ke dalam sistem pelaporan kesehatan.  

            #### 2. Metrik Prevalensi Ibu Hamil Anemia Sedang
            - **Definisi Operasional:** Persentase ibu hamil dengan kadar hemoglobin (Hb) 7–9.9 g/dL dari total ibu hamil yang diperiksa kadar hemoglobinnya dalam suatu periode tertentu di wilayah kerja tertentu.  
            - **Rumus Perhitungan:**  
            $$ \\text{Prevalensi Anemia Sedang (\\%)} = \\frac{\\text{Jumlah Ibu Hamil dengan Anemia Sedang}}{\\text{Jumlah Ibu Hamil yang Diperiksa Hb}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase ibu hamil yang memiliki anemia sedang dari semua ibu hamil yang diperiksa kadar Hb-nya, lalu dikalikan 100 untuk mendapatkan persentase.  
            - **Metode Pengumpulan Data:** Sama seperti anemia ringan, data diperoleh dari pemeriksaan laboratorium kadar Hb ibu hamil yang dilaporkan secara berkala.  

            #### 3. Metrik Prevalensi Ibu Hamil Anemia Berat
            - **Definisi Operasional:** Persentase ibu hamil dengan kadar hemoglobin (Hb) kurang dari 7 g/dL dari total ibu hamil yang diperiksa kadar hemoglobinnya dalam suatu periode tertentu di wilayah kerja tertentu.  
            - **Rumus Perhitungan:**  
            $$ \\text{Prevalensi Anemia Berat (\\%)} = \\frac{\\text{Jumlah Ibu Hamil dengan Anemia Berat}}{\\text{Jumlah Ibu Hamil yang Diperiksa Hb}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase ibu hamil yang memiliki anemia berat dari semua ibu hamil yang diperiksa kadar Hb-nya, lalu dikalikan 100 untuk mendapatkan persentase.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui pemeriksaan laboratorium kadar Hb ibu hamil, dengan fokus pada kasus anemia berat yang memerlukan penanganan segera.  

            #### 4. Metrik Prevalensi Ibu Hamil Anemia
            - **Definisi Operasional:** Persentase ibu hamil yang mengalami anemia (Hb < 11 g/dL) dari total ibu hamil yang diperiksa kadar hemoglobinnya dalam suatu periode tertentu di wilayah kerja tertentu.  
            - **Rumus Perhitungan:**  
            $$ \\text{Prevalensi Anemia (\\%)} = \\frac{\\text{Jumlah Ibu Hamil dengan Anemia}}{\\text{Jumlah Ibu Hamil yang Diperiksa Hb}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase ibu hamil yang mengalami anemia (termasuk ringan, sedang, dan berat) dari semua ibu hamil yang diperiksa kadar Hb-nya, lalu dikalikan 100 untuk mendapatkan persentase.  
            - **Metode Pengumpulan Data:** Data dihimpun dari hasil pemeriksaan kadar Hb ibu hamil, dengan klasifikasi anemia berdasarkan batasan kadar Hb (< 11 g/dL).  
            - **Target:** Prevalensi anemia ibu hamil ditargetkan di bawah 26%.  

            #### 5. Metrik Ibu Hamil Anemia yang Mendapat TTD Oral
            - **Definisi Operasional:** Persentase ibu hamil dengan anemia yang menerima Tablet Tambah Darah (TTD) secara oral dari total ibu hamil yang diperiksa kadar hemoglobinnya dalam suatu periode tertentu di wilayah kerja tertentu.  
            - **Rumus Perhitungan:**  
            $$ \\text{Cakupan TTD Oral (\\%)} = \\frac{\\text{Jumlah Ibu Hamil Anemia yang Mendapat TTD Oral}}{\\text{Jumlah Ibu Hamil yang Diperiksa Hb}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase ibu hamil yang mendapatkan tablet tambah darah untuk mengatasi anemia dari semua ibu hamil yang diperiksa kadar Hb-nya, lalu dikalikan 100 untuk mendapatkan persentase.  
            - **Metode Pengumpulan Data:** Data dikumpulkan dari laporan distribusi TTD di puskesmas atau posyandu, dengan verifikasi terhadap jumlah ibu hamil anemia yang menerima tablet.  
            - **Target:** Cakupan TTD oral ditargetkan di atas 40%.  

            #### 6. Metrik Ibu Hamil Anemia Sedang dan Berat yang Mendapatkan Tata Laksana di Tingkat Lanjutan
            - **Definisi Operasional:** Persentase ibu hamil dengan anemia sedang dan berat yang mendapatkan penanganan di fasilitas kesehatan tingkat lanjutan (seperti rumah sakit) dari total ibu hamil yang diperiksa kadar hemoglobinnya dalam suatu periode tertentu di wilayah kerja tertentu.  
            - **Rumus Perhitungan:**  
            $$ \\text{Cakupan Tata Laksana Tingkat Lanjutan (\\%)} = \\frac{\\text{Jumlah Ibu Hamil Anemia Sedang dan Berat yang Mendapat Tata Laksana di Tingkat Lanjutan}}{\\text{Jumlah Ibu Hamil yang Diperiksa Hb}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase ibu hamil dengan anemia sedang dan berat yang dirujuk dan ditangani di rumah sakit dari semua ibu hamil yang diperiksa kadar Hb-nya, lalu dikalikan 100 untuk mendapatkan persentase.  
            - **Metode Pengumpulan Data:** Data dikumpulkan dari laporan rujukan puskesmas ke fasilitas kesehatan tingkat lanjutan, dengan verifikasi terhadap jumlah ibu hamil anemia sedang dan berat yang mendapatkan penanganan.  
            - **Target:** Cakupan tata laksana tingkat lanjutan ditargetkan di atas 40%.  

            #### Insight Analisis
            - **Prevalensi Anemia:** Jika prevalensi anemia ibu hamil melebihi target 26%, ini mengindikasikan masalah kesehatan masyarakat yang serius, seperti kekurangan gizi (zat besi, asam folat), infeksi kronis, atau akses terbatas ke layanan kesehatan antenatal. Intervensi yang diperlukan meliputi peningkatan edukasi gizi, distribusi TTD yang lebih merata, dan pemeriksaan Hb yang lebih rutin.  
            - **Cakupan TTD Oral dan Tata Laksana:** Jika cakupan TTD oral atau tata laksana tingkat lanjutan di bawah target 40%, ini dapat disebabkan oleh keterbatasan stok TTD, kurangnya koordinasi rujukan ke fasilitas tingkat lanjutan, atau rendahnya kesadaran ibu hamil untuk memanfaatkan layanan kesehatan. Solusi yang diusulkan meliputi penguatan rantai pasok TTD, pelatihan tenaga kesehatan untuk manajemen anemia, dan edukasi kepada ibu hamil tentang pentingnya penanganan anemia.  
            - **Implikasi Kesehatan:** Anemia pada ibu hamil, terutama yang sedang dan berat, meningkatkan risiko komplikasi kehamilan seperti kelahiran prematur, berat badan lahir rendah, hingga mortalitas maternal. Oleh karena itu, pemantauan indikator ini sangat krusial untuk mendukung pencapaian target Sustainable Development Goals (SDGs) terkait kesehatan ibu dan anak.

            </div>
        """, unsafe_allow_html=True)


    # Daftar kolom yang dibutuhkan
    required_columns = [
        'Jumlah_ibu_hamil_periksa_Hb',
        'Anemia_ringan',
        'Anemia_sedang',
        'Anemia_berat',
        'Jumlah_ibu_hamil_anemia',
        'Jumlah_ibu_hamil_anemia_yang_mendapat_TTD_oral',
        'Jumlah_ibu_hamil_anemia_sedang_dan_berat_yang_mendapatkan_tata_laksana_di_tingkat_lanjutan'
    ]

    # Cek apakah semua kolom ada
    missing_cols = [col for col in required_columns if col not in filtered_df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di dataset: {missing_cols}")
        return

    # Inisialisasi scope
    scope = filtered_df.copy()

    # Terapkan filter periode (Bulan atau Triwulan)
    if periode_type == "Bulan" and periode_filter != "All":
        try:
            bulan_filter_int = int(periode_filter)
            scope = scope[scope['Bulan'] == bulan_filter_int]
        except ValueError:
            st.warning("⚠️ Pilihan bulan tidak valid.")
    elif periode_type == "Triwulan" and periode_filter != "All":
        triwulan_map = {
            "Triwulan 1": [1, 2, 3],
            "Triwulan 2": [4, 5, 6],
            "Triwulan 3": [7, 8, 9],
            "Triwulan 4": [10, 11, 12]
        }
        bulan_triwulan = triwulan_map.get(periode_filter, [])
        if bulan_triwulan:
            scope = scope[scope['Bulan'].isin(bulan_triwulan)]

    # Terapkan filter Puskesmas dan Kelurahan
    if puskesmas_filter != "All":
        scope = scope[scope['Puskesmas'] == puskesmas_filter]
    if kelurahan_filter != "All":
        scope = scope[scope['Kelurahan'] == kelurahan_filter]

    # Agregasi data berdasarkan periode
    group_cols = ['Puskesmas']
    if puskesmas_filter != "All":
        group_cols.append('Kelurahan')
    if periode_type == "Triwulan" and periode_filter != "All":
        scope = scope.groupby(group_cols).sum(numeric_only=True).reset_index()
    elif periode_type == "Bulan" and periode_filter != "All":
        scope = scope.groupby(group_cols).sum(numeric_only=True).reset_index()

    # Hitung total ibu hamil yang diperiksa Hb
    total_ibu_hamil = scope['Jumlah_ibu_hamil_periksa_Hb'].sum()
    if total_ibu_hamil == 0:
        st.warning("⚠️ Tidak ada data ibu hamil yang diperiksa Hb untuk filter ini.")
        return

    # Hitung total untuk metrik baru
    total_anemia_ringan = scope['Anemia_ringan'].sum()
    total_anemia_sedang = scope['Anemia_sedang'].sum()
    total_anemia_berat = scope['Anemia_berat'].sum()
    total_ibu_hamil_anemia = scope['Jumlah_ibu_hamil_anemia'].sum()
    total_ttd_oral = scope['Jumlah_ibu_hamil_anemia_yang_mendapat_TTD_oral'].sum()
    total_tata_laksana = scope['Jumlah_ibu_hamil_anemia_sedang_dan_berat_yang_mendapatkan_tata_laksana_di_tingkat_lanjutan'].sum()
    total_anemia_sedang_berat = total_anemia_sedang + total_anemia_berat

    # Hitung metrik dengan formula baru
    metrik_data = {
        "Metrik Prevalensi Ibu Hamil Anemia Ringan (%)": (total_anemia_ringan / total_ibu_hamil * 100) if total_ibu_hamil > 0 else 0,
        "Metrik Prevalensi Ibu Hamil Anemia Sedang (%)": (total_anemia_sedang / total_ibu_hamil * 100) if total_ibu_hamil > 0 else 0,
        "Metrik Prevalensi Ibu Hamil Anemia Berat (%)": (total_anemia_berat / total_ibu_hamil * 100) if total_ibu_hamil > 0 else 0,
        "Metrik Prevalensi Ibu Hamil Anemia (%)": (total_ibu_hamil_anemia / total_ibu_hamil * 100) if total_ibu_hamil > 0 else 0,
        "Metrik Ibu Hamil Anemia Ringan yang Mendapat TTD Oral (%)": (total_anemia_ringan / total_ttd_oral * 100) if total_ttd_oral > 0 else 0,
        "Metrik Ibu Hamil Anemia Sedang dan Berat yang Mendapatkan Tata Laksana di Tingkat Lanjutan (%)": (total_tata_laksana / total_anemia_sedang_berat * 100) if total_anemia_sedang_berat > 0 else 0
    }

    # Target (tetap sama)
    targets = {
        "Metrik Prevalensi Ibu Hamil Anemia (%)": 26,
        "Metrik Ibu Hamil Anemia Ringan yang Mendapat TTD Oral (%)": 40,
        "Metrik Ibu Hamil Anemia Sedang dan Berat yang Mendapatkan Tata Laksana di Tingkat Lanjutan (%)": 40
    }

    # 1. Metrik Score Card
    st.subheader("📊 Metrik Cakupan Layanan Kesehatan Ibu Hamil Anemia")
    metrik_list = list(metrik_data.items())
    cols1 = st.columns(2)
    for i in range(2):
        for j in range(3):
            idx = i * 3 + j
            if idx >= len(metrik_list):
                break
            label, value = metrik_list[idx]
            target = targets.get(label)
            if target is not None:
                gap = abs(value - target)
                if label == "Metrik Prevalensi Ibu Hamil Anemia (%)":
                    if value <= 26:
                        delta_str = f"Dibawah Target (gap: {gap:.2f}%)"
                        delta_color = "normal"
                        delta_arrow = "↓"
                    else:
                        delta_str = f"Diatas Target (gap: {gap:.2f}%)"
                        delta_color = "inverse"
                        delta_arrow = "↑"
                else:
                    if value >= 40:
                        delta_str = f"Diatas Target (gap: {gap:.2f}%)"
                        delta_color = "normal"
                        delta_arrow = "↑"
                    else:
                        delta_str = f"Dibawah Target (gap: {gap:.2f}%)"
                        delta_color = "inverse"
                        delta_arrow = "↓"
                cols1[i].metric(label=label, value=f"{value:.2f}%", delta=f"{delta_str} {delta_arrow}", delta_color=delta_color)
            else:
                cols1[i].metric(label=label, value=f"{value:.2f}%")

    # 2. Grafik Visualisasi
    # Grafik 1: Prevalensi Anemia
    st.subheader("📈 Grafik Prevalensi Anemia Ibu Hamil")
    if puskesmas_filter == "All":
        grouped_df = scope.groupby('Puskesmas').sum(numeric_only=True).reset_index()
        graph_data = pd.DataFrame({
            "Puskesmas": grouped_df['Puskesmas'],
            "Metrik Prevalensi Ibu Hamil Anemia Ringan (%)": (grouped_df['Anemia_ringan'] / grouped_df['Jumlah_ibu_hamil_periksa_Hb'] * 100).fillna(0),
            "Metrik Prevalensi Ibu Hamil Anemia Sedang (%)": (grouped_df['Anemia_sedang'] / grouped_df['Jumlah_ibu_hamil_periksa_Hb'] * 100).fillna(0),
            "Metrik Prevalensi Ibu Hamil Anemia Berat (%)": (grouped_df['Anemia_berat'] / grouped_df['Jumlah_ibu_hamil_periksa_Hb'] * 100).fillna(0),
            "Metrik Prevalensi Ibu Hamil Anemia (%)": (grouped_df['Jumlah_ibu_hamil_anemia'] / grouped_df['Jumlah_ibu_hamil_periksa_Hb'] * 100).fillna(0)
        }).melt(id_vars=["Puskesmas"], var_name="Indikator", value_name="Persentase")
        fig1 = px.bar(graph_data, x="Puskesmas", y="Persentase", color="Indikator", barmode="group",
                      title="Prevalensi Anemia Ibu Hamil per Puskesmas", text=graph_data["Persentase"].apply(lambda x: f"{x:.1f}%"))
    else:
        grouped_df = scope.groupby('Kelurahan').sum(numeric_only=True).reset_index()
        graph_data = pd.DataFrame({
            "Kelurahan": grouped_df['Kelurahan'],
            "Metrik Prevalensi Ibu Hamil Anemia Ringan (%)": (grouped_df['Anemia_ringan'] / grouped_df['Jumlah_ibu_hamil_periksa_Hb'] * 100).fillna(0),
            "Metrik Prevalensi Ibu Hamil Anemia Sedang (%)": (grouped_df['Anemia_sedang'] / grouped_df['Jumlah_ibu_hamil_periksa_Hb'] * 100).fillna(0),
            "Metrik Prevalensi Ibu Hamil Anemia Berat (%)": (grouped_df['Anemia_berat'] / grouped_df['Jumlah_ibu_hamil_periksa_Hb'] * 100).fillna(0),
            "Metrik Prevalensi Ibu Hamil Anemia (%)": (grouped_df['Jumlah_ibu_hamil_anemia'] / grouped_df['Jumlah_ibu_hamil_periksa_Hb'] * 100).fillna(0)
        }).melt(id_vars=["Kelurahan"], var_name="Indikator", value_name="Persentase")
        fig1 = px.bar(graph_data, x="Kelurahan", y="Persentase", color="Indikator", barmode="group",
                      title=f"Prevalensi Anemia Ibu Hamil per Kelurahan di {puskesmas_filter}", text=graph_data["Persentase"].apply(lambda x: f"{x:.1f}%"))

    fig1.add_hline(y=26, line_dash="dash", line_color="red", annotation_text="Target Prevalensi Anemia (26%)", annotation_position="top right")
    fig1.update_traces(textposition='outside')
    fig1.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", yaxis_range=[0, 100], title_x=0.5,
                       legend_title_text="Indikator", legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5),
                       height=500)
    st.plotly_chart(fig1, use_container_width=True)

    # Grafik 2: Cakupan Layanan Anemia
    st.subheader("📈 Grafik Cakupan Layanan Ibu Hamil Anemia")
    if puskesmas_filter == "All":
        grouped_df = scope.groupby('Puskesmas').sum(numeric_only=True).reset_index()
        graph_data2 = pd.DataFrame({
            "Puskesmas": grouped_df['Puskesmas'],
            "Metrik Ibu Hamil Anemia Ringan yang Mendapat TTD Oral (%)": (grouped_df['Anemia_ringan'] / grouped_df['Jumlah_ibu_hamil_anemia_yang_mendapat_TTD_oral'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0),
            "Metrik Ibu Hamil Anemia Sedang dan Berat yang Mendapatkan Tata Laksana di Tingkat Lanjutan (%)": (grouped_df['Jumlah_ibu_hamil_anemia_sedang_dan_berat_yang_mendapatkan_tata_laksana_di_tingkat_lanjutan'] / (grouped_df['Anemia_sedang'] + grouped_df['Anemia_berat']) * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
        }).melt(id_vars=["Puskesmas"], var_name="Indikator", value_name="Persentase")
        fig2 = px.bar(graph_data2, x="Puskesmas", y="Persentase", color="Indikator", barmode="group",
                      title="Cakupan Layanan Ibu Hamil Anemia per Puskesmas", text=graph_data2["Persentase"].apply(lambda x: f"{x:.1f}%"))
    else:
        grouped_df = scope.groupby('Kelurahan').sum(numeric_only=True).reset_index()
        graph_data2 = pd.DataFrame({
            "Kelurahan": grouped_df['Kelurahan'],
            "Metrik Ibu Hamil Anemia Ringan yang Mendapat TTD Oral (%)": (grouped_df['Anemia_ringan'] / grouped_df['Jumlah_ibu_hamil_anemia_yang_mendapat_TTD_oral'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0),
            "Metrik Ibu Hamil Anemia Sedang dan Berat yang Mendapatkan Tata Laksana di Tingkat Lanjutan (%)": (grouped_df['Jumlah_ibu_hamil_anemia_sedang_dan_berat_yang_mendapatkan_tata_laksana_di_tingkat_lanjutan'] / (grouped_df['Anemia_sedang'] + grouped_df['Anemia_berat']) * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
        }).melt(id_vars=["Kelurahan"], var_name="Indikator", value_name="Persentase")
        fig2 = px.bar(graph_data2, x="Kelurahan", y="Persentase", color="Indikator", barmode="group",
                      title=f"Cakupan Layanan Ibu Hamil Anemia per Kelurahan di {puskesmas_filter}", text=graph_data2["Persentase"].apply(lambda x: f"{x:.1f}%"))

    fig2.add_hline(y=40, line_dash="dash", line_color="red", annotation_text="Target Layanan Anemia (40%)", annotation_position="top right")
    fig2.update_traces(textposition='outside')
    fig2.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", yaxis_range=[0, 100], title_x=0.5,
                       legend_title_text="Indikator", legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5),
                       height=500)
    st.plotly_chart(fig2, use_container_width=True)

    # 3. Tabel Rekapitulasi
    st.subheader("📋 Tabel Rekapitulasi Cakupan Layanan Kesehatan Ibu Hamil Anemia")
    recap_df = scope.copy()
    recap_df['Metrik Prevalensi Ibu Hamil Anemia Ringan (%)'] = (recap_df['Anemia_ringan'] / recap_df['Jumlah_ibu_hamil_periksa_Hb'] * 100).fillna(0).round(2)
    recap_df['Metrik Prevalensi Ibu Hamil Anemia Sedang (%)'] = (recap_df['Anemia_sedang'] / recap_df['Jumlah_ibu_hamil_periksa_Hb'] * 100).fillna(0).round(2)
    recap_df['Metrik Prevalensi Ibu Hamil Anemia Berat (%)'] = (recap_df['Anemia_berat'] / recap_df['Jumlah_ibu_hamil_periksa_Hb'] * 100).fillna(0).round(2)
    recap_df['Metrik Prevalensi Ibu Hamil Anemia (%)'] = (recap_df['Jumlah_ibu_hamil_anemia'] / recap_df['Jumlah_ibu_hamil_periksa_Hb'] * 100).fillna(0).round(2)
    recap_df['Metrik Ibu Hamil Anemia Ringan yang Mendapat TTD Oral (%)'] = (recap_df['Anemia_ringan'] / recap_df['Jumlah_ibu_hamil_anemia_yang_mendapat_TTD_oral'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0).round(2)
    recap_df['Metrik Ibu Hamil Anemia Sedang dan Berat yang Mendapatkan Tata Laksana di Tingkat Lanjutan (%)'] = (recap_df['Jumlah_ibu_hamil_anemia_sedang_dan_berat_yang_mendapatkan_tata_laksana_di_tingkat_lanjutan'] / (recap_df['Anemia_sedang'] + recap_df['Anemia_berat']) * 100).replace([float('inf'), -float('inf')], 0).fillna(0).round(2)

    recap_display = recap_df[['Puskesmas', 'Kelurahan'] + list(metrik_data.keys())] if puskesmas_filter != "All" else recap_df[['Puskesmas'] + list(metrik_data.keys())]
    recap_display.insert(0, 'No', range(1, len(recap_display) + 1))
    st.dataframe(recap_display, use_container_width=True)

    # 4. Fitur Download Laporan PDF (tetap sama)
    st.subheader("📥 Unduh Laporan")
    def generate_pdf_report():
        img_buffer1 = BytesIO()
        img_buffer2 = BytesIO()
        fig1.write_image(img_buffer1, format='png', width=600, height=400, scale=2)
        fig2.write_image(img_buffer2, format='png', width=600, height=400, scale=2)
        img_buffer1.seek(0)
        img_buffer2.seek(0)
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        normal_style = styles['Normal']
        normal_style.textColor = colors.black
        elements.append(Paragraph("Laporan Cakupan Layanan Kesehatan Ibu Hamil Anemia", title_style))
        elements.append(Paragraph(f"Diperbarui: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("1. Metrik Cakupan Layanan", normal_style))
        metric_data = []
        for label, value in metrik_list:
            target = targets.get(label)
            if target is not None:
                gap = abs(value - target)
                if label == "Metrik Prevalensi Ibu Hamil Anemia (%)":
                    delta_str = f"Dibawah Target (gap: {gap:.2f}%)" if value <= 26 else f"Diatas Target (gap: {gap:.2f}%)"
                    delta_color = colors.green if value <= 26 else colors.red
                    delta_arrow = "↓" if value <= 26 else "↑"
                else:
                    delta_str = f"Diatas Target (gap: {gap:.2f}%)" if value >= 40 else f"Dibawah Target (gap: {gap:.2f}%)"
                    delta_color = colors.green if value >= 40 else colors.red
                    delta_arrow = "↑" if value >= 40 else "↓"
                metric_data.append([f"{label}: {value:.2f}%", f"({delta_str} {delta_arrow})", ""])
                metric_data[-1][2] = Paragraph(metric_data[-1][1], style=ParagraphStyle(name='Custom', textColor=delta_color))
            else:
                metric_data.append([f"{label}: {value:.2f}%", "", ""])
        metric_table = Table(metric_data, colWidths=[300, 150, 50])
        metric_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(metric_table)
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("2. Grafik Prevalensi Anemia Ibu Hamil", normal_style))
        elements.append(Image(img_buffer1, width=500, height=300))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("3. Grafik Cakupan Layanan Ibu Hamil Anemia", normal_style))
        elements.append(Image(img_buffer2, width=500, height=300))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("4. Tabel Rekapitulasi", normal_style))
        table_data = [recap_display.columns.tolist()] + recap_display.values.tolist()
        recap_table = Table(table_data)
        recap_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(recap_table)
        doc.build(elements)
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()

    if st.button("Download Laporan PDF"):
        st.warning("Membuat laporan PDF, harap tunggu...")
        pdf_data = generate_pdf_report()
        st.success("Laporan PDF siap diunduh!")
        st.download_button(
            label="Download Laporan PDF",
            data=pdf_data,
            file_name=f"Laporan_Cakupan_Anemia_Ibu_Hamil_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )

# ----------------------------- #
# 📈 Cakupan Suplementasi Gizi Ibu Hamil (Perbaikan)
# ----------------------------- #
def cakupan_suplementasi_gizi_ibu_hamil(filtered_df, desa_df, periode_filter, puskesmas_filter, kelurahan_filter, periode_type="Bulan"):
    """Menampilkan analisis Cakupan Suplementasi Gizi Ibu Hamil dengan fitur download laporan."""
    st.header("💊 Cakupan Suplementasi Gizi Ibu Hamil")

    # Tambahkan informasi definisi operasional dan insight analisis
    with st.expander("📜 Definisi Operasional dan Insight Analisis Cakupan Suplementasi Gizi Ibu Hamil", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Analisis Indikator

            Berikut adalah definisi operasional, rumus perhitungan, serta analisis insight dari indikator-indikator yang digunakan untuk memantau cakupan suplementasi gizi ibu hamil dalam bentuk tablet tambah darah (TTD) dan Multiple Micronutrient Supplementation (MMS). Rumus disajikan dalam format matematis untuk kejelasan, dengan penjelasan sederhana untuk memudahkan pemahaman.

            #### Apa itu MMS (Multiple Micronutrient Supplementation)?
            - **Definisi:** Multiple Micronutrient Supplementation (MMS) adalah suplementasi gizi yang mengandung kombinasi mikronutrien esensial, seperti zat besi, asam folat, vitamin A, vitamin D, vitamin E, vitamin B kompleks, seng, yodium, dan kalsium, yang dirancang untuk memenuhi kebutuhan gizi ibu hamil. MMS diberikan dalam bentuk tablet yang dikonsumsi secara rutin untuk mencegah defisiensi mikronutrien selama kehamilan.  
            - **Tujuan:** MMS bertujuan untuk mengurangi risiko anemia, kelahiran prematur, berat badan lahir rendah, serta meningkatkan kesehatan ibu dan janin. Berbeda dengan tablet tambah darah (TTD) yang terutama berfokus pada zat besi dan asam folat untuk mencegah anemia, MMS memberikan spektrum mikronutrien yang lebih luas untuk mendukung perkembangan janin dan kesejahteraan ibu.  
            - **Standar Pemberian:** Berdasarkan pedoman kesehatan, ibu hamil dianjurkan untuk menerima dan mengonsumsi minimal 180 tablet MMS selama satu tahun di suatu wilayah kerja (pelaporan secara kumulatif setiap bulannya), guna memastikan asupan gizi yang optimal sepanjang kehamilan.  

            #### 1. Metrik Ibu Hamil Mendapat Minimal 180 Tablet MMS
            - **Definisi Operasional:** Persentase ibu hamil yang menerima minimal 180 tablet MMS dari total sasaran ibu hamil dalam suatu periode tertentu di wilayah kerja tertentu.  
            - **Rumus Perhitungan:**  
            $$ \\text{Cakupan Mendapat MMS (\\%)} = \\frac{\\text{Jumlah Ibu Hamil Mendapat Minimal 180 Tablet MMS}}{\\text{Jumlah Sasaran Ibu Hamil}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase ibu hamil yang telah diberikan minimal 180 tablet MMS dari total ibu hamil yang menjadi sasaran program, lalu dikalikan 100 untuk mendapatkan persentase.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui laporan distribusi MMS di puskesmas, posyandu, atau fasilitas kesehatan primer lainnya, dengan verifikasi terhadap jumlah tablet yang diberikan kepada ibu hamil.  
            - **Target:** Cakupan penerimaan MMS ditargetkan mencapai 90%.  

            #### 2. Metrik Ibu Hamil Mendapat Minimal 180 Tablet TTD
            - **Definisi Operasional:** Persentase ibu hamil yang menerima minimal 180 tablet tambah darah (TTD) dari total sasaran ibu hamil dalam suatu periode tertentu di wilayah kerja tertentu.  
            - **Rumus Perhitungan:**  
            $$ \\text{Cakupan Mendapat TTD (\\%)} = \\frac{\\text{Jumlah Ibu Hamil Mendapat Minimal 180 Tablet TTD}}{\\text{Jumlah Sasaran Ibu Hamil}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase ibu hamil yang telah diberikan minimal 180 tablet TTD dari total ibu hamil yang menjadi sasaran program, lalu dikalikan 100 untuk mendapatkan persentase.  
            - **Metode Pengumpulan Data:** Data dihimpun dari laporan distribusi TTD di puskesmas atau posyandu, dengan verifikasi terhadap jumlah tablet yang diberikan.  
            - **Target:** Cakupan penerimaan TTD ditargetkan mencapai 90%.  

            #### 3. Metrik Ibu Hamil Mengonsumsi Minimal 180 Tablet MMS
            - **Definisi Operasional:** Persentase ibu hamil yang mengonsumsi minimal 180 tablet MMS dari total sasaran ibu hamil dalam suatu periode tertentu di wilayah kerja tertentu.  
            - **Rumus Perhitungan:**  
            $$ \\text{Cakupan Mengonsumsi MMS (\\%)} = \\frac{\\text{Jumlah Ibu Hamil Mengonsumsi Minimal 180 Tablet MMS}}{\\text{Jumlah Sasaran Ibu Hamil}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase ibu hamil yang telah mengonsumsi minimal 180 tablet MMS dari total ibu hamil yang menjadi sasaran program, lalu dikalikan 100 untuk mendapatkan persentase.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui wawancara atau laporan kunjungan petugas kesehatan ke ibu hamil, dengan verifikasi terhadap konsumsi tablet MMS berdasarkan catatan atau pengakuan ibu hamil.  
            - **Target:** Cakupan konsumsi MMS ditargetkan mencapai 48%.  

            #### 4. Metrik Ibu Hamil Mengonsumsi Minimal 180 Tablet TTD
            - **Definisi Operasional:** Persentase ibu hamil yang mengonsumsi minimal 180 tablet tambah darah (TTD) dari total sasaran ibu hamil dalam suatu periode tertentu di wilayah kerja tertentu.  
            - **Rumus Perhitungan:**  
            $$ \\text{Cakupan Mengonsumsi TTD (\\%)} = \\frac{\\text{Jumlah Ibu Hamil Mengonsumsi Minimal 180 Tablet TTD}}{\\text{Jumlah Sasaran Ibu Hamil}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase ibu hamil yang telah mengonsumsi minimal 180 tablet TTD dari total ibu hamil yang menjadi sasaran program, lalu dikalikan 100 untuk mendapatkan persentase.  
            - **Metode Pengumpulan Data:** Data diperoleh melalui wawancara atau laporan kunjungan petugas kesehatan, dengan verifikasi terhadap konsumsi tablet TTD berdasarkan catatan atau pengakuan ibu hamil.  
            - **Target:** Cakupan konsumsi TTD ditargetkan mencapai 48%.  

            #### Insight Analisis
            - **Distribusi Suplementasi (MMS dan TTD):** Jika cakupan penerimaan MMS atau TTD di bawah target 90%, hal ini dapat mengindikasikan adanya masalah dalam rantai pasok, seperti keterlambatan distribusi tablet, stok yang terbatas, atau kurangnya koordinasi antara puskesmas dan posyandu. Intervensi yang diperlukan meliputi penguatan sistem logistik dan pelatihan petugas kesehatan untuk memastikan distribusi yang merata.  
            - **Konsumsi Suplementasi (MMS dan TTD):** Jika cakupan konsumsi MMS atau TTD di bawah target 48%, ini dapat disebabkan oleh rendahnya kesadaran ibu hamil tentang pentingnya suplementasi, efek samping yang dirasakan (seperti mual saat mengonsumsi tablet), atau kurangnya pendampingan dari petugas kesehatan. Solusi yang diusulkan meliputi edukasi intensif kepada ibu hamil, penyediaan panduan konsumsi yang jelas, dan kunjungan rutin oleh kader kesehatan untuk memantau kepatuhan konsumsi.  
            - **Implikasi Kesehatan:** Suplementasi gizi yang tidak memadai selama kehamilan dapat meningkatkan risiko anemia, defisiensi mikronutrien, kelahiran prematur, dan gangguan perkembangan janin. Oleh karena itu, pencapaian target indikator ini sangat penting untuk mendukung kesehatan ibu dan anak, sejalan dengan Sustainable Development Goals (SDGs) terkait pengurangan mortalitas maternal dan neonatal.  

            </div>
        """, unsafe_allow_html=True)

    # Daftar kolom yang dibutuhkan
    required_columns = [
        'Jumlah_Sasaran_Ibu_Hamil',
        'Jumlah_ibu_hamil_mendapat_minimal_180_tablet_MMS',
        'Jumlah_ibu_hamil_mendapat_minimal_180_tablet_TTD',
        'Jumlah_ibu_hamil_mengonsumsi_minimal_180_tablet_MMS',
        'Jumlah_ibu_hamil_mengonsumsi_minimal_180_tablet_TTD'
    ]

    # Cek apakah semua kolom ada
    missing_cols = [col for col in required_columns if col not in filtered_df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di dataset: {missing_cols}. Periksa data di 'data_ibuhamil'!")
        return

    # Inisialisasi scope
    scope = filtered_df.copy()

    # Validasi dan konversi kolom Bulan
    if 'Bulan' in scope.columns:
        scope['Bulan'] = pd.to_numeric(scope['Bulan'], errors='coerce').fillna(0).astype(int)
    else:
        st.error("⚠️ Kolom 'Bulan' tidak ditemukan di dataset!")
        return

    # Terapkan filter periode (Bulan atau Triwulan)
    if periode_type == "Bulan" and periode_filter != "All":
        try:
            bulan_filter_int = int(periode_filter)
            scope = scope[scope['Bulan'] == bulan_filter_int]
        except ValueError:
            st.warning("⚠️ Pilihan bulan tidak valid.")
    elif periode_type == "Triwulan" and periode_filter != "All":
        triwulan_map = {
            "Triwulan 1": [1, 2, 3],
            "Triwulan 2": [4, 5, 6],
            "Triwulan 3": [7, 8, 9],
            "Triwulan 4": [10, 11, 12]
        }
        bulan_triwulan = triwulan_map.get(periode_filter, [])
        if bulan_triwulan:
            scope = scope[scope['Bulan'].isin(bulan_triwulan)]

    # Terapkan filter Puskesmas dan Kelurahan
    if puskesmas_filter != "All":
        scope = scope[scope['Puskesmas'] == puskesmas_filter]
    if kelurahan_filter != "All":
        scope = scope[scope['Kelurahan'] == kelurahan_filter]

    # Agregasi data berdasarkan periode
    group_cols = ['Puskesmas']
    if puskesmas_filter != "All":
        group_cols.append('Kelurahan')
    if periode_type == "Triwulan" and periode_filter != "All":
        scope = scope.groupby(group_cols).sum(numeric_only=True).reset_index()
    elif periode_type == "Bulan" and periode_filter != "All":
        scope = scope.groupby(group_cols).sum(numeric_only=True).reset_index()

    # Hitung total sasaran ibu hamil
    total_sasaran = scope['Jumlah_Sasaran_Ibu_Hamil'].sum()
    if total_sasaran == 0:
        st.warning("⚠️ Tidak ada data sasaran ibu hamil untuk filter ini.")
        return

    # Hitung metrik
    metrik_data = {
        "Metrik Ibu Hamil Mendapat Minimal 180 Tablet MMS (%)": (scope['Jumlah_ibu_hamil_mendapat_minimal_180_tablet_MMS'].sum() / total_sasaran * 100) if total_sasaran > 0 else 0,
        "Metrik Ibu Hamil Mendapat Minimal 180 Tablet TTD (%)": (scope['Jumlah_ibu_hamil_mendapat_minimal_180_tablet_TTD'].sum() / total_sasaran * 100) if total_sasaran > 0 else 0,
        "Metrik Ibu Hamil Mengonsumsi Minimal 180 Tablet MMS (%)": (scope['Jumlah_ibu_hamil_mengonsumsi_minimal_180_tablet_MMS'].sum() / total_sasaran * 100) if total_sasaran > 0 else 0,
        "Metrik Ibu Hamil Mengonsumsi Minimal 180 Tablet TTD (%)": (scope['Jumlah_ibu_hamil_mengonsumsi_minimal_180_tablet_TTD'].sum() / total_sasaran * 100) if total_sasaran > 0 else 0
    }

    # Target
    targets = {
        "Metrik Ibu Hamil Mendapat Minimal 180 Tablet MMS (%)": 90,
        "Metrik Ibu Hamil Mendapat Minimal 180 Tablet TTD (%)": 90,
        "Metrik Ibu Hamil Mengonsumsi Minimal 180 Tablet MMS (%)": 48,
        "Metrik Ibu Hamil Mengonsumsi Minimal 180 Tablet TTD (%)": 48
    }

    # 1. Metrik Score Card
    st.subheader("📊 Metrik Cakupan Suplementasi Gizi Ibu Hamil")
    metrik_list = list(metrik_data.items())
    cols1 = st.columns(2)
    for i in range(2):
        for j in range(2):
            idx = i * 2 + j
            if idx >= len(metrik_list):
                break
            label, value = metrik_list[idx]
            target = targets.get(label)
            if target is not None:
                gap = abs(value - target)
                if value < target:
                    delta_str = f"Dibawah Target (gap: {gap:.2f}%)"
                    delta_color = "inverse"  # Merah
                    delta_arrow = "↓"
                else:
                    delta_str = f"Diatas Target (gap: {gap:.2f}%)"
                    delta_color = "normal"  # Hijau
                    delta_arrow = "↑"
                cols1[i].metric(label=label, value=f"{value:.2f}%", delta=f"{delta_str} {delta_arrow}", delta_color=delta_color)
            else:
                cols1[i].metric(label=label, value=f"{value:.2f}%")

    # 2. Grafik Visualisasi
    # Grafik 1: Cakupan Suplementasi MMS
    st.subheader("📈 Grafik Cakupan Suplementasi MMS Ibu Hamil")
    if puskesmas_filter == "All":
        grouped_df = scope.groupby('Puskesmas').sum(numeric_only=True).reset_index()
        graph_data_mms = pd.DataFrame({
            "Puskesmas": grouped_df['Puskesmas'],
            "Metrik Ibu Hamil Mendapat Minimal 180 Tablet MMS (%)": (grouped_df['Jumlah_ibu_hamil_mendapat_minimal_180_tablet_MMS'] / grouped_df['Jumlah_Sasaran_Ibu_Hamil'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0),
            "Metrik Ibu Hamil Mengonsumsi Minimal 180 Tablet MMS (%)": (grouped_df['Jumlah_ibu_hamil_mengonsumsi_minimal_180_tablet_MMS'] / grouped_df['Jumlah_Sasaran_Ibu_Hamil'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
        }).melt(id_vars=["Puskesmas"], var_name="Indikator", value_name="Persentase")
        fig1 = px.bar(graph_data_mms, x="Puskesmas", y="Persentase", color="Indikator", barmode="group",
                      title="Cakupan Suplementasi MMS Ibu Hamil per Puskesmas", text=graph_data_mms["Persentase"].apply(lambda x: f"{x:.1f}%"))
    else:
        grouped_df = scope.groupby('Kelurahan').sum(numeric_only=True).reset_index()
        graph_data_mms = pd.DataFrame({
            "Kelurahan": grouped_df['Kelurahan'],
            "Metrik Ibu Hamil Mendapat Minimal 180 Tablet MMS (%)": (grouped_df['Jumlah_ibu_hamil_mendapat_minimal_180_tablet_MMS'] / grouped_df['Jumlah_Sasaran_Ibu_Hamil'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0),
            "Metrik Ibu Hamil Mengonsumsi Minimal 180 Tablet MMS (%)": (grouped_df['Jumlah_ibu_hamil_mengonsumsi_minimal_180_tablet_MMS'] / grouped_df['Jumlah_Sasaran_Ibu_Hamil'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
        }).melt(id_vars=["Kelurahan"], var_name="Indikator", value_name="Persentase")
        fig1 = px.bar(graph_data_mms, x="Kelurahan", y="Persentase", color="Indikator", barmode="group",
                      title=f"Cakupan Suplementasi MMS Ibu Hamil per Kelurahan di {puskesmas_filter}", text=graph_data_mms["Persentase"].apply(lambda x: f"{x:.1f}%"))

    # Tambahkan garis target untuk MMS
    colors_mms = px.colors.qualitative.Plotly[:2]  # Ambil 2 warna dari Plotly untuk MMS
    fig1.add_hline(y=90, line_dash="dash", line_color=colors_mms[0], annotation_text="Target Mendapat MMS (90%)", annotation_position="top right")
    fig1.add_hline(y=48, line_dash="dash", line_color=colors_mms[1], annotation_text="Target Mengonsumsi MMS (48%)", annotation_position="top left")
    fig1.update_traces(textposition='outside')
    fig1.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", yaxis_range=[0, 100], title_x=0.5,
                       legend_title_text="Indikator", legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5),
                       height=500)
    st.plotly_chart(fig1, use_container_width=True)

    # Grafik 2: Cakupan Suplementasi TTD
    st.subheader("📈 Grafik Cakupan Suplementasi TTD Ibu Hamil")
    if puskesmas_filter == "All":
        grouped_df = scope.groupby('Puskesmas').sum(numeric_only=True).reset_index()
        graph_data_ttd = pd.DataFrame({
            "Puskesmas": grouped_df['Puskesmas'],
            "Metrik Ibu Hamil Mendapat Minimal 180 Tablet TTD (%)": (grouped_df['Jumlah_ibu_hamil_mendapat_minimal_180_tablet_TTD'] / grouped_df['Jumlah_Sasaran_Ibu_Hamil'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0),
            "Metrik Ibu Hamil Mengonsumsi Minimal 180 Tablet TTD (%)": (grouped_df['Jumlah_ibu_hamil_mengonsumsi_minimal_180_tablet_TTD'] / grouped_df['Jumlah_Sasaran_Ibu_Hamil'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
        }).melt(id_vars=["Puskesmas"], var_name="Indikator", value_name="Persentase")
        fig2 = px.bar(graph_data_ttd, x="Puskesmas", y="Persentase", color="Indikator", barmode="group",
                      title="Cakupan Suplementasi TTD Ibu Hamil per Puskesmas", text=graph_data_ttd["Persentase"].apply(lambda x: f"{x:.1f}%"))
    else:
        grouped_df = scope.groupby('Kelurahan').sum(numeric_only=True).reset_index()
        graph_data_ttd = pd.DataFrame({
            "Kelurahan": grouped_df['Kelurahan'],
            "Metrik Ibu Hamil Mendapat Minimal 180 Tablet TTD (%)": (grouped_df['Jumlah_ibu_hamil_mendapat_minimal_180_tablet_TTD'] / grouped_df['Jumlah_Sasaran_Ibu_Hamil'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0),
            "Metrik Ibu Hamil Mengonsumsi Minimal 180 Tablet TTD (%)": (grouped_df['Jumlah_ibu_hamil_mengonsumsi_minimal_180_tablet_TTD'] / grouped_df['Jumlah_Sasaran_Ibu_Hamil'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
        }).melt(id_vars=["Kelurahan"], var_name="Indikator", value_name="Persentase")
        fig2 = px.bar(graph_data_ttd, x="Kelurahan", y="Persentase", color="Indikator", barmode="group",
                      title=f"Cakupan Suplementasi TTD Ibu Hamil per Kelurahan di {puskesmas_filter}", text=graph_data_ttd["Persentase"].apply(lambda x: f"{x:.1f}%"))

    # Tambahkan garis target untuk TTD
    colors_ttd = px.colors.qualitative.Plotly[2:4]  # Ambil 2 warna berikutnya dari Plotly untuk TTD
    fig2.add_hline(y=90, line_dash="dash", line_color=colors_ttd[0], annotation_text="Target Mendapat TTD (90%)", annotation_position="top right")
    fig2.add_hline(y=48, line_dash="dash", line_color=colors_ttd[1], annotation_text="Target Mengonsumsi TTD (48%)", annotation_position="top left")
    fig2.update_traces(textposition='outside')
    fig2.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", yaxis_range=[0, 100], title_x=0.5,
                       legend_title_text="Indikator", legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5),
                       height=500)
    st.plotly_chart(fig2, use_container_width=True)

    # 3. Tabel Rekapitulasi
    st.subheader("📋 Tabel Rekapitulasi Cakupan Suplementasi Gizi Ibu Hamil")
    recap_df = scope.copy()
    recap_df['Metrik Ibu Hamil Mendapat Minimal 180 Tablet MMS (%)'] = (recap_df['Jumlah_ibu_hamil_mendapat_minimal_180_tablet_MMS'] / recap_df['Jumlah_Sasaran_Ibu_Hamil'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0).round(2)
    recap_df['Metrik Ibu Hamil Mendapat Minimal 180 Tablet TTD (%)'] = (recap_df['Jumlah_ibu_hamil_mendapat_minimal_180_tablet_TTD'] / recap_df['Jumlah_Sasaran_Ibu_Hamil'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0).round(2)
    recap_df['Metrik Ibu Hamil Mengonsumsi Minimal 180 Tablet MMS (%)'] = (recap_df['Jumlah_ibu_hamil_mengonsumsi_minimal_180_tablet_MMS'] / recap_df['Jumlah_Sasaran_Ibu_Hamil'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0).round(2)
    recap_df['Metrik Ibu Hamil Mengonsumsi Minimal 180 Tablet TTD (%)'] = (recap_df['Jumlah_ibu_hamil_mengonsumsi_minimal_180_tablet_TTD'] / recap_df['Jumlah_Sasaran_Ibu_Hamil'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0).round(2)

    recap_display = recap_df[['Puskesmas', 'Kelurahan'] + list(metrik_data.keys())] if puskesmas_filter != "All" else recap_df[['Puskesmas'] + list(metrik_data.keys())]
    recap_display.insert(0, 'No', range(1, len(recap_display) + 1))
    st.dataframe(recap_display, use_container_width=True)

    # 4. Fitur Download Laporan PDF
    st.subheader("📥 Unduh Laporan")
    def generate_pdf_report():
        # Buat buffer untuk menyimpan grafik
        img_buffer1 = BytesIO()
        img_buffer2 = BytesIO()
        fig1.write_image(img_buffer1, format='png', width=600, height=400, scale=2)
        fig2.write_image(img_buffer2, format='png', width=600, height=400, scale=2)
        img_buffer1.seek(0)
        img_buffer2.seek(0)

        # Buat buffer untuk PDF
        pdf_buffer = BytesIO()

        # Buat dokumen PDF
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        elements = []

        # Gaya teks
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        normal_style = styles['Normal']
        normal_style.textColor = colors.black

        # Tambahkan judul
        elements.append(Paragraph("Laporan Cakupan Suplementasi Gizi Ibu Hamil", title_style))
        elements.append(Paragraph(f"Diperbarui: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
        elements.append(Spacer(1, 12))

        # Tambahkan Metrik
        elements.append(Paragraph("1. Metrik Cakupan Suplementasi", normal_style))
        metric_data = []
        for label, value in metrik_list:
            target = targets.get(label)
            if target is not None:
                gap = abs(value - target)
                if value < target:
                    delta_str = f"Dibawah Target (gap: {gap:.2f}%)"
                    delta_color = colors.red
                    delta_arrow = "↓"
                else:
                    delta_str = f"Diatas Target (gap: {gap:.2f}%)"
                    delta_color = colors.green
                    delta_arrow = "↑"
                metric_data.append([f"{label}: {value:.2f}%", f"({delta_str} {delta_arrow})", ""])
                metric_data[-1][2] = Paragraph(metric_data[-1][1], style=ParagraphStyle(name='Custom', textColor=delta_color))
            else:
                metric_data.append([f"{label}: {value:.2f}%", "", ""])
        metric_table = Table(metric_data, colWidths=[300, 150, 50])
        metric_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(metric_table)
        elements.append(Spacer(1, 12))

        # Tambahkan Grafik
        elements.append(Paragraph("2. Grafik Cakupan Suplementasi MMS Ibu Hamil", normal_style))
        elements.append(Image(img_buffer1, width=500, height=300))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("3. Grafik Cakupan Suplementasi TTD Ibu Hamil", normal_style))
        elements.append(Image(img_buffer2, width=500, height=300))
        elements.append(Spacer(1, 12))

        # Tambahkan Tabel Rekapitulasi
        elements.append(Paragraph("4. Tabel Rekapitulasi", normal_style))
        table_data = [recap_display.columns.tolist()] + recap_display.values.tolist()
        recap_table = Table(table_data)
        recap_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(recap_table)

        # Build PDF ke buffer
        doc.build(elements)
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()

    if st.button("Download Laporan PDF"):
        st.warning("Membuat laporan PDF, harap tunggu...")
        pdf_data = generate_pdf_report()
        st.success("Laporan PDF siap diunduh!")
        st.download_button(
            label="Download Laporan PDF",
            data=pdf_data,
            file_name=f"Laporan_Cakupan_Suplementasi_Gizi_Ibu_Hamil_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )

# ----------------------------- #
# 📉 Cakupan Layanan Kesehatan Ibu Hamil KEK (Perbaikan Filter Triwulan)
# ----------------------------- #
def cakupan_layanan_kesehatan_ibu_hamil_kek(filtered_df, desa_df, periode_filter, puskesmas_filter, kelurahan_filter, periode_type="Bulan", laporan_type="Bulanan"):
    """Menampilkan analisis Cakupan Layanan Kesehatan Ibu Hamil KEK dengan fitur download laporan."""
    st.header("📉 Cakupan Layanan Kesehatan Ibu Hamil KEK")

    # Tambahkan informasi definisi operasional dan insight analisis (tetap sama)
    with st.expander("📜 Definisi Operasional dan Insight Analisis Cakupan Layanan Kesehatan Ibu Hamil KEK", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Analisis Indikator

            Berikut adalah definisi operasional, rumus perhitungan, serta analisis insight dari indikator-indikator yang digunakan untuk memantau cakupan layanan kesehatan ibu hamil dengan kondisi Kurang Energi Kronis (KEK). Rumus disajikan dalam format matematis untuk kejelasan, dengan penjelasan sederhana untuk memudahkan pemahaman.

            #### Apa itu KEK (Kurang Energi Kronis) pada Ibu Hamil?
            - **Definisi:** Kurang Energi Kronis (KEK) pada ibu hamil merujuk pada kondisi gizi buruk yang ditandai oleh Indeks Massa Tubuh (IMT) Pra Hamil atau pada Trimester 1 (< 12 minggu) kurang dari 18,5 kg/m², atau ukuran Lingkar Lengan Atas (LILA) kurang dari 23,5 cm. Kondisi ini mencerminkan defisiensi energi kronis yang dapat terjadi sebelum atau selama kehamilan akibat asupan makanan yang tidak mencukupi dalam jangka panjang.  
            - **Tujuan Identifikasi:** Identifikasi KEK bertujuan untuk mendeteksi ibu hamil yang berisiko tinggi terhadap komplikasi kehamilan, seperti kelahiran prematur, berat badan bayi lahir rendah, atau mortalitas maternal, sehingga dapat diberikan intervensi gizi yang tepat.  
            - **Kriteria Pengukuran:** Pengukuran dilakukan melalui IMT (berdasarkan berat dan tinggi badan) dan LILA (ukuran lingkar lengan atas), yang mencerminkan status gizi ibu hamil. Pelaporan dilakukan secara kumulatif setiap bulannya untuk memantau perkembangan kondisi ini di suatu wilayah kerja.  

            #### 1. Metrik Prevalensi Ibu Hamil Risiko KEK/KEK
            - **Definisi Operasional:** Persentase ibu hamil yang teridentifikasi memiliki risiko KEK atau KEK (IMT < 18,5 kg/m² atau LILA < 23,5 cm) dari total ibu hamil yang diperiksa LILA dan/atau diukur IMT dalam suatu periode tertentu di wilayah kerja tertentu.  
            - **Rumus Perhitungan:**  
            $$ \\text{Prevalensi KEK (\\%)} = \\frac{\\text{Jumlah Ibu Hamil Teridentifikasi KEK dan Risiko KEK}}{\\text{Jumlah Ibu Hamil yang Diperiksa LILA dan/atau Diukur IMT}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase ibu hamil yang terdeteksi memiliki KEK atau berisiko KEK dari total ibu hamil yang diperiksa status gizinya, lalu dikalikan 100 untuk mendapatkan persentase.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui pemeriksaan LILA dan pengukuran IMT oleh petugas kesehatan di puskesmas atau posyandu, dengan pelaporan kumulatif setiap bulannya.  
            - **Target:** Prevalensi KEK ditargetkan di bawah 15% karena bersifat inversi—semakin rendah prevalensinya, semakin baik status gizi ibu hamil.  

            #### 2. Metrik Ibu Hamil KEK Mendapat Tambahan Asupan Gizi
            - **Definisi Operasional:** Persentase ibu hamil dengan KEK atau risiko KEK yang menerima tambahan asupan gizi dari total ibu hamil yang teridentifikasi memiliki KEK atau risiko KEK dalam suatu periode tertentu di wilayah kerja tertentu.  
            - **Rumus Perhitungan:**  
            $$ \\text{Cakupan Mendapat Asupan Gizi (\\%)} = \\frac{\\text{Jumlah Ibu Hamil KEK yang Mendapat Tambahan Asupan Gizi}}{\\text{Jumlah Ibu Hamil KEK dan Risiko KEK}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase ibu hamil dengan KEK yang telah diberikan tambahan asupan gizi (seperti makanan tambahan atau suplementasi) dari total ibu hamil yang terdeteksi memiliki KEK, lalu dikalikan 100 untuk mendapatkan persentase.  
            - **Metode Pengumpulan Data:** Data dihimpun dari laporan distribusi asupan gizi di puskesmas atau posyandu, dengan verifikasi terhadap jumlah ibu hamil KEK yang menerima intervensi gizi.  
            - **Target:** Cakupan penerimaan tambahan asupan gizi ditargetkan mencapai 84%.  

            #### 3. Metrik Ibu Hamil KEK Mengonsumsi Tambahan Asupan Gizi
            - **Definisi Operasional:** Persentase ibu hamil dengan KEK atau risiko KEK yang mengonsumsi tambahan asupan gizi dari total ibu hamil yang teridentifikasi memiliki KEK atau risiko KEK dalam suatu periode tertentu di wilayah kerja tertentu.  
            - **Rumus Perhitungan:**  
            $$ \\text{Cakupan Mengonsumsi Asupan Gizi (\\%)} = \\frac{\\text{Jumlah Ibu Hamil KEK yang Mengonsumsi Tambahan Asupan Gizi}}{\\text{Jumlah Ibu Hamil KEK dan Risiko KEK}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase ibu hamil dengan KEK yang telah mengonsumsi tambahan asupan gizi dari total ibu hamil yang terdeteksi memiliki KEK, lalu dikalikan 100 untuk mendapatkan persentase.  
            - **Metode Pengumpulan Data:** Data diperoleh melalui wawancara atau laporan kunjungan petugas kesehatan, dengan verifikasi terhadap konsumsi asupan gizi berdasarkan catatan atau pengakuan ibu hamil.  
            - **Target:** Cakupan konsumsi tambahan asupan gizi ditargetkan mencapai 83%.  

            #### Insight Analisis
            - **Prevalensi KEK:** Jika prevalensi KEK melebihi target 15%, ini mengindikasikan masalah gizi kronis yang signifikan di kalangan ibu hamil, yang dapat disebabkan oleh pola makan yang buruk, kemiskinan, atau akses terbatas ke layanan kesehatan. Intervensi yang diperlukan meliputi peningkatan edukasi gizi, penyediaan makanan tambahan, dan skrining rutin IMT dan LILA.  
            - **Cakupan Asupan Gizi:** Jika cakupan penerimaan atau konsumsi tambahan asupan gizi di bawah target (84% untuk penerimaan, 83% untuk konsumsi), ini dapat mencerminkan keterbatasan distribusi asupan gizi, rendahnya kepatuhan ibu hamil dalam mengonsumsi, atau kurangnya pendampingan oleh petugas kesehatan. Solusi yang diusulkan meliputi penguatan rantai pasok, edukasi intensif, dan monitoring kepatuhan konsumsi.  
            - **Implikasi Kesehatan:** KEK pada ibu hamil meningkatkan risiko komplikasi seperti kelahiran dengan berat badan rendah, stunting pada anak, dan mortalitas perinatal. Oleh karena itu, pemantauan indikator ini sangat krusial untuk mendukung pencapaian target Sustainable Development Goals (SDGs) terkait kesehatan ibu dan anak.  

            </div>
        """, unsafe_allow_html=True)

    # Daftar kolom yang dibutuhkan
    required_columns = [
        'Jumlah_ibu_hamil_diukur_LILA_IMT',
        'Jumlah_ibu_hamil_risiko_KEK',
        'Jumlah_ibu_hamil_KEK_mendapat_tambahan_asupan_gizi',
        'Jumlah_ibu_hamil_KEK_mengonsumsi_tambahan_asupan_gizi'
    ]

    # Cek apakah semua kolom ada
    missing_cols = [col for col in required_columns if col not in filtered_df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di dataset: {missing_cols}. Periksa data di 'data_ibuhamil'!")
        return

    # Inisialisasi scope
    scope = filtered_df.copy()

    # Validasi dan konversi kolom Bulan
    if 'Bulan' in scope.columns:
        scope['Bulan'] = pd.to_numeric(scope['Bulan'], errors='coerce').fillna(0).astype(int)
    else:
        st.error("⚠️ Kolom 'Bulan' tidak ditemukan di dataset!")
        return

    # Definisikan triwulan
    triwulan_map = {
        "Triwulan 1": [1, 2, 3],
        "Triwulan 2": [4, 5, 6],
        "Triwulan 3": [7, 8, 9],
        "Triwulan 4": [10, 11, 12]
    }

    # Target
    targets = {
        "Metrik Prevalensi Ibu Hamil Risiko KEK/KEK (%)": 15,
        "Metrik Ibu Hamil KEK Mendapat Tambahan Asupan Gizi (%)": 84,
        "Metrik Ibu Hamil KEK Mengonsumsi Tambahan Asupan Gizi (%)": 83
    }

    # List untuk menyimpan grafik dan tabel untuk PDF
    all_figs_prev = []
    all_figs_cakup = []
    all_recap_dfs = []

    # Proses data berdasarkan laporan_type
    if laporan_type == "Tahunan":
        triwulan_list = ["Triwulan 1", "Triwulan 2", "Triwulan 3", "Triwulan 4"]
        for triwulan in triwulan_list:
            st.subheader(f"📅 {triwulan}")
            triwulan_scope = scope.copy()
            bulan_range = triwulan_map[triwulan]
            triwulan_scope = triwulan_scope[triwulan_scope['Bulan'].isin(bulan_range)]

            # Terapkan filter Puskesmas dan Kelurahan
            if puskesmas_filter != "All":
                triwulan_scope = triwulan_scope[triwulan_scope['Puskesmas'] == puskesmas_filter]
            if kelurahan_filter != "All":
                triwulan_scope = triwulan_scope[triwulan_scope['Kelurahan'] == kelurahan_filter]

            # Agregasi data
            group_cols = ['Puskesmas']
            if puskesmas_filter != "All":
                group_cols.append('Kelurahan')
            triwulan_scope = triwulan_scope.groupby(group_cols).sum(numeric_only=True).reset_index()

            # Hitung total ibu hamil yang diukur LILA/IMT atau risiko KEK
            total_diukur = triwulan_scope['Jumlah_ibu_hamil_diukur_LILA_IMT'].sum()
            total_risiko_kek = triwulan_scope['Jumlah_ibu_hamil_risiko_KEK'].sum()
            if total_diukur == 0 or total_risiko_kek == 0:
                st.warning(f"⚠️ Tidak ada data ibu hamil yang diukur LILA/IMT atau berisiko KEK untuk {triwulan}.")
                continue

            # Hitung metrik
            metrik_data = {
                "Metrik Prevalensi Ibu Hamil Risiko KEK/KEK (%)": (triwulan_scope['Jumlah_ibu_hamil_risiko_KEK'].sum() / total_diukur * 100) if total_diukur > 0 else 0,
                "Metrik Ibu Hamil KEK Mendapat Tambahan Asupan Gizi (%)": (triwulan_scope['Jumlah_ibu_hamil_KEK_mendapat_tambahan_asupan_gizi'].sum() / total_risiko_kek * 100) if total_risiko_kek > 0 else 0,
                "Metrik Ibu Hamil KEK Mengonsumsi Tambahan Asupan Gizi (%)": (triwulan_scope['Jumlah_ibu_hamil_KEK_mengonsumsi_tambahan_asupan_gizi'].sum() / total_risiko_kek * 100) if total_risiko_kek > 0 else 0
            }

            # 1. Metrik Score Card
            st.subheader(f"📊 Metrik Cakupan Layanan Kesehatan Ibu Hamil KEK - {triwulan}")
            metrik_list = list(metrik_data.items())
            cols1 = st.columns(2)
            for i in range(2):
                for j in range(2):
                    idx = i * 2 + j
                    if idx >= len(metrik_list):
                        break
                    label, value = metrik_list[idx]
                    target = targets.get(label)
                    if target is not None:
                        gap = abs(value - target)
                        if label == "Metrik Prevalensi Ibu Hamil Risiko KEK/KEK (%)":
                            if value < target:
                                delta_str = f"Dibawah Target (gap: {gap:.2f}%)"
                                delta_color = "normal"  # Hijau (semakin kecil semakin baik)
                                delta_arrow = "↓"
                            else:
                                delta_str = f"Diatas Target (gap: {gap:.2f}%)"
                                delta_color = "inverse"  # Merah
                                delta_arrow = "↑"
                        else:  # Untuk cakupan asupan gizi
                            if value < target:
                                delta_str = f"Dibawah Target (gap: {gap:.2f}%)"
                                delta_color = "inverse"  # Merah
                                delta_arrow = "↓"
                            else:
                                delta_str = f"Diatas Target (gap: {gap:.2f}%)"
                                delta_color = "normal"  # Hijau
                                delta_arrow = "↑"
                        cols1[i].metric(label=label, value=f"{value:.2f}%", delta=f"{delta_str} {delta_arrow}", delta_color=delta_color)
                    else:
                        cols1[i].metric(label=label, value=f"{value:.2f}%")

            # 2. Grafik Visualisasi
            # Grafik 1: Prevalensi Ibu Hamil KEK
            st.subheader(f"📈 Grafik Prevalensi Ibu Hamil KEK - {triwulan}")
            if puskesmas_filter == "All":
                grouped_df = triwulan_scope.groupby('Puskesmas').sum(numeric_only=True).reset_index()
                graph_data_prev = pd.DataFrame({
                    "Puskesmas": grouped_df['Puskesmas'],
                    "Metrik Prevalensi Ibu Hamil Risiko KEK/KEK (%)": (grouped_df['Jumlah_ibu_hamil_risiko_KEK'] / grouped_df['Jumlah_ibu_hamil_diukur_LILA_IMT'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
                }).melt(id_vars=["Puskesmas"], var_name="Indikator", value_name="Persentase")
                fig1 = px.bar(graph_data_prev, x="Puskesmas", y="Persentase", color="Indikator", title=f"Prevalensi Ibu Hamil KEK per Puskesmas - {triwulan}", text=graph_data_prev["Persentase"].apply(lambda x: f"{x:.1f}%"), color_discrete_sequence=["#FF4040"])
            else:
                grouped_df = triwulan_scope.groupby('Kelurahan').sum(numeric_only=True).reset_index()
                graph_data_prev = pd.DataFrame({
                    "Kelurahan": grouped_df['Kelurahan'],
                    "Metrik Prevalensi Ibu Hamil Risiko KEK/KEK (%)": (grouped_df['Jumlah_ibu_hamil_risiko_KEK'] / grouped_df['Jumlah_ibu_hamil_diukur_LILA_IMT'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
                }).melt(id_vars=["Kelurahan"], var_name="Indikator", value_name="Persentase")
                fig1 = px.bar(graph_data_prev, x="Kelurahan", y="Persentase", color="Indikator", title=f"Prevalensi Ibu Hamil KEK per Kelurahan di {puskesmas_filter} - {triwulan}", text=graph_data_prev["Persentase"].apply(lambda x: f"{x:.1f}%"), color_discrete_sequence=["#FF4040"])

            # Tambahkan garis target untuk prevalensi KEK
            fig1.add_hline(y=15, line_dash="dash", line_color="#FF4040", annotation_text="Target Prevalensi KEK (15%)", annotation_position="top right")
            fig1.update_traces(textposition='outside')
            fig1.update_layout(
                xaxis_tickangle=-45,
                yaxis_title="Persentase (%)",
                yaxis_range=[0, 100],
                title_x=0.5,
                height=500,
                width=1000,
                margin=dict(t=80, b=100, l=60, r=60),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.5,
                    xanchor="center",
                    x=0.5
                )
            )
            st.plotly_chart(fig1, use_container_width=True)
            all_figs_prev.append((triwulan, fig1))

            # Grafik 2: Cakupan Layanan Ibu Hamil KEK
            st.subheader(f"📈 Grafik Cakupan Layanan Ibu Hamil KEK - {triwulan}")
            if puskesmas_filter == "All":
                grouped_df = triwulan_scope.groupby('Puskesmas').sum(numeric_only=True).reset_index()
                graph_data_cakup = pd.DataFrame({
                    "Puskesmas": grouped_df['Puskesmas'],
                    "Metrik Ibu Hamil KEK Mendapat Tambahan Asupan Gizi (%)": (grouped_df['Jumlah_ibu_hamil_KEK_mendapat_tambahan_asupan_gizi'] / grouped_df['Jumlah_ibu_hamil_risiko_KEK'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0),
                    "Metrik Ibu Hamil KEK Mengonsumsi Tambahan Asupan Gizi (%)": (grouped_df['Jumlah_ibu_hamil_KEK_mengonsumsi_tambahan_asupan_gizi'] / grouped_df['Jumlah_ibu_hamil_risiko_KEK'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
                }).melt(id_vars=["Puskesmas"], var_name="Indikator", value_name="Persentase")
                fig2 = px.bar(graph_data_cakup, x="Puskesmas", y="Persentase", color="Indikator", barmode="group",
                              title=f"Cakupan Layanan Ibu Hamil KEK per Puskesmas - {triwulan}", text=graph_data_cakup["Persentase"].apply(lambda x: f"{x:.1f}%"))
            else:
                grouped_df = triwulan_scope.groupby('Kelurahan').sum(numeric_only=True).reset_index()
                graph_data_cakup = pd.DataFrame({
                    "Kelurahan": grouped_df['Kelurahan'],
                    "Metrik Ibu Hamil KEK Mendapat Tambahan Asupan Gizi (%)": (grouped_df['Jumlah_ibu_hamil_KEK_mendapat_tambahan_asupan_gizi'] / grouped_df['Jumlah_ibu_hamil_risiko_KEK'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0),
                    "Metrik Ibu Hamil KEK Mengonsumsi Tambahan Asupan Gizi (%)": (grouped_df['Jumlah_ibu_hamil_KEK_mengonsumsi_tambahan_asupan_gizi'] / grouped_df['Jumlah_ibu_hamil_risiko_KEK'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
                }).melt(id_vars=["Kelurahan"], var_name="Indikator", value_name="Persentase")
                fig2 = px.bar(graph_data_cakup, x="Kelurahan", y="Persentase", color="Indikator", barmode="group",
                              title=f"Cakupan Layanan Ibu Hamil KEK per Kelurahan di {puskesmas_filter} - {triwulan}", text=graph_data_cakup["Persentase"].apply(lambda x: f"{x:.1f}%"))

            # Tambahkan garis target untuk cakupan KEK
            colors_cakup = px.colors.qualitative.Plotly[:2]
            fig2.add_hline(y=84, line_dash="dash", line_color=colors_cakup[0], annotation_text="Target Mendapat Asupan (84%)", annotation_position="top right")
            fig2.add_hline(y=83, line_dash="dash", line_color=colors_cakup[1], annotation_text="Target Mengonsumsi Asupan (83%)", annotation_position="top left")
            fig2.update_traces(textposition='outside')
            fig2.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", yaxis_range=[0, 100], title_x=0.5,
                               legend_title_text="Indikator", legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5),
                               height=500)
            st.plotly_chart(fig2, use_container_width=True)
            all_figs_cakup.append((triwulan, fig2))

            # 3. Tabel Rekapitulasi
            st.subheader(f"📋 Tabel Rekapitulasi Cakupan Layanan Kesehatan Ibu Hamil KEK - {triwulan}")
            recap_df = triwulan_scope.copy()
            recap_df['Metrik Prevalensi Ibu Hamil Risiko KEK/KEK (%)'] = (recap_df['Jumlah_ibu_hamil_risiko_KEK'] / recap_df['Jumlah_ibu_hamil_diukur_LILA_IMT'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0).round(2)
            recap_df['Metrik Ibu Hamil KEK Mendapat Tambahan Asupan Gizi (%)'] = (recap_df['Jumlah_ibu_hamil_KEK_mendapat_tambahan_asupan_gizi'] / recap_df['Jumlah_ibu_hamil_risiko_KEK'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0).round(2)
            recap_df['Metrik Ibu Hamil KEK Mengonsumsi Tambahan Asupan Gizi (%)'] = (recap_df['Jumlah_ibu_hamil_KEK_mengonsumsi_tambahan_asupan_gizi'] / recap_df['Jumlah_ibu_hamil_risiko_KEK'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0).round(2)

            recap_display = recap_df[['Puskesmas', 'Kelurahan'] + list(metrik_data.keys())] if puskesmas_filter != "All" else recap_df[['Puskesmas'] + list(metrik_data.keys())]
            recap_display.insert(0, 'No', range(1, len(recap_display) + 1))
            st.dataframe(recap_display, use_container_width=True)
            all_recap_dfs.append((triwulan, recap_display, metrik_data))

    else:
        # Proses untuk laporan Bulanan atau Triwulanan
        # Filter periode (mengadopsi logika dari cakupan_layanan_anemia_ibu_hamil)
        if periode_type == "Bulan" and periode_filter != "All":
            try:
                bulan_filter_int = int(periode_filter)
                scope = scope[scope['Bulan'] == bulan_filter_int]
            except ValueError:
                st.warning("⚠️ Pilihan bulan tidak valid.")
                return
        elif periode_type == "Triwulan" and periode_filter != "All":
            bulan_range = triwulan_map.get(periode_filter, [])
            if bulan_range:
                scope = scope[scope['Bulan'].isin(bulan_range)]

        # Terapkan filter Puskesmas dan Kelurahan
        if puskesmas_filter != "All":
            scope = scope[scope['Puskesmas'] == puskesmas_filter]
        if kelurahan_filter != "All":
            scope = scope[scope['Kelurahan'] == kelurahan_filter]

        # Agregasi data
        group_cols = ['Puskesmas']
        if puskesmas_filter != "All":
            group_cols.append('Kelurahan')
        if (periode_type == "Triwulan" or periode_type == "Bulan") and periode_filter != "All":
            scope = scope.groupby(group_cols).sum(numeric_only=True).reset_index()

        # Hitung total ibu hamil yang diukur LILA/IMT atau risiko KEK
        total_diukur = scope['Jumlah_ibu_hamil_diukur_LILA_IMT'].sum()
        total_risiko_kek = scope['Jumlah_ibu_hamil_risiko_KEK'].sum()
        if total_diukur == 0 or total_risiko_kek == 0:
            st.warning("⚠️ Tidak ada data ibu hamil yang diukur LILA/IMT atau berisiko KEK untuk filter ini.")
            return

        # Hitung metrik
        metrik_data = {
            "Metrik Prevalensi Ibu Hamil Risiko KEK/KEK (%)": (scope['Jumlah_ibu_hamil_risiko_KEK'].sum() / total_diukur * 100) if total_diukur > 0 else 0,
            "Metrik Ibu Hamil KEK Mendapat Tambahan Asupan Gizi (%)": (scope['Jumlah_ibu_hamil_KEK_mendapat_tambahan_asupan_gizi'].sum() / total_risiko_kek * 100) if total_risiko_kek > 0 else 0,
            "Metrik Ibu Hamil KEK Mengonsumsi Tambahan Asupan Gizi (%)": (scope['Jumlah_ibu_hamil_KEK_mengonsumsi_tambahan_asupan_gizi'].sum() / total_risiko_kek * 100) if total_risiko_kek > 0 else 0
        }

        # 1. Metrik Score Card
        st.subheader("📊 Metrik Cakupan Layanan Kesehatan Ibu Hamil KEK")
        metrik_list = list(metrik_data.items())
        cols1 = st.columns(2)
        for i in range(2):
            for j in range(2):
                idx = i * 2 + j
                if idx >= len(metrik_list):
                    break
                label, value = metrik_list[idx]
                target = targets.get(label)
                if target is not None:
                    gap = abs(value - target)
                    if label == "Metrik Prevalensi Ibu Hamil Risiko KEK/KEK (%)":
                        if value < target:
                            delta_str = f"Dibawah Target (gap: {gap:.2f}%)"
                            delta_color = "normal"  # Hijau (semakin kecil semakin baik)
                            delta_arrow = "↓"
                        else:
                            delta_str = f"Diatas Target (gap: {gap:.2f}%)"
                            delta_color = "inverse"  # Merah
                            delta_arrow = "↑"
                    else:  # Untuk cakupan asupan gizi
                        if value < target:
                            delta_str = f"Dibawah Target (gap: {gap:.2f}%)"
                            delta_color = "inverse"  # Merah
                            delta_arrow = "↓"
                        else:
                            delta_str = f"Diatas Target (gap: {gap:.2f}%)"
                            delta_color = "normal"  # Hijau
                            delta_arrow = "↑"
                    cols1[i].metric(label=label, value=f"{value:.2f}%", delta=f"{delta_str} {delta_arrow}", delta_color=delta_color)
                else:
                    cols1[i].metric(label=label, value=f"{value:.2f}%")

        # 2. Grafik Visualisasi
        # Grafik 1: Prevalensi Ibu Hamil KEK
        st.subheader("📈 Grafik Prevalensi Ibu Hamil KEK")
        if puskesmas_filter == "All":
            grouped_df = scope.groupby('Puskesmas').sum(numeric_only=True).reset_index()
            graph_data_prev = pd.DataFrame({
                "Puskesmas": grouped_df['Puskesmas'],
                "Metrik Prevalensi Ibu Hamil Risiko KEK/KEK (%)": (grouped_df['Jumlah_ibu_hamil_risiko_KEK'] / grouped_df['Jumlah_ibu_hamil_diukur_LILA_IMT'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
            }).melt(id_vars=["Puskesmas"], var_name="Indikator", value_name="Persentase")
            fig1 = px.bar(graph_data_prev, x="Puskesmas", y="Persentase", color="Indikator", title="Prevalensi Ibu Hamil KEK per Puskesmas", text=graph_data_prev["Persentase"].apply(lambda x: f"{x:.1f}%"), color_discrete_sequence=["#FF4040"])
        else:
            grouped_df = scope.groupby('Kelurahan').sum(numeric_only=True).reset_index()
            graph_data_prev = pd.DataFrame({
                "Kelurahan": grouped_df['Kelurahan'],
                "Metrik Prevalensi Ibu Hamil Risiko KEK/KEK (%)": (grouped_df['Jumlah_ibu_hamil_risiko_KEK'] / grouped_df['Jumlah_ibu_hamil_diukur_LILA_IMT'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
            }).melt(id_vars=["Kelurahan"], var_name="Indikator", value_name="Persentase")
            fig1 = px.bar(graph_data_prev, x="Kelurahan", y="Persentase", color="Indikator", title=f"Prevalensi Ibu Hamil KEK per Kelurahan di {puskesmas_filter}", text=graph_data_prev["Persentase"].apply(lambda x: f"{x:.1f}%"), color_discrete_sequence=["#FF4040"])

        # Tambahkan garis target untuk prevalensi KEK
        fig1.add_hline(y=15, line_dash="dash", line_color="#FF4040", annotation_text="Target Prevalensi KEK (15%)", annotation_position="top right")
        fig1.update_traces(textposition='outside')
        fig1.update_layout(
            xaxis_tickangle=-45,
            yaxis_title="Persentase (%)",
            yaxis_range=[0, 100],
            title_x=0.5,
            height=500,
            width=1000,
            margin=dict(t=80, b=100, l=60, r=60),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.5,
                xanchor="center",
                x=0.5
            )
        )
        st.plotly_chart(fig1, use_container_width=True)
        all_figs_prev.append(("Current", fig1))

        # Grafik 2: Cakupan Layanan Ibu Hamil KEK
        st.subheader("📈 Grafik Cakupan Layanan Ibu Hamil KEK")
        if puskesmas_filter == "All":
            grouped_df = scope.groupby('Puskesmas').sum(numeric_only=True).reset_index()
            graph_data_cakup = pd.DataFrame({
                "Puskesmas": grouped_df['Puskesmas'],
                "Metrik Ibu Hamil KEK Mendapat Tambahan Asupan Gizi (%)": (grouped_df['Jumlah_ibu_hamil_KEK_mendapat_tambahan_asupan_gizi'] / grouped_df['Jumlah_ibu_hamil_risiko_KEK'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0),
                "Metrik Ibu Hamil KEK Mengonsumsi Tambahan Asupan Gizi (%)": (grouped_df['Jumlah_ibu_hamil_KEK_mengonsumsi_tambahan_asupan_gizi'] / grouped_df['Jumlah_ibu_hamil_risiko_KEK'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
            }).melt(id_vars=["Puskesmas"], var_name="Indikator", value_name="Persentase")
            fig2 = px.bar(graph_data_cakup, x="Puskesmas", y="Persentase", color="Indikator", barmode="group",
                          title="Cakupan Layanan Ibu Hamil KEK per Puskesmas", text=graph_data_cakup["Persentase"].apply(lambda x: f"{x:.1f}%"))
        else:
            grouped_df = scope.groupby('Kelurahan').sum(numeric_only=True).reset_index()
            graph_data_cakup = pd.DataFrame({
                "Kelurahan": grouped_df['Kelurahan'],
                "Metrik Ibu Hamil KEK Mendapat Tambahan Asupan Gizi (%)": (grouped_df['Jumlah_ibu_hamil_KEK_mendapat_tambahan_asupan_gizi'] / grouped_df['Jumlah_ibu_hamil_risiko_KEK'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0),
                "Metrik Ibu Hamil KEK Mengonsumsi Tambahan Asupan Gizi (%)": (grouped_df['Jumlah_ibu_hamil_KEK_mengonsumsi_tambahan_asupan_gizi'] / grouped_df['Jumlah_ibu_hamil_risiko_KEK'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
            }).melt(id_vars=["Kelurahan"], var_name="Indikator", value_name="Persentase")
            fig2 = px.bar(graph_data_cakup, x="Kelurahan", y="Persentase", color="Indikator", barmode="group",
                          title=f"Cakupan Layanan Ibu Hamil KEK per Kelurahan di {puskesmas_filter}", text=graph_data_cakup["Persentase"].apply(lambda x: f"{x:.1f}%"))

        # Tambahkan garis target untuk cakupan KEK
        colors_cakup = px.colors.qualitative.Plotly[:2]
        fig2.add_hline(y=84, line_dash="dash", line_color=colors_cakup[0], annotation_text="Target Mendapat Asupan (84%)", annotation_position="top right")
        fig2.add_hline(y=83, line_dash="dash", line_color=colors_cakup[1], annotation_text="Target Mengonsumsi Asupan (83%)", annotation_position="top left")
        fig2.update_traces(textposition='outside')
        fig2.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", yaxis_range=[0, 100], title_x=0.5,
                           legend_title_text="Indikator", legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5),
                           height=500)
        st.plotly_chart(fig2, use_container_width=True)
        all_figs_cakup.append(("Current", fig2))

        # 3. Tabel Rekapitulasi
        st.subheader("📋 Tabel Rekapitulasi Cakupan Layanan Kesehatan Ibu Hamil KEK")
        recap_df = scope.copy()
        recap_df['Metrik Prevalensi Ibu Hamil Risiko KEK/KEK (%)'] = (recap_df['Jumlah_ibu_hamil_risiko_KEK'] / recap_df['Jumlah_ibu_hamil_diukur_LILA_IMT'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0).round(2)
        recap_df['Metrik Ibu Hamil KEK Mendapat Tambahan Asupan Gizi (%)'] = (recap_df['Jumlah_ibu_hamil_KEK_mendapat_tambahan_asupan_gizi'] / recap_df['Jumlah_ibu_hamil_risiko_KEK'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0).round(2)
        recap_df['Metrik Ibu Hamil KEK Mengonsumsi Tambahan Asupan Gizi (%)'] = (recap_df['Jumlah_ibu_hamil_KEK_mengonsumsi_tambahan_asupan_gizi'] / recap_df['Jumlah_ibu_hamil_risiko_KEK'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0).round(2)

        recap_display = recap_df[['Puskesmas', 'Kelurahan'] + list(metrik_data.keys())] if puskesmas_filter != "All" else recap_df[['Puskesmas'] + list(metrik_data.keys())]
        recap_display.insert(0, 'No', range(1, len(recap_display) + 1))
        st.dataframe(recap_display, use_container_width=True)
        all_recap_dfs.append(("Current", recap_display, metrik_data))

    # 4. Fitur Download Laporan PDF
    st.subheader("📥 Unduh Laporan")
    def generate_pdf_report():
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        elements = []

        # Gaya teks
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        normal_style = styles['Normal']
        normal_style.textColor = colors.black

        # Tambahkan judul
        elements.append(Paragraph("Laporan Cakupan Layanan Kesehatan Ibu Hamil KEK", title_style))
        elements.append(Paragraph(f"Diperbarui: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
        elements.append(Spacer(1, 12))

        # Tambahkan Metrik, Grafik, dan Tabel untuk setiap triwulan atau periode
        for idx, (period, recap_display, metrik_data) in enumerate(all_recap_dfs):
            # Tambahkan Metrik
            elements.append(Paragraph(f"1.{idx + 1} Metrik Cakupan Layanan - {period}", normal_style))
            metric_data = []
            metrik_list = list(metrik_data.items())
            for label, value in metrik_list:
                target = targets.get(label)
                if target is not None:
                    gap = abs(value - target)
                    if label == "Metrik Prevalensi Ibu Hamil Risiko KEK/KEK (%)":
                        if value < target:
                            delta_str = f"Dibawah Target (gap: {gap:.2f}%)"
                            delta_color = colors.green
                            delta_arrow = "↓"
                        else:
                            delta_str = f"Diatas Target (gap: {gap:.2f}%)"
                            delta_color = colors.red
                            delta_arrow = "↑"
                    else:
                        if value < target:
                            delta_str = f"Dibawah Target (gap: {gap:.2f}%)"
                            delta_color = colors.red
                            delta_arrow = "↓"
                        else:
                            delta_str = f"Diatas Target (gap: {gap:.2f}%)"
                            delta_color = colors.green
                            delta_arrow = "↑"
                    metric_data.append([f"{label}: {value:.2f}%", f"({delta_str} {delta_arrow})", ""])
                    metric_data[-1][2] = Paragraph(metric_data[-1][1], style=ParagraphStyle(name='Custom', textColor=delta_color))
                else:
                    metric_data.append([f"{label}: {value:.2f}%", "", ""])
            metric_table = Table(metric_data, colWidths=[300, 150, 50])
            metric_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(metric_table)
            elements.append(Spacer(1, 12))

            # Tambahkan Grafik Prevalensi
            elements.append(Paragraph(f"2.{idx + 1} Grafik Prevalensi Ibu Hamil KEK - {period}", normal_style))
            img_buffer_prev = BytesIO()
            all_figs_prev[idx][1].write_image(img_buffer_prev, format='png', width=600, height=400, scale=2)
            img_buffer_prev.seek(0)
            elements.append(Image(img_buffer_prev, width=500, height=300))
            elements.append(Spacer(1, 12))

            # Tambahkan Grafik Cakupan
            elements.append(Paragraph(f"3.{idx + 1} Grafik Cakupan Layanan Ibu Hamil KEK - {period}", normal_style))
            img_buffer_cakup = BytesIO()
            all_figs_cakup[idx][1].write_image(img_buffer_cakup, format='png', width=600, height=400, scale=2)
            img_buffer_cakup.seek(0)
            elements.append(Image(img_buffer_cakup, width=500, height=300))
            elements.append(Spacer(1, 12))

            # Tambahkan Tabel Rekapitulasi
            elements.append(Paragraph(f"4.{idx + 1} Tabel Rekapitulasi - {period}", normal_style))
            table_data = [recap_display.columns.tolist()] + recap_display.values.tolist()
            recap_table = Table(table_data)
            recap_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(recap_table)
            elements.append(Spacer(1, 12))

        # Build PDF ke buffer
        doc.build(elements)
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()

    if st.button("Download Laporan PDF"):
        st.warning("Membuat laporan PDF, harap tunggu...")
        pdf_data = generate_pdf_report()
        st.success("Laporan PDF siap diunduh!")
        st.download_button(
            label="Download Laporan PDF",
            data=pdf_data,
            file_name=f"Laporan_Cakupan_Layanan_KEK_Ibu_Hamil_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )
# ----------------------------- #
# 🚀 Main Function
# ----------------------------- #
def show_dashboard():
    """Menampilkan dashboard utama untuk indikator ibu hamil."""
    st.title("🤰 Dashboard Indikator Ibu Hamil")
    last_upload_time = get_last_upload_time()
    st.markdown(f"**📅 Data terakhir diperbarui:** {last_upload_time}")

    df, desa_df = load_data()
    if df is None or desa_df is None:
        st.error("❌ Gagal memuat data. Periksa database!")
        return

    # Validasi dan konversi kolom Tahun dan Bulan
    if 'Tahun' in df.columns:
        df['Tahun'] = pd.to_numeric(df['Tahun'], errors='coerce').fillna(0).astype(int)
    else:
        st.error("⚠️ Kolom 'Tahun' tidak ditemukan di dataset!")
        return
    if 'Bulan' in df.columns:
        df['Bulan'] = pd.to_numeric(df['Bulan'], errors='coerce').fillna(0).astype(int)
    else:
        st.error("⚠️ Kolom 'Bulan' tidak ditemukan di dataset!")
        return

    # Sidebar untuk filter
    with st.sidebar.expander("🔎 Filter Data"):
        # Filter Tahun
        tahun_options = ["All"] + sorted(df['Tahun'].dropna().unique().astype(str).tolist())
        tahun_filter = st.selectbox("📅 Pilih Tahun", options=tahun_options)

        # Filter Jenis Laporan
        jenis_laporan = st.radio("📊 Jenis Laporan", ["Bulanan", "Tahunan"])

        # Filter Bulan atau Triwulan
        if jenis_laporan == "Bulanan":
            bulan_options = ["All"] + [str(i) for i in range(1, 13)]
            periode_filter = st.selectbox("📅 Pilih Bulan", options=bulan_options)
            periode_type = "Bulan"
        else:  # Tahunan
            triwulan_options = ["All", "Triwulan 1", "Triwulan 2", "Triwulan 3", "Triwulan 4"]
            periode_filter = st.selectbox("📅 Pilih Triwulan", options=triwulan_options)
            periode_type = "Triwulan"

        # Filter Puskesmas
        puskesmas_filter = st.selectbox("🏥 Pilih Puskesmas", ["All"] + sorted(desa_df['Puskesmas'].unique().tolist()))
        
        # Filter Kelurahan
        kelurahan_options = ["All"]
        if puskesmas_filter != "All":
            kelurahan_options += sorted(desa_df[desa_df['Puskesmas'] == puskesmas_filter]['Kelurahan'].unique().tolist())
        kelurahan_filter = st.selectbox("🏡 Pilih Kelurahan", options=kelurahan_options)

    # Inisialisasi filtered_df
    filtered_df = df.copy()

    # Terapkan filter Tahun
    if tahun_filter != "All":
        try:
            tahun_filter_int = int(tahun_filter)
            filtered_df = filtered_df[filtered_df['Tahun'] == tahun_filter_int]
        except ValueError:
            st.warning("⚠️ Pilihan tahun tidak valid. Menampilkan semua data.")

    # Terapkan filter Periode (Bulan atau Triwulan)
    if periode_type == "Bulan" and periode_filter != "All":
        try:
            bulan_filter_int = int(periode_filter)
            filtered_df = filtered_df[filtered_df['Bulan'] == bulan_filter_int]
        except ValueError:
            st.warning("⚠️ Pilihan bulan tidak valid. Menampilkan semua data.")
    elif periode_type == "Triwulan" and periode_filter != "All":
        triwulan_map = {
            "Triwulan 1": [1, 2, 3],
            "Triwulan 2": [4, 5, 6],
            "Triwulan 3": [7, 8, 9],
            "Triwulan 4": [10, 11, 12]
        }
        bulan_triwulan = triwulan_map.get(periode_filter, [])
        if bulan_triwulan:
            filtered_df = filtered_df[filtered_df['Bulan'].isin(bulan_triwulan)]

    # Terapkan filter Puskesmas dan Kelurahan
    if puskesmas_filter != "All" and 'Puskesmas' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Puskesmas'] == puskesmas_filter]
    if kelurahan_filter != "All" and 'Kelurahan' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Kelurahan'] == kelurahan_filter]

    # Tampilkan data terfilter
    st.subheader("📝 Data Terfilter")
    if filtered_df.empty:
        st.warning("⚠️ Tidak ada data yang sesuai dengan filter.")
    else:
        st.dataframe(filtered_df, use_container_width=True)

    # Menu sidebar untuk analisis (tetap sama)
    menu = st.sidebar.radio("📂 Pilih Dashboard", ["📊 Kelengkapan Data", "📈 Analisis Indikator Ibu Hamil"])

    if menu == "📊 Kelengkapan Data":
        sub_menu = st.sidebar.radio("🔍 Pilih Analisis", ["✅ Compliance Rate", "📋 Completeness Rate"])
        if sub_menu == "✅ Compliance Rate":
            compliance_rate(filtered_df, desa_df, periode_filter, puskesmas_filter, kelurahan_filter)
        elif sub_menu == "📋 Completeness Rate":
            completeness_rate(filtered_df, desa_df, periode_filter, puskesmas_filter, kelurahan_filter)
    elif menu == "📈 Analisis Indikator Ibu Hamil":
        sub_analisis = st.sidebar.radio("📊 Pilih Sub Analisis", [
            "🩺 Cakupan Layanan Kesehatan Ibu Hamil Anemia",
            "💊 Cakupan Suplementasi Gizi Ibu Hamil",
            "📉 Cakupan Layanan Kesehatan Ibu Hamil KEK"
        ])
        if sub_analisis == "🩺 Cakupan Layanan Kesehatan Ibu Hamil Anemia":
            cakupan_layanan_anemia_ibu_hamil(filtered_df, desa_df, periode_filter, puskesmas_filter, kelurahan_filter, periode_type)
        elif sub_analisis == "💊 Cakupan Suplementasi Gizi Ibu Hamil":
            cakupan_suplementasi_gizi_ibu_hamil(filtered_df, desa_df, periode_filter, puskesmas_filter, kelurahan_filter)
        elif sub_analisis == "📉 Cakupan Layanan Kesehatan Ibu Hamil KEK":
            cakupan_layanan_kesehatan_ibu_hamil_kek(filtered_df, desa_df, periode_filter, puskesmas_filter, kelurahan_filter)

    st.markdown(
        '<p style="text-align: center; font-size: 12px; color: grey;">'
        'made with ❤️ by <a href="mailto:dedik2urniawan@gmail.com">dedik2urniawan@gmail.com</a>'
        '</p>', unsafe_allow_html=True)

