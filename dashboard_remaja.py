import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

def show_dashboard():
    st.title("👧 Dashboard Indikator Remaja Putri")

    conn = sqlite3.connect("rcs_data.db")
    try:
        df = pd.read_sql_query("SELECT * FROM data_remaja", conn)
        st.subheader("📄 Data Remaja Putri")
        st.dataframe(df, use_container_width=True)

        # Visualisasi: Anemia pada Remaja
        if "status_anemia" in df.columns:
            fig, ax = plt.subplots()
            df["status_anemia"].value_counts().plot(kind="pie", autopct='%1.1f%%', ax=ax, startangle=90)
            ax.set_title("Distribusi Anemia pada Remaja Putri")
            ax.set_ylabel("")
            st.pyplot(fig)
        else:
            st.warning("⚠️ Kolom 'status_anemia' tidak ditemukan.")
    except Exception as e:
        st.warning("⚠️ Data belum tersedia.")
        st.error(f"Error: {e}")
    finally:
        conn.close()
