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
    # Periksa apakah kolom 'Kelurahan' ada
    if 'Kelurahan' not in filtered_df.columns:
        st.error("⚠️ Kolom 'Kelurahan' tidak ditemukan dalam data yang difilter. Pastikan data lengkap.")
        return
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
def calculate_growth_metric(current, previous):
    """Menghitung perbedaan antara nilai saat ini dan sebelumnya dengan indikator panah."""
    if previous == 0 or pd.isna(previous) or pd.isna(current):
        return current, ""
    delta = current - previous
    icon = "🔼" if delta > 0 else "🔽"
    return current, f"{icon} {abs(delta):.2f}%"

def growth_development_metrics(df, filtered_df, previous_df, desa_df, puskesmas_filter, kelurahan_filter, bulan_filter, tahun_filter):
    """Menghitung metrik pertumbuhan & perkembangan balita dan mengembalikan data untuk PDF."""
    total_bulan_ini = filtered_df["Jumlah_balita_bulan_ini"].sum()
    total_sasaran = filtered_df["Jumlah_sasaran_balita"].sum()
    total_ditimbang_terkoreksi = filtered_df["Jumlah_balita_ditimbang_terkoreksi_Daksen"].sum()
    total_timbang_balita = filtered_df["Jumlah_balita_ditimbang"].sum()
    total_timbang_ukur_balita = filtered_df["Jumlah_balita_ditimbang_dan_diukur"].sum()
    total_Jumlah_balita_diukur_PBTB = filtered_df["Jumlah_balita_diukur_PBTB"].sum()

    prev_total_bulan_ini = previous_df["Jumlah_balita_bulan_ini"].sum() if not previous_df.empty else 0
    prev_total_sasaran = previous_df["Jumlah_sasaran_balita"].sum() if not previous_df.empty else 0
    prev_total_ditimbang_terkoreksi = previous_df["Jumlah_balita_ditimbang_terkoreksi_Daksen"].sum() if not previous_df.empty else 0

    try:
        metrics = {
            "Balita ditimbang (Proyeksi)": calculate_growth_metric(
                filtered_df["Jumlah_balita_ditimbang"].sum() / total_sasaran * 100 if total_sasaran else 0,
                previous_df["Jumlah_balita_ditimbang"].sum() / prev_total_sasaran * 100 if prev_total_sasaran else 0
            ),
            "Balita ditimbang (Data Rill)": calculate_growth_metric(
                filtered_df["Jumlah_balita_ditimbang"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0,
                previous_df["Jumlah_balita_ditimbang"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
            "Balita ditimbang & diukur": calculate_growth_metric(
                filtered_df["Jumlah_balita_ditimbang_dan_diukur"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0,
                previous_df["Jumlah_balita_ditimbang_dan_diukur"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
            "Balita diukur PB/TB": calculate_growth_metric(
                filtered_df["Jumlah_balita_diukur_PBTB"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0,
                previous_df["Jumlah_balita_diukur_PBTB"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
            "Balita memiliki Buku KIA": calculate_growth_metric(
                filtered_df["Jumlah_balita_punya_KIA"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0,
                previous_df["Jumlah_balita_punya_KIA"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
            "Balita Naik BB": calculate_growth_metric(
                filtered_df["Jumlah_balita_naik_berat_badannya_N"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0,
                previous_df["Jumlah_balita_naik_berat_badannya_N"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
            "Balita Naik dengan D Koreksi": calculate_growth_metric(
                filtered_df["Jumlah_balita_naik_berat_badannya_N"].sum() / total_ditimbang_terkoreksi * 100 if total_ditimbang_terkoreksi else 0,
                previous_df["Jumlah_balita_naik_berat_badannya_N"].sum() / prev_total_ditimbang_terkoreksi * 100 if prev_total_ditimbang_terkoreksi else 0
            ),
            "Balita Tidak Naik BB": calculate_growth_metric(
                filtered_df["Jumlah_balita_tidak_naik_berat_badannya_T"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0,
                previous_df["Jumlah_balita_tidak_naik_berat_badannya_T"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
            "Balita Tidak Timbang Bulan Lalu": calculate_growth_metric(
                filtered_df["Jumlah_balita_tidak_ditimbang_bulan_lalu_O"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0,
                previous_df["Jumlah_balita_tidak_ditimbang_bulan_lalu_O"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
            "Prevalensi Stunting": calculate_growth_metric(
                filtered_df["Jumlah_balita_stunting"].sum() / total_Jumlah_balita_diukur_PBTB * 100 if total_Jumlah_balita_diukur_PBTB else 0,
                previous_df["Jumlah_balita_stunting"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
            "Prevalensi Wasting": calculate_growth_metric(
                filtered_df["Jumlah_balita_wasting"].sum() / total_timbang_ukur_balita * 100 if total_timbang_ukur_balita else 0,
                previous_df["Jumlah_balita_wasting"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
            "Prevalensi Underweight": calculate_growth_metric(
                filtered_df["Jumlah_balita_underweight"].sum() / total_timbang_balita * 100 if total_timbang_balita else 0,
                previous_df["Jumlah_balita_underweight"].sum() / prev_total_bulan_ini * 100 if prev_total_bulan_ini else 0
            ),
            "Prevalensi Overweight": calculate_growth_metric(
                filtered_df["Jumlah_balita_overweight"].sum() / total_timbang_balita * 100 if total_timbang_balita else 0,
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
    # Bar chart
    metrics_df = pd.DataFrame({"Metrik": list(metrics.keys()), "Persentase": [val[0] for val in metrics.values()]})
    # Bulatkan Persentase ke 2 desimal
    metrics_df["Persentase"] = metrics_df["Persentase"].round(2)
    # Buat kolom untuk label teks dengan format persen
    metrics_df["Persentase_Text"] = metrics_df["Persentase"].apply(lambda x: f"{x:.2f}%")
    fig_bar = px.bar(metrics_df, x="Metrik", y="Persentase", text="Persentase_Text", title="📊 Metrik Pertumbuhan & Perkembangan Balita", color="Metrik")
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

    # Tren Visualisasi (Tren Indikator Pertumbuhan dan Perkembangan per Bulan)
    st.subheader("📊 Tren Indikator Pertumbuhan dan Perkembangan")

    # Gunakan data asli (df) untuk menghitung metrik per bulan
    essential_trend_data = []
    nutrition_trend_data = []

    if 'Bulan' in df.columns:
        # Filter data berdasarkan tahun, puskesmas, dan kelurahan
        df_trend = df.copy()
        if tahun_filter != "All":
            df_trend = df_trend[df_trend["Tahun"] == int(tahun_filter)]
        if puskesmas_filter != "All":
            df_trend = df_trend[df_trend["Puskesmas"] == puskesmas_filter]
        if kelurahan_filter != "All":
            df_trend = df_trend[df_trend["Kelurahan"] == kelurahan_filter]

        # Hitung metrik untuk setiap bulan
        for bulan in range(1, 13):
            df_bulan = df_trend[df_trend["Bulan"] == bulan]
            if df_bulan.empty:
                continue

            # Hitung total untuk denominator
            total_bulan_ini = df_bulan["Jumlah_balita_bulan_ini"].sum()
            total_sasaran = df_bulan["Jumlah_sasaran_balita"].sum()
            total_ditimbang_terkoreksi = df_bulan["Jumlah_balita_ditimbang_terkoreksi_Daksen"].sum()
            total_timbang_balita = df_bulan["Jumlah_balita_ditimbang"].sum()
            total_timbang_ukur_balita = df_bulan["Jumlah_balita_ditimbang_dan_diukur"].sum()
            total_Jumlah_balita_diukur_PBTB = df_bulan["Jumlah_balita_diukur_PBTB"].sum()

            # Hitung metrik untuk bulan ini (tanpa perbandingan dengan data sebelumnya)
            metrics_bulan = {
                "Balita ditimbang (Proyeksi)": round(df_bulan["Jumlah_balita_ditimbang"].sum() / total_sasaran * 100 if total_sasaran else 0, 2),
                "Balita ditimbang (Data Rill)": round(df_bulan["Jumlah_balita_ditimbang"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0, 2),
                "Balita ditimbang & diukur": round(df_bulan["Jumlah_balita_ditimbang_dan_diukur"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0, 2),
                "Balita diukur PB/TB": round(df_bulan["Jumlah_balita_diukur_PBTB"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0, 2),
                "Balita memiliki Buku KIA": round(df_bulan["Jumlah_balita_punya_KIA"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0, 2),
                "Balita Naik BB": round(df_bulan["Jumlah_balita_naik_berat_badannya_N"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0, 2),
                "Balita Naik dengan D Koreksi": round(df_bulan["Jumlah_balita_naik_berat_badannya_N"].sum() / total_ditimbang_terkoreksi * 100 if total_ditimbang_terkoreksi else 0, 2),
                "Balita Tidak Naik BB": round(df_bulan["Jumlah_balita_tidak_naik_berat_badannya_T"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0, 2),
                "Balita Tidak Timbang Bulan Lalu": round(df_bulan["Jumlah_balita_tidak_ditimbang_bulan_lalu_O"].sum() / total_bulan_ini * 100 if total_bulan_ini else 0, 2),
                "Prevalensi Stunting": round(df_bulan["Jumlah_balita_stunting"].sum() / total_Jumlah_balita_diukur_PBTB * 100 if total_Jumlah_balita_diukur_PBTB else 0, 2),
                "Prevalensi Wasting": round(df_bulan["Jumlah_balita_wasting"].sum() / total_timbang_ukur_balita * 100 if total_timbang_ukur_balita else 0, 2),
                "Prevalensi Underweight": round(df_bulan["Jumlah_balita_underweight"].sum() / total_timbang_balita * 100 if total_timbang_balita else 0, 2),
                "Prevalensi Overweight": round(df_bulan["Jumlah_balita_overweight"].sum() / total_timbang_balita * 100 if total_timbang_balita else 0, 2),
            }

            # Pisahkan data ke dalam dua kelompok: esensial dan status gizi
            essential_metrics = [
                "Balita ditimbang (Proyeksi)",
                "Balita ditimbang (Data Rill)",
                "Balita ditimbang & diukur",
                "Balita diukur PB/TB",
                "Balita memiliki Buku KIA",
                "Balita Naik BB",
                "Balita Naik dengan D Koreksi",
                "Balita Tidak Naik BB",
                "Balita Tidak Timbang Bulan Lalu"
            ]
            nutrition_metrics = [
                "Prevalensi Stunting",
                "Prevalensi Wasting",
                "Prevalensi Underweight",
                "Prevalensi Overweight"
            ]

            # Tambahkan data ke masing-masing kelompok
            for metric_name, value in metrics_bulan.items():
                if metric_name in essential_metrics:
                    essential_trend_data.append({
                        "Bulan": bulan,
                        "Metrik": metric_name,
                        "Persentase": value
                    })
                elif metric_name in nutrition_metrics:
                    nutrition_trend_data.append({
                        "Bulan": bulan,
                        "Metrik": metric_name,
                        "Persentase": value
                    })

    # Buat DataFrame untuk masing-masing line chart
    essential_trend_df = pd.DataFrame(essential_trend_data)
    nutrition_trend_df = pd.DataFrame(nutrition_trend_data)

    # Tampilkan line chart untuk Metrik Esensial
    st.subheader("📊 Tren Metrik Esensial Pertumbuhan dan Perkembangan")
    if not essential_trend_df.empty:
        fig_essential = px.line(
            essential_trend_df, 
            x="Bulan", 
            y="Persentase", 
            color="Metrik", 
            markers=True, 
            text="Persentase",
            title="📊 Tren Metrik Esensial Pertumbuhan dan Perkembangan"
        )
        fig_essential.update_traces(textposition="top center")
        fig_essential.update_layout(
            xaxis_title="Bulan",
            yaxis_title="Persentase (%)",
            xaxis=dict(tickmode='linear', tick0=1, dtick=1),
            yaxis_range=[0, 100]
        )
        st.plotly_chart(fig_essential, key=f"essential_trend_chart_{puskesmas_filter}_{kelurahan_filter}_{time.time()}", use_container_width=True)
    else:
        st.warning("⚠️ Tidak ada data untuk ditampilkan pada grafik tren metrik esensial.")

    # Tampilkan line chart untuk Metrik Status Gizi
    st.subheader("📊 Tren Metrik Status Gizi")
    if not nutrition_trend_df.empty:
        fig_nutrition = px.line(
            nutrition_trend_df, 
            x="Bulan", 
            y="Persentase", 
            color="Metrik", 
            markers=True, 
            text="Persentase",
            title="📊 Tren Metrik Status Gizi"
        )
        fig_nutrition.update_traces(textposition="top center")
        fig_nutrition.update_layout(
            xaxis_title="Bulan",
            yaxis_title="Persentase (%)",
            xaxis=dict(tickmode='linear', tick0=1, dtick=1),
            yaxis_range=[0, 100]
        )
        st.plotly_chart(fig_nutrition, key=f"nutrition_trend_chart_{puskesmas_filter}_{kelurahan_filter}_{time.time()}", use_container_width=True)
    else:
        st.warning("⚠️ Tidak ada data untuk ditampilkan pada grafik tren status gizi.")
    # Mengembalikan data untuk PDF
    return metrics, summary_df, fig_bar, fig_line

# ----------------------------- #
# 🍼 Analisis ASI Eksklusif & MPASI
# ----------------------------- #
def calculate_asi_metric(current, previous):
    if current is None or pd.isna(current):
        return 0, ""
    delta = ""
    if previous is not None and not pd.isna(previous):
        delta_value = current - previous
        delta = f"{delta_value:+.2f}%"
    return round(current, 2), delta

def create_pdf_from_dataframe(df, filename="rekapitulasi_asi_mpasi.pdf"):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # Convert DataFrame to list of lists for Table
    data = [df.columns.tolist()] + df.values.tolist()
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

def asi_exclusive_mpasi_analysis(filtered_df, previous_df, desa_df, puskesmas_filter, kelurahan_filter, bulan_filter, jenis_laporan="Laporan Bulanan"):
    st.header("🍼 Analisis ASI Eksklusif & MPASI")
    
    # Informasi Metrik ASI dan MPASI
    with st.expander("📜 Definisi dan Insight Analisis ASI Eksklusif dan MPASI", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Analisis Indikator

            Berikut adalah definisi operasional, rumus perhitungan, serta analisis insight dari indikator-indikator yang digunakan untuk memantau pemberian ASI eksklusif dan MPASI pada bayi dan anak dalam sistem kesehatan masyarakat. Rumus disajikan dalam format matematis untuk kejelasan, dengan penjelasan sederhana untuk memudahkan pemahaman.

            #### 1. Persentase Bayi Mendapat Inisiasi Menyusu Dini (IMD)
            - **Definisi Operasional:** Persentase bayi baru lahir yang diletakkan di dada ibu untuk menyusu dalam 1 jam pertama setelah kelahiran, di wilayah kerja puskesmas pada periode pelaporan tertentu. IMD bertujuan untuk merangsang produksi ASI dan memperkuat ikatan ibu-bayi.  
            - **Rumus Perhitungan:**  
            $$ \\text{IMD (\\%)} = \\frac{\\text{Jumlah bayi baru lahir yang mendapat IMD}}{\\text{Jumlah total bayi baru lahir}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen bayi yang menyusu dini dalam 1 jam setelah lahir dari total bayi baru lahir, lalu dikalikan 100 untuk mendapatkan persentase.  
            - **Metode Pengumpulan Data:** Data dikumpulkan bulanan melalui laporan dari bidan atau rumah sakit bersalin. Petugas mencatat apakah bayi diletakkan untuk IMD berdasarkan observasi langsung atau laporan ibu.  
            - **Insight Analisis:** Persentase IMD di bawah 80% dapat mengindikasikan kurangnya pelatihan tenaga kesehatan atau hambatan budaya, seperti pemisahan ibu-bayi setelah kelahiran. Peningkatan pelatihan bidan tentang manfaat IMD dan edukasi ibu selama kehamilan dapat meningkatkan cakupan, mengurangi risiko kematian neonatal dan mendukung keberhasilan menyusui.

            #### 2. Persentase Bayi ASI Eksklusif Sampai 6 Bulan
            - **Definisi Operasional:** Persentase bayi usia 6 bulan yang hanya menerima ASI tanpa makanan atau minuman lain (kecuali obat-obatan) selama 6 bulan pertama kehidupan, di wilayah kerja puskesmas pada periode pelaporan.  
            - **Rumus Perhitungan:**  
            $$ \\text{ASI Eksklusif 6 Bulan (\\%)} = \\frac{\\text{Jumlah bayi usia 6 bulan dengan ASI eksklusif}}{\\text{Jumlah total bayi usia 6 bulan}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen bayi berusia 6 bulan yang hanya minum ASI dari total bayi pada usia tersebut, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data diambil melalui wawancara ibu di posyandu atau kunjungan rumah oleh kader kesehatan, dengan pencatatan bulanan berdasarkan riwayat pemberian makan bayi sejak lahir.  
            - **Insight Analisis:** Jika persentase di bawah 50% (target WHO), ini mungkin menunjukkan mitos tentang ASI tidak cukup atau tekanan untuk memberikan makanan dini. Edukasi intensif tentang manfaat ASI eksklusif dan dukungan konseling laktasi di posyandu dapat meningkatkan angka ini, mendukung imunitas dan pertumbuhan optimal bayi.

            #### 3. Persentase Bayi 0-5 Bulan ASI Eksklusif Recall 24 Jam
            - **Definisi Operasional:** Persentase bayi usia 0-5 bulan yang hanya menerima ASI dalam 24 jam terakhir sebelum wawancara, di wilayah kerja puskesmas pada periode pelaporan. Metrik ini mengukur kepatuhan ASI eksklusif secara real-time.  
            - **Rumus Perhitungan:**  
            $$ \\text{Recall 24 Jam (\\%)} = \\frac{\\text{Jumlah bayi 0-5 bulan dengan ASI eksklusif dalam 24 jam}}{\\text{Jumlah bayi 0-5 bulan yang diwawancarai}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen bayi 0-5 bulan yang hanya minum ASI kemarin dari total bayi yang ditanya, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui wawancara recall 24 jam oleh kader posyandu atau petugas kesehatan, dengan laporan bulanan berdasarkan daftar bayi yang diwawancarai.  
            - **Insight Analisis:** Persentase di bawah 60% dapat mengindikasikan pemberian susu formula atau air karena kurangnya pengetahuan ibu. Intervensi seperti kelompok dukungan ibu menyusui dan kampanye “ASI saja cukup” dapat meningkatkan kepatuhan, mengurangi risiko diare dan infeksi pada bayi.

            #### 4. Persentase Proporsi Sampling Bayi 0-5 Bulan Recall ASI
            - **Definisi Operasional:** Persentase bayi usia 0-5 bulan yang diwawancarai untuk recall konsumsi ASI dari total populasi bayi usia 0-5 bulan, di wilayah kerja puskesmas pada periode pelaporan. Metrik ini mengukur representasi sampel.  
            - **Rumus Perhitungan:**  
            $$ \\text{Proporsi Sampling (\\%)} = \\frac{\\text{Jumlah bayi 0-5 bulan yang diwawancarai}}{\\text{Jumlah total bayi usia 0-5 bulan}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen bayi 0-5 bulan yang ditanya tentang ASI dari total bayi pada usia tersebut, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data diambil dari daftar wawancara posyandu atau kunjungan rumah, dibandingkan dengan register bayi 0-5 bulan, dilaporkan bulanan.  
            - **Insight Analisis:** Proporsi di bawah 70% menunjukkan sampel yang kurang representatif, yang dapat memengaruhi keakuratan metrik recall. Peningkatan koordinasi kader untuk menjangkau lebih banyak ibu dan penggunaan aplikasi pencatatan digital dapat memastikan sampel lebih luas, meningkatkan validitas data ASI.

            #### 5. Persentase Anak Usia 6-23 Bulan Konsumsi 5 dari 8 Kelompok Makanan
            - **Definisi Operasional:** Persentase anak usia 6-23 bulan yang mengonsumsi setidaknya 5 dari 8 kelompok makanan (misalnya, biji-bijian, sayur, buah, daging, telur, susu, kacang, lemak) pada hari sebelum wawancara, di wilayah kerja puskesmas.  
            - **Rumus Perhitungan:**  
            $$ \\text{Konsumsi 5 Kelompok (\\%)} = \\frac{\\text{Jumlah anak 6-23 bulan konsumsi 5 kelompok makanan}}{\\text{Jumlah anak 6-23 bulan yang diwawancarai}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen anak 6-23 bulan yang makan 5 jenis makanan kemarin dari total anak yang ditanya, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui wawancara recall 24 jam oleh kader posyandu, dengan pencatatan kelompok makanan yang dikonsumsi anak, dilaporkan bulanan.  
            - **Insight Analisis:** Persentase di bawah 40% (standar WHO untuk keanekaragaman pangan) dapat mengindikasikan pola makan monoton, sering karena keterbatasan ekonomi atau pengetahuan gizi. Edukasi orang tua tentang menu MPASI beragam dan program kebun gizi keluarga dapat meningkatkan keanekaragaman, mencegah stunting dan defisiensi mikronutrien.

            #### 6. Persentase Anak Usia 6-23 Bulan Konsumsi Telur, Ikan, Daging
            - **Definisi Operasional:** Persentase anak usia 6-23 bulan yang mengonsumsi setidaknya satu dari telur, ikan, atau daging pada hari sebelum wawancara, di wilayah kerja puskesmas. Metrik ini mengevaluasi asupan protein hewani.  
            - **Rumus Perhitungan:**  
            $$ \\text{Konsumsi Telur/Ikan/Daging (\\%)} = \\frac{\\text{Jumlah anak 6-23 bulan konsumsi telur/ikan/daging}}{\\text{Jumlah anak 6-23 bulan yang diwawancarai}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen anak 6-23 bulan yang makan telur, ikan, atau daging kemarin dari total anak yang ditanya, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data diambil melalui wawancara recall 24 jam di posyandu, dengan fokus pada konsumsi protein hewani, dilaporkan bulanan.  
            - **Insight Analisis:** Persentase di bawah 50% dapat mencerminkan akses terbatas ke protein hewani atau preferensi pola makan nabati. Inisiatif seperti distribusi telur gratis di posyandu atau edukasi tentang protein alternatif (misalnya, tempe) dapat meningkatkan asupan, mendukung pertumbuhan otot dan perkembangan kognitif anak.

            #### 7. Persentase Anak Usia 6-23 Bulan Mendapat MPASI Baik
            - **Definisi Operasional:** Persentase anak usia 6-23 bulan yang menerima MPASI dengan kualitas baik, yaitu memenuhi frekuensi makan, keanekaragaman pangan, dan porsi sesuai pedoman WHO, di wilayah kerja puskesmas.  
            - **Rumus Perhitungan:**  
            $$ \\text{MPASI Baik (\\%)} = \\frac{\\text{Jumlah anak 6-23 bulan dengan MPASI baik}}{\\text{Jumlah anak 6-23 bulan yang diwawancarai}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen anak 6-23 bulan yang mendapat MPASI berkualitas dari total anak yang ditanya, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui wawancara recall 24 jam dan penilaian MPASI berdasarkan checklist WHO (frekuensi, jumlah kelompok makanan, tekstur), dilaporkan bulanan oleh kader posyandu.  
            - **Insight Analisis:** Persentase di bawah 30% menunjukkan tantangan dalam kualitas MPASI, sering karena kurangnya pengetahuan atau sumber daya. Pelatihan ibu tentang resep MPASI lokal yang bergizi dan penyediaan bahan pangan terjangkau melalui koperasi desa dapat meningkatkan kualitas MPASI, mengurangi risiko gizi buruk dan stunting.

            </div>
        """, unsafe_allow_html=True)


    if filtered_df.empty:
        st.warning("⚠️ Tidak ada data untuk ditampilkan.")
        return {}, pd.DataFrame(), []

    # Kolom pengelompokan
    group_columns = ["Puskesmas"] if puskesmas_filter == "All" else ["Puskesmas", "Kelurahan"]
    
    # Agregasi data
    current_df = filtered_df.groupby(group_columns).agg({
        "Jumlah_Bayi_Mendapat_IMD": "sum",
        "Jumlah_bayi_baru_lahir_bulan_ini_B": "sum",
        "Jumlah_Bayi_Asi_Eksklusif_sampai_6_bulan": "sum",
        "Jumlah_Bayi_usia_6_bulan": "sum",
        "Jumlah_Bayi_usia_0-5_bulan_yang_mendapat_ASI_Eksklusif_berdasarkan_recall_24_jam": "sum",
        "Jumlah_Bayi_usia_0-5_bulan_yang_direcall": "sum",
        "Jumlah_anak_usia_6-23_bulan_yang_mengkonsumsi_makanan_dan_minuman_setidaknya_5_dari_8_jenis_kelompok_makanan_pada_hari_kemarin_sebelum_wawancara": "sum",
        "Jumlah_anak_usia_6-23_bulan_yang_diwawancarai": "sum",
        "Jumlah_anak_usia_6-23_bulan_yang_mengkonsumsi_telur_ikan_dan_atau_daging_pada_hari_kemarin_sebelum_wawancara": "sum",
        "Jumlah_anak_usia_6-23_bulan_yang_mendapat_MPASI_baik": "sum",
        "Jumlah_Bayi_usia_0-5_bulan": "sum",
    }).reset_index()

    # Agregasi data sebelumnya
    previous_agg_df = pd.DataFrame()
    if not previous_df.empty:
        previous_agg_df = previous_df.groupby(group_columns).agg({
            "Jumlah_Bayi_Mendapat_IMD": "sum",
            "Jumlah_bayi_baru_lahir_bulan_ini_B": "sum",
            "Jumlah_Bayi_Asi_Eksklusif_sampai_6_bulan": "sum",
            "Jumlah_Bayi_usia_6_bulan": "sum",
            "Jumlah_Bayi_usia_0-5_bulan_yang_mendapat_ASI_Eksklusif_berdasarkan_recall_24_jam": "sum",
            "Jumlah_Bayi_usia_0-5_bulan_yang_direcall": "sum",
            "Jumlah_anak_usia_6-23_bulan_yang_mengkonsumsi_makanan_dan_minuman_setidaknya_5_dari_8_jenis_kelompok_makanan_pada_hari_kemarin_sebelum_wawancara": "sum",
            "Jumlah_anak_usia_6-23_bulan_yang_diwawancarai": "sum",
            "Jumlah_anak_usia_6-23_bulan_yang_mengkonsumsi_telur_ikan_dan_atau_daging_pada_hari_kemarin_sebelum_wawancara": "sum",
            "Jumlah_anak_usia_6-23_bulan_yang_mendapat_MPASI_baik": "sum",
            "Jumlah_Bayi_usia_0-5_bulan": "sum",
        }).reset_index()

    # Perhitungan metrik untuk current_df
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

    # Perhitungan metrik untuk previous_agg_df
    if not previous_agg_df.empty:
        previous_agg_df["Metrik Bayi Mendapat IMD (%)"] = previous_agg_df.apply(
            lambda x: (x["Jumlah_Bayi_Mendapat_IMD"] / x["Jumlah_bayi_baru_lahir_bulan_ini_B"] * 100)
            if x["Jumlah_bayi_baru_lahir_bulan_ini_B"] != 0 else 0, axis=1
        ).round(2)
        previous_agg_df["Metrik Jumlah Bayi ASI Eksklusif Sampai 6 Bulan (%)"] = previous_agg_df.apply(
            lambda x: (x["Jumlah_Bayi_Asi_Eksklusif_sampai_6_bulan"] / x["Jumlah_Bayi_usia_6_bulan"] * 100)
            if x["Jumlah_Bayi_usia_6_bulan"] != 0 else 0, axis=1
        ).round(2)
        previous_agg_df["Metrik Bayi 0-5 Bulan ASI Eksklusif Recall 24 Jam (%)"] = previous_agg_df.apply(
            lambda x: (x["Jumlah_Bayi_usia_0-5_bulan_yang_mendapat_ASI_Eksklusif_berdasarkan_recall_24_jam"] / x["Jumlah_Bayi_usia_0-5_bulan_yang_direcall"] * 100)
            if x["Jumlah_Bayi_usia_0-5_bulan_yang_direcall"] != 0 else 0, axis=1
        ).round(2)
        previous_agg_df["Metrik Proporsi Sampling Bayi 0-5 Bulan Recall ASI (%)"] = previous_agg_df.apply(
            lambda x: (x["Jumlah_Bayi_usia_0-5_bulan_yang_direcall"] / x["Jumlah_Bayi_usia_0-5_bulan"] * 100)
            if x["Jumlah_Bayi_usia_0-5_bulan"] != 0 else 0, axis=1
        ).round(2)
        previous_agg_df["Metrik Anak Usia 6-23 Bulan Konsumsi 5 dari 8 Kelompok Makanan (%)"] = previous_agg_df.apply(
            lambda x: (x["Jumlah_anak_usia_6-23_bulan_yang_mengkonsumsi_makanan_dan_minuman_setidaknya_5_dari_8_jenis_kelompok_makanan_pada_hari_kemarin_sebelum_wawancara"] / x["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"] * 100)
            if x["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"] != 0 else 0, axis=1
        ).round(2)
        previous_agg_df["Metrik Anak Usia 6-23 Bulan Konsumsi Telur, Ikan, Daging (%)"] = previous_agg_df.apply(
            lambda x: (x["Jumlah_anak_usia_6-23_bulan_yang_mengkonsumsi_telur_ikan_dan_atau_daging_pada_hari_kemarin_sebelum_wawancara"] / x["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"] * 100)
            if x["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"] != 0 else 0, axis=1
        ).round(2)
        previous_agg_df["Metrik Anak Usia 6-23 Bulan Mendapat MPASI Baik (%)"] = previous_agg_df.apply(
            lambda x: (x["Jumlah_anak_usia_6-23_bulan_yang_mendapat_MPASI_baik"] / x["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"] * 100)
            if x["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"] != 0 else 0, axis=1
        ).round(2)

    # Scorecard
    metrics = {}
    metric_list = [
        "Metrik Bayi Mendapat IMD (%)",
        "Metrik Jumlah Bayi ASI Eksklusif Sampai 6 Bulan (%)",
        "Metrik Bayi 0-5 Bulan ASI Eksklusif Recall 24 Jam (%)",
        "Metrik Proporsi Sampling Bayi 0-5 Bulan Recall ASI (%)",
        "Metrik Anak Usia 6-23 Bulan Konsumsi 5 dari 8 Kelompok Makanan (%)",
        "Metrik Anak Usia 6-23 Bulan Konsumsi Telur, Ikan, Daging (%)",
        "Metrik Anak Usia 6-23 Bulan Mendapat MPASI Baik (%)",
    ]

    if puskesmas_filter == "All":
        # Hitung total untuk kabupaten
        total_imd = current_df["Jumlah_Bayi_Mendapat_IMD"].sum()
        total_newborn = current_df["Jumlah_bayi_baru_lahir_bulan_ini_B"].sum()
        total_asi_6bulan = current_df["Jumlah_Bayi_Asi_Eksklusif_sampai_6_bulan"].sum()
        total_bayi_6bulan = current_df["Jumlah_Bayi_usia_6_bulan"].sum()
        total_recall_asi = current_df["Jumlah_Bayi_usia_0-5_bulan_yang_mendapat_ASI_Eksklusif_berdasarkan_recall_24_jam"].sum()
        total_recall = current_df["Jumlah_Bayi_usia_0-5_bulan_yang_direcall"].sum()
        total_bayi_05 = current_df["Jumlah_Bayi_usia_0-5_bulan"].sum()
        total_makanan_5kelompok = current_df["Jumlah_anak_usia_6-23_bulan_yang_mengkonsumsi_makanan_dan_minuman_setidaknya_5_dari_8_jenis_kelompok_makanan_pada_hari_kemarin_sebelum_wawancara"].sum()
        total_telur_ikan_daging = current_df["Jumlah_anak_usia_6-23_bulan_yang_mengkonsumsi_telur_ikan_dan_atau_daging_pada_hari_kemarin_sebelum_wawancara"].sum()
        total_mpasi_baik = current_df["Jumlah_anak_usia_6-23_bulan_yang_mendapat_MPASI_baik"].sum()
        total_diwawancarai = current_df["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"].sum()

        # Hitung total sebelumnya
        prev_total_imd = previous_agg_df["Jumlah_Bayi_Mendapat_IMD"].sum() if not previous_agg_df.empty else 0
        prev_total_newborn = previous_agg_df["Jumlah_bayi_baru_lahir_bulan_ini_B"].sum() if not previous_agg_df.empty else 0
        prev_total_asi_6bulan = previous_agg_df["Jumlah_Bayi_Asi_Eksklusif_sampai_6_bulan"].sum() if not previous_agg_df.empty else 0
        prev_total_bayi_6bulan = previous_agg_df["Jumlah_Bayi_usia_6_bulan"].sum() if not previous_agg_df.empty else 0
        prev_total_recall_asi = previous_agg_df["Jumlah_Bayi_usia_0-5_bulan_yang_mendapat_ASI_Eksklusif_berdasarkan_recall_24_jam"].sum() if not previous_agg_df.empty else 0
        prev_total_recall = previous_agg_df["Jumlah_Bayi_usia_0-5_bulan_yang_direcall"].sum() if not previous_agg_df.empty else 0
        prev_total_bayi_05 = previous_agg_df["Jumlah_Bayi_usia_0-5_bulan"].sum() if not previous_agg_df.empty else 0
        prev_total_makanan_5kelompok = previous_agg_df["Jumlah_anak_usia_6-23_bulan_yang_mengkonsumsi_makanan_dan_minuman_setidaknya_5_dari_8_jenis_kelompok_makanan_pada_hari_kemarin_sebelum_wawancara"].sum() if not previous_agg_df.empty else 0
        prev_total_telur_ikan_daging = previous_agg_df["Jumlah_anak_usia_6-23_bulan_yang_mengkonsumsi_telur_ikan_dan_atau_daging_pada_hari_kemarin_sebelum_wawancara"].sum() if not previous_agg_df.empty else 0
        prev_total_mpasi_baik = previous_agg_df["Jumlah_anak_usia_6-23_bulan_yang_mendapat_MPASI_baik"].sum() if not previous_agg_df.empty else 0
        prev_total_diwawancarai = previous_agg_df["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"].sum() if not previous_agg_df.empty else 0

        # Hitung persentase untuk scorecard
        current_values = {
            "Metrik Bayi Mendapat IMD (%)": (total_imd / total_newborn * 100) if total_newborn != 0 else 0,
            "Metrik Jumlah Bayi ASI Eksklusif Sampai 6 Bulan (%)": (total_asi_6bulan / total_bayi_6bulan * 100) if total_bayi_6bulan != 0 else 0,
            "Metrik Bayi 0-5 Bulan ASI Eksklusif Recall 24 Jam (%)": (total_recall_asi / total_recall * 100) if total_recall != 0 else 0,
            "Metrik Proporsi Sampling Bayi 0-5 Bulan Recall ASI (%)": (total_recall / total_bayi_05 * 100) if total_bayi_05 != 0 else 0,
            "Metrik Anak Usia 6-23 Bulan Konsumsi 5 dari 8 Kelompok Makanan (%)": (total_makanan_5kelompok / total_diwawancarai * 100) if total_diwawancarai != 0 else 0,
            "Metrik Anak Usia 6-23 Bulan Konsumsi Telur, Ikan, Daging (%)": (total_telur_ikan_daging / total_diwawancarai * 100) if total_diwawancarai != 0 else 0,
            "Metrik Anak Usia 6-23 Bulan Mendapat MPASI Baik (%)": (total_mpasi_baik / total_diwawancarai * 100) if total_diwawancarai != 0 else 0,
        }
        previous_values = {
            "Metrik Bayi Mendapat IMD (%)": (prev_total_imd / prev_total_newborn * 100) if prev_total_newborn != 0 else None,
            "Metrik Jumlah Bayi ASI Eksklusif Sampai 6 Bulan (%)": (prev_total_asi_6bulan / prev_total_bayi_6bulan * 100) if prev_total_bayi_6bulan != 0 else None,
            "Metrik Bayi 0-5 Bulan ASI Eksklusif Recall 24 Jam (%)": (prev_total_recall_asi / prev_total_recall * 100) if prev_total_recall != 0 else None,
            "Metrik Proporsi Sampling Bayi 0-5 Bulan Recall ASI (%)": (prev_total_recall / prev_total_bayi_05 * 100) if prev_total_bayi_05 != 0 else None,
            "Metrik Anak Usia 6-23 Bulan Konsumsi 5 dari 8 Kelompok Makanan (%)": (prev_total_makanan_5kelompok / prev_total_diwawancarai * 100) if prev_total_diwawancarai != 0 else None,
            "Metrik Anak Usia 6-23 Bulan Konsumsi Telur, Ikan, Daging (%)": (prev_total_telur_ikan_daging / prev_total_diwawancarai * 100) if prev_total_diwawancarai != 0 else None,
            "Metrik Anak Usia 6-23 Bulan Mendapat MPASI Baik (%)": (prev_total_mpasi_baik / prev_total_diwawancarai * 100) if prev_total_diwawancarai != 0 else None,
        }

        for metric in metric_list:
            current_value = current_values[metric]
            previous_value = previous_values[metric]
            metrics[metric] = calculate_asi_metric(current_value, previous_value)
    else:
        for metric in metric_list:
            current_value = current_df[metric].mean()
            previous_value = previous_agg_df[metric].mean() if not previous_agg_df.empty else None
            metrics[metric] = calculate_asi_metric(current_value, previous_value)

    # Tampilkan scorecard
    st.subheader("📈 Scorecard Metrik ASI Eksklusif & MPASI")
    cols = st.columns(4)
    for i, metric in enumerate(metric_list):
        value, delta = metrics[metric]
        with cols[i % 4]:
            st.metric(label=metric, value=f"{value:.2f}%", delta=delta)

    # Visualisasi
    st.subheader("📊 Visualisasi Data")
    visualization_options = metric_list
    
    selected_visualization = st.selectbox(
        "Pilih Metrik untuk Visualisasi",
        visualization_options,
        key="asi_mpasi_viz_select"  # Ganti uuid dengan key statis untuk menghindari error
    )
    
    if selected_visualization:
        x_axis = "Puskesmas" if puskesmas_filter == "All" else "Kelurahan"
        title = f"{selected_visualization} per {x_axis}"
        fig = px.bar(
            current_df,
            x=x_axis,
            y=selected_visualization,
            title=title,
            labels={x_axis: x_axis, selected_visualization: selected_visualization},
            color=x_axis,
            text=selected_visualization,
        )
        fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
        fig.update_layout(
            xaxis_title=x_axis,
            yaxis_title=selected_visualization,
            showlegend=False,
            xaxis_tickangle=45,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Tabel rekapitulasi
    st.subheader("📋 Rekapitulasi Capaian ASI Eksklusif & MPASI")
    st.dataframe(current_df)
    
    return metrics, current_df, []
# ----------------------------- #
# 🥗 Analisis Masalah Gizi
# ----------------------------- #
def calculate_nutrition_metric(current, previous, target):
    """Menghitung metrik gizi dengan nilai saat ini, sebelumnya, dan target."""
    if current is None or pd.isna(current):
        return 0, "N/A", "N/A"
    
    # Bulatkan nilai saat ini
    current = round(current, 2)
    
    # Hitung delta (perubahan dari periode sebelumnya)
    delta = "N/A"
    if previous is not None and not pd.isna(previous):
        delta_value = current - previous
        delta = f"{delta_value:+.2f}%"
    
    # Tentukan status berdasarkan target
    status = "Baik" if current <= target else "Perhatian"
    
    return current, delta, status

def nutrition_issues_analysis(filtered_df, previous_df, desa_df, puskesmas_filter, kelurahan_filter, bulan_filter_int):
    """Menghitung metrik masalah gizi dan mengembalikan data untuk PDF."""
    st.header("🥗 Analisis Masalah Gizi")
   
    # Informasi terkait masalah gizi dengan pendekatan visual (collapsible) dan tone akademik formal
    st.markdown(
        """
        <style>
        .info-box {
            background-color: #e6f0fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 15px;
            width: 100%;
            box-sizing: border-box;
        }
        .info-box * {
            background-color: #e6f0fa !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    with st.expander("📚 Informasi Mengenai Masalah Gizi pada Balita", expanded=False):
        st.markdown(
            """
            <div class="info-box">
            <h3>Pemahaman Masalah Gizi pada Balita: Stunting, Wasting, Underweight, dan Overweight</h3>

            Masalah gizi pada balita merupakan indikator penting dalam menilai status kesehatan dan perkembangan anak. Berikut adalah penjelasan mengenai empat indikator utama yang dianalisis dalam dashboard ini, beserta formula perhitungannya:

            1. <strong>Stunting (Kerdil)</strong>  
            Stunting mengacu pada kondisi pertumbuhan terhambat akibat kekurangan gizi kronis, yang biasanya terlihat dari tinggi badan balita yang jauh di bawah standar untuk usianya. Stunting memiliki dampak jangka panjang terhadap perkembangan kognitif dan produktivitas anak.  
            <strong>Formula Perhitungan:</strong>  
            </div>
            """,
            unsafe_allow_html=True
        )
        st.latex(r"\text{Prevalensi Stunting (\%)} = \left( \frac{\text{Jumlah Balita Stunting}}{\text{Jumlah Balita yang Diukur Panjang/Tinggi Badan}} \right) \times 100")

        st.markdown(
            """
            <div class="info-box">
            2. <strong>Wasting (Kurus)</strong>  
            Wasting menunjukkan kekurangan gizi akut, di mana berat badan balita sangat rendah dibandingkan dengan tinggi badannya. Kondisi ini sering terjadi akibat kelaparan atau penyakit akut.  
            <strong>Formula Perhitungan:</strong>  
            </div>
            """,
            unsafe_allow_html=True
        )
        st.latex(r"\text{Prevalensi Wasting (\%)} = \left( \frac{\text{Jumlah Balita Wasting}}{\text{Jumlah Balita Ditimbang dan Diukur}} \right) \times 100")

        st.markdown(
            """
            <div class="info-box">
            3. <strong>Underweight (Berat Badan Kurang)</strong>  
            Underweight mengindikasikan berat badan balita yang rendah untuk usianya, yang dapat disebabkan oleh kekurangan gizi baik akut maupun kronis.  
            <strong>Formula Perhitungan:</strong>  
            </div>
            """,
            unsafe_allow_html=True
        )
        st.latex(r"\text{Prevalensi Underweight (\%)} = \left( \frac{\text{Jumlah Balita Underweight}}{\text{Jumlah Balita Ditimbang}} \right) \times 100")

        st.markdown(
            """
            <div class="info-box">
            4. <strong>Overweight (Berat Badan Berlebih)</strong>  
            Overweight menunjukkan berat badan balita yang melebihi standar untuk usianya, sering kali akibat asupan kalori berlebih dan kurangnya aktivitas fisik. Kondisi ini dapat meningkatkan risiko obesitas di masa depan.  
            <strong>Formula Perhitungan:</strong>  
            </div>
            """,
            unsafe_allow_html=True
        )
        st.latex(r"\text{Prevalensi Overweight (\%)} = \left( \frac{\text{Jumlah Balita Overweight}}{\text{Jumlah Balita Ditimbang}} \right) \times 100")

        st.markdown(
            """
            <div class="info-box">
            <strong>Sumber dan Referensi:</strong>  
            Indikator gizi ini diukur berdasarkan standar antropometri WHO (2006) dan menjadi fokus utama dalam intervensi kesehatan masyarakat untuk memastikan pertumbuhan optimal balita. Pemantauan prevalensi gizi secara berkala sangat penting untuk merancang strategi pencegahan dan penanganan yang efektif.
            </div>
            """,
            unsafe_allow_html=True
        )

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
    if filtered_df.empty:
        st.warning("⚠️ Tidak ada data untuk ditampilkan.")
        return {}, pd.DataFrame(), None, []

    # Target prevalensi
    target_stunting = 14  # Target prevalensi stunting (%)
    target_wasting = 7    # Target prevalensi wasting (%)
    target_underweight = 10  # Target prevalensi underweight (%)
    target_overweight = 5  # Target prevalensi overweight (%)

    # Kolom pengelompokan
    group_columns = ["Puskesmas"] if puskesmas_filter == "All" else ["Puskesmas", "Kelurahan"]
    
    # Agregasi data
    current_df = filtered_df.groupby(group_columns).agg({
        "Jumlah_balita_stunting": "sum",
        "Jumlah_balita_diukur_PBTB": "sum",
        "Jumlah_balita_wasting": "sum",
        "Jumlah_balita_ditimbang_dan_diukur": "sum",
        "Jumlah_balita_underweight": "sum",
        "Jumlah_balita_ditimbang": "sum",
        "Jumlah_balita_overweight": "sum",
    }).reset_index()

    # Agregasi data sebelumnya
    previous_agg_df = pd.DataFrame()
    if not previous_df.empty:
        previous_agg_df = previous_df.groupby(group_columns).agg({
            "Jumlah_balita_stunting": "sum",
            "Jumlah_balita_diukur_PBTB": "sum",
            "Jumlah_balita_wasting": "sum",
            "Jumlah_balita_ditimbang_dan_diukur": "sum",
            "Jumlah_balita_underweight": "sum",
            "Jumlah_balita_ditimbang": "sum",
            "Jumlah_balita_overweight": "sum",
        }).reset_index()

    # Perhitungan prevalensi saat ini per puskesmas/kelurahan
    current_df["Prevalensi Stunting (%)"] = current_df.apply(
        lambda x: (x["Jumlah_balita_stunting"] / x["Jumlah_balita_diukur_PBTB"] * 100)
        if x["Jumlah_balita_diukur_PBTB"] != 0 else 0, axis=1
    ).round(2)
    current_df["Prevalensi Wasting (%)"] = current_df.apply(
        lambda x: (x["Jumlah_balita_wasting"] / x["Jumlah_balita_ditimbang_dan_diukur"] * 100)
        if x["Jumlah_balita_ditimbang_dan_diukur"] != 0 else 0, axis=1
    ).round(2)
    current_df["Prevalensi Underweight (%)"] = current_df.apply(
        lambda x: (x["Jumlah_balita_underweight"] / x["Jumlah_balita_ditimbang"] * 100)
        if x["Jumlah_balita_ditimbang"] != 0 else 0, axis=1
    ).round(2)
    current_df["Prevalensi Overweight (%)"] = current_df.apply(
        lambda x: (x["Jumlah_balita_overweight"] / x["Jumlah_balita_ditimbang"] * 100)
        if x["Jumlah_balita_ditimbang"] != 0 else 0, axis=1
    ).round(2)

    # Perhitungan prevalensi sebelumnya per puskesmas/kelurahan
    if not previous_agg_df.empty:
        previous_agg_df["Prevalensi Stunting (%)"] = previous_agg_df.apply(
            lambda x: (x["Jumlah_balita_stunting"] / x["Jumlah_balita_diukur_PBTB"] * 100)
            if x["Jumlah_balita_diukur_PBTB"] != 0 else 0, axis=1
        ).round(2)
        previous_agg_df["Prevalensi Wasting (%)"] = previous_agg_df.apply(
            lambda x: (x["Jumlah_balita_wasting"] / x["Jumlah_balita_ditimbang_dan_diukur"] * 100)
            if x["Jumlah_balita_ditimbang_dan_diukur"] != 0 else 0, axis=1
        ).round(2)
        previous_agg_df["Prevalensi Underweight (%)"] = previous_agg_df.apply(
            lambda x: (x["Jumlah_balita_underweight"] / x["Jumlah_balita_ditimbang"] * 100)
            if x["Jumlah_balita_ditimbang"] != 0 else 0, axis=1
        ).round(2)
        previous_agg_df["Prevalensi Overweight (%)"] = previous_agg_df.apply(
            lambda x: (x["Jumlah_balita_overweight"] / x["Jumlah_balita_ditimbang"] * 100)
            if x["Jumlah_balita_ditimbang"] != 0 else 0, axis=1
        ).round(2)

    # Perhitungan metrik total (seperti growth_development_metrics)
    total_balita_diukur_PBTB = filtered_df["Jumlah_balita_diukur_PBTB"].sum()
    total_timbang_ukur_balita = filtered_df["Jumlah_balita_ditimbang_dan_diukur"].sum()
    total_timbang_balita = filtered_df["Jumlah_balita_ditimbang"].sum()

    total_prev_balita_diukur_PBTB = previous_df["Jumlah_balita_diukur_PBTB"].sum() if not previous_df.empty else 0
    total_prev_timbang_ukur_balita = previous_df["Jumlah_balita_ditimbang_dan_diukur"].sum() if not previous_df.empty else 0
    total_prev_timbang_balita = previous_df["Jumlah_balita_ditimbang"].sum() if not previous_df.empty else 0

    prevalensi_stunting = round(filtered_df["Jumlah_balita_stunting"].sum() / total_balita_diukur_PBTB * 100 if total_balita_diukur_PBTB else 0, 2)
    prevalensi_wasting = round(filtered_df["Jumlah_balita_wasting"].sum() / total_timbang_ukur_balita * 100 if total_timbang_ukur_balita else 0, 2)
    prevalensi_underweight = round(filtered_df["Jumlah_balita_underweight"].sum() / total_timbang_balita * 100 if total_timbang_balita else 0, 2)
    prevalensi_overweight = round(filtered_df["Jumlah_balita_overweight"].sum() / total_timbang_balita * 100 if total_timbang_balita else 0, 2)

    prev_prevalensi_stunting = round(previous_df["Jumlah_balita_stunting"].sum() / total_prev_balita_diukur_PBTB * 100 if total_prev_balita_diukur_PBTB else 0, 2) if not previous_df.empty else None
    prev_prevalensi_wasting = round(previous_df["Jumlah_balita_wasting"].sum() / total_prev_timbang_ukur_balita * 100 if total_prev_timbang_ukur_balita else 0, 2) if not previous_df.empty else None
    prev_prevalensi_underweight = round(previous_df["Jumlah_balita_underweight"].sum() / total_prev_timbang_balita * 100 if total_prev_timbang_balita else 0, 2) if not previous_df.empty else None
    prev_prevalensi_overweight = round(previous_df["Jumlah_balita_overweight"].sum() / total_prev_timbang_balita * 100 if total_prev_timbang_balita else 0, 2) if not previous_df.empty else None

    # Perhitungan metrik
    metrics = {
        "Prevalensi Stunting": calculate_nutrition_metric(prevalensi_stunting, prev_prevalensi_stunting, target_stunting),
        "Prevalensi Wasting": calculate_nutrition_metric(prevalensi_wasting, prev_prevalensi_wasting, target_wasting),
        "Prevalensi Underweight": calculate_nutrition_metric(prevalensi_underweight, prev_prevalensi_underweight, target_underweight),
        "Prevalensi Overweight": calculate_nutrition_metric(prevalensi_overweight, prev_prevalensi_overweight, target_overweight),
    }

    # Tampilkan scorecard
    st.subheader("📊 Metrik Prevalensi Masalah Gizi")
    cols = st.columns(4)
    for i, (metric, (value, delta, status)) in enumerate(metrics.items()):
        with cols[i % 4]:
            st.metric(label=metric, value=f"{value:.2f}%", delta=delta, delta_color="inverse" if status == "Perhatian" else "normal")

    # Visualisasi: Grafik Prevalensi Masalah Gizi (4 bar chart)
    st.subheader("📊 Grafik Prevalensi Masalah Gizi")
    metrics_df = pd.DataFrame({
        "Metrik": ["Stunting", "Wasting", "Underweight", "Overweight"],
        "Prevalensi (%)": [prevalensi_stunting, prevalensi_wasting, prevalensi_underweight, prevalensi_overweight]
    })
    fig = px.bar(
        metrics_df,
        x="Metrik",
        y="Prevalensi (%)",
        title="Prevalensi Masalah Gizi",
        text="Prevalensi (%)",
        color="Metrik",
    )
    fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    fig.update_layout(
        xaxis_title="Metrik",
        yaxis_title="Persentase (%)",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Grafik terpisah untuk setiap metrik dengan garis target
    st.subheader("📊 Grafik Prevalensi per Puskesmas/Kelurahan")
    prevalence_charts = []
    target_values = {
        "Prevalensi Stunting (%)": target_stunting,
        "Prevalensi Wasting (%)": target_wasting,
        "Prevalensi Underweight (%)": target_underweight,
        "Prevalensi Overweight (%)": target_overweight
    }
    for metric in ["Prevalensi Stunting (%)", "Prevalensi Wasting (%)", "Prevalensi Underweight (%)", "Prevalensi Overweight (%)"]:
        chart = px.bar(
            current_df,
            x="Puskesmas" if puskesmas_filter == "All" else "Kelurahan",
            y=metric,
            title=f"{metric} per {'Puskesmas' if puskesmas_filter == 'All' else 'Kelurahan'}",
            text=metric,
            color="Puskesmas" if puskesmas_filter == "All" else "Kelurahan",
        )
        chart.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
        # Tambahkan garis target
        chart.add_hline(
            y=target_values[metric],
            line_dash="dash",
            line_color="red",
            annotation_text=f"Target: {target_values[metric]}%",
            annotation_position="top right"
        )
        chart.update_layout(
            xaxis_title="Puskesmas" if puskesmas_filter == "All" else "Kelurahan",
            yaxis_title="Persentase (%)",
            showlegend=False,
            xaxis_tickangle=45,
        )
        prevalence_charts.append(chart)
        st.plotly_chart(chart, use_container_width=True)

    # Tabel rekapitulasi
    st.subheader("📋 Rekapitulasi Prevalensi Masalah Gizi")
    st.dataframe(current_df)

    return metrics, current_df, fig, prevalence_charts
# ----------------------------- #
# 🧑‍⚕️ Tatalaksana Balita Bermasalah Gizi
# ----------------------------- #
def tatalaksana_balita_bermasalah_gizi_analysis(df, desa_df, bulan_filter_int, puskesmas_filter, kelurahan_filter, jenis_laporan="Laporan Bulanan"):
    st.header("🧑‍⚕️ Analisis Tatalaksana Balita Bermasalah Gizi")

    # Filter data berdasarkan input
    filtered_df = df.copy()

    # Validasi untuk laporan tahunan
    if jenis_laporan == "Laporan Tahunan" and 'Bulan' in filtered_df.columns:
        available_months = filtered_df["Bulan"].unique()
        if not available_months.size:
            st.warning("⚠️ Tidak ada data yang sesuai dengan filter untuk periode yang dipilih.")
            return {}, pd.DataFrame(), []
        # Validasi bahwa bulan dalam filtered_df valid (1-12)
        invalid_months = filtered_df[~filtered_df["Bulan"].isin(range(1, 13))]["Bulan"].unique()
        if invalid_months.size:
            st.error(f"⚠️ Dataset berisi bulan tidak valid: {invalid_months}. Harap periksa data.")
            return {}, pd.DataFrame(), []

    # Filter untuk laporan bulanan
    if jenis_laporan == "Laporan Bulanan" and bulan_filter_int is not None and 'Bulan' in filtered_df.columns:
        if bulan_filter_int not in filtered_df["Bulan"].unique():
            st.warning(f"⚠️ Tidak ada data untuk bulan {bulan_filter_int}.")
            return {}, pd.DataFrame(), []
        filtered_df = filtered_df[filtered_df["Bulan"] == bulan_filter_int]

    # Filter Puskesmas dan Kelurahan
    if puskesmas_filter != "All":
        filtered_df = filtered_df[filtered_df["Puskesmas"] == puskesmas_filter]
    if kelurahan_filter != "All":
        filtered_df = filtered_df[filtered_df["Kelurahan"] == kelurahan_filter]

    # Pastikan data tidak kosong
    if filtered_df.empty:
        st.warning("⚠️ Tidak ada data yang sesuai dengan filter.")
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
        group_columns.append("Kelurahan")
    summary_df = filtered_df.groupby(group_columns).agg({
        col: "sum" for col in required_columns
    }).reset_index()

    # Validasi data tidak valid (numerator > denominator atau nilai negatif)
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
    for metric_name, (num, denom) in metrics_list.items():
        invalid_rows = summary_df[(summary_df[num] > summary_df[denom]) | (summary_df[num] < 0) | (summary_df[denom] < 0)]
        if not invalid_rows.empty:
            st.warning(f"⚠️ Data tidak valid untuk {metric_name}: {num} lebih besar dari {denom} atau ada nilai negatif.")
            break

    # Hitung persentase untuk setiap metrik seperti asi_exclusive_mpasi_analysis
    for metric_name, (numerator, denominator) in metrics_list.items():
        summary_df[metric_name] = summary_df.apply(
            lambda x: (x[numerator] / x[denominator] * 100) if x[denominator] != 0 else 0, axis=1
        ).round(2)

    # Hitung metrik untuk scorecard menggunakan total keseluruhan
    metrics = {}
    metric_names = list(metrics_list.keys())

    # Hitung total untuk semua metrik
    total_pmt_wasting = summary_df["Jumlah_balita_gizi_kurang_usia_6-59_bulan_yang_mendapatkan_makanan_tambahan_berbahan_pangan_lokal_sampai_bulan_ini"].sum()
    total_gizi_kurang = summary_df["Jumlah_seluruh_balita_(usia_6-59_bulan)_gizi_kurang_dengan_atau_tanpa_stunting_sampai_bulan_ini"].sum()
    total_pmt_underweight = summary_df["Jumlah_balita_BB_kurang_usia_6-59_bulan_yang_mendapatkan_makanan_tambahan_berbahan_pangan_lokal"].sum()
    total_bb_kurang = summary_df["Jumlah_seluruh_balita_(usia_6-59_bulan)_BB_kurang_yang_tidak_wasting_dengan_atau_tanpa_stunting_dan_tanpa_wasting"].sum()
    total_pmt_t659 = summary_df["Jumlah_Balita_T659_mendapatkan_PMT"].sum()
    total_sasaran_t = summary_df["Jumlah_sasaran_balita_T"].sum()
    total_perawatan_05 = summary_df["Jumlah_Kasus_Gizi_Buruk_bayi_0-5_Bulan_mendapat_perawatan_sampai_bulan_ini"].sum()
    total_gizi_buruk_05 = summary_df["Jumlah_kasus_gizi_buruk_bayi_0-5_Bulan_sampai_bulan_ini"].sum()
    total_perawatan_659 = summary_df["Jumlah_Kasus_Gizi_Buruk_Balita_6-59_Bulan_mendapat_perawatan_sampai_bulan_ini"].sum()
    total_gizi_buruk_659 = summary_df["Jumlah_kasus_gizi_buruk_Balita_6-59_Bulan_sampai_bulan_ini"].sum()
    total_stunting_dirujuk = summary_df["Jumlah_balita_stunting_dirujuk_Puskesmas_ke_RS_sampai_bulan_ini"].sum()
    total_stunting = summary_df["Jumlah_balita_stunting_sampai_bulan_ini"].sum()

    current_values = {
        "Balita Gizi Kurang (Wasting) 6-59 Bulan Mendapat PMT (%)": (total_pmt_wasting / total_gizi_kurang * 100) if total_gizi_kurang != 0 else 0,
        "Balita BB Kurang (Underweight) 6-59 Bulan Mendapat PMT (%)": (total_pmt_underweight / total_bb_kurang * 100) if total_bb_kurang != 0 else 0,
        "Balita BB Tidak Naik (T) 6-59 Bulan Mendapat PMT (%)": (total_pmt_t659 / total_sasaran_t * 100) if total_sasaran_t != 0 else 0,
        "Kasus Gizi Buruk Bayi 0-5 Bulan Mendapat Perawatan (%)": (total_perawatan_05 / total_gizi_buruk_05 * 100) if total_gizi_buruk_05 != 0 else 0,
        "Kasus Gizi Buruk Balita 6-59 Bulan Mendapat Perawatan (%)": (total_perawatan_659 / total_gizi_buruk_659 * 100) if total_gizi_buruk_659 != 0 else 0,
        "Balita Stunting Dirujuk ke RS (%)": (total_stunting_dirujuk / total_stunting * 100) if total_stunting != 0 else 0
    }

    for metric in metric_names:
        metrics[metric] = (current_values[metric], "")  # Delta belum dihitung karena tidak ada previous_df

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
        legend_orientation="h",
        legend=dict(y=-0.2, x=0, xanchor="left"),
    )
    st.plotly_chart(fig_pmt, key=f"tatalaksana_pmt_chart_{time.time()}", use_container_width=True)
    charts.append(fig_pmt)

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
        legend_orientation="h",
        legend=dict(y=-0.2, x=0, xanchor="left"),
    )
    st.plotly_chart(fig_malnutrisi, key=f"tatalaksana_malnutrisi_chart_{time.time()}", use_container_width=True)
    charts.append(fig_malnutrisi)

    # Tabel Rekapitulasi
    st.subheader("📋 Rekapitulasi Tatalaksana Balita Bermasalah Gizi")
    st.dataframe(summary_df, use_container_width=True)

    return metrics, summary_df, charts
# ----------------------------- #
# 🥗 Suplementasi Zat Gizi Micronutrients
# ----------------------------- #
def calculate_metric(current, previous):
    if current is None or pd.isna(current):
        return 0, ""
    delta = ""
    if previous is not None and not pd.isna(previous):
        delta_value = current - previous
        delta = f"{delta_value:+.2f}%"
    return round(current, 2), delta

def create_pdf_from_dataframe(df, filename="rekapitulasi_micronutrients.pdf"):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # Convert DataFrame to list of lists for Table
    data = [df.columns.tolist()] + df.values.tolist()
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

def micronutrient_supplementation_analysis(filtered_df, previous_df, desa_df, puskesmas_filter, kelurahan_filter, bulan_filter, jenis_laporan="Laporan Bulanan"):
    st.header("💊 Analisis Suplementasi Zat Gizi Mikro")
    
    # Informasi Metrik Suplementasi Zat Gizi
    with st.expander("📜 Definisi dan Insight Analisis Suplementasi Zat Gizi Mikro", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Analisis Indikator

            Berikut adalah definisi operasional, rumus perhitungan, serta analisis insight dari indikator-indikator yang digunakan untuk memantau suplementasi zat gizi mikro pada bayi dan balita dalam sistem kesehatan masyarakat. Rumus disajikan dalam format matematis untuk kejelasan, dengan penjelasan sederhana untuk memudahkan pemahaman.

            #### 1. Persentase Bayi Usia 6-11 Bulan yang Menerima Suplemen Vitamin A
            - **Definisi Operasional:** Persentase bayi usia 6-11 bulan yang menerima kapsul vitamin A dosis tinggi (biasanya 100.000 IU) dalam suatu periode pelaporan tertentu di wilayah kerja puskesmas. Suplementasi ini bertujuan untuk mencegah defisiensi vitamin A yang dapat mengganggu penglihatan dan imunitas.  
            - **Rumus Perhitungan:**  
            $$ \\text{Vitamin A Bayi 6-11 Bulan (\\%)} = \\frac{\\text{Jumlah bayi 6-11 bulan yang menerima vitamin A}}{\\text{Total bayi 6-11 bulan}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung berapa persen bayi usia 6-11 bulan yang mendapat kapsul vitamin A dari total bayi pada kelompok usia tersebut, lalu dikalikan 100 untuk mendapatkan persentase.  
            - **Metode Pengumpulan Data:** Data dikumpulkan bulanan melalui laporan dari posyandu atau puskesmas. Petugas kesehatan mencatat pemberian kapsul vitamin A kepada bayi yang memenuhi syarat usia, berdasarkan register imunisasi dan gizi.  
            - **Insight Analisis:** Persentase di bawah 80% dapat mengindikasikan rendahnya cakupan program suplementasi, yang mungkin disebabkan oleh kurangnya pasokan kapsul vitamin A, rendahnya kesadaran masyarakat, atau akses terbatas ke posyandu. Intervensi seperti kampanye edukasi gizi dan penguatan distribusi logistik dapat meningkatkan cakupan ini, mengurangi risiko xerophthalmia dan infeksi pada bayi.

            #### 2. Persentase Anak Usia 12-59 Bulan yang Menerima Suplemen Vitamin A
            - **Definisi Operasional:** Persentase anak usia 12-59 bulan yang menerima kapsul vitamin A dosis tinggi (biasanya 200.000 IU) sebanyak dua kali setahun dalam suatu periode pelaporan di wilayah kerja puskesmas. Tujuannya adalah mendukung pertumbuhan dan perkembangan optimal anak.  
            - **Rumus Perhitungan:**  
            $$ \\text{Vitamin A Anak 12-59 Bulan (\\%)} = \\frac{\\text{Jumlah anak 12-59 bulan yang menerima vitamin A}}{\\text{Total anak 12-59 bulan}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen anak usia 12-59 bulan yang mendapat kapsul vitamin A dari total anak pada kelompok usia tersebut, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data diambil dari laporan bulanan posyandu atau puskesmas, dengan pencatatan pemberian kapsul vitamin A oleh petugas kesehatan. Anak yang menerima dosis kedua dalam setahun juga dicatat untuk memastikan kepatuhan program.  
            - **Insight Analisis:** Jika persentase di bawah 85%, ini dapat menunjukkan adanya hambatan dalam frekuensi distribusi (misalnya, hanya sekali setahun) atau rendahnya partisipasi orang tua. Peningkatan pelatihan kader posyandu dan pengingat jadwal suplementasi melalui SMS atau media sosial dapat membantu mencapai target cakupan yang lebih tinggi, mendukung imunitas dan perkembangan kognitif anak.

            #### 3. Persentase Balita yang Menerima Suplementasi Zat Gizi Mikro
            - **Definisi Operasional:** Persentase balita dengan status gizi kurang (underweight) yang menerima suplementasi zat gizi mikro, seperti vitamin A, zat besi, atau seng, dalam suatu periode pelaporan di wilayah kerja puskesmas. Suplementasi ini menargetkan kelompok rentan untuk memperbaiki status gizi.  
            - **Rumus Perhitungan:**  
            $$ \\text{Suplementasi Zat Gizi Mikro (\\%)} = \\frac{\\text{Jumlah balita yang menerima suplementasi gizi mikro}}{\\text{Total balita dengan status gizi kurang}} \\times 100 $$  
            - **Penjelasan Sederhana:** Rumus ini menghitung persen balita gizi kurang yang mendapat suplementasi gizi mikro dari total balita gizi kurang, lalu dikalikan 100.  
            - **Metode Pengumpulan Data:** Data dikumpulkan melalui pemantauan bulanan di posyandu atau kunjungan rumah oleh kader kesehatan. Balita diidentifikasi sebagai gizi kurang berdasarkan pengukuran berat badan terhadap usia, lalu dicatat apakah mereka menerima suplementasi.  
            - **Insight Analisis:** Persentase di bawah 70% menunjukkan adanya kesenjangan dalam penargetan balita gizi kurang, yang mungkin disebabkan oleh identifikasi yang tidak akurat atau keterbatasan stok suplemen. Intervensi seperti peningkatan skrining gizi di posyandu, pelatihan kader untuk pengukuran antropometri yang tepat, dan koordinasi dengan dinas kesehatan untuk distribusi suplemen dapat meningkatkan cakupan, membantu mengurangi risiko stunting dan anemia.

            </div>
        """, unsafe_allow_html=True)

      
    if filtered_df.empty:
        st.warning("⚠️ Tidak ada data untuk ditampilkan.")
        return {}, pd.DataFrame(), None, None

    # Kolom pengelompokan
    group_columns = ["Puskesmas"] if puskesmas_filter == "All" else ["Puskesmas", "Kelurahan"]
    
    # Agregasi data
    current_df = filtered_df.groupby(group_columns).agg({
        "Jumlah_bayi_6-11_bulan_mendapat_Vitamin_A": "sum",
        "Jumlah_bayi_6-11_bulan": "sum",
        "Jumlah_anak_12-59_bulan_mendapat_Vitamin_A": "sum",
        "Jumlah_anak_12-59_bulan": "sum",
        "Jumlah_balita_yang_mendapatkan_suplementasi_gizi_mikro": "sum",
        "Jumlah_balita_Underweight_suplemen": "sum",
    }).reset_index()

    # Agregasi data sebelumnya
    previous_agg_df = pd.DataFrame()
    if not previous_df.empty:
        previous_agg_df = previous_df.groupby(group_columns).agg({
            "Jumlah_bayi_6-11_bulan_mendapat_Vitamin_A": "sum",
            "Jumlah_bayi_6-11_bulan": "sum",
            "Jumlah_anak_12-59_bulan_mendapat_Vitamin_A": "sum",
            "Jumlah_anak_12-59_bulan": "sum",
            "Jumlah_balita_yang_mendapatkan_suplementasi_gizi_mikro": "sum",
            "Jumlah_balita_Underweight_suplemen": "sum",
        }).reset_index()

    # Perhitungan metrik untuk current_df
    current_df["Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)"] = current_df.apply(
        lambda x: (x["Jumlah_bayi_6-11_bulan_mendapat_Vitamin_A"] / x["Jumlah_bayi_6-11_bulan"] * 100)
        if x["Jumlah_bayi_6-11_bulan"] != 0 else 0, axis=1
    ).round(2)
    current_df["Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)"] = current_df.apply(
        lambda x: (x["Jumlah_anak_12-59_bulan_mendapat_Vitamin_A"] / x["Jumlah_anak_12-59_bulan"] * 100)
        if x["Jumlah_anak_12-59_bulan"] != 0 else 0, axis=1
    ).round(2)
    current_df["Metrik Balita yang Mendapatkan Suplementasi Gizi Mikro (%)"] = current_df.apply(
        lambda x: (x["Jumlah_balita_yang_mendapatkan_suplementasi_gizi_mikro"] / x["Jumlah_balita_Underweight_suplemen"] * 100)
        if x["Jumlah_balita_Underweight_suplemen"] != 0 else 0, axis=1
    ).round(2)

    # Perhitungan metrik untuk previous_agg_df
    if not previous_agg_df.empty:
        previous_agg_df["Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)"] = previous_agg_df.apply(
            lambda x: (x["Jumlah_bayi_6-11_bulan_mendapat_Vitamin_A"] / x["Jumlah_bayi_6-11_bulan"] * 100)
            if x["Jumlah_bayi_6-11_bulan"] != 0 else 0, axis=1
        ).round(2)
        previous_agg_df["Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)"] = previous_agg_df.apply(
            lambda x: (x["Jumlah_anak_12-59_bulan_mendapat_Vitamin_A"] / x["Jumlah_anak_12-59_bulan"] * 100)
            if x["Jumlah_anak_12-59_bulan"] != 0 else 0, axis=1
        ).round(2)
        previous_agg_df["Metrik Balita yang Mendapatkan Suplementasi Gizi Mikro (%)"] = previous_agg_df.apply(
            lambda x: (x["Jumlah_balita_yang_mendapatkan_suplementasi_gizi_mikro"] / x["Jumlah_balita_Underweight_suplemen"] * 100)
            if x["Jumlah_balita_Underweight_suplemen"] != 0 else 0, axis=1
        ).round(2)

    # Scorecard
    metrics = {}
    metric_list = [
        "Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)",
        "Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)",
        "Metrik Balita yang Mendapatkan Suplementasi Gizi Mikro (%)",
    ]

    if puskesmas_filter == "All":
        # Hitung total untuk kabupaten
        total_bayi_6_11_vita = current_df["Jumlah_bayi_6-11_bulan_mendapat_Vitamin_A"].sum()
        total_bayi_6_11 = current_df["Jumlah_bayi_6-11_bulan"].sum()
        total_anak_12_59_vita = current_df["Jumlah_anak_12-59_bulan_mendapat_Vitamin_A"].sum()
        total_anak_12_59 = current_df["Jumlah_anak_12-59_bulan"].sum()
        total_balita_suplemen = current_df["Jumlah_balita_yang_mendapatkan_suplementasi_gizi_mikro"].sum()
        total_balita_underweight = current_df["Jumlah_balita_Underweight_suplemen"].sum()

        # Hitung total sebelumnya
        prev_total_bayi_6_11_vita = previous_agg_df["Jumlah_bayi_6-11_bulan_mendapat_Vitamin_A"].sum() if not previous_agg_df.empty else 0
        prev_total_bayi_6_11 = previous_agg_df["Jumlah_bayi_6-11_bulan"].sum() if not previous_agg_df.empty else 0
        prev_total_anak_12_59_vita = previous_agg_df["Jumlah_anak_12-59_bulan_mendapat_Vitamin_A"].sum() if not previous_agg_df.empty else 0
        prev_total_anak_12_59 = previous_agg_df["Jumlah_anak_12-59_bulan"].sum() if not previous_agg_df.empty else 0
        prev_total_balita_suplemen = previous_agg_df["Jumlah_balita_yang_mendapatkan_suplementasi_gizi_mikro"].sum() if not previous_agg_df.empty else 0
        prev_total_balita_underweight = previous_agg_df["Jumlah_balita_Underweight_suplemen"].sum() if not previous_agg_df.empty else 0

        # Hitung persentase untuk scorecard
        current_values = {
            "Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)": (total_bayi_6_11_vita / total_bayi_6_11 * 100) if total_bayi_6_11 != 0 else 0,
            "Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)": (total_anak_12_59_vita / total_anak_12_59 * 100) if total_anak_12_59 != 0 else 0,
            "Metrik Balita yang Mendapatkan Suplementasi Gizi Mikro (%)": (total_balita_suplemen / total_balita_underweight * 100) if total_balita_underweight != 0 else 0,
        }
        previous_values = {
            "Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)": (prev_total_bayi_6_11_vita / prev_total_bayi_6_11 * 100) if prev_total_bayi_6_11 != 0 else None,
            "Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)": (prev_total_anak_12_59_vita / prev_total_anak_12_59 * 100) if prev_total_anak_12_59 != 0 else None,
            "Metrik Balita yang Mendapatkan Suplementasi Gizi Mikro (%)": (prev_total_balita_suplemen / prev_total_balita_underweight * 100) if prev_total_balita_underweight != 0 else None,
        }

        for metric in metric_list:
            current_value = current_values[metric]
            previous_value = previous_values[metric]
            metrics[metric] = calculate_metric(current_value, previous_value)
    else:
        for metric in metric_list:
            current_value = current_df[metric].mean()
            previous_value = previous_agg_df[metric].mean() if not previous_agg_df.empty else None
            metrics[metric] = calculate_metric(current_value, previous_value)

    # Tampilkan scorecard
    st.subheader("📊 Metrik Suplementasi Gizi Mikro")
    cols = st.columns(4)
    for i, metric in enumerate(metric_list):
        value, delta = metrics[metric]
        with cols[i % 4]:
            st.metric(label=metric, value=f"{value:.2f}%", delta=delta)

    # Visualisasi
    st.subheader("📊 Grafik Suplementasi Zat Gizi Mikro")
    visualization_options = metric_list
    
    selected_visualization = st.selectbox(
        "Pilih Metrik untuk Visualisasi",
        visualization_options,
        key="micronutrients_viz_select"
    )
    
    fig = None
    if selected_visualization:
        x_axis = "Puskesmas" if puskesmas_filter == "All" else "Kelurahan"
        title = f"{selected_visualization} per {x_axis}"
        fig = px.bar(
            current_df,
            x=x_axis,
            y=selected_visualization,
            title=title,
            labels={x_axis: x_axis, selected_visualization: selected_visualization},
            color=x_axis,
            text=selected_visualization,
        )
        fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
        fig.update_layout(
            xaxis_title=x_axis,
            yaxis_title=selected_visualization,
            showlegend=False,
            xaxis_tickangle=45,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Grafik Perbandingan Vitamin A Februari vs Agustus (hanya jika ada data untuk kedua bulan)
    comparison_fig = None
    if not filtered_df.empty and "Bulan" in filtered_df.columns:
        # Periksa apakah ada data untuk Februari dan Agustus
        has_feb_data = len(filtered_df[filtered_df["Bulan"] == 2]) > 0
        has_aug_data = len(filtered_df[filtered_df["Bulan"] == 8]) > 0
        if has_feb_data and has_aug_data:
            # Filter data untuk Februari dan Agustus
            comparison_df = filtered_df[filtered_df["Bulan"].isin([2, 8])].copy()
            comparison_df["Bulan"] = comparison_df["Bulan"].map({2: "Februari", 8: "Agustus"})
            
            # Agregasi data per bulan
            comparison_agg = comparison_df.groupby(["Bulan"]).agg({
                "Jumlah_bayi_6-11_bulan_mendapat_Vitamin_A": "sum",
                "Jumlah_bayi_6-11_bulan": "sum",
                "Jumlah_anak_12-59_bulan_mendapat_Vitamin_A": "sum",
                "Jumlah_anak_12-59_bulan": "sum",
            }).reset_index()
            
            # Hitung persentase
            comparison_agg["Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)"] = comparison_agg.apply(
                lambda x: (x["Jumlah_bayi_6-11_bulan_mendapat_Vitamin_A"] / x["Jumlah_bayi_6-11_bulan"] * 100)
                if x["Jumlah_bayi_6-11_bulan"] != 0 else 0, axis=1
            ).round(2)
            comparison_agg["Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)"] = comparison_agg.apply(
                lambda x: (x["Jumlah_anak_12-59_bulan_mendapat_Vitamin_A"] / x["Jumlah_anak_12-59_bulan"] * 100)
                if x["Jumlah_anak_12-59_bulan"] != 0 else 0, axis=1
            ).round(2)
            
            # Buat grafik perbandingan
            comparison_fig = px.bar(
                comparison_agg,
                x="Bulan",
                y=["Jumlah Bayi 6-11 Bulan Mendapat Vitamin A (%)", "Jumlah Anak 12-59 Bulan Mendapat Vitamin A (%)"],
                barmode="group",
                title="Perbandingan Suplementasi Vitamin A: Februari vs Agustus",
                labels={"value": "Persentase (%)", "variable": "Metrik"},
                text_auto=True,
            )
            comparison_fig.update_traces(textposition="outside")
            comparison_fig.update_layout(
                xaxis_title="Bulan",
                yaxis_title="Persentase (%)",
                legend_title="Metrik",
            )
            st.plotly_chart(comparison_fig, use_container_width=True)
        elif has_feb_data and not has_aug_data:
            st.warning("⚠️ Tidak ada data untuk Agustus, grafik perbandingan tidak ditampilkan.")
        else:
            st.warning("⚠️ Tidak ada data untuk Februari, grafik perbandingan tidak ditampilkan.")

    # Tabel rekapitulasi
    st.subheader("📋 Rekapitulasi Suplementasi Zat Gizi Mikro")
    st.dataframe(current_df)

    return metrics, current_df, fig, comparison_fig
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
        # Filter Tahun
        tahun_options = ["All"] + sorted(df['Tahun'].astype(str).unique().tolist() if 'Tahun' in df.columns else [])
        tahun_filter = st.selectbox("📅 Pilih Tahun", options=tahun_options)

        # Filter Jenis Laporan
        jenis_laporan = st.selectbox("📋 Pilih Jenis Laporan", ["Laporan Bulanan", "Laporan Tahunan"])

        # Inisialisasi variabel untuk filter bulan/tribulan
        bulan_filter = "All"
        tribulan_filter = None
        bulan_filter_int = None
        bulan_range = None  # Untuk menyimpan rentang bulan berdasarkan tribulan

        # Filter Bulan atau Tribulan berdasarkan jenis laporan
        if jenis_laporan == "Laporan Bulanan":
            bulan_options = ["All"] + sorted(df['Bulan'].astype(str).unique().tolist() if 'Bulan' in df.columns else [])
            bulan_filter = st.selectbox("📅 Pilih Bulan", options=bulan_options)
        else:  # Laporan Tahunan
            tribulan_options = ["Tribulan I", "Tribulan II", "Tribulan III", "Tribulan IV"]
            tribulan_filter = st.selectbox("📅 Pilih Tribulan", options=tribulan_options)
            # Tentukan rentang bulan berdasarkan tribulan
            if tribulan_filter == "Tribulan I":
                bulan_range = [1, 2, 3]
            elif tribulan_filter == "Tribulan II":
                bulan_range = [4, 5, 6]
            elif tribulan_filter == "Tribulan III":
                bulan_range = [7, 8, 9]
            elif tribulan_filter == "Tribulan IV":
                bulan_range = [10, 11, 12]

        # Filter Puskesmas
        puskesmas_filter = st.selectbox("🏥 Pilih Puskesmas", ["All"] + sorted(desa_df['Puskesmas'].unique()))
        kelurahan_options = ["All"]
        if puskesmas_filter != "All":
            kelurahan_options += sorted(desa_df[desa_df['Puskesmas'] == puskesmas_filter]['Kelurahan'].unique())
        kelurahan_filter = st.selectbox("🏡 Pilih Kelurahan", options=kelurahan_options)

    # Inisialisasi filtered_df dan previous_df
    filtered_df = df.copy()
    previous_df = pd.DataFrame()

    # Filter Tahun
    if tahun_filter != "All":
        try:
            tahun_filter_int = int(tahun_filter)
            filtered_df = filtered_df[filtered_df["Tahun"] == tahun_filter_int] if 'Tahun' in df.columns else filtered_df
        except ValueError:
            st.error("⚠️ Pilihan tahun tidak valid. Menggunakan semua data.")
            filtered_df = df.copy()

    # Filter Bulan atau Tribulan
    if jenis_laporan == "Laporan Bulanan":
        if bulan_filter != "All":
            try:
                bulan_filter_int = int(bulan_filter)
                filtered_df = filtered_df[filtered_df["Bulan"] == bulan_filter_int] if 'Bulan' in df.columns else filtered_df
                # Ambil data bulan sebelumnya (N-1) secara dinamis
                if 'Bulan' in df.columns and bulan_filter_int > 1:  # Hanya ambil previous jika bukan Januari
                    previous_bulan = bulan_filter_int - 1
                    previous_df = df[df["Bulan"] == previous_bulan].copy()
                    if tahun_filter != "All":
                        previous_df = previous_df[previous_df["Tahun"] == tahun_filter_int]
                else:
                    previous_df = pd.DataFrame()  # Jika Januari atau tidak ada data sebelumnya, kosongkan
            except ValueError:
                st.error("⚠️ Pilihan bulan tidak valid. Menggunakan semua data.")
                filtered_df = df.copy()
    else:
        # Filter untuk Laporan Tahunan (agregasi berdasarkan tribulan)
        if bulan_range is not None and 'Bulan' in df.columns:
            # Validasi dinamis berdasarkan bulan yang tersedia di dataset
            available_months = df["Bulan"].unique()
            if not set(bulan_range).intersection(available_months):
                st.warning(f"⚠️ Tidak ada data yang sesuai dengan filter untuk {tribulan_filter}. Dataset hanya tersedia untuk bulan {sorted(available_months)}.")
                filtered_df = pd.DataFrame()  # Kosongkan filtered_df
            else:
                filtered_df = filtered_df[filtered_df["Bulan"].isin(bulan_range)]
            previous_df = pd.DataFrame()

    # Terapkan filter Puskesmas dan Kelurahan
    if puskesmas_filter != "All":
        filtered_df = filtered_df[filtered_df["Puskesmas"] == puskesmas_filter]
        if not previous_df.empty and 'Puskesmas' in previous_df.columns:
            previous_df = previous_df[previous_df["Puskesmas"] == puskesmas_filter]

    if kelurahan_filter != "All":
        filtered_df = filtered_df[filtered_df["Kelurahan"] == kelurahan_filter]
        if not previous_df.empty and 'Kelurahan' in previous_df.columns:
            previous_df = previous_df[previous_df["Kelurahan"] == kelurahan_filter]

    # Jika Laporan Tahunan, lakukan agregasi sum
    if jenis_laporan == "Laporan Tahunan" and not filtered_df.empty:
        group_columns = ["Puskesmas", "Kelurahan"]  # Selalu sertakan 'Kelurahan'
        numeric_columns = [col for col in filtered_df.columns if filtered_df[col].dtype in ['int64', 'float64']]
        if numeric_columns:
            agg_dict = {col: "sum" for col in numeric_columns}  # Gunakan sum alih-alih mean
            filtered_df = filtered_df.groupby(group_columns).agg(agg_dict).reset_index()

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
            metrics, summary_df, fig_bar, fig_line = growth_development_metrics(df, filtered_df, previous_df, desa_df, puskesmas_filter, kelurahan_filter, bulan_filter_int, tahun_filter)

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
                if filter_info['jenis_laporan'] == "Laporan Bulanan":
                    elements.append(Paragraph(f"Filter: Jenis Laporan = {filter_info['jenis_laporan']}, Tahun = {filter_info['tahun']}, Bulan = {filter_info['bulan']}, Puskesmas = {filter_info['puskesmas']}, Kelurahan = {filter_info['kelurahan']}", styles['Normal']))
                else:
                    elements.append(Paragraph(f"Filter: Jenis Laporan = {filter_info['jenis_laporan']}, Tahun = {filter_info['tahun']}, Tribulan = {filter_info['tribulan']}, Puskesmas = {filter_info['puskesmas']}, Kelurahan = {filter_info['kelurahan']}", styles['Normal']))
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
                'tahun': tahun_filter,
                'bulan': bulan_filter,
                'tribulan': tribulan_filter,
                'puskesmas': puskesmas_filter,
                'kelurahan': kelurahan_filter,
                'jenis_laporan': jenis_laporan
            }
            pdf_file = generate_pdf_growth(metrics, summary_df, fig_bar, fig_line, filter_info)
            st.download_button(
                label="📥 Download Laporan PDF",
                data=pdf_file,
                file_name=f"laporan_pertumbuhan_{puskesmas_filter}_{kelurahan_filter}_{time.strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf"
            )

        elif sub_analisis == "🥗 Masalah Gizi":
            # Panggil nutrition_issues_analysis
            metrics, summary_df, fig, prevalence_charts = nutrition_issues_analysis(
                filtered_df, previous_df, desa_df, puskesmas_filter, kelurahan_filter, bulan_filter_int
            )

            # Definisikan filter_info
            filter_info = {
                'tahun': tahun_filter,
                'bulan': bulan_filter,
                'tribulan': tribulan_filter,
                'puskesmas': puskesmas_filter,
                'kelurahan': kelurahan_filter,
                'jenis_laporan': jenis_laporan
            }
            def generate_pdf_nutrition(metrics, summary_df, fig, prevalence_charts, filter_info):
                """Menghasilkan laporan PDF untuk analisis masalah gizi."""
                pdf_buffer = io.BytesIO()
                doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(letter))
                styles = getSampleStyleSheet()
                elements = []

                # Judul Laporan
                elements.append(Paragraph("Laporan Masalah Gizi Balita", styles['Title']))
                elements.append(Spacer(1, 12))

                # Informasi Filter
                if filter_info['jenis_laporan'] == "Laporan Bulanan":
                    elements.append(Paragraph(f"Filter: Jenis Laporan = {filter_info['jenis_laporan']}, Tahun = {filter_info['tahun']}, Bulan = {filter_info['bulan']}, Puskesmas = {filter_info['puskesmas']}, Kelurahan = {filter_info['kelurahan']}", styles['Normal']))
                else:
                    elements.append(Paragraph(f"Filter: Jenis Laporan = {filter_info['jenis_laporan']}, Tahun = {filter_info['tahun']}, Tribulan = {filter_info['tribulan']}, Puskesmas = {filter_info['puskesmas']}, Kelurahan = {filter_info['kelurahan']}", styles['Normal']))
                elements.append(Spacer(1, 12))

                # Tabel Metrik
                metrics_table = [["Metrik", "Persentase Rata-rata (%)", "Status"]]
                for label, (value, delta, status) in metrics.items():
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
                if filter_info['jenis_laporan'] == "Laporan Bulanan":
                    elements.append(Paragraph(f"Filter: Jenis Laporan = {filter_info['jenis_laporan']}, Tahun = {filter_info['tahun']}, Bulan = {filter_info['bulan']}, Puskesmas = {filter_info['puskesmas']}, Kelurahan = {filter_info['kelurahan']}", styles['Normal']))
                else:
                    elements.append(Paragraph(f"Filter: Jenis Laporan = {filter_info['jenis_laporan']}, Tahun = {filter_info['tahun']}, Tribulan = {filter_info['tribulan']}, Puskesmas = {filter_info['puskesmas']}, Kelurahan = {filter_info['kelurahan']}", styles['Normal']))
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
                'tahun': tahun_filter,
                'bulan': bulan_filter,
                'tribulan': tribulan_filter,
                'puskesmas': puskesmas_filter,
                'kelurahan': kelurahan_filter,
                'jenis_laporan': jenis_laporan
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
                if filter_info['jenis_laporan'] == "Laporan Bulanan":
                    elements.append(Paragraph(f"Filter: Jenis Laporan = {filter_info['jenis_laporan']}, Tahun = {filter_info['tahun']}, Bulan = {filter_info['bulan']}, Puskesmas = {filter_info['puskesmas']}, Kelurahan = {filter_info['kelurahan']}", styles['Normal']))
                else:
                    elements.append(Paragraph(f"Filter: Jenis Laporan = {filter_info['jenis_laporan']}, Tahun = {filter_info['tahun']}, Tribulan = {filter_info['tribulan']}, Puskesmas = {filter_info['puskesmas']}, Kelurahan = {filter_info['kelurahan']}", styles['Normal']))
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
                'tahun': tahun_filter,
                'bulan': bulan_filter,
                'tribulan': tribulan_filter,
                'puskesmas': puskesmas_filter,
                'kelurahan': kelurahan_filter,
                'jenis_laporan': jenis_laporan
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
                if filter_info['jenis_laporan'] == "Laporan Bulanan":
                    elements.append(Paragraph(f"Filter: Jenis Laporan = {filter_info['jenis_laporan']}, Tahun = {filter_info['tahun']}, Bulan = {filter_info['bulan']}, Puskesmas = {filter_info['puskesmas']}, Kelurahan = {filter_info['kelurahan']}", styles['Normal']))
                else:
                    elements.append(Paragraph(f"Filter: Jenis Laporan = {filter_info['jenis_laporan']}, Tahun = {filter_info['tahun']}, Tribulan = {filter_info['tribulan']}, Puskesmas = {filter_info['puskesmas']}, Kelurahan = {filter_info['kelurahan']}", styles['Normal']))
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
                'tahun': tahun_filter,
                'bulan': bulan_filter,
                'tribulan': tribulan_filter,
                'puskesmas': puskesmas_filter,
                'kelurahan': kelurahan_filter,
                'jenis_laporan': jenis_laporan
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