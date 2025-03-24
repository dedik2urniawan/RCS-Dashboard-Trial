import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os
import datetime
import time
import plotly.graph_objects as go
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
import io
from plotly.io import to_image

# ----------------------------- #
# 📥 Fungsi untuk load data
# ----------------------------- #
@st.cache_data
def load_data():
    """Memuat data dari database SQLite rcs_data.db."""
    try:
        conn = sqlite3.connect("rcs_data.db")
        df = pd.read_sql_query("SELECT * FROM data_balita_gizi", conn)
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
    """Menghitung dan menampilkan tingkat kelengkapan data."""
    st.header("📋 Completeness Rate")
    completeness_columns = [
        "Jumlah_sasaran_balita", "Jumlah_balita_bulan_ini", "Jumlah_balita_ditimbang",
        "Jumlah_balita_ditimbang_dan_diukur", "Jumlah_balita_diukur_PBTB", "Jumlah_balita_punya_KIA",
        "Jumlah_balita_naik_berat_badannya_N", "Jumlah_balita_tidak_naik_berat_badannya_T",
        "Jumlah_balita_tidak_ditimbang_bulan_lalu_O", "Jumlah_bayi_baru_lahir_bulan_ini_B",
        "Jumlah_balita_ditimbang_terkoreksi_Daksen", "Jumlah_balita_stunting", "Jumlah_balita_wasting",
        "Jumlah_balita_overweight", "Jumlah_balita_underweight", "Jumlah_Bayi_Mendapat_IMD",
        "Jumlah_Bayi_usia_0-5_bulan", "Jumlah_Bayi_usia_0-5_bulan_yang_direcall",
        "Jumlah_Bayi_usia_0-5_bulan_yang_mendapat_ASI_Eksklusif_berdasarkan_recall_24_jam"
    ]

    missing_cols = [col for col in completeness_columns if col not in filtered_df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di dataset: {missing_cols}")
        return

    filtered_df['Lengkap'] = filtered_df[completeness_columns].notna().all(axis=1)

    if kelurahan_filter != "All":
        scope = filtered_df[filtered_df['Kelurahan'] == kelurahan_filter]
    elif puskesmas_filter != "All":
        scope = filtered_df[filtered_df['Puskesmas'] == puskesmas_filter]
    else:
        scope = filtered_df

    lengkap_count = scope['Lengkap'].sum()
    total_entries = scope.shape[0]
    completeness_value = (lengkap_count / total_entries * 100) if total_entries else 0

    st.metric(label="Completeness Rate (%)", value=f"{completeness_value:.2f}%")

    completeness_data = []
    for puskesmas in sorted(desa_df['Puskesmas'].unique()):
        df_pkm = filtered_df[filtered_df['Puskesmas'] == puskesmas]
        total_entries_pkm = df_pkm.shape[0]
        lengkap_entries_pkm = df_pkm['Lengkap'].sum()
        rate = (lengkap_entries_pkm / total_entries_pkm * 100) if total_entries_pkm else 0
        completeness_data.append({
            "Puskesmas": puskesmas,
            "Jumlah Entry": total_entries_pkm,
            "Entry Lengkap": lengkap_entries_pkm,
            "Completeness Rate (%)": f"{rate:.2f}%"
        })

    completeness_df = pd.DataFrame(completeness_data)
    st.subheader("📊 Tabel Completeness Rate per Puskesmas")
    st.dataframe(completeness_df, use_container_width=True)

    st.subheader("📈 Visualisasi Completeness Rate per Puskesmas")
    completeness_df["Completeness Rate (%)"] = completeness_df["Completeness Rate (%)"].str.rstrip('%').astype(float)
    fig_completeness = px.bar(completeness_df, x="Puskesmas", y="Completeness Rate (%)", text="Completeness Rate (%)",
                             title="📊 Completeness Rate per Puskesmas", color_discrete_sequence=["#FF6F61"])
    fig_completeness.update_traces(textposition='outside')
    fig_completeness.update_layout(xaxis_tickangle=-45, yaxis_title="Completeness Rate (%)", xaxis_title="Puskesmas",
                                 yaxis_range=[0, 110], title_x=0.5, height=500)
    st.plotly_chart(fig_completeness, key=f"completeness_chart_{puskesmas_filter}_{kelurahan_filter}_{time.time()}", use_container_width=True)
    
    # Detail kelengkapan per kolom (opsional)
    if st.checkbox("🔍 Tampilkan Detail Kelengkapan per Kolom"):
        completeness_per_col = filtered_df[completeness_columns].notna().mean() * 100
        st.subheader("📋 Persentase Kelengkapan per Kolom")
        col_data = [{"Kolom": col, "Kelengkapan (%)": f"{val:.2f}%"} 
                   for col, val in completeness_per_col.items()]
        st.dataframe(pd.DataFrame(col_data), use_container_width=True)
# ----------------------------- #
# 📊 Analisis Pertumbuhan & Perkembangan
# ----------------------------- #
def calculate_metric(current, previous):
    """Menghitung perbedaan antara nilai saat ini dan sebelumnya dengan indikator panah."""
    if previous == 0 or pd.isna(previous) or pd.isna(current):
        return current, ""
    delta = current - previous
    icon = "🔼" if delta > 0 else "🔽"
    return current, f"{icon} {abs(delta):.2f}%"

def growth_development_metrics(filtered_df, previous_df, desa_df, puskesmas_filter, kelurahan_filter, bulan_filter):
    """Menghitung metrik pertumbuhan & perkembangan balita dan mengembalikan data untuk PDF."""
    total_bulan_ini = filtered_df["Jumlah_balita_bulan_ini"].sum()
    total_sasaran = filtered_df["Jumlah_sasaran_balita"].sum()
    total_ditimbang_terkoreksi = filtered_df["Jumlah_balita_ditimbang_terkoreksi_Daksen"].sum()

    prev_total_bulan_ini = previous_df["Jumlah_balita_bulan_ini"].sum() if not previous_df.empty else 0
    prev_total_sasaran = previous_df["Jumlah_sasaran_balita"].sum() if not previous_df.empty else 0
    prev_total_ditimbang_terkoreksi = previous_df["Jumlah_balita_ditimbang_terkoreksi_Daksen"].sum() if not previous_df.empty else 0

    try:
        metrics = {
            "Balita ditimbang (Proyeksi)": calculate_metric(
                filtered_df["Jumlah_balita_ditimbang"].sum() / total_sasaran * 100 if total_sasaran else 0,
                previous_df["Jumlah_balita_ditimbang"].sum() / prev_total_sasaran * 100 if prev_total_sasaran else 0
            ),
            "Balita ditimbang (Data Rill)": calculate_metric(
                filtered_df["Jumlah_balita_ditimbang"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0,
                previous_df["Jumlah_balita_ditimbang"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
            "Balita ditimbang & diukur": calculate_metric(
                filtered_df["Jumlah_balita_ditimbang_dan_diukur"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0,
                previous_df["Jumlah_balita_ditimbang_dan_diukur"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
            "Balita diukur PB/TB": calculate_metric(
                filtered_df["Jumlah_balita_diukur_PBTB"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0,
                previous_df["Jumlah_balita_diukur_PBTB"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
            "Balita memiliki Buku KIA": calculate_metric(
                filtered_df["Jumlah_balita_punya_KIA"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0,
                previous_df["Jumlah_balita_punya_KIA"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
            "Balita Naik BB": calculate_metric(
                filtered_df["Jumlah_balita_naik_berat_badannya_N"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0,
                previous_df["Jumlah_balita_naik_berat_badannya_N"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
            "Balita Naik dengan D Koreksi": calculate_metric(
                filtered_df["Jumlah_balita_naik_berat_badannya_N"].sum() / total_ditimbang_terkoreksi * 100 if total_ditimbang_terkoreksi else 0,
                previous_df["Jumlah_balita_naik_berat_badannya_N"].sum() / prev_total_ditimbang_terkoreksi * 100 if prev_total_ditimbang_terkoreksi else 0
            ),
            "Balita Tidak Naik BB": calculate_metric(
                filtered_df["Jumlah_balita_tidak_naik_berat_badannya_T"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0,
                previous_df["Jumlah_balita_tidak_naik_berat_badannya_T"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
            "Balita Tidak Timbang Bulan Lalu": calculate_metric(
                filtered_df["Jumlah_balita_tidak_ditimbang_bulan_lalu_O"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0,
                previous_df["Jumlah_balita_tidak_ditimbang_bulan_lalu_O"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
            "Prevalensi Stunting": calculate_metric(
                filtered_df["Jumlah_balita_stunting"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0,
                previous_df["Jumlah_balita_stunting"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
            "Prevalensi Wasting": calculate_metric(
                filtered_df["Jumlah_balita_wasting"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0,
                previous_df["Jumlah_balita_wasting"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
            "Prevalensi Underweight": calculate_metric(
                filtered_df["Jumlah_balita_underweight"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0,
                previous_df["Jumlah_balita_underweight"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
            "Prevalensi Overweight": calculate_metric(
                filtered_df["Jumlah_balita_overweight"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0,
                previous_df["Jumlah_balita_overweight"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
        }
    except Exception as e:
        st.error(f"Error menghitung metrik: {e}")
        return {}, pd.DataFrame(), None, None

    st.subheader("📊 Metrik Pertumbuhan & Perkembangan Balita")
    col1, col2, col3 = st.columns(3)
    for idx, (label, (value, change)) in enumerate(metrics.items()):
        with (col1 if idx % 3 == 0 else col2 if idx % 3 == 1 else col3):
            st.metric(label, f"{value:.2f}%", delta=change)

    # Bar chart
    metrics_df = pd.DataFrame({"Metrik": list(metrics.keys()), "Persentase": [val[0] for val in metrics.values()]})
    fig_bar = px.bar(metrics_df, x="Metrik", y="Persentase", text="Persentase", title="📊 Metrik Pertumbuhan & Perkembangan Balita", color="Metrik")
    fig_bar.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_bar, key=f"bar_chart_{puskesmas_filter}_{kelurahan_filter}_{time.time()}", use_container_width=True)

    # Tabel Rekapitulasi
    summary_df = filtered_df.groupby("Puskesmas").agg({
        "Jumlah_sasaran_balita": "sum",
        "Jumlah_balita_bulan_ini": "sum",
        "Jumlah_balita_ditimbang_dan_diukur": "sum",
        "Jumlah_balita_naik_berat_badannya_N": "sum",
        "Jumlah_balita_ditimbang_terkoreksi_Daksen": "sum",
        "Jumlah_balita_ditimbang": "sum"
    }).reset_index()

    summary_df["% Balita ditimbang dan diukur"] = (summary_df["Jumlah_balita_ditimbang_dan_diukur"] / summary_df["Jumlah_balita_bulan_ini"] * 100).round(2)
    summary_df["% N/D koreksi"] = (summary_df["Jumlah_balita_naik_berat_badannya_N"] / summary_df["Jumlah_balita_ditimbang_terkoreksi_Daksen"] * 100).round(2)
    summary_df["% N/D rill"] = (summary_df["Jumlah_balita_naik_berat_badannya_N"] / summary_df["Jumlah_balita_ditimbang"] * 100).round(2)

    summary_df = summary_df[["Puskesmas", "Jumlah_sasaran_balita", "Jumlah_balita_bulan_ini",
                           "% Balita ditimbang dan diukur", "% N/D koreksi", "% N/D rill"]]
    st.subheader("📋 Rekapitulasi Metrik Data Pertumbuhan")
    st.dataframe(summary_df, use_container_width=True)

    # Tren Visualisasi
    st.subheader("📊 Tren %D/S, %N/D koreksi, dan %N/D riil per Puskesmas")
    line_chart_data = summary_df.melt(id_vars=["Puskesmas"], value_vars=["% Balita ditimbang dan diukur", "% N/D koreksi", "% N/D rill"],
                                    var_name="Metrik", value_name="Persentase")
    fig_line = px.line(line_chart_data, x="Puskesmas", y="Persentase", color="Metrik", markers=True, text="Persentase",
                      title="📊 Tren %D/S, %N/D koreksi, dan %N/D riil per Puskesmas")
    fig_line.update_traces(textposition="top center")
    fig_line.add_hline(y=85, line_dash="dash", line_color="green", annotation_text="Target %D/S = 85%", annotation_position="top left")
    fig_line.add_hline(y=88, line_dash="dash", line_color="purple", annotation_text="Target %N/D = 88%", annotation_position="top right")
    st.plotly_chart(fig_line, key=f"line_chart_{puskesmas_filter}_{kelurahan_filter}_{time.time()}", use_container_width=True)

    # Mengembalikan data untuk PDF
    return metrics, summary_df, fig_bar, fig_line

# ----------------------------- #
# 🍼 Analisis ASI Eksklusif & MPASI
# ----------------------------- #
def calculate_asi_metric(current, previous):
    """Menghitung perbedaan antara nilai saat ini dan sebelumnya dengan tanda panah."""
    if previous == 0 or pd.isna(previous) or pd.isna(current):
        return current, ""
    delta = current - previous
    icon = "🔼" if delta > 0 else "🔽"
    return current, f"{icon} {abs(delta):.2f}%"

def asi_exclusive_mpasi_analysis(filtered_df, previous_df, desa_df, puskesmas_filter, kelurahan_filter, bulan_filter):
    """Menganalisis capaian ASI Eksklusif dan MPASI."""
    st.header("🍼 Analisis ASI Eksklusif & MPASI")

    if filtered_df.empty:
        st.warning("⚠️ Tidak ada data untuk ditampilkan.")
        return {}, pd.DataFrame(), []

    # Periksa ketersediaan kolom yang dibutuhkan
    required_columns = [
        "Jumlah_Bayi_Mendapat_IMD", "Jumlah_bayi_baru_lahir_bulan_ini_B",
        "Jumlah_Bayi_Asi_Eksklusif_sampai_6_bulan", "Jumlah_Bayi_usia_6_bulan",
        "Jumlah_Bayi_usia_0-5_bulan_yang_mendapat_ASI_Eksklusif_berdasarkan_recall_24_jam",
        "Jumlah_Bayi_usia_0-5_bulan_yang_direcall", "Jumlah_Bayi_usia_0-5_bulan",
        "Jumlah_anak_usia_6-23_bulan_yang_diwawancarai", "Jumlah_anak_usia_6-23_bulan",
        "Jumlah_anak_usia_6-23_bulan_yang_mengkonsumsi_makanan_dan_minuman_setidaknya_5_dari_8_jenis_kelompok_makanan_pada_hari_kemarin_sebelum_wawancara",
        "Jumlah_anak_usia_6-23_bulan_yang_mengkonsumsi_telur_ikan_dan_atau_daging_pada_hari_kemarin_sebelum_wawancara",
        "Jumlah_anak_usia_6-23_bulan_yang_mendapat_MPASI_baik"
    ]
    missing_cols = [col for col in required_columns if col not in filtered_df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di dataset: {missing_cols}")
        return {}, pd.DataFrame(), []

    # Menghitung metrik
    group_columns = ["Puskesmas"]
    if puskesmas_filter != "All":
        group_columns.append("Kelurahan")

    # Data saat ini
    current_df = filtered_df.groupby(group_columns).agg({
        "Jumlah_Bayi_Mendapat_IMD": "sum",
        "Jumlah_bayi_baru_lahir_bulan_ini_B": "sum",
        "Jumlah_Bayi_Asi_Eksklusif_sampai_6_bulan": "sum",
        "Jumlah_Bayi_usia_6_bulan": "sum",
        "Jumlah_Bayi_usia_0-5_bulan_yang_mendapat_ASI_Eksklusif_berdasarkan_recall_24_jam": "sum",
        "Jumlah_Bayi_usia_0-5_bulan_yang_direcall": "sum",
        "Jumlah_Bayi_usia_0-5_bulan": "sum",
        "Jumlah_anak_usia_6-23_bulan_yang_diwawancarai": "sum",
        "Jumlah_anak_usia_6-23_bulan": "sum",
        "Jumlah_anak_usia_6-23_bulan_yang_mengkonsumsi_makanan_dan_minuman_setidaknya_5_dari_8_jenis_kelompok_makanan_pada_hari_kemarin_sebelum_wawancara": "sum",
        "Jumlah_anak_usia_6-23_bulan_yang_mengkonsumsi_telur_ikan_dan_atau_daging_pada_hari_kemarin_sebelum_wawancara": "sum",
        "Jumlah_anak_usia_6-23_bulan_yang_mendapat_MPASI_baik": "sum"
    }).reset_index()

    # Hitung metrik untuk data saat ini
    current_df["Metrik Bayi Mendapat IMD (%)"] = current_df.apply(
        lambda x: (x["Jumlah_Bayi_Mendapat_IMD"] / x["Jumlah_bayi_baru_lahir_bulan_ini_B"] * 100)
        if x["Jumlah_bayi_baru_lahir_bulan_ini_B"] != 0 else 0, axis=1
    ).round(2)

    current_df["Metrik Jumlah Bayi ASI Eksklusif Sampai 6 Bulan (%)"] = current_df.apply(
        lambda x: (x["Jumlah_Bayi_Asi_Eksklusif_sampai_6_bulan"] / x["Jumlah_Bayi_usia_6_bulan"] * 100)
        if x["Jumlah_Bayi_usia_6_bulan"] != 0 else 0, axis=1
    ).round(2)

    current_df["Metrik Bayi 0-5 Bulan ASI Eksklusif Recall 24 Jam (%)"] = current_df.apply(
        lambda x: (x["Jumlah_Bayi_usia_0-5_bulan_yang_mendapat_ASI_Eksklusif_berdasarkan_recall_24_jam"] / x["Jumlah_Bayi_usia_0-5_bulan_yang_direcall"] * 100)
        if x["Jumlah_Bayi_usia_0-5_bulan_yang_direcall"] != 0 else 0, axis=1
    ).round(2)

    current_df["Metrik Proporsi Sampling Bayi 0-5 Bulan Recall ASI (%)"] = current_df.apply(
        lambda x: (x["Jumlah_Bayi_usia_0-5_bulan_yang_direcall"] / x["Jumlah_Bayi_usia_0-5_bulan"] * 100)
        if x["Jumlah_Bayi_usia_0-5_bulan"] != 0 else 0, axis=1
    ).round(2)

    current_df["Metrik Rerata Jumlah Anak Usia 6-23 Bulan yang Diwawancarai (%)"] = current_df.apply(
        lambda x: (x["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"] / x["Jumlah_anak_usia_6-23_bulan"] * 100)
        if x["Jumlah_anak_usia_6-23_bulan"] != 0 else 0, axis=1
    ).round(2)

    current_df["Metrik Anak Usia 6-23 Bulan Konsumsi 5 dari 8 Kelompok Makanan (%)"] = current_df.apply(
        lambda x: (x["Jumlah_anak_usia_6-23_bulan_yang_mengkonsumsi_makanan_dan_minuman_setidaknya_5_dari_8_jenis_kelompok_makanan_pada_hari_kemarin_sebelum_wawancara"] / x["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"] * 100)
        if x["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"] != 0 else 0, axis=1
    ).round(2)

    current_df["Metrik Anak Usia 6-23 Bulan Konsumsi Telur, Ikan, Daging (%)"] = current_df.apply(
        lambda x: (x["Jumlah_anak_usia_6-23_bulan_yang_mengkonsumsi_telur_ikan_dan_atau_daging_pada_hari_kemarin_sebelum_wawancara"] / x["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"] * 100)
        if x["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"] != 0 else 0, axis=1
    ).round(2)

    current_df["Metrik Anak Usia 6-23 Bulan Mendapat MPASI Baik (%)"] = current_df.apply(
        lambda x: (x["Jumlah_anak_usia_6-23_bulan_yang_mendapat_MPASI_baik"] / x["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"] * 100)
        if x["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"] != 0 else 0, axis=1
    ).round(2)

    # Daftar metrik untuk dashboard
    metrics_list = [
        "Metrik Bayi Mendapat IMD (%)",
        "Metrik Jumlah Bayi ASI Eksklusif Sampai 6 Bulan (%)",
        "Metrik Bayi 0-5 Bulan ASI Eksklusif Recall 24 Jam (%)",
        "Metrik Proporsi Sampling Bayi 0-5 Bulan Recall ASI (%)",
        "Metrik Rerata Jumlah Anak Usia 6-23 Bulan yang Diwawancarai (%)",
        "Metrik Anak Usia 6-23 Bulan Konsumsi 5 dari 8 Kelompok Makanan (%)",
        "Metrik Anak Usia 6-23 Bulan Konsumsi Telur, Ikan, Daging (%)",
        "Metrik Anak Usia 6-23 Bulan Mendapat MPASI Baik (%)"
    ]

    # Hitung metrik dengan perbandingan ke data sebelumnya
    metrics = {}
    if not previous_df.empty:  # Hanya hitung delta jika ada data bulan sebelumnya
        previous_data = previous_df.groupby(group_columns).agg({
            "Jumlah_Bayi_Mendapat_IMD": "sum",
            "Jumlah_bayi_baru_lahir_bulan_ini_B": "sum",
            "Jumlah_Bayi_Asi_Eksklusif_sampai_6_bulan": "sum",
            "Jumlah_Bayi_usia_6_bulan": "sum",
            "Jumlah_Bayi_usia_0-5_bulan_yang_mendapat_ASI_Eksklusif_berdasarkan_recall_24_jam": "sum",
            "Jumlah_Bayi_usia_0-5_bulan_yang_direcall": "sum",
            "Jumlah_Bayi_usia_0-5_bulan": "sum",
            "Jumlah_anak_usia_6-23_bulan_yang_diwawancarai": "sum",
            "Jumlah_anak_usia_6-23_bulan": "sum",
            "Jumlah_anak_usia_6-23_bulan_yang_mengkonsumsi_makanan_dan_minuman_setidaknya_5_dari_8_jenis_kelompok_makanan_pada_hari_kemarin_sebelum_wawancara": "sum",
            "Jumlah_anak_usia_6-23_bulan_yang_mengkonsumsi_telur_ikan_dan_atau_daging_pada_hari_kemarin_sebelum_wawancara": "sum",
            "Jumlah_anak_usia_6-23_bulan_yang_mendapat_MPASI_baik": "sum"
        }).reset_index()

        previous_data["Metrik Bayi Mendapat IMD (%)"] = previous_data.apply(
            lambda x: (x["Jumlah_Bayi_Mendapat_IMD"] / x["Jumlah_bayi_baru_lahir_bulan_ini_B"] * 100)
            if x["Jumlah_bayi_baru_lahir_bulan_ini_B"] != 0 else 0, axis=1
        ).round(2)

        previous_data["Metrik Jumlah Bayi ASI Eksklusif Sampai 6 Bulan (%)"] = previous_data.apply(
            lambda x: (x["Jumlah_Bayi_Asi_Eksklusif_sampai_6_bulan"] / x["Jumlah_Bayi_usia_6_bulan"] * 100)
            if x["Jumlah_Bayi_usia_6_bulan"] != 0 else 0, axis=1
        ).round(2)

        previous_data["Metrik Bayi 0-5 Bulan ASI Eksklusif Recall 24 Jam (%)"] = previous_data.apply(
            lambda x: (x["Jumlah_Bayi_usia_0-5_bulan_yang_mendapat_ASI_Eksklusif_berdasarkan_recall_24_jam"] / x["Jumlah_Bayi_usia_0-5_bulan_yang_direcall"] * 100)
            if x["Jumlah_Bayi_usia_0-5_bulan_yang_direcall"] != 0 else 0, axis=1
        ).round(2)

        previous_data["Metrik Proporsi Sampling Bayi 0-5 Bulan Recall ASI (%)"] = previous_data.apply(
            lambda x: (x["Jumlah_Bayi_usia_0-5_bulan_yang_direcall"] / x["Jumlah_Bayi_usia_0-5_bulan"] * 100)
            if x["Jumlah_Bayi_usia_0-5_bulan"] != 0 else 0, axis=1
        ).round(2)

        previous_data["Metrik Rerata Jumlah Anak Usia 6-23 Bulan yang Diwawancarai (%)"] = previous_data.apply(
            lambda x: (x["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"] / x["Jumlah_anak_usia_6-23_bulan"] * 100)
            if x["Jumlah_anak_usia_6-23_bulan"] != 0 else 0, axis=1
        ).round(2)

        previous_data["Metrik Anak Usia 6-23 Bulan Konsumsi 5 dari 8 Kelompok Makanan (%)"] = previous_data.apply(
            lambda x: (x["Jumlah_anak_usia_6-23_bulan_yang_mengkonsumsi_makanan_dan_minuman_setidaknya_5_dari_8_jenis_kelompok_makanan_pada_hari_kemarin_sebelum_wawancara"] / x["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"] * 100)
            if x["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"] != 0 else 0, axis=1
        ).round(2)

        previous_data["Metrik Anak Usia 6-23 Bulan Konsumsi Telur, Ikan, Daging (%)"] = previous_data.apply(
            lambda x: (x["Jumlah_anak_usia_6-23_bulan_yang_mengkonsumsi_telur_ikan_dan_atau_daging_pada_hari_kemarin_sebelum_wawancara"] / x["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"] * 100)
            if x["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"] != 0 else 0, axis=1
        ).round(2)

        previous_data["Metrik Anak Usia 6-23 Bulan Mendapat MPASI Baik (%)"] = previous_data.apply(
            lambda x: (x["Jumlah_anak_usia_6-23_bulan_yang_mendapat_MPASI_baik"] / x["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"] * 100)
            if x["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"] != 0 else 0, axis=1
        ).round(2)

        # Hitung delta untuk setiap metrik
        for metric in metrics_list:
            current_value = current_df[metric].mean()  # Rata-rata nilai saat ini
            previous_value = previous_data[metric].mean() if not previous_data.empty else 0  # Rata-rata nilai sebelumnya, 0 jika tidak ada data
            delta = current_value - previous_value if previous_value != 0 else 0
            icon = "🔼" if delta > 0 else "🔽" if delta < 0 else ""
            metrics[metric] = (current_value, f"{icon} {abs(delta):.2f}%" if previous_value != 0 else "")
    else:
        # Jika tidak ada data sebelumnya, hanya tampilkan nilai saat ini tanpa delta
        for metric in metrics_list:
            current_value = current_df[metric].mean()
            metrics[metric] = (current_value, "")

    # Tampilkan metrik di dashboard
    st.subheader("📊 Metrik ASI Eksklusif & MPASI")
    col1, col2 = st.columns(2)
    for idx, (label, (value, change)) in enumerate(metrics.items()):
        with (col1 if idx % 2 == 0 else col2):
            st.metric(label, f"{value:.2f}%", delta=change)

    # Visualisasi Grafik (tidak diubah, tetap menggunakan current_df)
    st.subheader("📊 Grafik Capaian ASI Eksklusif & MPASI")
    charts = []
    metrics_to_plot = metrics_list
    if puskesmas_filter == "All":
        for idx, metric in enumerate(metrics_to_plot):
            st.subheader(f"📊 {metric} per Puskesmas")
            fig = px.bar(current_df, x="Puskesmas", y=metric, title=f"{metric} per Puskesmas", 
                        text=current_df[metric].round(2).astype(str) + "%", labels={metric: "Persentase (%)"})
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, key=f"asi_chart_{metric}_all_{idx}_{time.time()}", use_container_width=True)
            charts.append(fig)
    elif kelurahan_filter == "All":
        for idx, metric in enumerate(metrics_to_plot):
            st.subheader(f"📊 {metric} per Kelurahan di {puskesmas_filter}")
            fig = px.bar(current_df, x="Kelurahan", y=metric, title=f"{metric} per Kelurahan di {puskesmas_filter}", 
                        text=current_df[metric].round(2).astype(str) + "%", labels={metric: "Persentase (%)"})
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, key=f"asi_chart_{metric}_{puskesmas_filter}_{idx}_{time.time()}", use_container_width=True)
            charts.append(fig)
    else:
        for idx, metric in enumerate(metrics_to_plot):
            st.subheader(f"📊 {metric} di {kelurahan_filter}, {puskesmas_filter}")
            kel_df = current_df[current_df["Kelurahan"] == kelurahan_filter]
            fig = px.bar(kel_df, x="Kelurahan", y=metric, title=f"{metric} di {kelurahan_filter}, {puskesmas_filter}", 
                        text=kel_df[metric].round(2).astype(str) + "%", labels={metric: "Persentase (%)"})
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, key=f"asi_chart_{metric}_{kelurahan_filter}_{puskesmas_filter}_{idx}_{time.time()}", use_container_width=True)
            charts.append(fig)

    # Tabel Rekapitulasi
    st.subheader("📋 Rekapitulasi Capaian ASI Eksklusif & MPASI")
    if current_df.empty:
        st.warning("⚠️ Tidak ada data untuk Puskesmas atau Kelurahan yang dipilih. Rekapitulasi tidak dapat ditampilkan.")
        summary_df = pd.DataFrame(columns=group_columns + metrics_list)
    else:
        summary_df = current_df[group_columns + metrics_list]
    st.dataframe(summary_df, use_container_width=True)

    return metrics, summary_df, charts
# ----------------------------- #
# 🥗 Analisis Masalah Gizi
# ----------------------------- #
def nutrition_issues_analysis(filtered_df, previous_df, desa_df, puskesmas_filter, kelurahan_filter, bulan_filter):
    """Menganalisis masalah gizi (stunting, wasting, underweight, overweight) dan menghasilkan laporan PDF."""
    st.header("🥗 Analisis Masalah Gizi")

    if filtered_df.empty:
        st.warning("⚠️ Tidak ada data untuk ditampilkan.")
        return {}, pd.DataFrame(), None, []

    # Tambahkan keterangan tentang target nilai
    st.info(
        """
        📌 **Catatan Penting tentang Target Prevalensi Gizi:**  
        - **Stunting**: Target maksimal 14% (Kita ingin angka ini tetap rendah untuk kesehatan balita!)  
        - **Wasting**: Target maksimal 7% (Pastikan balita terhindar dari kekurangan gizi akut!)  
        - **Underweight**: Target maksimal 15% (Mari jaga berat badan balita ideal!)  
        - **Overweight**: Target maksimal 4% (Keseimbangan gizi sangat penting!)  
        Nilai target ini adalah panduan untuk menilai status gizi balita. Periksa metrik di bawah untuk melihat apakah kita di bawah atau di atas target! 😊
        """
    )
    
    # Definisi target prevalensi
    target_values = {
        "Prevalensi Stunting": 14,
        "Prevalensi Wasting": 7,
        "Prevalensi Underweight": 15,
        "Prevalensi Overweight": 4
    }

    # Menghitung prevalensi
    group_columns = ["Puskesmas"]
    if puskesmas_filter != "All":
        group_columns.append("Kelurahan")

    prev_df = filtered_df.groupby(group_columns).agg({
        "Jumlah_balita_stunting": "sum",
        "Jumlah_balita_wasting": "sum",
        "Jumlah_balita_underweight": "sum",
        "Jumlah_balita_overweight": "sum",
        "Jumlah_balita_diukur_PBTB": "sum",
        "Jumlah_balita_ditimbang_dan_diukur": "sum",
        "Jumlah_balita_ditimbang": "sum"
    }).reset_index()

    prev_df["Prevalensi Stunting"] = (prev_df["Jumlah_balita_stunting"] / prev_df["Jumlah_balita_diukur_PBTB"] * 100).round(2)
    prev_df["Prevalensi Wasting"] = (prev_df["Jumlah_balita_wasting"] / prev_df["Jumlah_balita_ditimbang_dan_diukur"] * 100).round(2)
    prev_df["Prevalensi Underweight"] = (prev_df["Jumlah_balita_underweight"] / prev_df["Jumlah_balita_ditimbang"] * 100).round(2)
    prev_df["Prevalensi Overweight"] = (prev_df["Jumlah_balita_overweight"] / prev_df["Jumlah_balita_ditimbang_dan_diukur"] * 100).round(2)

    # Hitung metrik perbandingan dengan target
    metrics = {}
    for metric, target in target_values.items():
        current_value = prev_df[metric].mean()  # Rata-rata prevalensi
        previous_value = 0 if previous_df.empty else previous_df.groupby(group_columns).agg({
            "Jumlah_balita_stunting": "sum",
            "Jumlah_balita_wasting": "sum",
            "Jumlah_balita_underweight": "sum",
            "Jumlah_balita_overweight": "sum",
            "Jumlah_balita_diukur_PBTB": "sum",
            "Jumlah_balita_ditimbang_dan_diukur": "sum",
            "Jumlah_balita_ditimbang": "sum"
        }).reset_index().apply(
            lambda x: (x["Jumlah_balita_stunting"] / x["Jumlah_balita_diukur_PBTB"] * 100) if metric == "Prevalensi Stunting" else
                      (x["Jumlah_balita_wasting"] / x["Jumlah_balita_ditimbang_dan_diukur"] * 100) if metric == "Prevalensi Wasting" else
                      (x["Jumlah_balita_underweight"] / x["Jumlah_balita_ditimbang"] * 100) if metric == "Prevalensi Underweight" else
                      (x["Jumlah_balita_overweight"] / x["Jumlah_balita_ditimbang_dan_diukur"] * 100), axis=1
        ).mean()

        delta = current_value - target
        status = "✅ Di bawah target" if current_value <= target else "⚠️ Di atas target"
        metrics[metric] = (current_value, f"{status} ({delta:+.2f}%)")

    # Tampilkan metrik
    st.subheader("📊 Metrik Prevalensi Masalah Gizi")
    col1, col2 = st.columns(2)
    for idx, (label, (value, status)) in enumerate(metrics.items()):
        with (col1 if idx % 2 == 0 else col2):
            st.metric(label, f"{value:.2f}%", delta=status)

    # Visualisasi Grafik Pertama (Grouped Bar Chart)
    st.subheader("📊 Grafik Prevalensi Masalah Gizi")
    if prev_df.empty:
        st.warning("⚠️ Tidak ada data untuk membuat grafik prevalensi masalah gizi.")
        fig = None
    else:
        melted_df = prev_df.melt(id_vars=group_columns, value_vars=list(target_values.keys()), var_name="Metrik", value_name="Persentase")
        fig = px.bar(melted_df, x="Puskesmas", y="Persentase", color="Metrik", barmode="group", text="Persentase",
                 title="📊 Prevalensi Stunting, Wasting, Underweight, dan Overweight per Puskesmas")
        fig.update_traces(textposition="outside")
        for metric, target in target_values.items():
            fig.add_hline(y=target, line_dash="dash", line_color="red",
                      annotation_text=f"Target {metric} = {target}%", annotation_position="top right")
        fig.update_layout(xaxis_tickangle=-45, yaxis_title="Persentase (%)", height=600)
        st.plotly_chart(fig, key=f"nutrition_issues_chart_{puskesmas_filter}_{kelurahan_filter}_{time.time()}", use_container_width=True)

    # Visualisasi Grafik Kedua (Grafik Prevalensi Status Gizi per Metrik)
    st.subheader("📊 Grafik Prevalensi Status Gizi per Metrik")
    prevalence_charts = []  # List untuk menyimpan grafik prevalensi
    if prev_df.empty:
        st.warning("⚠️ Tidak ada data untuk membuat grafik prevalensi status gizi per metrik.")
    else:
        if puskesmas_filter == "All":
            for idx, title in enumerate(target_values.keys()):
                st.subheader(f"📊 {title} per Puskesmas")
                fig_prev = px.bar(prev_df, x="Puskesmas", y=title, title=f"{title} per Puskesmas", text=title, labels={title: "Persentase (%)"})
                fig_prev.update_traces(textposition="outside")
                fig_prev.add_hline(y=target_values[title], line_dash="dash", line_color="red",
                               annotation_text=f"Target {title} = {target_values[title]}%", annotation_position="top right")
                st.plotly_chart(fig_prev, key=f"prev_chart_{title}_all_{idx}_{time.time()}", use_container_width=True)
                prevalence_charts.append(fig_prev)
        elif kelurahan_filter == "All":
            for idx, title in enumerate(target_values.keys()):
                st.subheader(f"📊 {title} per Kelurahan di {puskesmas_filter}")
                fig_prev = px.bar(prev_df, x="Kelurahan", y=title, title=f"{title} per Kelurahan di {puskesmas_filter}", text=title, labels={title: "Persentase (%)"})
                fig_prev.update_traces(textposition="outside")
                fig_prev.add_hline(y=target_values[title], line_dash="dash", line_color="red",
                                annotation_text=f"Target {title} = {target_values[title]}%", annotation_position="top right")
                st.plotly_chart(fig_prev, key=f"prev_chart_{title}_{puskesmas_filter}_{idx}_{time.time()}", use_container_width=True)
                prevalence_charts.append(fig_prev)
        else:
            for idx, title in enumerate(target_values.keys()):
                st.subheader(f"📊 {title} di {kelurahan_filter}, {puskesmas_filter}")
                kel_df = prev_df[prev_df["Kelurahan"] == kelurahan_filter]
                fig_prev = px.bar(kel_df, x="Kelurahan", y=title, title=f"{title} di {kelurahan_filter}, {puskesmas_filter}", text=title, labels={title: "Persentase (%)"})
                fig_prev.update_traces(textposition="outside")
                fig_prev.add_hline(y=target_values[title], line_dash="dash", line_color="red",
                                annotation_text=f"Target {title} = {target_values[title]}%", annotation_position="top right")
                st.plotly_chart(fig_prev, key=f"prev_chart_{title}_{kelurahan_filter}_{puskesmas_filter}_{idx}_{time.time()}", use_container_width=True)
                prevalence_charts.append(fig_prev)

    # Tabel Rekapitulasi
    st.subheader("📋 Rekapitulasi Prevalensi Masalah Gizi")
    if prev_df.empty:
        st.warning("⚠️ Tidak ada data untuk rekapitulasi prevalensi masalah gizi.")
        summary_df = pd.DataFrame(columns=group_columns + list(target_values.keys()))  # DataFrame kosong tanpa baris
    else:
        summary_df = prev_df[group_columns + list(target_values.keys())].copy()  # Gunakan .copy() untuk menghindari masalah referensi

    st.dataframe(summary_df, use_container_width=True)
    return metrics, summary_df, fig, prevalence_charts

# ----------------------------- #
# 🧑‍⚕️ Tatalaksana Balita Bermasalah Gizi
# ----------------------------- #
def tatalaksana_balita_bermasalah_gizi_analysis(df, desa_df, bulan_filter_int, puskesmas_filter, kelurahan_filter):
    st.header("🧑‍⚕️ Analisis Tatalaksana Balita Bermasalah Gizi")

    # Filter data berdasarkan bulan, puskesmas, dan kelurahan
    filtered_df = df[df["Bulan"] == bulan_filter_int].copy() if bulan_filter_int is not None else df.copy()
    if puskesmas_filter != "All":
        filtered_df = filtered_df[filtered_df["Puskesmas"] == puskesmas_filter]
    if kelurahan_filter != "All":
        filtered_df = filtered_df[filtered_df["Kelurahan"] == kelurahan_filter]

    # Pastikan data tidak kosong
    if filtered_df.empty:
        st.warning("⚠️ Tidak ada data untuk filter yang dipilih.")
        return {}, pd.DataFrame(), []

    # Kolom yang diperlukan
    required_columns = [
        "Jumlah_balita_gizi_kurang_usia_6-59_bulan_yang_mendapatkan_makanan_tambahan_berbahan_pangan_lokal_sampai_bulan_ini",
        "Jumlah_seluruh_balita_(usia_6-59_bulan)_gizi_kurang_dengan_atau_tanpa_stunting_sampai_bulan_ini",
        "Jumlah_balita_BB_kurang_usia_6-59_bulan_yang_mendapatkan_makanan_tambahan_berbahan_pangan_lokal",
        "Jumlah_seluruh_balita_(usia_6-59_bulan)_BB_kurang_yang_tidak_wasting_dengan_atau_tanpa_stunting_dan_tanpa_wasting",
        "Jumlah_Balita_T659_mendapatkan_PMT",
        "Jumlah_sasaran_balita_T",
        "Jumlah_Kasus_Gizi_Buruk_bayi_0-5_Bulan_mendapat_perawatan_sampai_bulan_ini",
        "Jumlah_kasus_gizi_buruk_bayi_0-5_Bulan_sampai_bulan_ini",
        "Jumlah_Kasus_Gizi_Buruk_Balita_6-59_Bulan_mendapat_perawatan_sampai_bulan_ini",
        "Jumlah_kasus_gizi_buruk_Balita_6-59_Bulan_sampai_bulan_ini",
        "Jumlah_balita_stunting_dirujuk_Puskesmas_ke_RS_sampai_bulan_ini",
        "Jumlah_balita_stunting_sampai_bulan_ini"
    ]
    missing_cols = [col for col in required_columns if col not in filtered_df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di dataset: {missing_cols}")
        return {}, pd.DataFrame(), []

    # Hitung metrik
    group_columns = ["Puskesmas"]
    if puskesmas_filter != "All":
        group_columns.append("Kelurahan")  # Tambahkan "Kelurahan" untuk breakdown
    summary_df = filtered_df.groupby(group_columns).agg({
        col: "sum" for col in required_columns
    }).reset_index()

    # Hitung persentase untuk setiap metrik
    metrics_list = {
        "Balita Gizi Kurang (Wasting) 6-59 Bulan Mendapat PMT (%)": (
            "Jumlah_balita_gizi_kurang_usia_6-59_bulan_yang_mendapatkan_makanan_tambahan_berbahan_pangan_lokal_sampai_bulan_ini",
            "Jumlah_seluruh_balita_(usia_6-59_bulan)_gizi_kurang_dengan_atau_tanpa_stunting_sampai_bulan_ini"
        ),
        "Balita BB Kurang (Underweight) 6-59 Bulan Mendapat PMT (%)": (
            "Jumlah_balita_BB_kurang_usia_6-59_bulan_yang_mendapatkan_makanan_tambahan_berbahan_pangan_lokal",
            "Jumlah_seluruh_balita_(usia_6-59_bulan)_BB_kurang_yang_tidak_wasting_dengan_atau_tanpa_stunting_dan_tanpa_wasting"
        ),
        "Balita BB Tidak Naik (T) 6-59 Bulan Mendapat PMT (%)": (
            "Jumlah_Balita_T659_mendapatkan_PMT",
            "Jumlah_sasaran_balita_T"
        ),
        "Kasus Gizi Buruk Bayi 0-5 Bulan Mendapat Perawatan (%)": (
            "Jumlah_Kasus_Gizi_Buruk_bayi_0-5_Bulan_mendapat_perawatan_sampai_bulan_ini",
            "Jumlah_kasus_gizi_buruk_bayi_0-5_Bulan_sampai_bulan_ini"
        ),
        "Kasus Gizi Buruk Balita 6-59 Bulan Mendapat Perawatan (%)": (
            "Jumlah_Kasus_Gizi_Buruk_Balita_6-59_Bulan_mendapat_perawatan_sampai_bulan_ini",
            "Jumlah_kasus_gizi_buruk_Balita_6-59_Bulan_sampai_bulan_ini"
        ),
        "Balita Stunting Dirujuk ke RS (%)": (
            "Jumlah_balita_stunting_dirujuk_Puskesmas_ke_RS_sampai_bulan_ini",
            "Jumlah_balita_stunting_sampai_bulan_ini"
        )
    }

    for metric_name, (numerator, denominator) in metrics_list.items():
        summary_df[metric_name] = (summary_df[numerator] / summary_df[denominator].replace(0, pd.NA) * 100).fillna(0).round(2)

    # Hitung metrik rata-rata untuk dashboard
    metrics = {}
    for metric_name in metrics_list.keys():
        current_value = summary_df[metric_name].mean()
        metrics[metric_name] = (current_value, "")

    # Tampilkan metrik di dashboard
    st.subheader("📊 Metrik Tatalaksana Balita Bermasalah Gizi")
    col1, col2, col3 = st.columns(3)
    for idx, (label, (value, _)) in enumerate(metrics.items()):
        with (col1 if idx % 3 == 0 else col2 if idx % 3 == 1 else col3):
            st.metric(label, f"{value:.2f}%")

    # Definisikan dua kelompok variabel untuk grafik
    pmt_metrics = [
        "Balita Gizi Kurang (Wasting) 6-59 Bulan Mendapat PMT (%)",
        "Balita BB Kurang (Underweight) 6-59 Bulan Mendapat PMT (%)",
        "Balita BB Tidak Naik (T) 6-59 Bulan Mendapat PMT (%)"
    ]
    malnutrisi_metrics = [
        "Kasus Gizi Buruk Bayi 0-5 Bulan Mendapat Perawatan (%)",
        "Kasus Gizi Buruk Balita 6-59 Bulan Mendapat Perawatan (%)",
        "Balita Stunting Dirujuk ke RS (%)"
    ]

    # Siapkan DataFrame untuk grafik (melt untuk multiple bars)
    chart_df = summary_df.melt(
        id_vars=group_columns,
        value_vars=pmt_metrics + malnutrisi_metrics,
        var_name="Metrik",
        value_name="Persentase"
    )

    # Grafik Terpisah
    st.subheader("📊 Grafik Tatalaksana Balita Bermasalah Gizi")
    charts = []

    # Grafik 1: Intervensi PMT
    pmt_df = chart_df[chart_df["Metrik"].isin(pmt_metrics)]
    if puskesmas_filter == "All":
        fig_pmt = px.bar(
            pmt_df,
            x="Puskesmas",
            y="Persentase",
            color="Metrik",
            barmode="group",
            title="Intervensi PMT per Puskesmas",
            text=pmt_df["Persentase"].round(2).astype(str) + "%",
            labels={"Persentase": "Persentase (%)"}
        )
    elif kelurahan_filter == "All":
        fig_pmt = px.bar(
            pmt_df,
            x="Kelurahan",
            y="Persentase",
            color="Metrik",
            barmode="group",
            title=f"Intervensi PMT per Kelurahan di {puskesmas_filter}",
            text=pmt_df["Persentase"].round(2).astype(str) + "%",
            labels={"Persentase": "Persentase (%)"}
        )
    else:
        fig_pmt = px.bar(
            pmt_df,
            x="Kelurahan",
            y="Persentase",
            color="Metrik",
            barmode="group",
            title=f"Intervensi PMT di {kelurahan_filter}, {puskesmas_filter}",
            text=pmt_df["Persentase"].round(2).astype(str) + "%",
            labels={"Persentase": "Persentase (%)"}
        )
    fig_pmt.update_traces(textposition="outside")
    fig_pmt.update_layout(
        xaxis_tickangle=-45,
        yaxis_range=[0, 110],
        height=500,
        legend_title_text="Metrik PMT",
        legend_orientation="h",  # Mengatur legend horizontal
        legend=dict(y=-0.2, x=0, xanchor="left"),  # Memindahkan legend ke bawah
    )
    st.plotly_chart(fig_pmt, key=f"tatalaksana_pmt_chart_{time.time()}", use_container_width=True)

    # Grafik 2: Tatalaksana Balita Malnutrisi
    malnutrisi_df = chart_df[chart_df["Metrik"].isin(malnutrisi_metrics)]
    if puskesmas_filter == "All":
        fig_malnutrisi = px.bar(
            malnutrisi_df,
            x="Puskesmas",
            y="Persentase",
            color="Metrik",
            barmode="group",
            title="Tatalaksana Balita Malnutrisi per Puskesmas",
            text=malnutrisi_df["Persentase"].round(2).astype(str) + "%",
            labels={"Persentase": "Persentase (%)"}
        )
    elif kelurahan_filter == "All":
        fig_malnutrisi = px.bar(
            malnutrisi_df,
            x="Kelurahan",
            y="Persentase",
            color="Metrik",
            barmode="group",
            title=f"Tatalaksana Balita Malnutrisi per Kelurahan di {puskesmas_filter}",
            text=malnutrisi_df["Persentase"].round(2).astype(str) + "%",
            labels={"Persentase": "Persentase (%)"}
        )
    else:
        fig_malnutrisi = px.bar(
            malnutrisi_df,
            x="Kelurahan",
            y="Persentase",
            color="Metrik",
            barmode="group",
            title=f"Tatalaksana Balita Malnutrisi di {kelurahan_filter}, {puskesmas_filter}",
            text=malnutrisi_df["Persentase"].round(2).astype(str) + "%",
            labels={"Persentase": "Persentase (%)"}
        )
    fig_malnutrisi.update_traces(textposition="outside")
    fig_malnutrisi.update_layout(
        xaxis_tickangle=-45,
        yaxis_range=[0, 110],
        height=500,
        legend_title_text="Metrik Malnutrisi",
        legend_orientation="h",  # Mengatur legend horizontal
        legend=dict(y=-0.2, x=0, xanchor="left"),  # Memindahkan legend ke bawah
    )
    st.plotly_chart(fig_malnutrisi, key=f"tatalaksana_malnutrisi_chart_{time.time()}", use_container_width=True)

    # Tabel Rekapitulasi
    st.subheader("📋 Rekapitulasi Tatalaksana Balita Bermasalah Gizi")
    st.dataframe(summary_df, use_container_width=True)

    return metrics, summary_df, charts
# ----------------------------- #
# 🥗 Suplementasi Zat Gizi Micronutrients
# ----------------------------- #
def micronutrient_supplementation_analysis(filtered_df, previous_df, desa_df, puskesmas_filter, kelurahan_filter, bulan_filter_int):
    """Menganalisis suplementasi zat gizi mikro untuk balita."""
    st.header("💊 Analisis Suplementasi Zat Gizi Mikro")

    if filtered_df.empty:
        st.warning("⚠️ Tidak ada data untuk ditampilkan.")
        return {}, pd.DataFrame(), None, None

    # Periksa ketersediaan kolom yang dibutuhkan
    required_columns = [
        "Jumlah_bayi_6-11_bulan_mendapat_Vitamin_A", "Jumlah_bayi_6-11_bulan",
        "Jumlah_anak_12-59_bulan_mendapat_Vitamin_A", "Jumlah_anak_12-59_bulan",
        "Jumlah_balita_yang_mendapatkan_suplementasi_gizi_mikro", "Jumlah_balita_Underweight_suplemen"
    ]
    missing_cols = [col for col in required_columns if col not in filtered_df.columns]
    if missing_cols:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di dataset: {missing_cols}")
        return {}, pd.DataFrame(), None, None

    # Grouping berdasarkan Puskesmas atau Kelurahan
    group_columns = ["Puskesmas"]
    if puskesmas_filter != "All":
        group_columns.append("Kelurahan")

    current_df = filtered_df.groupby(group_columns).agg({
        "Jumlah_bayi_6-11_bulan_mendapat_Vitamin_A": "sum",
        "Jumlah_bayi_6-11_bulan": "sum",
        "Jumlah_anak_12-59_bulan_mendapat_Vitamin_A": "sum",
        "Jumlah_anak_12-59_bulan": "sum",
        "Jumlah_balita_yang_mendapatkan_suplementasi_gizi_mikro": "sum",
        "Jumlah_balita_Underweight_suplemen": "sum"
    }).reset_index()

    # Hitung metrik
    current_df["Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)"] = (current_df["Jumlah_bayi_6-11_bulan_mendapat_Vitamin_A"] / current_df["Jumlah_bayi_6-11_bulan"].replace(0, pd.NA) * 100).fillna(0).round(2)
    current_df["Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)"] = (current_df["Jumlah_anak_12-59_bulan_mendapat_Vitamin_A"] / current_df["Jumlah_anak_12-59_bulan"].replace(0, pd.NA) * 100).fillna(0).round(2)
    current_df["Metrik Balita yang Mendapatkan Suplementasi Gizi Mikro (%)"] = (current_df["Jumlah_balita_yang_mendapatkan_suplementasi_gizi_mikro"] / current_df["Jumlah_balita_Underweight_suplemen"].replace(0, pd.NA) * 100).fillna(0).round(2)

    # Tambahkan metrik cakupan tahunan Vitamin A hanya untuk bulan 8
    if bulan_filter_int == 8 and "Jumlah_anak_6-59_bulan_mendapat_Vitamin_A" in filtered_df.columns and "Jumlah_anak_6-59_bulan" in filtered_df.columns:
        current_df["Jumlah Cakupan Anak 6-59 Bulan Mendapat Vitamin A Tahunan (%)"] = (
            current_df["Jumlah_anak_6-59_bulan_mendapat_Vitamin_A"] / current_df["Jumlah_anak_6-59_bulan"].replace(0, pd.NA) * 100
        ).fillna(0).round(2)
    else:
        current_df["Jumlah Cakupan Anak 6-59 Bulan Mendapat Vitamin A Tahunan (%)"] = 0.0

    # Tentukan metrics_list berdasarkan bulan
    if bulan_filter_int == 8:
        metrics_list = [
            "Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)",
            "Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)",
            "Metrik Balita yang Mendapatkan Suplementasi Gizi Mikro (%)",
            "Jumlah Cakupan Anak 6-59 Bulan Mendapat Vitamin A Tahunan (%)"
        ]
    else:
        metrics_list = [
            "Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)",
            "Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)",
            "Metrik Balita yang Mendapatkan Suplementasi Gizi Mikro (%)"
        ]

    # Hitung metrik dengan perbandingan ke data sebelumnya dan target 91%
    target_vitamin_a = 91.0  # Target Vitamin A dalam persen
    metrics = {}
    if not previous_df.empty:
        previous_data = previous_df.groupby(group_columns).agg({
            "Jumlah_bayi_6-11_bulan_mendapat_Vitamin_A": "sum",
            "Jumlah_bayi_6-11_bulan": "sum",
            "Jumlah_anak_12-59_bulan_mendapat_Vitamin_A": "sum",
            "Jumlah_anak_12-59_bulan": "sum",
            "Jumlah_balita_yang_mendapatkan_suplementasi_gizi_mikro": "sum",
            "Jumlah_balita_Underweight_suplemen": "sum"
        }).reset_index()

        # Hitung metrik untuk previous_data
        previous_data["Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)"] = (previous_data["Jumlah_bayi_6-11_bulan_mendapat_Vitamin_A"] / previous_data["Jumlah_bayi_6-11_bulan"].replace(0, pd.NA) * 100).fillna(0).round(2)
        previous_data["Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)"] = (previous_data["Jumlah_anak_12-59_bulan_mendapat_Vitamin_A"] / previous_data["Jumlah_anak_12-59_bulan"].replace(0, pd.NA) * 100).fillna(0).round(2)
        previous_data["Metrik Balita yang Mendapatkan Suplementasi Gizi Mikro (%)"] = (previous_data["Jumlah_balita_yang_mendapatkan_suplementasi_gizi_mikro"] / previous_data["Jumlah_balita_Underweight_suplemen"].replace(0, pd.NA) * 100).fillna(0).round(2)
        # Tambahkan metrik tahunan hanya jika bulan 8
        if bulan_filter_int == 8 and "Jumlah_anak_6-59_bulan_mendapat_Vitamin_A" in previous_df.columns and "Jumlah_anak_6-59_bulan" in previous_df.columns:
            previous_data["Jumlah Cakupan Anak 6-59 Bulan Mendapat Vitamin A Tahunan (%)"] = (
                previous_data["Jumlah_anak_6-59_bulan_mendapat_Vitamin_A"] / previous_data["Jumlah_anak_6-59_bulan"].replace(0, pd.NA) * 100
            ).fillna(0).round(2)
        else:
            previous_data["Jumlah Cakupan Anak 6-59 Bulan Mendapat Vitamin A Tahunan (%)"] = 0.0

        for metric in metrics_list:
            current_value = current_df[metric].mean()
            previous_value = previous_data[metric].mean() if metric in previous_data.columns else 0
            delta = current_value - previous_value if previous_value != 0 else 0
            icon = "🔼" if delta > 0 else "🔽" if delta < 0 else ""
            metrics[metric] = (current_value, f"{icon} {abs(delta):.2f}% vs Target ({target_vitamin_a}%)")
    else:
        for metric in metrics_list:
            current_value = current_df[metric].mean()
            delta = current_value - target_vitamin_a
            icon = "🔼" if delta > 0 else "🔽" if delta < 0 else ""
            metrics[metric] = (current_value, f"{icon} {abs(delta):.2f}% vs Target ({target_vitamin_a}%)")

    # Tampilkan metrik
    st.subheader("📊 Metrik Suplementasi Gizi Mikro")
    col1, col2 = st.columns(2)
    for idx, (label, (value, change)) in enumerate(metrics.items()):
        with (col1 if idx % 2 == 0 else col2):
            st.metric(label, f"{value:.2f}%", delta=change)

    # Grafik Utama: Cakupan Suplementasi Zat Gizi Mikro
    st.subheader("📊 Grafik Suplementasi Zat Gizi Mikro")
    fig = go.Figure()
    if current_df.empty:
        st.warning("⚠️ Tidak ada data untuk grafik Suplementasi Zat Gizi Mikro.")
    else:
        if puskesmas_filter != "All" and kelurahan_filter == "All":
            kelurahan_data = filtered_df[filtered_df["Puskesmas"] == puskesmas_filter].groupby("Kelurahan").agg({
                "Jumlah_bayi_6-11_bulan_mendapat_Vitamin_A": "sum",
                "Jumlah_bayi_6-11_bulan": "sum",
                "Jumlah_anak_12-59_bulan_mendapat_Vitamin_A": "sum",
                "Jumlah_anak_12-59_bulan": "sum",
                "Jumlah_balita_yang_mendapatkan_suplementasi_gizi_mikro": "sum",
                "Jumlah_balita_Underweight_suplemen": "sum"
            }).reset_index()

            kelurahan_data["Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)"] = (kelurahan_data["Jumlah_bayi_6-11_bulan_mendapat_Vitamin_A"] / kelurahan_data["Jumlah_bayi_6-11_bulan"].replace(0, pd.NA) * 100).fillna(0).round(2)
            kelurahan_data["Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)"] = (kelurahan_data["Jumlah_anak_12-59_bulan_mendapat_Vitamin_A"] / kelurahan_data["Jumlah_anak_12-59_bulan"].replace(0, pd.NA) * 100).fillna(0).round(2)
            kelurahan_data["Metrik Balita yang Mendapatkan Suplementasi Gizi Mikro (%)"] = (kelurahan_data["Jumlah_balita_yang_mendapatkan_suplementasi_gizi_mikro"] / kelurahan_data["Jumlah_balita_Underweight_suplemen"].replace(0, pd.NA) * 100).fillna(0).round(2)

            if bulan_filter_int is None or bulan_filter_int in [2, 8]:
                fig.add_trace(go.Bar(
                    x=kelurahan_data["Kelurahan"],
                    y=kelurahan_data["Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)"],
                    name="Bayi 6-11 Bulan",
                    text=kelurahan_data["Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)"],
                    textposition='auto',
                    marker_color='#1f77b4'
                ))
                fig.add_trace(go.Bar(
                    x=kelurahan_data["Kelurahan"],
                    y=kelurahan_data["Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)"],
                    name="Anak 12-59 Bulan",
                    text=kelurahan_data["Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)"],
                    textposition='auto',
                    marker_color='#ff0000'
                ))
            if bulan_filter_int == 8:
                fig.add_trace(go.Bar(
                    x=kelurahan_data["Kelurahan"],
                    y=kelurahan_data["Jumlah Cakupan Anak 6-59 Bulan Mendapat Vitamin A Tahunan (%)"],
                    name="Vitamin A Tahunan 6-59 Bulan",
                    text=kelurahan_data["Jumlah Cakupan Anak 6-59 Bulan Mendapat Vitamin A Tahunan (%)"],
                    textposition='auto',
                    marker_color='#ff9900'
                ))
            fig.add_trace(go.Bar(
                x=kelurahan_data["Kelurahan"],
                y=kelurahan_data["Metrik Balita yang Mendapatkan Suplementasi Gizi Mikro (%)"],
                name="Suplementasi Gizi Mikro",
                text=kelurahan_data["Metrik Balita yang Mendapatkan Suplementasi Gizi Mikro (%)"],
                textposition='auto',
                marker_color='#00ff00'
            ))
            fig.update_layout(
                title=f"Cakupan Suplementasi Zat Gizi Mikro per Kelurahan di {puskesmas_filter}",
                xaxis_title="Kelurahan",
                yaxis_title="Persentase (%)",
                barmode='group',
                bargap=0.15,
                xaxis_tickangle=-45
            )
        elif kelurahan_filter != "All":
            kelurahan_data = current_df[current_df["Kelurahan"] == kelurahan_filter]

            if bulan_filter_int is None or bulan_filter_int in [2, 8]:
                fig.add_trace(go.Bar(
                    x=[kelurahan_filter],
                    y=kelurahan_data["Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)"],
                    name="Bayi 6-11 Bulan",
                    text=kelurahan_data["Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)"],
                    textposition='auto',
                    marker_color='#1f77b4'
                ))
                fig.add_trace(go.Bar(
                    x=[kelurahan_filter],
                    y=kelurahan_data["Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)"],
                    name="Anak 12-59 Bulan",
                    text=kelurahan_data["Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)"],
                    textposition='auto',
                    marker_color='#ff0000'
                ))
            if bulan_filter_int == 8:
                fig.add_trace(go.Bar(
                    x=[kelurahan_filter],
                    y=kelurahan_data["Jumlah Cakupan Anak 6-59 Bulan Mendapat Vitamin A Tahunan (%)"],
                    name="Vitamin A Tahunan 6-59 Bulan",
                    text=kelurahan_data["Jumlah Cakupan Anak 6-59 Bulan Mendapat Vitamin A Tahunan (%)"],
                    textposition='auto',
                    marker_color='#ff9900'
                ))
            fig.add_trace(go.Bar(
                x=[kelurahan_filter],
                y=kelurahan_data["Metrik Balita yang Mendapatkan Suplementasi Gizi Mikro (%)"],
                name="Suplementasi Gizi Mikro",
                text=kelurahan_data["Metrik Balita yang Mendapatkan Suplementasi Gizi Mikro (%)"],
                textposition='auto',
                marker_color='#00ff00'
            ))
            fig.update_layout(
                title=f"Cakupan Suplementasi Zat Gizi Mikro di {kelurahan_filter}, {puskesmas_filter}",
                xaxis_title="Kelurahan",
                yaxis_title="Persentase (%)",
                barmode='group',
                bargap=0.15
            )
        else:
            if bulan_filter_int is None or bulan_filter_int in [2, 8]:
                fig.add_trace(go.Bar(
                    x=current_df["Puskesmas"],
                    y=current_df["Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)"],
                    name="Bayi 6-11 Bulan",
                    text=current_df["Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)"],
                    textposition='auto',
                    marker_color='#1f77b4'
                ))
                fig.add_trace(go.Bar(
                    x=current_df["Puskesmas"],
                    y=current_df["Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)"],
                    name="Anak 12-59 Bulan",
                    text=current_df["Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)"],
                    textposition='auto',
                    marker_color='#ff0000'
                ))
            if bulan_filter_int == 8:
                fig.add_trace(go.Bar(
                    x=current_df["Puskesmas"],
                    y=current_df["Jumlah Cakupan Anak 6-59 Bulan Mendapat Vitamin A Tahunan (%)"],
                    name="Vitamin A Tahunan 6-59 Bulan",
                    text=current_df["Jumlah Cakupan Anak 6-59 Bulan Mendapat Vitamin A Tahunan (%)"],
                    textposition='auto',
                    marker_color='#ff9900'
                ))
            fig.add_trace(go.Bar(
                x=current_df["Puskesmas"],
                y=current_df["Metrik Balita yang Mendapatkan Suplementasi Gizi Mikro (%)"],
                name="Suplementasi Gizi Mikro",
                text=current_df["Metrik Balita yang Mendapatkan Suplementasi Gizi Mikro (%)"],
                textposition='auto',
                marker_color='#00ff00'
            ))
            fig.update_layout(
                title="Cakupan Suplementasi Zat Gizi Mikro per Puskesmas",
                xaxis_title="Puskesmas",
                yaxis_title="Persentase (%)",
                barmode='group',
                bargap=0.15,
                xaxis_tickangle=-45
            )
        st.plotly_chart(fig, use_container_width=True)

    # Grafik Perbandingan Vitamin A Februari vs Agustus (hanya jika ada data untuk kedua bulan)
    comparison_fig = None
    if not filtered_df.empty and "Bulan" in filtered_df.columns:
        # Periksa apakah ada data untuk Februari dan Agustus
        has_feb_data = len(filtered_df[filtered_df["Bulan"] == 2]) > 0
        has_aug_data = len(filtered_df[filtered_df["Bulan"] == 8]) > 0

        if has_feb_data and has_aug_data and (bulan_filter_int is None or bulan_filter_int == 8):
            # Gunakan filtered_df sebagai data awal, filter untuk bulan Februari
            feb_data = filtered_df[filtered_df["Bulan"] == 2]
            if puskesmas_filter != "All":
                feb_data = feb_data[feb_data["Puskesmas"] == puskesmas_filter]
            if kelurahan_filter != "All":
                feb_data = feb_data[feb_data["Kelurahan"] == kelurahan_filter]

            if not feb_data.empty:
                feb_summary = feb_data.groupby(group_columns).agg({
                    "Jumlah_bayi_6-11_bulan_mendapat_Vitamin_A": "sum",
                    "Jumlah_bayi_6-11_bulan": "sum",
                    "Jumlah_anak_12-59_bulan_mendapat_Vitamin_A": "sum",
                    "Jumlah_anak_12-59_bulan": "sum"
                }).reset_index()

                # Filter untuk Agustus dari filtered_df
                aug_data = filtered_df[filtered_df["Bulan"] == 8]
                if puskesmas_filter != "All":
                    aug_data = aug_data[aug_data["Puskesmas"] == puskesmas_filter]
                if kelurahan_filter != "All":
                    aug_data = aug_data[aug_data["Kelurahan"] == kelurahan_filter]
                aug_summary = aug_data.groupby(group_columns).agg({
                    "Jumlah_bayi_6-11_bulan_mendapat_Vitamin_A": "sum",
                    "Jumlah_bayi_6-11_bulan": "sum",
                    "Jumlah_anak_12-59_bulan_mendapat_Vitamin_A": "sum",
                    "Jumlah_anak_12-59_bulan": "sum"
                }).reset_index() if not aug_data.empty else pd.DataFrame()

                feb_summary["Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)"] = (feb_summary["Jumlah_bayi_6-11_bulan_mendapat_Vitamin_A"] / feb_summary["Jumlah_bayi_6-11_bulan"].replace(0, pd.NA) * 100).fillna(0).round(2)
                feb_summary["Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)"] = (feb_summary["Jumlah_anak_12-59_bulan_mendapat_Vitamin_A"] / feb_summary["Jumlah_anak_12-59_bulan"].replace(0, pd.NA) * 100).fillna(0).round(2)

                aug_summary["Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)"] = (aug_summary["Jumlah_bayi_6-11_bulan_mendapat_Vitamin_A"] / aug_summary["Jumlah_bayi_6-11_bulan"].replace(0, pd.NA) * 100).fillna(0).round(2) if not aug_summary.empty else 0
                aug_summary["Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)"] = (aug_summary["Jumlah_anak_12-59_bulan_mendapat_Vitamin_A"] / aug_summary["Jumlah_anak_12-59_bulan"].replace(0, pd.NA) * 100).fillna(0).round(2) if not aug_summary.empty else 0

                comparison_fig = go.Figure()
                comparison_fig.add_trace(go.Bar(
                    x=["Februari", "Agustus"],
                    y=[
                        feb_summary["Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)"].mean(),
                        aug_summary["Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)"].mean() if not aug_summary.empty else 0
                    ],
                    name="Bayi 6-11 Bulan",
                    marker_color='#1f77b4'
                ))
                comparison_fig.add_trace(go.Bar(
                    x=["Februari", "Agustus"],
                    y=[
                        feb_summary["Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)"].mean(),
                        aug_summary["Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)"].mean() if not aug_summary.empty else 0
                    ],
                    name="Anak 12-59 Bulan",
                    marker_color='#ff0000'
                ))
                comparison_fig.update_layout(
                    title="Perbandingan Cakupan Vitamin A: Februari vs Agustus",
                    xaxis_title="Bulan",
                    yaxis_title="Persentase (%)",
                    barmode='group'
                )
                st.plotly_chart(comparison_fig, use_container_width=True)
        elif not has_aug_data and (bulan_filter_int is None or bulan_filter_int == 8):
            st.warning("⚠️ Tidak ada data untuk Agustus, grafik perbandingan tidak ditampilkan.")

    # Tabel Rekapitulasi
    st.subheader("📋 Rekapitulasi Suplementasi Zat Gizi Mikro")
    if current_df.empty:
        st.warning("⚠️ Tidak ada data untuk rekapitulasi suplementasi zat gizi mikro.")
        summary_df = pd.DataFrame(columns=group_columns + metrics_list)
    else:
        summary_df = current_df[group_columns + metrics_list].copy()
        for col in summary_df.columns:
            if "(%)" in col:
                summary_df[col] = summary_df[col].round(2)

    st.dataframe(summary_df, use_container_width=True)

    return metrics, summary_df, fig, comparison_fig
# ----------------------------- #
# 🚀 Main Function
# ----------------------------- #
def show_dashboard():
    """Menampilkan dashboard utama untuk indikator balita gizi."""
    st.title("🍼 Dashboard Indikator Balita Gizi")
    last_upload_time = get_last_upload_time()
    st.markdown(f"**📅 Data terakhir diperbarui:** {last_upload_time}")

    df, desa_df = load_data()
    if df is None:
        st.error("❌ Gagal memuat data. Periksa database!")
        return

    # Debug: Tampilkan kolom untuk verifikasi
    debug_mode = st.checkbox("Aktifkan Mode Debug", value=False)
    if debug_mode:
        st.write("Kolom di df:", df.columns.tolist())

    with st.sidebar.expander("🔎 Filter Data"):
        # Ambil opsi bulan dari dataset, konversi ke string, dan tambahkan "All"
        bulan_options = ["All"] + sorted(df['Bulan'].astype(str).unique().tolist() if 'Bulan' in df.columns else [])
        bulan_filter = st.selectbox("📅 Pilih Bulan", options=bulan_options)

        puskesmas_filter = st.selectbox("🏥 Pilih Puskesmas", ["All"] + sorted(desa_df['Puskesmas'].unique()))
        kelurahan_options = ["All"]
        if puskesmas_filter != "All":
            kelurahan_options += sorted(desa_df[desa_df['Puskesmas'] == puskesmas_filter]['Kelurahan'].unique())
        kelurahan_filter = st.selectbox("🏡 Pilih Kelurahan", options=kelurahan_options)

    # Inisialisasi filtered_df dan previous_df
    filtered_df = df.copy()
    previous_df = pd.DataFrame()

    # Konversi bulan_filter ke integer hanya jika bukan "All"
    bulan_filter_int = None
    if bulan_filter != "All":
        try:
            bulan_filter_int = int(bulan_filter)
            filtered_df = df[df["Bulan"] == bulan_filter_int] if 'Bulan' in df.columns else df
            # Ambil data bulan sebelumnya (N-1) secara dinamis
            if 'Bulan' in df.columns and bulan_filter_int > 1:  # Hanya ambil previous jika bukan Januari
                previous_bulan = bulan_filter_int - 1
                previous_df = df[df["Bulan"] == previous_bulan].copy()
            else:
                previous_df = pd.DataFrame()  # Jika Januari atau tidak ada data sebelumnya, kosongkan
        except ValueError:
            st.error("⚠️ Pilihan bulan tidak valid. Menggunakan semua data.")
            filtered_df = df.copy()  # Kembali ke semua data jika konversi gagal

    # Terapkan filter Puskesmas dan Kelurahan
    if puskesmas_filter != "All":
        filtered_df = filtered_df[filtered_df["Puskesmas"] == puskesmas_filter]
        if not previous_df.empty and 'Puskesmas' in previous_df.columns:
            previous_df = previous_df[previous_df["Puskesmas"] == puskesmas_filter]

    if kelurahan_filter != "All":
        filtered_df = filtered_df[filtered_df["Kelurahan"] == kelurahan_filter]
        if not previous_df.empty and 'Kelurahan' in previous_df.columns:
            previous_df = previous_df[previous_df["Kelurahan"] == kelurahan_filter]

    # Tampilkan data terfilter
    st.subheader("📝 Data Terfilter")
    if filtered_df.empty:
        st.warning("⚠️ Tidak ada data yang sesuai dengan filter.")
    else:
        st.dataframe(filtered_df, use_container_width=True)

    # Menu sidebar
    menu = st.sidebar.radio("📂 Pilih Dashboard", ["📊 Kelengkapan Data Laporan", "📈 Analisis Indikator Balita"])

    if menu == "📊 Kelengkapan Data Laporan":
        sub_menu = st.sidebar.radio("🔍 Pilih Analisis", ["✅ Compliance Rate", "📋 Completeness Rate"])
        if sub_menu == "✅ Compliance Rate":
            compliance_rate(filtered_df, desa_df, puskesmas_filter, kelurahan_filter)
        elif sub_menu == "📋 Completeness Rate":
            completeness_rate(filtered_df, desa_df, puskesmas_filter, kelurahan_filter)

    elif menu == "📈 Analisis Indikator Balita":
        sub_analisis = st.sidebar.radio("📊 Pilih Sub Analisis", [
            "📈 Pertumbuhan & Perkembangan",
            "🥗 Masalah Gizi",
            "🍼 ASI Eksklusif & MPASI",
            "💊 Suplementasi Zat Gizi Mikro",
            "🧑‍⚕️ Tatalaksana Balita Bermasalah Gizi"
        ])
        if sub_analisis == "📈 Pertumbuhan & Perkembangan":
            metrics, summary_df, fig_bar, fig_line = growth_development_metrics(filtered_df, previous_df, desa_df, puskesmas_filter, kelurahan_filter, bulan_filter_int)

            # Tombol Download untuk Pertumbuhan & Perkembangan (tanpa perubahan)
            def generate_pdf_growth(metrics, summary_df, fig_bar, fig_line, filter_info):
                pdf_buffer = io.BytesIO()
                doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(letter))
                styles = getSampleStyleSheet()
                elements = []

                # Judul Laporan
                elements.append(Paragraph("Laporan Pertumbuhan & Perkembangan Balita", styles['Title']))
                elements.append(Spacer(1, 12))

                # Informasi Filter
                elements.append(Paragraph(f"Filter: Bulan = {filter_info['bulan']}, Puskesmas = {filter_info['puskesmas']}, Kelurahan = {filter_info['kelurahan']}", styles['Normal']))
                elements.append(Spacer(1, 12))

                # Tabel Metrik
                metrics_table = [["Metrik", "Persentase (%)", "Perubahan"]]
                for label, (value, change) in metrics.items():
                    metrics_table.append([label, f"{value:.2f}%", change])
                table = Table(metrics_table)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('SPLITBYROW', (0, 0), (-1, -1), 1)
                ]))
                elements.append(table)
                elements.append(Spacer(1, 12))

                # Grafik Bar sebagai Gambar
                bar_img = io.BytesIO(to_image(fig_bar, format='png', width=600, height=400))
                elements.append(Image(bar_img, width=500, height=300))
                elements.append(Spacer(1, 12))

                # Tabel Rekapitulasi
                if summary_df.empty or len(summary_df.columns) == 0 or len(summary_df.values.tolist()) == 0:
                    st.error("⚠️ Tidak ada data yang cukup untuk menghasilkan laporan PDF. Silakan pilih Puskesmas atau Kelurahan dengan data pelaporan.")
                    return io.BytesIO()
                else:                               
                    summary_table = [summary_df.columns.tolist()] + summary_df.values.tolist()
                    table = Table(summary_table)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 14),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 12),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('SPLITBYROW', (0, 0), (-1, -1), 1)
                    ]))
                    elements.append(Paragraph("⚠️ Rekapitulasi Prevalensi Masalah Gizi ", styles['Heading2']))
                    elements.append(table)
                    elements.append(Spacer(1, 12))

                # Grafik Line sebagai Gambar
                line_img = io.BytesIO(to_image(fig_line, format='png', width=600, height=400))
                elements.append(Image(line_img, width=500, height=300))
                elements.append(Spacer(1, 12))

                # Build PDF
                doc.build(elements)
                pdf_buffer.seek(0)
                return pdf_buffer

            filter_info = {
                'bulan': bulan_filter,  # Tetap string untuk label PDF
                'puskesmas': puskesmas_filter,
                'kelurahan': kelurahan_filter
            }
            pdf_file = generate_pdf_growth(metrics, summary_df, fig_bar, fig_line, filter_info)
            st.download_button(
                label="📥 Download Laporan PDF",
                data=pdf_file,
                file_name=f"laporan_pertumbuhan_{puskesmas_filter}_{kelurahan_filter}_{time.strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf"
            )

        elif sub_analisis == "🥗 Masalah Gizi":
            metrics, summary_df, fig, prevalence_charts = nutrition_issues_analysis(filtered_df, previous_df, desa_df, puskesmas_filter, kelurahan_filter, bulan_filter_int)

            # Tombol Download untuk Masalah Gizi (tanpa perubahan)
            def generate_pdf_nutrition(metrics, summary_df, fig, prevalence_charts, filter_info):
                pdf_buffer = io.BytesIO()
                doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(letter))
                styles = getSampleStyleSheet()
                elements = []

                # Judul Laporan
                elements.append(Paragraph("Laporan Masalah Gizi Balita", styles['Title']))
                elements.append(Spacer(1, 12))

                # Informasi Filter
                elements.append(Paragraph(f"Filter: Bulan = {filter_info['bulan']}, Puskesmas = {filter_info['puskesmas']}, Kelurahan = {filter_info['kelurahan']}", styles['Normal']))
                elements.append(Spacer(1, 12))

                # Tabel Metrik
                metrics_table = [["Metrik", "Persentase Rata-rata (%)", "Status"]]
                for label, (value, status) in metrics.items():
                    metrics_table.append([label, f"{value:.2f}%", status])
                table = Table(metrics_table)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('SPLITBYROW', (0, 0), (-1, -1), 1)
                ]))
                elements.append(table)
                elements.append(Spacer(1, 12))

                # Grafik Pertama (Grouped Bar Chart) sebagai Gambar
                if fig is None:
                    elements.append(Paragraph("⚠️ Grafik Prevalensi Masalah Gizi tidak tersedia karena data kosong.", styles['Normal']))
                    elements.append(Spacer(1, 12))
                else:
                    chart_img = io.BytesIO(to_image(fig, format='png', width=600, height=400))
                    elements.append(Image(chart_img, width=500, height=300))
                    elements.append(Spacer(1, 12))
                          
             
                # Tabel Rekapitulasi
                if summary_df.empty or len(summary_df.columns) == 0 or len(summary_df.values.tolist()) == 0:
                    st.error("⚠️ Tidak ada data yang cukup untuk menghasilkan laporan PDF. Silakan pilih Puskesmas atau Kelurahan dengan data pelaporan.")
                    elements.append(Paragraph("⚠️ Rekapitulasi Prevalensi Masalah Gizi tidak tersedia karena data kosong.", styles['Normal']))
                    elements.append(Spacer(1, 12))
                    doc.build(elements)
                    pdf_buffer.seek(0)
                    return pdf_buffer
                else:
                    summary_table = [summary_df.columns.tolist()] + summary_df.values.tolist()
                    if len(summary_table) > 1 and all(len(row) == len(summary_table[0]) for row in summary_table):
                        table = Table(summary_table)
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 14),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                            ('FONTSIZE', (0, 1), (-1, -1), 12),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                            ('SPLITBYROW', (0, 0), (-1, -1), 1)
                        ]))
                        elements.append(Paragraph("Rekapitulasi Prevalensi Masalah Gizi", styles['Heading2']))
                        elements.append(table)
                    else:
                        elements.append(Paragraph("⚠️ Rekapitulasi Prevalensi Masalah Gizi tidak tersedia karena struktur data tidak valid.", styles['Normal']))
                    elements.append(Spacer(1, 12))

                # Grafik Prevalensi Status Gizi per Metrik
                elements.append(Paragraph("Grafik Prevalensi Status Gizi per Metrik", styles['Heading2']))
                if not prevalence_charts:
                    elements.append(Paragraph("⚠️ Grafik Prevalensi Status Gizi per Metrik tidak tersedia karena data kosong.", styles['Normal']))
                    elements.append(Spacer(1, 12))
                else:                    
                    for chart in prevalence_charts:
                        chart_img = io.BytesIO(to_image(chart, format='png', width=600, height=400))
                        elements.append(Image(chart_img, width=500, height=300))
                        elements.append(Spacer(1, 12))

                # Build PDF
                doc.build(elements)
                pdf_buffer.seek(0)
                return pdf_buffer

            filter_info = {
                'bulan': bulan_filter,  # Tetap string untuk label PDF
                'puskesmas': puskesmas_filter,
                'kelurahan': kelurahan_filter
            }
            pdf_file = generate_pdf_nutrition(metrics, summary_df, fig, prevalence_charts, filter_info)
            st.download_button(
                label="📥 Download Laporan PDF",
                data=pdf_file,
                file_name=f"laporan_masalah_gizi_{puskesmas_filter}_{kelurahan_filter}_{time.strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf"
            )

        elif sub_analisis == "🍼 ASI Eksklusif & MPASI":
            metrics, summary_df, charts = asi_exclusive_mpasi_analysis(filtered_df, previous_df, desa_df, puskesmas_filter, kelurahan_filter, bulan_filter_int)

            # Tombol Download untuk ASI Eksklusif & MPASI (tanpa perubahan)
            def generate_pdf_asi(metrics, summary_df, charts, filter_info):
                pdf_buffer = io.BytesIO()
                doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(letter))
                styles = getSampleStyleSheet()
                elements = []

                # Judul Laporan
                elements.append(Paragraph("Laporan ASI Eksklusif & MPASI", styles['Title']))
                elements.append(Spacer(1, 12))

                # Informasi Filter
                elements.append(Paragraph(f"Filter: Bulan = {filter_info['bulan']}, Puskesmas = {filter_info['puskesmas']}, Kelurahan = {filter_info['kelurahan']}", styles['Normal']))
                elements.append(Spacer(1, 12))

                # Tabel Metrik
                metrics_table = [["Metrik", "Persentase (%)", "Perubahan"]]
                for label, (value, change) in metrics.items():
                    metrics_table.append([label, f"{value:.2f}%", change])
                table = Table(metrics_table)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('SPLITBYROW', (0, 0), (-1, -1), 1)
                ]))
                elements.append(table)
                elements.append(Spacer(1, 12))

                # Grafik Capaian sebagai Gambar
                for chart in charts:
                    chart_img = io.BytesIO(to_image(chart, format='png', width=600, height=400))
                    elements.append(Image(chart_img, width=500, height=300))
                    elements.append(Spacer(1, 12))

                # Tabel Rekapitulasi
                if summary_df.empty or len(summary_df.columns) == 0:
                    st.error("⚠️ Tidak ada data yang cukup untuk menghasilkan laporan PDF. Silakan pilih Puskesmas atau Kelurahan dengan data pelaporan.")
                    return io.BytesIO()  # Kembalikan buffer kosong untuk mencegah error
                else:
                    summary_table = [summary_df.columns.tolist()] + summary_df.values.tolist()
                    table = Table(summary_table)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('SPLITBYROW', (0, 0), (-1, -1), 1)
                ]))
                elements.append(Paragraph("Rekapitulasi Capaian ASI Eksklusif & MPASI", styles['Heading2']))
                elements.append(table)
                elements.append(Spacer(1, 12))

                # Build PDF
                doc.build(elements)
                pdf_buffer.seek(0)
                return pdf_buffer

            filter_info = {
                'bulan': bulan_filter,  # Tetap string untuk label PDF
                'puskesmas': puskesmas_filter,
                'kelurahan': kelurahan_filter
            }
            pdf_file = generate_pdf_asi(metrics, summary_df, charts, filter_info)
            st.download_button(
                label="📥 Download Laporan PDF",
                data=pdf_file,
                file_name=f"laporan_asi_mpasi_{puskesmas_filter}_{kelurahan_filter}_{time.strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf"
            )
        elif sub_analisis == "💊 Suplementasi Zat Gizi Mikro":
            metrics, summary_df, fig, comparison_fig = micronutrient_supplementation_analysis(filtered_df, previous_df, desa_df, puskesmas_filter, kelurahan_filter, bulan_filter_int)
            def generate_pdf_micronutrient(metrics, summary_df, fig, comparison_fig, filter_info):
                pdf_buffer = io.BytesIO()
                doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(letter))
                styles = getSampleStyleSheet()
                elements = []

                # Judul Laporan
                elements.append(Paragraph("Laporan Suplementasi Zat Gizi Mikro Balita", styles['Title']))
                elements.append(Spacer(1, 12))

                # Informasi Filter
                elements.append(Paragraph(f"Filter: Bulan = {filter_info['bulan']}, Puskesmas = {filter_info['puskesmas']}, Kelurahan = {filter_info['kelurahan']}", styles['Normal']))
                elements.append(Spacer(1, 12))

                # Tabel Metrik
                metrics_table = [["Metrik", "Persentase Rata-rata (%)", "Status"]]
                for label, (value, status) in metrics.items():
                    metrics_table.append([label, f"{value:.2f}%", status])
                table = Table(metrics_table)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('SPLITBYROW', (0, 0), (-1, -1), 1)
                ]))
                elements.append(table)
                elements.append(Spacer(1, 12))

                # Grafik Utama (Cakupan Suplementasi Zat Gizi Mikro)
                if fig is None:
                    elements.append(Paragraph("⚠️ Grafik Cakupan Suplementasi Zat Gizi Mikro tidak tersedia karena data kosong.", styles['Normal']))
                    elements.append(Spacer(1, 12))
                else:
                    chart_img = io.BytesIO(to_image(fig, format='png', width=600, height=400))
                    elements.append(Image(chart_img, width=500, height=300))
                    elements.append(Spacer(1, 12))

                # Grafik Perbandingan Februari vs Agustus (hanya untuk bulan >= 8)
                if filter_info['bulan'] != "All" and int(filter_info['bulan']) >= 8:
                    if comparison_fig is None:
                        elements.append(Paragraph("⚠️ Grafik Perbandingan Cakupan Vitamin A Februari vs Agustus tidak tersedia karena data kosong.", styles['Normal']))
                        elements.append(Spacer(1, 12))
                    else:
                        chart_img = io.BytesIO(to_image(comparison_fig, format='png', width=600, height=400))
                        elements.append(Image(chart_img, width=500, height=300))
                        elements.append(Spacer(1, 12))

                # Tabel Rekapitulasi
                if summary_df.empty or len(summary_df.columns) == 0 or len(summary_df.values.tolist()) == 0:
                    st.error("⚠️ Tidak ada data yang cukup untuk menghasilkan laporan PDF. Silakan pilih Puskesmas atau Kelurahan dengan data pelaporan.")
                    elements.append(Paragraph("⚠️ Rekapitulasi Suplementasi Zat Gizi Mikro tidak tersedia karena data kosong.", styles['Normal']))
                    elements.append(Spacer(1, 12))
                    doc.build(elements)
                    pdf_buffer.seek(0)
                    return pdf_buffer
                else:
                    summary_table = [summary_df.columns.tolist()] + summary_df.values.tolist()
                    if len(summary_table) > 1 and all(len(row) == len(summary_table[0]) for row in summary_table):
                        table = Table(summary_table)
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 14),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                            ('FONTSIZE', (0, 1), (-1, -1), 12),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                            ('SPLITBYROW', (0, 0), (-1, -1), 1)
                        ]))
                        elements.append(Paragraph("Rekapitulasi Suplementasi Zat Gizi Mikro", styles['Heading2']))
                        elements.append(table)
                    else:
                        elements.append(Paragraph("⚠️ Rekapitulasi Suplementasi Zat Gizi Mikro tidak tersedia karena struktur data tidak valid.", styles['Normal']))
                    elements.append(Spacer(1, 12))

                # Build PDF
                doc.build(elements)
                pdf_buffer.seek(0)
                return pdf_buffer
            
            # Tombol Download untuk Suplementasi Zat Gizi Mikro
            filter_info = {
                'bulan': bulan_filter,  # Tetap string untuk label PDF
                'puskesmas': puskesmas_filter,
                'kelurahan': kelurahan_filter
            }
            pdf_file = generate_pdf_micronutrient(metrics, summary_df, fig, comparison_fig, filter_info)
            st.download_button(
                label="📥 Download Laporan PDF",
                data=pdf_file,
                file_name=f"laporan_suplementasi_zat_gizi_mikro_{puskesmas_filter}_{kelurahan_filter}_{time.strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf"
            )
        elif sub_analisis == "🧑‍⚕️ Tatalaksana Balita Bermasalah Gizi":
            metrics, summary_df, charts = tatalaksana_balita_bermasalah_gizi_analysis(df, desa_df, bulan_filter_int, puskesmas_filter, kelurahan_filter)
            
            # Fungsi untuk menghasilkan PDF
            def generate_pdf_tatalaksana(metrics, summary_df, charts, filter_info):
                pdf_buffer = io.BytesIO()
                doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(letter))
                styles = getSampleStyleSheet()
                elements = []

                # Judul Laporan
                elements.append(Paragraph("Laporan Tatalaksana Balita Bermasalah Gizi", styles['Title']))
                elements.append(Spacer(1, 12))

                # Informasi Filter
                elements.append(Paragraph(
                    f"Filter: Bulan = {filter_info['bulan']}, Puskesmas = {filter_info['puskesmas']}, Kelurahan = {filter_info['kelurahan']}",
                    styles['Normal']
                ))
                elements.append(Spacer(1, 12))

                # Tabel Metrik
                metrics_table = [["Metrik", "Persentase Rata-rata (%)", "Status"]]
                for label, (value, status) in metrics.items():
                    metrics_table.append([label, f"{value:.2f}%", status])
                table = Table(metrics_table)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('SPLITBYROW', (0, 0), (-1, -1), 1)
                ]))
                elements.append(table)
                elements.append(Spacer(1, 12))

                # Grafik Terpisah sebagai Gambar
                if not charts:
                    elements.append(Paragraph("⚠️ Grafik Tatalaksana Balita Bermasalah Gizi tidak tersedia karena data kosong.", styles['Normal']))
                    elements.append(Spacer(1, 12))
                else:
                    for idx, chart in enumerate(charts):
                        chart_img = io.BytesIO(to_image(chart, format='png', width=600, height=400))
                        elements.append(Paragraph(f"Grafik {idx + 1}: {chart.layout.title.text}", styles['Heading2']))
                        elements.append(Image(chart_img, width=500, height=300))
                        elements.append(Spacer(1, 12))

                # Tabel Rekapitulasi
                if summary_df.empty or len(summary_df.columns) == 0 or len(summary_df.values.tolist()) == 0:
                    elements.append(Paragraph("⚠️ Rekapitulasi Tatalaksana Balita Bermasalah Gizi tidak tersedia karena data kosong.", styles['Normal']))
                    elements.append(Spacer(1, 12))
                else:
                    # Format persentase di tabel
                    styled_df = summary_df.copy()
                    for col in styled_df.columns:
                        if "(%)" in col:
                            styled_df[col] = styled_df[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
                    summary_table = [styled_df.columns.tolist()] + styled_df.values.tolist()
                    
                    if len(summary_table) > 1 and all(len(row) == len(summary_table[0]) for row in summary_table):
                        table = Table(summary_table)
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 14),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                            ('FONTSIZE', (0, 1), (-1, -1), 12),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                            ('SPLITBYROW', (0, 0), (-1, -1), 1)
                        ]))
                        elements.append(Paragraph("Rekapitulasi Tatalaksana Balita Bermasalah Gizi", styles['Heading2']))
                        elements.append(table)
                    else:
                        elements.append(Paragraph("⚠️ Rekapitulasi Tatalaksana Balita Bermasalah Gizi tidak tersedia karena struktur data tidak valid.", styles['Normal']))
                    elements.append(Spacer(1, 12))

                # Build PDF
                doc.build(elements)
                pdf_buffer.seek(0)
                return pdf_buffer

            # Informasi filter untuk PDF
            filter_info = {
                'bulan': bulan_filter,
                'puskesmas': puskesmas_filter,
                'kelurahan': kelurahan_filter
            }

            # Generate PDF dan tambahkan tombol download
            pdf_file = generate_pdf_tatalaksana(metrics, summary_df, charts, filter_info)
            st.download_button(
                label="📥 Download Laporan PDF",
                data=pdf_file,
                file_name=f"laporan_tatalaksana_{puskesmas_filter}_{kelurahan_filter}_{time.strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf"
            )
    st.markdown(
        '<p style="text-align: center; font-size: 12px; color: grey;">'
        'made with ❤️ by <a href="mailto:dedik2urniawan@gmail.com">dedik2urniawan@gmail.com</a>'
        '</p>', unsafe_allow_html=True)

if __name__ == "__main__":
    show_dashboard()