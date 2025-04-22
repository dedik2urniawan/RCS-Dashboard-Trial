import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import json
import auth
import upload_data
import dashboard_balita_gizi
import dashboard_balita_kia
import dashboard_ibuhamil
import dashboard_remaja
import dashboard_eppgbm
import rcs_calc
import pmt_pkmk
import composite_analysis
import rest_api
import time
import os
import datetime

# Konfigurasi halaman
st.set_page_config(page_title="Dashboard RCS", layout="wide")

# Fungsi untuk memuat data dari database
@st.cache_data
def load_data(table_name, db_path="rcs_data.db"):
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ Gagal memuat data: {e}")
        return pd.DataFrame()

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

# Fungsi untuk menghitung skor metrik
def calculate_metrics(df, tahun=None, bulan=None, puskesmas=None):
    filtered_df = df.copy()
    if tahun and tahun != "ALL":
        filtered_df = filtered_df[filtered_df['Tahun'] == int(tahun)]
    if bulan and bulan != "ALL":
        filtered_df = filtered_df[filtered_df['Bulan'] == int(bulan)]
    if puskesmas and puskesmas != "ALL":
        filtered_df = filtered_df[filtered_df['Puskesmas'] == puskesmas]

    agg_data = filtered_df.agg({
        'jumlah_timbang': 'sum',
        'data_sasaran': 'sum',
        'jumlah_ukur': 'sum',
        'jumlah_timbang_ukur': 'sum',
        'Stunting': 'sum',
        'Wasting': 'sum',
        'Underweight': 'sum',
        'Obesitas': 'sum'
    })

    metrics = {
        '% Data Entry Penimbangan': round((agg_data['jumlah_timbang'] / agg_data['data_sasaran'] * 100) if agg_data['data_sasaran'] > 0 else 0, 2),
        'Jumlah Kasus Stunting': int(agg_data['Stunting']),
        'Jumlah Kasus Wasting': int(agg_data['Wasting']),
        'Jumlah Kasus Underweight': int(agg_data['Underweight']),
        'Jumlah Kasus Obesitas': int(agg_data['Obesitas']),
        'Prevalensi Stunting': round((agg_data['Stunting'] / agg_data['jumlah_ukur'] * 100) if agg_data['jumlah_ukur'] > 0 else 0, 2),
        'Prevalensi Wasting': round((agg_data['Wasting'] / agg_data['jumlah_timbang_ukur'] * 100) if agg_data['jumlah_timbang_ukur'] > 0 else 0, 2),
        'Prevalensi Underweight': round((agg_data['Underweight'] / agg_data['jumlah_timbang'] * 100) if agg_data['jumlah_timbang'] > 0 else 0, 2),
        'Prevalensi Obesitas': round((agg_data['Obesitas'] / agg_data['jumlah_timbang_ukur'] * 100) if agg_data['jumlah_timbang_ukur'] > 0 else 0, 2)
    }
    return metrics

