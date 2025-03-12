import pandas as pd
import sqlite3
import streamlit as st

# 📥 Load data dari database
@st.cache_data
def load_data():
    try:
        conn = sqlite3.connect("rcs_data.db")
        df = pd.read_sql_query("SELECT * FROM data_balita_gizi", conn)
        desa_df = pd.read_sql_query("SELECT * FROM dataset_desa", conn)
        conn.close()
        return df, desa_df
    except Exception as e:
        st.error(f"❌ Gagal memuat data: {e}")
        return None, None

# 🎛️ Filter Data
def filter_data(df, desa_df):
    st.sidebar.subheader("🔎 Filter Data")
    bulan_filter = st.sidebar.selectbox("📅 Pilih Bulan", ["All"] + sorted(df['Bulan'].unique().tolist()))
    puskesmas_filter = st.sidebar.selectbox("🏥 Pilih Puskesmas", ["All"] + sorted(desa_df['Puskesmas'].unique()))
    kelurahan_options = ["All"] + (sorted(desa_df[desa_df['Puskesmas'] == puskesmas_filter]['Kelurahan'].unique()) if puskesmas_filter != "All" else [])
    kelurahan_filter = st.sidebar.selectbox("🏘️ Pilih Kelurahan", kelurahan_options)

    filtered_df = df.copy()
    if bulan_filter != "All":
        filtered_df = filtered_df[filtered_df["Bulan"] == int(bulan_filter)]
    if puskesmas_filter != "All":
        filtered_df = filtered_df[filtered_df["Puskesmas"] == puskesmas_filter]
    if kelurahan_filter != "All":
        filtered_df = filtered_df[filtered_df["Kelurahan"] == kelurahan_filter]

    return filtered_df, bulan_filter, puskesmas_filter, kelurahan_filter
