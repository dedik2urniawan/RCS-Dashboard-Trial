import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import os
import datetime
import time

# ----------------------------- #
# 📥 Fungsi untuk Load Data
# ----------------------------- #
@st.cache_data
def load_data():
    """Memuat data dari database SQLite rcs_data.db untuk remaja putri."""
    try:
        conn = sqlite3.connect("rcs_data.db")
        df = pd.read_sql_query("SELECT * FROM data_remaja", conn)
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
    """Menghitung dan menampilkan tingkat kepatuhan pelaporan untuk data remaja putri."""
    st.header("✅ Compliance Rate")
    
    # Tambahkan informasi definisi operasional dan insight analisis
    with st.expander("📜 Definisi dan Insight Analisis Kelengkapan Laporan Data", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Analisis Indikator

            Berikut adalah definisi operasional, rumus perhitungan, serta analisis insight dari indikator-indikator yang digunakan untuk memantau kelengkapan dan kepatuhan pelaporan data remaja putri dalam sistem kesehatan masyarakat. Rumus disajikan dalam format matematis untuk kejelasan, dengan penjelasan sederhana untuk memudahkan pemahaman.

            #### 1. Compliance Rate
            - **Definisi Operasional:** Persentase desa atau kelurahan yang telah melaporkan data remaja putri secara lengkap dalam suatu periode tertentu di wilayah kerja tertentu, dibandingkan dengan total desa atau kelurahan yang seharusnya melapor.  
            - **Rumus Perhitungan:**  
            $$ \\text{Compliance Rate (\\%)} = \\frac{\\text{Jumlah Desa/Kelurahan yang Melapor}}{\\text{Jumlah Total Desa/Kelurahan}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase desa atau kelurahan yang sudah mengirimkan laporan dibandingkan dengan semua desa atau kelurahan yang diharapkan melapor, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan secara bulanan dari basis data puskesmas dan desa melalui sistem pelaporan elektronik atau manual, dengan verifikasi terhadap keberadaan laporan dari setiap kelurahan.  
            - **Insight Analisis:** Tingkat kepatuhan pelaporan yang rendah (di bawah 80%) dapat mengindikasikan adanya hambatan logistik, kurangnya pelatihan petugas, atau akses terbatas ke teknologi pelaporan. Persentase ini penting untuk memastikan kualitas data yang digunakan dalam pengambilan keputusan kebijakan kesehatan. Intervensi yang disarankan meliputi pelatihan rutin untuk petugas kesehatan dan peningkatan infrastruktur teknologi informasi.

            #### 2. Completeness Rate
            - **Definisi Operasional:** Persentase entri data remaja putri yang memiliki semua kolom kunci terisi secara lengkap dalam suatu periode tertentu di wilayah kerja tertentu, dibandingkan dengan total entri data yang ada.  
            - **Rumus Perhitungan:**  
            $$ \\text{Completeness Rate (\\%)} = \\frac{\\text{Jumlah Entri Data Lengkap}}{\\text{Jumlah Total Entri Data}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase data yang sudah terisi penuh untuk semua kolom penting (seperti jumlah remaja putri yang mendapat TTD atau skrining anemia) dibandingkan dengan semua data yang dicatat, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui formulir pelaporan bulanan dari puskesmas, dengan validasi otomatis untuk memastikan semua kolom kunci terisi.  
            - **Insight Analisis:** Tingkat kelengkapan data yang rendah (di bawah 90%) dapat mengindikasikan kesalahan pengisian, kurangnya pengawasan, atau kurangnya pemahaman petugas terhadap pentingnya data lengkap. Data yang tidak lengkap dapat menyulitkan analisis epidemiologi dan perencanaan intervensi kesehatan. Peningkatan pelatihan data entry dan penggunaan sistem validasi real-time dapat meningkatkan angka ini.

            </div>
        """, unsafe_allow_html=True)

    # Filter data berdasarkan Bulan, Puskesmas, dan Kelurahan
    desa_terlapor = filtered_df['Kelurahan'].unique()
    total_desa = desa_df.copy()
    
    if bulan_filter != "All":
        bulan_value = int(bulan_filter) if bulan_filter.isdigit() else bulan_filter
        total_desa = total_desa[total_desa['Bulan'] == bulan_value] if 'Bulan' in total_desa.columns else total_desa
        filtered_df = filtered_df[filtered_df['Bulan'] == bulan_value] if 'Bulan' in filtered_df.columns else filtered_df
    if puskesmas_filter != "All":
        total_desa = total_desa[total_desa['Puskesmas'] == puskesmas_filter]
        filtered_df = filtered_df[filtered_df['Puskesmas'] == puskesmas_filter]
    if kelurahan_filter != "All":
        total_desa = total_desa[total_desa['Kelurahan'] == kelurahan_filter]
        filtered_df = filtered_df[filtered_df['Kelurahan'] == kelurahan_filter]

    # Hitung Compliance Rate
    total_desa_count = total_desa['Kelurahan'].nunique()
    desa_lapor_count = len(desa_terlapor)
    compliance_value = (desa_lapor_count / total_desa_count * 100) if total_desa_count else 0

    st.metric(label="Compliance Rate (%)", value=f"{compliance_value:.2f}%")

    # Tentukan iterable untuk bulan
    if bulan_filter == "All" and 'Bulan' in desa_df.columns:
        bulan_iterable = sorted(desa_df['Bulan'].unique())
    else:
        bulan_iterable = [int(bulan_filter)] if bulan_filter != "All" and bulan_filter.isdigit() else [0]

    # Tabel Compliance Rate per Puskesmas
    compliance_data = []
    for bulan in bulan_iterable:
        for puskesmas in sorted(desa_df['Puskesmas'].unique()):
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
    """Menghitung dan menampilkan tingkat kelengkapan data untuk data remaja putri."""
    st.header("📋 Completeness Rate")

    # Tambahkan informasi definisi operasional dan insight analisis
    with st.expander("📜 Definisi dan Insight Analisis Kelengkapan Laporan Data", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Analisis Indikator

            Berikut adalah definisi operasional, rumus perhitungan, serta analisis insight dari indikator-indikator yang digunakan untuk memantau kelengkapan dan kepatuhan pelaporan data remaja putri dalam sistem kesehatan masyarakat. Rumus disajikan dalam format matematis untuk kejelasan, dengan penjelasan sederhana untuk memudahkan pemahaman.

            #### 1. Compliance Rate
            - **Definisi Operasional:** Persentase desa atau kelurahan yang telah melaporkan data remaja putri secara lengkap dalam suatu periode tertentu di wilayah kerja tertentu, dibandingkan dengan total desa atau kelurahan yang seharusnya melapor.  
            - **Rumus Perhitungan:**  
            $$ \\text{Compliance Rate (\\%)} = \\frac{\\text{Jumlah Desa/Kelurahan yang Melapor}}{\\text{Jumlah Total Desa/Kelurahan}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase desa atau kelurahan yang sudah mengirimkan laporan dibandingkan dengan semua desa atau kelurahan yang diharapkan melapor, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan secara bulanan dari basis data puskesmas dan desa melalui sistem pelaporan elektronik atau manual, dengan verifikasi terhadap keberadaan laporan dari setiap kelurahan.  
            - **Insight Analisis:** Tingkat kepatuhan pelaporan yang rendah (di bawah 80%) dapat mengindikasikan adanya hambatan logistik, kurangnya pelatihan petugas, atau akses terbatas ke teknologi pelaporan. Persentase ini penting untuk memastikan kualitas data yang digunakan dalam pengambilan keputusan kebijakan kesehatan. Intervensi yang disarankan meliputi pelatihan rutin untuk petugas kesehatan dan peningkatan infrastruktur teknologi informasi.

            #### 2. Completeness Rate
            - **Definisi Operasional:** Persentase entri data remaja putri yang memiliki semua kolom kunci terisi secara lengkap dalam suatu periode tertentu di wilayah kerja tertentu, dibandingkan dengan total entri data yang ada.  
            - **Rumus Perhitungan:**  
            $$ \\text{Completeness Rate (\\%)} = \\frac{\\text{Jumlah Entri Data Lengkap}}{\\text{Jumlah Total Entri Data}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase data yang sudah terisi penuh untuk semua kolom penting (seperti jumlah remaja putri yang mendapat TTD atau skrining anemia) dibandingkan dengan semua data yang dicatat, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui formulir pelaporan bulanan dari puskesmas, dengan validasi otomatis untuk memastikan semua kolom kunci terisi.  
            - **Insight Analisis:** Tingkat kelengkapan data yang rendah (di bawah 90%) dapat mengindikasikan kesalahan pengisian, kurangnya pengawasan, atau kurangnya pemahaman petugas terhadap pentingnya data lengkap. Data yang tidak lengkap dapat menyulitkan analisis epidemiologi dan perencanaan intervensi kesehatan. Peningkatan pelatihan data entry dan penggunaan sistem validasi real-time dapat meningkatkan angka ini.

            </div>
        """, unsafe_allow_html=True)

    # Daftar kolom kunci untuk cek kelengkapan
    completeness_columns = [
        "Jumlah_sasaran_remaja_putri",
        "Jumlah_remaja_putri_di_satuan_pendidikan_mendapat_TTD_sesuai_standar",
        "Jumlah_remaja_putri_di_satuan_pendidikan_mengonsumsi_TTD_sesuai_standar",
        "Jumlah_remaja_putri_di_satuan_pendidikan_mendapat_TTD_krg26",
        "Jumlah_remaja_putri_di_satuan_pendidikan_mendapat_TTD_lbh26",
        "Jumlah_remaja_putri_di_satuan_pendidikan_mengonsumsi_TTD_krg26",
        "Jumlah_remaja_putri_di_satuan_pendidikan_mengonsumsi_TTD_lbh26",
        "Jumlah_remaja_putri_kelas_7_di_satuan_pendidikan",
        "Jumlah_remaja_putri_kelas_7_di_satuan_pendidikan_skrining_anemia",
        "Jumlah_remaja_putri_kelas_10_di_satuan_pendidikan",
        "Jumlah_remaja_putri_kelas_10_di_satuan_pendidikan_skrining_anemia",
        "Jumlah_remaja_putri_kelas_7_dan_10_di_satuan_pendidikan",
        "Jumlah_remaja_putri_kelas_7_dan_10_di_satuan_pendidikan_skrining_anemia",
        "Jumlah_Rematri_kelas_7_Anemia_Ringan",
        "Jumlah_Rematri_kelas_7_Anemia_Sedang",
        "Jumlah_Rematri_kelas_7_Anemia_Berat",
        "Jumlah_Anemia_Rematri_Kelas_7",
        "Jumlah_Rematri_kelas_10_Anemia_Ringan",
        "Jumlah_Rematri_kelas_10_Anemia_Sedang",
        "Jumlah_Rematri_kelas_10_Anemia_Berat",
        "Jumlah_Anemia_Rematri_Kelas_10",
        "Jumlah_remaja_putri_kelas_7_10_teridentifikasi_anemia",
        "Jumlah_Rematri_kelas_7_dan_10_mendapatkan_tatalaksana_anemia"
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
        scope = scope[scope['Bulan'] == int(bulan_filter)] if 'Bulan' in scope.columns else scope
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
        if bulan_filter != "All" and 'Bulan' in df_pkm.columns:
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
# 💊 Cakupan Suplementasi TTD Rematri
# ----------------------------- #
def cakupan_suplementasi_ttd_rematri(filtered_df, desa_df, bulan_filter, puskesmas_filter, kelurahan_filter):
    """Menampilkan analisis Cakupan Suplementasi TTD Rematri."""
    st.header("💊 Cakupan Suplementasi TTD Rematri")

    # Tambahkan informasi definisi operasional dan insight analisis
    with st.expander("📜 Definisi dan Insight Analisis Cakupan Suplementasi TTD Rematri", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Analisis Indikator

            Berikut adalah definisi operasional, rumus perhitungan, serta analisis insight dari indikator-indikator yang digunakan untuk memantau cakupan suplementasi Tablet Tambah Darah (TTD) untuk remaja putri (Rematri) dalam sistem kesehatan masyarakat.

            #### 1. Cakupan Rematri Mendapat TTD Sesuai Standar
            - **Definisi Operasional:** Persentase remaja putri di satuan pendidikan yang mendapatkan TTD sesuai standar (minimal 26 tablet per tahun) dari total sasaran remaja putri.  
            - **Rumus Perhitungan:**  
            $$ \\text{Cakupan Mendapat TTD Sesuai Standar (\\%)} = \\frac{\\text{Jumlah Rematri Mendapat TTD Sesuai Standar}}{\\text{Jumlah Sasaran Rematri}} \\times 100 $$  
            - **Target:** 85%  
            - **Insight Analisis:** Jika cakupan di bawah target, ini dapat mengindikasikan masalah distribusi TTD atau kurangnya koordinasi dengan satuan pendidikan. Intervensi yang disarankan meliputi peningkatan logistik dan edukasi kepada petugas kesehatan.

            #### 2. Cakupan Rematri Mengkonsumsi TTD Sesuai Standar
            - **Definisi Operasional:** Persentase remaja putri di satuan pendidikan yang mengkonsumsi TTD sesuai standar (minimal 26 tablet per tahun) dari total sasaran remaja putri.  
            - **Rumus Perhitungan:**  
            $$ \\text{Cakupan Mengkonsumsi TTD Sesuai Standar (\\%)} = \\frac{\\text{Jumlah Rematri Mengkonsumsi TTD Sesuai Standar}}{\\text{Jumlah Sasaran Rematri}} \\times 100 $$  
            - **Target:** 63%  
            - **Insight Analisis:** Cakupan konsumsi yang rendah dapat disebabkan oleh kurangnya kesadaran remaja putri tentang pentingnya TTD atau efek samping yang dirasakan. Edukasi gizi dan konseling di satuan pendidikan dapat membantu meningkatkan angka ini.

            #### 3. Cakupan Rematri Mendapat/Mengkonsumsi TTD < 26 Tablet dan ≥ 26 Tablet
            - **Definisi Operasional:** Persentase remaja putri yang mendapat atau mengkonsumsi TTD kurang dari 26 tablet atau lebih dari/ sama dengan 26 tablet dari total sasaran remaja putri.  
            - **Rumus Perhitungan:**  
            $$ \\text{Cakupan (\\%)} = \\frac{\\text{Jumlah Rematri pada Kategori Tertentu}}{\\text{Jumlah Sasaran Rematri}} \\times 100 $$  
            - **Insight Analisis:** Data ini membantu mengidentifikasi distribusi dan konsumsi TTD yang tidak merata. Fokus pada remaja yang mendapat/mengkonsumsi < 26 tablet untuk intervensi lebih lanjut.

            </div>
        """, unsafe_allow_html=True)

    # Import tambahan untuk PDF
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    # Kolom kunci untuk perhitungan
    required_columns = [
        "Jumlah_sasaran_remaja_putri",
        "Jumlah_remaja_putri_di_satuan_pendidikan_mendapat_TTD_sesuai_standar",
        "Jumlah_remaja_putri_di_satuan_pendidikan_mendapat_TTD_krg26",
        "Jumlah_remaja_putri_di_satuan_pendidikan_mendapat_TTD_lbh26",
        "Jumlah_remaja_putri_di_satuan_pendidikan_mengonsumsi_TTD_sesuai_standar",
        "Jumlah_remaja_putri_di_satuan_pendidikan_mengonsumsi_TTD_krg26",
        "Jumlah_remaja_putri_di_satuan_pendidikan_mengonsumsi_TTD_lbh26"
    ]

    # Cek kolom yang hilang di dataset
    missing_cols = [col for col in required_columns if col not in filtered_df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di dataset: {missing_cols}")
        return

    # Hitung metrik
    total_sasaran = filtered_df["Jumlah_sasaran_remaja_putri"].sum()
    if total_sasaran == 0:
        st.warning("⚠️ Tidak ada data sasaran remaja putri untuk filter yang dipilih.")
        return

    # Metrik a: Rematri mendapat TTD sesuai Standar
    mendapat_sesuai_standar = filtered_df["Jumlah_remaja_putri_di_satuan_pendidikan_mendapat_TTD_sesuai_standar"].sum()
    metric_a = (mendapat_sesuai_standar / total_sasaran * 100) if total_sasaran else 0
    target_a = 85
    gap_a = metric_a - target_a
    status_a = "Diatas Target" if metric_a > target_a else "Dibawah Target"
    color_a = "green" if metric_a > target_a else "red"
    arrow_a = "⬆️" if metric_a > target_a else "⬇️"

    # Metrik b: Rematri mendapat TTD < 26 Tablet
    mendapat_krg26 = filtered_df["Jumlah_remaja_putri_di_satuan_pendidikan_mendapat_TTD_krg26"].sum()
    metric_b = (mendapat_krg26 / total_sasaran * 100) if total_sasaran else 0

    # Metrik c: Rematri mendapat TTD >= 26 Tablet
    mendapat_lbh26 = filtered_df["Jumlah_remaja_putri_di_satuan_pendidikan_mendapat_TTD_lbh26"].sum()
    metric_c = (mendapat_lbh26 / total_sasaran * 100) if total_sasaran else 0

    # Metrik d: Rematri mengkonsumsi TTD sesuai Standar
    konsumsi_sesuai_standar = filtered_df["Jumlah_remaja_putri_di_satuan_pendidikan_mengonsumsi_TTD_sesuai_standar"].sum()
    metric_d = (konsumsi_sesuai_standar / total_sasaran * 100) if total_sasaran else 0
    target_d = 63
    gap_d = metric_d - target_d
    status_d = "Diatas Target" if metric_d > target_d else "Dibawah Target"
    color_d = "green" if metric_d > target_d else "red"
    arrow_d = "⬆️" if metric_d > target_d else "⬇️"

    # Metrik e: Rematri mengkonsumsi TTD < 26 Tablet
    konsumsi_krg26 = filtered_df["Jumlah_remaja_putri_di_satuan_pendidikan_mengonsumsi_TTD_krg26"].sum()
    metric_e = (konsumsi_krg26 / total_sasaran * 100) if total_sasaran else 0

    # Metrik f: Rematri mengkonsumsi TTD >= 26 Tablet
    konsumsi_lbh26 = filtered_df["Jumlah_remaja_putri_di_satuan_pendidikan_mengonsumsi_TTD_lbh26"].sum()
    metric_f = (konsumsi_lbh26 / total_sasaran * 100) if total_sasaran else 0

    # Score Card dalam 2 kolom
    st.subheader("📊 Score Card Cakupan Suplementasi TTD Rematri")
    col1, col2 = st.columns(2)

    with col1:
        # Metrik a
        st.metric(
            label="Rematri Mendapat TTD Sesuai Standar (%)",
            value=f"{metric_a:.2f}%",
            delta=f"{arrow_a} {status_a} (Gap: {abs(gap_a):.2f}%)",
            delta_color="normal" if color_a == "green" else "inverse"
        )
        # Metrik b
        st.metric(
            label="Rematri Mendapat TTD < 26 Tablet (%)",
            value=f"{metric_b:.2f}%"
        )
        # Metrik c
        st.metric(
            label="Rematri Mendapat TTD ≥ 26 Tablet (%)",
            value=f"{metric_c:.2f}%"
        )

    with col2:
        # Metrik d
        st.metric(
            label="Rematri Mengkonsumsi TTD Sesuai Standar (%)",
            value=f"{metric_d:.2f}%",
            delta=f"{arrow_d} {status_d} (Gap: {abs(gap_d):.2f}%)",
            delta_color="normal" if color_d == "green" else "inverse"
        )
        # Metrik e
        st.metric(
            label="Rematri Mengkonsumsi TTD < 26 Tablet (%)",
            value=f"{metric_e:.2f}%"
        )
        # Metrik f
        st.metric(
            label="Rematri Mengkonsumsi TTD ≥ 26 Tablet (%)",
            value=f"{metric_f:.2f}%"
        )

    # Grafik 1: Cakupan Rematri Mendapatkan TTD
    st.subheader("📈 Grafik Cakupan Rematri Mendapatkan TTD")
    level = "Kelurahan" if puskesmas_filter != "All" else "Puskesmas"
    grouped_df = filtered_df.groupby(level).sum(numeric_only=True).reset_index()

    # Hitung metrik per level (Puskesmas/Kelurahan)
    grouped_df["Mendapat TTD Sesuai Standar (%)"] = (grouped_df["Jumlah_remaja_putri_di_satuan_pendidikan_mendapat_TTD_sesuai_standar"] / grouped_df["Jumlah_sasaran_remaja_putri"] * 100).fillna(0)
    grouped_df["Mendapat TTD < 26 Tablet (%)"] = (grouped_df["Jumlah_remaja_putri_di_satuan_pendidikan_mendapat_TTD_krg26"] / grouped_df["Jumlah_sasaran_remaja_putri"] * 100).fillna(0)
    grouped_df["Mendapat TTD ≥ 26 Tablet (%)"] = (grouped_df["Jumlah_remaja_putri_di_satuan_pendidikan_mendapat_TTD_lbh26"] / grouped_df["Jumlah_sasaran_remaja_putri"] * 100).fillna(0)

    # Reshape data untuk bar chart
    plot_df = grouped_df.melt(id_vars=[level], value_vars=["Mendapat TTD Sesuai Standar (%)", "Mendapat TTD < 26 Tablet (%)", "Mendapat TTD ≥ 26 Tablet (%)"],
                              var_name="Metrik", value_name="Persentase")

    # Buat bar chart dengan 3 warna berbeda
    fig_mendapat = px.bar(plot_df, x=level, y="Persentase", color="Metrik",
                          title=f"📊 Cakupan Rematri Mendapatkan TTD per {level}",
                          color_discrete_map={
                              "Mendapat TTD Sesuai Standar (%)": "#00C49F",
                              "Mendapat TTD < 26 Tablet (%)": "#FF6F61",
                              "Mendapat TTD ≥ 26 Tablet (%)": "#FFB347"
                          },
                          text=plot_df["Persentase"].apply(lambda x: f"{x:.2f}%"))

    # Tambahkan garis target 85% untuk Metrik a
    fig_mendapat.add_hline(y=85, line_dash="dash", line_color="red",
                           annotation_text="Target: 85%", annotation_position="top right")

    fig_mendapat.update_traces(textposition='outside')
    fig_mendapat.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", xaxis_title=level,
                              yaxis_range=[0, 110], title_x=0.5, height=500, barmode='group')
    st.plotly_chart(fig_mendapat, key=f"mendapat_ttd_chart_{bulan_filter}_{puskesmas_filter}_{kelurahan_filter}_{time.time()}", use_container_width=True)

    # Grafik 2: Cakupan Rematri Mengkonsumsi TTD
    st.subheader("📈 Grafik Cakupan Rematri Mengkonsumsi TTD")
    grouped_df["Mengkonsumsi TTD Sesuai Standar (%)"] = (grouped_df["Jumlah_remaja_putri_di_satuan_pendidikan_mengonsumsi_TTD_sesuai_standar"] / grouped_df["Jumlah_sasaran_remaja_putri"] * 100).fillna(0)
    grouped_df["Mengkonsumsi TTD < 26 Tablet (%)"] = (grouped_df["Jumlah_remaja_putri_di_satuan_pendidikan_mengonsumsi_TTD_krg26"] / grouped_df["Jumlah_sasaran_remaja_putri"] * 100).fillna(0)
    grouped_df["Mengkonsumsi TTD ≥ 26 Tablet (%)"] = (grouped_df["Jumlah_remaja_putri_di_satuan_pendidikan_mengonsumsi_TTD_lbh26"] / grouped_df["Jumlah_sasaran_remaja_putri"] * 100).fillna(0)

    # Reshape data untuk bar chart
    plot_df_konsumsi = grouped_df.melt(id_vars=[level], value_vars=["Mengkonsumsi TTD Sesuai Standar (%)", "Mengkonsumsi TTD < 26 Tablet (%)", "Mengkonsumsi TTD ≥ 26 Tablet (%)"],
                                       var_name="Metrik", value_name="Persentase")

    # Buat bar chart dengan 3 warna berbeda
    fig_konsumsi = px.bar(plot_df_konsumsi, x=level, y="Persentase", color="Metrik",
                          title=f"📊 Cakupan Rematri Mengkonsumsi TTD per {level}",
                          color_discrete_map={
                              "Mengkonsumsi TTD Sesuai Standar (%)": "#00C49F",
                              "Mengkonsumsi TTD < 26 Tablet (%)": "#FF6F61",
                              "Mengkonsumsi TTD ≥ 26 Tablet (%)": "#FFB347"
                          },
                          text=plot_df_konsumsi["Persentase"].apply(lambda x: f"{x:.2f}%"))

    # Tambahkan garis target 63% untuk Metrik d
    fig_konsumsi.add_hline(y=63, line_dash="dash", line_color="red",
                           annotation_text="Target: 63%", annotation_position="top right")

    fig_konsumsi.update_traces(textposition='outside')
    fig_konsumsi.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", xaxis_title=level,
                              yaxis_range=[0, 110], title_x=0.5, height=500, barmode='group')
    st.plotly_chart(fig_konsumsi, key=f"konsumsi_ttd_chart_{bulan_filter}_{puskesmas_filter}_{kelurahan_filter}_{time.time()}", use_container_width=True)

    # Tabel Rekapitulasi
    st.subheader("📋 Tabel Rekapitulasi Cakupan Suplementasi TTD Rematri")
    rekap_data = []
    for index, row in grouped_df.iterrows():
        rekap_data.append({
            level: row[level],
            "Mendapat TTD Sesuai Standar (%)": f"{row['Mendapat TTD Sesuai Standar (%)']:.2f}%",
            "Mendapat TTD < 26 Tablet (%)": f"{row['Mendapat TTD < 26 Tablet (%)']:.2f}%",
            "Mendapat TTD ≥ 26 Tablet (%)": f"{row['Mendapat TTD ≥ 26 Tablet (%)']:.2f}%",
            "Mengkonsumsi TTD Sesuai Standar (%)": f"{row['Mengkonsumsi TTD Sesuai Standar (%)']:.2f}%",
            "Mengkonsumsi TTD < 26 Tablet (%)": f"{row['Mengkonsumsi TTD < 26 Tablet (%)']:.2f}%",
            "Mengkonsumsi TTD ≥ 26 Tablet (%)": f"{row['Mengkonsumsi TTD ≥ 26 Tablet (%)']:.2f}%"
        })

    rekap_df = pd.DataFrame(rekap_data)
    st.dataframe(rekap_df, use_container_width=True)

    # 4. Fitur Download Laporan PDF
    st.subheader("📥 Unduh Laporan")
    def generate_pdf_report():
        # Buat buffer untuk menyimpan grafik
        img_buffer1 = BytesIO()
        img_buffer2 = BytesIO()
        fig_mendapat.write_image(img_buffer1, format='png', width=600, height=400, scale=2)
        fig_konsumsi.write_image(img_buffer2, format='png', width=600, height=400, scale=2)
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
        elements.append(Paragraph("Laporan Cakupan Suplementasi TTD Rematri", title_style))
        elements.append(Paragraph(f"Diperbarui: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
        elements.append(Spacer(1, 12))

        # Tambahkan Metrik
        elements.append(Paragraph("1. Metrik Cakupan Suplementasi TTD", normal_style))
        metrik_list = [
            ("Rematri Mendapat TTD Sesuai Standar (%)", metric_a),
            ("Rematri Mendapat TTD < 26 Tablet (%)", metric_b),
            ("Rematri Mendapat TTD ≥ 26 Tablet (%)", metric_c),
            ("Rematri Mengkonsumsi TTD Sesuai Standar (%)", metric_d),
            ("Rematri Mengkonsumsi TTD < 26 Tablet (%)", metric_e),
            ("Rematri Mengkonsumsi TTD ≥ 26 Tablet (%)", metric_f)
        ]
        targets = {
            "Rematri Mendapat TTD Sesuai Standar (%)": 85,
            "Rematri Mengkonsumsi TTD Sesuai Standar (%)": 63
        }
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
        elements.append(Paragraph("2. Grafik Cakupan Rematri Mendapatkan TTD", normal_style))
        elements.append(Image(img_buffer1, width=500, height=300))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("3. Grafik Cakupan Rematri Mengkonsumsi TTD", normal_style))
        elements.append(Image(img_buffer2, width=500, height=300))
        elements.append(Spacer(1, 12))

        # Tambahkan Tabel Rekapitulasi
        elements.append(Paragraph("4. Tabel Rekapitulasi", normal_style))
        table_data = [rekap_df.columns.tolist()] + rekap_df.values.tolist()
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
            file_name=f"Laporan_Cakupan_Suplementasi_TTD_Rematri_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )

# ----------------------------- #
# 🔍 Cakupan Rematri Skrining Anemia
# ----------------------------- #
def cakupan_rematri_skrining_anemia(filtered_df, desa_df, bulan_filter, puskesmas_filter, kelurahan_filter):
    """Menampilkan analisis Cakupan Rematri Skrining Anemia."""
    st.header("🔍 Cakupan Rematri Skrining Anemia")

    # Tambahkan informasi definisi operasional dan insight analisis
    with st.expander("📜 Definisi dan Insight Analisis Cakupan Rematri Skrining Anemia", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Analisis Indikator

            Berikut adalah definisi operasional, rumus perhitungan, serta analisis insight dari indikator-indikator yang digunakan untuk memantau cakupan skrining anemia pada remaja putri (Rematri) di satuan pendidikan.

            #### 1. Cakupan Rematri Kelas 7 Skrining Anemia
            - **Definisi Operasional:** Persentase remaja putri kelas 7 di satuan pendidikan yang menjalani skrining anemia dari total remaja putri kelas 7.  
            - **Rumus Perhitungan:**  
            $$ \\text{Cakupan Kelas 7 (\\%)} = \\frac{\\text{Jumlah Rematri Kelas 7 Skrining Anemia}}{\\text{Jumlah Rematri Kelas 7}} \\times 100 $$  
            - **Target:** 75%  
            - **Insight Analisis:** Cakupan di bawah target dapat menunjukkan rendahnya kesadaran atau akses ke layanan skrining. Intervensi seperti kampanye kesehatan sekolah dapat meningkatkan angka ini.

            #### 2. Cakupan Rematri Kelas 10 Skrining Anemia
            - **Definisi Operasional:** Persentase remaja putri kelas 10 di satuan pendidikan yang menjalani skrining anemia dari total remaja putri kelas 10.  
            - **Rumus Perhitungan:**  
            $$ \\text{Cakupan Kelas 10 (\\%)} = \\frac{\\text{Jumlah Rematri Kelas 10 Skrining Anemia}}{\\text{Jumlah Rematri Kelas 10}} \\times 100 $$  
            - **Target:** 75%  
            - **Insight Analisis:** Rendahnya cakupan dapat terkait dengan kurangnya tenaga medis atau alat skrining. Peningkatan fasilitas kesehatan di sekolah diperlukan.

            #### 3. Cakupan Rematri Kelas 7 & 10 Skrining Anemia
            - **Definisi Operasional:** Persentase remaja putri kelas 7 dan 10 secara keseluruhan yang menjalani skrining anemia dari total remaja putri kelas 7 dan 10.  
            - **Rumus Perhitungan:**  
            $$ \\text{Cakupan Kelas 7 dan 10 (\\%)} = \\frac{\\text{Jumlah Rematri Kelas 7 dan 10 Skrining Anemia}}{\\text{Jumlah Rematri Kelas 7 dan 10}} \\times 100 $$  
            - **Target:** 75%  
            - **Insight Analisis:** Data ini memberikan gambaran keseluruhan efektivitas program skrining. Jika rendah, evaluasi terhadap cakupan per kelas dapat membantu menentukan prioritas intervensi.

            </div>
        """, unsafe_allow_html=True)

    # Import tambahan untuk PDF
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    # Kolom kunci untuk perhitungan
    required_columns = [
        "Jumlah_remaja_putri_kelas_7_di_satuan_pendidikan",
        "Jumlah_remaja_putri_kelas_7_di_satuan_pendidikan_skrining_anemia",
        "Jumlah_remaja_putri_kelas_10_di_satuan_pendidikan",
        "Jumlah_remaja_putri_kelas_10_di_satuan_pendidikan_skrining_anemia",
        "Jumlah_remaja_putri_kelas_7_dan_10_di_satuan_pendidikan",
        "Jumlah_remaja_putri_kelas_7_dan_10_di_satuan_pendidikan_skrining_anemia"
    ]

    # Cek kolom yang hilang di dataset
    missing_cols = [col for col in required_columns if col not in filtered_df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di dataset: {missing_cols}")
        return

    # Hitung metrik
    # Metrik a: Rematri kelas 7 skrining anemia
    total_kelas_7 = filtered_df["Jumlah_remaja_putri_kelas_7_di_satuan_pendidikan"].sum()
    skrining_kelas_7 = filtered_df["Jumlah_remaja_putri_kelas_7_di_satuan_pendidikan_skrining_anemia"].sum()
    metric_a = (skrining_kelas_7 / total_kelas_7 * 100) if total_kelas_7 else 0
    target = 75
    gap_a = metric_a - target
    status_a = "Diatas Target" if metric_a > target else "Dibawah Target"
    color_a = "green" if metric_a > target else "red"
    arrow_a = "⬆️" if metric_a > target else "⬇️"

    # Metrik b: Rematri kelas 10 skrining anemia
    total_kelas_10 = filtered_df["Jumlah_remaja_putri_kelas_10_di_satuan_pendidikan"].sum()
    skrining_kelas_10 = filtered_df["Jumlah_remaja_putri_kelas_10_di_satuan_pendidikan_skrining_anemia"].sum()
    metric_b = (skrining_kelas_10 / total_kelas_10 * 100) if total_kelas_10 else 0
    gap_b = metric_b - target
    status_b = "Diatas Target" if metric_b > target else "Dibawah Target"
    color_b = "green" if metric_b > target else "red"
    arrow_b = "⬆️" if metric_b > target else "⬇️"

    # Metrik c: Rematri kelas 7 & 10 skrining anemia
    total_kelas_7_10 = filtered_df["Jumlah_remaja_putri_kelas_7_dan_10_di_satuan_pendidikan"].sum()
    skrining_kelas_7_10 = filtered_df["Jumlah_remaja_putri_kelas_7_dan_10_di_satuan_pendidikan_skrining_anemia"].sum()
    metric_c = (skrining_kelas_7_10 / total_kelas_7_10 * 100) if total_kelas_7_10 else 0
    gap_c = metric_c - target
    status_c = "Diatas Target" if metric_c > target else "Dibawah Target"
    color_c = "green" if metric_c > target else "red"
    arrow_c = "⬆️" if metric_c > target else "⬇️"

    # Score Card dalam 2 kolom
    st.subheader("📊 Score Card Cakupan Rematri Skrining Anemia")
    col1, col2 = st.columns(2)

    with col1:
        # Metrik a
        st.metric(
            label="Rematri Kelas 7 Skrining Anemia (%)",
            value=f"{metric_a:.2f}%",
            delta=f"{arrow_a} {status_a} (Gap: {abs(gap_a):.2f}%)",
            delta_color="normal" if color_a == "green" else "inverse"
        )

    with col2:
        # Metrik b
        st.metric(
            label="Rematri Kelas 10 Skrining Anemia (%)",
            value=f"{metric_b:.2f}%",
            delta=f"{arrow_b} {status_b} (Gap: {abs(gap_b):.2f}%)",
            delta_color="normal" if color_b == "green" else "inverse"
        )
        # Metrik c
        st.metric(
            label="Rematri Kelas 7 & 10 Skrining Anemia (%)",
            value=f"{metric_c:.2f}%",
            delta=f"{arrow_c} {status_c} (Gap: {abs(gap_c):.2f}%)",
            delta_color="normal" if color_c == "green" else "inverse"
        )

    # Grafik: Cakupan Rematri Skrining Anemia
    st.subheader("📈 Grafik Cakupan Rematri Skrining Anemia")
    level = "Kelurahan" if puskesmas_filter != "All" else "Puskesmas"
    grouped_df = filtered_df.groupby(level).sum(numeric_only=True).reset_index()

    # Hitung metrik per level (Puskesmas/Kelurahan)
    grouped_df["Kelas 7 Skrining Anemia (%)"] = (grouped_df["Jumlah_remaja_putri_kelas_7_di_satuan_pendidikan_skrining_anemia"] / grouped_df["Jumlah_remaja_putri_kelas_7_di_satuan_pendidikan"] * 100).fillna(0)
    grouped_df["Kelas 10 Skrining Anemia (%)"] = (grouped_df["Jumlah_remaja_putri_kelas_10_di_satuan_pendidikan_skrining_anemia"] / grouped_df["Jumlah_remaja_putri_kelas_10_di_satuan_pendidikan"] * 100).fillna(0)
    grouped_df["Kelas 7 & 10 Skrining Anemia (%)"] = (grouped_df["Jumlah_remaja_putri_kelas_7_dan_10_di_satuan_pendidikan_skrining_anemia"] / grouped_df["Jumlah_remaja_putri_kelas_7_dan_10_di_satuan_pendidikan"] * 100).fillna(0)

    # Reshape data untuk bar chart
    plot_df = grouped_df.melt(id_vars=[level], value_vars=["Kelas 7 Skrining Anemia (%)", "Kelas 10 Skrining Anemia (%)", "Kelas 7 & 10 Skrining Anemia (%)"],
                              var_name="Metrik", value_name="Persentase")

    # Buat bar chart dengan 3 warna berbeda
    fig = px.bar(plot_df, x=level, y="Persentase", color="Metrik",
                 title=f"📊 Cakupan Rematri Skrining Anemia per {level}",
                 color_discrete_map={
                     "Kelas 7 Skrining Anemia (%)": "#00C49F",
                     "Kelas 10 Skrining Anemia (%)": "#FF6F61",
                     "Kelas 7 & 10 Skrining Anemia (%)": "#FFB347"
                 },
                 text=plot_df["Persentase"].apply(lambda x: f"{x:.2f}%"))

    # Tambahkan garis target 75%
    fig.add_hline(y=75, line_dash="dash", line_color="red",
                  annotation_text="Target: 75%", annotation_position="top right")

    fig.update_traces(textposition='outside')
    fig.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", xaxis_title=level,
                      yaxis_range=[0, 110], title_x=0.5, height=500, barmode='group')
    st.plotly_chart(fig, key=f"skrining_anemia_chart_{bulan_filter}_{puskesmas_filter}_{kelurahan_filter}_{time.time()}", use_container_width=True)

    # Tabel Rekapitulasi
    st.subheader("📋 Tabel Rekapitulasi Cakupan Rematri Skrining Anemia")
    rekap_data = []
    for index, row in grouped_df.iterrows():
        rekap_data.append({
            level: row[level],
            "Kelas 7 Skrining Anemia (%)": f"{row['Kelas 7 Skrining Anemia (%)']:.2f}%",
            "Kelas 10 Skrining Anemia (%)": f"{row['Kelas 10 Skrining Anemia (%)']:.2f}%",
            "Kelas 7 & 10 Skrining Anemia (%)": f"{row['Kelas 7 & 10 Skrining Anemia (%)']:.2f}%"
        })

    rekap_df = pd.DataFrame(rekap_data)
    st.dataframe(rekap_df, use_container_width=True)

    # 4. Fitur Download Laporan PDF
    st.subheader("📥 Unduh Laporan")
    def generate_pdf_report():
        # Buat buffer untuk menyimpan grafik
        img_buffer = BytesIO()
        fig.write_image(img_buffer, format='png', width=600, height=400, scale=2)
        img_buffer.seek(0)

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
        elements.append(Paragraph("Laporan Cakupan Rematri Skrining Anemia", title_style))
        elements.append(Paragraph(f"Diperbarui: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
        elements.append(Spacer(1, 12))

        # Tambahkan Metrik
        elements.append(Paragraph("1. Metrik Cakupan Skrining Anemia", normal_style))
        metrik_list = [
            ("Rematri Kelas 7 Skrining Anemia (%)", metric_a),
            ("Rematri Kelas 10 Skrining Anemia (%)", metric_b),
            ("Rematri Kelas 7 & 10 Skrining Anemia (%)", metric_c)
        ]
        targets = {
            "Rematri Kelas 7 Skrining Anemia (%)": 75,
            "Rematri Kelas 10 Skrining Anemia (%)": 75,
            "Rematri Kelas 7 & 10 Skrining Anemia (%)": 75
        }
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
        elements.append(Paragraph("2. Grafik Cakupan Rematri Skrining Anemia", normal_style))
        elements.append(Image(img_buffer, width=500, height=300))
        elements.append(Spacer(1, 12))

        # Tambahkan Tabel Rekapitulasi
        elements.append(Paragraph("3. Tabel Rekapitulasi", normal_style))
        table_data = [rekap_df.columns.tolist()] + rekap_df.values.tolist()
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
            file_name=f"Laporan_Cakupan_Skrining_Anemia_Rematri_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )
# ----------------------------- #
# 📉 Prevalensi Anemia Rematri
# ----------------------------- #
def prevalensi_anemia_rematri(filtered_df, desa_df, bulan_filter, puskesmas_filter, kelurahan_filter):
    """Menampilkan analisis Prevalensi Anemia Rematri."""
    st.header("📉 Prevalensi Anemia Rematri")

    # Tambahkan informasi definisi operasional dan insight analisis
    with st.expander("📜 Definisi dan Insight Analisis Prevalensi Anemia Rematri", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Analisis Indikator

            Berikut adalah definisi operasional, rumus perhitungan, serta analisis insight dari indikator-indikator yang digunakan untuk memantau prevalensi anemia pada remaja putri (Rematri) di satuan pendidikan.

            #### 1. Prevalensi Anemia Rematri Kelas 7
            - **Definisi Operasional:** Persentase remaja putri kelas 7 yang teridentifikasi anemia (ringan, sedang, atau berat) dari total remaja putri kelas 7 yang telah diskrining anemia.  
            - **Rumus Perhitungan:**  
            $$ \\text{Prevalensi Anemia Kelas 7 (\\%)} = \\frac{\\text{Jumlah Anemia Rematri Kelas 7}}{\\text{Jumlah Rematri Kelas 7 yang Diskrining}} \\times 100 $$  
            - **Target:** 25% (semakin rendah dari target, semakin baik)  
            - **Insight Analisis:** Prevalensi di atas target menunjukkan tingginya kasus anemia. Intervensi seperti suplementasi TTD dan edukasi gizi perlu ditingkatkan.

            #### 2. Prevalensi Anemia Rematri Kelas 10
            - **Definisi Operasional:** Persentase remaja putri kelas 10 yang teridentifikasi anemia (ringan, sedang, atau berat) dari total remaja putri kelas 10 yang telah diskrining anemia.  
            - **Rumus Perhitungan:**  
            $$ \\text{Prevalensi Anemia Kelas 10 (\\%)} = \\frac{\\text{Jumlah Anemia Rematri Kelas 10}}{\\text{Jumlah Rematri Kelas 10 yang Diskrining}} \\times 100 $$  
            - **Target:** 25% (semakin rendah dari target, semakin baik)  
            - **Insight Analisis:** Prevalensi tinggi dapat terkait dengan faktor gizi atau kepatuhan konsumsi TTD. Program edukasi dan monitoring perlu diperkuat.

            #### 3. Prevalensi Anemia Rematri Kelas 7 dan 10
            - **Definisi Operasional:** Persentase remaja putri kelas 7 dan 10 secara keseluruhan yang teridentifikasi anemia dari total remaja putri kelas 7 dan 10 yang telah diskrining anemia.  
            - **Rumus Perhitungan:**  
            $$ \\text{Prevalensi Anemia Kelas 7 dan 10 (\\%)} = \\frac{\\text{Jumlah Rematri Kelas 7 dan 10 Teridentifikasi Anemia}}{\\text{Jumlah Rematri Kelas 7 dan 10 yang Diskrining}} \\times 100 $$  
            - **Target:** 25% (semakin rendah dari target, semakin baik)  
            - **Insight Analisis:** Data ini memberikan gambaran keseluruhan prevalensi anemia. Jika tinggi, intervensi harus mencakup semua kelompok usia rematri.

            #### 4. Prevalensi Berdasarkan Tingkat Keparahan
            - **Definisi Operasional:** Persentase remaja putri kelas 7 atau 10 yang teridentifikasi anemia ringan, sedang, atau berat dari total yang telah diskrining.  
            - **Rumus Perhitungan:**  
            $$ \\text{Prevalensi Keparahan (\\%)} = \\frac{\\text{Jumlah Rematri dengan Keparahan Tertentu}}{\\text{Jumlah Rematri yang Diskrining}} \\times 100 $$  
            - **Insight Analisis:** Data ini membantu mengidentifikasi tingkat keparahan anemia untuk menentukan prioritas intervensi medis.

            </div>
        """, unsafe_allow_html=True)

    # Import tambahan untuk PDF
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    # Kolom kunci untuk perhitungan
    required_columns = [
        "Jumlah_remaja_putri_kelas_7_di_satuan_pendidikan_skrining_anemia",
        "Jumlah_Rematri_kelas_7_Anemia_Ringan",
        "Jumlah_Rematri_kelas_7_Anemia_Sedang",
        "Jumlah_Rematri_kelas_7_Anemia_Berat",
        "Jumlah_Anemia_Rematri_Kelas_7",
        "Jumlah_remaja_putri_kelas_10_di_satuan_pendidikan_skrining_anemia",
        "Jumlah_Rematri_kelas_10_Anemia_Ringan",
        "Jumlah_Rematri_kelas_10_Anemia_Sedang",
        "Jumlah_Rematri_kelas_10_Anemia_Berat",
        "Jumlah_Anemia_Rematri_Kelas_10",
        "Jumlah_remaja_putri_kelas_7_dan_10_di_satuan_pendidikan_skrining_anemia",
        "Jumlah_remaja_putri_kelas_7_10_teridentifikasi_anemia"
    ]

    # Cek kolom yang hilang di dataset
    missing_cols = [col for col in required_columns if col not in filtered_df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di dataset: {missing_cols}")
        return

    # Hitung metrik
    # Kelas 7
    total_skrining_kelas_7 = filtered_df["Jumlah_remaja_putri_kelas_7_di_satuan_pendidikan_skrining_anemia"].sum()
    if total_skrining_kelas_7 == 0:
        st.warning("⚠️ Tidak ada data remaja putri kelas 7 yang diskrining anemia untuk filter yang dipilih.")
        return

    # Metrik a: Rematri kelas 7 teridentifikasi Anemia Ringan
    anemia_ringan_kelas_7 = filtered_df["Jumlah_Rematri_kelas_7_Anemia_Ringan"].sum()
    metric_a = (anemia_ringan_kelas_7 / total_skrining_kelas_7 * 100) if total_skrining_kelas_7 else 0

    # Metrik b: Rematri kelas 7 teridentifikasi Anemia Sedang
    anemia_sedang_kelas_7 = filtered_df["Jumlah_Rematri_kelas_7_Anemia_Sedang"].sum()
    metric_b = (anemia_sedang_kelas_7 / total_skrining_kelas_7 * 100) if total_skrining_kelas_7 else 0

    # Metrik c: Rematri kelas 7 teridentifikasi Anemia Berat
    anemia_berat_kelas_7 = filtered_df["Jumlah_Rematri_kelas_7_Anemia_Berat"].sum()
    metric_c = (anemia_berat_kelas_7 / total_skrining_kelas_7 * 100) if total_skrining_kelas_7 else 0

    # Metrik d: Rematri kelas 7 teridentifikasi Anemia
    anemia_total_kelas_7 = filtered_df["Jumlah_Anemia_Rematri_Kelas_7"].sum()
    metric_d = (anemia_total_kelas_7 / total_skrining_kelas_7 * 100) if total_skrining_kelas_7 else 0
    target = 25
    gap_d = metric_d - target
    status_d = "Dibawah Target" if metric_d < target else "Diatas Target"
    color_d = "green" if metric_d < target else "red"
    arrow_d = "⬇️" if metric_d < target else "⬆️"

    # Kelas 10
    total_skrining_kelas_10 = filtered_df["Jumlah_remaja_putri_kelas_10_di_satuan_pendidikan_skrining_anemia"].sum()
    if total_skrining_kelas_10 == 0:
        st.warning("⚠️ Tidak ada data remaja putri kelas 10 yang diskrining anemia untuk filter yang dipilih.")
        return

    # Metrik e: Rematri kelas 10 teridentifikasi Anemia Ringan
    anemia_ringan_kelas_10 = filtered_df["Jumlah_Rematri_kelas_10_Anemia_Ringan"].sum()
    metric_e = (anemia_ringan_kelas_10 / total_skrining_kelas_10 * 100) if total_skrining_kelas_10 else 0

    # Metrik f: Rematri kelas 10 teridentifikasi Anemia Sedang
    anemia_sedang_kelas_10 = filtered_df["Jumlah_Rematri_kelas_10_Anemia_Sedang"].sum()
    metric_f = (anemia_sedang_kelas_10 / total_skrining_kelas_10 * 100) if total_skrining_kelas_10 else 0

    # Metrik g: Rematri kelas 10 teridentifikasi Anemia Berat
    anemia_berat_kelas_10 = filtered_df["Jumlah_Rematri_kelas_10_Anemia_Berat"].sum()
    metric_g = (anemia_berat_kelas_10 / total_skrining_kelas_10 * 100) if total_skrining_kelas_10 else 0

    # Metrik h: Rematri kelas 10 teridentifikasi Anemia
    anemia_total_kelas_10 = filtered_df["Jumlah_Anemia_Rematri_Kelas_10"].sum()
    metric_h = (anemia_total_kelas_10 / total_skrining_kelas_10 * 100) if total_skrining_kelas_10 else 0
    gap_h = metric_h - target
    status_h = "Dibawah Target" if metric_h < target else "Diatas Target"
    color_h = "green" if metric_h < target else "red"
    arrow_h = "⬇️" if metric_h < target else "⬆️"

    # Kelas 7 & 10
    total_skrining_kelas_7_10 = filtered_df["Jumlah_remaja_putri_kelas_7_dan_10_di_satuan_pendidikan_skrining_anemia"].sum()
    if total_skrining_kelas_7_10 == 0:
        st.warning("⚠️ Tidak ada data remaja putri kelas 7 dan 10 yang diskrining anemia untuk filter yang dipilih.")
        return

    # Metrik i: Rematri kelas 7 & 10 teridentifikasi Anemia
    anemia_total_kelas_7_10 = filtered_df["Jumlah_remaja_putri_kelas_7_10_teridentifikasi_anemia"].sum()
    metric_i = (anemia_total_kelas_7_10 / total_skrining_kelas_7_10 * 100) if total_skrining_kelas_7_10 else 0
    gap_i = metric_i - target
    status_i = "Dibawah Target" if metric_i < target else "Diatas Target"
    color_i = "green" if metric_i < target else "red"
    arrow_i = "⬇️" if metric_i < target else "⬆️"

    # Score Card dalam 3 kolom
    st.subheader("📊 Score Card Prevalensi Anemia Rematri")
    col1, col2, col3 = st.columns(3)

    with col1:
        # Metrik a
        st.metric(
            label="Rematri Kelas 7 Anemia Ringan (%)",
            value=f"{metric_a:.2f}%"
        )
        # Metrik b
        st.metric(
            label="Rematri Kelas 7 Anemia Sedang (%)",
            value=f"{metric_b:.2f}%"
        )
        # Metrik c
        st.metric(
            label="Rematri Kelas 7 Anemia Berat (%)",
            value=f"{metric_c:.2f}%"
        )
        # Metrik d
        st.metric(
            label="Rematri Kelas 7 Teridentifikasi Anemia (%)",
            value=f"{metric_d:.2f}%",
            delta=f"{arrow_d} {status_d} (Gap: {abs(gap_d):.2f}%)",
            delta_color="normal" if color_d == "green" else "inverse"
        )

    with col2:
        # Metrik e
        st.metric(
            label="Rematri Kelas 10 Anemia Ringan (%)",
            value=f"{metric_e:.2f}%"
        )
        # Metrik f
        st.metric(
            label="Rematri Kelas 10 Anemia Sedang (%)",
            value=f"{metric_f:.2f}%"
        )
        # Metrik g
        st.metric(
            label="Rematri Kelas 10 Anemia Berat (%)",
            value=f"{metric_g:.2f}%"
        )
        # Metrik h
        st.metric(
            label="Rematri Kelas 10 Teridentifikasi Anemia (%)",
            value=f"{metric_h:.2f}%",
            delta=f"{arrow_h} {status_h} (Gap: {abs(gap_h):.2f}%)",
            delta_color="normal" if color_h == "green" else "inverse"
        )

    with col3:
        # Metrik i
        st.metric(
            label="Rematri Kelas 7 & 10 Teridentifikasi Anemia (%)",
            value=f"{metric_i:.2f}%",
            delta=f"{arrow_i} {status_i} (Gap: {abs(gap_i):.2f}%)",
            delta_color="normal" if color_i == "green" else "inverse"
        )

    # Grafik 1: Prevalensi Anemia Remaja Putri Kelas 7
    st.subheader("📈 Grafik Prevalensi Anemia Remaja Putri Kelas 7")
    level = "Kelurahan" if puskesmas_filter != "All" else "Puskesmas"
    grouped_df = filtered_df.groupby(level).sum(numeric_only=True).reset_index()

    # Hitung metrik per level (Puskesmas/Kelurahan)
    grouped_df["Kelas 7 Anemia Ringan (%)"] = (grouped_df["Jumlah_Rematri_kelas_7_Anemia_Ringan"] / grouped_df["Jumlah_remaja_putri_kelas_7_di_satuan_pendidikan_skrining_anemia"] * 100).fillna(0)
    grouped_df["Kelas 7 Anemia Sedang (%)"] = (grouped_df["Jumlah_Rematri_kelas_7_Anemia_Sedang"] / grouped_df["Jumlah_remaja_putri_kelas_7_di_satuan_pendidikan_skrining_anemia"] * 100).fillna(0)
    grouped_df["Kelas 7 Anemia Berat (%)"] = (grouped_df["Jumlah_Rematri_kelas_7_Anemia_Berat"] / grouped_df["Jumlah_remaja_putri_kelas_7_di_satuan_pendidikan_skrining_anemia"] * 100).fillna(0)
    grouped_df["Kelas 7 Teridentifikasi Anemia (%)"] = (grouped_df["Jumlah_Anemia_Rematri_Kelas_7"] / grouped_df["Jumlah_remaja_putri_kelas_7_di_satuan_pendidikan_skrining_anemia"] * 100).fillna(0)

    # Reshape data untuk bar chart
    plot_df_kelas_7 = grouped_df.melt(id_vars=[level], value_vars=["Kelas 7 Anemia Ringan (%)", "Kelas 7 Anemia Sedang (%)", "Kelas 7 Anemia Berat (%)", "Kelas 7 Teridentifikasi Anemia (%)"],
                                      var_name="Metrik", value_name="Persentase")

    # Buat bar chart dengan 4 warna berbeda
    fig_kelas_7 = px.bar(plot_df_kelas_7, x=level, y="Persentase", color="Metrik",
                         title=f"📊 Prevalensi Anemia Rematri Kelas 7 per {level}",
                         color_discrete_map={
                             "Kelas 7 Anemia Ringan (%)": "#00C49F",
                             "Kelas 7 Anemia Sedang (%)": "#FF6F61",
                             "Kelas 7 Anemia Berat (%)": "#FFB347",
                             "Kelas 7 Teridentifikasi Anemia (%)": "#1F77B4"
                         },
                         text=plot_df_kelas_7["Persentase"].apply(lambda x: f"{x:.2f}%"))

    # Tambahkan garis target 25% untuk Metrik d
    fig_kelas_7.add_hline(y=25, line_dash="dash", line_color="red",
                          annotation_text="Target: 25%", annotation_position="top right")

    fig_kelas_7.update_traces(textposition='outside')
    fig_kelas_7.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", xaxis_title=level,
                              yaxis_range=[0, 110], title_x=0.5, height=500, barmode='group')
    st.plotly_chart(fig_kelas_7, key=f"anemia_kelas_7_chart_{bulan_filter}_{puskesmas_filter}_{kelurahan_filter}_{time.time()}", use_container_width=True)

    # Grafik 2: Prevalensi Anemia Remaja Putri Kelas 10
    st.subheader("📈 Grafik Prevalensi Anemia Remaja Putri Kelas 10")
    grouped_df["Kelas 10 Anemia Ringan (%)"] = (grouped_df["Jumlah_Rematri_kelas_10_Anemia_Ringan"] / grouped_df["Jumlah_remaja_putri_kelas_10_di_satuan_pendidikan_skrining_anemia"] * 100).fillna(0)
    grouped_df["Kelas 10 Anemia Sedang (%)"] = (grouped_df["Jumlah_Rematri_kelas_10_Anemia_Sedang"] / grouped_df["Jumlah_remaja_putri_kelas_10_di_satuan_pendidikan_skrining_anemia"] * 100).fillna(0)
    grouped_df["Kelas 10 Anemia Berat (%)"] = (grouped_df["Jumlah_Rematri_kelas_10_Anemia_Berat"] / grouped_df["Jumlah_remaja_putri_kelas_10_di_satuan_pendidikan_skrining_anemia"] * 100).fillna(0)
    grouped_df["Kelas 10 Teridentifikasi Anemia (%)"] = (grouped_df["Jumlah_Anemia_Rematri_Kelas_10"] / grouped_df["Jumlah_remaja_putri_kelas_10_di_satuan_pendidikan_skrining_anemia"] * 100).fillna(0)

    # Reshape data untuk bar chart
    plot_df_kelas_10 = grouped_df.melt(id_vars=[level], value_vars=["Kelas 10 Anemia Ringan (%)", "Kelas 10 Anemia Sedang (%)", "Kelas 10 Anemia Berat (%)", "Kelas 10 Teridentifikasi Anemia (%)"],
                                       var_name="Metrik", value_name="Persentase")

    # Buat bar chart dengan 4 warna berbeda
    fig_kelas_10 = px.bar(plot_df_kelas_10, x=level, y="Persentase", color="Metrik",
                          title=f"📊 Prevalensi Anemia Rematri Kelas 10 per {level}",
                          color_discrete_map={
                              "Kelas 10 Anemia Ringan (%)": "#00C49F",
                              "Kelas 10 Anemia Sedang (%)": "#FF6F61",
                              "Kelas 10 Anemia Berat (%)": "#FFB347",
                              "Kelas 10 Teridentifikasi Anemia (%)": "#1F77B4"
                          },
                          text=plot_df_kelas_10["Persentase"].apply(lambda x: f"{x:.2f}%"))

    # Tambahkan garis target 25% untuk Metrik h
    fig_kelas_10.add_hline(y=25, line_dash="dash", line_color="red",
                           annotation_text="Target: 25%", annotation_position="top right")

    fig_kelas_10.update_traces(textposition='outside')
    fig_kelas_10.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", xaxis_title=level,
                               yaxis_range=[0, 110], title_x=0.5, height=500, barmode='group')
    st.plotly_chart(fig_kelas_10, key=f"anemia_kelas_10_chart_{bulan_filter}_{puskesmas_filter}_{kelurahan_filter}_{time.time()}", use_container_width=True)

    # Grafik 3: Prevalensi Anemia Remaja Putri Kelas 7 & 10
    st.subheader("📈 Grafik Prevalensi Anemia Remaja Putri Kelas 7 & 10")
    grouped_df["Kelas 7 & 10 Teridentifikasi Anemia (%)"] = (grouped_df["Jumlah_remaja_putri_kelas_7_10_teridentifikasi_anemia"] / grouped_df["Jumlah_remaja_putri_kelas_7_dan_10_di_satuan_pendidikan_skrining_anemia"] * 100).fillna(0)

    # Reshape data untuk bar chart
    plot_df_kelas_7_10 = grouped_df.melt(id_vars=[level], value_vars=["Kelas 7 & 10 Teridentifikasi Anemia (%)"],
                                         var_name="Metrik", value_name="Persentase")

    # Buat bar chart dengan 1 warna
    fig_kelas_7_10 = px.bar(plot_df_kelas_7_10, x=level, y="Persentase", color="Metrik",
                            title=f"📊 Prevalensi Anemia Rematri Kelas 7 & 10 per {level}",
                            color_discrete_map={
                                "Kelas 7 & 10 Teridentifikasi Anemia (%)": "#1F77B4"
                            },
                            text=plot_df_kelas_7_10["Persentase"].apply(lambda x: f"{x:.2f}%"))

    # Tambahkan garis target 25% untuk Metrik i
    fig_kelas_7_10.add_hline(y=25, line_dash="dash", line_color="red",
                             annotation_text="Target: 25%", annotation_position="top right")

    fig_kelas_7_10.update_traces(textposition='outside')
    fig_kelas_7_10.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", xaxis_title=level,
                                 yaxis_range=[0, 110], title_x=0.5, height=500, barmode='group')
    st.plotly_chart(fig_kelas_7_10, key=f"anemia_kelas_7_10_chart_{bulan_filter}_{puskesmas_filter}_{kelurahan_filter}_{time.time()}", use_container_width=True)

    # Tabel Rekapitulasi
    st.subheader("📋 Tabel Rekapitulasi Prevalensi Anemia Rematri")
    rekap_data = []
    for index, row in grouped_df.iterrows():
        rekap_data.append({
            level: row[level],
            "Kelas 7 Anemia Ringan (%)": f"{row['Kelas 7 Anemia Ringan (%)']:.2f}%",
            "Kelas 7 Anemia Sedang (%)": f"{row['Kelas 7 Anemia Sedang (%)']:.2f}%",
            "Kelas 7 Anemia Berat (%)": f"{row['Kelas 7 Anemia Berat (%)']:.2f}%",
            "Kelas 7 Teridentifikasi Anemia (%)": f"{row['Kelas 7 Teridentifikasi Anemia (%)']:.2f}%",
            "Kelas 10 Anemia Ringan (%)": f"{row['Kelas 10 Anemia Ringan (%)']:.2f}%",
            "Kelas 10 Anemia Sedang (%)": f"{row['Kelas 10 Anemia Sedang (%)']:.2f}%",
            "Kelas 10 Anemia Berat (%)": f"{row['Kelas 10 Anemia Berat (%)']:.2f}%",
            "Kelas 10 Teridentifikasi Anemia (%)": f"{row['Kelas 10 Teridentifikasi Anemia (%)']:.2f}%",
            "Kelas 7 & 10 Teridentifikasi Anemia (%)": f"{row['Kelas 7 & 10 Teridentifikasi Anemia (%)']:.2f}%"
        })

    rekap_df = pd.DataFrame(rekap_data)
    st.dataframe(rekap_df, use_container_width=True)

    # 4. Fitur Download Laporan PDF
    st.subheader("📥 Unduh Laporan")
    def generate_pdf_report():
        # Buat buffer untuk menyimpan grafik
        img_buffer1 = BytesIO()
        img_buffer2 = BytesIO()
        img_buffer3 = BytesIO()
        fig_kelas_7.write_image(img_buffer1, format='png', width=600, height=400, scale=2)
        fig_kelas_10.write_image(img_buffer2, format='png', width=600, height=400, scale=2)
        fig_kelas_7_10.write_image(img_buffer3, format='png', width=600, height=400, scale=2)
        img_buffer1.seek(0)
        img_buffer2.seek(0)
        img_buffer3.seek(0)

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
        elements.append(Paragraph("Laporan Prevalensi Anemia Rematri", title_style))
        elements.append(Paragraph(f"Diperbarui: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
        elements.append(Spacer(1, 12))

        # Tambahkan Metrik
        elements.append(Paragraph("1. Metrik Prevalensi Anemia", normal_style))
        metrik_list = [
            ("Rematri Kelas 7 Anemia Ringan (%)", metric_a),
            ("Rematri Kelas 7 Anemia Sedang (%)", metric_b),
            ("Rematri Kelas 7 Anemia Berat (%)", metric_c),
            ("Rematri Kelas 7 Teridentifikasi Anemia (%)", metric_d),
            ("Rematri Kelas 10 Anemia Ringan (%)", metric_e),
            ("Rematri Kelas 10 Anemia Sedang (%)", metric_f),
            ("Rematri Kelas 10 Anemia Berat (%)", metric_g),
            ("Rematri Kelas 10 Teridentifikasi Anemia (%)", metric_h),
            ("Rematri Kelas 7 & 10 Teridentifikasi Anemia (%)", metric_i)
        ]
        targets = {
            "Rematri Kelas 7 Teridentifikasi Anemia (%)": 25,
            "Rematri Kelas 10 Teridentifikasi Anemia (%)": 25,
            "Rematri Kelas 7 & 10 Teridentifikasi Anemia (%)": 25
        }
        metric_data = []
        for label, value in metrik_list:
            target = targets.get(label)
            if target is not None:
                gap = abs(value - target)
                if value < target:
                    delta_str = f"Dibawah Target (gap: {gap:.2f}%)"
                    delta_color = colors.green
                    delta_arrow = "↓"
                else:
                    delta_str = f"Diatas Target (gap: {gap:.2f}%)"
                    delta_color = colors.red
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
        elements.append(Paragraph("2. Grafik Prevalensi Anemia Rematri Kelas 7", normal_style))
        elements.append(Image(img_buffer1, width=500, height=300))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("3. Grafik Prevalensi Anemia Rematri Kelas 10", normal_style))
        elements.append(Image(img_buffer2, width=500, height=300))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("4. Grafik Prevalensi Anemia Rematri Kelas 7 & 10", normal_style))
        elements.append(Image(img_buffer3, width=500, height=300))
        elements.append(Spacer(1, 12))

        # Tambahkan Tabel Rekapitulasi
        elements.append(Paragraph("5. Tabel Rekapitulasi", normal_style))
        table_data = [rekap_df.columns.tolist()] + rekap_df.values.tolist()
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
            file_name=f"Laporan_Prevalensi_Anemia_Rematri_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )

# ----------------------------- #
# 🩺 Tatalaksana Rematri Anemia
# ----------------------------- #
def tatalaksana_rematri_anemia(filtered_df, desa_df, bulan_filter, puskesmas_filter, kelurahan_filter):
    """Menampilkan analisis Tatalaksana Rematri Anemia."""
    st.header("🩺 Tatalaksana Rematri Anemia")

    # Tambahkan informasi definisi operasional dan insight analisis
    with st.expander("📜 Definisi dan Insight Analisis Tatalaksana Rematri Anemia", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Analisis Indikator

            Berikut adalah definisi operasional, rumus perhitungan, serta analisis insight dari indikator yang digunakan untuk memantau tatalaksana anemia pada remaja putri (Rematri) di satuan pendidikan.

            #### 1. Tatalaksana Rematri Anemia
            - **Definisi Operasional:** Persentase remaja putri kelas 7 dan 10 yang mendapatkan tatalaksana anemia dari total remaja putri kelas 7 dan 10 yang telah diskrining anemia.  
            - **Rumus Perhitungan:**  
            $$ \\text{Tatalaksana Anemia (\\%)} = \\frac{\\text{Jumlah Rematri Kelas 7 dan 10 Mendapatkan Tatalaksana Anemia}}{\\text{Jumlah Rematri Kelas 7 dan 10 yang Diskrining Anemia}} \\times 100 $$  
            - **Target:** 30%  
            - **Insight Analisis:** Cakupan tatalaksana di bawah target menunjukkan rendahnya akses atau efektivitas pelayanan tatalaksana. Peningkatan koordinasi antara sekolah dan puskesmas dapat meningkatkan angka ini.

            </div>
        """, unsafe_allow_html=True)

    # Import tambahan untuk PDF
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    # Kolom kunci untuk perhitungan
    required_columns = [
        "Jumlah_remaja_putri_kelas_7_dan_10_di_satuan_pendidikan_skrining_anemia",
        "Jumlah_Rematri_kelas_7_dan_10_mendapatkan_tatalaksana_anemia"
    ]

    # Cek kolom yang hilang di dataset
    missing_cols = [col for col in required_columns if col not in filtered_df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di dataset: {missing_cols}")
        return

    # Hitung metrik
    # Metrik a: Rematri Mendapatkan Tatalaksana Anemia
    total_skrining_kelas_7_10 = filtered_df["Jumlah_remaja_putri_kelas_7_dan_10_di_satuan_pendidikan_skrining_anemia"].sum()
    if total_skrining_kelas_7_10 == 0:
        st.warning("⚠️ Tidak ada data remaja putri kelas 7 dan 10 yang diskrining anemia untuk filter yang dipilih.")
        return

    tatalaksana_kelas_7_10 = filtered_df["Jumlah_Rematri_kelas_7_dan_10_mendapatkan_tatalaksana_anemia"].sum()
    metric_a = (tatalaksana_kelas_7_10 / total_skrining_kelas_7_10 * 100) if total_skrining_kelas_7_10 else 0
    target = 30
    gap_a = metric_a - target
    status_a = "Diatas Target" if metric_a > target else "Dibawah Target"
    color_a = "green" if metric_a > target else "red"
    arrow_a = "⬆️" if metric_a > target else "⬇️"

    # Score Card
    st.subheader("📊 Score Card Tatalaksana Rematri Anemia")
    st.metric(
        label="Rematri Mendapatkan Tatalaksana Anemia (%)",
        value=f"{metric_a:.2f}%",
        delta=f"{arrow_a} {status_a} (Gap: {abs(gap_a):.2f}%)",
        delta_color="normal" if color_a == "green" else "inverse"
    )

    # Grafik: Tatalaksana Rematri Anemia
    st.subheader("📈 Grafik Tatalaksana Rematri Anemia")
    level = "Kelurahan" if puskesmas_filter != "All" else "Puskesmas"
    grouped_df = filtered_df.groupby(level).sum(numeric_only=True).reset_index()

    # Hitung metrik per level (Puskesmas/Kelurahan)
    grouped_df["Tatalaksana Anemia (%)"] = (grouped_df["Jumlah_Rematri_kelas_7_dan_10_mendapatkan_tatalaksana_anemia"] / grouped_df["Jumlah_remaja_putri_kelas_7_dan_10_di_satuan_pendidikan_skrining_anemia"] * 100).fillna(0)

    # Reshape data untuk bar chart
    plot_df = grouped_df.melt(id_vars=[level], value_vars=["Tatalaksana Anemia (%)"],
                              var_name="Metrik", value_name="Persentase")

    # Buat bar chart dengan warna biru muda
    fig = px.bar(plot_df, x=level, y="Persentase", color="Metrik",
                 title=f"📊 Tatalaksana Rematri Anemia per {level}",
                 color_discrete_map={
                     "Tatalaksana Anemia (%)": "#87CEEB"
                 },
                 text=plot_df["Persentase"].apply(lambda x: f"{x:.2f}%"))

    # Tambahkan garis target 30%
    fig.add_hline(y=30, line_dash="dash", line_color="red",
                  annotation_text="Target: 30%", annotation_position="top right")

    fig.update_traces(textposition='outside')
    fig.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", xaxis_title=level,
                      yaxis_range=[0, 110], title_x=0.5, height=500, barmode='group')
    st.plotly_chart(fig, key=f"tatalaksana_anemia_chart_{bulan_filter}_{puskesmas_filter}_{kelurahan_filter}_{time.time()}", use_container_width=True)

    # Tabel Rekapitulasi
    st.subheader("📋 Tabel Rekapitulasi Tatalaksana Rematri Anemia")
    rekap_data = []
    for index, row in grouped_df.iterrows():
        rekap_data.append({
            level: row[level],
            "Tatalaksana Anemia (%)": f"{row['Tatalaksana Anemia (%)']:.2f}%"
        })

    rekap_df = pd.DataFrame(rekap_data)
    st.dataframe(rekap_df, use_container_width=True)

    # 3. Fitur Download Laporan PDF
    st.subheader("📥 Unduh Laporan")
    def generate_pdf_report():
        # Buat buffer untuk menyimpan grafik
        img_buffer = BytesIO()
        fig.write_image(img_buffer, format='png', width=600, height=400, scale=2)
        img_buffer.seek(0)

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
        elements.append(Paragraph("Laporan Tatalaksana Rematri Anemia", title_style))
        elements.append(Paragraph(f"Diperbarui: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
        elements.append(Spacer(1, 12))

        # Tambahkan Metrik
        elements.append(Paragraph("1. Metrik Tatalaksana Anemia", normal_style))
        metrik_list = [("Rematri Mendapatkan Tatalaksana Anemia (%)", metric_a)]
        targets = {"Rematri Mendapatkan Tatalaksana Anemia (%)": 30}
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
        elements.append(Paragraph("2. Grafik Tatalaksana Rematri Anemia", normal_style))
        elements.append(Image(img_buffer, width=500, height=300))
        elements.append(Spacer(1, 12))

        # Tambahkan Tabel Rekapitulasi
        elements.append(Paragraph("3. Tabel Rekapitulasi", normal_style))
        table_data = [rekap_df.columns.tolist()] + rekap_df.values.tolist()
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
            file_name=f"Laporan_Tatalaksana_Anemia_Rematri_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )

# ----------------------------- #
# 🚀 Main Function
# ----------------------------- #
def show_dashboard():
    """Menampilkan dashboard utama untuk indikator remaja putri."""
    st.title("👧 Dashboard Indikator Remaja Putri")
    last_upload_time = get_last_upload_time()
    st.markdown(f"**📅 Data terakhir diperbarui:** {last_upload_time}")

    df, desa_df = load_data()
    if df is None:
        st.error("❌ Gagal memuat data. Periksa database!")
        return

    # Sidebar untuk filter
    with st.sidebar.expander("🔎 Filter Data"):
        bulan_options = ["All"] + sorted(df['Bulan'].astype(str).unique().tolist() if 'Bulan' in df.columns else [])
        bulan_filter = st.selectbox("📅 Pilih Bulan", options=bulan_options)

        puskesmas_filter = st.selectbox("🏥 Pilih Puskesmas", ["All"] + sorted(desa_df['Puskesmas'].unique()))
        kelurahan_options = ["All"]
        if puskesmas_filter != "All":
            kelurahan_options += sorted(desa_df[desa_df['Puskesmas'] == puskesmas_filter]['Kelurahan'].unique())
        kelurahan_filter = st.selectbox("🏡 Pilih Kelurahan", options=kelurahan_options)

    # Inisialisasi filtered_df
    filtered_df = df.copy()
    if bulan_filter != "All":
        try:
            bulan_filter_int = int(bulan_filter)
            filtered_df = df[df["Bulan"] == bulan_filter_int] if 'Bulan' in df.columns else df
        except ValueError:
            st.error("⚠️ Pilihan bulan tidak valid. Menggunakan semua data.")
            filtered_df = df.copy()

    if puskesmas_filter != "All":
        filtered_df = filtered_df[filtered_df["Puskesmas"] == puskesmas_filter]
    if kelurahan_filter != "All":
        filtered_df = filtered_df[filtered_df["Kelurahan"] == kelurahan_filter]

    # Tampilkan data terfilter
    st.subheader("📝 Data Terfilter")
    if filtered_df.empty:
        st.warning("⚠️ Tidak ada data yang sesuai dengan filter.")
    else:
        st.dataframe(filtered_df, use_container_width=True)

    # Menu sidebar untuk analisis
    menu = st.sidebar.radio("📂 Pilih Dashboard", ["📊 Kelengkapan Data", "📈 Analisis Indikator Remaja Putri"])

    if menu == "📊 Kelengkapan Data":
        sub_menu = st.sidebar.radio("🔍 Pilih Analisis", ["✅ Compliance Rate", "📋 Completeness Rate"])
        if sub_menu == "✅ Compliance Rate":
            compliance_rate(filtered_df, desa_df, bulan_filter, puskesmas_filter, kelurahan_filter)
        elif sub_menu == "📋 Completeness Rate":
            completeness_rate(filtered_df, desa_df, bulan_filter, puskesmas_filter, kelurahan_filter)

    elif menu == "📈 Analisis Indikator Remaja Putri":
        sub_analisis = st.sidebar.radio("📊 Pilih Sub Analisis", [
            "💊 Cakupan Suplementasi TTD Rematri",
            "🔍 Cakupan Rematri Skrining Anemia",
            "📊 Prevalensi Anemia Rematri",
            "🩺 Tatalaksana Rematri Anemia"
        ])
        if sub_analisis == "💊 Cakupan Suplementasi TTD Rematri":
            cakupan_suplementasi_ttd_rematri(filtered_df, desa_df, bulan_filter, puskesmas_filter, kelurahan_filter)
        elif sub_analisis == "🔍 Cakupan Rematri Skrining Anemia":
            cakupan_rematri_skrining_anemia(filtered_df, desa_df, bulan_filter, puskesmas_filter, kelurahan_filter)
        elif sub_analisis == "📊 Prevalensi Anemia Rematri":
            prevalensi_anemia_rematri(filtered_df, desa_df, bulan_filter, puskesmas_filter, kelurahan_filter)
        elif sub_analisis == "🩺 Tatalaksana Rematri Anemia":
            tatalaksana_rematri_anemia(filtered_df, desa_df, bulan_filter, puskesmas_filter, kelurahan_filter)

    st.markdown(
        '<p style="text-align: center; font-size: 12px; color: grey;">'
        'made with ❤️ by <a href="mailto:dedik2urniawan@gmail.com">dedik2urniawan@gmail.com</a>'
        '</p>', unsafe_allow_html=True)

if __name__ == "__main__":
    show_dashboard()