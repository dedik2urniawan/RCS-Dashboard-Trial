import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

def show_dashboard():
    st.title("📈 Dashboard EPPGBM")

    conn = sqlite3.connect("rcs_data.db")
    try:
        df = pd.read_sql_query("SELECT * FROM data_eppgbm", conn)
        st.subheader("📄 Data EPPGBM")
        st.dataframe(df, use_container_width=True)

        # Visualisasi: Status Gizi dari EPPGBM
        if "status_gizi" in df.columns:
            fig, ax = plt.subplots()
            df["status_gizi"].value_counts().plot(kind="bar", color='green', ax=ax)
            ax.set_title("Status Gizi Anak Berdasarkan EPPGBM")
            ax.set_ylabel("Jumlah Anak")
            st.pyplot(fig)
        else:
            st.warning("⚠️ Kolom 'status_gizi' tidak ditemukan.")
    except Exception as e:
        st.warning("⚠️ Data belum tersedia.")
        st.error(f"Error: {e}")
    finally:
        conn.close()
