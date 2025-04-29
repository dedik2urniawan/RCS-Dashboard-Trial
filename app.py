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
def calculate_metrics(df, tahun=None, bulan=None, puskesmas=None, kelurahan=None):
    filtered_df = df.copy()
    if tahun and tahun != "ALL":
        filtered_df = filtered_df[filtered_df['Tahun'] == int(tahun)]
    if bulan and bulan != "ALL":
        filtered_df = filtered_df[filtered_df['Bulan'] == int(bulan)]
    if puskesmas and puskesmas != "ALL":
        filtered_df = filtered_df[filtered_df['Puskesmas'] == puskesmas]
    if kelurahan and kelurahan != "ALL":
        filtered_df = filtered_df[filtered_df['Kelurahan'] == kelurahan]

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
        'Jumlah Total Sasaran': int(agg_data['data_sasaran']),
        'Jumlah Balita Di Timbang': int(agg_data['jumlah_timbang']),
        'Jumlah Balita Di Ukur': int(agg_data['jumlah_ukur']),
        'Jumlah Balita Di Timbang & Ukur': int(agg_data['jumlah_timbang_ukur']),
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

# Fungsi untuk membuat peta interaktif (untuk level Puskesmas)
def create_interactive_map_puskesmas(df, geojson_data, tahun, bulan, puskesmas):
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
        title=f'Peta Prevalensi Gizi per Puskesmas ({puskesmas if puskesmas != "ALL" else "Semua Puskesmas"})'
    )

    # Selalu tampilkan peta pada level Puskesmas secara keseluruhan
    fig.update_geos(fitbounds="locations", visible=False)

    fig.update_layout(margin={"r":0,"t":50,"l":0,"b":0})

    # Highlight Puskesmas yang dipilih
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

