import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt

def show_dashboard():
    st.title("🍼 Dashboard Indikator Balita KIA")

    # Ambil data dari database
    conn = sqlite3.connect("rcs_data.db")
    df = pd.read_sql_query("SELECT * FROM data_balita_kia", conn)
    conn.close()

    if not df.empty:
        st.dataframe(df.head())
        st.write("📈 Visualisasi Data Balita KIA")

        # Contoh visualisasi
        fig, ax = plt.subplots()
        df.groupby("wilayah")["jumlah_balita_kia"].sum().plot(kind="bar", ax=ax)
        ax.set_ylabel("Jumlah Balita (KIA)")
        ax.set_title("Distribusi Balita KIA per Wilayah")
        st.pyplot(fig)
    else:
        st.warning("🚫 Data belum tersedia. Silakan upload data terlebih dahulu.")
