import streamlit as st
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
                 text="Compliance Rate (%)", title="📊 Compliance Rate per Puskesmas", color_discrete_sequence=["#00C49F"])
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
        "Cakupan Bayi Prematur & BBLR Mendapat Buku KIA (%)": (filtered_df['Jumlah_bayi_prematur_dan_BBLR_yang_mendapat_buku_KIA_bayi_kecil'].sum() / total_bayi * 100),
        "Cakupan Bayi BBLR Mendapat Tatalaksana (%)": (filtered_df['Jumlah_bayi_baru_lahir_dengan_BBLR_mendapat_tata_laksana'].sum() / total_bayi * 100),
        "Cakupan Bayi PBLR (%)": (filtered_df['Jumlah_Bayi_PBLR'].sum() / total_bayi * 100),
        "Cakupan Bayi LIKA Rendah (%)": (filtered_df['Jumlah_Bayi_LIKA_Rendah'].sum() / total_bayi * 100)
    }

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
    fig1.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", yaxis_range=[0, 100], title_x=0.5,
                       legend_title_text="Indikator", legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5),
                       height=500)
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader(f"📈 Grafik Cakupan Tatalaksana Bayi Kecil ({periode_label})")
    if puskesmas_filter == "All":
        grouped_df = filtered_df.groupby('Puskesmas').sum().reset_index()
        graph_data2 = pd.DataFrame({
            "Puskesmas": grouped_df['Puskesmas'],
            "Cakupan Buku KIA (%)": (grouped_df['Jumlah_bayi_prematur_dan_BBLR_yang_mendapat_buku_KIA_bayi_kecil'] / grouped_df['Jumlah_bayi_baru_lahir_hidup'] * 100).fillna(0),
            "Cakupan Tatalaksana (%)": (grouped_df['Jumlah_bayi_baru_lahir_dengan_BBLR_mendapat_tata_laksana'] / grouped_df['Jumlah_bayi_baru_lahir_hidup'] * 100).fillna(0)
        }).melt(id_vars=["Puskesmas"], var_name="Indikator", value_name="Persentase")
        fig2 = px.bar(graph_data2, x="Puskesmas", y="Persentase", color="Indikator", barmode="group",
                      title=f"Cakupan Tatalaksana Bayi Kecil per Puskesmas ({periode_label})", text=graph_data2["Persentase"].apply(lambda x: f"{x:.1f}%"))
    else:
        grouped_df = filtered_df.groupby('Kelurahan').sum().reset_index()
        graph_data2 = pd.DataFrame({
            "Kelurahan": grouped_df['Kelurahan'],
            "Cakupan Buku KIA (%)": (grouped_df['Jumlah_bayi_prematur_dan_BBLR_yang_mendapat_buku_KIA_bayi_kecil'] / grouped_df['Jumlah_bayi_baru_lahir_hidup'] * 100).fillna(0),
            "Cakupan Tatalaksana (%)": (grouped_df['Jumlah_bayi_baru_lahir_dengan_BBLR_mendapat_tata_laksana'] / grouped_df['Jumlah_bayi_baru_lahir_hidup'] * 100).fillna(0)
        }).melt(id_vars=["Kelurahan"], var_name="Indikator", value_name="Persentase")
        fig2 = px.bar(graph_data2, x="Kelurahan", y="Persentase", color="Indikator", barmode="group",
                      title=f"Cakupan Tatalaksana Bayi Kecil per Kelurahan di {puskesmas_filter} ({periode_label})", text=graph_data2["Persentase"].apply(lambda x: f"{x:.1f}%"))

    fig2.update_traces(textposition='outside')
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
    recap_df['Cakupan Bayi Prematur & BBLR Mendapat Buku KIA (%)'] = (recap_df['Jumlah_bayi_prematur_dan_BBLR_yang_mendapat_buku_KIA_bayi_kecil'] / recap_df['Jumlah_bayi_baru_lahir_hidup'] * 100).fillna(0).round(2)
    recap_df['Cakupan Bayi BBLR Mendapat Tatalaksana (%)'] = (recap_df['Jumlah_bayi_baru_lahir_dengan_BBLR_mendapat_tata_laksana'] / recap_df['Jumlah_bayi_baru_lahir_hidup'] * 100).fillna(0).round(2)
    recap_df['Cakupan Bayi PBLR (%)'] = (recap_df['Jumlah_Bayi_PBLR'] / recap_df['Jumlah_bayi_baru_lahir_hidup'] * 100).fillna(0).round(2)
    recap_df['Cakupan Bayi LIKA Rendah (%)'] = (recap_df['Jumlah_Bayi_LIKA_Rendah'] / recap_df['Jumlah_bayi_baru_lahir_hidup'] * 100).fillna(0).round(2)

    recap_display = recap_df[['Puskesmas', 'Kelurahan'] + list(indikator_data.keys())] if puskesmas_filter != "All" else recap_df[['Puskesmas'] + list(indikator_data.keys())]
    recap_display.insert(0, 'No', range(1, len(recap_display) + 1))
    st.dataframe(recap_display, use_container_width=True)

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
# ----------------------------- #
# 📈 Pemantauan Tumbuh Kembang Balita
# ----------------------------- #
def pemantauan_tumbuh_kembang_balita(filtered_df, desa_df, puskesmas_filter, kelurahan_filter, jenis_laporan, tahun_filter, bulan_filter_int=None, tribulan_filter=None):
    """Menampilkan analisis Pemantauan Tumbuh Kembang Balita dengan fitur download laporan."""
    st.header("📈 Pemantauan Tumbuh Kembang Balita")

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

    recap_display = recap_df[['Puskesmas', 'Kelurahan'] + list(metrik_data.keys())] if puskesmas_filter != "All" else recap_df[['Puskesmas'] + list(metrik_data.keys())]
    recap_display.insert(0, 'No', range(1, len(recap_display) + 1))
    st.dataframe(recap_display, use_container_width=True)

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

    # Inisialisasi periode untuk label
    periode_label = ""
    if tahun_filter != "All":
        periode_label += f"Tahun {tahun_filter}"
    if jenis_laporan == "Bulanan" and bulan_filter_int is not None:
        periode_label += f" Bulan {bulan_filter_int}" if periode_label else f"Bulan {bulan_filter_int}"
    elif jenis_laporan == "Tahunan" and tribulan_filter:
        periode_label += f" {tribulan_filter}" if periode_label else tribulan_filter

    # 1. Memuat data Jumlah_balita_punya_KIA dari data_balita_gizi
    try:
        conn = sqlite3.connect("rcs_data.db")
        gizi_df = pd.read_sql_query("SELECT Kelurahan, Bulan, Jumlah_balita_punya_KIA FROM data_balita_gizi", conn)
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
        gizi_df[['Kelurahan', 'Bulan', 'Jumlah_balita_punya_KIA']],
        on=['Kelurahan', 'Bulan'],
        how='left'
    )

    # Cek apakah ada data yang tidak match
    if merged_df['Jumlah_balita_punya_KIA'].isna().all():
        st.warning("⚠️ Tidak ada data Jumlah_balita_punya_KIA yang cocok dengan filter Kelurahan dan Bulan. Periksa data di data_balita_gizi!")
        return

    # Hitung total balita usia 12-59 bulan dan total terdeteksi gangguan
    total_balita = merged_df['Jumlah_balita_usia_12-59_bulan_sampai_bulan_ini'].sum()
    total_deteksi_gangguan = merged_df['Jumlah_balita_terdeteksi_gangguan_tumbang'].sum()
    total_punya_kia = merged_df['Jumlah_balita_punya_KIA'].sum()

    if total_balita == 0:
        st.warning("⚠️ Tidak ada data balita usia 12-59 bulan untuk filter ini.")
        return
    if total_deteksi_gangguan == 0 and 'Jumlah_balita_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi' in required_columns:
        st.warning("⚠️ Tidak ada data balita terdeteksi gangguan untuk filter ini.")
    if total_punya_kia == 0 and 'Jumlah_balita_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan' in required_columns:
        st.warning("⚠️ Tidak ada data balita yang memiliki Buku KIA untuk filter ini.")

    # Hitung metrik
    metrik_data = {
        "Metrik Balita dipantau pertumbuhan dan perkembangan (%)": (merged_df['Jumlah_balita_pantau_tumbang'].sum() / total_balita * 100),
        "Metrik balita yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)": (merged_df['Jumlah_balita_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi'].sum() / total_deteksi_gangguan * 100 if total_deteksi_gangguan else 0),
        "Metrik balita mendapat pelayanan SDIDTK di Fasyankes (%)": (merged_df['Jumlah_balita_mendapat_pelayanan_SDIDTK_di_FKTP'].sum() / total_balita * 100),
        "Metrik Balita yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)": (merged_df['Jumlah_balita_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan'].sum() / total_punya_kia * 100 if total_punya_kia else 0),
        "Metrik balita yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)": (merged_df['Jumlah_balita_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'].sum() / total_balita * 100)
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
                    metric: (grouped_df['Jumlah_balita_mendapat_pelayanan_SDIDTK_di_FKTP'] / grouped_df['Jumlah_balita_usia_12-59_bulan_sampai_bulan_ini'] * 100).fillna(0)
                })
            elif metric == "Metrik Balita yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)":
                graph_data = pd.DataFrame({
                    "Puskesmas": grouped_df['Puskesmas'],
                    metric: (grouped_df['Jumlah_balita_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan'] / grouped_df['Jumlah_balita_punya_KIA'] * 100).fillna(0)
                })
            elif metric == "Metrik balita yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)":
                graph_data = pd.DataFrame({
                    "Puskesmas": grouped_df['Puskesmas'],
                    metric: (grouped_df['Jumlah_balita_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'] / grouped_df['Jumlah_balita_usia_12-59_bulan_sampai_bulan_ini'] * 100).fillna(0)
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
                    metric: (grouped_df['Jumlah_balita_mendapat_pelayanan_SDIDTK_di_FKTP'] / grouped_df['Jumlah_balita_usia_12-59_bulan_sampai_bulan_ini'] * 100).fillna(0)
                })
            elif metric == "Metrik Balita yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)":
                graph_data = pd.DataFrame({
                    "Kelurahan": grouped_df['Kelurahan'],
                    metric: (grouped_df['Jumlah_balita_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan'] / grouped_df['Jumlah_balita_punya_KIA'] * 100).fillna(0)
                })
            elif metric == "Metrik balita yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)":
                graph_data = pd.DataFrame({
                    "Kelurahan": grouped_df['Kelurahan'],
                    metric: (grouped_df['Jumlah_balita_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'] / grouped_df['Jumlah_balita_usia_12-59_bulan_sampai_bulan_ini'] * 100).fillna(0)
                })
            fig = px.bar(graph_data, x="Kelurahan", y=metric, text=graph_data[metric].apply(lambda x: f"{x:.1f}%"),
                         title=f"{metric} per Kelurahan di {puskesmas_filter} ({periode_label})", color_discrete_sequence=["#1E90FF"])

        fig.update_traces(textposition='outside')
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

    recap_df['Metrik Balita dipantau pertumbuhan dan perkembangan (%)'] = (recap_df['Jumlah_balita_pantau_tumbang'] / recap_df['Jumlah_balita_usia_12-59_bulan_sampai_bulan_ini'] * 100).fillna(0).round(2)
    recap_df['Metrik balita yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)'] = (recap_df['Jumlah_balita_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi'] / recap_df['Jumlah_balita_terdeteksi_gangguan_tumbang'] * 100).fillna(0).round(2)
    recap_df['Metrik balita mendapat pelayanan SDIDTK di Fasyankes (%)'] = (recap_df['Jumlah_balita_mendapat_pelayanan_SDIDTK_di_FKTP'] / recap_df['Jumlah_balita_usia_12-59_bulan_sampai_bulan_ini'] * 100).fillna(0).round(2)
    recap_df['Metrik Balita yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)'] = (recap_df['Jumlah_balita_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan'] / recap_df['Jumlah_balita_punya_KIA'] * 100).fillna(0).round(2)
    recap_df['Metrik balita yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)'] = (recap_df['Jumlah_balita_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'] / recap_df['Jumlah_balita_usia_12-59_bulan_sampai_bulan_ini'] * 100).fillna(0).round(2)

    recap_display = recap_df[['Puskesmas', 'Kelurahan'] + list(metrik_data.keys())] if puskesmas_filter != "All" else recap_df[['Puskesmas'] + list(metrik_data.keys())]
    recap_display.insert(0, 'No', range(1, len(recap_display) + 1))
    st.dataframe(recap_display, use_container_width=True)

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

    # Inisialisasi periode untuk label
    periode_label = ""
    if tahun_filter != "All":
        periode_label += f"Tahun {tahun_filter}"
    if jenis_laporan == "Bulanan" and bulan_filter_int is not None:
        periode_label += f" Bulan {bulan_filter_int}" if periode_label else f"Bulan {bulan_filter_int}"
    elif jenis_laporan == "Tahunan" and tribulan_filter:
        periode_label += f" {tribulan_filter}" if periode_label else tribulan_filter

    # Daftar kolom yang dibutuhkan
    required_columns = [
        'Jumlah_Apras_terdeteksi_gangguan_tumbang',
        'Jumlah_Apras_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi',
        'Jumlah_Apras_mendapat_pelayanan_SDIDTK_di_FKTP',
        'Jumlah_anak_prasekolah_bulan_ini',
        'Jumlah_Apras_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan',
        'Jumlah_anak_prasekolah_punya_Buku_KIA',
        'Jumlah_Apras_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'
    ]

    # Cek apakah semua kolom ada
    missing_cols = [col for col in required_columns if col not in filtered_df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di dataset: {missing_cols}. Periksa data di 'data_balita_kia'!")
        return

    # Agregasi data berdasarkan jenis laporan
    if jenis_laporan == "Tahunan" and not filtered_df.empty:
        group_columns = ["Puskesmas", "Kelurahan"]
        numeric_columns = [col for col in filtered_df.columns if filtered_df[col].dtype in ['int64', 'float64']]
        if numeric_columns:
            agg_dict = {col: "sum" for col in numeric_columns}
            filtered_df = filtered_df.groupby(group_columns).agg(agg_dict).reset_index()

    # Hitung total Apras dan total terdeteksi gangguan
    total_apras = filtered_df['Jumlah_anak_prasekolah_bulan_ini'].sum()
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
        "Metrik Apras mendapat pelayanan SDIDTK di Fasyankes (%)": (filtered_df['Jumlah_Apras_mendapat_pelayanan_SDIDTK_di_FKTP'].sum() / total_apras * 100),
        "Metrik Apras yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)": (filtered_df['Jumlah_Apras_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan'].sum() / total_apras_dengan_buku_kia * 100 if total_apras_dengan_buku_kia else 0),
        "Metrik Apras yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)": (filtered_df['Jumlah_Apras_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'].sum() / total_apras * 100)
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
            grouped_df = filtered_df.groupby('Puskesmas').sum().reset_index()
            if metric == "Metrik Apras yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)":
                graph_data = pd.DataFrame({
                    "Puskesmas": grouped_df['Puskesmas'],
                    metric: (grouped_df['Jumlah_Apras_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi'] / grouped_df['Jumlah_Apras_terdeteksi_gangguan_tumbang'] * 100).fillna(0)
                })
            elif metric == "Metrik Apras mendapat pelayanan SDIDTK di Fasyankes (%)":
                graph_data = pd.DataFrame({
                    "Puskesmas": grouped_df['Puskesmas'],
                    metric: (grouped_df['Jumlah_Apras_mendapat_pelayanan_SDIDTK_di_FKTP'] / grouped_df['Jumlah_anak_prasekolah_bulan_ini'] * 100).fillna(0)
                })
            elif metric == "Metrik Apras yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)":
                graph_data = pd.DataFrame({
                    "Puskesmas": grouped_df['Puskesmas'],
                    metric: (grouped_df['Jumlah_Apras_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan'] / grouped_df['Jumlah_anak_prasekolah_punya_Buku_KIA'] * 100).fillna(0)
                })
            elif metric == "Metrik Apras yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)":
                graph_data = pd.DataFrame({
                    "Puskesmas": grouped_df['Puskesmas'],
                    metric: (grouped_df['Jumlah_Apras_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'] / grouped_df['Jumlah_anak_prasekolah_bulan_ini'] * 100).fillna(0)
                })
            fig = px.bar(graph_data, x="Puskesmas", y=metric, text=graph_data[metric].apply(lambda x: f"{x:.1f}%"),
                         title=f"{metric} per Puskesmas ({periode_label})", color_discrete_sequence=["#32CD32"])
        else:
            grouped_df = filtered_df.groupby('Kelurahan').sum().reset_index()
            if metric == "Metrik Apras yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)":
                graph_data = pd.DataFrame({
                    "Kelurahan": grouped_df['Kelurahan'],
                    metric: (grouped_df['Jumlah_Apras_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi'] / grouped_df['Jumlah_Apras_terdeteksi_gangguan_tumbang'] * 100).fillna(0)
                })
            elif metric == "Metrik Apras mendapat pelayanan SDIDTK di Fasyankes (%)":
                graph_data = pd.DataFrame({
                    "Kelurahan": grouped_df['Kelurahan'],
                    metric: (grouped_df['Jumlah_Apras_mendapat_pelayanan_SDIDTK_di_FKTP'] / grouped_df['Jumlah_anak_prasekolah_bulan_ini'] * 100).fillna(0)
                })
            elif metric == "Metrik Apras yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)":
                graph_data = pd.DataFrame({
                    "Kelurahan": grouped_df['Kelurahan'],
                    metric: (grouped_df['Jumlah_Apras_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan'] / grouped_df['Jumlah_anak_prasekolah_punya_Buku_KIA'] * 100).fillna(0)
                })
            elif metric == "Metrik Apras yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)":
                graph_data = pd.DataFrame({
                    "Kelurahan": grouped_df['Kelurahan'],
                    metric: (grouped_df['Jumlah_Apras_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'] / grouped_df['Jumlah_anak_prasekolah_bulan_ini'] * 100).fillna(0)
                })
            fig = px.bar(graph_data, x="Kelurahan", y=metric, text=graph_data[metric].apply(lambda x: f"{x:.1f}%"),
                         title=f"{metric} per Kelurahan di {puskesmas_filter} ({periode_label})", color_discrete_sequence=["#32CD32"])

        fig.update_traces(textposition='outside')
        fig.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", yaxis_range=[0, 100], title_x=0.5,
                          height=400)
        st.plotly_chart(fig, use_container_width=True)
        figures_list.append(fig)  # Simpan setiap fig ke daftar

    # 3. Tabel Rekapitulasi
    st.subheader(f"📋 Tabel Rekapitulasi Cakupan Layanan Kesehatan Apras ({periode_label})")
    if puskesmas_filter == "All":
        recap_df = filtered_df.groupby('Puskesmas').sum().reset_index()
    else:
        recap_df = filtered_df.groupby(['Puskesmas', 'Kelurahan']).sum().reset_index()

    recap_df['Metrik Apras yang terdeteksi ada gangguan atau penyimpangan perkembangan yang mendapat intervensi (%)'] = (recap_df['Jumlah_Apras_yang_terdeteksi_gangguan_tumbang_mendapat_intervensi'] / recap_df['Jumlah_Apras_terdeteksi_gangguan_tumbang'] * 100).fillna(0).round(2)
    recap_df['Metrik Apras mendapat pelayanan SDIDTK di Fasyankes (%)'] = (recap_df['Jumlah_Apras_mendapat_pelayanan_SDIDTK_di_FKTP'] / recap_df['Jumlah_anak_prasekolah_bulan_ini'] * 100).fillna(0).round(2)
    recap_df['Metrik Apras yang Buku KIA nya terisi lengkap bagian pemantauan perkembangan (%)'] = (recap_df['Jumlah_Apras_Buku_KIA_terisi_lengkap_bagian_pemantauan_perkembangan'] / recap_df['Jumlah_anak_prasekolah_punya_Buku_KIA'] * 100).fillna(0).round(2)
    recap_df['Metrik Apras yang ibu/orangtua/wali/keluarga/pengasuh telah mengikuti minimal 4 (empat) kali kelas ibu balita (%)'] = (recap_df['Jumlah_Apras_ortu_mengikuti_minimal_4_kali_kelas_ibu_balita'] / recap_df['Jumlah_anak_prasekolah_bulan_ini'] * 100).fillna(0).round(2)

    recap_display = recap_df[['Puskesmas', 'Kelurahan'] + list(metrik_data.keys())] if puskesmas_filter != "All" else recap_df[['Puskesmas'] + list(metrik_data.keys())]
    recap_display.insert(0, 'No', range(1, len(recap_display) + 1))
    st.dataframe(recap_display, use_container_width=True)

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
    fig.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", yaxis_range=[0, 100], title_x=0.5, height=400)
    st.plotly_chart(fig, use_container_width=True)
    figures_list.append(fig)

    # 3. Tabel Rekapitulasi
    st.subheader(f"📋 Tabel Rekapitulasi Cakupan PKAT ({periode_label})")
    if puskesmas_filter == "All":
        recap_df = merged_df.groupby('Puskesmas').sum().reset_index()
    else:
        recap_df = merged_df.groupby(['Puskesmas', 'Kelurahan']).sum().reset_index()

    # Hitung metrik
    recap_df[metric] = (recap_df['Cakupan_bayi_dilayani_PKAT'] / recap_df['Jumlah_Bayi_usia_6_bulan'] * 100).fillna(0).round(2)

    # Siapkan kolom untuk ditampilkan
    recap_display = recap_df[['Puskesmas', 'Kelurahan', 'Jumlah_Bayi_usia_6_bulan', 'Cakupan_bayi_dilayani_PKAT', metric]] if puskesmas_filter != "All" else recap_df[['Puskesmas', 'Jumlah_Bayi_usia_6_bulan', 'Cakupan_bayi_dilayani_PKAT', metric]]

    # Tambahkan kolom nomor urut
    recap_display.insert(0, 'No', range(1, len(recap_display) + 1))

    # Tampilkan tabel
    st.dataframe(recap_display, use_container_width=True)

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

    # Footer
    st.markdown(
        '<p style="text-align: center; font-size: 12px; color: grey;">'
        'made with ❤️ by <a href="mailto:dedik2urniawan@gmail.com">dedik2urniawan@gmail.com</a>'
        '</p>', unsafe_allow_html=True)