# Fungsi untuk membuat peta interaktif (untuk level Kelurahan)
def create_interactive_map_kelurahan(df, geojson_data, tahun, bulan, puskesmas, kelurahan):
    filtered_df = df.copy()
    if tahun and tahun != "ALL":
        filtered_df = filtered_df[filtered_df['Tahun'] == int(tahun)]
    if bulan and bulan != "ALL":
        filtered_df = filtered_df[filtered_df['Bulan'] == int(bulan)]
    if puskesmas and puskesmas != "ALL":
        filtered_df = filtered_df[filtered_df['Puskesmas'] == puskesmas]

    agg_df = filtered_df.groupby('Kelurahan').agg({
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

    # Normalisasi nama Kelurahan di dataset (strip spasi, ubah ke title case)
    agg_df['Kelurahan'] = agg_df['Kelurahan'].str.strip().str.title()

    # Normalisasi nama di GeoJSON (strip spasi, ubah ke title case)
    for feature in geojson_data['features']:
        feature['properties']['nama_desa'] = feature['properties']['nama_desa'].strip().title()

    # Pengecekan apakah ada data yang cocok antara agg_df dan GeoJSON
    geojson_kelurahan = [f['properties']['nama_desa'] for f in geojson_data['features']]
    matched_kelurahan = set(agg_df['Kelurahan']).intersection(geojson_kelurahan)
    if not matched_kelurahan:
        st.error("⚠️ Tidak ada data Kelurahan yang cocok antara dataset dan GeoJSON. Pastikan nama Kelurahan di dataset sama dengan 'nama_desa' di GeoJSON.")
        st.write("Nama di dataset:", sorted(set(agg_df['Kelurahan'])))
        st.write("Nama di GeoJSON:", sorted(set(geojson_kelurahan)))
        return None

    fig = px.choropleth(
        agg_df,
        geojson=geojson_data,
        locations='Kelurahan',
        featureidkey='properties.nama_desa',
        color='Prevalensi Stunting',
        hover_data=['% Data Entry Penimbangan', 'Prevalensi Stunting', 'Prevalensi Wasting', 'Prevalensi Underweight', 'Prevalensi Obesitas'],
        color_continuous_scale='Reds',
        title='Peta Prevalensi Gizi per Kelurahan'
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin={"r":0,"t":50,"l":0,"b":0})

    if kelurahan and kelurahan != "ALL":
        highlight_df = agg_df[agg_df['Kelurahan'] == kelurahan]
        if not highlight_df.empty:
            fig.add_trace(
                go.Choropleth(
                    geojson=geojson_data,
                    locations=[kelurahan],
                    featureidkey='properties.nama_desa',
                    z=[highlight_df['Prevalensi Stunting'].iloc[0]],
                    colorscale=[[0, 'rgba(0,0,0,0)'], [1, 'yellow']],
                    showscale=False,
                    hoverinfo='none'
                )
            )

    return fig

# Fungsi untuk membuat grafik dan tabel (untuk level Puskesmas)
def create_graph_and_table_puskesmas(df, metric, tahun, bulan, puskesmas):
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

    # Membuat grafik
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

    # Membuat DataFrame untuk tabel
    table_df = agg_df.rename(columns={
        'data_sasaran': 'Jumlah Sasaran Balita',
        'jumlah_timbang': 'Jumlah Balita Timbang',
        'jumlah_ukur': 'Jumlah Balita Ukur',
        'jumlah_timbang_ukur': 'Jumlah Balita Ukur&Timbang',
        'Stunting': 'Jumlah Stunting',
        'Underweight': 'Jumlah Underweight',
        'Wasting': 'Jumlah Wasting',
        'Obesitas': 'Jumlah Obesitas'
    })[[
        'Puskesmas',
        'Jumlah Sasaran Balita',
        'Jumlah Balita Timbang',
        'Jumlah Balita Ukur',
        'Jumlah Balita Ukur&Timbang',
        'Jumlah Stunting',
        'Jumlah Underweight',
        'Jumlah Wasting',
        'Jumlah Obesitas',
        'Prevalensi Stunting',
        'Prevalensi Underweight',
        'Prevalensi Wasting',
        'Prevalensi Obesitas'
    ]]

    return fig, table_df

# Fungsi untuk membuat grafik dan tabel (untuk level Kelurahan)
def create_graph_and_table_kelurahan(df, metric, tahun, bulan, puskesmas, kelurahan):
    filtered_df = df.copy()
    if tahun and tahun != "ALL":
        filtered_df = filtered_df[filtered_df['Tahun'] == int(tahun)]
    if bulan and bulan != "ALL":
        filtered_df = filtered_df[filtered_df['Bulan'] == int(bulan)]
    if puskesmas and puskesmas != "ALL":
        filtered_df = filtered_df[filtered_df['Puskesmas'] == puskesmas]
    if kelurahan and kelurahan != "ALL":
        filtered_df = filtered_df[filtered_df['Kelurahan'] == kelurahan]

    agg_df = filtered_df.groupby('Kelurahan').agg({
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

    # Membuat grafik
    fig = px.bar(
        agg_df,
        x='Kelurahan',
        y=metric,
        title=f'{metric} per Kelurahan (Tertinggi ke Terendah)',
        labels={'Kelurahan': 'Kelurahan', metric: metric}
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
        xaxis_title="Kelurahan",
        yaxis_title=metric,
        xaxis_tickangle=45,
        showlegend=False
    )

    # Membuat DataFrame untuk tabel
    table_df = agg_df.rename(columns={
        'data_sasaran': 'Jumlah Sasaran Balita',
        'jumlah_timbang': 'Jumlah Balita Timbang',
        'jumlah_ukur': 'Jumlah Balita Ukur',
        'jumlah_timbang_ukur': 'Jumlah Balita Ukur&Timbang',
        'Stunting': 'Jumlah Stunting',
        'Underweight': 'Jumlah Underweight',
        'Wasting': 'Jumlah Wasting',
        'Obesitas': 'Jumlah Obesitas'
    })[[
        'Kelurahan',
        'Jumlah Sasaran Balita',
        'Jumlah Balita Timbang',
        'Jumlah Balita Ukur',
        'Jumlah Balita Ukur&Timbang',
        'Jumlah Stunting',
        'Jumlah Underweight',
        'Jumlah Wasting',
        'Jumlah Obesitas',
        'Prevalensi Stunting',
        'Prevalensi Underweight',
        'Prevalensi Wasting',
        'Prevalensi Obesitas'
    ]]

    return fig, table_df

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
                    <p style="font-size: 16px; color: #333; line-height: 1.6; font-family: Arial, sans-serif;">
                        Dashboard RCS menggabungkan data dari <strong>SIGIZI-KESGA</strong> dan laporan Posyandu. Data dikumpulkan setiap Februari dan Agustus dengan verifikasi ketat untuk memastikan akurasi. Sistem ini dilengkapi alat analisis seperti <strong>RCS Calculator</strong> dan <strong>Analisis Composite</strong> untuk mendeteksi tren dan mengevaluasi program gizi.
                    </p>
                    <p style="font-size: 16px; color: #333; line-height: 1.6; font-family: Arial, sans-serif;">
                        Tujuan Dashboard RCS adalah membantu pengambilan keputusan untuk intervensi gizi yang lebih baik. Dengan visualisasi real-time dan akses di ponsel atau komputer, dashboard ini menjadi alat penting untuk memantau dan meningkatkan kesehatan masyarakat di Kabupaten Malang. Pilih menu di sidebar untuk lihat analisis lebih lanjut.
                    </p>
                </div>
            """, unsafe_allow_html=True)

            # Tambahkan divider elegan
            st.markdown(
                """
                <div style="border-top: 2px solid #1976D2; margin: 20px 0; width: 50%;"></div>
                """,
                unsafe_allow_html=True
            )

            # Tampilkan waktu terakhir data diperbarui
            last_upload = get_last_upload_time()
            st.markdown(f"📅 **Data terakhir diperbarui:** {last_upload}")

            # Memuat data untuk level Puskesmas
            df_puskesmas = load_data("data_bultim")
            try:
                with open("puskesmas_fix.geojson", "r") as f:
                    geojson_puskesmas = json.load(f)
            except Exception as e:
                st.error(f"❌ Gagal memuat GeoJSON Puskesmas: {e}")
                geojson_puskesmas = None

            # Memuat data untuk level Kelurahan
            df_kelurahan = load_data("data_bultim_kelurahan")
            try:
                with open("desa_fix.geojson", "r") as f:
                    geojson_kelurahan = json.load(f)
            except Exception as e:
                st.error(f"❌ Gagal memuat GeoJSON Kelurahan: {e}")
                geojson_kelurahan = None

            if (not df_puskesmas.empty and geojson_puskesmas) or (not df_kelurahan.empty and geojson_kelurahan):
                # Tabs untuk memisahkan analisis
                st.subheader("📂 Pilih Dashboard EPPGBM")
                tab1, tab2 = st.tabs(["Analisis Level Puskesmas", "Analisis Level Kelurahan"])

                # Tab 1: Analisis Level Puskesmas
                with tab1:
                    # Filter untuk level Puskesmas (dipindahkan ke dalam tab)
                    st.subheader("🔎 Filter Data")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        tahun_options_puskesmas = ["ALL"] + sorted(df_puskesmas['Tahun'].astype(str).unique().tolist())
                        tahun_puskesmas = st.selectbox("📅 Tahun", tahun_options_puskesmas, key="tahun_puskesmas_tab1")
                    with col2:
                        bulan_options_puskesmas = ["ALL"] + [str(i) for i in range(1, 13)]
                        bulan_puskesmas = st.selectbox("🗓️ Bulan", bulan_options_puskesmas, key="bulan_puskesmas_tab1")
                    with col3:
                        puskesmas_options = ["ALL"] + sorted(df_puskesmas['Puskesmas'].unique().tolist())
                        puskesmas = st.selectbox("🏥 Puskesmas", puskesmas_options, key="puskesmas_tab1")

                    if not df_puskesmas.empty and geojson_puskesmas:
                        st.subheader("Progress Capaian Penimbangan EPPGBM")
                        st.subheader("Score Card Pertumbuhan")
                        metrics = calculate_metrics(df_puskesmas, tahun_puskesmas, bulan_puskesmas, puskesmas)
                        cols = st.columns(3)
                        for i, (metric, value) in enumerate(metrics.items()):
                            with cols[i % 3]:
                                if metric.startswith('Jumlah Kasus') or metric.startswith('Jumlah Total') or metric.startswith('Jumlah Balita'):
                                    formatted_value = f"{value:,}".replace(",", ".")
                                    st.metric(metric, f"{formatted_value} Balita")
                                else:
                                    st.metric(metric, f"{value:.2f}%")

                        st.subheader("🗺️ Peta Interaktif Prevalensi Gizi")
                        map_fig = create_interactive_map_puskesmas(df_puskesmas, geojson_puskesmas, tahun_puskesmas, bulan_puskesmas, puskesmas)
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
                        selected_metric = st.selectbox("📊 Pilih Metrik untuk Grafik", metric_options, key="metric_puskesmas_tab1")
                        graph_fig, table_df = create_graph_and_table_puskesmas(df_puskesmas, selected_metric, tahun_puskesmas, bulan_puskesmas, puskesmas)
                        st.plotly_chart(graph_fig, use_container_width=True)

                        st.subheader("📋 Tabel Detail Data per Puskesmas")
                        def highlight_outliers(row):
                            styles = [''] * len(row)
                            targets = {
                                'Prevalensi Stunting': 14,
                                'Prevalensi Wasting': 7,
                                'Prevalensi Underweight': 10,
                                'Prevalensi Obesitas': 5
                            }
                            for col in targets:
                                if col in row.index and row[col] > targets[col]:
                                    idx = row.index.get_loc(col)
                                    styles[idx] = 'background-color: #FF6666; color: white;'
                            return styles

                        styled_df = table_df.style.apply(highlight_outliers, axis=1).format({
                            'Prevalensi Stunting': "{:.2f}%",
                            'Prevalensi Wasting': "{:.2f}%",
                            'Prevalensi Underweight': "{:.2f}%",
                            'Prevalensi Obesitas': "{:.2f}%"
                        })
                        st.dataframe(styled_df, use_container_width=True)
                    else:
                        st.warning("⚠️ Data untuk analisis level Puskesmas tidak tersedia.")

                # Tab 2: Analisis Level Kelurahan
                with tab2:
                    # Filter untuk level Kelurahan (dipindahkan ke dalam tab)
                    st.subheader("Filter Data Level Kelurahan")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        tahun_options_kelurahan = ["ALL"] + sorted(df_kelurahan['Tahun'].astype(str).unique().tolist())
                        tahun_kelurahan = st.selectbox("📅 Tahun", tahun_options_kelurahan, key="tahun_kelurahan_tab2")
                    with col2:
                        bulan_options_kelurahan = ["ALL"] + [str(i) for i in range(1, 13)]
                        bulan_kelurahan = st.selectbox("🗓️ Bulan", bulan_options_kelurahan, key="bulan_kelurahan_tab2")
                    with col3:
                        puskesmas_options_kelurahan = ["ALL"] + sorted(df_kelurahan['Puskesmas'].unique().tolist())
                        puskesmas_kelurahan = st.selectbox("🏥 Puskesmas", puskesmas_options_kelurahan, key="puskesmas_kelurahan_tab2")
                    with col4:
                        # Filter Kelurahan berdasarkan Puskesmas yang dipilih
                        filtered_kelurahan = df_kelurahan
                        if puskesmas_kelurahan != "ALL":
                            filtered_kelurahan = filtered_kelurahan[filtered_kelurahan['Puskesmas'] == puskesmas_kelurahan]
                        kelurahan_options_filtered = ["ALL"] + sorted(filtered_kelurahan['Kelurahan'].unique().tolist())
                        kelurahan = st.selectbox("🏘️ Kelurahan", kelurahan_options_filtered, key="kelurahan_tab2")

                    if not df_kelurahan.empty and geojson_kelurahan:
                        st.subheader("Progress Capaian Penimbangan EPPGBM")
                        st.subheader("Score Card Pertumbuhan")
                        metrics = calculate_metrics(df_kelurahan, tahun_kelurahan, bulan_kelurahan, puskesmas_kelurahan, kelurahan)
                        cols = st.columns(3)
                        for i, (metric, value) in enumerate(metrics.items()):
                            with cols[i % 3]:
                                if metric.startswith('Jumlah Kasus') or metric.startswith('Jumlah Total') or metric.startswith('Jumlah Balita'):
                                    formatted_value = f"{value:,}".replace(",", ".")
                                    st.metric(metric, f"{formatted_value} Balita")
                                else:
                                    st.metric(metric, f"{value:.2f}%")

                        st.subheader("🗺️ Peta Interaktif Prevalensi Gizi")
                        map_fig = create_interactive_map_kelurahan(df_kelurahan, geojson_kelurahan, tahun_kelurahan, bulan_kelurahan, puskesmas_kelurahan, kelurahan)
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
                        selected_metric = st.selectbox("📊 Pilih Metrik untuk Grafik", metric_options, key="metric_kelurahan_tab2")
                        graph_fig, table_df = create_graph_and_table_kelurahan(df_kelurahan, selected_metric, tahun_kelurahan, bulan_kelurahan, puskesmas_kelurahan, kelurahan)
                        st.plotly_chart(graph_fig, use_container_width=True)

                        st.subheader("📋 Tabel Detail Data per Kelurahan")
                        def highlight_outliers(row):
                            styles = [''] * len(row)
                            targets = {
                                'Prevalensi Stunting': 14,
                                'Prevalensi Wasting': 7,
                                'Prevalensi Underweight': 10,
                                'Prevalensi Obesitas': 5
                            }
                            for col in targets:
                                if col in row.index and row[col] > targets[col]:
                                    idx = row.index.get_loc(col)
                                    styles[idx] = 'background-color: #FF6666; color: white;'
                            return styles

                        styled_df = table_df.style.apply(highlight_outliers, axis=1).format({
                            'Prevalensi Stunting': "{:.2f}%",
                            'Prevalensi Wasting': "{:.2f}%",
                            'Prevalensi Underweight': "{:.2f}%",
                            'Prevalensi Obesitas': "{:.2f}%"
                        })
                        st.dataframe(styled_df, use_container_width=True)
                    else:
                        st.warning("⚠️ Data untuk analisis level Kelurahan tidak tersedia.")

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