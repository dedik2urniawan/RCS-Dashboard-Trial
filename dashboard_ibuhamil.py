import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

def show_dashboard():
    st.title("🤰 Dashboard Indikator Ibu Hamil")

    conn = sqlite3.connect("rcs_data.db")
    try:
        df = pd.read_sql_query("SELECT * FROM data_ibuhamil", conn)
        st.subheader("📄 Data Ibu Hamil")
        st.dataframe(df, use_container_width=True)

        # Visualisasi: Cakupan Pemeriksaan Kehamilan
        if "pemeriksaan_kehamilan" in df.columns:
            fig, ax = plt.subplots()
            df["pemeriksaan_kehamilan"].value_counts().plot(kind="bar", ax=ax, color='orange')
            ax.set_title("Cakupan Pemeriksaan Kehamilan")
            ax.set_ylabel("Jumlah")
            st.pyplot(fig)
        else:
            st.warning("⚠️ Kolom 'pemeriksaan_kehamilan' tidak ditemukan.")
    except Exception as e:
        st.warning("⚠️ Data belum tersedia.")
        st.error(f"Error: {e}")
    finally:
        conn.close()