# Fungsi untuk membuat peta interaktif
def create_interactive_map(df, geojson_data, tahun, bulan, puskesmas):
    filtered_df = df.copy()
    if tahun and tahun != "ALL":
        filtered_df = filtered_df[filtered_df['Tahun'] == int(tahun)]
    if bulan and bulan != "ALL":
        filtered_df = filtered_df[filtered_df['Bulan'] == int(bulan)]

    agg_df = filtered_df.groupby('Puskesmas').agg({
        'jumlah_timbang': 'sum',
        'data_sasaran': 'sum',
        'jumlah_ukur': 'sum',
        'jumlah_timbang_ukur': 'sum',
        'Stunting': 'sum',
        'Wasting': 'sum',
        'Underweight': 'sum',
        'Obesitas': 'sum'
    }).reset_index()

    agg_df['% Data Entry Penimbangan'] = agg_df.apply(
        lambda x: round((x['jumlah_timbang'] / x['data_sasaran'] * 100) if x['data_sasaran'] > 0 else 0, 2), axis=1)
    agg_df['Prevalensi Stunting'] = agg_df.apply(
        lambda x: round((x['Stunting'] / x['jumlah_ukur'] * 100) if x['jumlah_ukur'] > 0 else 0, 2), axis=1)
    agg_df['Prevalensi Wasting'] = agg_df.apply(
        lambda x: round((x['Wasting'] / x['jumlah_timbang_ukur'] * 100) if x['jumlah_timbang_ukur'] > 0 else 0, 2), axis=1)
    agg_df['Prevalensi Underweight'] = agg_df.apply(
        lambda x: round((x['Underweight'] / x['jumlah_timbang'] * 100) if x['jumlah_timbang'] > 0 else 0, 2), axis=1)
    agg_df['Prevalensi Obesitas'] = agg_df.apply(
        lambda x: round((x['Obesitas'] / x['jumlah_timbang_ukur'] * 100) if x['jumlah_timbang_ukur'] > 0 else 0, 2), axis=1)

    # Normalisasi nama Puskesmas di dataset (strip spasi, ubah ke title case)
    agg_df['Puskesmas'] = agg_df['Puskesmas'].str.strip().str.title()

    # Normalisasi nama di GeoJSON (strip spasi, ubah ke title case)
    for feature in geojson_data['features']:
        feature['properties']['nama_puskesmas'] = feature['properties']['nama_puskesmas'].strip().title()

    # Pengecekan apakah ada data yang cocok antara agg_df dan GeoJSON
    geojson_puskesmas = [f['properties']['nama_puskesmas'] for f in geojson_data['features']]
    matched_puskesmas = set(agg_df['Puskesmas']).intersection(geojson_puskesmas)
    if not matched_puskesmas:
        st.error("⚠️ Tidak ada data Puskesmas yang cocok antara dataset dan GeoJSON. Pastikan nama Puskesmas di dataset sama dengan 'nama_puskesmas' di GeoJSON.")
        st.write("Nama di dataset:", sorted(set(agg_df['Puskesmas'])))
        st.write("Nama di GeoJSON:", sorted(set(geojson_puskesmas)))
        return None

    fig = px.choropleth(
        agg_df,
        geojson=geojson_data,
        locations='Puskesmas',
        featureidkey='properties.nama_puskesmas',
        color='Prevalensi Stunting',
        hover_data=['% Data Entry Penimbangan', 'Prevalensi Stunting', 'Prevalensi Wasting', 'Prevalensi Underweight', 'Prevalensi Obesitas'],
        color_continuous_scale='Reds',
        title='Peta Prevalensi Gizi per Puskesmas'
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin={"r":0,"t":50,"l":0,"b":0})

    if puskesmas and puskesmas != "ALL":
        highlight_df = agg_df[agg_df['Puskesmas'] == puskesmas]
        if not highlight_df.empty:
            fig.add_trace(
                go.Choropleth(
                    geojson=geojson_data,
                    locations=[puskesmas],
                    featureidkey='properties.nama_puskesmas',
                    z=[highlight_df['Prevalensi Stunting'].iloc[0]],
                    colorscale=[[0, 'rgba(0,0,0,0)'], [1, 'yellow']],
                    showscale=False,
                    hoverinfo='none'
                )
            )

    return fig

# Fungsi untuk membuat grafik
def create_graph(df, metric, tahun, bulan, puskesmas):
    filtered_df = df.copy()
    if tahun and tahun != "ALL":
        filtered_df = filtered_df[filtered_df['Tahun'] == int(tahun)]
    if bulan and bulan != "ALL":
        filtered_df = filtered_df[filtered_df['Bulan'] == int(bulan)]
    if puskesmas and puskesmas != "ALL":
        filtered_df = filtered_df[filtered_df['Puskesmas'] == puskesmas]

    agg_df = filtered_df.groupby('Puskesmas').agg({
        'jumlah_timbang': 'sum',
        'data_sasaran': 'sum',
        'jumlah_ukur': 'sum',
        'jumlah_timbang_ukur': 'sum',
        'Stunting': 'sum',
        'Wasting': 'sum',
        'Underweight': 'sum',
        'Obesitas': 'sum'
    }).reset_index()

    agg_df['% Data Entry Penimbangan'] = agg_df.apply(
        lambda x: round((x['jumlah_timbang'] / x['data_sasaran'] * 100) if x['data_sasaran'] > 0 else 0, 2), axis=1)
    agg_df['Prevalensi Stunting'] = agg_df.apply(
        lambda x: round((x['Stunting'] / x['jumlah_ukur'] * 100) if x['jumlah_ukur'] > 0 else 0, 2), axis=1)
    agg_df['Prevalensi Wasting'] = agg_df.apply(
        lambda x: round((x['Wasting'] / x['jumlah_timbang_ukur'] * 100) if x['jumlah_timbang_ukur'] > 0 else 0, 2), axis=1)
    agg_df['Prevalensi Underweight'] = agg_df.apply(
        lambda x: round((x['Underweight'] / x['jumlah_timbang'] * 100) if x['jumlah_timbang'] > 0 else 0, 2), axis=1)
    agg_df['Prevalensi Obesitas'] = agg_df.apply(
        lambda x: round((x['Obesitas'] / x['jumlah_timbang_ukur'] * 100) if x['jumlah_timbang_ukur'] > 0 else 0, 2), axis=1)

    # Urutkan dari tertinggi ke terendah berdasarkan metrik
    agg_df = agg_df.sort_values(by=metric, ascending=False)

    # Target prevalensi
    target_stunting = 14  # Target prevalensi stunting (%)
    target_wasting = 7    # Target prevalensi wasting (%)
    target_underweight = 10  # Target prevalensi underweight (%)
    target_overweight = 5  # Target prevalensi overweight (%) -> untuk Obesitas
    target_data_entry = 90  # Target % Data Entry Penimbangan (%)

    # Pilih target berdasarkan metrik
    target = {
        'Prevalensi Stunting': target_stunting,
        'Prevalensi Wasting': target_wasting,
        'Prevalensi Underweight': target_underweight,
        'Prevalensi Obesitas': target_overweight,
        '% Data Entry Penimbangan': target_data_entry
    }.get(metric)

    fig = px.bar(
        agg_df,
        x='Puskesmas',
        y=metric,
        title=f'{metric} per Puskesmas (Tertinggi ke Terendah)',
        labels={'Puskesmas': 'Puskesmas', metric: metric}
    )

    # Tambahkan garis target jika ada
    if target is not None:
        fig.add_shape(
            type="line",
            x0=-0.5,
            x1=len(agg_df) - 0.5,
            y0=target,
            y1=target,
            line=dict(color="Green", width=2, dash="dash"),
            name=f'Target {metric}'
        )
        fig.add_annotation(
            x=len(agg_df) - 0.5,
            y=target,
            text=f'Target: {target}%',
            showarrow=True,
            arrowhead=1,
            ax=20,
            ay=-30
        )

    fig.update_layout(
        xaxis_title="Puskesmas",
        yaxis_title=metric,
        xaxis_tickangle=45,
        showlegend=False
    )
    return fig

