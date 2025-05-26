import streamlit as st
import numpy as np
import pandas as pd
import sqlite3
import plotly.express as px
import os
from datetime import datetime
import time
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from scipy import stats

# ----------------------------- #
# 📥 Fungsi untuk load data
# ----------------------------- #
@st.cache_data
def load_data():
    """Memuat data dari database SQLite rcs_data.db."""
    try:
        conn = sqlite3.connect("rcs_data.db")
        df = pd.read_sql_query("SELECT * FROM data_balita_kia", conn)
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
        print(f"Checking file path: {os.path.abspath(file_path)}")  # Debug path
        if not os.path.exists(file_path):
            return "Belum ada data yang diunggah (File database tidak ditemukan)"
        last_modified_time = os.path.getmtime(file_path)
        return datetime.fromtimestamp(last_modified_time).strftime("%d %B %Y, %H:%M:%S")
    except PermissionError:
        return "Gagal mendapatkan waktu upload (Izin akses ditolak)"
    except Exception as e:
        return f"Gagal mendapatkan waktu upload (Error: {str(e)})"
    
# ----------------------------- #
# 🧮 Compliance Rate
# ----------------------------- #
def compliance_rate(filtered_df, desa_df, puskesmas_filter, kelurahan_filter):
    """Menghitung dan menampilkan tingkat kepatuhan pelaporan."""
    st.header("✅ Compliance Rate")
    desa_terlapor = filtered_df['Kelurahan'].unique()
    total_desa = desa_df.copy()

    if puskesmas_filter != "All":
        total_desa = total_desa[total_desa['Puskesmas'] == puskesmas_filter]
    if kelurahan_filter != "All":
        total_desa = total_desa[total_desa['Kelurahan'] == kelurahan_filter]

    total_desa_count = total_desa['Kelurahan'].nunique()
    desa_lapor_count = len(desa_terlapor)
    compliance_value = (desa_lapor_count / total_desa_count * 100) if total_desa_count else 0

    st.metric(label="Compliance Rate (%)", value=f"{compliance_value:.2f}%")

    compliance_data = [
        {
            "Puskesmas": puskesmas,
            "Jumlah Desa": desa_df[desa_df['Puskesmas'] == puskesmas]['Kelurahan'].nunique(),
            "Jumlah Desa Lapor": filtered_df[filtered_df['Puskesmas'] == puskesmas]['Kelurahan'].nunique(),
            "Compliance Rate (%)": f"{(filtered_df[filtered_df['Puskesmas'] == puskesmas]['Kelurahan'].nunique() / desa_df[desa_df['Puskesmas'] == puskesmas]['Kelurahan'].nunique() * 100) if desa_df[desa_df['Puskesmas'] == puskesmas]['Kelurahan'].nunique() else 0:.2f}%"
        }
        for puskesmas in sorted(desa_df['Puskesmas'].unique())
    ]

    compliance_df = pd.DataFrame(compliance_data)
    st.subheader("📋 Tabel Compliance Rate per Puskesmas")
    st.dataframe(compliance_df, use_container_width=True)

    st.subheader("📊 Visualisasi Compliance Rate per Puskesmas")
    fig = px.bar(compliance_df, x="Puskesmas", y=compliance_df["Compliance Rate (%)"].str.rstrip('%').astype(float),
                 text="Compliance Rate (%)", title="📊 Compliance Rate per Puskesmas Indikator Balita KIA", color_discrete_sequence=["#00C49F"])
    fig.update_traces(textposition='outside')
    fig.update_layout(xaxis_tickangle=-45, yaxis_title="Compliance Rate (%)", xaxis_title="Puskesmas", yaxis_range=[0, 110], title_x=0.5, height=500)
    st.plotly_chart(fig, key=f"compliance_chart_{puskesmas_filter}_{kelurahan_filter}_{time.time()}", use_container_width=True)

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
def completeness_rate(filtered_df, desa_df, puskesmas_filter, kelurahan_filter):
    """Menghitung dan menampilkan tingkat kelengkapan data berdasarkan variabel kunci."""
    st.header("📋 Completeness Rate")

    # Daftar kolom kunci untuk cek kelengkapan (subset dari data_balita_kia)
    completeness_columns = [
        "Jumlah_bayi_baru_lahir_hidup",
        "Jumlah_bayi_BBLR",
        "Jumlah_bayi_prematur_dan_BBLR_yang_mendapat_buku_KIA_bayi_kecil",
        "Jumlah_anak_prasekolah_bulan_ini",
        "Jumlah_anak_prasekolah_punya_Buku_KIA",
        "Jumlah_balita_diskrining_perkembangan",
        "Jumlah_balita_usia_12-59_bulan_sampai_bulan_ini",
        "Jumlah_balita_pantau_tumbang",
        "Jumlah_balita_mendapat_pelayanan_SDIDTK_di_FKTP",
        "Cakupan_bayi_dilayani_PKAT"
    ]

    # Cek kolom yang hilang di dataset
    missing_cols = [col for col in completeness_columns if col not in filtered_df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di dataset: {missing_cols}")
        return

    # Tambahkan kolom 'Lengkap' untuk mengecek apakah semua kolom kunci terisi
    filtered_df['Lengkap'] = filtered_df[completeness_columns].notna().all(axis=1)

    # Tentukan scope berdasarkan filter
    if kelurahan_filter != "All":
        scope = filtered_df[filtered_df['Kelurahan'] == kelurahan_filter]
    elif puskesmas_filter != "All":
        scope = filtered_df[filtered_df['Puskesmas'] == puskesmas_filter]
    else:
        scope = filtered_df

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
    st.plotly_chart(fig_completeness, key=f"completeness_chart_{puskesmas_filter}_{kelurahan_filter}_{time.time()}", 
                    use_container_width=True)

    # Detail kelengkapan per kolom (opsional)
    if st.checkbox("🔍 Tampilkan Detail Kelengkapan per Kolom"):
        completeness_per_col = filtered_df[completeness_columns].notna().mean() * 100
        st.subheader("📋 Persentase Kelengkapan per Kolom")
        col_data = [{"Kolom": col, "Kelengkapan (%)": f"{val:.2f}%"} 
                    for col, val in completeness_per_col.items()]
        st.dataframe(pd.DataFrame(col_data), use_container_width=True)
        
def indikator_bayi_kecil(filtered_df, desa_df, puskesmas_filter, kelurahan_filter, jenis_laporan, tahun_filter, bulan_filter_int=None, tribulan_filter=None):
    """Menampilkan analisis Indikator Bayi Kecil dengan fitur download laporan menggunakan reportlab."""
    st.header("👶 Indikator Bayi Kecil")

    # Tambahkan info dengan tone akademik, rendering rumus, penjelasan untuk orang awam, dan background biru muda
    with st.expander("📜 Definisi dan Insight Analisis Indikator Bayi Kecil", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Analisis Indikator

            Berikut adalah definisi operasional, rumus perhitungan, serta analisis insight dari indikator-indikator yang digunakan untuk memantau kesehatan bayi kecil dalam sistem kesehatan masyarakat. Rumus disajikan dalam format matematis untuk kejelasan, dengan penjelasan sederhana untuk memudahkan pemahaman.

            #### 1. Persentase Bayi Lahir Prematur
            - **Definisi Operasional:** Persentase bayi yang lahir sebelum usia gestasi mencapai 37 minggu (<37 minggu), dihitung berdasarkan perkiraan usia kehamilan dari hari pertama haid terakhir (HPHT) ibu, dalam suatu periode dan wilayah kerja tertentu.  
            - **Rumus Perhitungan:**  
            $$ \\text{Persentase Bayi Prematur (\\%)} = \\frac{\\text{Jumlah bayi lahir dengan usia kehamilan < 37 minggu}}{\\text{Jumlah total bayi lahir hidup}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini membagi jumlah bayi yang lahir prematur (usia kehamilan kurang dari 37 minggu) dengan total bayi lahir hidup, lalu dikalikan 100 untuk mendapatkan persentase.  
            - **Metode Pengumpulan Data:** Data dikumpulkan secara bulanan melalui pencatatan individu. Bayi dengan usia gestasi <37 minggu diklasifikasikan sebagai kasus prematur.  
            - **Insight Analisis:** Tingkat kelahiran prematur yang tinggi dapat mengindikasikan adanya faktor risiko seperti malnutrisi ibu, infeksi selama kehamilan, atau akses terbatas terhadap layanan antenatal care (ANC). Persentase yang melebihi 11% (standar global WHO) menunjukkan perlunya intervensi intensif, seperti peningkatan edukasi ibu hamil dan akses ke fasilitas kesehatan primer.

            #### 2. Persentase Bayi dengan Berat Badan Lahir Rendah (BBLR)
            - **Definisi Operasional:** Persentase bayi yang lahir hidup dengan berat badan lahir kurang dari 2500 gram (<2500 gram) dalam suatu periode tertentu di wilayah kerja tertentu.  
            - **Rumus Perhitungan:**  
            $$ \\text{Persentase Bayi BBLR (\\%)} = \\frac{\\text{Jumlah bayi lahir hidup dengan berat badan < 2500 gram}}{\\text{Jumlah total bayi lahir hidup}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase bayi yang lahir dengan berat kurang dari 2500 gram dibandingkan dengan semua bayi lahir hidup, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Pengukuran berat badan dilakukan segera setelah kelahiran, dengan pelaporan bulanan berdasarkan data individu.  
            - **Insight Analisis:** Prevalensi BBLR yang tinggi (di atas 5.8% menurut standar WHO) dapat menjadi indikator adanya masalah gizi kronis pada ibu, seperti anemia atau asupan kalori yang tidak memadai selama kehamilan. Hal ini juga berkorelasi dengan risiko morbiditas neonatal, seperti infeksi dan gangguan pernapasan. Intervensi yang direkomendasikan meliputi suplementasi gizi ibu dan pemeriksaan kehamilan rutin.

            #### 3. Persentase Panjang Bayi Lahir Rendah
            - **Definisi Operasional:** Persentase bayi lahir hidup dengan panjang badan lahir kurang dari 48 cm dalam suatu periode tertentu di wilayah kerja tertentu.  
            - **Rumus Perhitungan:**  
            $$ \\text{Persentase Panjang Bayi Lahir Rendah (\\%)} = \\frac{\\text{Jumlah bayi lahir hidup dengan panjang < 48 cm}}{\\text{Jumlah total bayi lahir hidup}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase bayi yang panjang badannya kurang dari 48 cm saat lahir dibandingkan dengan semua bayi lahir hidup, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Pengukuran dilakukan saat kelahiran menggunakan infantometer atau pita ukur khusus, dengan pelaporan bulanan.  
            - **Insight Analisis:** Panjang badan lahir rendah dapat mengindikasikan gangguan pertumbuhan intrauterin (IUGR), yang sering dikaitkan dengan faktor seperti hipertensi pada ibu atau paparan zat beracun (misalnya asap rokok). Jika persentase ini tinggi, diperlukan evaluasi lebih lanjut terhadap faktor lingkungan dan status kesehatan ibu, serta peningkatan skrining antenatal untuk mendeteksi IUGR sejak dini.

            #### 4. Persentase Lingkar Kepala Bayi Lahir Rendah
            - **Definisi Operasional:** Persentase bayi lahir hidup dengan lingkar kepala lahir kurang dari 34 cm dalam suatu periode tertentu di wilayah kerja tertentu.  
            - **Rumus Perhitungan:**  
            $$ \\text{Persentase Lingkar Kepala Bayi Rendah (\\%)} = \\frac{\\text{Jumlah bayi lahir hidup dengan lingkar kepala < 34 cm}}{\\text{Jumlah total bayi lahir hidup}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase bayi yang lingkar kepalanya kurang dari 34 cm saat lahir dibandingkan dengan semua bayi lahir hidup, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Pengukuran dilakukan segera setelah kelahiran menggunakan pita pengukur lingkar kepala standar, dengan pelaporan bulanan.  
            - **Insight Analisis:** Lingkar kepala yang lebih kecil dari standar dapat menjadi indikator adanya risiko gangguan perkembangan otak atau mikrosefali, yang mungkin terkait dengan infeksi TORCH (Toxoplasma, Rubella, Cytomegalovirus, Herpes) selama kehamilan. Persentase yang tinggi memerlukan tindak lanjut berupa skrining neurologis dini dan edukasi ibu mengenai pencegahan infeksi selama kehamilan.

            #### 5. Persentase Bayi Baru Lahir dengan BBLR yang Mendapat Tata Laksana
            - **Definisi Operasional:** Persentase bayi baru lahir dengan berat badan lahir rendah yang mendapatkan tata laksana sesuai standar dari total bayi BBLR dalam suatu periode tertentu.  
            - **Rumus Perhitungan:**  
            $$ \\text{Persentase Bayi BBLR Mendapat Tata Laksana (\\%)} = \\frac{\\text{Jumlah bayi BBLR yang mendapat tata laksana standar}}{\\text{Jumlah total bayi baru lahir dengan BBLR}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase bayi BBLR yang mendapat perawatan khusus (seperti ASI dini atau kangaroo care) dibandingkan dengan total bayi BBLR, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Tata laksana mencakup pemberian ASI dini, inisiasi kontak kulit-ke-kulit (kangaroo care), dan monitoring intensif. Data dikumpulkan secara kumulatif bulanan.  
            - **Insight Analisis:** Persentase di bawah 35% menunjukkan adanya tantangan dalam kualitas pelayanan kesehatan neonatal, seperti kurangnya tenaga kesehatan terlatih atau fasilitas yang memadai. Peningkatan pelatihan tenaga kesehatan dan penyediaan fasilitas kangaroo care dapat meningkatkan angka ini, sehingga mengurangi risiko mortalitas dan morbiditas pada bayi BBLR.

            #### 6. Persentase Bayi BBLR yang Mendapat Buku KIA (Kesehatan Ibu dan Anak) Bayi Kecil
            - **Definisi Operasional:** Persentase bayi dengan berat badan lahir rendah yang menerima Buku KIA bayi kecil sebagai bagian dari layanan kesehatan ibu dan anak dalam suatu periode tertentu.  
            - **Rumus Perhitungan:**  
            $$ \\text{Persentase Bayi BBLR Mendapat Buku KIA (\\%)} = \\frac{\\text{Jumlah bayi BBLR yang mendapat Buku KIA}}{\\text{Jumlah total bayi baru lahir dengan BBLR}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persentase bayi BBLR yang mendapatkan Buku KIA dibandingkan dengan total bayi BBLR, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Buku KIA berisi catatan pemantauan pertumbuhan dan intervensi spesifik untuk bayi kecil, dicatat secara bulanan berdasarkan data individu.  
            - **Insight Analisis:** Persentase yang rendah (di bawah 50%) dapat mengindikasikan rendahnya implementasi program kesehatan ibu dan anak, yang berpotensi memengaruhi pemantauan jangka panjang bayi BBLR. Peningkatan distribusi Buku KIA dan edukasi kepada orang tua mengenai pentingnya pemantauan dapat membantu meningkatkan angka ini, sehingga mendukung perkembangan optimal bayi.

            </div>
        """, unsafe_allow_html=True)

    # Daftar kolom yang dibutuhkan
    required_columns = [
        'Jumlah_bayi_baru_lahir_hidup',
        'Jumlah_bayi_lahir_37_minggu',
        'Jumlah_bayi_BBLR',
        'Jumlah_Bayi_PBLR',
        'Jumlah_Bayi_LIKA_Rendah',
        'Jumlah_bayi_prematur_dan_BBLR_yang_mendapat_buku_KIA_bayi_kecil',
        'Jumlah_bayi_baru_lahir_dengan_BBLR_mendapat_tata_laksana'
    ]

    # Cek apakah semua kolom ada
    missing_cols = [col for col in required_columns if col not in filtered_df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di dataset: {missing_cols}. Periksa data di 'data_balita_kia'!")
        return

    # Inisialisasi periode untuk label
    periode_label = ""
    if tahun_filter != "All":
        periode_label += f"Tahun {tahun_filter}"
    if jenis_laporan == "Bulanan" and bulan_filter_int is not None:
        periode_label += f" Bulan {bulan_filter_int}" if periode_label else f"Bulan {bulan_filter_int}"
    elif jenis_laporan == "Tahunan" and tribulan_filter:
        periode_label += f" {tribulan_filter}" if periode_label else tribulan_filter

    # Agregasi data berdasarkan jenis laporan
    if jenis_laporan == "Tahunan" and not filtered_df.empty:
        group_columns = ["Puskesmas", "Kelurahan"]
        numeric_columns = [col for col in filtered_df.columns if filtered_df[col].dtype in ['int64', 'float64']]
        if numeric_columns:
            agg_dict = {col: "sum" for col in numeric_columns}
            filtered_df = filtered_df.groupby(group_columns).agg(agg_dict).reset_index()

    # Hitung indikator
    total_bayi = filtered_df['Jumlah_bayi_baru_lahir_hidup'].sum()
    if total_bayi == 0:
        st.warning("⚠️ Tidak ada data bayi baru lahir hidup untuk filter ini.")
        return

    indikator_data = {
    "Cakupan Bayi Lahir Prematur (%)": (filtered_df['Jumlah_bayi_lahir_37_minggu'].sum() / total_bayi * 100),
    "Cakupan Bayi BBLR (%)": (filtered_df['Jumlah_bayi_BBLR'].sum() / total_bayi * 100),
    "Cakupan Bayi Prematur & BBLR Mendapat Buku KIA (%)": (filtered_df['Jumlah_bayi_prematur_dan_BBLR_yang_mendapat_buku_KIA_bayi_kecil'].sum() / filtered_df['Jumlah_bayi_BBLR'].sum() * 100),
    "Cakupan Bayi BBLR Mendapat Tatalaksana (%)": (filtered_df['Jumlah_bayi_baru_lahir_dengan_BBLR_mendapat_tata_laksana'].sum() / filtered_df['Jumlah_bayi_BBLR'].sum() * 100),
    "Cakupan Bayi PBLR (%)": (filtered_df['Jumlah_Bayi_PBLR'].sum() / total_bayi * 100),
    "Cakupan Bayi LIKA Rendah (%)": (filtered_df['Jumlah_Bayi_LIKA_Rendah'].sum() / total_bayi * 100)
}
    metric_list = [
        "Cakupan Bayi Lahir Prematur (%)",
        "Cakupan Bayi BBLR (%)",
        "Cakupan Bayi Prematur & BBLR Mendapat Buku KIA (%)",
        "Cakupan Bayi BBLR Mendapat Tatalaksana (%)",
        "Cakupan Bayi PBLR (%)",
        "Cakupan Bayi LIKA Rendah (%)"
    ]

    metric_to_columns = {
        "Cakupan Bayi Lahir Prematur (%)": ("Jumlah_bayi_lahir_37_minggu", "Jumlah_bayi_baru_lahir_hidup"),
        "Cakupan Bayi BBLR (%)": ("Jumlah_bayi_BBLR", "Jumlah_bayi_baru_lahir_hidup"),
        "Cakupan Bayi Prematur & BBLR Mendapat Buku KIA (%)": ("Jumlah_bayi_prematur_dan_BBLR_yang_mendapat_buku_KIA_bayi_kecil", "Jumlah_bayi_BBLR"),
        "Cakupan Bayi BBLR Mendapat Tatalaksana (%)": ("Jumlah_bayi_baru_lahir_dengan_BBLR_mendapat_tata_laksana", "Jumlah_bayi_BBLR"),
        "Cakupan Bayi PBLR (%)": ("Jumlah_Bayi_PBLR", "Jumlah_bayi_baru_lahir_hidup"),
        "Cakupan Bayi LIKA Rendah (%)": ("Jumlah_Bayi_LIKA_Rendah", "Jumlah_bayi_baru_lahir_hidup")
    }

    # Hitung persentase per baris dan tambahkan ke filtered_df
    for metric, (numerator_col, denominator_col) in metric_to_columns.items():
        filtered_df[metric] = (filtered_df[numerator_col] / filtered_df[denominator_col] * 100).round(2)
        # Ganti NaN atau inf dengan 0 untuk kebersihan data
        filtered_df[metric] = filtered_df[metric].replace([float('inf'), float('-inf')], 0).fillna(0)

    # Target
    targets = {
        "Cakupan Bayi Lahir Prematur (%)": 11,
        "Cakupan Bayi BBLR (%)": 5.8,
        "Cakupan Bayi Prematur & BBLR Mendapat Buku KIA (%)": 50,
        "Cakupan Bayi BBLR Mendapat Tatalaksana (%)": 35,
        "Cakupan Bayi PBLR (%)": None,
        "Cakupan Bayi LIKA Rendah (%)": None
    }

    # 1. Metrik Score Card
    st.subheader(f"📊 Metrik Indikator Bayi Kecil ({periode_label})")
    indikator_list = list(indikator_data.items())
    cols1 = st.columns(3)
    for i in range(3):
        label, value = indikator_list[i]
        target = targets[label]
        if target is not None:
            if label == "Cakupan Bayi Lahir Prematur (%)":
                if value <= 11:
                    delta_str = "dibawah target 11%"
                    delta_color = "normal"
                    delta_arrow = "↓"
                else:
                    delta_str = "diatas target 11%"
                    delta_color = "inverse"
                    delta_arrow = "↑"
            elif label == "Cakupan Bayi BBLR (%)":
                if value <= 5.8:
                    delta_str = "dibawah target 5.8%"
                    delta_color = "normal"
                    delta_arrow = "↓"
                else:
                    delta_str = "diatas target 5.8%"
                    delta_color = "inverse"
                    delta_arrow = "↑"
            else:  # Cakupan Bayi Prematur & BBLR Mendapat Buku KIA
                if value >= 50:
                    delta_str = "diatas target minimal 50%"
                    delta_color = "normal"
                    delta_arrow = "↑"
                else:
                    delta_str = "dibawah target minimal 50%"
                    delta_color = "inverse"
                    delta_arrow = "↓"
            cols1[i].metric(label=label, value=f"{value:.2f}%", delta=f"{delta_str} {delta_arrow}", delta_color=delta_color)
        else:
            cols1[i].metric(label=label, value=f"{value:.2f}%")

    cols2 = st.columns(3)
    for i in range(3):
        label, value = indikator_list[i + 3]
        target = targets[label]
        if target is not None:
            if label == "Cakupan Bayi BBLR Mendapat Tatalaksana (%)":
                if value >= 35:
                    delta_str = "diatas target minimal 35%"
                    delta_color = "normal"
                    delta_arrow = "↑"
                else:
                    delta_str = "dibawah target minimal 35%"
                    delta_color = "inverse"
                    delta_arrow = "↓"
            cols2[i].metric(label=label, value=f"{value:.2f}%", delta=f"{delta_str} {delta_arrow}", delta_color=delta_color)
        else:
            cols2[i].metric(label=label, value=f"{value:.2f}%")

    # 2. Grafik Visualisasi
    st.subheader(f"📈 Grafik Cakupan Bayi Kecil ({periode_label})")
    if puskesmas_filter == "All":
        grouped_df = filtered_df.groupby('Puskesmas').sum().reset_index()
        graph_data = pd.DataFrame({
            "Puskesmas": grouped_df['Puskesmas'],
            "Cakupan Bayi Lahir Prematur (%)": (grouped_df['Jumlah_bayi_lahir_37_minggu'] / grouped_df['Jumlah_bayi_baru_lahir_hidup'] * 100).fillna(0),
            "Cakupan Bayi BBLR (%)": (grouped_df['Jumlah_bayi_BBLR'] / grouped_df['Jumlah_bayi_baru_lahir_hidup'] * 100).fillna(0),
            "Cakupan Bayi PBLR (%)": (grouped_df['Jumlah_Bayi_PBLR'] / grouped_df['Jumlah_bayi_baru_lahir_hidup'] * 100).fillna(0),
            "Cakupan Bayi LIKA Rendah (%)": (grouped_df['Jumlah_Bayi_LIKA_Rendah'] / grouped_df['Jumlah_bayi_baru_lahir_hidup'] * 100).fillna(0)
        }).melt(id_vars=["Puskesmas"], var_name="Indikator", value_name="Persentase")
        fig1 = px.bar(graph_data, x="Puskesmas", y="Persentase", color="Indikator", barmode="group",
                      title=f"Cakupan Bayi Kecil per Puskesmas ({periode_label})", text=graph_data["Persentase"].apply(lambda x: f"{x:.1f}%"))
    else:
        grouped_df = filtered_df.groupby('Kelurahan').sum().reset_index()
        graph_data = pd.DataFrame({
            "Kelurahan": grouped_df['Kelurahan'],
            "Cakupan Bayi Lahir Prematur (%)": (grouped_df['Jumlah_bayi_lahir_37_minggu'] / grouped_df['Jumlah_bayi_baru_lahir_hidup'] * 100).fillna(0),
            "Cakupan Bayi BBLR (%)": (grouped_df['Jumlah_bayi_BBLR'] / grouped_df['Jumlah_bayi_baru_lahir_hidup'] * 100).fillna(0),
            "Cakupan Bayi PBLR (%)": (grouped_df['Jumlah_Bayi_PBLR'] / grouped_df['Jumlah_bayi_baru_lahir_hidup'] * 100).fillna(0),
            "Cakupan Bayi LIKA Rendah (%)": (grouped_df['Jumlah_Bayi_LIKA_Rendah'] / grouped_df['Jumlah_bayi_baru_lahir_hidup'] * 100).fillna(0)
        }).melt(id_vars=["Kelurahan"], var_name="Indikator", value_name="Persentase")
        fig1 = px.bar(graph_data, x="Kelurahan", y="Persentase", color="Indikator", barmode="group",
                      title=f"Cakupan Bayi Kecil per Kelurahan di {puskesmas_filter} ({periode_label})", text=graph_data["Persentase"].apply(lambda x: f"{x:.1f}%"))

    fig1.update_traces(textposition='outside')
    fig1.add_hline(
    y=100,
    line_dash="dash",
    line_color="red",
    annotation_text="Target: 100%",
    annotation_position="top right"
    )
    fig1.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", yaxis_range=[0, 100], title_x=0.5,
                       legend_title_text="Indikator", legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5),
                       height=500)
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader(f"📈 Grafik Cakupan Tatalaksana Bayi Kecil ({periode_label})")
    if puskesmas_filter == "All":
        grouped_df = filtered_df.groupby('Puskesmas').sum().reset_index()
        graph_data2 = pd.DataFrame({
            "Puskesmas": grouped_df['Puskesmas'],
            "Cakupan Buku KIA (%)": (grouped_df['Jumlah_bayi_prematur_dan_BBLR_yang_mendapat_buku_KIA_bayi_kecil'] / grouped_df['Jumlah_bayi_BBLR'] * 100).fillna(0),
            "Cakupan Tatalaksana (%)": (grouped_df['Jumlah_bayi_baru_lahir_dengan_BBLR_mendapat_tata_laksana'] / grouped_df['Jumlah_bayi_BBLR'] * 100).fillna(0)
        }).melt(id_vars=["Puskesmas"], var_name="Indikator", value_name="Persentase")
        fig2 = px.bar(graph_data2, x="Puskesmas", y="Persentase", color="Indikator", barmode="group",
                      title=f"Cakupan Tatalaksana Bayi Kecil per Puskesmas ({periode_label})", text=graph_data2["Persentase"].apply(lambda x: f"{x:.1f}%"))
    else:
        grouped_df = filtered_df.groupby('Kelurahan').sum().reset_index()
        graph_data2 = pd.DataFrame({
            "Kelurahan": grouped_df['Kelurahan'],
            "Cakupan Buku KIA (%)": (grouped_df['Jumlah_bayi_prematur_dan_BBLR_yang_mendapat_buku_KIA_bayi_kecil'] / grouped_df['Jumlah_bayi_BBLR'] * 100).fillna(0),
            "Cakupan Tatalaksana (%)": (grouped_df['Jumlah_bayi_baru_lahir_dengan_BBLR_mendapat_tata_laksana'] / grouped_df['Jumlah_bayi_BBLR'] * 100).fillna(0)
        }).melt(id_vars=["Kelurahan"], var_name="Indikator", value_name="Persentase")
        fig2 = px.bar(graph_data2, x="Kelurahan", y="Persentase", color="Indikator", barmode="group",
                      title=f"Cakupan Tatalaksana Bayi Kecil per Kelurahan di {puskesmas_filter} ({periode_label})", text=graph_data2["Persentase"].apply(lambda x: f"{x:.1f}%"))

    fig2.update_traces(textposition='outside')
    fig2.add_hline(
    y=100,
    line_dash="dash",
    line_color="red",
    annotation_text="Target: 100%",
    annotation_position="top right"
    )
    fig2.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", yaxis_range=[0, 100], title_x=0.5,
                       legend_title_text="Indikator", legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5),
                       height=500)
    st.plotly_chart(fig2, use_container_width=True)

    # 3. Tabel Rekapitulasi
    st.subheader(f"📋 Tabel Rekapitulasi Indikator Bayi Kecil ({periode_label})")
    if puskesmas_filter == "All":
        recap_df = filtered_df.groupby('Puskesmas').sum().reset_index()
    else:
        recap_df = filtered_df.groupby(['Puskesmas', 'Kelurahan']).sum().reset_index()

    recap_df['Cakupan Bayi Lahir Prematur (%)'] = (recap_df['Jumlah_bayi_lahir_37_minggu'] / recap_df['Jumlah_bayi_baru_lahir_hidup'] * 100).fillna(0).round(2)
    recap_df['Cakupan Bayi BBLR (%)'] = (recap_df['Jumlah_bayi_BBLR'] / recap_df['Jumlah_bayi_baru_lahir_hidup'] * 100).fillna(0).round(2)
    recap_df['Cakupan Bayi Prematur & BBLR Mendapat Buku KIA (%)'] = (recap_df['Jumlah_bayi_prematur_dan_BBLR_yang_mendapat_buku_KIA_bayi_kecil'] / recap_df['Jumlah_bayi_BBLR'] * 100).fillna(0).round(2)
    recap_df['Cakupan Bayi BBLR Mendapat Tatalaksana (%)'] = (recap_df['Jumlah_bayi_baru_lahir_dengan_BBLR_mendapat_tata_laksana'] / recap_df['Jumlah_bayi_BBLR'] * 100).fillna(0).round(2)
    recap_df['Cakupan Bayi PBLR (%)'] = (recap_df['Jumlah_Bayi_PBLR'] / recap_df['Jumlah_bayi_baru_lahir_hidup'] * 100).fillna(0).round(2)
    recap_df['Cakupan Bayi LIKA Rendah (%)'] = (recap_df['Jumlah_Bayi_LIKA_Rendah'] / recap_df['Jumlah_bayi_baru_lahir_hidup'] * 100).fillna(0).round(2)

    recap_display = recap_df[['Puskesmas', 'Kelurahan'] + list(indikator_data.keys())] if puskesmas_filter != "All" else recap_df[['Puskesmas'] + list(indikator_data.keys())]
    recap_display.insert(0, 'No', range(1, len(recap_display) + 1))

    # Definisikan fungsi highlight
    def highlight_outliers(row):
        styles = [''] * len(row)
        targets = {
            'Cakupan Bayi Lahir Prematur (%)': 100,
            'Cakupan Bayi BBLR (%)': 100,
            'Cakupan Bayi Prematur & BBLR Mendapat Buku KIA (%)': 100,
            'Cakupan Bayi BBLR Mendapat Tatalaksana (%)': 100,
            'Cakupan Bayi PBLR (%)': 100,
            'Cakupan Bayi LIKA Rendah (%)': 100
        }
        for col in targets:
            if col in row.index and pd.notna(row[col]) and row[col] > targets[col]:
                idx = row.index.get_loc(col)
                styles[idx] = 'background-color: #FF6666; color: white;'
        return styles

    # Pastikan data numerik dan bulatkan ke 2 digit desimal
    cols_to_check = [
        'Cakupan Bayi Lahir Prematur (%)',
        'Cakupan Bayi BBLR (%)',
        'Cakupan Bayi Prematur & BBLR Mendapat Buku KIA (%)',
        'Cakupan Bayi BBLR Mendapat Tatalaksana (%)',
        'Cakupan Bayi PBLR (%)',
        'Cakupan Bayi LIKA Rendah (%)'
    ]
    for col in cols_to_check:
        if col in recap_display.columns:
            recap_display[col] = pd.to_numeric(recap_display[col], errors='coerce').round(2)

    # Terapkan styling dan formatting
    styled_df = recap_display.style.apply(highlight_outliers, axis=1).format({
        'Cakupan Bayi Lahir Prematur (%)': "{:.2f}%",
        'Cakupan Bayi BBLR (%)': "{:.2f}%",
        'Cakupan Bayi Prematur & BBLR Mendapat Buku KIA (%)': "{:.2f}%",
        'Cakupan Bayi BBLR Mendapat Tatalaksana (%)': "{:.2f}%",
        'Cakupan Bayi PBLR (%)': "{:.2f}%",
        'Cakupan Bayi LIKA Rendah (%)': "{:.2f}%"
    }, na_rep="N/A", precision=2)

    # Render tabel dengan styling yang eksplisit
    st.write(styled_df, unsafe_allow_html=True)

    # Tambahkan notice di bawah tabel
    st.markdown(
        """
        <div style="background-color: #ADD8E6; padding: 10px; border-radius: 5px; color: black; font-size: 14px; font-family: Arial, sans-serif;">
            <strong>Catatan Penting:</strong> Nilai yang melebihi 100% (indikasi data outlier) telah dihighlight <span style="color: #FF6666; font-weight: bold;">Warna Merah</span>. Untuk analisis lebih lanjut dan koreksi data, mohon dilakukan pemeriksaan pada <strong>Menu Daftar Entry</strong>.
        </div>
        """,
        unsafe_allow_html=True
    )
    # 3.1 🚨 Tabel Deteksi Outlier (Logis)
    st.subheader("🚨 Tabel Deteksi Outlier")
    # Mapping metrik ke kolom numerator dan denominator
    metric_to_columns = {
        "Cakupan Bayi Lahir Prematur (%)": ("Jumlah_bayi_lahir_37_minggu", "Jumlah_bayi_baru_lahir_hidup"),
        "Cakupan Bayi BBLR (%)": ("Jumlah_bayi_BBLR", "Jumlah_bayi_baru_lahir_hidup"),
        "Cakupan Bayi Prematur & BBLR Mendapat Buku KIA (%)": ("Jumlah_bayi_prematur_dan_BBLR_yang_mendapat_buku_KIA_bayi_kecil", "Jumlah_bayi_BBLR"),
        "Cakupan Bayi BBLR Mendapat Tatalaksana (%)": ("Jumlah_bayi_baru_lahir_dengan_BBLR_mendapat_tata_laksana", "Jumlah_bayi_BBLR"),
        "Cakupan Bayi PBLR (%)": ("Jumlah_Bayi_PBLR", "Jumlah_bayi_baru_lahir_hidup"),
        "Cakupan Bayi LIKA Rendah (%)": ("Jumlah_Bayi_LIKA_Rendah", "Jumlah_bayi_baru_lahir_hidup")
    }

    # Inisialisasi DataFrame untuk outlier logis
    outliers_df = pd.DataFrame(columns=["Puskesmas", "Kelurahan", "Metrik", "Numerator", "Denominator", "Rasio", "Alasan"])

    # Deteksi outlier logis untuk setiap metrik
    for metric, (numerator_col, denominator_col) in metric_to_columns.items():
        # Kasus 1: Numerator > Denominator
        outlier_data_num = filtered_df[
            (filtered_df[numerator_col] > filtered_df[denominator_col]) &
            (filtered_df[denominator_col] != 0)
        ][["Puskesmas", "Kelurahan", numerator_col, denominator_col]]
        if not outlier_data_num.empty:
            outlier_data_num["Metrik"] = metric
            outlier_data_num["Numerator"] = outlier_data_num[numerator_col]
            outlier_data_num["Denominator"] = outlier_data_num[denominator_col]
            outlier_data_num["Rasio"] = (outlier_data_num[numerator_col] / outlier_data_num[denominator_col] * 100).round(2)
            outlier_data_num["Alasan"] = "Numerator > Denominator"
            outliers_df = pd.concat(
                [outliers_df, outlier_data_num[["Puskesmas", "Kelurahan", "Metrik", "Numerator", "Denominator", "Rasio", "Alasan"]]],
                ignore_index=True
            )

        # Kasus 2: Denominator = 0
        outlier_data_zero = filtered_df[
            (filtered_df[denominator_col] == 0) &
            (filtered_df[numerator_col] > 0)
        ][["Puskesmas", "Kelurahan", numerator_col, denominator_col]]
        if not outlier_data_zero.empty:
            outlier_data_zero["Metrik"] = metric
            outlier_data_zero["Numerator"] = outlier_data_zero[numerator_col]
            outlier_data_zero["Denominator"] = outlier_data_zero[denominator_col]
            outlier_data_zero["Rasio"] = "Infinity"
            outlier_data_zero["Alasan"] = "Denominator = 0"
            outliers_df = pd.concat(
                [outliers_df, outlier_data_zero[["Puskesmas", "Kelurahan", "Metrik", "Numerator", "Denominator", "Rasio", "Alasan"]]],
                ignore_index=True
            )

    # Tampilkan Tabel Outlier Logis
    if not outliers_df.empty:
        styled_outliers = outliers_df.style.apply(
            lambda x: ['background-color: #FF6666; color: white;' if x['Alasan'] == "Numerator > Denominator" else 'background-color: #FF4500; color: white;'] * len(x),
            axis=1
        ).format({
            "Numerator": "{:.0f}",
            "Denominator": "{:.0f}",
            "Rasio": lambda x: f"{x:.2f}%" if isinstance(x, (int, float)) else x
        }).set_properties(**{
            'border': '1px solid black',
            'text-align': 'center',
            'font-size': '14px',
            'font-family': 'Arial, sans-serif'
        }).set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold')]},
            {'selector': 'caption', 'props': [('caption-side', 'top'), ('font-size', '18px'), ('font-weight', 'bold'), ('color', '#333')]},
        ]).set_caption("Tabel Outlier: Data dengan Numerator > Denominator atau Denominator = 0")

        st.write(styled_outliers, unsafe_allow_html=True)
    else:
        st.success("✅ Tidak ada outlier terdeteksi berdasarkan kriteria Numerator > Denominator atau Denominator = 0.")

    # 3.2 ⚙️ Analisis Outlier Statistik
    st.subheader("⚙️ Analisis Outlier Statistik")
    # Gunakan recap_df yang sudah dihitung persentasenya
    cols_to_check = list(indikator_data.keys())

    # Inisialisasi DataFrame untuk outlier statistik
    base_columns = ["Puskesmas", "Metrik", "Nilai", "Metode"]
    if puskesmas_filter != "All":
        base_columns.insert(1, "Kelurahan")
    statistical_outliers_df = pd.DataFrame(columns=base_columns)

    # Dropdown untuk memilih metode deteksi outlier statistik
    outlier_method = st.selectbox(
        "Pilih Metode Deteksi Outlier Statistik",
        ["Tidak Ada", "Z-Score", "IQR"],
        key=f"outlier_method_select_bayi_kecil_{periode_label}"
    )

    if outlier_method != "Tidak Ada":
        for metric in cols_to_check:
            if metric not in recap_df.columns:
                continue

            # Pilih kolom berdasarkan filter
            if puskesmas_filter == "All":
                metric_data = recap_df[[metric, "Puskesmas"]].dropna()
            else:
                metric_data = recap_df[[metric, "Puskesmas", "Kelurahan"]].dropna()

            if metric_data.empty:
                continue

            # Z-Score Method
            if outlier_method == "Z-Score":
                z_scores = stats.zscore(metric_data[metric], nan_policy='omit')
                z_outlier_mask = abs(z_scores) > 3  # Threshold Z-Score > 3
                z_outliers = metric_data[z_outlier_mask].copy()
                if not z_outliers.empty:
                    z_outliers["Metrik"] = metric
                    z_outliers["Nilai"] = z_outliers[metric]
                    z_outliers["Metode"] = "Z-Score"
                    if puskesmas_filter == "All":
                        z_outliers_subset = z_outliers[["Puskesmas", "Metrik", "Nilai", "Metode"]]
                    else:
                        z_outliers_subset = z_outliers[["Puskesmas", "Kelurahan", "Metrik", "Nilai", "Metode"]]
                    statistical_outliers_df = pd.concat(
                        [statistical_outliers_df, z_outliers_subset],
                        ignore_index=True
                    )

            # IQR Method
            elif outlier_method == "IQR":
                Q1 = metric_data[metric].quantile(0.25)
                Q3 = metric_data[metric].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                iqr_outlier_mask = (metric_data[metric] < lower_bound) | (metric_data[metric] > upper_bound)
                iqr_outliers = metric_data[iqr_outlier_mask].copy()
                if not iqr_outliers.empty:
                    iqr_outliers["Metrik"] = metric
                    iqr_outliers["Nilai"] = iqr_outliers[metric]
                    iqr_outliers["Metode"] = "IQR"
                    if puskesmas_filter == "All":
                        iqr_outliers_subset = iqr_outliers[["Puskesmas", "Metrik", "Nilai", "Metode"]]
                    else:
                        iqr_outliers_subset = iqr_outliers[["Puskesmas", "Kelurahan", "Metrik", "Nilai", "Metode"]]
                    statistical_outliers_df = pd.concat(
                        [statistical_outliers_df, iqr_outliers_subset],
                        ignore_index=True
                    )

    # 3.3 📊 Tabel Outlier Statistik
    if not statistical_outliers_df.empty:
        st.markdown("### 📊 Tabel Outlier Statistik")
        styled_stat_outliers = statistical_outliers_df.style.apply(
            lambda x: ['background-color: #FFA500; color: white;' if x['Metode'] == "Z-Score" else 'background-color: #FF8C00; color: white;'] * len(x),
            axis=1
        ).format({
            "Nilai": "{:.2f}%"
        }).set_properties(**{
            'border': '1px solid black',
            'text-align': 'center',
            'font-size': '14px',
            'font-family': 'Arial, sans-serif'
        }).set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#FF9800'), ('color', 'white'), ('font-weight', 'bold')]},
            {'selector': 'caption', 'props': [('caption-side', 'top'), ('font-size', '18px'), ('font-weight', 'bold'), ('color', '#333')]},
        ]).set_caption(f"Tabel Outlier Statistik ({outlier_method})")

        st.write(styled_stat_outliers, unsafe_allow_html=True)
    else:
        if outlier_method != "Tidak Ada":
            st.info(f"ℹ️ Tidak ada outlier statistik terdeteksi menggunakan metode {outlier_method}.")

    # 3.4 📊 Visualisasi Outlier
    st.subheader("📊 Visualisasi Outlier")
    show_outlier_viz = st.checkbox(
        "Tampilkan Visualisasi Outlier",
        value=False,
        key=f"bayi_kecil_viz_toggle_{periode_label}"
    )

    if show_outlier_viz:
        # Gabungkan outlier logis dan statistik
        combined_outliers = outliers_df[["Puskesmas", "Kelurahan", "Metrik", "Rasio"]].copy()
        combined_outliers["Metode"] = "Logis (Numerator > Denominator atau Denominator = 0)"
        # Ganti "Infinity" dengan nilai besar untuk visualisasi
        combined_outliers["Rasio"] = combined_outliers["Rasio"].replace("Infinity", 9999)
        if not statistical_outliers_df.empty:
            stat_outliers = statistical_outliers_df[["Puskesmas", "Metrik", "Metode"]].copy()
            stat_outliers["Rasio"] = statistical_outliers_df["Nilai"]
            if "Kelurahan" in statistical_outliers_df.columns:
                stat_outliers["Kelurahan"] = statistical_outliers_df["Kelurahan"]
            else:
                stat_outliers["Kelurahan"] = "N/A"
            combined_outliers = pd.concat([combined_outliers, stat_outliers], ignore_index=True)

        if not combined_outliers.empty:
            viz_type = st.selectbox(
                "Pilih Tipe Visualisasi Outlier",
                ["Heatmap", "Grafik Batang", "Boxplot"],
                key=f"outlier_viz_select_bayi_kecil_{periode_label}"
            )

            if viz_type == "Heatmap":
                pivot_df = combined_outliers.pivot_table(
                    index="Puskesmas",
                    columns="Metrik",
                    values="Rasio",
                    aggfunc="mean",
                    fill_value=0
                )
                fig_heatmap = px.imshow(
                    pivot_df,
                    text_auto=True,
                    aspect="auto",
                    title="Heatmap Distribusi Outlier per Puskesmas",
                    color_continuous_scale="Reds"
                )
                fig_heatmap.update_layout(
                    xaxis_title="Metrik",
                    yaxis_title="Puskesmas",
                    coloraxis_colorbar_title="Rasio (%)"
                )
                st.plotly_chart(fig_heatmap, use_container_width=True)

            elif viz_type == "Grafik Batang":
                count_df = combined_outliers.groupby(["Metrik", "Metode"]).size().reset_index(name="Jumlah")
                fig_bar = px.bar(
                    count_df,
                    x="Metrik",
                    y="Jumlah",
                    color="Metode",
                    barmode="group",
                    title="Jumlah Outlier per Metrik dan Metode Deteksi",
                    text="Jumlah"
                )
                fig_bar.update_traces(textposition="outside")
                fig_bar.update_layout(
                    xaxis_title="Metrik",
                    yaxis_title="Jumlah Outlier",
                    xaxis_tickangle=45,
                    legend_title="Metode Deteksi"
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            elif viz_type == "Boxplot":
                fig_box = px.box(
                    combined_outliers,
                    x="Metrik",
                    y="Rasio",
                    color="Metode",
                    title="Boxplot Distribusi Outlier per Metrik dan Metode Deteksi",
                    points="all"
                )
                fig_box.update_layout(
                    xaxis_title="Metrik",
                    yaxis_title="Rasio (%)",
                    xaxis_tickangle=45,
                    legend_title="Metode Deteksi"
                )
                st.plotly_chart(fig_box, use_container_width=True)
        else:
            st.info("ℹ️ Tidak ada data outlier untuk divisualisasikan.")
    
    # 3.5 📈 Analisis Tren Metrik Bayi Kecil (diperbarui)
    st.subheader("📈 Tren Metrik Bayi Kecil")
    # Filter dan agregasi data berdasarkan Bulan
    trend_df = filtered_df.groupby("Bulan")[metric_list].mean().reset_index()
    trend_df = trend_df.melt(
        id_vars="Bulan",
        value_vars=metric_list,
        var_name="Metrik",
        value_name="Persentase"
    )

    # Bulatkan kolom Persentase menjadi 2 digit desimal
    trend_df["Persentase"] = trend_df["Persentase"].round(2)

    # Tampilkan line chart untuk semua metrik
    if not trend_df.empty:
        fig_trend = px.line(
            trend_df,
            x="Bulan",
            y="Persentase",
            color="Metrik",
            markers=True,
            text=trend_df["Persentase"].apply(lambda x: f"{x:.2f}"),
            title="📈 Tren Metrik Bayi Kecil dari Awal hingga Akhir Bulan"
        )
        fig_trend.update_traces(textposition="top center")
        fig_trend.update_layout(
            xaxis_title="Bulan",
            yaxis_title="Persentase (%)",
            xaxis=dict(tickmode='linear', tick0=1, dtick=1),
            yaxis_range=[0, 100],
            legend_title="Metrik",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(
            fig_trend,
            key=f"bayi_kecil_trend_chart_{puskesmas_filter}_{kelurahan_filter}_{time.time()}",
            use_container_width=True
        )
    else:
        st.warning("⚠️ Tidak ada data untuk ditampilkan pada grafik tren Bayi Kecil.")

    # 3.6 📊 Analisis Komparasi Antar Wilayah
    st.subheader("📊 Analisis Komparasi Antar Wilayah")
    # Dropdown untuk memilih metrik yang ingin dibandingkan
    selected_metric = st.selectbox(
        "Pilih Metrik untuk Komparasi Antar Wilayah",
        metric_list,
        key="comp_metric_select_bayi_kecil"
    )

    # Filter data berdasarkan metrik yang dipilih
    comp_df = filtered_df.groupby(["Puskesmas", "Kelurahan"])[selected_metric].mean().reset_index()
    if not comp_df.empty:
        fig_comp = px.bar(
            comp_df,
            x="Puskesmas",
            y=selected_metric,
            color="Kelurahan",
            title=f"📊 Komparasi {selected_metric} Antar Wilayah",
            text=comp_df[selected_metric].apply(lambda x: f"{x:.2f}%"),
            height=400
        )
        fig_comp.update_traces(textposition="outside")
        fig_comp.update_layout(
            xaxis_title="Puskesmas",
            yaxis_title="Persentase (%)",
            xaxis_tickangle=45,
            yaxis_range=[0, 100],
            legend_title="Kelurahan"
        )
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.warning("⚠️ Tidak ada data untuk komparasi antar wilayah.")

    # 3.7 🔍 Analisis Korelasi Antar Metrik
    st.subheader("🔍 Analisis Korelasi Antar Metrik")
    # Hitung korelasi antar metrik menggunakan data agregat per Puskesmas/Kelurahan
    corr_df = filtered_df.groupby(["Puskesmas", "Kelurahan"])[metric_list].mean().reset_index()
    if len(corr_df) > 1:  # Pastikan ada cukup data untuk korelasi
        correlation_matrix = corr_df[metric_list].corr()
        fig_corr = px.imshow(
            correlation_matrix,
            text_auto=True,
            aspect="auto",
            title="🔍 Matriks Korelasi Antar Metrik Bayi Kecil",
            color_continuous_scale="RdBu",
            range_color=[-1, 1]
        )
        fig_corr.update_layout(
            xaxis_title="Metrik",
            yaxis_title="Metrik",
            coloraxis_colorbar_title="Koefisien Korelasi"
        )
        st.plotly_chart(fig_corr, use_container_width=True)
        st.markdown("**Catatan:** Nilai mendekati 1 atau -1 menunjukkan korelasi kuat (positif atau negatif), sementara 0 menunjukkan tidak ada korelasi.")
    else:
        st.warning("⚠️ Tidak cukup data untuk menghitung korelasi antar metrik.")

    # 3.8 📅 Analisis Perubahan Persentase (Growth/Decline)
    st.subheader("📅 Analisis Perubahan Persentase (Growth/Decline)")
    # Pastikan data tren sudah ada
    if not trend_df.empty:
        # Hitung perubahan persentase dari bulan ke bulan
        trend_df = trend_df.sort_values("Bulan")
        trend_df["Perubahan Persentase"] = trend_df.groupby("Metrik")["Persentase"].pct_change() * 100
        trend_df["Perubahan Persentase"] = trend_df["Perubahan Persentase"].round(2)

        # Tampilkan tabel perubahan
        st.dataframe(
            trend_df[["Bulan", "Metrik", "Persentase", "Perubahan Persentase"]].style.format({
                "Persentase": "{:.2f}%",
                "Perubahan Persentase": "{:.2f}%"
            }).set_properties(**{
                'text-align': 'center',
                'font-size': '14px',
                'border': '1px solid black'
            }).set_table_styles([
                {'selector': 'th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold')]},
                {'selector': 'caption', 'props': [('caption-side', 'top'), ('font-size', '18px'), ('font-weight', 'bold'), ('color', '#333')]},
            ]).set_caption("📅 Tabel Perubahan Persentase Antar Bulan"),
            use_container_width=True
        )

        # Visualisasi perubahan dengan grafik garis
        fig_change = px.line(
            trend_df,
            x="Bulan",
            y="Perubahan Persentase",
            color="Metrik",
            markers=True,
            text=trend_df["Perubahan Persentase"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else ""),
            title="📅 Tren Perubahan Persentase Metrik Bayi Kecil"
        )
        fig_change.update_traces(textposition="top center")
        fig_change.update_layout(
            xaxis_title="Bulan",
            yaxis_title="Perubahan Persentase (%)",
            xaxis=dict(tickmode='linear', tick0=1, dtick=1),
            legend_title="Metrik",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_change, use_container_width=True)
    else:
        st.warning("⚠️ Tidak ada data untuk menganalisis perubahan persentase.")

    # 3.9 📉 Analisis Distribusi Data (Histogram)
    st.subheader("📉 Analisis Distribusi Data (Histogram)")
    # Dropdown untuk memilih metrik yang ingin dianalisis distribusinya
    selected_metric_dist = st.selectbox(
        "Pilih Metrik untuk Analisis Distribusi",
        metric_list,
        key="dist_metric_select_bayi_kecil"
    )

    # Buat histogram berdasarkan data per Puskesmas/Kelurahan
    dist_df = filtered_df.groupby(["Puskesmas", "Kelurahan"])[selected_metric_dist].mean().reset_index()
    if not dist_df.empty:
        fig_dist = px.histogram(
            dist_df,
            x=selected_metric_dist,
            nbins=20,
            title=f"📉 Distribusi {selected_metric_dist} di Seluruh Wilayah",
            labels={"value": "Persentase (%)", "count": "Jumlah Wilayah"},
            height=400
        )
        fig_dist.update_layout(
            xaxis_title="Persentase (%)",
            yaxis_title="Jumlah Wilayah",
            bargap=0.1
        )
        st.plotly_chart(fig_dist, use_container_width=True)
        # Tambahan statistik dasar
        mean_val = dist_df[selected_metric_dist].mean().round(2)
        median_val = dist_df[selected_metric_dist].median().round(2)
        st.markdown(f"**Statistik Distribusi:** Rata-rata = {mean_val}%, Median = {median_val}%")
    else:
        st.warning("⚠️ Tidak ada data untuk analisis distribusi.")

    # 4. Fitur Download Laporan PDF dengan reportlab tanpa menyimpan file lokal
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
        elements.append(Paragraph(f"Laporan Indikator Bayi Kecil ({periode_label})", title_style))
        elements.append(Paragraph(f"Diperbarui: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
        elements.append(Spacer(1, 12))

        # Tambahkan Metrik
        elements.append(Paragraph("1. Metrik Indikator", normal_style))
        metric_data = []
        for label, value in indikator_list:
            target = targets[label]
            if target is not None:
                if label == "Cakupan Bayi Lahir Prematur (%)":
                    delta_str = "dibawah target 11%" if value <= 11 else "diatas target 11%"
                    delta_color = colors.green if value <= 11 else colors.red
                elif label == "Cakupan Bayi BBLR (%)":
                    delta_str = "dibawah target 5.8%" if value <= 5.8 else "diatas target 5.8%"
                    delta_color = colors.green if value <= 5.8 else colors.red
                elif label == "Cakupan Bayi Prematur & BBLR Mendapat Buku KIA (%)":
                    delta_str = "diatas target minimal 50%" if value >= 50 else "dibawah target minimal 50%"
                    delta_color = colors.green if value >= 50 else colors.red
                elif label == "Cakupan Bayi BBLR Mendapat Tatalaksana (%)":
                    delta_str = "diatas target minimal 35%" if value >= 35 else "dibawah target minimal 35%"
                    delta_color = colors.green if value >= 35 else colors.red
                delta_arrow = "↓" if (value <= 11 or value <= 5.8 or value >= 50 or value >= 35) else "↑"
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
        elements.append(Paragraph("2. Grafik Cakupan Bayi Kecil", normal_style))
        elements.append(Image(img_buffer1, width=500, height=300))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("3. Grafik Cakupan Tatalaksana Bayi Kecil", normal_style))
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

    if st.button("Download Laporan PDF", key=f"download_indikator_bayi_kecil_{periode_label}"):
        st.warning("Membuat laporan PDF, harap tunggu...")
        pdf_data = generate_pdf_report()
        st.success("Laporan PDF siap diunduh!")
        st.download_button(
            label="Download Laporan PDF",
            data=pdf_data,
            file_name=f"Laporan_Indikator_Bayi_Kecil_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )
# ---------------------------------- #
# 📈 Pemantauan Tumbuh Kembang Balita
# ---------------------------------- #
def pemantauan_tumbuh_kembang_balita(filtered_df, desa_df, puskesmas_filter, kelurahan_filter, jenis_laporan, tahun_filter, bulan_filter_int=None, tribulan_filter=None):
    """Menampilkan analisis Pemantauan Tumbuh Kembang Balita dengan fitur download laporan."""
    st.header("📈 Pemantauan Tumbuh Kembang Balita")
    # Informasi Metrik Pemantauan Tumbuh Kembang Balita
    with st.expander("📜 Definisi dan Insight Analisis Pemantauan Tumbuh Kembang Balita", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Analisis Indikator

            Berikut adalah definisi operasional, rumus perhitungan, serta analisis insight dari indikator-indikator yang digunakan untuk memantau tumbuh kembang balita (usia 0-5 tahun) dalam kerangka Surveilans Deteksi Dini Tumbuh Kembang (SDIDTK) versi terbaru, diperbarui hingga Mei 2025. Rumus disajikan dalam format matematis untuk kejelasan, dengan penjelasan sederhana untuk mendukung pemahaman petugas kesehatan.

            #### 1. Persentase Balita Ditimbang
            - **Definisi Operasional:** Persentase balita (usia 0-5 tahun) yang ditimbang berat badannya terhadap total balita pada bulan pelaporan di wilayah kerja puskesmas, sesuai pedoman SDIDTK untuk pemantauan pertumbuhan fisik.  
            - **Rumus Perhitungan:**  
            $$ \\text{Metrik Balita ditimbang (\\%)} = \\frac{\\text{Jumlah balita ditimbang}}{\\text{Total balita bulan ini}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen balita yang ditimbang dari total balita pada bulan tersebut, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan bulanan melalui laporan posyandu atau puskesmas, dengan pencatatan jumlah balita yang ditimbang menggunakan timbangan standar SDIDTK.  
            - **Insight Analisis:** Persentase di bawah 80% (target SDIDTK 2025) dapat mengindikasikan rendahnya cakupan pemantauan atau keterbatasan akses. Peningkatan pelatihan kader dan penyediaan alat timbangan dapat meningkatkan cakupan, mendukung deteksi dini gangguan pertumbuhan seperti stunting atau wasting.

            #### 2. Persentase Balita Memiliki Buku KIA
            - **Definisi Operasional:** Persentase balita (usia 0-5 tahun) yang memiliki Buku Kesehatan Ibu dan Anak (KIA) untuk dokumentasi tumbuh kembang terhadap total balita pada bulan pelaporan, sesuai pedoman SDIDTK.  
            - **Rumus Perhitungan:**  
            $$ \\text{Metrik Balita punya buku KIA (\\%)} = \\frac{\\text{Jumlah balita punya Buku KIA}}{\\text{Total balita bulan ini}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen balita yang memiliki Buku KIA dari total balita pada bulan tersebut, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data diambil dari laporan bulanan posyandu, dengan pencatatan jumlah balita yang membawa atau didokumentasikan memiliki Buku KIA.  
            - **Insight Analisis:** Persentase di bawah 90% (target SDIDTK 2025) dapat menunjukkan kurangnya distribusi Buku KIA. Peningkatan sosialisasi dan penyediaan gratis dapat meningkatkan kepemilikan, memastikan rekam medis perkembangan balita yang konsisten.

            #### 3. Persentase Balita dengan Perkembangan Normal
            - **Definisi Operasional:** Persentase balita (usia 0-5 tahun) yang menunjukkan perkembangan normal berdasarkan skrining SDIDTK terhadap total balita yang diskrining pada bulan pelaporan di wilayah kerja puskesmas.  
            - **Rumus Perhitungan:**  
            $$ \\text{Metrik Balita dengan perkembangan normal (\\%)} = \\frac{\\text{Jumlah balita dengan perkembangan normal}}{\\text{Total balita diskrining}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen balita dengan perkembangan normal dari total balita yang diskrining, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui laporan bulanan posyandu, dengan skrining menggunakan alat KPSP (Kuesioner Pra Skrining Perkembangan) versi terbaru SDIDTK 2025, disesuaikan untuk usia balita.  
            - **Insight Analisis:** Persentase di bawah 85% dapat mengindikasikan adanya masalah perkembangan yang perlu ditindaklanjuti. Pelatihan kader untuk penggunaan KPSP dan rujukan dini ke layanan kesehatan dapat meningkatkan intervensi, mencegah keterlambatan perkembangan.

            #### 4. Persentase Balita dengan Perkembangan Meragukan
            - **Definisi Operasional:** Persentase balita (usia 0-5 tahun) yang menunjukkan perkembangan meragukan berdasarkan skrining SDIDTK terhadap total balita yang diskrining pada bulan pelaporan.  
            - **Rumus Perhitungan:**  
            $$ \\text{Metrik Balita dengan perkembangan meragukan (\\%)} = \\frac{\\text{Jumlah balita dengan perkembangan meragukan}}{\\text{Total balita diskrining}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen balita dengan perkembangan meragukan dari total balita yang diskrining, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data diambil dari laporan bulanan posyandu, dengan klasifikasi berdasarkan hasil KPSP SDIDTK 2025 untuk balita.  
            - **Insight Analisis:** Persentase di atas 10% (batas SDIDTK 2025) dapat menunjukkan kebutuhan intervensi tambahan, seperti stimulasi perkembangan. Edukasi orang tua dan skrining ulang dapat mengurangi angka ini.

            #### 5. Persentase Balita dengan Kemungkinan Penyimpangan
            - **Definisi Operasional:** Persentase balita (usia 0-5 tahun) yang menunjukkan kemungkinan penyimpangan perkembangan berdasarkan skrining SDIDTK terhadap total balita yang diskrining pada bulan pelaporan.  
            - **Rumus Perhitungan:**  
            $$ \\text{Metrik Balita dengan kemungkinan penyimpangan (\\%)} = \\frac{\\text{Jumlah balita dengan kemungkinan penyimpangan}}{\\text{Total balita diskrining}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen balita dengan kemungkinan penyimpangan dari total balita yang diskrining, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui laporan bulanan posyandu, dengan hasil skrining KPSP SDIDTK 2025 yang divalidasi oleh tenaga kesehatan untuk balita.  
            - **Insight Analisis:** Persentase di atas 5% (batas SDIDTK 2025) menunjukkan kebutuhan rujukan segera ke layanan kesehatan spesialis. Koordinasi dengan puskesmas untuk rujukan dan intervensi terapeutik dapat menurunkan angka ini, mencegah dampak perkembangan jangka panjang.

            </div>
        """, unsafe_allow_html=True)

    # Daftar kolom yang dibutuhkan
    required_columns = [
        'Jumlah_balita_diskrining_perkembangan',
        'Jumlah_balita_dengan_perkembangan_normal',
        'Jumlah_balita_dengan_perkembangan_meragukan',
        'Jumlah_balita_dengan_kemungkinan_penyimpangan'
    ]

    # Cek apakah semua kolom ada
    missing_cols = [col for col in required_columns if col not in filtered_df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di dataset: {missing_cols}. Periksa data di 'data_balita_kia'!")
        return

    # Inisialisasi periode untuk label
    periode_label = ""
    if tahun_filter != "All":
        periode_label += f"Tahun {tahun_filter}"
    if jenis_laporan == "Bulanan" and bulan_filter_int is not None:
        periode_label += f" Bulan {bulan_filter_int}" if periode_label else f"Bulan {bulan_filter_int}"
    elif jenis_laporan == "Tahunan" and tribulan_filter:
        periode_label += f" {tribulan_filter}" if periode_label else tribulan_filter

    # Agregasi data berdasarkan jenis laporan
    if jenis_laporan == "Tahunan" and not filtered_df.empty:
        group_columns = ["Puskesmas", "Kelurahan"]
        numeric_columns = [col for col in filtered_df.columns if filtered_df[col].dtype in ['int64', 'float64']]
        if numeric_columns:
            agg_dict = {col: "sum" for col in numeric_columns}
            filtered_df = filtered_df.groupby(group_columns).agg(agg_dict).reset_index()

    # Hitung total balita yang diskrining
    total_diskrining = filtered_df['Jumlah_balita_diskrining_perkembangan'].sum()
    if total_diskrining == 0:
        st.warning("⚠️ Tidak ada data balita yang diskrining untuk filter ini.")
        return

    # Hitung metrik
    metrik_data = {
        "Metrik Balita dengan perkembangan normal (%)": (filtered_df['Jumlah_balita_dengan_perkembangan_normal'].sum() / total_diskrining * 100),
        "Metrik Balita dengan perkembangan meragukan (%)": (filtered_df['Jumlah_balita_dengan_perkembangan_meragukan'].sum() / total_diskrining * 100),
        "Metrik Balita dengan kemungkinan penyimpangan (%)": (filtered_df['Jumlah_balita_dengan_kemungkinan_penyimpangan'].sum() / total_diskrining * 100)
    }
    # Hitung metrik persentase per baris dan tambahkan ke filtered_df
    filtered_df['Metrik Balita dengan perkembangan normal (%)'] = (
        (filtered_df['Jumlah_balita_dengan_perkembangan_normal'] / filtered_df['Jumlah_balita_diskrining_perkembangan'] * 100)
        .round(2)
        .fillna(0)
    )
    filtered_df['Metrik Balita dengan perkembangan meragukan (%)'] = (
        (filtered_df['Jumlah_balita_dengan_perkembangan_meragukan'] / filtered_df['Jumlah_balita_diskrining_perkembangan'] * 100)
        .round(2)
        .fillna(0)
    )
    filtered_df['Metrik Balita dengan kemungkinan penyimpangan (%)'] = (
        (filtered_df['Jumlah_balita_dengan_kemungkinan_penyimpangan'] / filtered_df['Jumlah_balita_diskrining_perkembangan'] * 100)
        .round(2)
        .fillna(0)
    )

    # 1. Metrik Score Card
    st.subheader(f"📊 Metrik Pemantauan Tumbuh Kembang Balita ({periode_label})")
    metrik_list = list(metrik_data.items())
    cols = st.columns(3)
    for i in range(3):
        label, value = metrik_list[i]
        cols[i].metric(label=label, value=f"{value:.2f}%")

    # 2. Grafik Visualisasi
    st.subheader(f"📈 Grafik Pemantauan Tumbuh Kembang Balita ({periode_label})")
    if puskesmas_filter == "All":
        grouped_df = filtered_df.groupby('Puskesmas').sum().reset_index()
        graph_data = pd.DataFrame({
            "Puskesmas": grouped_df['Puskesmas'],
            "Metrik Balita dengan perkembangan normal (%)": (grouped_df['Jumlah_balita_dengan_perkembangan_normal'] / grouped_df['Jumlah_balita_diskrining_perkembangan'] * 100).fillna(0),
            "Metrik Balita dengan perkembangan meragukan (%)": (grouped_df['Jumlah_balita_dengan_perkembangan_meragukan'] / grouped_df['Jumlah_balita_diskrining_perkembangan'] * 100).fillna(0),
            "Metrik Balita dengan kemungkinan penyimpangan (%)": (grouped_df['Jumlah_balita_dengan_kemungkinan_penyimpangan'] / grouped_df['Jumlah_balita_diskrining_perkembangan'] * 100).fillna(0)
        }).melt(id_vars=["Puskesmas"], var_name="Indikator", value_name="Persentase")
        fig = px.bar(graph_data, x="Puskesmas", y="Persentase", color="Indikator", barmode="group",
                     title=f"Pemantauan Tumbuh Kembang Balita per Puskesmas ({periode_label})", text=graph_data["Persentase"].apply(lambda x: f"{x:.1f}%"))
    else:
        grouped_df = filtered_df.groupby('Kelurahan').sum().reset_index()
        graph_data = pd.DataFrame({
            "Kelurahan": grouped_df['Kelurahan'],
            "Metrik Balita dengan perkembangan normal (%)": (grouped_df['Jumlah_balita_dengan_perkembangan_normal'] / grouped_df['Jumlah_balita_diskrining_perkembangan'] * 100).fillna(0),
            "Metrik Balita dengan perkembangan meragukan (%)": (grouped_df['Jumlah_balita_dengan_perkembangan_meragukan'] / grouped_df['Jumlah_balita_diskrining_perkembangan'] * 100).fillna(0),
            "Metrik Balita dengan kemungkinan penyimpangan (%)": (grouped_df['Jumlah_balita_dengan_kemungkinan_penyimpangan'] / grouped_df['Jumlah_balita_diskrining_perkembangan'] * 100).fillna(0)
        }).melt(id_vars=["Kelurahan"], var_name="Indikator", value_name="Persentase")
        fig = px.bar(graph_data, x="Kelurahan", y="Persentase", color="Indikator", barmode="group",
                     title=f"Pemantauan Tumbuh Kembang Balita per Kelurahan di {puskesmas_filter} ({periode_label})", text=graph_data["Persentase"].apply(lambda x: f"{x:.1f}%"))

    fig.update_traces(textposition='outside')
    fig.add_hline(
        y=100,
        line_dash="dash",
        line_color="red",
        annotation_text="Target: 100%",
        annotation_position="top right"
    )
    fig.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", yaxis_range=[0, 100], title_x=0.5,
                      legend_title_text="Indikator", legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5),
                      height=500)
    st.plotly_chart(fig, use_container_width=True)

    # 3. Tabel Rekapitulasi
    st.subheader(f"📋 Tabel Rekapitulasi Pemantauan Tumbuh Kembang Balita ({periode_label})")
    if puskesmas_filter == "All":
        recap_df = filtered_df.groupby('Puskesmas').sum().reset_index()
    else:
        recap_df = filtered_df.groupby(['Puskesmas', 'Kelurahan']).sum().reset_index()

    recap_df['Metrik Balita dengan perkembangan normal (%)'] = (recap_df['Jumlah_balita_dengan_perkembangan_normal'] / recap_df['Jumlah_balita_diskrining_perkembangan'] * 100).fillna(0).round(2)
    recap_df['Metrik Balita dengan perkembangan meragukan (%)'] = (recap_df['Jumlah_balita_dengan_perkembangan_meragukan'] / recap_df['Jumlah_balita_diskrining_perkembangan'] * 100).fillna(0).round(2)
    recap_df['Metrik Balita dengan kemungkinan penyimpangan (%)'] = (recap_df['Jumlah_balita_dengan_kemungkinan_penyimpangan'] / recap_df['Jumlah_balita_diskrining_perkembangan'] * 100).fillna(0).round(2)

    # Pastikan semua kunci di metrik_data ada di recap_df
    metrik_keys = list(metrik_data.keys())
    available_metrik_keys = [key for key in metrik_keys if key in recap_df.columns]

    recap_display = recap_df[['Puskesmas', 'Kelurahan'] + available_metrik_keys] if puskesmas_filter != "All" else recap_df[['Puskesmas'] + available_metrik_keys]
    recap_display.insert(0, 'No', range(1, len(recap_display) + 1))

    # Definisikan fungsi highlight untuk outlier > 100%
    def highlight_outliers(row):
        styles = [''] * len(row)
        targets = {
            'Metrik Balita dengan perkembangan normal (%)': 100,
            'Metrik Balita dengan perkembangan meragukan (%)': 100,
            'Metrik Balita dengan kemungkinan penyimpangan (%)': 100
        }
        for col in targets:
            if col in row.index and pd.notna(row[col]) and row[col] > targets[col]:
                idx = row.index.get_loc(col)
                styles[idx] = 'background-color: #FF6666; color: white;'
        return styles

    # Pastikan data numerik dan bulatkan ke 2 digit desimal
    cols_to_check = [
        'Metrik Balita dengan perkembangan normal (%)',
        'Metrik Balita dengan perkembangan meragukan (%)',
        'Metrik Balita dengan kemungkinan penyimpangan (%)'
    ]
    for col in cols_to_check:
        if col in recap_display.columns:
            recap_display[col] = pd.to_numeric(recap_display[col], errors='coerce').round(2)

    # Terapkan styling dan formatting
    styled_df = recap_display.style.apply(highlight_outliers, axis=1).format({
        'Metrik Balita dengan perkembangan normal (%)': "{:.2f}%",
        'Metrik Balita dengan perkembangan meragukan (%)': "{:.2f}%",
        'Metrik Balita dengan kemungkinan penyimpangan (%)': "{:.2f}%"
    }, na_rep="N/A", precision=2)

    # Render tabel dengan styling yang eksplisit
    st.write(styled_df, unsafe_allow_html=True)

    # Tambahkan notice di bawah tabel
    st.markdown(
        """
        <div style="background-color: #ADD8E6; padding: 10px; border-radius: 5px; color: black; font-size: 14px; font-family: Arial, sans-serif;">
            <strong>Catatan Penting:</strong> Nilai yang melebihi 100% (indikasi data outlier) telah dihighlight <span style="color: #FF6666; font-weight: bold;">Warna Merah</span>. Untuk analisis lebih lanjut dan koreksi data, mohon dilakukan pemeriksaan pada <strong>Menu Daftar Entry</strong>.
        </div>
        """,
        unsafe_allow_html=True
    )
        # 3.1 🚨 Tabel Deteksi Outlier (Logis)
    st.subheader("🚨 Tabel Deteksi Outlier")
    # Mapping metrik ke kolom numerator dan denominator
    metric_to_columns = {
        "Metrik Balita dengan perkembangan normal (%)": ("Jumlah_balita_dengan_perkembangan_normal", "Jumlah_balita_diskrining_perkembangan"),
        "Metrik Balita dengan perkembangan meragukan (%)": ("Jumlah_balita_dengan_perkembangan_meragukan", "Jumlah_balita_diskrining_perkembangan"),
        "Metrik Balita dengan kemungkinan penyimpangan (%)": ("Jumlah_balita_dengan_kemungkinan_penyimpangan", "Jumlah_balita_diskrining_perkembangan")
    }

    # Inisialisasi DataFrame untuk outlier logis
    outliers_df = pd.DataFrame(columns=["Puskesmas", "Kelurahan", "Metrik", "Numerator", "Denominator", "Rasio", "Alasan"])

    # Deteksi outlier logis untuk setiap metrik
    for metric, (numerator_col, denominator_col) in metric_to_columns.items():
        # Kasus 1: Numerator > Denominator
        outlier_data_num = filtered_df[
            (filtered_df[numerator_col] > filtered_df[denominator_col]) &
            (filtered_df[denominator_col] != 0)
        ][["Puskesmas", "Kelurahan", numerator_col, denominator_col]]
        if not outlier_data_num.empty:
            outlier_data_num["Metrik"] = metric
            outlier_data_num["Numerator"] = outlier_data_num[numerator_col]
            outlier_data_num["Denominator"] = outlier_data_num[denominator_col]
            outlier_data_num["Rasio"] = (outlier_data_num[numerator_col] / outlier_data_num[denominator_col] * 100).round(2)
            outlier_data_num["Alasan"] = "Numerator > Denominator"
            outliers_df = pd.concat(
                [outliers_df, outlier_data_num[["Puskesmas", "Kelurahan", "Metrik", "Numerator", "Denominator", "Rasio", "Alasan"]]],
                ignore_index=True
            )

        # Kasus 2: Denominator = 0
        outlier_data_zero = filtered_df[
            (filtered_df[denominator_col] == 0) &
            (filtered_df[numerator_col] > 0)
        ][["Puskesmas", "Kelurahan", numerator_col, denominator_col]]
        if not outlier_data_zero.empty:
            outlier_data_zero["Metrik"] = metric
            outlier_data_zero["Numerator"] = outlier_data_zero[numerator_col]
            outlier_data_zero["Denominator"] = outlier_data_zero[denominator_col]
            outlier_data_zero["Rasio"] = "Infinity"
            outlier_data_zero["Alasan"] = "Denominator = 0"
            outliers_df = pd.concat(
                [outliers_df, outlier_data_zero[["Puskesmas", "Kelurahan", "Metrik", "Numerator", "Denominator", "Rasio", "Alasan"]]],
                ignore_index=True
            )

    # Tampilkan Tabel Outlier Logis
    if not outliers_df.empty:
        styled_outliers = outliers_df.style.apply(
            lambda x: ['background-color: #FF6666; color: white;' if x['Alasan'] == "Numerator > Denominator" else 'background-color: #FF4500; color: white;'] * len(x),
            axis=1
        ).format({
            "Numerator": "{:.0f}",
            "Denominator": "{:.0f}",
            "Rasio": lambda x: f"{x:.2f}%" if isinstance(x, (int, float)) else x
        }).set_properties(**{
            'border': '1px solid black',
            'text-align': 'center',
            'font-size': '14px',
            'font-family': 'Arial, sans-serif'
        }).set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold')]},
            {'selector': 'caption', 'props': [('caption-side', 'top'), ('font-size', '18px'), ('font-weight', 'bold'), ('color', '#333')]},
        ]).set_caption("Tabel Outlier: Data dengan Numerator > Denominator atau Denominator = 0")

        st.write(styled_outliers, unsafe_allow_html=True)
    else:
        st.success("✅ Tidak ada outlier terdeteksi berdasarkan kriteria Numerator > Denominator atau Denominator = 0.")

    # 3.2 ⚙️ Analisis Outlier Statistik
    st.subheader("⚙️ Analisis Outlier Statistik")
    # Gunakan recap_df yang sudah dihitung persentasenya
    cols_to_check = list(metrik_data.keys())

    # Inisialisasi DataFrame untuk outlier statistik
    base_columns = ["Puskesmas", "Metrik", "Nilai", "Metode"]
    if puskesmas_filter != "All":
        base_columns.insert(1, "Kelurahan")
    statistical_outliers_df = pd.DataFrame(columns=base_columns)

    # Dropdown untuk memilih metode deteksi outlier statistik
    outlier_method = st.selectbox(
        "Pilih Metode Deteksi Outlier Statistik",
        ["Tidak Ada", "Z-Score", "IQR"],
        key=f"outlier_method_select_tumbuh_kembang_{periode_label}"
    )

    if outlier_method != "Tidak Ada":
        for metric in cols_to_check:
            if metric not in recap_df.columns:
                continue

            # Pilih kolom berdasarkan filter
            if puskesmas_filter == "All":
                metric_data = recap_df[[metric, "Puskesmas"]].dropna()
            else:
                metric_data = recap_df[[metric, "Puskesmas", "Kelurahan"]].dropna()

            if metric_data.empty:
                continue

            # Z-Score Method
            if outlier_method == "Z-Score":
                z_scores = stats.zscore(metric_data[metric], nan_policy='omit')
                z_outlier_mask = abs(z_scores) > 3  # Threshold Z-Score > 3
                z_outliers = metric_data[z_outlier_mask].copy()
                if not z_outliers.empty:
                    z_outliers["Metrik"] = metric
                    z_outliers["Nilai"] = z_outliers[metric]
                    z_outliers["Metode"] = "Z-Score"
                    if puskesmas_filter == "All":
                        z_outliers_subset = z_outliers[["Puskesmas", "Metrik", "Nilai", "Metode"]]
                    else:
                        z_outliers_subset = z_outliers[["Puskesmas", "Kelurahan", "Metrik", "Nilai", "Metode"]]
                    statistical_outliers_df = pd.concat(
                        [statistical_outliers_df, z_outliers_subset],
                        ignore_index=True
                    )

            # IQR Method
            elif outlier_method == "IQR":
                Q1 = metric_data[metric].quantile(0.25)
                Q3 = metric_data[metric].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                iqr_outlier_mask = (metric_data[metric] < lower_bound) | (metric_data[metric] > upper_bound)
                iqr_outliers = metric_data[iqr_outlier_mask].copy()
                if not iqr_outliers.empty:
                    iqr_outliers["Metrik"] = metric
                    iqr_outliers["Nilai"] = iqr_outliers[metric]
                    iqr_outliers["Metode"] = "IQR"
                    if puskesmas_filter == "All":
                        iqr_outliers_subset = iqr_outliers[["Puskesmas", "Metrik", "Nilai", "Metode"]]
                    else:
                        iqr_outliers_subset = iqr_outliers[["Puskesmas", "Kelurahan", "Metrik", "Nilai", "Metode"]]
                    statistical_outliers_df = pd.concat(
                        [statistical_outliers_df, iqr_outliers_subset],
                        ignore_index=True
                    )

    # 3.3 📊 Tabel Outlier Statistik
    if not statistical_outliers_df.empty:
        st.markdown("### 📊 Tabel Outlier Statistik")
        styled_stat_outliers = statistical_outliers_df.style.apply(
            lambda x: ['background-color: #FFA500; color: white;' if x['Metode'] == "Z-Score" else 'background-color: #FF8C00; color: white;'] * len(x),
            axis=1
        ).format({
            "Nilai": "{:.2f}%"
        }).set_properties(**{
            'border': '1px solid black',
            'text-align': 'center',
            'font-size': '14px',
            'font-family': 'Arial, sans-serif'
        }).set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#FF9800'), ('color', 'white'), ('font-weight', 'bold')]},
            {'selector': 'caption', 'props': [('caption-side', 'top'), ('font-size', '18px'), ('font-weight', 'bold'), ('color', '#333')]},
        ]).set_caption(f"Tabel Outlier Statistik ({outlier_method})")

        st.write(styled_stat_outliers, unsafe_allow_html=True)
    else:
        if outlier_method != "Tidak Ada":
            st.info(f"ℹ️ Tidak ada outlier statistik terdeteksi menggunakan metode {outlier_method}.")

    # 3.4 📊 Visualisasi Outlier
    st.subheader("📊 Visualisasi Outlier")
    show_outlier_viz = st.checkbox(
        "Tampilkan Visualisasi Outlier",
        value=False,
        key=f"tumbuh_kembang_viz_toggle_{periode_label}"
    )

    if show_outlier_viz:
        # Gabungkan outlier logis dan statistik
        combined_outliers = outliers_df[["Puskesmas", "Kelurahan", "Metrik", "Rasio"]].copy()
        combined_outliers["Metode"] = "Logis (Numerator > Denominator atau Denominator = 0)"
        # Ganti "Infinity" dengan nilai besar untuk visualisasi
        combined_outliers["Rasio"] = combined_outliers["Rasio"].replace("Infinity", 9999)
        if not statistical_outliers_df.empty:
            stat_outliers = statistical_outliers_df[["Puskesmas", "Metrik", "Metode"]].copy()
            stat_outliers["Rasio"] = statistical_outliers_df["Nilai"]
            if "Kelurahan" in statistical_outliers_df.columns:
                stat_outliers["Kelurahan"] = statistical_outliers_df["Kelurahan"]
            else:
                stat_outliers["Kelurahan"] = "N/A"
            combined_outliers = pd.concat([combined_outliers, stat_outliers], ignore_index=True)

        if not combined_outliers.empty:
            viz_type = st.selectbox(
                "Pilih Tipe Visualisasi Outlier",
                ["Heatmap", "Grafik Batang", "Boxplot"],
                key=f"outlier_viz_select_tumbuh_kembang_{periode_label}"
            )

            if viz_type == "Heatmap":
                pivot_df = combined_outliers.pivot_table(
                    index="Puskesmas",
                    columns="Metrik",
                    values="Rasio",
                    aggfunc="mean",
                    fill_value=0
                )
                fig_heatmap = px.imshow(
                    pivot_df,
                    text_auto=True,
                    aspect="auto",
                    title="Heatmap Distribusi Outlier per Puskesmas",
                    color_continuous_scale="Reds"
                )
                fig_heatmap.update_layout(
                    xaxis_title="Metrik",
                    yaxis_title="Puskesmas",
                    coloraxis_colorbar_title="Rasio (%)"
                )
                st.plotly_chart(fig_heatmap, use_container_width=True)

            elif viz_type == "Grafik Batang":
                count_df = combined_outliers.groupby(["Metrik", "Metode"]).size().reset_index(name="Jumlah")
                fig_bar = px.bar(
                    count_df,
                    x="Metrik",
                    y="Jumlah",
                    color="Metode",
                    barmode="group",
                    title="Jumlah Outlier per Metrik dan Metode Deteksi",
                    text="Jumlah"
                )
                fig_bar.update_traces(textposition="outside")
                fig_bar.update_layout(
                    xaxis_title="Metrik",
                    yaxis_title="Jumlah Outlier",
                    xaxis_tickangle=45,
                    legend_title="Metode Deteksi"
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            elif viz_type == "Boxplot":
                fig_box = px.box(
                    combined_outliers,
                    x="Metrik",
                    y="Rasio",
                    color="Metode",
                    title="Boxplot Distribusi Outlier per Metrik dan Metode Deteksi",
                    points="all"
                )
                fig_box.update_layout(
                    xaxis_title="Metrik",
                    yaxis_title="Rasio (%)",
                    xaxis_tickangle=45,
                    legend_title="Metode Deteksi"
                )
                st.plotly_chart(fig_box, use_container_width=True)
        else:
            st.info("ℹ️ Tidak ada data outlier untuk divisualisasikan.")
    # 3.5 📈 Analisis Tren Metrik Tumbuh Kembang Balita
    st.subheader("📈 Tren Metrik Tumbuh Kembang Balita")

    # Daftar metrik yang akan dianalisis trennya
    metric_list = [
        "Metrik Balita dengan perkembangan normal (%)",
        "Metrik Balita dengan perkembangan meragukan (%)",
        "Metrik Balita dengan kemungkinan penyimpangan (%)"
    ]

    # Mapping kolom numerator dan denominator untuk setiap metrik
    metric_to_columns = {
        "Metrik Balita dengan perkembangan normal (%)": ("Jumlah_balita_dengan_perkembangan_normal", "Jumlah_balita_diskrining_perkembangan"),
        "Metrik Balita dengan perkembangan meragukan (%)": ("Jumlah_balita_dengan_perkembangan_meragukan", "Jumlah_balita_diskrining_perkembangan"),
        "Metrik Balita dengan kemungkinan penyimpangan (%)": ("Jumlah_balita_dengan_kemungkinan_penyimpangan", "Jumlah_balita_diskrining_perkembangan")
    }

    # Salin filtered_df agar tidak mengubah aslinya
    trend_data = filtered_df.copy()

    # Hitung metrik persentase untuk setiap baris di trend_data
    for metric, (numerator_col, denominator_col) in metric_to_columns.items():
        trend_data[metric] = (trend_data[numerator_col] / trend_data[denominator_col] * 100).round(2)
        # Ganti NaN atau inf dengan 0 untuk kebersihan data
        trend_data[metric] = trend_data[metric].replace([float('inf'), float('-inf')], 0).fillna(0)

    # Filter dan agregasi data berdasarkan Bulan
    trend_df = trend_data.groupby("Bulan")[metric_list].mean().reset_index()
    trend_df = trend_df.melt(
        id_vars="Bulan",
        value_vars=metric_list,
        var_name="Metrik",
        value_name="Persentase"
    )

    # Bulatkan kolom Persentase menjadi 2 digit desimal
    trend_df["Persentase"] = trend_df["Persentase"].round(2)

    # Tampilkan line chart untuk semua metrik
    if not trend_df.empty:
        fig_trend = px.line(
            trend_df,
            x="Bulan",
            y="Persentase",
            color="Metrik",
            markers=True,
            text=trend_df["Persentase"].apply(lambda x: f"{x:.2f}"),  # Format teks menjadi 2 digit desimal
            title="📈 Tren Metrik Tumbuh Kembang Balita dari Awal hingga Akhir Bulan"
        )
        fig_trend.update_traces(textposition="top center")
        fig_trend.update_layout(
            xaxis_title="Bulan",
            yaxis_title="Persentase (%)",
            xaxis=dict(tickmode='linear', tick0=1, dtick=1),
            yaxis_range=[0, 100],
            legend_title="Metrik",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(
            fig_trend,
            key=f"tumbuh_kembang_balita_trend_chart_{puskesmas_filter}_{kelurahan_filter}_{time.time()}",
            use_container_width=True
        )
    else:
        st.warning("⚠️ Tidak ada data untuk ditampilkan pada grafik tren Tumbuh Kembang Balita.")
        
    # 4. 📊 Analisis Komparasi Antar Wilayah
    st.subheader("📊 Analisis Komparasi Antar Wilayah")
    selected_metric = st.selectbox(
        "Pilih Metrik untuk Komparasi Antar Wilayah",
        [
            "Metrik Balita dengan perkembangan normal (%)",
            "Metrik Balita dengan perkembangan meragukan (%)",
            "Metrik Balita dengan kemungkinan penyimpangan (%)"
        ],
        key="comp_metric_select_tumbuh_kembang"
    )

    # Gunakan filtered_df untuk konsistensi dengan pendekatan balita kecil
    group_cols = ["Puskesmas"]
    if 'Kelurahan' in filtered_df.columns:
        group_cols.append("Kelurahan")

    # Menghitung rata-rata metrik berdasarkan kelompok
    comp_df = filtered_df.groupby(group_cols)[selected_metric].mean().reset_index()

    if not comp_df.empty:
        if "Kelurahan" in comp_df.columns:
            # Filter kelurahan teratas (top 5 berdasarkan jumlah data)
            top_kelurahan = comp_df['Kelurahan'].value_counts().index[:5].tolist()
            comp_df_filtered = comp_df[comp_df['Kelurahan'].isin(top_kelurahan)]

            # Membuat bar chart dengan Plotly Express
            fig_comp = px.bar(
                comp_df_filtered,
                x="Puskesmas",
                y=selected_metric,
                color="Kelurahan",
                title=f"📊 Komparasi {selected_metric} Antar Wilayah",
                text=comp_df_filtered[selected_metric].apply(lambda x: f"{x:.2f}%"),
                barmode="group",  # Mode group untuk memisahkan kelurahan
                height=500,  # Sesuaikan tinggi untuk keseimbangan
                width=900    # Lebar sedikit lebih besar untuk kejelasan
            )

            # Memperbaiki tata letak dan legenda
            fig_comp.update_traces(textposition="outside")
            fig_comp.update_layout(
                xaxis_title="Puskesmas",
                yaxis_title="Persentase (%)",
                xaxis_tickangle=45,
                yaxis_range=[0, 100],
                legend_title="Kelurahan",
                legend=dict(
                    orientation="h",  # Legenda horizontal
                    yanchor="bottom",
                    y=-0.2,  # Posisi di bawah grafik
                    xanchor="center",
                    x=0.5
                ),
                uniformtext_minsize=8,  # Ukuran teks minimum
                uniformtext_mode='hide',  # Sembunyikan teks jika terlalu kecil
                bargap=0.15,  # Jarak antar grup bar
                bargroupgap=0.1  # Jarak antar bar dalam grup
            )
        else:
            fig_comp = px.bar(
                comp_df,
                x="Puskesmas",
                y=selected_metric,
                title=f"📊 Komparasi {selected_metric} Antar Wilayah (Tanpa Kelurahan)",
                text=comp_df[selected_metric].apply(lambda x: f"{x:.2f}%"),
                height=500,
                width=900
            )
            fig_comp.update_traces(textposition="outside")
            fig_comp.update_layout(
                xaxis_title="Puskesmas",
                yaxis_title="Persentase (%)",
                xaxis_tickangle=45,
                yaxis_range=[0, 100]
            )
            st.warning("⚠️ Data 'Kelurahan' tidak tersedia di filtered_df.")

        # Menampilkan grafik
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.warning("⚠️ Tidak ada data untuk komparasi antar wilayah.")

    # 5. 🔍 Analisis Korelasi Antar Metrik
    st.subheader("🔍 Analisis Korelasi Antar Metrik")
    corr_df = recap_df.groupby(group_cols)[metric_list].mean().reset_index()
    if len(corr_df) > 1:
        correlation_matrix = corr_df[metric_list].corr()
        fig_corr = px.imshow(
            correlation_matrix,
            text_auto=True,
            aspect="auto",
            title="🔍 Matriks Korelasi Antar Metrik Tumbuh Kembang Balita",
            color_continuous_scale="RdBu",
            range_color=[-1, 1]
        )
        fig_corr.update_layout(
            xaxis_title="Metrik",
            yaxis_title="Metrik",
            coloraxis_colorbar_title="Koefisien Korelasi"
        )
        st.plotly_chart(fig_corr, use_container_width=True)
        st.markdown("**Catatan:** Nilai mendekati 1 atau -1 menunjukkan korelasi kuat (positif atau negatif), sementara 0 menunjukkan tidak ada korelasi.")
    else:
        st.warning("⚠️ Tidak cukup data untuk menghitung korelasi antar metrik.")

    # 6. 📅 Analisis Perubahan Persentase (Growth/Decline)
    st.subheader("📅 Analisis Perubahan Persentase (Growth/Decline)")
    if 'Bulan' in filtered_df.columns:
        trend_melted = trend_df.copy()
        trend_melted["Perubahan Persentase"] = trend_melted.groupby("Metrik")["Persentase"].pct_change() * 100
        trend_melted["Perubahan Persentase"] = trend_melted["Perubahan Persentase"].round(2)

        if not trend_melted.empty:
            # Tampilkan tabel perubahan
            st.dataframe(
                trend_melted[["Bulan", "Metrik", "Persentase", "Perubahan Persentase"]].style.format({
                    "Persentase": "{:.2f}%",
                    "Perubahan Persentase": "{:.2f}%"
                }).set_properties(**{
                    'text-align': 'center',
                    'font-size': '14px',
                    'border': '1px solid black'
                }).set_table_styles([
                    {'selector': 'th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold')]},
                    {'selector': 'caption', 'props': [('caption-side', 'top'), ('font-size', '18px'), ('font-weight', 'bold'), ('color', '#333')]},
                ]).set_caption("📅 Tabel Perubahan Persentase Antar Bulan"),
                use_container_width=True
            )

            # Visualisasi perubahan dengan grafik garis
            fig_change = px.line(
                trend_melted,
                x="Bulan",
                y="Perubahan Persentase",
                color="Metrik",
                markers=True,
                text=trend_melted["Perubahan Persentase"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else ""),
                title="📅 Tren Perubahan Persentase Metrik Tumbuh Kembang Balita"
            )
            fig_change.update_traces(textposition="top center")
            fig_change.update_layout(
                xaxis_title="Bulan",
                yaxis_title="Perubahan Persentase (%)",
                xaxis=dict(tickmode='linear', tick0=1, dtick=1),
                legend_title="Metrik",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_change, use_container_width=True)
        else:
            st.warning("⚠️ Tidak ada data untuk menganalisis perubahan persentase.")
    else:
        st.warning("⚠️ Kolom 'Bulan' tidak tersedia di data. Analisis perubahan persentase tidak dapat dilakukan.")

    # 7. 📉 Analisis Distribusi Data (Histogram)
    st.subheader("📉 Analisis Distribusi Data (Histogram)")
    selected_metric_dist = st.selectbox(
        "Pilih Metrik untuk Analisis Distribusi",
        metric_list,
        key="dist_metric_select_tumbuh_kembang"
    )

    dist_df = recap_df.groupby(group_cols)[selected_metric_dist].mean().reset_index()
    if not dist_df.empty:
        fig_dist = px.histogram(
            dist_df,
            x=selected_metric_dist,
            nbins=20,
            title=f"📉 Distribusi {selected_metric_dist} di Seluruh Wilayah",
            labels={"value": "Persentase (%)", "count": "Jumlah Wilayah"},
            height=400
        )
        fig_dist.update_layout(
            xaxis_title="Persentase (%)",
            yaxis_title="Jumlah Wilayah",
            bargap=0.1
        )
        st.plotly_chart(fig_dist, use_container_width=True)
        # Tambahan statistik dasar
        mean_val = dist_df[selected_metric_dist].mean().round(2)
        median_val = dist_df[selected_metric_dist].median().round(2)
        st.markdown(f"**Statistik Distribusi:** Rata-rata = {mean_val}%, Median = {median_val}%")
    else:
        st.warning("⚠️ Tidak ada data untuk analisis distribusi.")

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
        elements.append(Paragraph(f"Laporan Pemantauan Tumbuh Kembang Balita ({periode_label})", title_style))
        elements.append(Paragraph(f"Diperbarui: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
        elements.append(Spacer(1, 12))

        # Tambahkan Metrik
        elements.append(Paragraph("1. Metrik Pemantauan", normal_style))
        metric_data = [[f"{label}: {value:.2f}%" for label, value in metrik_list]]
        metric_table = Table(metric_data, colWidths=[300])
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
        elements.append(Paragraph("2. Grafik Pemantauan Tumbuh Kembang Balita", normal_style))
        elements.append(Image(img_buffer, width=500, height=300))
        elements.append(Spacer(1, 12))

        # Tambahkan Tabel Rekapitulasi
        elements.append(Paragraph("3. Tabel Rekapitulasi", normal_style))
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

    if st.button("Download Laporan PDF", key=f"download_pemantauan_tumbuh_kembang_{periode_label}"):
        st.warning("Membuat laporan PDF, harap tunggu...")
        pdf_data = generate_pdf_report()
        st.success("Laporan PDF siap diunduh!")
        st.download_button(
            label="Download Laporan PDF",
            data=pdf_data,
            file_name=f"Laporan_Pemantauan_Tumbuh_Kembang_Balita_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )
# ----------------------------- #
# 📉 Pemantauan Tumbuh Kembang Apras (Anak Pra-Sekolah)
# ----------------------------- #
def pemantauan_tumbuh_kembang_apras(filtered_df, desa_df, puskesmas_filter, kelurahan_filter, jenis_laporan, tahun_filter, bulan_filter_int=None, tribulan_filter=None):
    """Menampilkan analisis Pemantauan Tumbuh Kembang Anak Pra-Sekolah (Apras) dengan fitur download laporan."""
    st.header("📉 Pemantauan Tumbuh Kembang Apras (Anak Pra-Sekolah)")
    # Informasi Metrik Pemantauan Tumbuh Kembang Apras
    with st.expander("📜 Definisi dan Insight Analisis Pemantauan Tumbuh Kembang Apras", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Analisis Indikator

            Berikut adalah definisi operasional, rumus perhitungan, serta analisis insight dari indikator-indikator yang digunakan untuk memantau tumbuh kembang anak prasekolah (Apras) dalam kerangka Surveilans Deteksi Dini Tumbuh Kembang (SDIDTK) versi terbaru, diperbarui hingga Mei 2025. Rumus disajikan dalam format matematis untuk kejelasan, dengan penjelasan sederhana untuk mendukung pemahaman petugas kesehatan.

            #### 1. Persentase Anak Prasekolah Ditimbang
            - **Definisi Operasional:** Persentase anak prasekolah yang ditimbang berat badannya terhadap total anak prasekolah pada bulan pelaporan di wilayah kerja puskesmas, sesuai pedoman SDIDTK untuk pemantauan pertumbuhan fisik.  
            - **Rumus Perhitungan:**  
            $$ \\text{Metrik Anak prasekolah ditimbang (\\%)} = \\frac{\\text{Jumlah anak prasekolah ditimbang}}{\\text{Total anak prasekolah bulan ini}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen anak prasekolah yang ditimbang dari total anak prasekolah pada bulan tersebut, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan bulanan melalui laporan posyandu atau puskesmas, dengan pencatatan jumlah anak yang ditimbang menggunakan timbangan standar SDIDTK.  
            - **Insight Analisis:** Persentase di bawah 80% (target SDIDTK 2025) dapat mengindikasikan rendahnya cakupan pemantauan atau keterbatasan akses. Peningkatan pelatihan kader dan penyediaan alat timbangan dapat meningkatkan cakupan, mendukung deteksi dini gangguan pertumbuhan.

            #### 2. Persentase Anak Prasekolah Memiliki Buku KIA
            - **Definisi Operasional:** Persentase anak prasekolah yang memiliki Buku Kesehatan Ibu dan Anak (KIA) untuk dokumentasi tumbuh kembang terhadap total anak prasekolah pada bulan pelaporan, sesuai pedoman SDIDTK.  
            - **Rumus Perhitungan:**  
            $$ \\text{Metrik Anak prasekolah punya buku KIA (\\%)} = \\frac{\\text{Jumlah anak prasekolah punya Buku KIA}}{\\text{Total anak prasekolah bulan ini}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen anak prasekolah yang memiliki Buku KIA dari total anak prasekolah pada bulan tersebut, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data diambil dari laporan bulanan posyandu, dengan pencatatan jumlah anak yang membawa atau didokumentasikan memiliki Buku KIA.  
            - **Insight Analisis:** Persentase di bawah 90% (target SDIDTK 2025) dapat menunjukkan kurangnya distribusi Buku KIA. Peningkatan sosialisasi dan penyediaan gratis dapat meningkatkan kepemilikan, mendukung rekam medis yang konsisten.

            #### 3. Persentase Anak Prasekolah dengan Perkembangan Normal
            - **Definisi Operasional:** Persentase anak prasekolah yang menunjukkan perkembangan normal berdasarkan skrining SDIDTK terhadap total anak yang diskrining pada bulan pelaporan di wilayah kerja puskesmas.  
            - **Rumus Perhitungan:**  
            $$ \\text{Metrik Anak prasekolah dengan perkembangan normal (\\%)} = \\frac{\\text{Jumlah anak prasekolah dengan perkembangan normal}}{\\text{Total anak prasekolah diskrining}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen anak dengan perkembangan normal dari total anak yang diskrining, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui laporan bulanan posyandu, dengan skrining menggunakan alat KPSP (Kuesioner Pra Skrining Perkembangan) versi terbaru SDIDTK 2025.  
            - **Insight Analisis:** Persentase di bawah 85% dapat mengindikasikan adanya masalah perkembangan yang perlu ditindaklanjuti. Peningkatan pelatihan kader untuk penggunaan KPSP dan rujukan dini dapat meningkatkan intervensi.

            #### 4. Persentase Anak Prasekolah dengan Perkembangan Meragukan
            - **Definisi Operasional:** Persentase anak prasekolah yang menunjukkan perkembangan meragukan berdasarkan skrining SDIDTK terhadap total anak yang diskrining pada bulan pelaporan.  
            - **Rumus Perhitungan:**  
            $$ \\text{Metrik Anak prasekolah dengan perkembangan meragukan (\\%)} = \\frac{\\text{Jumlah anak prasekolah dengan perkembangan meragukan}}{\\text{Total anak prasekolah diskrining}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen anak dengan perkembangan meragukan dari total anak yang diskrining, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data diambil dari laporan bulanan posyandu, dengan klasifikasi berdasarkan hasil KPSP SDIDTK 2025.  
            - **Insight Analisis:** Persentase di atas 10% (batas SDIDTK 2025) dapat menunjukkan kebutuhan intervensi tambahan. Peningkatan skrining ulang dan edukasi orang tua dapat mengurangi angka ini.

            #### 5. Persentase Anak Prasekolah dengan Kemungkinan Penyimpangan
            - **Definisi Operasional:** Persentase anak prasekolah yang menunjukkan kemungkinan penyimpangan perkembangan berdasarkan skrining SDIDTK terhadap total anak yang diskrining pada bulan pelaporan.  
            - **Rumus Perhitungan:**  
            $$ \\text{Metrik Anak prasekolah dengan kemungkinan penyimpangan (\\%)} = \\frac{\\text{Jumlah anak prasekolah dengan kemungkinan penyimpangan}}{\\text{Total anak prasekolah diskrining}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen anak dengan kemungkinan penyimpangan dari total anak yang diskrining, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui laporan bulanan posyandu, dengan hasil skrining KPSP SDIDTK 2025 yang divalidasi oleh tenaga kesehatan.  
            - **Insight Analisis:** Persentase di atas 5% (batas SDIDTK 2025) menunjukkan kebutuhan rujukan segera. Koordinasi dengan puskesmas untuk rujukan dan intervensi terapeutik dapat menurunkan angka ini, mencegah dampak perkembangan jangka panjang.

            </div>
        """, unsafe_allow_html=True)

    # Daftar kolom yang dibutuhkan
    required_columns = [
        'Jumlah_anak_prasekolah_bulan_ini',
        'Jumlah_anak_prasekolah_ditimbang',
        'Jumlah_anak_prasekolah_punya_Buku_KIA',
        'Jumlah_anak_prasekolah_diskrining_perkembangan',
        'Jumlah_anak_prasekolah_dengan_perkembangan_normal',
        'Jumlah_anak_prasekolah_dengan_perkembangan_meragukan',
        'Jumlah_anak_prasekolah_dengan_kemungkinan_penyimpangan'
    ]

    # Cek apakah semua kolom ada
    missing_cols = [col for col in required_columns if col not in filtered_df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di dataset: {missing_cols}. Periksa data di 'data_balita_kia'!")
        return

    # Inisialisasi periode untuk label
    periode_label = ""
    if tahun_filter != "All":
        periode_label += f"Tahun {tahun_filter}"
    if jenis_laporan == "Bulanan" and bulan_filter_int is not None:
        periode_label += f" Bulan {bulan_filter_int}" if periode_label else f"Bulan {bulan_filter_int}"
    elif jenis_laporan == "Tahunan" and tribulan_filter:
        periode_label += f" {tribulan_filter}" if periode_label else tribulan_filter

    # Agregasi data berdasarkan jenis laporan
    if jenis_laporan == "Tahunan" and not filtered_df.empty:
        group_columns = ["Puskesmas", "Kelurahan"]
        numeric_columns = [col for col in filtered_df.columns if filtered_df[col].dtype in ['int64', 'float64']]
        if numeric_columns:
            agg_dict = {col: "sum" for col in numeric_columns}
            filtered_df = filtered_df.groupby(group_columns).agg(agg_dict).reset_index()

    # Hitung total anak prasekolah bulan ini dan total diskrining
    total_apras = filtered_df['Jumlah_anak_prasekolah_bulan_ini'].sum()
    total_diskrining = filtered_df['Jumlah_anak_prasekolah_diskrining_perkembangan'].sum()

    if total_apras == 0:
        st.warning("⚠️ Tidak ada data anak prasekolah bulan ini untuk filter ini.")
        return
    if total_diskrining == 0:
        st.warning("⚠️ Tidak ada data anak prasekolah yang diskrining untuk filter ini.")
        return

    # Hitung metrik
    metrik_data = {
        "Metrik Anak prasekolah ditimbang (%)": (filtered_df['Jumlah_anak_prasekolah_ditimbang'].sum() / total_apras * 100),
        "Metrik Anak prasekolah punya buku KIA (%)": (filtered_df['Jumlah_anak_prasekolah_punya_Buku_KIA'].sum() / total_apras * 100),
        "Metrik Anak prasekolah dengan perkembangan normal (%)": (filtered_df['Jumlah_anak_prasekolah_dengan_perkembangan_normal'].sum() / total_diskrining * 100),
        "Metrik Anak prasekolah dengan perkembangan meragukan (%)": (filtered_df['Jumlah_anak_prasekolah_dengan_perkembangan_meragukan'].sum() / total_diskrining * 100),
        "Metrik Anak prasekolah dengan kemungkinan penyimpangan (%)": (filtered_df['Jumlah_anak_prasekolah_dengan_kemungkinan_penyimpangan'].sum() / total_diskrining * 100)
    }

    # 1. Metrik Score Card
    st.subheader(f"📊 Metrik Pemantauan Tumbuh Kembang Apras ({periode_label})")
    metrik_list = list(metrik_data.items())
    cols = st.columns(3)
    for i in range(3):
        label, value = metrik_list[i]
        cols[i].metric(label=label, value=f"{value:.2f}%")
    
    cols = st.columns(2)
    for i in range(2):
        label, value = metrik_list[i + 3]
        cols[i].metric(label=label, value=f"{value:.2f}%")

    # 2. Grafik Visualisasi (Dibagi menjadi 2 grafik)
    # Grafik 1: Cakupan Layanan Apras
    st.subheader(f"📈 Grafik Cakupan Layanan Apras ({periode_label})")
    if puskesmas_filter == "All":
        grouped_df = filtered_df.groupby('Puskesmas').sum().reset_index()
        graph_data_cakupan = pd.DataFrame({
            "Puskesmas": grouped_df['Puskesmas'],
            "Metrik Anak prasekolah ditimbang (%)": (grouped_df['Jumlah_anak_prasekolah_ditimbang'] / grouped_df['Jumlah_anak_prasekolah_bulan_ini'] * 100).fillna(0),
            "Metrik Anak prasekolah punya buku KIA (%)": (grouped_df['Jumlah_anak_prasekolah_punya_Buku_KIA'] / grouped_df['Jumlah_anak_prasekolah_bulan_ini'] * 100).fillna(0)
        }).melt(id_vars=["Puskesmas"], var_name="Indikator", value_name="Persentase")
        fig1 = px.bar(graph_data_cakupan, x="Puskesmas", y="Persentase", color="Indikator", barmode="group",
                      title=f"Cakupan Layanan Apras per Puskesmas ({periode_label})", text=graph_data_cakupan["Persentase"].apply(lambda x: f"{x:.1f}%"))
    else:
        grouped_df = filtered_df.groupby('Kelurahan').sum().reset_index()
        graph_data_cakupan = pd.DataFrame({
            "Kelurahan": grouped_df['Kelurahan'],
            "Metrik Anak prasekolah ditimbang (%)": (grouped_df['Jumlah_anak_prasekolah_ditimbang'] / grouped_df['Jumlah_anak_prasekolah_bulan_ini'] * 100).fillna(0),
            "Metrik Anak prasekolah punya buku KIA (%)": (grouped_df['Jumlah_anak_prasekolah_punya_Buku_KIA'] / grouped_df['Jumlah_anak_prasekolah_bulan_ini'] * 100).fillna(0)
        }).melt(id_vars=["Kelurahan"], var_name="Indikator", value_name="Persentase")
        fig1 = px.bar(graph_data_cakupan, x="Kelurahan", y="Persentase", color="Indikator", barmode="group",
                      title=f"Cakupan Layanan Apras per Kelurahan di {puskesmas_filter} ({periode_label})", text=graph_data_cakupan["Persentase"].apply(lambda x: f"{x:.1f}%"))

    fig1.update_traces(textposition='outside')
    fig1.add_hline(
        y=100,
        line_dash="dash",
        line_color="red",
        annotation_text="Target: 100%",
        annotation_position="top right"
    )
    fig1.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", yaxis_range=[0, 100], title_x=0.5,
                       legend_title_text="Indikator", legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5),
                       height=500)
    st.plotly_chart(fig1, use_container_width=True)

    # Grafik 2: Pemantauan Tumbuh Kembang Apras
    st.subheader(f"📈 Grafik Pemantauan Tumbuh Kembang Apras ({periode_label})")
    if puskesmas_filter == "All":
        grouped_df = filtered_df.groupby('Puskesmas').sum().reset_index()
        graph_data_pemantauan = pd.DataFrame({
            "Puskesmas": grouped_df['Puskesmas'],
            "Metrik Anak prasekolah dengan perkembangan normal (%)": (grouped_df['Jumlah_anak_prasekolah_dengan_perkembangan_normal'] / grouped_df['Jumlah_anak_prasekolah_diskrining_perkembangan'] * 100).fillna(0),
            "Metrik Anak prasekolah dengan perkembangan meragukan (%)": (grouped_df['Jumlah_anak_prasekolah_dengan_perkembangan_meragukan'] / grouped_df['Jumlah_anak_prasekolah_diskrining_perkembangan'] * 100).fillna(0),
            "Metrik Anak prasekolah dengan kemungkinan penyimpangan (%)": (grouped_df['Jumlah_anak_prasekolah_dengan_kemungkinan_penyimpangan'] / grouped_df['Jumlah_anak_prasekolah_diskrining_perkembangan'] * 100).fillna(0)
        }).melt(id_vars=["Puskesmas"], var_name="Indikator", value_name="Persentase")
        fig2 = px.bar(graph_data_pemantauan, x="Puskesmas", y="Persentase", color="Indikator", barmode="group",
                      title=f"Pemantauan Tumbuh Kembang Apras per Puskesmas ({periode_label})", text=graph_data_pemantauan["Persentase"].apply(lambda x: f"{x:.1f}%"))
    else:
        grouped_df = filtered_df.groupby('Kelurahan').sum().reset_index()
        graph_data_pemantauan = pd.DataFrame({
            "Kelurahan": grouped_df['Kelurahan'],
            "Metrik Anak prasekolah dengan perkembangan normal (%)": (grouped_df['Jumlah_anak_prasekolah_dengan_perkembangan_normal'] / grouped_df['Jumlah_anak_prasekolah_diskrining_perkembangan'] * 100).fillna(0),
            "Metrik Anak prasekolah dengan perkembangan meragukan (%)": (grouped_df['Jumlah_anak_prasekolah_dengan_perkembangan_meragukan'] / grouped_df['Jumlah_anak_prasekolah_diskrining_perkembangan'] * 100).fillna(0),
            "Metrik Anak prasekolah dengan kemungkinan penyimpangan (%)": (grouped_df['Jumlah_anak_prasekolah_dengan_kemungkinan_penyimpangan'] / grouped_df['Jumlah_anak_prasekolah_diskrining_perkembangan'] * 100).fillna(0)
        }).melt(id_vars=["Kelurahan"], var_name="Indikator", value_name="Persentase")
        fig2 = px.bar(graph_data_pemantauan, x="Kelurahan", y="Persentase", color="Indikator", barmode="group",
                      title=f"Pemantauan Tumbuh Kembang Apras per Kelurahan di {puskesmas_filter} ({periode_label})", text=graph_data_pemantauan["Persentase"].apply(lambda x: f"{x:.1f}%"))

    fig2.update_traces(textposition='outside')
    fig2.add_hline(
        y=100,
        line_dash="dash",
        line_color="red",
        annotation_text="Target: 100%",
        annotation_position="top right"
    )
    fig2.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", yaxis_range=[0, 100], title_x=0.5,
                       legend_title_text="Indikator", legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5),
                       height=500)
    st.plotly_chart(fig2, use_container_width=True)

    # 3. Tabel Rekapitulasi
    st.subheader(f"📋 Tabel Rekapitulasi Pemantauan Tumbuh Kembang Apras ({periode_label})")
    if puskesmas_filter == "All":
        recap_df = filtered_df.groupby('Puskesmas').sum().reset_index()
    else:
        recap_df = filtered_df.groupby(['Puskesmas', 'Kelurahan']).sum().reset_index()

    recap_df['Metrik Anak prasekolah ditimbang (%)'] = (recap_df['Jumlah_anak_prasekolah_ditimbang'] / recap_df['Jumlah_anak_prasekolah_bulan_ini'] * 100).fillna(0).round(2)
    recap_df['Metrik Anak prasekolah punya buku KIA (%)'] = (recap_df['Jumlah_anak_prasekolah_punya_Buku_KIA'] / recap_df['Jumlah_anak_prasekolah_bulan_ini'] * 100).fillna(0).round(2)
    recap_df['Metrik Anak prasekolah dengan perkembangan normal (%)'] = (recap_df['Jumlah_anak_prasekolah_dengan_perkembangan_normal'] / recap_df['Jumlah_anak_prasekolah_diskrining_perkembangan'] * 100).fillna(0).round(2)
    recap_df['Metrik Anak prasekolah dengan perkembangan meragukan (%)'] = (recap_df['Jumlah_anak_prasekolah_dengan_perkembangan_meragukan'] / recap_df['Jumlah_anak_prasekolah_diskrining_perkembangan'] * 100).fillna(0).round(2)
    recap_df['Metrik Anak prasekolah dengan kemungkinan penyimpangan (%)'] = (recap_df['Jumlah_anak_prasekolah_dengan_kemungkinan_penyimpangan'] / recap_df['Jumlah_anak_prasekolah_diskrining_perkembangan'] * 100).fillna(0).round(2)

    # Pastikan semua kunci di metrik_data ada di recap_df
    metrik_keys = list(metrik_data.keys())
    available_metrik_keys = [key for key in metrik_keys if key in recap_df.columns]

    recap_display = recap_df[['Puskesmas', 'Kelurahan'] + available_metrik_keys] if puskesmas_filter != "All" else recap_df[['Puskesmas'] + available_metrik_keys]
    recap_display.insert(0, 'No', range(1, len(recap_display) + 1))

    # Definisikan fungsi highlight untuk outlier > 100%
    def highlight_outliers(row):
        styles = [''] * len(row)
        targets = {
            'Metrik Anak prasekolah ditimbang (%)': 100,
            'Metrik Anak prasekolah punya buku KIA (%)': 100,
            'Metrik Anak prasekolah dengan perkembangan normal (%)': 100,
            'Metrik Anak prasekolah dengan perkembangan meragukan (%)': 100,
            'Metrik Anak prasekolah dengan kemungkinan penyimpangan (%)': 100
        }
        for col in targets:
            if col in row.index and pd.notna(row[col]) and row[col] > targets[col]:
                idx = row.index.get_loc(col)
                styles[idx] = 'background-color: #FF6666; color: white;'
        return styles

    # Pastikan data numerik dan bulatkan ke 2 digit desimal
    cols_to_check = [
        'Metrik Anak prasekolah ditimbang (%)',
        'Metrik Anak prasekolah punya buku KIA (%)',
        'Metrik Anak prasekolah dengan perkembangan normal (%)',
        'Metrik Anak prasekolah dengan perkembangan meragukan (%)',
        'Metrik Anak prasekolah dengan kemungkinan penyimpangan (%)'
    ]
    for col in cols_to_check:
        if col in recap_display.columns:
            recap_display[col] = pd.to_numeric(recap_display[col], errors='coerce').round(2)

    # Terapkan styling dan formatting
    styled_df = recap_display.style.apply(highlight_outliers, axis=1).format({
        'Metrik Anak prasekolah ditimbang (%)': "{:.2f}%",
        'Metrik Anak prasekolah punya buku KIA (%)': "{:.2f}%",
        'Metrik Anak prasekolah dengan perkembangan normal (%)': "{:.2f}%",
        'Metrik Anak prasekolah dengan perkembangan meragukan (%)': "{:.2f}%",
        'Metrik Anak prasekolah dengan kemungkinan penyimpangan (%)': "{:.2f}%"
    }, na_rep="N/A", precision=2)

    # Render tabel dengan styling yang eksplisit
    st.write(styled_df, unsafe_allow_html=True)

    # Tambahkan notice di bawah tabel
    st.markdown(
        """
        <div style="background-color: #ADD8E6; padding: 10px; border-radius: 5px; color: black; font-size: 14px; font-family: Arial, sans-serif;">
            <strong>Catatan Penting:</strong> Nilai yang melebihi 100% (indikasi data outlier) telah dihighlight <span style="color: #FF6666; font-weight: bold;">Warna Merah</span>. Untuk analisis lebih lanjut dan koreksi data, mohon dilakukan pemeriksaan pada <strong>Menu Daftar Entry</strong>.
        </div>
        """,
        unsafe_allow_html=True
    )
        # 3.1 🚨 Tabel Deteksi Outlier (Logis)
    st.subheader("🚨 Tabel Deteksi Outlier")
    # Mapping metrik ke kolom numerator dan denominator
    metric_to_columns = {
        "Metrik Anak prasekolah ditimbang (%)": ("Jumlah_anak_prasekolah_ditimbang", "Jumlah_anak_prasekolah_bulan_ini"),
        "Metrik Anak prasekolah punya buku KIA (%)": ("Jumlah_anak_prasekolah_punya_Buku_KIA", "Jumlah_anak_prasekolah_bulan_ini"),
        "Metrik Anak prasekolah dengan perkembangan normal (%)": ("Jumlah_anak_prasekolah_dengan_perkembangan_normal", "Jumlah_anak_prasekolah_diskrining_perkembangan"),
        "Metrik Anak prasekolah dengan perkembangan meragukan (%)": ("Jumlah_anak_prasekolah_dengan_perkembangan_meragukan", "Jumlah_anak_prasekolah_diskrining_perkembangan"),
        "Metrik Anak prasekolah dengan kemungkinan penyimpangan (%)": ("Jumlah_anak_prasekolah_dengan_kemungkinan_penyimpangan", "Jumlah_anak_prasekolah_diskrining_perkembangan")
    }

    # Inisialisasi DataFrame untuk outlier logis
    outliers_df = pd.DataFrame(columns=["Puskesmas", "Kelurahan", "Metrik", "Numerator", "Denominator", "Rasio", "Alasan"])

    # Deteksi outlier logis untuk setiap metrik
    for metric, (numerator_col, denominator_col) in metric_to_columns.items():
        # Kasus 1: Numerator > Denominator
        outlier_data_num = filtered_df[
            (filtered_df[numerator_col] > filtered_df[denominator_col]) &
            (filtered_df[denominator_col] != 0)
        ][["Puskesmas", "Kelurahan", numerator_col, denominator_col]]
        if not outlier_data_num.empty:
            outlier_data_num["Metrik"] = metric
            outlier_data_num["Numerator"] = outlier_data_num[numerator_col]
            outlier_data_num["Denominator"] = outlier_data_num[denominator_col]
            outlier_data_num["Rasio"] = (outlier_data_num[numerator_col] / outlier_data_num[denominator_col] * 100).round(2)
            outlier_data_num["Alasan"] = "Numerator > Denominator"
            outliers_df = pd.concat(
                [outliers_df, outlier_data_num[["Puskesmas", "Kelurahan", "Metrik", "Numerator", "Denominator", "Rasio", "Alasan"]]],
                ignore_index=True
            )

        # Kasus 2: Denominator = 0
        outlier_data_zero = filtered_df[
            (filtered_df[denominator_col] == 0) &
            (filtered_df[numerator_col] > 0)
        ][["Puskesmas", "Kelurahan", numerator_col, denominator_col]]
        if not outlier_data_zero.empty:
            outlier_data_zero["Metrik"] = metric
            outlier_data_zero["Numerator"] = outlier_data_zero[numerator_col]
            outlier_data_zero["Denominator"] = outlier_data_zero[denominator_col]
            outlier_data_zero["Rasio"] = "Infinity"
            outlier_data_zero["Alasan"] = "Denominator = 0"
            outliers_df = pd.concat(
                [outliers_df, outlier_data_zero[["Puskesmas", "Kelurahan", "Metrik", "Numerator", "Denominator", "Rasio", "Alasan"]]],
                ignore_index=True
            )

    # Tampilkan Tabel Outlier Logis
    if not outliers_df.empty:
        styled_outliers = outliers_df.style.apply(
            lambda x: ['background-color: #FF6666; color: white;' if x['Alasan'] == "Numerator > Denominator" else 'background-color: #FF4500; color: white;'] * len(x),
            axis=1
        ).format({
            "Numerator": "{:.0f}",
            "Denominator": "{:.0f}",
            "Rasio": lambda x: f"{x:.2f}%" if isinstance(x, (int, float)) else x
        }).set_properties(**{
            'border': '1px solid black',
            'text-align': 'center',
            'font-size': '14px',
            'font-family': 'Arial, sans-serif'
        }).set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold')]},
            {'selector': 'caption', 'props': [('caption-side', 'top'), ('font-size', '18px'), ('font-weight', 'bold'), ('color', '#333')]},
        ]).set_caption("Tabel Outlier: Data dengan Numerator > Denominator atau Denominator = 0")

        st.write(styled_outliers, unsafe_allow_html=True)
    else:
        st.success("✅ Tidak ada outlier terdeteksi berdasarkan kriteria Numerator > Denominator atau Denominator = 0.")

    # 3.2 ⚙️ Analisis Outlier Statistik
    st.subheader("⚙️ Analisis Outlier Statistik")
    # Gunakan recap_df yang sudah dihitung persentasenya
    cols_to_check = list(metrik_data.keys())

    # Inisialisasi DataFrame untuk outlier statistik
    base_columns = ["Puskesmas", "Metrik", "Nilai", "Metode"]
    if puskesmas_filter != "All":
        base_columns.insert(1, "Kelurahan")
    statistical_outliers_df = pd.DataFrame(columns=base_columns)

    # Dropdown untuk memilih metode deteksi outlier statistik
    outlier_method = st.selectbox(
        "Pilih Metode Deteksi Outlier Statistik",
        ["Tidak Ada", "Z-Score", "IQR"],
        key=f"outlier_method_select_apras_{periode_label}"
    )

    if outlier_method != "Tidak Ada":
        for metric in cols_to_check:
            if metric not in recap_df.columns:
                continue

            # Pilih kolom berdasarkan filter
            if puskesmas_filter == "All":
                metric_data = recap_df[[metric, "Puskesmas"]].dropna()
            else:
                metric_data = recap_df[[metric, "Puskesmas", "Kelurahan"]].dropna()

            if metric_data.empty:
                continue

            # Z-Score Method
            if outlier_method == "Z-Score":
                z_scores = stats.zscore(metric_data[metric], nan_policy='omit')
                z_outlier_mask = abs(z_scores) > 3  # Threshold Z-Score > 3
                z_outliers = metric_data[z_outlier_mask].copy()
                if not z_outliers.empty:
                    z_outliers["Metrik"] = metric
                    z_outliers["Nilai"] = z_outliers[metric]
                    z_outliers["Metode"] = "Z-Score"
                    if puskesmas_filter == "All":
                        z_outliers_subset = z_outliers[["Puskesmas", "Metrik", "Nilai", "Metode"]]
                    else:
                        z_outliers_subset = z_outliers[["Puskesmas", "Kelurahan", "Metrik", "Nilai", "Metode"]]
                    statistical_outliers_df = pd.concat(
                        [statistical_outliers_df, z_outliers_subset],
                        ignore_index=True
                    )

            # IQR Method
            elif outlier_method == "IQR":
                Q1 = metric_data[metric].quantile(0.25)
                Q3 = metric_data[metric].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                iqr_outlier_mask = (metric_data[metric] < lower_bound) | (metric_data[metric] > upper_bound)
                iqr_outliers = metric_data[iqr_outlier_mask].copy()
                if not iqr_outliers.empty:
                    iqr_outliers["Metrik"] = metric
                    iqr_outliers["Nilai"] = iqr_outliers[metric]
                    iqr_outliers["Metode"] = "IQR"
                    if puskesmas_filter == "All":
                        iqr_outliers_subset = iqr_outliers[["Puskesmas", "Metrik", "Nilai", "Metode"]]
                    else:
                        iqr_outliers_subset = iqr_outliers[["Puskesmas", "Kelurahan", "Metrik", "Nilai", "Metode"]]
                    statistical_outliers_df = pd.concat(
                        [statistical_outliers_df, iqr_outliers_subset],
                        ignore_index=True
                    )

    # 3.3 📊 Tabel Outlier Statistik
    if not statistical_outliers_df.empty:
        st.markdown("### 📊 Tabel Outlier Statistik")
        styled_stat_outliers = statistical_outliers_df.style.apply(
            lambda x: ['background-color: #FFA500; color: white;' if x['Metode'] == "Z-Score" else 'background-color: #FF8C00; color: white;'] * len(x),
            axis=1
        ).format({
            "Nilai": "{:.2f}%"
        }).set_properties(**{
            'border': '1px solid black',
            'text-align': 'center',
            'font-size': '14px',
            'font-family': 'Arial, sans-serif'
        }).set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#FF9800'), ('color', 'white'), ('font-weight', 'bold')]},
            {'selector': 'caption', 'props': [('caption-side', 'top'), ('font-size', '18px'), ('font-weight', 'bold'), ('color', '#333')]},
        ]).set_caption(f"Tabel Outlier Statistik ({outlier_method})")

        st.write(styled_stat_outliers, unsafe_allow_html=True)
    else:
        if outlier_method != "Tidak Ada":
            st.info(f"ℹ️ Tidak ada outlier statistik terdeteksi menggunakan metode {outlier_method}.")

    # 3.4 📊 Visualisasi Outlier
    st.subheader("📊 Visualisasi Outlier")
    show_outlier_viz = st.checkbox(
        "Tampilkan Visualisasi Outlier",
        value=False,
        key=f"apras_viz_toggle_{periode_label}"
    )

    if show_outlier_viz:
        # Gabungkan outlier logis dan statistik
        combined_outliers = outliers_df[["Puskesmas", "Kelurahan", "Metrik", "Rasio"]].copy()
        combined_outliers["Metode"] = "Logis (Numerator > Denominator atau Denominator = 0)"
        # Ganti "Infinity" dengan nilai besar untuk visualisasi
        combined_outliers["Rasio"] = combined_outliers["Rasio"].replace("Infinity", 9999)
        if not statistical_outliers_df.empty:
            stat_outliers = statistical_outliers_df[["Puskesmas", "Metrik", "Metode"]].copy()
            stat_outliers["Rasio"] = statistical_outliers_df["Nilai"]
            if "Kelurahan" in statistical_outliers_df.columns:
                stat_outliers["Kelurahan"] = statistical_outliers_df["Kelurahan"]
            else:
                stat_outliers["Kelurahan"] = "N/A"
            combined_outliers = pd.concat([combined_outliers, stat_outliers], ignore_index=True)

        if not combined_outliers.empty:
            viz_type = st.selectbox(
                "Pilih Tipe Visualisasi Outlier",
                ["Heatmap", "Grafik Batang", "Boxplot"],
                key=f"outlier_viz_select_apras_{periode_label}"
            )

            if viz_type == "Heatmap":
                pivot_df = combined_outliers.pivot_table(
                    index="Puskesmas",
                    columns="Metrik",
                    values="Rasio",
                    aggfunc="mean",
                    fill_value=0
                )
                fig_heatmap = px.imshow(
                    pivot_df,
                    text_auto=True,
                    aspect="auto",
                    title="Heatmap Distribusi Outlier per Puskesmas",
                    color_continuous_scale="Reds"
                )
                fig_heatmap.update_layout(
                    xaxis_title="Metrik",
                    yaxis_title="Puskesmas",
                    coloraxis_colorbar_title="Rasio (%)"
                )
                st.plotly_chart(fig_heatmap, use_container_width=True)

            elif viz_type == "Grafik Batang":
                count_df = combined_outliers.groupby(["Metrik", "Metode"]).size().reset_index(name="Jumlah")
                fig_bar = px.bar(
                    count_df,
                    x="Metrik",
                    y="Jumlah",
                    color="Metode",
                    barmode="group",
                    title="Jumlah Outlier per Metrik dan Metode Deteksi",
                    text="Jumlah"
                )
                fig_bar.update_traces(textposition="outside")
                fig_bar.update_layout(
                    xaxis_title="Metrik",
                    yaxis_title="Jumlah Outlier",
                    xaxis_tickangle=45,
                    legend_title="Metode Deteksi"
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            elif viz_type == "Boxplot":
                fig_box = px.box(
                    combined_outliers,
                    x="Metrik",
                    y="Rasio",
                    color="Metode",
                    title="Boxplot Distribusi Outlier per Metrik dan Metode Deteksi",
                    points="all"
                )
                fig_box.update_layout(
                    xaxis_title="Metrik",
                    yaxis_title="Rasio (%)",
                    xaxis_tickangle=45,
                    legend_title="Metode Deteksi"
                )
                st.plotly_chart(fig_box, use_container_width=True)
        else:
            st.info("ℹ️ Tidak ada data outlier untuk divisualisasikan.")
        # 3.5 📈 Analisis Tren Metrik Tumbuh Kembang Anak Prasekolah
    st.subheader("📈 Tren Metrik Tumbuh Kembang Anak Prasekolah")

    # Daftar metrik yang akan dianalisis trennya
    metric_list = [
        "Metrik Anak prasekolah ditimbang (%)",
        "Metrik Anak prasekolah punya buku KIA (%)",
        "Metrik Anak prasekolah dengan perkembangan normal (%)",
        "Metrik Anak prasekolah dengan perkembangan meragukan (%)",
        "Metrik Anak prasekolah dengan kemungkinan penyimpangan (%)"
    ]

    # Mapping kolom numerator dan denominator untuk setiap metrik
    metric_to_columns = {
        "Metrik Anak prasekolah ditimbang (%)": ("Jumlah_anak_prasekolah_ditimbang", "Jumlah_anak_prasekolah_bulan_ini"),
        "Metrik Anak prasekolah punya buku KIA (%)": ("Jumlah_anak_prasekolah_punya_Buku_KIA", "Jumlah_anak_prasekolah_bulan_ini"),
        "Metrik Anak prasekolah dengan perkembangan normal (%)": ("Jumlah_anak_prasekolah_dengan_perkembangan_normal", "Jumlah_anak_prasekolah_diskrining_perkembangan"),
        "Metrik Anak prasekolah dengan perkembangan meragukan (%)": ("Jumlah_anak_prasekolah_dengan_perkembangan_meragukan", "Jumlah_anak_prasekolah_diskrining_perkembangan"),
        "Metrik Anak prasekolah dengan kemungkinan penyimpangan (%)": ("Jumlah_anak_prasekolah_dengan_kemungkinan_penyimpangan", "Jumlah_anak_prasekolah_diskrining_perkembangan")
    }

    # Salin filtered_df agar tidak mengubah aslinya
    trend_data = filtered_df.copy()

    # Hitung metrik persentase untuk setiap baris di trend_data
    for metric, (numerator_col, denominator_col) in metric_to_columns.items():
        trend_data[metric] = (trend_data[numerator_col] / trend_data[denominator_col] * 100).round(2)
        # Ganti NaN atau inf dengan 0 untuk kebersihan data
        trend_data[metric] = trend_data[metric].replace([float('inf'), float('-inf')], 0).fillna(0)

    # Filter dan agregasi data berdasarkan Bulan
    trend_df = trend_data.groupby("Bulan")[metric_list].mean().reset_index()
    trend_df = trend_df.melt(
        id_vars="Bulan",
        value_vars=metric_list,
        var_name="Metrik",
        value_name="Persentase"
    )

    # Bulatkan kolom Persentase menjadi 2 digit desimal
    trend_df["Persentase"] = trend_df["Persentase"].round(2)

    # Tampilkan line chart untuk semua metrik
    if not trend_df.empty:
        fig_trend = px.line(
            trend_df,
            x="Bulan",
            y="Persentase",
            color="Metrik",
            markers=True,
            text=trend_df["Persentase"].apply(lambda x: f"{x:.2f}"),  # Format teks menjadi 2 digit desimal
            title="📈 Tren Metrik Tumbuh Kembang Anak Prasekolah dari Awal hingga Akhir Bulan"
        )
        fig_trend.update_traces(textposition="top center")
        fig_trend.update_layout(
            xaxis_title="Bulan",
            yaxis_title="Persentase (%)",
            xaxis=dict(tickmode='linear', tick0=1, dtick=1),
            yaxis_range=[0, 100],
            legend_title="Metrik",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(
            fig_trend,
            key=f"tumbuh_kembang_apras_trend_chart_{puskesmas_filter}_{kelurahan_filter}_{time.time()}",
            use_container_width=True
        )
    else:
        st.warning("⚠️ Tidak ada data untuk ditampilkan pada grafik tren Tumbuh Kembang Anak Prasekolah.")
    # 4. 📊 Analisis Komparasi Antar Wilayah
    st.subheader("📊 Analisis Komparasi Antar Wilayah")
    selected_metric = st.selectbox(
        "Pilih Metrik untuk Komparasi Antar Wilayah",
        metric_list,
        key="comp_metric_select_apras"
    )

    # Gunakan recap_df karena metrik persentase ada di sini
    group_cols = ["Puskesmas"]
    if 'Kelurahan' in recap_df.columns:
        group_cols.append("Kelurahan")

    comp_df = recap_df.groupby(group_cols)[selected_metric].mean().reset_index()
    if not comp_df.empty:
        if "Kelurahan" in comp_df.columns:
            fig_comp = px.bar(
                comp_df,
                x="Puskesmas",
                y=selected_metric,
                color="Kelurahan",
                title=f"📊 Komparasi {selected_metric} Antar Wilayah",
                text=comp_df[selected_metric].apply(lambda x: f"{x:.2f}%"),
                height=400
            )
            fig_comp.update_traces(textposition="outside")
            fig_comp.update_layout(
                xaxis_title="Puskesmas",
                yaxis_title="Persentase (%)",
                xaxis_tickangle=45,
                yaxis_range=[0, 100],
                legend_title="Kelurahan"
            )
        else:
            fig_comp = px.bar(
                comp_df,
                x="Puskesmas",
                y=selected_metric,
                title=f"📊 Komparasi {selected_metric} Antar Wilayah (Tanpa Kelurahan)",
                text=comp_df[selected_metric].apply(lambda x: f"{x:.2f}%"),
                height=400
            )
            fig_comp.update_traces(textposition="outside")
            fig_comp.update_layout(
                xaxis_title="Puskesmas",
                yaxis_title="Persentase (%)",
                xaxis_tickangle=45,
                yaxis_range=[0, 100]
            )
            st.warning("⚠️ Data 'Kelurahan' tidak tersedia di recap_df.")
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.warning("⚠️ Tidak ada data untuk komparasi antar wilayah.")

    # 5. 🔍 Analisis Korelasi Antar Metrik
    st.subheader("🔍 Analisis Korelasi Antar Metrik")
    corr_df = recap_df.groupby(group_cols)[metric_list].mean().reset_index()
    if len(corr_df) > 1:
        correlation_matrix = corr_df[metric_list].corr()
        fig_corr = px.imshow(
            correlation_matrix,
            text_auto=True,
            aspect="auto",
            title="🔍 Matriks Korelasi Antar Metrik Tumbuh Kembang Apras",
            color_continuous_scale="RdBu",
            range_color=[-1, 1]
        )
        fig_corr.update_layout(
            xaxis_title="Metrik",
            yaxis_title="Metrik",
            coloraxis_colorbar_title="Koefisien Korelasi"
        )
        st.plotly_chart(fig_corr, use_container_width=True)
        st.markdown("**Catatan:** Nilai mendekati 1 atau -1 menunjukkan korelasi kuat (positif atau negatif), sementara 0 menunjukkan tidak ada korelasi.")
    else:
        st.warning("⚠️ Tidak cukup data untuk menghitung korelasi antar metrik.")

    # 6. 📅 Analisis Perubahan Persentase (Growth/Decline)
    st.subheader("📅 Analisis Perubahan Persentase (Growth/Decline)")
    if 'Bulan' in filtered_df.columns:
        trend_melted = trend_df.copy()
        trend_melted["Perubahan Persentase"] = trend_melted.groupby("Metrik")["Persentase"].pct_change() * 100
        trend_melted["Perubahan Persentase"] = trend_melted["Perubahan Persentase"].round(2)

        if not trend_melted.empty:
            # Tampilkan tabel perubahan
            st.dataframe(
                trend_melted[["Bulan", "Metrik", "Persentase", "Perubahan Persentase"]].style.format({
                    "Persentase": "{:.2f}%",
                    "Perubahan Persentase": "{:.2f}%"
                }).set_properties(**{
                    'text-align': 'center',
                    'font-size': '14px',
                    'border': '1px solid black'
                }).set_table_styles([
                    {'selector': 'th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold')]},
                    {'selector': 'caption', 'props': [('caption-side', 'top'), ('font-size', '18px'), ('font-weight', 'bold'), ('color', '#333')]},
                ]).set_caption("📅 Tabel Perubahan Persentase Antar Bulan"),
                use_container_width=True
            )

            # Visualisasi perubahan dengan grafik garis
            fig_change = px.line(
                trend_melted,
                x="Bulan",
                y="Perubahan Persentase",
                color="Metrik",
                markers=True,
                text=trend_melted["Perubahan Persentase"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else ""),
                title="📅 Tren Perubahan Persentase Metrik Tumbuh Kembang Apras"
            )
            fig_change.update_traces(textposition="top center")
            fig_change.update_layout(
                xaxis_title="Bulan",
                yaxis_title="Perubahan Persentase (%)",
                xaxis=dict(tickmode='linear', tick0=1, dtick=1),
                legend_title="Metrik",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_change, use_container_width=True)
        else:
            st.warning("⚠️ Tidak ada data untuk menganalisis perubahan persentase.")
    else:
        st.warning("⚠️ Kolom 'Bulan' tidak tersedia di data. Analisis perubahan persentase tidak dapat dilakukan.")

    # 7. 📉 Analisis Distribusi Data (Histogram)
    st.subheader("📉 Analisis Distribusi Data (Histogram)")
    selected_metric_dist = st.selectbox(
        "Pilih Metrik untuk Analisis Distribusi",
        metric_list,
        key="dist_metric_select_apras"
    )

    dist_df = recap_df.groupby(group_cols)[selected_metric_dist].mean().reset_index()
    if not dist_df.empty:
        fig_dist = px.histogram(
            dist_df,
            x=selected_metric_dist,
            nbins=20,
            title=f"📉 Distribusi {selected_metric_dist} di Seluruh Wilayah",
            labels={"value": "Persentase (%)", "count": "Jumlah Wilayah"},
            height=400
        )
        fig_dist.update_layout(
            xaxis_title="Persentase (%)",
            yaxis_title="Jumlah Wilayah",
            bargap=0.1
        )
        st.plotly_chart(fig_dist, use_container_width=True)
        # Tambahan statistik dasar
        mean_val = dist_df[selected_metric_dist].mean().round(2)
        median_val = dist_df[selected_metric_dist].median().round(2)
        st.markdown(f"**Statistik Distribusi:** Rata-rata = {mean_val}%, Median = {median_val}%")
    else:
        st.warning("⚠️ Tidak ada data untuk analisis distribusi.")

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
        elements.append(Paragraph(f"Laporan Pemantauan Tumbuh Kembang Apras ({periode_label})", title_style))
        elements.append(Paragraph(f"Diperbarui: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
        elements.append(Spacer(1, 12))

        # Tambahkan Metrik
        elements.append(Paragraph("1. Metrik Pemantauan", normal_style))
        metric_data = [[f"{label}: {value:.2f}%" for label, value in metrik_list]]
        metric_table = Table(metric_data, colWidths=[300])
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

        # Tambahkan Grafik 1: Cakupan Layanan Apras
        elements.append(Paragraph("2. Grafik Cakupan Layanan Apras", normal_style))
        elements.append(Image(img_buffer1, width=500, height=300))
        elements.append(Spacer(1, 12))

        # Tambahkan Grafik 2: Pemantauan Tumbuh Kembang Apras
        elements.append(Paragraph("3. Grafik Pemantauan Tumbuh Kembang Apras", normal_style))
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

    if st.button("Download Laporan PDF", key=f"download_pemantauan_tumbuh_kembang_apras_{periode_label}"):
        st.warning("Membuat laporan PDF, harap tunggu...")
        pdf_data = generate_pdf_report()
        st.success("Laporan PDF siap diunduh!")
        st.download_button(
            label="Download Laporan PDF",
            data=pdf_data,
            file_name=f"Laporan_Pemantauan_Tumbuh_Kembang_Apras_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )
# ----------------------------- #
# 🏥 Cakupan Layanan Kesehatan Balita
# ----------------------------- #
def cakupan_layanan_kesehatan_balita(filtered_df, desa_df, puskesmas_filter, kelurahan_filter, jenis_laporan, tahun_filter, bulan_filter_int=None, tribulan_filter=None):
    """Menampilkan analisis Cakupan Layanan Kesehatan Balita dengan fitur download laporan."""
    st.header("🏥 Cakupan Layanan Kesehatan Balita")
    # Informasi Metrik Cakupan Layanan Kesehatan Balita
    with st.expander("📜 Definisi dan Insight Analisis Cakupan Layanan Kesehatan Balita", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Analisis Indikator

            Berikut adalah definisi operasional, rumus perhitungan, serta analisis insight dari indikator-indikator yang digunakan untuk memantau cakupan layanan kesehatan balita (usia 12-59 bulan) dalam kerangka Surveilans Deteksi Dini Tumbuh Kembang (SDIDTK) dan pedoman pemantauan pertumbuhan versi terbaru, diperbarui hingga Mei 2025. Rumus disajikan dalam format matematis untuk kejelasan, dengan penjelasan sederhana untuk mendukung pemahaman petugas kesehatan.

            #### 1. Persentase Balita Dipantau Pertumbuhan dan Perkembangan
            - **Definisi Operasional:** Persentase balita usia 12-59 bulan yang dipantau pertumbuhan dan perkembangannya terhadap total balita pada bulan pelaporan di wilayah kerja puskesmas, sesuai pedoman SDIDTK untuk pemantauan rutin.  
            - **Rumus Perhitungan:**  
            $$ \\text{Metrik Balita dipantau pertumbuhan dan perkembangan (\\%)} = \\frac{\\text{Jumlah balita dipantau tumbang}}{\\text{Total balita usia 12-59 bulan}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen balita yang dipantau pertumbuhan dan perkembangannya dari total balita pada bulan tersebut, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan bulanan melalui laporan posyandu atau puskesmas, dengan pencatatan jumlah balita yang dipantau menggunakan alat standar SDIDTK, seperti timbangan dan alat ukur tinggi.  
            - **Insight Analisis:** Persentase di bawah 80% (target SDIDTK 2025) dapat mengindikasikan rendahnya cakupan pemantauan atau keterbatasan akses layanan. Peningkatan pelatihan kader dan penyediaan alat ukur dapat mendukung deteksi dini gangguan pertumbuhan, seperti stunting atau underweight, yang prevalensinya masih tinggi di Indonesia berdasarkan laporan Kementerian Kesehatan 2024.

            #### 2. Persentase Balita Terdeteksi Gangguan atau Penyimpangan Perkembangan yang Mendapat Intervensi
            - **Definisi Operasional:** Persentase balita usia 12-59 bulan yang terdeteksi memiliki gangguan atau penyimpangan perkembangan dan mendapatkan intervensi terhadap total balita yang terdeteksi gangguan pada bulan pelaporan, sesuai pedoman SDIDTK.  
            - **Rumus Perhitungan:**  
            $$ \\text{Metrik Balita terdeteksi gangguan yang mendapat intervensi (\\%)} = \\frac{\\text{Jumlah balita terdeteksi gangguan yang mendapat intervensi}}{\\text{Total balita terdeteksi gangguan}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen balita yang mendapat intervensi dari total balita yang terdeteksi memiliki gangguan, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data diambil dari laporan bulanan posyandu atau puskesmas, dengan pencatatan jumlah balita yang terdeteksi gangguan melalui skrining KPSP (Kuesioner Pra Skrining Perkembangan) dan yang mendapat intervensi seperti rujukan atau stimulasi perkembangan.  
            - **Insight Analisis:** Persentase di bawah 90% (target SDIDTK 2025) menunjukkan rendahnya tindak lanjut intervensi. Koordinasi dengan tenaga kesehatan untuk rujukan dini dan pelatihan stimulasi perkembangan dapat meningkatkan angka ini, mencegah dampak jangka panjang seperti keterlambatan perkembangan motorik atau kognitif.

            #### 3. Persentase Balita Mendapat Pelayanan SDIDTK di Fasilitas Kesehatan Primer (FKTP)
            - **Definisi Operasional:** Persentase balita usia 12-59 bulan yang mendapatkan pelayanan SDIDTK di fasilitas kesehatan primer (FKTP) terhadap total balita pada bulan pelaporan, sesuai pedoman SDIDTK.  
            - **Rumus Perhitungan:**  
            $$ \\text{Metrik Balita mendapat pelayanan SDIDTK di Fasyankes (\\%)} = \\frac{\\text{Jumlah balita mendapat pelayanan SDIDTK di FKTP}}{\\text{Total balita usia 12-59 bulan}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen balita yang mendapat pelayanan SDIDTK di FKTP dari total balita pada bulan tersebut, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui laporan bulanan puskesmas, dengan pencatatan jumlah balita yang mendapatkan pelayanan SDIDTK di FKTP seperti puskesmas atau posyandu terintegrasi.  
            - **Insight Analisis:** Persentase di bawah 80% (target SDIDTK 2025) dapat mengindikasikan rendahnya akses ke layanan FKTP. Peningkatan integrasi posyandu dengan puskesmas dan penyediaan tenaga kesehatan terlatih dapat meningkatkan cakupan layanan ini.

            #### 4. Persentase Balita yang Buku KIA-nya Terisi Lengkap Bagian Pemantauan Perkembangan
            - **Definisi Operasional:** Persentase balita usia 12-59 bulan yang Buku KIA-nya terisi lengkap pada bagian pemantauan perkembangan terhadap total balita yang memiliki Buku KIA pada bulan pelaporan, sesuai pedoman SDIDTK.  
            - **Rumus Perhitungan:**  
            $$ \\text{Metrik Balita yang Buku KIA terisi lengkap (\\%)} = \\frac{\\text{Jumlah balita dengan Buku KIA terisi lengkap}}{\\text{Total balita yang punya Buku KIA}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen balita yang Buku KIA-nya terisi lengkap dari total balita yang memiliki Buku KIA, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data diambil dari laporan bulanan posyandu atau puskesmas, dengan verifikasi kelengkapan pengisian Buku KIA pada bagian pemantauan perkembangan oleh tenaga kesehatan.  
            - **Insight Analisis:** Persentase di bawah 90% (target SDIDTK 2025) dapat menunjukkan kurangnya konsistensi dalam pengisian Buku KIA. Pelatihan kader dan edukasi ibu balita tentang pentingnya dokumentasi dapat meningkatkan kepatuhan pengisian, mendukung pemantauan perkembangan yang berkelanjutan.

            #### 5. Persentase Balita yang Ibu/Orang Tua/Wali/Keluarga/Pengasuh Mengikuti Minimal 4 Kali Kelas Ibu Balita
            - **Definisi Operasional:** Persentase balita usia 12-59 bulan yang ibu/orang tua/wali/keluarga/pengasuhnya telah mengikuti minimal 4 kali kelas ibu balita terhadap total balita pada bulan pelaporan, sesuai pedoman SDIDTK.  
            - **Rumus Perhitungan:**  
            $$ \\text{Metrik Balita yang ibu mengikuti kelas ibu balita (\\%)} = \\frac{\\text{Jumlah balita yang ibu mengikuti minimal 4 kali kelas}}{\\text{Total balita usia 12-59 bulan}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen balita yang ibunya mengikuti minimal 4 kali kelas ibu balita dari total balita pada bulan tersebut, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui laporan bulanan posyandu, dengan pencatatan kehadiran ibu/orang tua dalam kelas ibu balita yang diselenggarakan oleh posyandu atau puskesmas.  
            - **Insight Analisis:** Persentase di bawah 70% (target SDIDTK 2025) dapat mengindikasikan rendahnya partisipasi ibu dalam kelas edukasi. Peningkatan jadwal kelas yang fleksibel dan sosialisasi manfaat kelas ibu balita dapat meningkatkan partisipasi, yang penting untuk edukasi gizi dan stimulasi perkembangan balita.

            </div>
        """, unsafe_allow_html=True)

    # Inisialisasi periode untuk label
    periode_label = ""
    if tahun_filter != "All":
        periode_label += f"Tahun {tahun_filter}"
    if jenis_laporan == "Bulanan" and bulan_filter_int is not None:
        periode_label += f" Bulan {bulan_filter_int}" if periode_label else f"Bulan {bulan_filter_int}"
    elif jenis_laporan == "Tahunan" and tribulan_filter:
        periode_label += f" {tribulan_filter}" if periode_label else tribulan_filter

    # 1. Memuat data dari data_balita_gizi (Jumlah_balita_punya_KIA dan Jumlah_sasaran_balita)
    try:
        conn = sqlite3.connect("rcs_data.db")
        gizi_df = pd.read_sql_query("SELECT Kelurahan, Bulan, Jumlah_balita_punya_KIA, Jumlah_sasaran_balita FROM data_balita_gizi", conn)
        conn.close()
    except Exception as e:
        st.error(f"❌ Gagal memuat data dari data_balita_gizi: {e}")
        return

    # Daftar kolom yang dibutuhkan dari data_balita_kia
    required_columns = [
        'Jumlah_balita_usia_12-59_bulan_sampai_bulan_ini',
        'Jumlah_balita_pantau_tumbang',
        'Jumlah_balita_terdeteksi_gangguan_tumbang',
        'Jumlah_balita_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi',
        'Jumlah_balita_mendapat_pelayanan_SDIDTK_di_FKTP',
        'Jumlah_balita_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan',
        'Jumlah_balita_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'
    ]

    # Cek apakah semua kolom ada
    missing_cols = [col for col in required_columns if col not in filtered_df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di dataset: {missing_cols}. Periksa data di 'data_balita_kia'!")
        return

    # Pastikan tipe data Bulan sama
    filtered_df['Bulan'] = filtered_df['Bulan'].astype(int)
    gizi_df['Bulan'] = gizi_df['Bulan'].astype(int)

    # Agregasi data berdasarkan jenis laporan
    if jenis_laporan == "Tahunan" and not filtered_df.empty:
        group_columns = ["Puskesmas", "Kelurahan"]
        numeric_columns = [col for col in filtered_df.columns if filtered_df[col].dtype in ['int64', 'float64']]
        if numeric_columns:
            agg_dict = {col: "sum" for col in numeric_columns}
            filtered_df = filtered_df.groupby(group_columns).agg(agg_dict).reset_index()

    # Gabungkan data dari data_balita_kia dengan data_balita_gizi
    merged_df = pd.merge(
        filtered_df,
        gizi_df[['Kelurahan', 'Bulan', 'Jumlah_balita_punya_KIA', 'Jumlah_sasaran_balita']],
        on=['Kelurahan', 'Bulan'],
        how='left'
    )

    # Cek apakah ada data yang tidak match
    if merged_df['Jumlah_balita_punya_KIA'].isna().all() or merged_df['Jumlah_sasaran_balita'].isna().all():
        st.warning("⚠️ Tidak ada data Jumlah_balita_punya_KIA atau Jumlah_sasaran_balita yang cocok dengan filter Kelurahan dan Bulan. Periksa data di data_balita_gizi!")
        return

    # Hitung total dari filtered_df (sebagai basis utama) dan merged_df untuk Jumlah_sasaran_balita
    total_balita = filtered_df['Jumlah_balita_usia_12-59_bulan_sampai_bulan_ini'].sum()
    total_deteksi_gangguan = filtered_df['Jumlah_balita_terdeteksi_gangguan_tumbang'].sum()
    total_punya_kia = merged_df['Jumlah_balita_punya_KIA'].sum()
    total_sasaran_balita = merged_df['Jumlah_sasaran_balita'].sum()

    if total_balita == 0:
        st.warning("⚠️ Tidak ada data balita usia 12-59 bulan untuk filter ini.")
        return
    if total_deteksi_gangguan == 0 and 'Jumlah_balita_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi' in required_columns:
        st.warning("⚠️ Tidak ada data balita terdeteksi gangguan untuk filter ini.")
    if total_punya_kia == 0 and 'Jumlah_balita_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan' in required_columns:
        st.warning("⚠️ Tidak ada data balita yang memiliki Buku KIA untuk filter ini.")
    if total_sasaran_balita == 0:
        st.warning("⚠️ Tidak ada data Jumlah_sasaran_balita untuk filter ini.")
        return

    # Hitung metrik menggunakan filtered_df untuk numerator dan sebagian denominator, dengan penyesuaian untuk SDIDTK dan Kelas Ibu Balita
    metrik_data = {
        "Metrik Balita dipantau pertumbuhan dan perkembangan (%)": (filtered_df['Jumlah_balita_pantau_tumbang'].sum() / total_balita * 100),
        "Metrik balita yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)": (filtered_df['Jumlah_balita_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi'].sum() / total_deteksi_gangguan * 100 if total_deteksi_gangguan else 0),
        "Metrik balita mendapat pelayanan SDIDTK di Fasyankes (%)": (filtered_df['Jumlah_balita_mendapat_pelayanan_SDIDTK_di_FKTP'].sum() / total_sasaran_balita * 100 if total_sasaran_balita else 0),
        "Metrik Balita yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)": (filtered_df['Jumlah_balita_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan'].sum() / total_punya_kia * 100 if total_punya_kia else 0),
        "Metrik balita yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)": (filtered_df['Jumlah_balita_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'].sum() / total_sasaran_balita * 100 if total_sasaran_balita else 0)
    }

    # 1. Metrik Score Card
    st.subheader(f"📊 Metrik Cakupan Layanan Kesehatan Balita ({periode_label})")
    metrik_list = list(metrik_data.items())
    cols = st.columns(2)  # 2 kolom
    for i in range(2):
        if i < len(metrik_list):
            label, value = metrik_list[i]
            cols[i].metric(label=label, value=f"{value:.2f}%")
    for i in range(2, len(metrik_list)):
        label, value = metrik_list[i]
        cols[i % 2].metric(label=label, value=f"{value:.2f}%")

    # 2. Grafik Visualisasi (5 grafik terpisah per metrik)
    st.subheader(f"📈 Grafik Cakupan Layanan Kesehatan Balita ({periode_label})")
    metrics = list(metrik_data.keys())
    figures_list = []  # Daftar untuk menyimpan semua objek fig
    for metric in metrics:
        if puskesmas_filter == "All":
            grouped_df = merged_df.groupby('Puskesmas').sum().reset_index()
            if metric == "Metrik Balita dipantau pertumbuhan dan perkembangan (%)":
                graph_data = pd.DataFrame({
                    "Puskesmas": grouped_df['Puskesmas'],
                    metric: (grouped_df['Jumlah_balita_pantau_tumbang'] / grouped_df['Jumlah_balita_usia_12-59_bulan_sampai_bulan_ini'] * 100).fillna(0)
                })
            elif metric == "Metrik balita yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)":
                graph_data = pd.DataFrame({
                    "Puskesmas": grouped_df['Puskesmas'],
                    metric: (grouped_df['Jumlah_balita_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi'] / grouped_df['Jumlah_balita_terdeteksi_gangguan_tumbang'] * 100).fillna(0)
                })
            elif metric == "Metrik balita mendapat pelayanan SDIDTK di Fasyankes (%)":
                graph_data = pd.DataFrame({
                    "Puskesmas": grouped_df['Puskesmas'],
                    metric: (grouped_df['Jumlah_balita_mendapat_pelayanan_SDIDTK_di_FKTP'] / grouped_df['Jumlah_sasaran_balita'] * 100).fillna(0)
                })
            elif metric == "Metrik Balita yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)":
                graph_data = pd.DataFrame({
                    "Puskesmas": grouped_df['Puskesmas'],
                    metric: (grouped_df['Jumlah_balita_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan'] / grouped_df['Jumlah_balita_punya_KIA'] * 100).fillna(0)
                })
            elif metric == "Metrik balita yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)":
                graph_data = pd.DataFrame({
                    "Puskesmas": grouped_df['Puskesmas'],
                    metric: (grouped_df['Jumlah_balita_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'] / grouped_df['Jumlah_sasaran_balita'] * 100).fillna(0)
                })
            fig = px.bar(graph_data, x="Puskesmas", y=metric, text=graph_data[metric].apply(lambda x: f"{x:.1f}%"),
                        title=f"{metric} per Puskesmas ({periode_label})", color_discrete_sequence=["#1E90FF"])
        else:
            grouped_df = merged_df.groupby('Kelurahan').sum().reset_index()
            if metric == "Metrik Balita dipantau pertumbuhan dan perkembangan (%)":
                graph_data = pd.DataFrame({
                    "Kelurahan": grouped_df['Kelurahan'],
                    metric: (grouped_df['Jumlah_balita_pantau_tumbang'] / grouped_df['Jumlah_balita_usia_12-59_bulan_sampai_bulan_ini'] * 100).fillna(0)
                })
            elif metric == "Metrik balita yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)":
                graph_data = pd.DataFrame({
                    "Kelurahan": grouped_df['Kelurahan'],
                    metric: (grouped_df['Jumlah_balita_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi'] / grouped_df['Jumlah_balita_terdeteksi_gangguan_tumbang'] * 100).fillna(0)
                })
            elif metric == "Metrik balita mendapat pelayanan SDIDTK di Fasyankes (%)":
                graph_data = pd.DataFrame({
                    "Kelurahan": grouped_df['Kelurahan'],
                    metric: (grouped_df['Jumlah_balita_mendapat_pelayanan_SDIDTK_di_FKTP'] / grouped_df['Jumlah_sasaran_balita'] * 100).fillna(0)
                })
            elif metric == "Metrik Balita yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)":
                graph_data = pd.DataFrame({
                    "Kelurahan": grouped_df['Kelurahan'],
                    metric: (grouped_df['Jumlah_balita_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan'] / grouped_df['Jumlah_balita_punya_KIA'] * 100).fillna(0)
                })
            elif metric == "Metrik balita yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)":
                graph_data = pd.DataFrame({
                    "Kelurahan": grouped_df['Kelurahan'],
                    metric: (grouped_df['Jumlah_balita_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'] / grouped_df['Jumlah_sasaran_balita'] * 100).fillna(0)
                })
            fig = px.bar(graph_data, x="Kelurahan", y=metric, text=graph_data[metric].apply(lambda x: f"{x:.1f}%"),
                        title=f"{metric} per Kelurahan di {puskesmas_filter} ({periode_label})", color_discrete_sequence=["#1E90FF"])

        fig.update_traces(textposition='outside')
        fig.add_hline(
            y=100,
            line_dash="dash",
            line_color="red",
            annotation_text="Target: 100%",
            annotation_position="top right"
        )
        fig.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", yaxis_range=[0, 100], title_x=0.5,
                        height=400)
        st.plotly_chart(fig, use_container_width=True)
        figures_list.append(fig)  # Simpan setiap fig ke daftar

    # 3. Tabel Rekapitulasi
    st.subheader(f"📋 Tabel Rekapitulasi Cakupan Layanan Kesehatan Balita ({periode_label})")
    if puskesmas_filter == "All":
        recap_df = merged_df.groupby('Puskesmas').sum().reset_index()
    else:
        recap_df = merged_df.groupby(['Puskesmas', 'Kelurahan']).sum().reset_index()

    # Hitung metrik dengan penanganan inf
    recap_df['Metrik Balita dipantau pertumbuhan dan perkembangan (%)'] = (recap_df['Jumlah_balita_pantau_tumbang'] / recap_df['Jumlah_balita_usia_12-59_bulan_sampai_bulan_ini'] * 100).replace([np.inf, -np.inf], 0).fillna(0).round(2)
    recap_df['Metrik balita yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)'] = (recap_df['Jumlah_balita_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi'] / recap_df['Jumlah_balita_terdeteksi_gangguan_tumbang'] * 100).replace([np.inf, -np.inf], 0).fillna(0).round(2)
    recap_df['Metrik balita mendapat pelayanan SDIDTK di Fasyankes (%)'] = (recap_df['Jumlah_balita_mendapat_pelayanan_SDIDTK_di_FKTP'] / recap_df['Jumlah_sasaran_balita'] * 100).replace([np.inf, -np.inf], 0).fillna(0).round(2)
    recap_df['Metrik Balita yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)'] = (recap_df['Jumlah_balita_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan'] / recap_df['Jumlah_balita_punya_KIA'] * 100).replace([np.inf, -np.inf], 0).fillna(0).round(2)
    recap_df['Metrik balita yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)'] = (recap_df['Jumlah_balita_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'] / recap_df['Jumlah_sasaran_balita'] * 100).replace([np.inf, -np.inf], 0).fillna(0).round(2)

    # Pastikan semua kunci di metrik_data ada di recap_df
    metrik_keys = list(metrik_data.keys())
    available_metrik_keys = [key for key in metrik_keys if key in recap_df.columns]

    recap_display = recap_df[['Puskesmas', 'Kelurahan'] + available_metrik_keys] if puskesmas_filter != "All" else recap_df[['Puskesmas'] + available_metrik_keys]
    recap_display.insert(0, 'No', range(1, len(recap_display) + 1))

    # Definisikan fungsi highlight untuk outlier > 100%
    def highlight_outliers(row):
        styles = [''] * len(row)
        targets = {
            'Metrik Balita dipantau pertumbuhan dan perkembangan (%)': 100,
            'Metrik balita yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)': 100,
            'Metrik balita mendapat pelayanan SDIDTK di Fasyankes (%)': 100,
            'Metrik Balita yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)': 100,
            'Metrik balita yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)': 100
        }
        for col in targets:
            if col in row.index and pd.notna(row[col]) and row[col] > targets[col]:
                idx = row.index.get_loc(col)
                styles[idx] = 'background-color: #FF6666; color: white;'
        return styles

    # Pastikan data numerik dan bulatkan ke 2 digit desimal
    cols_to_check = [
        'Metrik Balita dipantau pertumbuhan dan perkembangan (%)',
        'Metrik balita yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)',
        'Metrik balita mendapat pelayanan SDIDTK di Fasyankes (%)',
        'Metrik Balita yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)',
        'Metrik balita yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)'
    ]
    for col in cols_to_check:
        if col in recap_display.columns:
            recap_display[col] = pd.to_numeric(recap_display[col], errors='coerce').round(2)

    # Terapkan styling dan formatting
    styled_df = recap_display.style.apply(highlight_outliers, axis=1).format({
        'Metrik Balita dipantau pertumbuhan dan perkembangan (%)': "{:.2f}%",
        'Metrik balita yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)': "{:.2f}%",
        'Metrik balita mendapat pelayanan SDIDTK di Fasyankes (%)': "{:.2f}%",
        'Metrik Balita yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)': "{:.2f}%",
        'Metrik balita yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)': "{:.2f}%"
    }, na_rep="N/A", precision=2)

    # Render tabel dengan styling yang eksplisit
    st.write(styled_df, unsafe_allow_html=True)

    # Tambahkan notice di bawah tabel
    st.markdown(
        """
        <div style="background-color: #ADD8E6; padding: 10px; border-radius: 5px; color: black; font-size: 14px; font-family: Arial, sans-serif;">
            <strong>Catatan Penting:</strong> Nilai yang melebihi 100% (indikasi data outlier) telah dihighlight <span style="color: #FF6666; font-weight: bold;">Warna Merah</span>. Nilai <code>inf%</code> (infinity percent) terjadi ketika total balita atau balita dengan Buku KIA bernilai 0, dan telah diganti menjadi 0% untuk kejelasan. Untuk analisis lebih lanjut dan koreksi data, mohon dilakukan pemeriksaan pada <strong>Menu Daftar Entry</strong>.
        </div>
        """,
        unsafe_allow_html=True
    )

    # 4. 🚨 Tabel Deteksi Outlier (Logis)
    st.subheader(f"🚨 Tabel Deteksi Outlier ({periode_label})")
    # Mapping metrik ke kolom numerator dan denominator
    metric_to_columns = {
        "Metrik Balita dipantau pertumbuhan dan perkembangan (%)": ("Jumlah_balita_pantau_tumbang", "Jumlah_balita_usia_12-59_bulan_sampai_bulan_ini"),
        "Metrik balita yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)": ("Jumlah_balita_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi", "Jumlah_balita_terdeteksi_gangguan_tumbang"),
        "Metrik balita mendapat pelayanan SDIDTK di Fasyankes (%)": ("Jumlah_balita_mendapat_pelayanan_SDIDTK_di_FKTP", "Jumlah_sasaran_balita"),
        "Metrik Balita yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)": ("Jumlah_balita_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan", "Jumlah_balita_punya_KIA"),
        "Metrik balita yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)": ("Jumlah_balita_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita", "Jumlah_sasaran_balita")
    }

    # Inisialisasi DataFrame untuk outlier logis
    outliers_df = pd.DataFrame(columns=["Puskesmas", "Kelurahan", "Metrik", "Numerator", "Denominator", "Rasio", "Alasan"])

    # Deteksi outlier logis untuk setiap metrik
    for metric, (numerator_col, denominator_col) in metric_to_columns.items():
        # Kasus 1: Numerator > Denominator
        outlier_data_num = merged_df[
            (merged_df[numerator_col] > merged_df[denominator_col]) &
            (merged_df[denominator_col] != 0)
        ][["Puskesmas", "Kelurahan", numerator_col, denominator_col]]
        if not outlier_data_num.empty:
            outlier_data_num["Metrik"] = metric
            outlier_data_num["Numerator"] = outlier_data_num[numerator_col]
            outlier_data_num["Denominator"] = outlier_data_num[denominator_col]
            outlier_data_num["Rasio"] = (outlier_data_num[numerator_col] / outlier_data_num[denominator_col] * 100).round(2)
            outlier_data_num["Alasan"] = "Numerator > Denominator"
            outliers_df = pd.concat(
                [outliers_df, outlier_data_num[["Puskesmas", "Kelurahan", "Metrik", "Numerator", "Denominator", "Rasio", "Alasan"]]],
                ignore_index=True
            )

        # Kasus 2: Denominator = 0
        outlier_data_zero = merged_df[
            (merged_df[denominator_col] == 0) &
            (merged_df[numerator_col] > 0)
        ][["Puskesmas", "Kelurahan", numerator_col, denominator_col]]
        if not outlier_data_zero.empty:
            outlier_data_zero["Metrik"] = metric
            outlier_data_zero["Numerator"] = outlier_data_zero[numerator_col]
            outlier_data_zero["Denominator"] = outlier_data_zero[denominator_col]
            outlier_data_zero["Rasio"] = "Infinity"
            outlier_data_zero["Alasan"] = "Denominator = 0"
            outliers_df = pd.concat(
                [outliers_df, outlier_data_zero[["Puskesmas", "Kelurahan", "Metrik", "Numerator", "Denominator", "Rasio", "Alasan"]]],
                ignore_index=True
            )

    # Tampilkan Tabel Outlier Logis
    if not outliers_df.empty:
        styled_outliers = outliers_df.style.apply(
            lambda x: ['background-color: #FF6666; color: white;' if x['Alasan'] == "Numerator > Denominator" else 'background-color: #FF4500; color: white;'] * len(x),
            axis=1
        ).format({
            "Numerator": "{:.0f}",
            "Denominator": "{:.0f}",
            "Rasio": lambda x: f"{x:.2f}%" if isinstance(x, (int, float)) else x
        }).set_properties(**{
            'border': '1px solid black',
            'text-align': 'center',
            'font-size': '14px',
            'font-family': 'Arial, sans-serif'
        }).set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold')]},
            {'selector': 'caption', 'props': [('caption-side', 'top'), ('font-size', '18px'), ('font-weight', 'bold'), ('color', '#333')]},
        ]).set_caption("Tabel Outlier: Data dengan Numerator > Denominator atau Denominator = 0")

        st.write(styled_outliers, unsafe_allow_html=True)
    else:
        st.success("✅ Tidak ada outlier terdeteksi berdasarkan kriteria Numerator > Denominator atau Denominator = 0.")

    # 5. ⚙️ Analisis Outlier Statistik
    st.subheader(f"⚙️ Analisis Outlier Statistik ({periode_label})")
    # Gunakan recap_df yang sudah dihitung persentasenya
    cols_to_check = list(metrik_data.keys())

    # Inisialisasi DataFrame untuk outlier statistik
    base_columns = ["Puskesmas", "Metrik", "Nilai", "Metode"]
    if puskesmas_filter != "All":
        base_columns.insert(1, "Kelurahan")
    statistical_outliers_df = pd.DataFrame(columns=base_columns)

    # Dropdown untuk memilih metode deteksi outlier statistik
    outlier_method = st.selectbox(
        "Pilih Metode Deteksi Outlier Statistik",
        ["Tidak Ada", "Z-Score", "IQR"],
        key=f"outlier_method_select_balita_{periode_label}"
    )

    if outlier_method != "Tidak Ada":
        for metric in cols_to_check:
            if metric not in recap_df.columns:
                continue

            # Pilih kolom berdasarkan filter
            if puskesmas_filter == "All":
                metric_data = recap_df[[metric, "Puskesmas"]].dropna()
            else:
                metric_data = recap_df[[metric, "Puskesmas", "Kelurahan"]].dropna()

            if metric_data.empty:
                continue

            # Z-Score Method
            if outlier_method == "Z-Score":
                z_scores = stats.zscore(metric_data[metric], nan_policy='omit')
                z_outlier_mask = abs(z_scores) > 3  # Threshold Z-Score > 3
                z_outliers = metric_data[z_outlier_mask].copy()
                if not z_outliers.empty:
                    z_outliers["Metrik"] = metric
                    z_outliers["Nilai"] = z_outliers[metric]
                    z_outliers["Metode"] = "Z-Score"
                    if puskesmas_filter == "All":
                        z_outliers_subset = z_outliers[["Puskesmas", "Metrik", "Nilai", "Metode"]]
                    else:
                        z_outliers_subset = z_outliers[["Puskesmas", "Kelurahan", "Metrik", "Nilai", "Metode"]]
                    statistical_outliers_df = pd.concat(
                        [statistical_outliers_df, z_outliers_subset],
                        ignore_index=True
                    )

            # IQR Method
            elif outlier_method == "IQR":
                Q1 = metric_data[metric].quantile(0.25)
                Q3 = metric_data[metric].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                iqr_outlier_mask = (metric_data[metric] < lower_bound) | (metric_data[metric] > upper_bound)
                iqr_outliers = metric_data[iqr_outlier_mask].copy()
                if not iqr_outliers.empty:
                    iqr_outliers["Metrik"] = metric
                    iqr_outliers["Nilai"] = iqr_outliers[metric]
                    iqr_outliers["Metode"] = "IQR"
                    if puskesmas_filter == "All":
                        iqr_outliers_subset = iqr_outliers[["Puskesmas", "Metrik", "Nilai", "Metode"]]
                    else:
                        iqr_outliers_subset = iqr_outliers[["Puskesmas", "Kelurahan", "Metrik", "Nilai", "Metode"]]
                    statistical_outliers_df = pd.concat(
                        [statistical_outliers_df, iqr_outliers_subset],
                        ignore_index=True
                    )

    # 6. 📊 Tabel Outlier Statistik
    if not statistical_outliers_df.empty:
        st.markdown(f"### 📊 Tabel Outlier Statistik ({periode_label})")
        styled_stat_outliers = statistical_outliers_df.style.apply(
            lambda x: ['background-color: #FFA500; color: white;' if x['Metode'] == "Z-Score" else 'background-color: #FF8C00; color: white;'] * len(x),
            axis=1
        ).format({
            "Nilai": "{:.2f}%"
        }).set_properties(**{
            'border': '1px solid black',
            'text-align': 'center',
            'font-size': '14px',
            'font-family': 'Arial, sans-serif'
        }).set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#FF9800'), ('color', 'white'), ('font-weight', 'bold')]},
            {'selector': 'caption', 'props': [('caption-side', 'top'), ('font-size', '18px'), ('font-weight', 'bold'), ('color', '#333')]},
        ]).set_caption(f"Tabel Outlier Statistik ({outlier_method})")

        st.write(styled_stat_outliers, unsafe_allow_html=True)
    else:
        if outlier_method != "Tidak Ada":
            st.info(f"ℹ️ Tidak ada outlier statistik terdeteksi menggunakan metode {outlier_method}.")

    # 7. 📊 Visualisasi Outlier
    st.subheader(f"📊 Visualisasi Outlier ({periode_label})")
    show_outlier_viz = st.checkbox(
        "Tampilkan Visualisasi Outlier",
        value=False,
        key=f"balita_viz_toggle_{periode_label}"
    )

    if show_outlier_viz:
        # Gabungkan outlier logis dan statistik
        combined_outliers = outliers_df[["Puskesmas", "Kelurahan", "Metrik", "Rasio"]].copy()
        combined_outliers["Metode"] = "Logis (Numerator > Denominator atau Denominator = 0)"
        # Ganti "Infinity" dengan nilai besar untuk visualisasi
        combined_outliers["Rasio"] = combined_outliers["Rasio"].replace("Infinity", 9999)
        if not statistical_outliers_df.empty:
            stat_outliers = statistical_outliers_df[["Puskesmas", "Metrik", "Metode"]].copy()
            stat_outliers["Rasio"] = statistical_outliers_df["Nilai"]
            if "Kelurahan" in statistical_outliers_df.columns:
                stat_outliers["Kelurahan"] = statistical_outliers_df["Kelurahan"]
            else:
                stat_outliers["Kelurahan"] = "N/A"
            combined_outliers = pd.concat([combined_outliers, stat_outliers], ignore_index=True)

        if not combined_outliers.empty:
            viz_type = st.selectbox(
                "Pilih Tipe Visualisasi Outlier",
                ["Heatmap", "Grafik Batang", "Boxplot"],
                key=f"outlier_viz_select_balita_{periode_label}"
            )

            if viz_type == "Heatmap":
                pivot_df = combined_outliers.pivot_table(
                    index="Puskesmas",
                    columns="Metrik",
                    values="Rasio",
                    aggfunc="mean",
                    fill_value=0
                )
                fig_heatmap = px.imshow(
                    pivot_df,
                    text_auto=True,
                    aspect="auto",
                    title="Heatmap Distribusi Outlier per Puskesmas",
                    color_continuous_scale="Reds"
                )
                fig_heatmap.update_layout(
                    xaxis_title="Metrik",
                    yaxis_title="Puskesmas",
                    coloraxis_colorbar_title="Rasio (%)"
                )
                st.plotly_chart(fig_heatmap, use_container_width=True)

            elif viz_type == "Grafik Batang":
                count_df = combined_outliers.groupby(["Metrik", "Metode"]).size().reset_index(name="Jumlah")
                fig_bar = px.bar(
                    count_df,
                    x="Metrik",
                    y="Jumlah",
                    color="Metode",
                    barmode="group",
                    title="Jumlah Outlier per Metrik dan Metode Deteksi",
                    text="Jumlah"
                )
                fig_bar.update_traces(textposition="outside")
                fig_bar.update_layout(
                    xaxis_title="Metrik",
                    yaxis_title="Jumlah Outlier",
                    xaxis_tickangle=45,
                    legend_title="Metode Deteksi"
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            elif viz_type == "Boxplot":
                fig_box = px.box(
                    combined_outliers,
                    x="Metrik",
                    y="Rasio",
                    color="Metode",
                    title="Boxplot Distribusi Outlier per Metrik dan Metode Deteksi",
                    points="all"
                )
                fig_box.update_layout(
                    xaxis_title="Metrik",
                    yaxis_title="Rasio (%)",
                    xaxis_tickangle=45,
                    legend_title="Metode Deteksi"
                )
                st.plotly_chart(fig_box, use_container_width=True)
        else:
            st.info("ℹ️ Tidak ada data outlier untuk divisualisasikan.")
    # 8. 📈 Tren Metrik
    st.subheader(f"📈 Tren Metrik ({periode_label})")
    metric_list = list(metrik_data.keys())
    # Hitung metrik per bulan
    trend_df = merged_df.copy()
    trend_df['Metrik Balita dipantau pertumbuhan dan perkembangan (%)'] = (trend_df['Jumlah_balita_pantau_tumbang'] / trend_df['Jumlah_balita_usia_12-59_bulan_sampai_bulan_ini'] * 100).replace([np.inf, -np.inf], 0).fillna(0)
    trend_df['Metrik balita yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)'] = (trend_df['Jumlah_balita_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi'] / trend_df['Jumlah_balita_terdeteksi_gangguan_tumbang'] * 100).replace([np.inf, -np.inf], 0).fillna(0)
    trend_df['Metrik balita mendapat pelayanan SDIDTK di Fasyankes (%)'] = (trend_df['Jumlah_balita_mendapat_pelayanan_SDIDTK_di_FKTP'] / trend_df['Jumlah_balita_usia_12-59_bulan_sampai_bulan_ini'] * 100).replace([np.inf, -np.inf], 0).fillna(0)
    trend_df['Metrik Balita yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)'] = (trend_df['Jumlah_balita_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan'] / trend_df['Jumlah_balita_punya_KIA'] * 100).replace([np.inf, -np.inf], 0).fillna(0)
    trend_df['Metrik balita yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)'] = (trend_df['Jumlah_balita_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'] / trend_df['Jumlah_balita_usia_12-59_bulan_sampai_bulan_ini'] * 100).replace([np.inf, -np.inf], 0).fillna(0)

    # Filter dan agregasi data berdasarkan Bulan
    trend_df = trend_df.groupby("Bulan")[metric_list].mean().reset_index()
    trend_df = trend_df.melt(
        id_vars="Bulan",
        value_vars=metric_list,
        var_name="Metrik",
        value_name="Persentase"
    )

    # Bulatkan kolom Persentase menjadi 2 digit desimal
    trend_df["Persentase"] = trend_df["Persentase"].round(2)

    # Tampilkan line chart untuk semua metrik
    if not trend_df.empty:
        fig_trend = px.line(
            trend_df,
            x="Bulan",
            y="Persentase",
            color="Metrik",
            markers=True,
            text=trend_df["Persentase"].apply(lambda x: f"{x:.2f}"),
            title="📈 Tren Metrik Cakupan Layanan Kesehatan Balita dari Awal hingga Akhir Bulan"
        )
        fig_trend.update_traces(textposition="top center")
        fig_trend.update_layout(
            xaxis_title="Bulan",
            yaxis_title="Persentase (%)",
            xaxis=dict(tickmode='linear', tick0=1, dtick=1),
            yaxis_range=[0, 100],
            legend_title="Metrik",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(
            fig_trend,
            key=f"balita_trend_chart_{puskesmas_filter}_{kelurahan_filter}_{time.time()}",
            use_container_width=True
        )
    else:
        st.warning("⚠️ Tidak ada data untuk ditampilkan pada grafik tren Cakupan Layanan Kesehatan Balita.")

    # 9. 📊 Analisis Komparasi Antar Wilayah
    st.subheader(f"📊 Analisis Komparasi Antar Wilayah ({periode_label})")
    # Dropdown untuk memilih metrik yang ingin dibandingkan
    selected_metric = st.selectbox(
        "Pilih Metrik untuk Komparasi Antar Wilayah",
        metric_list,
        key="comp_metric_select_balita"
    )

    # Filter data berdasarkan metrik yang dipilih
    comp_df = recap_df.groupby(["Puskesmas", "Kelurahan"])[selected_metric].mean().reset_index()
    if not comp_df.empty:
        fig_comp = px.bar(
            comp_df,
            x="Puskesmas",
            y=selected_metric,
            color="Kelurahan",
            title=f"📊 Komparasi {selected_metric} Antar Wilayah",
            text=comp_df[selected_metric].apply(lambda x: f"{x:.2f}%"),
            height=400
        )
        fig_comp.update_traces(textposition="outside")
        fig_comp.update_layout(
            xaxis_title="Puskesmas",
            yaxis_title="Persentase (%)",
            xaxis_tickangle=45,
            yaxis_range=[0, 100],
            legend_title="Kelurahan"
        )
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.warning("⚠️ Tidak ada data untuk komparasi antar wilayah.")

    # 10. 🔍 Analisis Korelasi Antar Metrik
    st.subheader(f"🔍 Analisis Korelasi Antar Metrik ({periode_label})")
    # Hitung korelasi antar metrik menggunakan data agregat per Puskesmas/Kelurahan
    corr_df = recap_df.groupby(["Puskesmas", "Kelurahan"])[metric_list].mean().reset_index()
    if len(corr_df) > 1:  # Pastikan ada cukup data untuk korelasi
        correlation_matrix = corr_df[metric_list].corr()
        fig_corr = px.imshow(
            correlation_matrix,
            text_auto=True,
            aspect="auto",
            title="🔍 Matriks Korelasi Antar Metrik Cakupan Layanan Kesehatan Balita",
            color_continuous_scale="RdBu",
            range_color=[-1, 1]
        )
        fig_corr.update_layout(
            xaxis_title="Metrik",
            yaxis_title="Metrik",
            coloraxis_colorbar_title="Koefisien Korelasi"
        )
        st.plotly_chart(fig_corr, use_container_width=True)
        st.markdown("**Catatan:** Nilai mendekati 1 atau -1 menunjukkan korelasi kuat (positif atau negatif), sementara 0 menunjukkan tidak ada korelasi.")
    else:
        st.warning("⚠️ Tidak cukup data untuk menghitung korelasi antar metrik.")

    # 11. 📅 Analisis Perubahan Persentase (Growth/Decline)
    st.subheader(f"📅 Analisis Perubahan Persentase (Growth/Decline) ({periode_label})")
    # Pastikan data tren sudah ada
    if not trend_df.empty:
        # Hitung perubahan persentase dari bulan ke bulan
        trend_df = trend_df.sort_values("Bulan")
        trend_df["Perubahan Persentase"] = trend_df.groupby("Metrik")["Persentase"].pct_change() * 100
        trend_df["Perubahan Persentase"] = trend_df["Perubahan Persentase"].round(2)

        # Tampilkan tabel perubahan
        st.dataframe(
            trend_df[["Bulan", "Metrik", "Persentase", "Perubahan Persentase"]].style.format({
                "Persentase": "{:.2f}%",
                "Perubahan Persentase": "{:.2f}%"
            }).set_properties(**{
                'text-align': 'center',
                'font-size': '14px',
                'border': '1px solid black'
            }).set_table_styles([
                {'selector': 'th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold')]},
                {'selector': 'caption', 'props': [('caption-side', 'top'), ('font-size', '18px'), ('font-weight', 'bold'), ('color', '#333')]},
            ]).set_caption("📅 Tabel Perubahan Persentase Antar Bulan"),
            use_container_width=True
        )

        # Visualisasi perubahan dengan grafik garis
        fig_change = px.line(
            trend_df,
            x="Bulan",
            y="Perubahan Persentase",
            color="Metrik",
            markers=True,
            text=trend_df["Perubahan Persentase"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else ""),
            title="📅 Tren Perubahan Persentase Metrik Cakupan Layanan Kesehatan Balita"
        )
        fig_change.update_traces(textposition="top center")
        fig_change.update_layout(
            xaxis_title="Bulan",
            yaxis_title="Perubahan Persentase (%)",
            xaxis=dict(tickmode='linear', tick0=1, dtick=1),
            legend_title="Metrik",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_change, use_container_width=True)
    else:
        st.warning("⚠️ Tidak ada data untuk menganalisis perubahan persentase.")

    # 12. 📉 Analisis Distribusi Data (Histogram)
    st.subheader(f"📉 Analisis Distribusi Data (Histogram) ({periode_label})")
    # Dropdown untuk memilih metrik yang ingin dianalisis distribusinya
    selected_metric_dist = st.selectbox(
        "Pilih Metrik untuk Analisis Distribusi",
        metric_list,
        key="dist_metric_select_balita"
    )

    # Buat histogram berdasarkan data per Puskesmas/Kelurahan
    dist_df = recap_df.groupby(["Puskesmas", "Kelurahan"])[selected_metric_dist].mean().reset_index()
    if not dist_df.empty:
        fig_dist = px.histogram(
            dist_df,
            x=selected_metric_dist,
            nbins=20,
            title=f"📉 Distribusi {selected_metric_dist} di Seluruh Wilayah",
            labels={"value": "Persentase (%)", "count": "Jumlah Wilayah"},
            height=400
        )
        fig_dist.update_layout(
            xaxis_title="Persentase (%)",
            yaxis_title="Jumlah Wilayah",
            bargap=0.1
        )
        st.plotly_chart(fig_dist, use_container_width=True)
        # Tambahan statistik dasar
        mean_val = dist_df[selected_metric_dist].mean().round(2)
        median_val = dist_df[selected_metric_dist].median().round(2)
        st.markdown(f"**Statistik Distribusi:** Rata-rata = {mean_val}%, Median = {median_val}%")
    else:
        st.warning("⚠️ Tidak ada data untuk analisis distribusi.")


    # 4. Fitur Download Laporan PDF
    st.subheader("📥 Unduh Laporan")
    def generate_pdf_report(figures_list):
        # Buat buffer untuk menyimpan grafik
        img_buffers = []
        for fig in figures_list:
            img_buffer = BytesIO()
            fig.write_image(img_buffer, format='png', width=600, height=400, scale=2)
            img_buffer.seek(0)
            img_buffers.append(img_buffer)

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
        elements.append(Paragraph(f"Laporan Cakupan Layanan Kesehatan Balita ({periode_label})", title_style))
        elements.append(Paragraph(f"Diperbarui: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
        elements.append(Spacer(1, 12))

        # Tambahkan Metrik
        elements.append(Paragraph("1. Metrik Cakupan", normal_style))
        metric_data = [[f"{label}: {value:.2f}%" for label, value in metrik_list]]
        metric_table = Table(metric_data, colWidths=[300])
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
        for i, metric in enumerate(metrics):
            elements.append(Paragraph(f"2.{i+1}. Grafik {metric}", normal_style))
            elements.append(Image(img_buffers[i], width=500, height=300))
            elements.append(Spacer(1, 12))

        # Tambahkan Tabel Rekapitulasi
        elements.append(Paragraph(f"3. Tabel Rekapitulasi", normal_style))
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

    if st.button("Download Laporan PDF", key=f"download_cakupan_layanan_kesehatan_balita_{periode_label}"):
        st.warning("Membuat laporan PDF, harap tunggu...")
        pdf_data = generate_pdf_report(figures_list)
        st.success("Laporan PDF siap diunduh!")
        st.download_button(
            label="Download Laporan PDF",
            data=pdf_data,
            file_name=f"Laporan_Cakupan_Layanan_Kesehatan_Balita_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )
# ----------------------------- #
# 🏡 Cakupan Layanan Kesehatan Apras
# ----------------------------- #
def cakupan_layanan_kesehatan_apras(filtered_df, desa_df, puskesmas_filter, kelurahan_filter, jenis_laporan, tahun_filter, bulan_filter_int=None, tribulan_filter=None):
    """Menampilkan analisis Cakupan Layanan Kesehatan Apras dengan fitur download laporan."""
    st.header("🏡 Cakupan Layanan Kesehatan Apras")
    # Informasi Metrik Cakupan Layanan Kesehatan Apras
    with st.expander("📜 Definisi dan Insight Analisis Cakupan Layanan Kesehatan Apras", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Analisis Indikator

            Berikut adalah definisi operasional, rumus perhitungan, serta analisis insight dari indikator-indikator yang digunakan untuk memantau cakupan layanan kesehatan anak prasekolah (Apras) dalam kerangka Surveilans Deteksi Dini Tumbuh Kembang (SDIDTK) dan pedoman pemantauan pertumbuhan versi terbaru, diperbarui hingga Mei 2025. Rumus disajikan dalam format matematis untuk kejelasan, dengan penjelasan sederhana untuk mendukung pemahaman petugas kesehatan.

            #### 1. Persentase Apras Terdeteksi Gangguan atau Penyimpangan Perkembangan yang Mendapat Intervensi
            - **Definisi Operasional:** Persentase anak prasekolah (Apras) yang terdeteksi memiliki gangguan atau penyimpangan perkembangan dan mendapatkan intervensi terhadap total Apras yang terdeteksi gangguan pada bulan pelaporan, sesuai pedoman SDIDTK.  
            - **Rumus Perhitungan:**  
            $$ \\text{Metrik Apras terdeteksi gangguan yang mendapat intervensi (\\%)} = \\frac{\\text{Jumlah Apras terdeteksi gangguan yang mendapat intervensi}}{\\text{Total Apras terdeteksi gangguan}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen Apras yang mendapat intervensi dari total Apras yang terdeteksi memiliki gangguan, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data diambil dari laporan bulanan posyandu atau puskesmas, dengan pencatatan jumlah Apras yang terdeteksi gangguan melalui skrining KPSP (Kuesioner Pra Skrining Perkembangan) dan yang mendapat intervensi seperti rujukan atau stimulasi perkembangan.  
            - **Insight Analisis:** Persentase di bawah 90% (target SDIDTK 2025) menunjukkan rendahnya tindak lanjut intervensi. Koordinasi dengan tenaga kesehatan untuk rujukan dini dan pelatihan stimulasi perkembangan dapat meningkatkan angka ini, mencegah dampak jangka panjang seperti keterlambatan perkembangan kognitif, yang masih menjadi perhatian berdasarkan laporan Kementerian Kesehatan 2024.

            #### 2. Persentase Apras Mendapat Pelayanan SDIDTK di Fasilitas Kesehatan Primer (FKTP)
            - **Definisi Operasional:** Persentase anak prasekolah (Apras) yang mendapatkan pelayanan SDIDTK di fasilitas kesehatan primer (FKTP) terhadap total Apras pada bulan pelaporan, sesuai pedoman SDIDTK.  
            - **Rumus Perhitungan:**  
            $$ \\text{Metrik Apras mendapat pelayanan SDIDTK di Fasyankes (\\%)} = \\frac{\\text{Jumlah Apras mendapat pelayanan SDIDTK di FKTP}}{\\text{Total Apras}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen Apras yang mendapat pelayanan SDIDTK di FKTP dari total Apras pada bulan tersebut, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui laporan bulanan puskesmas, dengan pencatatan jumlah Apras yang mendapatkan pelayanan SDIDTK di FKTP seperti puskesmas atau posyandu terintegrasi.  
            - **Insight Analisis:** Persentase di bawah 80% (target SDIDTK 2025) dapat mengindikasikan rendahnya akses ke layanan FKTP. Peningkatan integrasi posyandu dengan puskesmas dan penyediaan tenaga kesehatan terlatih dapat meningkatkan cakupan layanan ini, mendukung pemantauan pertumbuhan seperti pencegahan wasting.

            #### 3. Persentase Apras yang Buku KIA-nya Terisi Lengkap Bagian Pemantauan Perkembangan
            - **Definisi Operasional:** Persentase anak prasekolah (Apras) yang Buku KIA-nya terisi lengkap pada bagian pemantauan perkembangan terhadap total Apras yang memiliki Buku KIA pada bulan pelaporan, sesuai pedoman SDIDTK.  
            - **Rumus Perhitungan:**  
            $$ \\text{Metrik Apras yang Buku KIA terisi lengkap (\\%)} = \\frac{\\text{Jumlah Apras dengan Buku KIA terisi lengkap}}{\\text{Total Apras yang punya Buku KIA}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen Apras yang Buku KIA-nya terisi lengkap dari total Apras yang memiliki Buku KIA, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data diambil dari laporan bulanan posyandu atau puskesmas, dengan verifikasi kelengkapan pengisian Buku KIA pada bagian pemantauan perkembangan oleh tenaga kesehatan.  
            - **Insight Analisis:** Persentase di bawah 90% (target SDIDTK 2025) dapat menunjukkan kurangnya konsistensi dalam pengisian Buku KIA. Pelatihan kader dan edukasi orang tua tentang pentingnya dokumentasi dapat meningkatkan kepatuhan pengisian, mendukung pemantauan pertumbuhan dan perkembangan yang berkelanjutan.

            #### 4. Persentase Apras yang Ibu/Orang Tua/Wali/Keluarga/Pengasuh Mengikuti Minimal 4 Kali Kelas Ibu Balita
            - **Definisi Operasional:** Persentase anak prasekolah (Apras) yang ibu/orang tua/wali/keluarga/pengasuhnya telah mengikuti minimal 4 kali kelas ibu balita terhadap total Apras pada bulan pelaporan, sesuai pedoman SDIDTK.  
            - **Rumus Perhitungan:**  
            $$ \\text{Metrik Apras yang ibu mengikuti kelas ibu balita (\\%)} = \\frac{\\text{Jumlah Apras yang ibu mengikuti minimal 4 kali kelas}}{\\text{Total Apras}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen Apras yang ibunya mengikuti minimal 4 kali kelas ibu balita dari total Apras pada bulan tersebut, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui laporan bulanan posyandu, dengan pencatatan kehadiran ibu/orang tua dalam kelas ibu balita yang diselenggarakan oleh posyandu atau puskesmas.  
            - **Insight Analisis:** Persentase di bawah 70% (target SDIDTK 2025) dapat mengindikasikan rendahnya partisipasi orang tua dalam kelas edukasi. Peningkatan jadwal kelas yang fleksibel dan sosialisasi manfaat kelas ibu balita dapat meningkatkan partisipasi, yang penting untuk edukasi gizi dan stimulasi perkembangan Apras.

            </div>
        """, unsafe_allow_html=True)

    # Inisialisasi periode untuk label
    periode_label = ""
    if tahun_filter != "All":
        periode_label += f"Tahun {tahun_filter}"
    if jenis_laporan == "Bulanan" and bulan_filter_int is not None:
        periode_label += f" Bulan {bulan_filter_int}" if periode_label else f"Bulan {bulan_filter_int}"
    elif jenis_laporan == "Tahunan" and tribulan_filter:
        periode_label += f" {tribulan_filter}" if periode_label else tribulan_filter

    # 1. Memuat data Jumlah_apras dari dataset_apras
    try:
        conn = sqlite3.connect("rcs_data.db")
        apras_df = pd.read_sql_query("SELECT Puskesmas, Kelurahan, Tahun, Jumlah_apras FROM dataset_apras", conn)
        conn.close()
    except Exception as e:
        st.error(f"❌ Gagal memuat data dari dataset_apras: {e}")
        return

    # Daftar kolom yang dibutuhkan dari filtered_df (data utama, misalnya data_apras_kia)
    required_columns = [
        'Jumlah_Apras_terdeteksi_gangguan_tumbang',
        'Jumlah_Apras_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi',
        'Jumlah_Apras_mendapat_pelayanan_SDIDTK_di_FKTP',
        'Jumlah_anak_prasekolah_bulan_ini',
        'Jumlah_Apras_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan',
        'Jumlah_anak_prasekolah_punya_Buku_KIA',
        'Jumlah_Apras_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'
    ]

    # Cek apakah semua kolom ada di filtered_df
    missing_cols = [col for col in required_columns if col not in filtered_df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di dataset: {missing_cols}. Periksa data di 'data_apras_kia'!")
        return

    # Pastikan tipe data Tahun sama
    filtered_df['Tahun'] = filtered_df['Tahun'].astype(int)
    if 'Tahun' in apras_df.columns:
        apras_df['Tahun'] = apras_df['Tahun'].astype(int)

    # Agregasi data berdasarkan jenis laporan
    if jenis_laporan == "Tahunan" and not filtered_df.empty:
        group_columns = ["Puskesmas", "Kelurahan"]
        numeric_columns = [col for col in filtered_df.columns if filtered_df[col].dtype in ['int64', 'float64']]
        if numeric_columns:
            agg_dict = {col: "sum" for col in numeric_columns}
            filtered_df = filtered_df.groupby(group_columns).agg(agg_dict).reset_index()

    # Gabungkan data dari filtered_df dengan dataset_apras untuk mendapatkan Jumlah_apras (berdasarkan Puskesmas, Kelurahan, Tahun)
    merged_df = pd.merge(
        filtered_df,
        apras_df[['Puskesmas', 'Kelurahan', 'Tahun', 'Jumlah_apras']],
        on=['Puskesmas', 'Kelurahan', 'Tahun'],
        how='left'
    )

    # Cek apakah ada data yang tidak match
    if merged_df['Jumlah_apras'].isna().all():
        st.warning("⚠️ Tidak ada data Jumlah_apras yang cocok dengan filter Puskesmas, Kelurahan, dan Tahun. Periksa data di dataset_apras!")
        return

    # Hitung total Apras dan total terdeteksi gangguan
    total_apras = merged_df['Jumlah_apras'].sum()  # Gunakan Jumlah_apras dari dataset_apras
    total_deteksi_gangguan = filtered_df['Jumlah_Apras_terdeteksi_gangguan_tumbang'].sum()
    total_apras_dengan_buku_kia = filtered_df['Jumlah_anak_prasekolah_punya_Buku_KIA'].sum()

    if total_apras == 0:
        st.warning("⚠️ Tidak ada data anak prasekolah untuk filter ini.")
        return
    if total_deteksi_gangguan == 0 and 'Jumlah_Apras_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi' in required_columns:
        st.warning("⚠️ Tidak ada data Apras terdeteksi gangguan untuk filter ini.")
    if total_apras_dengan_buku_kia == 0 and 'Jumlah_Apras_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan' in required_columns:
        st.warning("⚠️ Tidak ada data Apras dengan Buku KIA untuk filter ini.")

    # Hitung metrik
    metrik_data = {
        "Metrik Apras yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)": (filtered_df['Jumlah_Apras_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi'].sum() / total_deteksi_gangguan * 100 if total_deteksi_gangguan else 0),
        "Metrik Apras mendapat pelayanan SDIDTK di Fasyankes (%)": (filtered_df['Jumlah_Apras_mendapat_pelayanan_SDIDTK_di_FKTP'].sum() / total_apras * 100 if total_apras else 0),
        "Metrik Apras yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)": (filtered_df['Jumlah_Apras_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan'].sum() / total_apras_dengan_buku_kia * 100 if total_apras_dengan_buku_kia else 0),
        "Metrik Apras yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)": (filtered_df['Jumlah_Apras_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'].sum() / total_apras * 100 if total_apras else 0)
    }

    # 1. Metrik Score Card
    st.subheader(f"📊 Metrik Cakupan Layanan Kesehatan Apras ({periode_label})")
    metrik_list = list(metrik_data.items())
    cols = st.columns(2)  # 2 kolom
    for i in range(2):
        if i < len(metrik_list):
            label, value = metrik_list[i]
            cols[i].metric(label=label, value=f"{value:.2f}%")
    for i in range(2, len(metrik_list)):
        label, value = metrik_list[i]
        cols[i % 2].metric(label=label, value=f"{value:.2f}%")

    # 2. Grafik Visualisasi (4 grafik terpisah per metrik)
    st.subheader(f"📈 Grafik Cakupan Layanan Kesehatan Apras ({periode_label})")
    metrics = list(metrik_data.keys())
    figures_list = []  # Daftar untuk menyimpan semua objek fig
    for metric in metrics:
        if puskesmas_filter == "All":
            grouped_df = merged_df.groupby('Puskesmas').sum().reset_index()
            if metric == "Metrik Apras yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)":
                graph_data = pd.DataFrame({
                    "Puskesmas": grouped_df['Puskesmas'],
                    metric: (grouped_df['Jumlah_Apras_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi'] / grouped_df['Jumlah_Apras_terdeteksi_gangguan_tumbang'] * 100).fillna(0)
                })
            elif metric == "Metrik Apras mendapat pelayanan SDIDTK di Fasyankes (%)":
                graph_data = pd.DataFrame({
                    "Puskesmas": grouped_df['Puskesmas'],
                    metric: (grouped_df['Jumlah_Apras_mendapat_pelayanan_SDIDTK_di_FKTP'] / grouped_df['Jumlah_apras'] * 100).fillna(0)
                })
            elif metric == "Metrik Apras yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)":
                graph_data = pd.DataFrame({
                    "Puskesmas": grouped_df['Puskesmas'],
                    metric: (grouped_df['Jumlah_Apras_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan'] / grouped_df['Jumlah_anak_prasekolah_punya_Buku_KIA'] * 100).fillna(0)
                })
            elif metric == "Metrik Apras yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)":
                graph_data = pd.DataFrame({
                    "Puskesmas": grouped_df['Puskesmas'],
                    metric: (grouped_df['Jumlah_Apras_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'] / grouped_df['Jumlah_apras'] * 100).fillna(0)
                })
            fig = px.bar(graph_data, x="Puskesmas", y=metric, text=graph_data[metric].apply(lambda x: f"{x:.1f}%"),
                        title=f"{metric} per Puskesmas ({periode_label})", color_discrete_sequence=["#32CD32"])
        else:
            grouped_df = merged_df.groupby('Kelurahan').sum().reset_index()
            if metric == "Metrik Apras yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)":
                graph_data = pd.DataFrame({
                    "Kelurahan": grouped_df['Kelurahan'],
                    metric: (grouped_df['Jumlah_Apras_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi'] / grouped_df['Jumlah_Apras_terdeteksi_gangguan_tumbang'] * 100).fillna(0)
                })
            elif metric == "Metrik Apras mendapat pelayanan SDIDTK di Fasyankes (%)":
                graph_data = pd.DataFrame({
                    "Kelurahan": grouped_df['Kelurahan'],
                    metric: (grouped_df['Jumlah_Apras_mendapat_pelayanan_SDIDTK_di_FKTP'] / grouped_df['Jumlah_apras'] * 100).fillna(0)
                })
            elif metric == "Metrik Apras yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)":
                graph_data = pd.DataFrame({
                    "Kelurahan": grouped_df['Kelurahan'],
                    metric: (grouped_df['Jumlah_Apras_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan'] / grouped_df['Jumlah_anak_prasekolah_punya_Buku_KIA'] * 100).fillna(0)
                })
            elif metric == "Metrik Apras yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)":
                graph_data = pd.DataFrame({
                    "Kelurahan": grouped_df['Kelurahan'],
                    metric: (grouped_df['Jumlah_Apras_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'] / grouped_df['Jumlah_apras'] * 100).fillna(0)
                })
            fig = px.bar(graph_data, x="Kelurahan", y=metric, text=graph_data[metric].apply(lambda x: f"{x:.1f}%"),
                        title=f"{metric} per Kelurahan di {puskesmas_filter} ({periode_label})", color_discrete_sequence=["#32CD32"])

        fig.update_traces(textposition='outside')
        fig.add_hline(
            y=100,
            line_dash="dash",
            line_color="red",
            annotation_text="Target: 100%",
            annotation_position="top right"
        )
        fig.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", yaxis_range=[0, 100], title_x=0.5,
                        height=400)
        st.plotly_chart(fig, use_container_width=True)
        figures_list.append(fig)  # Simpan setiap fig ke daftar

    # 3. Tabel Rekapitulasi
    st.subheader(f"📋 Tabel Rekapitulasi Cakupan Layanan Kesehatan Apras ({periode_label})")
    if puskesmas_filter == "All":
        recap_df = merged_df.groupby('Puskesmas').sum().reset_index()
    else:
        recap_df = merged_df.groupby(['Puskesmas', 'Kelurahan']).sum().reset_index()

    # Hitung metrik dengan penanganan inf
    recap_df['Metrik Apras yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)'] = (recap_df['Jumlah_Apras_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi'] / recap_df['Jumlah_Apras_terdeteksi_gangguan_tumbang'] * 100).replace([np.inf, -np.inf], 0).fillna(0).round(2)
    recap_df['Metrik Apras mendapat pelayanan SDIDTK di Fasyankes (%)'] = (recap_df['Jumlah_Apras_mendapat_pelayanan_SDIDTK_di_FKTP'] / recap_df['Jumlah_apras'] * 100).replace([np.inf, -np.inf], 0).fillna(0).round(2)
    recap_df['Metrik Apras yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)'] = (recap_df['Jumlah_Apras_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan'] / recap_df['Jumlah_anak_prasekolah_punya_Buku_KIA'] * 100).replace([np.inf, -np.inf], 0).fillna(0).round(2)
    recap_df['Metrik Apras yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)'] = (recap_df['Jumlah_Apras_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'] / recap_df['Jumlah_apras'] * 100).replace([np.inf, -np.inf], 0).fillna(0).round(2)

    # Pastikan semua kunci di metrik_data ada di recap_df
    metrik_keys = list(metrik_data.keys())
    available_metrik_keys = [key for key in metrik_keys if key in recap_df.columns]

    recap_display = recap_df[['Puskesmas', 'Kelurahan'] + available_metrik_keys] if puskesmas_filter != "All" else recap_df[['Puskesmas'] + available_metrik_keys]
    recap_display.insert(0, 'No', range(1, len(recap_display) + 1))

    # Definisikan fungsi highlight untuk outlier > 100%
    def highlight_outliers(row):
        styles = [''] * len(row)
        targets = {
            'Metrik Apras yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)': 100,
            'Metrik Apras mendapat pelayanan SDIDTK di Fasyankes (%)': 100,
            'Metrik Apras yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)': 100,
            'Metrik Apras yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)': 100
        }
        for col in targets:
            if col in row.index and pd.notna(row[col]) and row[col] > targets[col]:
                idx = row.index.get_loc(col)
                styles[idx] = 'background-color: #FF6666; color: white;'
        return styles

    # Pastikan data numerik dan bulatkan ke 2 digit desimal
    cols_to_check = [
        'Metrik Apras yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)',
        'Metrik Apras mendapat pelayanan SDIDTK di Fasyankes (%)',
        'Metrik Apras yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)',
        'Metrik Apras yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)'
    ]
    for col in cols_to_check:
        if col in recap_display.columns:
            recap_display[col] = pd.to_numeric(recap_display[col], errors='coerce').round(2)

    # Terapkan styling dan formatting
    styled_df = recap_display.style.apply(highlight_outliers, axis=1).format({
        'Metrik Apras yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)': "{:.2f}%",
        'Metrik Apras mendapat pelayanan SDIDTK di Fasyankes (%)': "{:.2f}%",
        'Metrik Apras yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)': "{:.2f}%",
        'Metrik Apras yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)': "{:.2f}%"
    }, na_rep="N/A", precision=2)

    # Render tabel dengan styling yang eksplisit
    st.write(styled_df, unsafe_allow_html=True)

    # Tambahkan notice di bawah tabel
    st.markdown(
        """
        <div style="background-color: #ADD8E6; padding: 10px; border-radius: 5px; color: black; font-size: 14px; font-family: Arial, sans-serif;">
            <strong>Catatan Penting:</strong> Nilai yang melebihi 100% (indikasi data outlier) telah dihighlight <span style="color: #FF6666; font-weight: bold;">Warna Merah</span>. Nilai <code>inf%</code> (infinity percent) terjadi ketika total Apras atau Apras dengan Buku KIA bernilai 0, dan telah diganti menjadi 0% untuk kejelasan. Untuk analisis lebih lanjut dan koreksi data, mohon dilakukan pemeriksaan pada <strong>Menu Daftar Entry</strong>.
        </div>
        """,
        unsafe_allow_html=True
    )

    # 4. 🚨 Tabel Deteksi Outlier
    st.subheader(f"🚨 Tabel Deteksi Outlier ({periode_label})")
    # Mapping metrik ke kolom numerator dan denominator
    metric_to_columns = {
        "Metrik Apras yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)": ("Jumlah_Apras_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi", "Jumlah_Apras_terdeteksi_gangguan_tumbang"),
        "Metrik Apras mendapat pelayanan SDIDTK di Fasyankes (%)": ("Jumlah_Apras_mendapat_pelayanan_SDIDTK_di_FKTP", "Jumlah_apras"),
        "Metrik Apras yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)": ("Jumlah_Apras_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan", "Jumlah_anak_prasekolah_punya_Buku_KIA"),
        "Metrik Apras yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)": ("Jumlah_Apras_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita", "Jumlah_apras")
    }

    # Inisialisasi DataFrame untuk outlier logis
    outliers_df = pd.DataFrame(columns=["Puskesmas", "Kelurahan", "Metrik", "Numerator", "Denominator", "Rasio", "Alasan"])

    # Deteksi outlier logis untuk setiap metrik
    for metric, (numerator_col, denominator_col) in metric_to_columns.items():
        # Kasus 1: Numerator > Denominator
        outlier_data_num = merged_df[
            (merged_df[numerator_col] > merged_df[denominator_col]) &
            (merged_df[denominator_col] != 0)
        ][["Puskesmas", "Kelurahan", numerator_col, denominator_col]]
        if not outlier_data_num.empty:
            outlier_data_num["Metrik"] = metric
            outlier_data_num["Numerator"] = outlier_data_num[numerator_col]
            outlier_data_num["Denominator"] = outlier_data_num[denominator_col]
            outlier_data_num["Rasio"] = (outlier_data_num[numerator_col] / outlier_data_num[denominator_col] * 100).round(2)
            outlier_data_num["Alasan"] = "Numerator > Denominator"
            outliers_df = pd.concat([outliers_df, outlier_data_num[["Puskesmas", "Kelurahan", "Metrik", "Numerator", "Denominator", "Rasio", "Alasan"]]], ignore_index=True)

        # Kasus 2: Denominator = 0
        outlier_data_zero = merged_df[
            (merged_df[denominator_col] == 0) &
            (merged_df[numerator_col] > 0)
        ][["Puskesmas", "Kelurahan", numerator_col, denominator_col]]
        if not outlier_data_zero.empty:
            outlier_data_zero["Metrik"] = metric
            outlier_data_zero["Numerator"] = outlier_data_zero[numerator_col]
            outlier_data_zero["Denominator"] = outlier_data_zero[denominator_col]
            outlier_data_zero["Rasio"] = "Infinity"
            outlier_data_zero["Alasan"] = "Denominator = 0"
            outliers_df = pd.concat([outliers_df, outlier_data_zero[["Puskesmas", "Kelurahan", "Metrik", "Numerator", "Denominator", "Rasio", "Alasan"]]], ignore_index=True)

    # Tampilkan Tabel Outlier Logis
    if not outliers_df.empty:
        styled_outliers = outliers_df.style.apply(
            lambda x: ['background-color: #FF6666; color: white;' if x['Alasan'] == "Numerator > Denominator" else 'background-color: #FF4500; color: white;'] * len(x),
            axis=1
        ).format({
            "Numerator": "{:.0f}",
            "Denominator": "{:.0f}",
            "Rasio": lambda x: f"{x:.2f}%" if isinstance(x, (int, float)) else x
        }).set_properties(**{
            'border': '1px solid black',
            'text-align': 'center',
            'font-size': '14px',
            'font-family': 'Arial, sans-serif'
        }).set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold')]},
            {'selector': 'caption', 'props': [('caption-side', 'top'), ('font-size', '18px'), ('font-weight', 'bold'), ('color', '#333')]},
        ]).set_caption("Tabel Outlier: Data dengan Numerator > Denominator atau Denominator = 0")
        st.write(styled_outliers, unsafe_allow_html=True)
    else:
        st.success("✅ Tidak ada outlier terdeteksi berdasarkan kriteria Numerator > Denominator atau Denominator = 0.")

    # 2. ⚙️ Analisis Outlier Statistik
    st.subheader(f"⚙️ Analisis Outlier Statistik ({periode_label})")
    # Gunakan recap_df yang sudah dihitung persentasenya
    cols_to_check = list(metrik_data.keys())

    # Inisialisasi DataFrame untuk outlier statistik
    base_columns = ["Puskesmas", "Metrik", "Nilai", "Metode"]
    if puskesmas_filter != "All":
        base_columns.insert(1, "Kelurahan")
    statistical_outliers_df = pd.DataFrame(columns=base_columns)

    # Dropdown untuk memilih metode deteksi outlier statistik
    # Tambahkan timestamp ke key untuk memastikan keunikan
    outlier_method = st.selectbox(
        "Pilih Metode Deteksi Outlier Statistik",
        ["Tidak Ada", "Z-Score", "IQR"],
        key=f"outlier_method_select_apras_{periode_label}_{time.time()}"
    )

    if outlier_method != "Tidak Ada":
        for metric in cols_to_check:
            if metric not in recap_df.columns:
                continue

            # Pilih kolom berdasarkan filter
            if puskesmas_filter == "All":
                metric_data = recap_df[[metric, "Puskesmas"]].dropna()
            else:
                metric_data = recap_df[[metric, "Puskesmas", "Kelurahan"]].dropna()

            if metric_data.empty:
                continue

            # Z-Score Method
            if outlier_method == "Z-Score":
                z_scores = stats.zscore(metric_data[metric], nan_policy='omit')
                z_outlier_mask = abs(z_scores) > 3  # Threshold Z-Score > 3
                z_outliers = metric_data[z_outlier_mask].copy()
                if not z_outliers.empty:
                    z_outliers["Metrik"] = metric
                    z_outliers["Nilai"] = z_outliers[metric]
                    z_outliers["Metode"] = "Z-Score"
                    if puskesmas_filter == "All":
                        z_outliers_subset = z_outliers[["Puskesmas", "Metrik", "Nilai", "Metode"]]
                    else:
                        z_outliers_subset = z_outliers[["Puskesmas", "Kelurahan", "Metrik", "Nilai", "Metode"]]
                    statistical_outliers_df = pd.concat([statistical_outliers_df, z_outliers_subset], ignore_index=True)

            # IQR Method
            elif outlier_method == "IQR":
                Q1 = metric_data[metric].quantile(0.25)
                Q3 = metric_data[metric].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                iqr_outlier_mask = (metric_data[metric] < lower_bound) | (metric_data[metric] > upper_bound)
                iqr_outliers = metric_data[iqr_outlier_mask].copy()
                if not iqr_outliers.empty:
                    iqr_outliers["Metrik"] = metric
                    iqr_outliers["Nilai"] = iqr_outliers[metric]
                    iqr_outliers["Metode"] = "IQR"
                    if puskesmas_filter == "All":
                        iqr_outliers_subset = iqr_outliers[["Puskesmas", "Metrik", "Nilai", "Metode"]]
                    else:
                        iqr_outliers_subset = iqr_outliers[["Puskesmas", "Kelurahan", "Metrik", "Nilai", "Metode"]]
                    statistical_outliers_df = pd.concat([statistical_outliers_df, iqr_outliers_subset], ignore_index=True)

    # 3. 📊 Tabel Outlier Statistik
    if not statistical_outliers_df.empty:
        st.markdown(f"### 📊 Tabel Outlier Statistik ({periode_label})")
        styled_stat_outliers = statistical_outliers_df.style.apply(
            lambda x: ['background-color: #FFA500; color: white;' if x['Metode'] == "Z-Score" else 'background-color: #FF8C00; color: white;'] * len(x),
            axis=1
        ).format({
            "Nilai": "{:.2f}%"
        }).set_properties(**{
            'border': '1px solid black',
            'text-align': 'center',
            'font-size': '14px',
            'font-family': 'Arial, sans-serif'
        }).set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#FF9800'), ('color', 'white'), ('font-weight', 'bold')]},
            {'selector': 'caption', 'props': [('caption-side', 'top'), ('font-size', '18px'), ('font-weight', 'bold'), ('color', '#333')]},
        ]).set_caption(f"Tabel Outlier Statistik ({outlier_method})")
        st.write(styled_stat_outliers, unsafe_allow_html=True)
    else:
        if outlier_method != "Tidak Ada":
            st.info(f"ℹ️ Tidak ada outlier statistik terdeteksi menggunakan metode {outlier_method}.")
    
    # 3.4 📊 Visualisasi Outlier
    st.subheader("📊 Visualisasi Outlier")
    show_outlier_viz = st.checkbox(
        "Tampilkan Visualisasi Outlier",
        value=False,
        key=f"cakupan_apras_viz_toggle_{periode_label}"
    )

    if show_outlier_viz:
        # Gabungkan outlier logis dan statistik
        combined_outliers = outliers_df[["Puskesmas", "Kelurahan", "Metrik", "Rasio"]].copy()
        combined_outliers["Metode"] = "Logis (Numerator > Denominator atau Denominator = 0)"
        # Ganti "Infinity" dengan nilai besar untuk visualisasi
        combined_outliers["Rasio"] = combined_outliers["Rasio"].replace("Infinity", 9999)
        if not statistical_outliers_df.empty:
            stat_outliers = statistical_outliers_df[["Puskesmas", "Metrik", "Metode", "Nilai"]].copy()
            stat_outliers = stat_outliers.rename(columns={"Nilai": "Rasio"})
            if "Kelurahan" in statistical_outliers_df.columns:
                stat_outliers["Kelurahan"] = statistical_outliers_df["Kelurahan"]
            else:
                stat_outliers["Kelurahan"] = "N/A"
            combined_outliers = pd.concat([combined_outliers, stat_outliers], ignore_index=True)

        if not combined_outliers.empty:
            viz_type = st.selectbox(
                "Pilih Tipe Visualisasi Outlier",
                ["Heatmap", "Grafik Batang", "Boxplot"],
                key=f"outlier_viz_select_apras_{periode_label}"
            )

            if viz_type == "Heatmap":
                pivot_df = combined_outliers.pivot_table(
                    index="Puskesmas",
                    columns="Metrik",
                    values="Rasio",
                    aggfunc="mean",
                    fill_value=0
                )
                fig_heatmap = px.imshow(
                    pivot_df,
                    text_auto=True,
                    aspect="auto",
                    title="Heatmap Distribusi Outlier per Puskesmas",
                    color_continuous_scale="Reds"
                )
                fig_heatmap.update_layout(
                    xaxis_title="Metrik",
                    yaxis_title="Puskesmas",
                    coloraxis_colorbar_title="Rasio (%)"
                )
                st.plotly_chart(fig_heatmap, use_container_width=True)

            elif viz_type == "Grafik Batang":
                count_df = combined_outliers.groupby(["Metrik", "Metode"]).size().reset_index(name="Jumlah")
                fig_bar = px.bar(
                    count_df,
                    x="Metrik",
                    y="Jumlah",
                    color="Metode",
                    barmode="group",
                    title="Jumlah Outlier per Metrik dan Metode Deteksi",
                    text="Jumlah"
                )
                fig_bar.update_traces(textposition="outside")
                fig_bar.update_layout(
                    xaxis_title="Metrik",
                    yaxis_title="Jumlah Outlier",
                    xaxis_tickangle=45,
                    legend_title="Metode Deteksi"
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            elif viz_type == "Boxplot":
                fig_box = px.box(
                    combined_outliers,
                    x="Metrik",
                    y="Rasio",
                    color="Metode",
                    title="Boxplot Distribusi Outlier per Metrik dan Metode Deteksi",
                    points="all"
                )
                fig_box.update_layout(
                    xaxis_title="Metrik",
                    yaxis_title="Rasio (%)",
                    xaxis_tickangle=45,
                    legend_title="Metode Deteksi"
                )
                st.plotly_chart(fig_box, use_container_width=True)
        else:
            st.info("ℹ️ Tidak ada data outlier untuk divisualisasikan.")

    # 4. 📈 Tren Metrik
    st.subheader(f"📈 Tren Metrik ({periode_label})")
    metric_list = list(metrik_data.keys())
    # Hitung metrik per bulan
    trend_df = filtered_df.copy()
    trend_df['Metrik Apras yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)'] = (trend_df['Jumlah_Apras_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi'] / trend_df['Jumlah_Apras_terdeteksi_gangguan_tumbang'] * 100).replace([np.inf, -np.inf], 0).fillna(0)
    trend_df['Metrik Apras mendapat pelayanan SDIDTK di Fasyankes (%)'] = (trend_df['Jumlah_Apras_mendapat_pelayanan_SDIDTK_di_FKTP'] / trend_df['Jumlah_anak_prasekolah_bulan_ini'] * 100).replace([np.inf, -np.inf], 0).fillna(0)
    trend_df['Metrik Apras yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)'] = (trend_df['Jumlah_Apras_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan'] / trend_df['Jumlah_anak_prasekolah_punya_Buku_KIA'] * 100).replace([np.inf, -np.inf], 0).fillna(0)
    trend_df['Metrik Apras yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)'] = (trend_df['Jumlah_Apras_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'] / trend_df['Jumlah_anak_prasekolah_bulan_ini'] * 100).replace([np.inf, -np.inf], 0).fillna(0)

    # Filter dan agregasi data berdasarkan Bulan (asumsi kolom Bulan ada)
    trend_df = trend_df.groupby("Bulan")[metric_list].mean().reset_index()
    trend_df = trend_df.melt(
        id_vars="Bulan",
        value_vars=metric_list,
        var_name="Metrik",
        value_name="Persentase"
    )

    # Bulatkan kolom Persentase menjadi 2 digit desimal
    trend_df["Persentase"] = trend_df["Persentase"].round(2)

    # Tampilkan line chart untuk semua metrik
    if not trend_df.empty:
        fig_trend = px.line(
            trend_df,
            x="Bulan",
            y="Persentase",
            color="Metrik",
            markers=True,
            text=trend_df["Persentase"].apply(lambda x: f"{x:.2f}"),
            title="📈 Tren Metrik Cakupan Layanan Kesehatan Apras dari Awal hingga Akhir Bulan"
        )
        fig_trend.update_traces(textposition="top center")
        fig_trend.update_layout(
            xaxis_title="Bulan",
            yaxis_title="Persentase (%)",
            xaxis=dict(tickmode='linear', tick0=1, dtick=1),
            yaxis_range=[0, 100],
            legend_title="Metrik",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(
            fig_trend,
            key=f"apras_trend_chart_{puskesmas_filter}_{kelurahan_filter}_{time.time()}",
            use_container_width=True
        )
    else:
        st.warning("⚠️ Tidak ada data untuk ditampilkan pada grafik tren Cakupan Layanan Kesehatan Apras.")

    # 5. 📊 Analisis Komparasi Antar Wilayah
    st.subheader(f"📊 Analisis Komparasi Antar Wilayah ({periode_label})")
    # Dropdown untuk memilih metrik yang ingin dibandingkan
    # Tambahkan timestamp ke key untuk memastikan keunikan
    selected_metric = st.selectbox(
        "Pilih Metrik untuk Komparasi Antar Wilayah",
        metric_list,
        key=f"comp_metric_select_apras_{time.time()}"
    )

    # Filter data berdasarkan metrik yang dipilih
    comp_df = recap_df.groupby(["Puskesmas", "Kelurahan"])[selected_metric].mean().reset_index()
    if not comp_df.empty:
        fig_comp = px.bar(
            comp_df,
            x="Puskesmas",
            y=selected_metric,
            color="Kelurahan",
            title=f"📊 Komparasi {selected_metric} Antar Wilayah",
            text=comp_df[selected_metric].apply(lambda x: f"{x:.2f}%"),
            height=400
        )
        fig_comp.update_traces(textposition="outside")
        fig_comp.update_layout(
            xaxis_title="Puskesmas",
            yaxis_title="Persentase (%)",
            xaxis_tickangle=45,
            yaxis_range=[0, 100],
            legend_title="Kelurahan"
        )
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.warning("⚠️ Tidak ada data untuk komparasi antar wilayah.")

    # 6. 🔍 Analisis Korelasi Antar Metrik
    st.subheader(f"🔍 Analisis Korelasi Antar Metrik ({periode_label})")
    # Hitung korelasi antar metrik menggunakan data agregat per Puskesmas/Kelurahan
    corr_df = recap_df.groupby(["Puskesmas", "Kelurahan"])[metric_list].mean().reset_index()
    if len(corr_df) > 1:  # Pastikan ada cukup data untuk korelasi
        correlation_matrix = corr_df[metric_list].corr()
        fig_corr = px.imshow(
            correlation_matrix,
            text_auto=True,
            aspect="auto",
            title="🔍 Matriks Korelasi Antar Metrik Cakupan Layanan Kesehatan Apras",
            color_continuous_scale="RdBu",
            range_color=[-1, 1]
        )
        fig_corr.update_layout(
            xaxis_title="Metrik",
            yaxis_title="Metrik",
            coloraxis_colorbar_title="Koefisien Korelasi"
        )
        st.plotly_chart(fig_corr, use_container_width=True)
        st.markdown("**Catatan:** Nilai mendekati 1 atau -1 menunjukkan korelasi kuat (positif atau negatif), sementara 0 menunjukkan tidak ada korelasi.")
    else:
        st.warning("⚠️ Tidak cukup data untuk menghitung korelasi antar metrik.")

    # 7. 📅 Analisis Perubahan Persentase (Growth/Decline)
    st.subheader(f"📅 Analisis Perubahan Persentase (Growth/Decline) ({periode_label})")
    # Pastikan data tren sudah ada
    if not trend_df.empty:
        # Hitung perubahan persentase dari bulan ke bulan
        trend_df = trend_df.sort_values("Bulan")
        trend_df["Perubahan Persentase"] = trend_df.groupby("Metrik")["Persentase"].pct_change() * 100
        trend_df["Perubahan Persentase"] = trend_df["Perubahan Persentase"].round(2)

        # Tampilkan tabel perubahan
        st.dataframe(
            trend_df[["Bulan", "Metrik", "Persentase", "Perubahan Persentase"]].style.format({
                "Persentase": "{:.2f}%",
                "Perubahan Persentase": "{:.2f}%"
            }).set_properties(**{
                'text-align': 'center',
                'font-size': '14px',
                'border': '1px solid black'
            }).set_table_styles([
                {'selector': 'th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold')]},
                {'selector': 'caption', 'props': [('caption-side', 'top'), ('font-size', '18px'), ('font-weight', 'bold'), ('color', '#333')]},
            ]).set_caption("📅 Tabel Perubahan Persentase Antar Bulan"),
            use_container_width=True
        )

        # Visualisasi perubahan dengan grafik garis
        fig_change = px.line(
            trend_df,
            x="Bulan",
            y="Perubahan Persentase",
            color="Metrik",
            markers=True,
            text=trend_df["Perubahan Persentase"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else ""),
            title="📅 Tren Perubahan Persentase Metrik Cakupan Layanan Kesehatan Apras"
        )
        fig_change.update_traces(textposition="top center")
        fig_change.update_layout(
            xaxis_title="Bulan",
            yaxis_title="Perubahan Persentase (%)",
            xaxis=dict(tickmode='linear', tick0=1, dtick=1),
            legend_title="Metrik",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_change, use_container_width=True)
    else:
        st.warning("⚠️ Tidak ada data untuk menganalisis perubahan persentase.")

    # 8. 📉 Analisis Distribusi Data (Histogram)
    st.subheader(f"📉 Analisis Distribusi Data (Histogram) ({periode_label})")
    # Dropdown untuk memilih metrik yang ingin dianalisis distribusinya
    # Tambahkan timestamp ke key untuk memastikan keunikan
    selected_metric_dist = st.selectbox(
        "Pilih Metrik untuk Analisis Distribusi",
        metric_list,
        key=f"dist_metric_select_apras_{time.time()}"
    )

    # Buat histogram berdasarkan data per Puskesmas/Kelurahan
    dist_df = recap_df.groupby(["Puskesmas", "Kelurahan"])[selected_metric_dist].mean().reset_index()
    if not dist_df.empty:
        fig_dist = px.histogram(
            dist_df,
            x=selected_metric_dist,
            nbins=20,
            title=f"📉 Distribusi {selected_metric_dist} di Seluruh Wilayah",
            labels={"value": "Persentase (%)", "count": "Jumlah Wilayah"},
            height=400
        )
        fig_dist.update_layout(
            xaxis_title="Persentase (%)",
            yaxis_title="Jumlah Wilayah",
            bargap=0.1
        )
        st.plotly_chart(fig_dist, use_container_width=True)
        # Tambahan statistik dasar
        mean_val = dist_df[selected_metric_dist].mean().round(2)
        median_val = dist_df[selected_metric_dist].median().round(2)
        st.markdown(f"**Statistik Distribusi:** Rata-rata = {mean_val}%, Median = {median_val}%")
    else:
        st.warning("⚠️ Tidak ada data untuk analisis distribusi.")

    # 4. Fitur Download Laporan PDF
    st.subheader("📥 Unduh Laporan")
    def generate_pdf_report(figures_list):
        # Buat buffer untuk menyimpan grafik
        img_buffers = []
        for fig in figures_list:
            img_buffer = BytesIO()
            fig.write_image(img_buffer, format='png', width=600, height=400, scale=2)
            img_buffer.seek(0)
            img_buffers.append(img_buffer)

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
        elements.append(Paragraph(f"Laporan Cakupan Layanan Kesehatan Apras ({periode_label})", title_style))
        elements.append(Paragraph(f"Diperbarui: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
        elements.append(Spacer(1, 12))

        # Tambahkan Metrik
        elements.append(Paragraph("1. Metrik Cakupan", normal_style))
        metric_data = [[f"{label}: {value:.2f}%" for label, value in metrik_list]]
        metric_table = Table(metric_data, colWidths=[300])
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
        for i, metric in enumerate(metrics):
            elements.append(Paragraph(f"2.{i+1}. Grafik {metric}", normal_style))
            elements.append(Image(img_buffers[i], width=500, height=300))
            elements.append(Spacer(1, 12))

        # Tambahkan Tabel Rekapitulasi
        elements.append(Paragraph(f"3. Tabel Rekapitulasi", normal_style))
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

    if st.button("Download Laporan PDF", key=f"download_cakupan_layanan_kesehatan_apras_{periode_label}"):
        st.warning("Membuat laporan PDF, harap tunggu...")
        pdf_data = generate_pdf_report(figures_list)
        st.success("Laporan PDF siap diunduh!")
        st.download_button(
            label="Download Laporan PDF",
            data=pdf_data,
            file_name=f"Laporan_Cakupan_Layanan_Kesehatan_Apras_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )
# ----------------------------- #
# 🩺 Cakupan PKAT (Pemeriksaan Kesehatan Anak Terintegrasi)
# ----------------------------- #
def cakupan_pkat(filtered_df, desa_df, puskesmas_filter, kelurahan_filter, jenis_laporan, tahun_filter, bulan_filter_int=None, tribulan_filter=None):
    """Menampilkan analisis Cakupan PKAT dengan fitur download laporan."""
    st.header("🩺 Cakupan PKAT (Pemeriksaan Kesehatan Anak Terintegrasi)")

    # Inisialisasi periode untuk label
    periode_label = ""
    if tahun_filter != "All":
        periode_label += f"Tahun {tahun_filter}"
    if jenis_laporan == "Bulanan" and bulan_filter_int is not None:
        periode_label += f" Bulan {bulan_filter_int}" if periode_label else f"Bulan {bulan_filter_int}"
    elif jenis_laporan == "Tahunan" and tribulan_filter:
        periode_label += f" {tribulan_filter}" if periode_label else tribulan_filter

    # 1. Memuat data Jumlah_Bayi_usia_6_bulan dari data_balita_gizi
    try:
        conn = sqlite3.connect("rcs_data.db")
        gizi_df = pd.read_sql_query("SELECT Kelurahan, Bulan, Jumlah_Bayi_usia_6_bulan FROM data_balita_gizi", conn)
        conn.close()
    except Exception as e:
        st.error(f"❌ Gagal memuat data dari data_balita_gizi: {e}")
        return

    # Pastikan kolom yang dibutuhkan ada di filtered_df
    required_columns = ['Cakupan_bayi_dilayani_PKAT']
    missing_cols = [col for col in required_columns if col not in filtered_df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di dataset data_balita_kia: {missing_cols}.")
        return

    # Agregasi filtered_df berdasarkan jenis laporan
    if jenis_laporan == "Tahunan" and not filtered_df.empty:
        group_columns = ["Puskesmas", "Kelurahan"]
        numeric_columns = [col for col in filtered_df.columns if filtered_df[col].dtype in ['int64', 'float64']]
        if numeric_columns:
            agg_dict = {col: "sum" for col in numeric_columns}
            filtered_df = filtered_df.groupby(group_columns).agg(agg_dict).reset_index()

    # Agregasi gizi_df untuk laporan tahunan (Tribulan)
    if jenis_laporan == "Tahunan" and tribulan_filter:
        # Tentukan bulan berdasarkan tribulan
        if tribulan_filter == "Tribulan I":
            bulan_range = [1, 2, 3]
        elif tribulan_filter == "Tribulan II":
            bulan_range = [4, 5, 6]
        elif tribulan_filter == "Tribulan III":
            bulan_range = [7, 8, 9]
        elif tribulan_filter == "Tribulan IV":
            bulan_range = [10, 11, 12]
        else:
            st.error("⚠️ Tribulan tidak valid!")
            return
        # Filter gizi_df untuk bulan dalam tribulan
        gizi_df = gizi_df[gizi_df['Bulan'].isin(bulan_range)]
        # Agregasi gizi_df per Kelurahan
        gizi_df = gizi_df.groupby('Kelurahan').agg({'Jumlah_Bayi_usia_6_bulan': 'sum'}).reset_index()

    # Gabungkan data dari data_balita_kia (filtered_df) dengan data_balita_gizi (gizi_df)
    if jenis_laporan == "Bulanan":
        # Untuk bulanan, pastikan tipe data Bulan sama
        filtered_df['Bulan'] = filtered_df['Bulan'].astype(int)
        gizi_df['Bulan'] = gizi_df['Bulan'].astype(int)
        # Gabungkan berdasarkan Kelurahan dan Bulan
        merged_df = pd.merge(
            filtered_df,
            gizi_df[['Kelurahan', 'Bulan', 'Jumlah_Bayi_usia_6_bulan']],
            on=['Kelurahan', 'Bulan'],
            how='left'
        )
    else:
        # Untuk tahunan, gabungkan hanya berdasarkan Kelurahan
        merged_df = pd.merge(
            filtered_df,
            gizi_df[['Kelurahan', 'Jumlah_Bayi_usia_6_bulan']],
            on='Kelurahan',
            how='left'
        )

    # Cek apakah ada data yang tidak match
    if merged_df['Jumlah_Bayi_usia_6_bulan'].isna().all():
        st.warning("⚠️ Tidak ada data Jumlah_Bayi_usia_6_bulan yang cocok dengan filter Kelurahan. Periksa data di data_balita_gizi!")
        return

    # Hitung total
    total_bayi_6_bulan = merged_df['Jumlah_Bayi_usia_6_bulan'].sum()
    total_dilayani_pkat = merged_df['Cakupan_bayi_dilayani_PKAT'].sum()

    if total_bayi_6_bulan == 0:
        st.warning("⚠️ Tidak ada data bayi usia 6 bulan untuk filter ini.")
        return

    # Hitung metrik
    metrik_data = {
        "Metrik bayi usia 6 bulan - 6 bulan 29 hari yang dilayani PKAT (%)": (total_dilayani_pkat / total_bayi_6_bulan * 100)
    }

    # 1. Metrik Score Card
    st.subheader(f"📊 Metrik Cakupan PKAT ({periode_label})")
    cols = st.columns(2)  # 2 kolom untuk konsistensi tata letak
    label, value = list(metrik_data.items())[0]
    cols[0].metric(label=label, value=f"{value:.2f}%")
    # Kolom kedua dibiarkan kosong untuk tata letak

    # 2. Grafik Visualisasi
    st.subheader(f"📈 Grafik Cakupan PKAT ({periode_label})")
    metric = list(metrik_data.keys())[0]
    figures_list = []  # Daftar untuk menyimpan semua objek fig
    if puskesmas_filter == "All":
        grouped_df = merged_df.groupby('Puskesmas').sum().reset_index()
        graph_data = pd.DataFrame({
            "Puskesmas": grouped_df['Puskesmas'],
            metric: (grouped_df['Cakupan_bayi_dilayani_PKAT'] / grouped_df['Jumlah_Bayi_usia_6_bulan'] * 100).fillna(0)
        })
        fig = px.bar(graph_data, x="Puskesmas", y=metric, text=graph_data[metric].apply(lambda x: f"{x:.1f}%"),
                     title=f"{metric} per Puskesmas ({periode_label})", color_discrete_sequence=["#FF4500"])
    else:
        grouped_df = merged_df.groupby('Kelurahan').sum().reset_index()
        graph_data = pd.DataFrame({
            "Kelurahan": grouped_df['Kelurahan'],
            metric: (grouped_df['Cakupan_bayi_dilayani_PKAT'] / grouped_df['Jumlah_Bayi_usia_6_bulan'] * 100).fillna(0)
        })
        fig = px.bar(graph_data, x="Kelurahan", y=metric, text=graph_data[metric].apply(lambda x: f"{x:.1f}%"),
                     title=f"{metric} per Kelurahan di {puskesmas_filter} ({periode_label})", color_discrete_sequence=["#FF4500"])

    fig.update_traces(textposition='outside')
    fig.add_hline(
        y=100,
        line_dash="dash",
        line_color="red",
        annotation_text="Target: 100%",
        annotation_position="top right"
    )
    fig.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", yaxis_range=[0, 100], title_x=0.5, height=400)
    st.plotly_chart(fig, use_container_width=True)
    figures_list.append(fig)

    # 3. Tabel Rekapitulasi
    st.subheader(f"📋 Tabel Rekapitulasi Cakupan PKAT ({periode_label})")
    if puskesmas_filter == "All":
        recap_df = merged_df.groupby('Puskesmas').sum().reset_index()
    else:
        recap_df = merged_df.groupby(['Puskesmas', 'Kelurahan']).sum().reset_index()

    # Hitung metrik dengan penanganan inf
    recap_df[metric] = (recap_df['Cakupan_bayi_dilayani_PKAT'] / recap_df['Jumlah_Bayi_usia_6_bulan'] * 100).replace([np.inf, -np.inf], 0).fillna(0).round(2)

    # Siapkan kolom untuk ditampilkan
    recap_display = recap_df[['Puskesmas', 'Kelurahan', 'Jumlah_Bayi_usia_6_bulan', 'Cakupan_bayi_dilayani_PKAT', metric]] if puskesmas_filter != "All" else recap_df[['Puskesmas', 'Jumlah_Bayi_usia_6_bulan', 'Cakupan_bayi_dilayani_PKAT', metric]]

    # Tambahkan kolom nomor urut
    recap_display.insert(0, 'No', range(1, len(recap_display) + 1))

    # Definisikan fungsi highlight untuk outlier > 100%
    def highlight_outliers(row):
        styles = [''] * len(row)
        if metric in row.index and pd.notna(row[metric]) and row[metric] > 100:
            idx = row.index.get_loc(metric)
            styles[idx] = 'background-color: #FF6666; color: white;'
        return styles

    # Pastikan data numerik dan bulatkan ke 2 digit desimal
    if metric in recap_display.columns:
        recap_display[metric] = pd.to_numeric(recap_display[metric], errors='coerce').round(2)

    # Terapkan styling dan formatting
    styled_df = recap_display.style.apply(highlight_outliers, axis=1).format({
        metric: "{:.2f}%"
    }, na_rep="N/A", precision=2)

    # Render tabel dengan styling yang eksplisit
    st.write(styled_df, unsafe_allow_html=True)

    # Tambahkan notice di bawah tabel
    st.markdown(
        """
        <div style="background-color: #ADD8E6; padding: 10px; border-radius: 5px; color: black; font-size: 14px; font-family: Arial, sans-serif;">
            <strong>Catatan Penting:</strong> Nilai yang melebihi 100% (indikasi data outlier) telah dihighlight <span style="color: #FF6666; font-weight: bold;">Warna Merah</span>. Nilai <code>inf%</code> (infinity percent) terjadi ketika total bayi usia 6 bulan bernilai 0, dan telah diganti menjadi 0% untuk kejelasan. Untuk analisis lebih lanjut dan koreksi data, mohon dilakukan pemeriksaan pada <strong>Menu Daftar Entry</strong>.
        </div>
        """,
        unsafe_allow_html=True
    )

    # 1. 🚨 Tabel Deteksi Outlier
    st.subheader(f"🚨 Tabel Deteksi Outlier ({periode_label})")
    metric = "Metrik bayi usia 6 bulan - 6 bulan 29 hari yang dilayani PKAT (%)"
    outliers_df = pd.DataFrame(columns=["Puskesmas", "Kelurahan", "Numerator", "Denominator", "Rasio", "Alasan"])
    outlier_data_num = merged_df[
        (merged_df['Cakupan_bayi_dilayani_PKAT'] > merged_df['Jumlah_Bayi_usia_6_bulan']) &
        (merged_df['Jumlah_Bayi_usia_6_bulan'] != 0)
    ][["Puskesmas", "Kelurahan", "Cakupan_bayi_dilayani_PKAT", "Jumlah_Bayi_usia_6_bulan"]]
    if not outlier_data_num.empty:
        outlier_data_num["Numerator"] = outlier_data_num["Cakupan_bayi_dilayani_PKAT"]
        outlier_data_num["Denominator"] = outlier_data_num["Jumlah_Bayi_usia_6_bulan"]
        outlier_data_num["Rasio"] = (outlier_data_num["Numerator"] / outlier_data_num["Denominator"] * 100).round(2)
        outlier_data_num["Alasan"] = "Numerator > Denominator"
        outliers_df = pd.concat([outliers_df, outlier_data_num[["Puskesmas", "Kelurahan", "Numerator", "Denominator", "Rasio", "Alasan"]]], ignore_index=True)

    outlier_data_zero = merged_df[
        (merged_df['Jumlah_Bayi_usia_6_bulan'] == 0) &
        (merged_df['Cakupan_bayi_dilayani_PKAT'] > 0)
    ][["Puskesmas", "Kelurahan", "Cakupan_bayi_dilayani_PKAT", "Jumlah_Bayi_usia_6_bulan"]]
    if not outlier_data_zero.empty:
        outlier_data_zero["Numerator"] = outlier_data_zero["Cakupan_bayi_dilayani_PKAT"]
        outlier_data_zero["Denominator"] = outlier_data_zero["Jumlah_Bayi_usia_6_bulan"]
        outlier_data_zero["Rasio"] = "Infinity"
        outlier_data_zero["Alasan"] = "Denominator = 0"
        outliers_df = pd.concat([outliers_df, outlier_data_zero[["Puskesmas", "Kelurahan", "Numerator", "Denominator", "Rasio", "Alasan"]]], ignore_index=True)

    if not outliers_df.empty:
        styled_outliers = outliers_df.style.apply(
            lambda x: ['background-color: #FF6666; color: white;' if x['Alasan'] == "Numerator > Denominator" else 'background-color: #FF4500; color: white;'] * len(x),
            axis=1
        ).format({
            "Numerator": "{:.0f}",
            "Denominator": "{:.0f}",
            "Rasio": lambda x: f"{x:.2f}%" if isinstance(x, (int, float)) else x
        }).set_properties(**{'border': '1px solid black', 'text-align': 'center', 'font-size': '14px'}).set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold')]},
            {'selector': 'caption', 'props': [('caption-side', 'top'), ('font-size', '18px'), ('font-weight', 'bold')]}
        ]).set_caption("Tabel Outlier: Data dengan Numerator > Denominator atau Denominator = 0")
        st.write(styled_outliers, unsafe_allow_html=True)
    else:
        st.success("✅ Tidak ada outlier terdeteksi berdasarkan kriteria Numerator > Denominator atau Denominator = 0.")

    # 2. ⚙️ Analisis Outlier Statistik
    st.subheader(f"⚙️ Analisis Outlier Statistik ({periode_label})")
    base_columns = ["Puskesmas", "Nilai", "Metode"]
    if puskesmas_filter != "All":
        base_columns.insert(1, "Kelurahan")
    statistical_outliers_df = pd.DataFrame(columns=base_columns)
    outlier_method = st.selectbox(
        "Pilih Metode Deteksi Outlier Statistik",
        ["Tidak Ada", "Z-Score", "IQR"],
        key=f"outlier_method_select_pkat_{time.time()}"
    )
    if outlier_method != "Tidak Ada":
        if puskesmas_filter == "All":
            metric_data = recap_df[[metric, "Puskesmas"]].dropna()
        else:
            metric_data = recap_df[[metric, "Puskesmas", "Kelurahan"]].dropna()
        if not metric_data.empty:
            if outlier_method == "Z-Score":
                z_scores = stats.zscore(metric_data[metric], nan_policy='omit')
                z_outlier_mask = abs(z_scores) > 3
                z_outliers = metric_data[z_outlier_mask].copy()
                if not z_outliers.empty:
                    z_outliers["Nilai"] = z_outliers[metric]
                    z_outliers["Metode"] = "Z-Score"
                    if puskesmas_filter == "All":
                        statistical_outliers_df = pd.concat([statistical_outliers_df, z_outliers[["Puskesmas", "Nilai", "Metode"]]], ignore_index=True)
                    else:
                        statistical_outliers_df = pd.concat([statistical_outliers_df, z_outliers[["Puskesmas", "Kelurahan", "Nilai", "Metode"]]], ignore_index=True)
            elif outlier_method == "IQR":
                Q1 = metric_data[metric].quantile(0.25)
                Q3 = metric_data[metric].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                iqr_outlier_mask = (metric_data[metric] < lower_bound) | (metric_data[metric] > upper_bound)
                iqr_outliers = metric_data[iqr_outlier_mask].copy()
                if not iqr_outliers.empty:
                    iqr_outliers["Nilai"] = iqr_outliers[metric]
                    iqr_outliers["Metode"] = "IQR"
                    if puskesmas_filter == "All":
                        statistical_outliers_df = pd.concat([statistical_outliers_df, iqr_outliers[["Puskesmas", "Nilai", "Metode"]]], ignore_index=True)
                    else:
                        statistical_outliers_df = pd.concat([statistical_outliers_df, iqr_outliers[["Puskesmas", "Kelurahan", "Nilai", "Metode"]]], ignore_index=True)
    if not statistical_outliers_df.empty:
        st.markdown(f"### 📊 Tabel Outlier Statistik ({periode_label})")
        styled_stat_outliers = statistical_outliers_df.style.apply(
            lambda x: ['background-color: #FFA500; color: white;' if x['Metode'] == "Z-Score" else 'background-color: #FF8C00; color: white;'] * len(x),
            axis=1
        ).format({"Nilai": "{:.2f}%"}).set_properties(**{'border': '1px solid black', 'text-align': 'center', 'font-size': '14px'}).set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#FF9800'), ('color', 'white'), ('font-weight', 'bold')]},
            {'selector': 'caption', 'props': [('caption-side', 'top'), ('font-size', '18px'), ('font-weight', 'bold')]}
        ]).set_caption(f"Tabel Outlier Statistik ({outlier_method})")
        st.write(styled_stat_outliers, unsafe_allow_html=True)
    else:
        if outlier_method != "Tidak Ada":
            st.info(f"ℹ️ Tidak ada outlier statistik terdeteksi menggunakan metode {outlier_method}.")
    
    # 3.4 📊 Visualisasi Outlier
    st.subheader("📊 Visualisasi Outlier")
    show_outlier_viz = st.checkbox(
        "Tampilkan Visualisasi Outlier",
        value=False,
        key=f"pkat_viz_toggle_{periode_label}_{time.time()}"
    )

    if show_outlier_viz:
        # Gabungkan outlier logis dan statistik
        combined_outliers = outliers_df[["Puskesmas", "Kelurahan", "Rasio"]].copy()
        combined_outliers["Metrik"] = "Metrik bayi usia 6 bulan - 6 bulan 29 hari yang dilayani PKAT (%)"
        combined_outliers["Metode"] = "Logis (Numerator > Denominator atau Denominator = 0)"
        # Ganti "Infinity" dengan nilai besar untuk visualisasi
        combined_outliers["Rasio"] = combined_outliers["Rasio"].replace("Infinity", 9999)
        if not statistical_outliers_df.empty:
            stat_outliers = statistical_outliers_df[["Puskesmas", "Metode", "Nilai"]].copy()
            stat_outliers = stat_outliers.rename(columns={"Nilai": "Rasio"})
            stat_outliers["Metrik"] = "Metrik bayi usia 6 bulan - 6 bulan 29 hari yang dilayani PKAT (%)"
            if "Kelurahan" in statistical_outliers_df.columns:
                stat_outliers["Kelurahan"] = statistical_outliers_df["Kelurahan"]
            else:
                stat_outliers["Kelurahan"] = "N/A"
            combined_outliers = pd.concat([combined_outliers, stat_outliers], ignore_index=True)

        if not combined_outliers.empty:
            viz_type = st.selectbox(
                "Pilih Tipe Visualisasi Outlier",
                ["Heatmap", "Grafik Batang", "Boxplot"],
                key=f"outlier_viz_select_pkat_{periode_label}_{time.time()}"
            )

            if viz_type == "Heatmap":
                pivot_df = combined_outliers.pivot_table(
                    index="Puskesmas",
                    columns="Metrik",
                    values="Rasio",
                    aggfunc="mean",
                    fill_value=0
                )
                fig_heatmap = px.imshow(
                    pivot_df,
                    text_auto=True,
                    aspect="auto",
                    title="Heatmap Distribusi Outlier per Puskesmas",
                    color_continuous_scale="Reds"
                )
                fig_heatmap.update_layout(
                    xaxis_title="Metrik",
                    yaxis_title="Puskesmas",
                    coloraxis_colorbar_title="Rasio (%)"
                )
                st.plotly_chart(fig_heatmap, use_container_width=True)

            elif viz_type == "Grafik Batang":
                count_df = combined_outliers.groupby(["Metrik", "Metode"]).size().reset_index(name="Jumlah")
                fig_bar = px.bar(
                    count_df,
                    x="Metrik",
                    y="Jumlah",
                    color="Metode",
                    barmode="group",
                    title="Jumlah Outlier per Metrik dan Metode Deteksi",
                    text="Jumlah"
                )
                fig_bar.update_traces(textposition="outside")
                fig_bar.update_layout(
                    xaxis_title="Metrik",
                    yaxis_title="Jumlah Outlier",
                    xaxis_tickangle=45,
                    legend_title="Metode Deteksi"
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            elif viz_type == "Boxplot":
                fig_box = px.box(
                    combined_outliers,
                    x="Metrik",
                    y="Rasio",
                    color="Metode",
                    title="Boxplot Distribusi Outlier per Metrik dan Metode Deteksi",
                    points="all"
                )
                fig_box.update_layout(
                    xaxis_title="Metrik",
                    yaxis_title="Rasio (%)",
                    xaxis_tickangle=45,
                    legend_title="Metode Deteksi"
                )
                st.plotly_chart(fig_box, use_container_width=True)
        else:
            st.info("ℹ️ Tidak ada data outlier untuk divisualisasikan.")

    # 3. 📈 Tren Metrik
    st.subheader(f"📈 Tren Metrik ({periode_label})")
    metric = "Metrik bayi usia 6 bulan - 6 bulan 29 hari yang dilayani PKAT (%)"
    trend_df = merged_df.copy()
    trend_df[metric] = (trend_df['Cakupan_bayi_dilayani_PKAT'] / trend_df['Jumlah_Bayi_usia_6_bulan'] * 100).replace([np.inf, -np.inf], 0).fillna(0)
    trend_df = trend_df.groupby("Bulan")[metric].mean().reset_index()
    if not trend_df.empty:
        fig_trend = px.line(
            trend_df,
            x="Bulan",
            y=metric,
            markers=True,
            text=trend_df[metric].apply(lambda x: f"{x:.2f}"),
            title="📈 Tren Metrik Cakupan PKAT dari Awal hingga Akhir Bulan"
        )
        fig_trend.update_traces(textposition="top center")
        fig_trend.update_layout(xaxis_title="Bulan", yaxis_title="Persentase (%)", xaxis=dict(tickmode='linear', tick0=1, dtick=1), yaxis_range=[0, 100])
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.warning("⚠️ Tidak ada data untuk ditampilkan pada grafik tren Cakupan PKAT.")

    # 4. 📊 Analisis Komparasi Antar Wilayah
    st.subheader(f"📊 Analisis Komparasi Antar Wilayah ({periode_label})")
    selected_metric = st.selectbox(
        "Pilih Metrik untuk Komparasi Antar Wilayah",
        [metric],
        key=f"comp_metric_select_pkat_{time.time()}"
    )
    comp_df = recap_df.groupby(["Puskesmas", "Kelurahan"])[selected_metric].mean().reset_index()
    if not comp_df.empty:
        fig_comp = px.bar(
            comp_df,
            x="Puskesmas",
            y=selected_metric,
            color="Kelurahan",
            title=f"📊 Komparasi {selected_metric} Antar Wilayah",
            text=comp_df[selected_metric].apply(lambda x: f"{x:.2f}%"),
            height=400
        )
        fig_comp.update_traces(textposition="outside")
        fig_comp.update_layout(xaxis_title="Puskesmas", yaxis_title="Persentase (%)", xaxis_tickangle=45, yaxis_range=[0, 100], legend_title="Kelurahan")
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.warning("⚠️ Tidak ada data untuk komparasi antar wilayah.")

    # 5. 🔍 Analisis Korelasi Antar Metrik
    st.subheader(f"🔍 Analisis Korelasi Antar Metrik ({periode_label})")
    st.warning("⚠️ Analisis korelasi antar metrik tidak dapat dilakukan karena hanya ada satu metrik (PKAT).")

    # 6. 📅 Analisis Perubahan Persentase (Growth/Decline)
    st.subheader(f"📅 Analisis Perubahan Persentase (Growth/Decline) ({periode_label})")
    if not trend_df.empty:
        trend_df = trend_df.sort_values("Bulan")
        trend_df["Perubahan Persentase"] = trend_df[metric].pct_change() * 100
        trend_df["Perubahan Persentase"] = trend_df["Perubahan Persentase"].round(2)
        st.dataframe(
            trend_df[["Bulan", metric, "Perubahan Persentase"]].style.format({
                metric: "{:.2f}%",
                "Perubahan Persentase": "{:.2f}%"
            }).set_properties(**{'text-align': 'center', 'font-size': '14px', 'border': '1px solid black'}).set_table_styles([
                {'selector': 'th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold')]},
                {'selector': 'caption', 'props': [('caption-side', 'top'), ('font-size', '18px'), ('font-weight', 'bold')]}
            ]).set_caption("📅 Tabel Perubahan Persentase Antar Bulan")
        )
        fig_change = px.line(
            trend_df,
            x="Bulan",
            y="Perubahan Persentase",
            markers=True,
            text=trend_df["Perubahan Persentase"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else ""),
            title="📅 Tren Perubahan Persentase Metrik Cakupan PKAT"
        )
        fig_change.update_traces(textposition="top center")
        fig_change.update_layout(xaxis_title="Bulan", yaxis_title="Perubahan Persentase (%)", xaxis=dict(tickmode='linear', tick0=1, dtick=1))
        st.plotly_chart(fig_change, use_container_width=True)
    else:
        st.warning("⚠️ Tidak ada data untuk menganalisis perubahan persentase.")

    # 7. 📉 Analisis Distribusi Data (Histogram)
    st.subheader(f"📉 Analisis Distribusi Data (Histogram) ({periode_label})")
    selected_metric_dist = st.selectbox(
        "Pilih Metrik untuk Analisis Distribusi",
        [metric],
        key=f"dist_metric_select_pkat_{time.time()}"
    )
    dist_df = recap_df.groupby(["Puskesmas", "Kelurahan"])[selected_metric_dist].mean().reset_index()
    if not dist_df.empty:
        fig_dist = px.histogram(
            dist_df,
            x=selected_metric_dist,
            nbins=20,
            title=f"📉 Distribusi {selected_metric_dist} di Seluruh Wilayah",
            labels={"value": "Persentase (%)", "count": "Jumlah Wilayah"},
            height=400
        )
        fig_dist.update_layout(xaxis_title="Persentase (%)", yaxis_title="Jumlah Wilayah", bargap=0.1)
        st.plotly_chart(fig_dist, use_container_width=True)
        mean_val = dist_df[selected_metric_dist].mean().round(2)
        median_val = dist_df[selected_metric_dist].median().round(2)
        st.markdown(f"**Statistik Distribusi:** Rata-rata = {mean_val}%, Median = {median_val}%")
    else:
        st.warning("⚠️ Tidak ada data untuk analisis distribusi.")

    # 4. Fitur Download Laporan PDF
    st.subheader("📥 Unduh Laporan")
    def generate_pdf_report(figures_list):
        # Buat buffer untuk menyimpan grafik
        img_buffers = []
        for fig in figures_list:
            img_buffer = BytesIO()
            fig.write_image(img_buffer, format='png', width=600, height=400, scale=2)
            img_buffer.seek(0)
            img_buffers.append(img_buffer)

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
        elements.append(Paragraph(f"Laporan Cakupan PKAT (Pemeriksaan Kesehatan Anak Terintegrasi) ({periode_label})", title_style))
        elements.append(Paragraph(f"Diperbarui: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
        elements.append(Spacer(1, 12))

        # Tambahkan Metrik
        elements.append(Paragraph("1. Metrik Cakupan", normal_style))
        metric_data = [[f"{label}: {value:.2f}%" for label, value in metrik_data.items()]]
        metric_table = Table(metric_data, colWidths=[300])
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
        elements.append(Paragraph("2. Grafik Cakupan PKAT", normal_style))
        elements.append(Image(img_buffers[0], width=500, height=300))
        elements.append(Spacer(1, 12))

        # Tambahkan Tabel Rekapitulasi
        elements.append(Paragraph("3. Tabel Rekapitulasi", normal_style))
        table_data = [recap_display.columns.tolist()] + recap_display.values.tolist()
        recap_table = Table(table_data, colWidths=[50, 150, 150, 100, 100, 150])
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

    if st.button("Download Laporan PDF", key=f"download_cakupan_pkat_{periode_label}"):
        st.warning("Membuat laporan PDF, harap tunggu...")
        pdf_data = generate_pdf_report(figures_list)
        st.success("Laporan PDF siap diunduh!")
        st.download_button(
            label="Download Laporan PDF",
            data=pdf_data,
            file_name=f"Laporan_Cakupan_PKAT_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )
# ----------------------------- #
# 🚀 Main Function
# ----------------------------- #
def show_dashboard():
    """Menampilkan dashboard utama untuk indikator balita KIA dengan filter dan menu di main page."""
    st.title("🍼 Dashboard Indikator Balita KIA")
    last_upload_time = get_last_upload_time()
    st.markdown(f"**📅 Data terakhir diperbarui:** {last_upload_time}")

    # Muat data
    df, desa_df = load_data()
    if df is None or desa_df is None:
        st.error("❌ Gagal memuat data. Pastikan file 'rcs_data.db' tersedia dan tabel 'data_balita_kia' serta 'dataset_desa' valid.")
        return

    # Validasi kolom wajib
    required_columns = ["Puskesmas", "Kelurahan"]
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom wajib berikut tidak ditemukan di dataset: {missing_cols}. Periksa tabel 'data_balita_kia'.")
        return

    # Tentukan opsi tahun secara fleksibel
    if "Tahun" in df.columns:
        tahun_options = ["All"] + sorted(df['Tahun'].astype(str).unique().tolist())
    else:
        st.warning("⚠️ Kolom 'Tahun' tidak ditemukan. Menggunakan rentang tahun default (5 tahun terakhir).")
        current_year = datetime.now().year
        tahun_options = ["All"] + [str(y) for y in range(current_year - 4, current_year + 1)]

    # Filter Data di Main Page
    st.subheader("🔎 Filter Data")
    with st.container():
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])

        with col1:
            tahun_filter = st.selectbox("📅 Pilih Tahun", options=tahun_options, help="Pilih tahun untuk analisis atau 'All' untuk semua tahun.")

        with col2:
            jenis_laporan = st.selectbox("📋 Pilih Jenis Laporan", ["Bulanan", "Tahunan"], help="Pilih jenis laporan: Bulanan atau Tahunan.")

        bulan_filter = "All"
        tribulan_filter = None
        bulan_filter_int = None
        bulan_range = None

        with col3:
            if jenis_laporan == "Bulanan":
                if "Bulan" in df.columns:
                    bulan_options = ["All"] + sorted(df['Bulan'].astype(str).unique().tolist())
                else:
                    st.warning("⚠️ Kolom 'Bulan' tidak ditemukan. Filter bulan dinonaktifkan.")
                    bulan_options = ["All"]
                bulan_filter = st.selectbox("📅 Pilih Bulan", options=bulan_options, help="Pilih bulan untuk laporan bulanan atau 'All'.")
            else:
                tribulan_options = ["Tribulan I", "Tribulan II", "Tribulan III", "Tribulan IV"]
                tribulan_filter = st.selectbox("📅 Pilih Tribulan", options=tribulan_options, help="Pilih tribulan untuk laporan tahunan.")
                if tribulan_filter == "Tribulan I":
                    bulan_range = [1, 2, 3]
                elif tribulan_filter == "Tribulan II":
                    bulan_range = [4, 5, 6]
                elif tribulan_filter == "Tribulan III":
                    bulan_range = [7, 8, 9]
                elif tribulan_filter == "Tribulan IV":
                    bulan_range = [10, 11, 12]

        with col4:
            puskesmas_filter = st.selectbox("🏥 Pilih Puskesmas", ["All"] + sorted(desa_df['Puskesmas'].unique()), help="Pilih Puskesmas atau 'All'.")

        with col5:
            kelurahan_options = ["All"]
            if puskesmas_filter != "All":
                kelurahan_options += sorted(desa_df[desa_df['Puskesmas'] == puskesmas_filter]['Kelurahan'].unique())
            kelurahan_filter = st.selectbox("🏡 Pilih Kelurahan", options=kelurahan_options, help="Pilih Kelurahan atau 'All'.")

    # Inisialisasi filtered_df
    filtered_df = df.copy()
    periode_label = ""

    # Terapkan filter tahun
    if tahun_filter != "All":
        try:
            tahun_filter_int = int(tahun_filter)
            if "Tahun" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["Tahun"] == tahun_filter_int]
                periode_label += f"Tahun {tahun_filter}"
            else:
                st.warning("⚠️ Tidak dapat memfilter tahun karena kolom 'Tahun' tidak ada.")
        except ValueError:
            st.error("⚠️ Pilihan tahun tidak valid.")
            filtered_df = df.copy()

    # Terapkan filter berdasarkan jenis laporan
    if jenis_laporan == "Bulanan" and bulan_filter != "All":
        try:
            bulan_filter_int = int(bulan_filter)
            if "Bulan" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["Bulan"] == bulan_filter_int]
                periode_label += f" Bulan {bulan_filter_int}" if periode_label else f"Bulan {bulan_filter_int}"
            else:
                st.warning("⚠️ Tidak dapat memfilter bulan karena kolom 'Bulan' tidak ada.")
        except ValueError:
            st.error("⚠️ Pilihan bulan tidak valid (harus berupa angka).")
            bulan_filter_int = None
    elif jenis_laporan == "Tahunan" and tribulan_filter is not None:
        if bulan_range is not None and "Bulan" in filtered_df.columns:
            available_months = df["Bulan"].unique()
            if not set(bulan_range).intersection(available_months):
                st.warning(f"⚠️ Tidak ada data untuk {tribulan_filter}. Dataset hanya tersedia untuk bulan {sorted(available_months)}.")
                filtered_df = pd.DataFrame()
            else:
                filtered_df = filtered_df[filtered_df["Bulan"].isin(bulan_range)]
                periode_label += f" {tribulan_filter}" if periode_label else tribulan_filter
        else:
            st.warning("⚠️ Tidak dapat memfilter tribulan karena kolom 'Bulan' tidak ada.")

    # Terapkan filter Puskesmas dan Kelurahan
    if puskesmas_filter != "All":
        filtered_df = filtered_df[filtered_df["Puskesmas"] == puskesmas_filter]
    if kelurahan_filter != "All":
        filtered_df = filtered_df[filtered_df["Kelurahan"] == kelurahan_filter]

    # Jika Laporan Tahunan, lakukan agregasi sum
    if jenis_laporan == "Tahunan" and not filtered_df.empty:
        group_columns = ["Puskesmas", "Kelurahan"]
        numeric_columns = [col for col in filtered_df.columns if filtered_df[col].dtype in ['int64', 'float64']]
        if numeric_columns:
            agg_dict = {col: "sum" for col in numeric_columns}
            filtered_df = filtered_df.groupby(group_columns).agg(agg_dict).reset_index()

    # Menu Utama dengan Tabs di Main Page
    st.subheader("📂 Pilih Dashboard")
    tab1, tab2 = st.tabs(["📊 Kelengkapan Data Laporan", "📈 Analisis Indikator Balita"])

    # Tab 1: Kelengkapan Data Laporan
    with tab1:
        st.subheader("🔍 Pilih Analisis")
        subtab1, subtab2 = st.tabs(["✅ Compliance Rate", "📋 Completeness Rate"])
        with subtab1:
            compliance_rate(filtered_df, desa_df, puskesmas_filter, kelurahan_filter)
        with subtab2:
            completeness_rate(filtered_df, desa_df, puskesmas_filter, kelurahan_filter)

    # Tab 2: Analisis Indikator Balita
    with tab2:
        st.subheader("🔍 Pilih Analisis")
        subtab1, subtab2, subtab3, subtab4, subtab5, subtab6 = st.tabs([
            "👶 Indikator Bayi Kecil",
            "📈 Pemantauan Tumbuh Kembang Balita",
            "📉 Pemantauan Tumbuh Kembang Apras",
            "🏥 Cakupan Layanan Kesehatan Balita",
            "🏡 Cakupan Layanan Kesehatan Apras",
            "🩺 Cakupan PKAT (Pemeriksaan Kesehatan Anak Terintegrasi)"
        ])
        with subtab1:
            indikator_bayi_kecil(filtered_df, desa_df, puskesmas_filter, kelurahan_filter, jenis_laporan, tahun_filter, bulan_filter_int, tribulan_filter)
        with subtab2:
            pemantauan_tumbuh_kembang_balita(filtered_df, desa_df, puskesmas_filter, kelurahan_filter, jenis_laporan, tahun_filter, bulan_filter_int, tribulan_filter)
        with subtab3:
            pemantauan_tumbuh_kembang_apras(filtered_df, desa_df, puskesmas_filter, kelurahan_filter, jenis_laporan, tahun_filter, bulan_filter_int, tribulan_filter)
        with subtab4:
            cakupan_layanan_kesehatan_balita(filtered_df, desa_df, puskesmas_filter, kelurahan_filter, jenis_laporan, tahun_filter, bulan_filter_int, tribulan_filter)
        with subtab5:
            cakupan_layanan_kesehatan_apras(filtered_df, desa_df, puskesmas_filter, kelurahan_filter, jenis_laporan, tahun_filter, bulan_filter_int, tribulan_filter)
        with subtab6:
            cakupan_pkat(filtered_df, desa_df, puskesmas_filter, kelurahan_filter, jenis_laporan, tahun_filter, bulan_filter_int, tribulan_filter)
    
    # Tampilkan data terfilter
        st.subheader("📝 Data Terfilter")
        if filtered_df.empty:
            st.warning("⚠️ Tidak ada data yang sesuai dengan filter.")
        else:
            st.dataframe(filtered_df, use_container_width=True)
    # Footer
    st.markdown(
        '<p style="text-align: center; font-size: 12px; color: grey;">'
        'made with ❤️ by <a href="mailto:dedik2urniawan@gmail.com">dedik2urniawan@gmail.com</a>'
        '</p>', unsafe_allow_html=True)