# Fungsi utama aplikasi
def main():
    if "username" not in st.session_state:
        auth.show_login()
    else:
        if "last_active" in st.session_state:
            if time.time() - st.session_state["last_active"] > 1800:
                auth.sign_out()
            else:
                st.session_state["last_active"] = time.time()

        st.sidebar.title(f"👤 Selamat Datang, {st.session_state['username']}")
        st.sidebar.write(f"**Role:** {st.session_state['role']}")

        st.sidebar.header("🔍 Navigasi")
        menu_options = [
            "📊 Dashboard Overview",
            "🍼 Indikator Balita",
            "🤰 Indikator Ibu Hamil",
            "👧 Indikator Remaja Putri",
            "📋 EPPGBM",
            "🧮 RCS Calculator",
            "🍽️ Analisis PMT & PKMK",
            "📈 Analisis Composite",
            "🌐 API Integrasi"
        ]

        if st.session_state["role"] == "admin_dinkes":
            menu_options.append("📂 Upload Data")

        menu = st.sidebar.radio("Pilih Menu:", menu_options, index=0)

        if menu == "📊 Dashboard Overview":
            st.subheader("📊 Dashboard Overview: Latar Belakang dan Tujuan Sistem")

            st.markdown("""
                <div style="background-color: #F9F9F9; padding: 20px; border-radius: 10px; border-left: 6px solid #1976D2; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                    <p style="font-size: 16px; color: #333; line-height: 1.6; font-family: Arial, sans-serif;">
                        Selamat datang di <strong>Dashboard RCS</strong>! Sistem ini dibuat oleh Dinas Kesehatan Kabupaten Malang untuk membantu menganalisis data gizi masyarakat. Dashboard ini memberikan gambaran umum dan analisis mendalam tentang status gizi balita, ibu hamil, dan remaja putri, dengan data dari 39 Puskesmas dan 390 desa di Kabupaten Malang.
                    </p>
                    <p style="font-size: 16px;iono 16px; color: #333; line-height: 1.6; font-family: Arial, sans-serif;">
                        Dashboard RCS menggabungkan data dari <strong>SIGIZI-KESGA</strong> dan laporan Posyandu. Data dikumpulkan setiap Februari dan Agustus dengan verifikasi ketat untuk memastikan akurasi. Sistem ini dilengkapi alat analisis seperti <strong>RCS Calculator</strong> dan <strong>Analisis Composite</strong> untuk mendeteksi tren dan mengevaluasi program gizi.
                    </p>
                    <p style="font-size: 16px; color: #333; line-height: 1.6; font-family: Arial, sans-serif;">
                        Tujuan Dashboard RCS adalah membantu pengambilan keputusan untuk intervensi gizi yang lebih baik. Dengan visualisasi real-time dan akses di ponsel atau komputer, dashboard ini menjadi alat penting untuk memantau dan meningkatkan kesehatan masyarakat di Kabupaten Malang. Pilih menu di sidebar untuk lihat analisis lebih lanjut.
                    </p>
                </div>
            """, unsafe_allow_html=True)

            df = load_data("data_bultim")
            try:
                with open("puskesmas_fix.geojson", "r") as f:
                    geojson_data = json.load(f)
            except Exception as e:
                st.error(f"❌ Gagal memuat GeoJSON: {e}")
                geojson_data = None

            if not df.empty and geojson_data:
                st.sidebar.header("⚙️ Filter Data")
                tahun_options = ["ALL"] + sorted(df['Tahun'].astype(str).unique().tolist())
                bulan_options = ["ALL"] + [str(i) for i in range(1, 13)]
                puskesmas_options = ["ALL"] + sorted(df['Puskesmas'].unique().tolist())

                tahun = st.sidebar.selectbox("📅 Tahun", tahun_options)
                bulan = st.sidebar.selectbox("🗓️ Bulan", bulan_options)
                puskesmas = st.sidebar.selectbox("🏥 Puskesmas", puskesmas_options)

                # Tampilkan waktu terakhir data diperbarui
                last_upload = get_last_upload_time()
                st.markdown(f"📅 **Data terakhir diperbarui:** {last_upload}")

                st.subheader("Progress Capaian Penimbangan EPPGBM")
                st.subheader("Score Card Pertumbuhan")
                metrics = calculate_metrics(df, tahun, bulan, puskesmas)
                cols = st.columns(3)
                for i, (metric, value) in enumerate(metrics.items()):
                    with cols[i % 3]:
                        if metric.startswith('Jumlah Kasus'):
                            st.metric(metric, f"{value} Balita")
                        else:
                            st.metric(metric, f"{value:.2f}%")

                st.subheader("🗺️ Peta Interaktif Prevalensi Gizi")
                map_fig = create_interactive_map(df, geojson_data, tahun, bulan, puskesmas)
                if map_fig:
                    st.plotly_chart(map_fig, use_container_width=True)

                st.subheader("📈 Grafik Prevalensi dan Data Entry")
                metric_options = [
                    '% Data Entry Penimbangan',
                    'Prevalensi Stunting',
                    'Prevalensi Wasting',
                    'Prevalensi Underweight',
                    'Prevalensi Obesitas'
                ]
                selected_metric = st.selectbox("📊 Pilih Metrik untuk Grafik", metric_options)
                graph_fig = create_graph(df, selected_metric, tahun, bulan, puskesmas)
                st.plotly_chart(graph_fig, use_container_width=True)

        elif menu == "🍼 Indikator Balita":
            sub_menu = st.sidebar.radio(
                "➡️ Pilih Sub-Menu Balita",
                ["📉 Dashboard Balita Gizi", "🩺 Dashboard Balita KIA"]
            )
            if sub_menu == "📉 Dashboard Balita Gizi":
                dashboard_balita_gizi.show_dashboard()
            elif sub_menu == "🩺 Dashboard Balita KIA":
                dashboard_balita_kia.show_dashboard()

        elif menu == "🤰 Indikator Ibu Hamil":
            dashboard_ibuhamil.show_dashboard()

        elif menu == "👧 Indikator Remaja Putri":
            dashboard_remaja.show_dashboard()

        elif menu == "📋 EPPGBM":
            if st.session_state["role"] in ["admin_dinkes", "admin_puskesmas"]:
                dashboard_eppgbm.show_dashboard()
            else:
                st.warning("🚫 Anda tidak memiliki akses ke EPPGBM.")

        elif menu == "🧮 RCS Calculator":
            sub_menu_rcs = st.sidebar.selectbox(
                "➡️ Pilih Versi RCS Calculator",
                ["RCS Calc versi 1.0.0", "RCS Calc versi 1.0.1"],
                key="rcs_submenu"
            )
            rcs_calc.show_rcs_calculator(sub_menu_rcs)

        elif menu == "🍽️ Analisis PMT & PKMK":
            pmt_pkmk.show_dashboard()

        elif menu == "📈 Analisis Composite":
            composite_analysis.show_dashboard()

        elif menu == "🌐 API Integrasi":
            rest_api.show_dashboard()

        elif menu == "📂 Upload Data" and st.session_state["role"] == "admin_dinkes":
            upload_data.show_upload_page()

        st.sidebar.markdown("---")
        auth.logout()

if __name__ == "__main__":
    main()