import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import xlsxwriter
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import numpy as np
from scipy.stats import norm

# Fungsi untuk menghitung prevalensi stunting
def calculate_prevalensi_stunting(df_grouped):
    total_balita = df_grouped.shape[0]
    if total_balita == 0:
        return 0
    stunting_count = df_grouped[df_grouped["ZS_TBU"] < -2].shape[0]
    return (stunting_count / total_balita) * 100

# Fungsi untuk Analisis Differensiasi Prevalensi Stunting
def show_analisis_differensiasi_stunting(df):
    st.subheader("📊 Analisis Differensiasi Prevalensi Stunting")
    
    # Tambahkan informasi dengan pendekatan data science, akademik, dan formal
    with st.expander("📜 Definisi dan Insight Analisis Differensiasi Prevalensi Stunting", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Insight Analisis Differensiasi Prevalensi Stunting

            Analisis ini bertujuan untuk **mengukur perbedaan (differensiasi) prevalensi stunting** antara dua periode pengukuran (periode awal dan periode akhir) pada level **Puskesmas** dan **Kelurahan**, dengan pendekatan data science untuk mendukung pengambilan keputusan berbasis data dalam program kesehatan masyarakat.

            #### Definisi Operasional
            - **Prevalensi Stunting**: Persentase balita dengan Z-Score Tinggi Badan menurut Umur (ZS_TBU) < -2, dihitung sebagai (jumlah balita stunting / total balita) × 100%.
            - **Periode Awal dan Akhir**: Dua periode pengukuran yang dipilih oleh pengguna (format: bulan_tahun, misalnya `agustus_2024` dan `februari_2025`).
            - **Selisih Prevalensi**: Perbedaan prevalensi stunting antara periode akhir dan awal (Prevalensi Akhir - Prevalensi Awal).
            - **Klasifikasi Data**:
              - **Valid Data**: Jika selisih prevalensi ≤ 2%, data dianggap valid, ditandai dengan warna biru.
              - **Unplausible Data**: Jika selisih prevalensi > 2%, data dianggap *unplausible* (tidak realistis), ditandai dengan warna merah.
            - **Level Analisis**:
              - **Puskesmas**: Analisis dilakukan untuk 39 Puskesmas di Kabupaten Malang.
              - **Kelurahan**: Analisis dilakukan untuk 390 Kelurahan, dikelompokkan berdasarkan Puskesmas.

            #### Metode Analisis
            1. **Pengumpulan Data**: Data diambil dari kolom `ZS_TBU` untuk menghitung prevalensi stunting per Puskesmas dan Kelurahan pada periode yang dipilih.
            2. **Perhitungan Prevalensi**: Prevalensi stunting dihitung untuk setiap periode menggunakan rumus:  
               Prevalensi (%) = (Jumlah balita dengan ZS_TBU < -2 / Total balita) × 100.
            3. **Perhitungan Selisih**: Selisih prevalensi dihitung sebagai Prevalensi Akhir - Prevalensi Awal.
            4. **Visualisasi**:
               - **Scatterplot**: Menampilkan prevalensi awal (sumbu x) vs prevalensi akhir (sumbu y), dengan warna titik berdasarkan selisih prevalensi (biru untuk ≤ 2%, merah untuk > 2%).
               - **Tabel Heatmap**: Menampilkan selisih prevalensi dengan gradasi warna (biru untuk selisih rendah, merah untuk selisih tinggi).

            #### Insight Analisis
            - **Valid Data (Selisih ≤ 2%)**: Perubahan prevalensi yang kecil menunjukkan stabilitas status gizi di wilayah tersebut, tetapi juga dapat mengindikasikan kurangnya efektivitas intervensi jika prevalensi tetap tinggi.
            - **Unplausible Data (Selisih > 2%)**: Perubahan prevalensi yang signifikan dapat mengindikasikan adanya masalah dalam pengukuran (misalnya, inkonsistensi data atau bias pengukuran) atau adanya perubahan nyata dalam status gizi (misalnya, akibat intervensi besar atau bencana). Data ini perlu diverifikasi lebih lanjut untuk memastikan keakuratannya.
            - Analisis ini membantu mengidentifikasi wilayah dengan perubahan prevalensi stunting yang tidak realistis, sehingga dapat dilakukan investigasi lebih lanjut terhadap kualitas data atau efektivitas program gizi di wilayah tersebut.

            </div>
        """, unsafe_allow_html=True)

    # Validasi kolom yang diperlukan
    required_columns = ["periode", "puskesmas", "kelurahan", "ZS_TBU"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"Kolom berikut tidak ditemukan di dataset: {', '.join(missing_columns)}. Silakan periksa data.")
        return

    # Filter periode awal dan akhir
    st.sidebar.subheader("🔍 Filter Periode Analisis Differensiasi")
    periode_options = sorted(df["periode"].dropna().unique().tolist())
    if len(periode_options) < 2:
        st.sidebar.warning("⚠️ Dataset hanya memiliki satu periode. Analisis ini memerlukan minimal dua periode.")
        return

    periode_awal = st.sidebar.selectbox("Pilih Periode Awal", periode_options, index=0, key="periode_awal_diff")
    periode_akhir_options = [p for p in periode_options if p > periode_awal]
    if not periode_akhir_options:
        st.sidebar.warning("⚠️ Tidak ada periode setelah periode awal yang dipilih. Silakan pilih periode awal yang lebih awal.")
        return
    periode_akhir = st.sidebar.selectbox("Pilih Periode Akhir", periode_akhir_options, index=len(periode_akhir_options)-1, key="periode_akhir_diff")

    # Filter dataset berdasarkan periode
    df_filtered = df[df["periode"].isin([periode_awal, periode_akhir])].copy()
    if df_filtered.empty:
        st.warning("⚠️ Tidak ada data yang sesuai dengan filter periode yang dipilih.")
        return

    # Tab untuk memilih level analisis
    tabs = st.tabs(["Level Puskesmas", "Level Kelurahan"])

    # Tab 1: Analisis Differensiasi Prevalensi Stunting Level Puskesmas
    with tabs[0]:
        st.write("### Analisis Differensiasi Prevalensi Stunting Level Puskesmas")

        # Hitung prevalensi stunting per Puskesmas untuk periode awal dan akhir
        df_awal = df_filtered[df_filtered["periode"] == periode_awal]
        df_akhir = df_filtered[df_filtered["periode"] == periode_akhir]

        # Pastikan semua Puskesmas yang ada di dataset dimasukkan
        all_puskesmas = sorted(df["puskesmas"].unique())
        prevalensi_awal = df_awal.groupby("puskesmas").apply(calculate_prevalensi_stunting).reset_index(name="Prevalensi_Awal")
        prevalensi_akhir = df_akhir.groupby("puskesmas").apply(calculate_prevalensi_stunting).reset_index(name="Prevalensi_Akhir")

        # Buat DataFrame dengan semua Puskesmas
        prevalensi_df = pd.DataFrame({"puskesmas": all_puskesmas})
        prevalensi_df = prevalensi_df.merge(prevalensi_awal, on="puskesmas", how="left").merge(prevalensi_akhir, on="puskesmas", how="left").fillna(0)
        prevalensi_df["Selisih"] = prevalensi_df["Prevalensi_Akhir"] - prevalensi_df["Prevalensi_Awal"]
        prevalensi_df["Selisih_Abs"] = prevalensi_df["Selisih"].abs()  # Untuk gradasi warna

        # Klasifikasi valid/unplausible
        prevalensi_df["Status"] = prevalensi_df["Selisih_Abs"].apply(lambda x: "Valid" if x <= 2 else "Unplausible")
        prevalensi_df["Color"] = prevalensi_df["Selisih_Abs"].apply(lambda x: "#1E90FF" if x <= 2 else "#FF0000")

        # Visualisasi 1: Scatterplot
        st.write("#### Scatterplot Prevalensi Stunting per Puskesmas")
        fig_scatter = px.scatter(
            prevalensi_df,
            x="Prevalensi_Awal",
            y="Prevalensi_Akhir",
            color="Selisih_Abs",
            color_continuous_scale=["#1E90FF", "#FF0000"],
            size_max=15,
            text="puskesmas",
            labels={"Prevalensi_Awal": f"Prevalensi Stunting {periode_awal} (%)", "Prevalensi_Akhir": f"Prevalensi Stunting {periode_akhir} (%)"},
            title="Perbandingan Prevalensi Stunting per Puskesmas",
            range_x=[-5, 105],
            range_y=[-5, 105],
        )
        fig_scatter.update_traces(
            textposition="top center",
            marker=dict(size=10, opacity=0.8),
            hovertemplate="Puskesmas: %{text}<br>Prevalensi Awal: %{x:.2f}%<br>Prevalensi Akhir: %{y:.2f}%<br>Selisih: %{customdata:.2f}%",
            customdata=prevalensi_df["Selisih"]
        )
        fig_scatter.update_layout(
            coloraxis_colorbar_title="% Selisih",
            coloraxis_colorbar=dict(
                tickvals=[0, 2, 10],
                ticktext=["0.0", "2.0", "10.0"]
            ),
            height=600,
            showlegend=False,
            template="plotly_white"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

        # Visualisasi 2: Tabel Heatmap
        st.write("#### Tabel Heatmap Prevalensi Stunting per Puskesmas")
        fig_heatmap = go.Figure(data=go.Heatmap(
            z=prevalensi_df["Selisih_Abs"],
            x=["% Selisih"],
            y=prevalensi_df["puskesmas"],
            colorscale=["#1E90FF", "#FF0000"],
            zmin=0,
            zmax=10,
            text=prevalensi_df["Selisih"].apply(lambda x: f"{x:.2f}%"),
            texttemplate="%{text}",
            hoverongaps=False
        ))
        fig_heatmap.update_layout(
            title="Heatmap Selisih Prevalensi Stunting per Puskesmas",
            xaxis_title="",
            yaxis_title="Puskesmas",
            height=max(400, len(prevalensi_df) * 30),  # Sesuaikan tinggi berdasarkan jumlah Puskesmas
            template="plotly_white"
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)

        # Tabel setelah heatmap
        st.write("#### Tabel Prevalensi Stunting per Puskesmas")
        heatmap_data = prevalensi_df[["puskesmas", "Prevalensi_Awal", "Prevalensi_Akhir", "Selisih"]].copy()
        heatmap_data.columns = ["Puskesmas", "Prevalensi Awal (%)", "Prevalensi Akhir (%)", "% Selisih"]
        heatmap_data["% Selisih"] = heatmap_data["% Selisih"].apply(lambda x: f"{x:.2f}%")
        st.dataframe(heatmap_data, use_container_width=True)

    # Tab 2: Analisis Differensiasi Prevalensi Stunting Level Kelurahan
    with tabs[1]:
        st.write("### Analisis Differensiasi Prevalensi Stunting Level Kelurahan")

        # Hitung prevalensi stunting per Kelurahan untuk periode awal dan akhir
        df_awal = df_filtered[df_filtered["periode"] == periode_awal]
        df_akhir = df_filtered[df_filtered["periode"] == periode_akhir]

        prevalensi_awal_kel = df_awal.groupby(["puskesmas", "kelurahan"]).apply(calculate_prevalensi_stunting).reset_index(name="Prevalensi_Awal")
        prevalensi_akhir_kel = df_akhir.groupby(["puskesmas", "kelurahan"]).apply(calculate_prevalensi_stunting).reset_index(name="Prevalensi_Akhir")

        # Pastikan semua kombinasi Puskesmas dan Kelurahan dimasukkan
        all_combinations = df[["puskesmas", "kelurahan"]].drop_duplicates().sort_values(by=["puskesmas", "kelurahan"])
        prevalensi_df_kel = all_combinations.merge(prevalensi_awal_kel, on=["puskesmas", "kelurahan"], how="left").merge(prevalensi_akhir_kel, on=["puskesmas", "kelurahan"], how="left").fillna(0)
        prevalensi_df_kel["Selisih"] = prevalensi_df_kel["Prevalensi_Akhir"] - prevalensi_df_kel["Prevalensi_Awal"]
        prevalensi_df_kel["Selisih_Abs"] = prevalensi_df_kel["Selisih"].abs()

        # Klasifikasi valid/unplausible
        prevalensi_df_kel["Status"] = prevalensi_df_kel["Selisih_Abs"].apply(lambda x: "Valid" if x <= 2 else "Unplausible")
        prevalensi_df_kel["Color"] = prevalensi_df_kel["Selisih_Abs"].apply(lambda x: "#1E90FF" if x <= 2 else "#FF0000")

        # Visualisasi 1: Scatterplot
        st.write("#### Scatterplot Prevalensi Stunting per Kelurahan")
        fig_scatter_kel = px.scatter(
            prevalensi_df_kel,
            x="Prevalensi_Awal",
            y="Prevalensi_Akhir",
            color="Selisih_Abs",
            color_continuous_scale=["#1E90FF", "#FF0000"],
            size_max=10,
            text="kelurahan",
            labels={"Prevalensi_Awal": f"Prevalensi Stunting {periode_awal} (%)", "Prevalensi_Akhir": f"Prevalensi Stunting {periode_akhir} (%)"},
            title="Perbandingan Prevalensi Stunting per Kelurahan",
            range_x=[-5, 105],
            range_y=[-5, 105],
        )
        fig_scatter_kel.update_traces(
            textposition="top center",
            marker=dict(size=8, opacity=0.7),
            hovertemplate="Kelurahan: %{text}<br>Prevalensi Awal: %{x:.2f}%<br>Prevalensi Akhir: %{y:.2f}%<br>Selisih: %{customdata:.2f}%",
            customdata=prevalensi_df_kel["Selisih"]
        )
        fig_scatter_kel.update_layout(
            coloraxis_colorbar_title="% Selisih",
            coloraxis_colorbar=dict(
                tickvals=[0, 2, 10],
                ticktext=["0.0", "2.0", "10.0"]
            ),
            height=600,
            showlegend=False,
            template="plotly_white"
        )
        st.plotly_chart(fig_scatter_kel, use_container_width=True)

        # Visualisasi 2: Tabel Heatmap (Mirip SC, dengan Puskesmas di sumbu Y dan Kelurahan di sumbu X)
        st.write("#### Tabel Heatmap Prevalensi Stunting per Kelurahan")

        # Pivot data untuk heatmap
        # Membuat pivot table dengan Puskesmas sebagai baris dan Kelurahan sebagai kolom
        pivot_df = prevalensi_df_kel.pivot(index="puskesmas", columns="kelurahan", values="Selisih_Abs").fillna(0)
        pivot_text = prevalensi_df_kel.pivot(index="puskesmas", columns="kelurahan", values="Selisih").apply(lambda x: x.map(lambda v: f"{v:.2f}%")).fillna("0.00%")

        # Buat heatmap
        fig_heatmap_kel = go.Figure(data=go.Heatmap(
            z=pivot_df.values,
            x=pivot_df.columns,
            y=pivot_df.index,
            colorscale=["#D3D3D3", "#FF0000"],
            zmin=0,
            zmax=10,
            text=pivot_text.values,
            texttemplate="%{text}",
            hoverongaps=False,
            hovertemplate="Puskesmas: %{y}<br>Kelurahan: %{x}<br>% Selisih: %{text}<br>Selisih Absolut: %{z:.2f}%"
        ))

        # Update layout untuk heatmap
        fig_heatmap_kel.update_layout(
            title="Heatmap Selisih Prevalensi Stunting per Kelurahan",
            xaxis_title="Kelurahan",
            yaxis_title="Puskesmas",
            height=max(400, len(pivot_df) * 30),  # Sesuaikan tinggi berdasarkan jumlah Puskesmas
            width=max(600, len(pivot_df.columns) * 20),  # Sesuaikan lebar berdasarkan jumlah Kelurahan
            template="plotly_white",
            xaxis=dict(tickangle=45),  # Putar label Kelurahan agar lebih mudah dibaca
        )

        # Tambahkan garis pemisah antar Puskesmas
        for i in range(len(pivot_df.index) - 1):
            fig_heatmap_kel.add_shape(
                type="line",
                x0=-0.5,
                x1=len(pivot_df.columns) - 0.5,
                y0=i + 0.5,
                y1=i + 0.5,
                line=dict(color="black", width=1),
            )

        st.plotly_chart(fig_heatmap_kel, use_container_width=True)

        # Tabel setelah heatmap
        st.write("#### Tabel Prevalensi Stunting per Kelurahan")
        heatmap_data_kel = prevalensi_df_kel[["puskesmas", "kelurahan", "Prevalensi_Awal", "Prevalensi_Akhir", "Selisih"]].copy()
        heatmap_data_kel.columns = ["Puskesmas", "Kelurahan", "Prevalensi Awal (%)", "Prevalensi Akhir (%)", "% Selisih"]
        heatmap_data_kel["% Selisih"] = heatmap_data_kel["% Selisih"].apply(lambda x: f"{x:.2f}%")
        st.dataframe(heatmap_data_kel, use_container_width=True)

# Modifikasi fungsi show_info_data_eppgbm untuk menambahkan submenu
def show_info_data_eppgbm(df):
    # Tambahkan radio button untuk memilih submenu
    st.sidebar.subheader("🔍 Pilih Submenu Analisis")
    submenu_options = ["Informasi Data EPPGBM", "Analisis Differensiasi Prevalensi Stunting"]
    selected_submenu = st.sidebar.radio("Pilih Submenu", submenu_options, key="submenu_info_data")

    if selected_submenu == "Informasi Data EPPGBM":
        st.subheader("📋 Informasi Data EPPGBM: Latar Belakang dan Konteks Analisis")
        st.markdown("""
            <div style="background-color: #F9F9F9; padding: 20px; border-radius: 10px; border-left: 6px solid #1976D2; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                <p style="font-size: 16px; color: #333; line-height: 1.6; font-family: Arial, sans-serif;">
                    Analisis EPPGBM (Elektronik Pencatatan dan Pelaporan Gizi Berbasis Masyarakat) dalam dashboard ini disusun berdasarkan data yang diperoleh dari aplikasi 
                    <a href="https://sigizikesga.kemkes.go.id/login_sisfo/" target="_blank" style="color: #1976D2; text-decoration: underline; font-weight: bold;">SIGIZI-KESGA</a>. 
                    Sumber data utama berasal dari upaya pengumpulan yang dilakukan oleh para kader kesehatan di 390 desa, yang tersebar di bawah koordinasi 39 Puskesmas di wilayah Kabupaten Malang. 
                    Proses pengumpulan ini dilakukan di bawah pengawasan Dinas Kesehatan Kabupaten Malang, memastikan representasi data yang luas dan relevan.
                </p>
                <p style="font-size: 16px; color: #333; line-height: 1.6; font-family: Arial, sans-serif;">
                    Data yang digunakan telah melalui proses verifikasi bertahap yang ketat, melibatkan tim Penanggung Jawab (PJ) Kesehatan Desa hingga tingkat Puskesmas. 
                    Platform SIGIZI-KESGA telah menerapkan mekanisme perbaikan data secara sistemik, termasuk deteksi outlier melalui analisis otomatis, guna menjamin akurasi dan keandalan informasi yang disajikan. 
                    Fitur analisis ini saat ini difokuskan pada data pengukuran dari dua periode utama, yaitu bulan Februari dan Agustus, yang mencerminkan data aktual hasil penimbangan serta proyeksi target 
                    Indikator Kinerja Utama (IKU) Pemerintah Kabupaten Malang.
                </p>
                <p style="font-size: 16px; color: #333; line-height: 1.6; font-family: Arial, sans-serif;">
                    Analisis EPPGBM dirancang untuk memberikan wawasan mendalam mengenai pertumbuhan anak, dengan cakupan yang mencakup empat aspek utama:  
                    1. <strong style="color: #1976D2;">Distribusi Data EPPGBM</strong>: Menyajikan gambaran distribusi data pertumbuhan secara keseluruhan.  
                    2. <strong style="color: #1976D2;">Distribusi Z-Score Analysis</strong>: Menganalisis distribusi nilai Z-score untuk menilai status gizi.  
                    3. <strong style="color: #1976D2;">Analisis Z-Score Flag</strong>: Mengidentifikasi data yang memerlukan perhatian khusus berdasarkan flag Z-score.  
                    4. <strong style="color: #1976D2;">Analisis Trend Pertumbuhan EPPGBM</strong>: Melacak perkembangan pertumbuhan anak secara longitudinal.  
                    Dengan pendekatan ini, dashboard EPPGBM bertujuan menjadi alat strategis bagi pengambil keputusan di tingkat lokal untuk memantau, mengevaluasi, dan meningkatkan program kesehatan masyarakat.
                </p>
            </div>
        """, unsafe_allow_html=True)
        st.subheader("📄 Data EPPGBM")
        st.dataframe(df, use_container_width=True)

        # Pastikan kolom Z-Score yang diperlukan ada
        required_zscore_columns = ["ZS_BBU", "ZS_TBU", "ZS_BBTB"]
        missing_zscore_columns = [col for col in required_zscore_columns if col not in df.columns]
        if missing_zscore_columns:
            st.error(f"Kolom Z-Score berikut tidak ditemukan di dataset: {', '.join(missing_zscore_columns)}. Silakan periksa data.")
            return

        # Pastikan kolom BB_Lahir dan TB_Lahir ada
        required_columns = ["BB_Lahir", "TB_Lahir"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"Kolom berikut tidak ditemukan di dataset: {', '.join(missing_columns)}. Silakan periksa data.")
            return

        # Tambahkan filter untuk periode, puskesmas, dan kelurahan
        st.sidebar.subheader("🔍 Filter Data Prevalensi")
        if "periode" in df.columns:
            periode_options = ["All"] + sorted(df["periode"].dropna().unique().tolist())
            if not periode_options or len(periode_options) <= 1:
                st.sidebar.warning("⚠️ Kolom 'periode' tidak memiliki data unik yang valid selain 'All'. Periksa dataset.")
        else:
            periode_options = ["All"]
            st.sidebar.warning("⚠️ Kolom 'periode' tidak ditemukan di dataset. Filter default ke 'All'.")
        selected_periode = st.sidebar.selectbox("Pilih Periode Pengukuran", periode_options, key="periode_prevalensi")

        puskesmas_options = ["All"] + sorted(df["puskesmas"].unique().tolist()) if "puskesmas" in df.columns else ["All"]
        selected_puskesmas = st.sidebar.selectbox("Pilih Puskesmas", puskesmas_options, key="puskesmas_prevalensi")

        kelurahan_options = ["All"] + sorted(df["kelurahan"].unique().tolist()) if "kelurahan" in df.columns else ["All"]
        selected_kelurahan = st.sidebar.selectbox("Pilih Kelurahan", kelurahan_options, key="kelurahan_prevalensi")

        # Filter dataset berdasarkan pilihan
        filtered_df = df.copy()
        if selected_periode != "All":
            filtered_df = filtered_df[filtered_df["periode"] == selected_periode]
        if selected_puskesmas != "All":
            filtered_df = filtered_df[filtered_df["puskesmas"] == selected_puskesmas]
        if selected_kelurahan != "All":
            filtered_df = filtered_df[filtered_df["kelurahan"] == selected_kelurahan]

        if filtered_df.empty:
            st.warning("⚠️ Tidak ada data yang sesuai dengan filter yang dipilih. Silakan sesuaikan filter.")
            return

        # Data Cleaning untuk BB_Lahir
        def clean_bb_lahir(value):
            try:
                value = float(value)
                if value < 1:
                    return 0
                elif value > 5:
                    if len(str(int(value))) > 3:
                        value = value / 1000
                        value = round(value, 1)
                        return min(value, 5)
                    return 5
                return value
            except:
                return 0

        # Data Cleaning untuk TB_Lahir
        def clean_tb_lahir(value):
            try:
                value = float(value)
                if value < 44:
                    return 44
                elif value > 55.6:
                    return 55.6
                return value
            except:
                return 44

        # Terapkan cleaning
        filtered_df["BB_Lahir"] = filtered_df["BB_Lahir"].apply(clean_bb_lahir)
        filtered_df["TB_Lahir"] = filtered_df["TB_Lahir"].apply(clean_tb_lahir)

        # Hitung prevalensi untuk Stunting, Wasting, Underweight, dan Overweight
        def calculate_prevalensi(df_grouped):
            total_balita = df_grouped.shape[0]
            if total_balita == 0:
                return pd.Series({
                    "Prevalensi_Stunting": 0,
                    "Prevalensi_Wasting": 0,
                    "Prevalensi_Underweight": 0,
                    "Prevalensi_Overweight": 0
                })
            stunting_count = df_grouped[df_grouped["ZS_TBU"] < -2].shape[0]
            wasting_count = df_grouped[df_grouped["ZS_BBTB"] < -2].shape[0]
            underweight_count = df_grouped[df_grouped["ZS_BBU"] < -2].shape[0]
            overweight_count = df_grouped[df_grouped["ZS_BBU"] > 2].shape[0]
            return pd.Series({
                "Prevalensi_Stunting": (stunting_count / total_balita) * 100,
                "Prevalensi_Wasting": (wasting_count / total_balita) * 100,
                "Prevalensi_Underweight": (underweight_count / total_balita) * 100,
                "Prevalensi_Overweight": (overweight_count / total_balita) * 100
            })

        # Grafik Trend Prevalensi Masalah Gizi
        st.subheader("📈 Grafik Trend Prevalensi Masalah Gizi")
        prevalensi_trend_df = filtered_df.groupby("periode").apply(calculate_prevalensi).reset_index()

        fig_combined = go.Figure()
        fig_combined.add_trace(go.Scatter(
            x=prevalensi_trend_df["periode"],
            y=prevalensi_trend_df["Prevalensi_Stunting"],
            mode="lines+markers",
            name="Stunting (TBU)",
            line=dict(color="blue")
        ))
        fig_combined.add_trace(go.Scatter(
            x=prevalensi_trend_df["periode"],
            y=prevalensi_trend_df["Prevalensi_Wasting"],
            mode="lines+markers",
            name="Wasting (BBTB)",
            line=dict(color="red")
        ))
        fig_combined.add_trace(go.Scatter(
            x=prevalensi_trend_df["periode"],
            y=prevalensi_trend_df["Prevalensi_Underweight"],
            mode="lines+markers",
            name="Underweight (BBU)",
            line=dict(color="green")
        ))

        fig_combined.update_layout(
            title="Trend Prevalensi Masalah Gizi",
            xaxis_title="Periode",
            yaxis_title="Prevalensi (%)",
            legend_title="Indikator",
            hovermode="x unified",
            template="plotly_white"
        )
        st.plotly_chart(fig_combined, use_container_width=True)

        # Analisis Tren Prevalensi
        st.subheader("📋 Analisis Tren Prevalensi")
        if len(prevalensi_trend_df) > 1:
            st.markdown("""
                <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px; border: 1px solid #D3E3F5;">
                <h4 style="color: #1F77B4;">📈 Analisis Tren Prevalensi</h4>
            """, unsafe_allow_html=True)

            for indicator in ["Prevalensi_Stunting", "Prevalensi_Wasting", "Prevalensi_Underweight"]:
                first_value = prevalensi_trend_df[indicator].iloc[0]
                last_value = prevalensi_trend_df[indicator].iloc[-1]
                if last_value > first_value:
                    trend = "meningkat"
                    icon = "📈"
                    color = "#FF4D4F"
                elif last_value < first_value:
                    trend = "menurun"
                    icon = "📉"
                    color = "#2CA02C"
                else:
                    trend = "stabil"
                    icon = "➖"
                    color = "#FFA500"
                st.markdown(
                    f"""
                    <p style="color: {color}; font-size: 16px;">
                        {icon} <strong>{indicator.replace('Prevalensi_', '')}:</strong> Tren <strong>{trend}</strong> dari {first_value:.2f}% menjadi {last_value:.2f}%.
                    </p>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown("""
                <div style="background-color: #FFF3CD; padding: 15px; border-radius: 10px; border: 1px solid #FFECB3;">
                ⚠️ Data tidak cukup untuk analisis tren (minimal 2 periode).
                </div>
            """, unsafe_allow_html=True)

        # Grafik Prevalensi Terpisah (Bar Chart)
        st.subheader("📊 Grafik Prevalensi per Indikator (Berdasarkan Puskesmas)")
        if selected_puskesmas != "All":
            if "kelurahan" in filtered_df.columns:
                prevalensi_per_indikator_df = filtered_df.groupby(["puskesmas", "kelurahan"]).apply(calculate_prevalensi).reset_index()
                group_by = "kelurahan"
            else:
                prevalensi_per_indikator_df = filtered_df.groupby("puskesmas").apply(calculate_prevalensi).reset_index()
                group_by = "puskesmas"
        else:
            prevalensi_per_indikator_df = filtered_df.groupby("puskesmas").apply(calculate_prevalensi).reset_index()
            group_by = "puskesmas"

        indicators = [
            ("Prevalensi_Stunting", "Stunting (TBU)", "blue", 18.8),
            ("Prevalensi_Wasting", "Wasting (BBTB)", "red", 8.0),
            ("Prevalensi_Underweight", "Underweight (BBU)", "green", 15.0),
            ("Prevalensi_Overweight", "Overweight (BBU)", "purple", 4.0)
        ]

        for indicator, title, color, target in indicators:
            st.write(f"#### Prevalensi {title}")
            # Urutkan DataFrame berdasarkan nilai prevalensi secara menurun
            sorted_df = prevalensi_per_indikator_df.sort_values(by=indicator, ascending=False)
            x_values = sorted_df[group_by]
            y_values = sorted_df[indicator]
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=x_values,
                y=y_values,
                name=title,
                marker_color=color,
                text=y_values.apply(lambda x: f"{x:.2f}%"),
                textposition="auto"
            ))
            fig.add_shape(
                type="line",
                x0=-0.5,
                x1=len(x_values) - 0.5,
                y0=target,
                y1=target,
                line=dict(color="black", dash="dash", width=2),
                name=f"Target {title}"
            )
            fig.add_annotation(
                x=len(x_values) - 0.5,
                y=target,
                text=f"Target: {target}%",
                showarrow=True,
                arrowhead=1,
                ax=20,
                ay=-30
            )
            fig.update_layout(
                title=f"Prevalensi {title}",
                xaxis_title="Kelurahan" if selected_puskesmas != "All" and "kelurahan" in filtered_df.columns else "Puskesmas",
                yaxis_title="Prevalensi (%)",
                template="plotly_white",
                showlegend=False
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

        # Analisis Odds Ratio (OR)
        st.subheader("📉 Analisis Odds Ratio (OR) untuk Risiko Stunting")
        filtered_df["BBLR"] = filtered_df["BB_Lahir"] < 2.5
        filtered_df["PBLR"] = filtered_df["TB_Lahir"] < 48
        filtered_df["BBLR_PBLR"] = (filtered_df["BBLR"] & filtered_df["PBLR"])
        filtered_df["Stunting"] = filtered_df["ZS_TBU"] < -2

        def calculate_odds_ratio(df, exposure_col, outcome_col):
            a = df[(df[exposure_col] == True) & (df[outcome_col] == True)].shape[0]
            b = df[(df[exposure_col] == True) & (df[outcome_col] == False)].shape[0]
            c = df[(df[exposure_col] == False) & (df[outcome_col] == True)].shape[0]
            d = df[(df[exposure_col] == False) & (df[outcome_col] == False)].shape[0]
            if b == 0 or c == 0 or d == 0:
                return float('inf'), (a, b, c, d)
            odds_ratio = (a * d) / (b * c)
            return odds_ratio, (a, b, c, d)

        or_bblr, table_bblr = calculate_odds_ratio(filtered_df, "BBLR", "Stunting")
        or_pblr, table_pblr = calculate_odds_ratio(filtered_df, "PBLR", "Stunting")
        or_bblr_pblr, table_bblr_pblr = calculate_odds_ratio(filtered_df, "BBLR_PBLR", "Stunting")

        st.markdown("""
            <div style="background-color: #F0F9E8; padding: 20px; border-radius: 10px; border: 1px solid #D4EDDA;">
            <h4 style="color: #2CA02C;">📊 Analisis Odds Ratio (OR) untuk Risiko Stunting</h4>
        """, unsafe_allow_html=True)
        st.markdown(
            f"""
            <p style="color: #2CA02C; font-size: 16px;">
                📌 <strong>BBLR (BB_Lahir < 2.5 kg):</strong> Balita dengan BBLR memiliki risiko stunting <strong>{or_bblr:.2f}</strong> kali lebih tinggi dibandingkan yang tidak BBLR.<br>
                <em>Tabel Kontingensi: Stunting+ BBLR+ = {table_bblr[0]}, Stunting- BBLR+ = {table_bblr[1]}, Stunting+ BBLR- = {table_bblr[2]}, Stunting- BBLR- = {table_bblr[3]}</em>
            </p>
            """,
            unsafe_allow_html=True
        )
        st.markdown(
            f"""
            <p style="color: #2CA02C; font-size: 16px;">
                📌 <strong>PBLR (TB_Lahir < 48 cm):</strong> Balita dengan PBLR memiliki risiko stunting <strong>{or_pblr:.2f}</strong> kali lebih tinggi dibandingkan yang tidak PBLR.<br>
                <em>Tabel Kontingensi: Stunting+ PBLR+ = {table_pblr[0]}, Stunting- PBLR+ = {table_pblr[1]}, Stunting+ PBLR- = {table_pblr[2]}, Stunting- PBLR- = {table_pblr[3]}</em>
            </p>
            """,
            unsafe_allow_html=True
        )
        st.markdown(
            f"""
            <p style="color: #2CA02C; font-size: 16px;">
                📌 <strong>BBLR + PBLR:</strong> Balita dengan BBLR dan PBLR memiliki risiko stunting <strong>{or_bblr_pblr:.2f}</strong> kali lebih tinggi dibandingkan yang tidak memiliki keduanya.<br>
                <em>Tabel Kontingensi: Stunting+ (BBLR+PBLR)+ = {table_bblr_pblr[0]}, Stunting- (BBLR+PBLR)+ = {table_bblr_pblr[1]}, Stunting+ (BBLR+PBLR)- = {table_bblr_pblr[2]}, Stunting- (BBLR+PBLR)- = {table_bblr_pblr[3]}</em>
            </p>
            """,
            unsafe_allow_html=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

    elif selected_submenu == "Analisis Differensiasi Prevalensi Stunting":
        show_analisis_differensiasi_stunting(df)


# Fungsi untuk menampilkan Distribusi Data EPPGBM
def show_distribusi_data_eppgbm(df):
    # Tambahkan info dengan tone akademik dan expandable section
    with st.expander("📜 Definisi dan Insight Analisis Distribusi Data EPPGBM", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Insight Analisis Distribusi Data EPPGBM

            Berikut adalah penjelasan operasional dan insight analisis dari lima komponen utama dalam analisis distribusi data Elektronik Pencatatan dan Pelaporan Gizi Berbasis Masyarakat (EPPGBM). Penjelasan ini disusun untuk memberikan pemahaman mendalam tentang distribusi data dan implikasinya terhadap pemantauan pertumbuhan anak balita.

            #### 1. Distribusi Data Berdasarkan Kelompok Usia dan Jenis Kelamin
            - **Definisi Operasional:** Analisis ini mengelompokkan data balita berdasarkan rentang usia dalam bulan (0-5, 6-11, 12-23, 24-35, 36-47, 48-59) dan jenis kelamin (Laki-laki dan Perempuan), yang divisualisasikan dalam bentuk diagram batang bertumpuk.  
            - **Metode Pengumpulan Data:** Usia dihitung dari selisih tanggal pengukuran (`Tgl_ukur`) dan tanggal lahir (`Tgl_Lahir`), dikonversi ke bulan, dan dikelompokkan sesuai rentang standar balita (0-59 bulan). Jenis kelamin diambil dari kolom `jk` ("L" untuk Laki-laki, "P" untuk Perempuan).  
            - **Insight Analisis:** Distribusi ini memberikan gambaran demografis populasi balita yang diukur, memungkinkan identifikasi ketidakseimbangan gender atau kelompok usia tertentu yang dominan dalam pengukuran. Jika terdapat ketimpangan signifikan (misalnya, lebih banyak anak laki-laki pada kelompok usia tertentu), hal ini dapat mengindikasikan bias pengambilan sampel atau akses layanan kesehatan yang tidak merata, yang memerlukan investigasi lebih lanjut untuk memastikan representasi data yang akurat.

            #### 2. Distribusi Data Berdasarkan Umur (Tahun) dan Jenis Kelamin
            - **Definisi Operasional:** Analisis ini menyajikan distribusi balita berdasarkan umur dalam tahun (0, 1, 2, 3, 4 tahun) dan jenis kelamin, divisualisasikan dalam diagram batang bertumpuk untuk menunjukkan jumlah balita pada setiap kategori.  
            - **Metode Pengumpulan Data:** Umur dalam tahun dipetakan dari usia dalam bulan (`usia_bulan`) menggunakan fungsi pemetaan berbasis rentang (0-11 bulan = 0 tahun, 12-23 bulan = 1 tahun, dst.), dengan jenis kelamin dari kolom `jk`.  
            - **Insight Analisis:** Visualisasi ini mempermudah pemahaman tren pertumbuhan tahunan dan distribusi gender pada skala yang lebih kasar dibandingkan kelompok usia bulanan. Pola yang tidak merata (misalnya, penurunan jumlah balita pada usia 4 tahun) dapat menunjukkan rendahnya cakupan pengukuran pada anak yang mendekati batas usia balita, sehingga diperlukan strategi untuk meningkatkan partisipasi kader dalam pengukuran kelompok usia tersebut.

            #### 3. Tabel Proporsi Mismatches Posisi Pengukuran Panjang dan Tinggi Badan
            - **Definisi Operasional:** Tabel ini menghitung proporsi balita yang diukur dalam posisi tidak sesuai dengan rekomendasi (terlentang untuk <24 bulan, berdiri untuk ≥24 bulan), berdasarkan perbandingan kolom `cara_ukur` dengan posisi yang diharapkan (`expected_position`) sesuai kelompok usia.  
            - **Metode Pengumpulan Data:** Data diambil dari kolom `cara_ukur` dan `age_group`, dengan mismatch dihitung sebagai persentase kasus yang tidak sesuai dari total pengukuran per kelompok usia.  
            - **Insight Analisis:** Tingkat mismatch yang tinggi (misalnya >20%) mengindikasikan inkonsistensi dalam pelaksanaan prosedur pengukuran oleh kader kesehatan, yang dapat memengaruhi akurasi data tinggi/panjang badan. Hal ini menyarankan perlunya pelatihan ulang kader untuk mematuhi standar pengukuran WHO, meskipun ada faktor koreksi yang dapat diterapkan pada data.

            #### 4. Distribusi Digit Preferensi Berat Badan (BB) dan Tinggi Badan (TB)
            - **Definisi Operasional:** Analisis ini mengevaluasi distribusi digit desimal (0.0 hingga 0.9) dari pengukuran berat badan (`bb`) dan tinggi badan (`tinggi`), divisualisasikan dalam diagram batang horizontal untuk mengidentifikasi kecenderungan pembulatan atau preferensi digit tertentu.  
            - **Metode Pengumpulan Data:** Digit desimal diekstraksi dari nilai `bb` dan `tinggi` menggunakan operasi modulus dan pembulatan, kemudian dihitung proporsinya dalam persentase.  
            - **Insight Analisis:** Distribusi yang tidak merata (misalnya, dominasi digit 0.0 atau 0.5) menunjukkan adanya bias pengukuran atau pembulatan oleh kader, yang dapat mengurangi ketepatan data. Jika proporsi digit tertentu jauh lebih tinggi dari rata-rata acak (10%), diperlukan kalibrasi alat ukur dan pelatihan untuk memastikan pengukuran dilakukan dengan presisi yang lebih tinggi.

            #### 5. Distribusi Metrik Berat Badan dan Tinggi Badan
            - **Definisi Operasional:** Analisis ini menyajikan distribusi frekuensi digit integer dari berat badan (`bb`) dan tinggi badan (`tinggi`) berdasarkan jumlah individu unik (`nik`), divisualisasikan dalam diagram batang untuk menunjukkan pola pengukuran.  
            - **Metode Pengumpulan Data:** Digit integer diambil dari `bb` dan `tinggi`, dengan frekuensi dihitung berdasarkan `nik` untuk menghindari duplikasi, dan divisualisasikan dalam dua grafik berdampingan.  
            - **Insight Analisis:** Puncak frekuensi yang tidak wajar (misalnya, terlalu banyak pengukuran pada 10 kg atau 70 cm) dapat mengindikasikan preferensi pengukuran atau kesalahan sistematik dalam pencatatan. Pola ini menyarankan perlunya audit data dan pemeriksaan alat ukur untuk memastikan validitas pengukuran, yang krusial untuk analisis status gizi lebih lanjut seperti Z-score.

            </div>
        """, unsafe_allow_html=True)

    st.subheader("📊 Distribusi Data EPPGBM")
    # Filter Periode, Puskesmas, dan Kelurahan
    st.sidebar.subheader("🔍 Filter Data")
    if "periode" in df.columns:
        periode_options = ["All"] + sorted(df["periode"].dropna().unique().tolist())
        if not periode_options or len(periode_options) <= 1:
            st.sidebar.warning("⚠️ Kolom 'periode' tidak memiliki data unik yang valid selain 'All'. Periksa dataset.")
    else:
        periode_options = ["All"]
        st.sidebar.warning("⚠️ Kolom 'periode' tidak ditemukan di dataset. Filter default ke 'All'.")
    selected_periode = st.sidebar.selectbox("Pilih Periode Pengukuran", periode_options)
    
    puskesmas_options = ["All"] + sorted(df["puskesmas"].unique().tolist()) if "puskesmas" in df.columns else ["All"]
    kelurahan_options = ["All"] + sorted(df["kelurahan"].unique().tolist()) if "kelurahan" in df.columns else ["All"]
    selected_puskesmas = st.sidebar.selectbox("Pilih Puskesmas", puskesmas_options)
    selected_kelurahan = st.sidebar.selectbox("Pilih Kelurahan", kelurahan_options)

    # Filter dataset berdasarkan pilihan
    filtered_df = df.copy()
    if selected_periode != "All":
        filtered_df = filtered_df[filtered_df["periode"] == selected_periode]
    if selected_puskesmas != "All":
        filtered_df = filtered_df[filtered_df["puskesmas"] == selected_puskesmas]
    if selected_kelurahan != "All":
        filtered_df = filtered_df[filtered_df["kelurahan"] == selected_kelurahan]

    # Menghitung usia dalam bulan
    filtered_df["usia_bulan"] = ((pd.to_datetime(filtered_df["Tgl_ukur"]) - pd.to_datetime(filtered_df["Tgl_Lahir"])) / pd.Timedelta(days=30.4375)).astype(int)

    # Memastikan usia_bulan dalam rentang yang valid (0-59 bulan untuk balita)
    filtered_df = filtered_df[(filtered_df["usia_bulan"] >= 0) & (filtered_df["usia_bulan"] <= 59)]

    # Membuat kelompok usia dalam bulan
    bins_bulan = [-1, 5, 11, 23, 35, 47, 59]
    labels_bulan = ["0-5 bulan", "6-11 bulan", "12-23 bulan", "24-35 bulan", "36-47 bulan", "48-59 bulan"]
    filtered_df["age_group"] = pd.cut(filtered_df["usia_bulan"], bins=bins_bulan, labels=labels_bulan, right=True, include_lowest=True)

    # Visualisasi Distribusi Berdasarkan Kelompok Usia (Bulan)
    distribusi_df = filtered_df.groupby(["age_group", "jk"]).agg({"nama_balita": "count"}).reset_index()
    distribusi_df = distribusi_df.pivot(index="age_group", columns="jk", values="nama_balita").fillna(0)
    distribusi_df = distribusi_df.reset_index()

    fig = px.bar(distribusi_df, x="age_group", y=["L", "P"],
                 title="Distribusi Data Berdasarkan Kelompok Usia dan Jenis Kelamin",
                 labels={"value": "Jumlah Balita", "age_group": "Kelompok Usia"},
                 color_discrete_map={"L": "#1E90FF", "P": "#FF69B4"},
                 barmode="stack",
                 text_auto=True)
    fig.update_traces(textposition="auto", textfont=dict(size=12))
    fig.update_layout(
        xaxis_title="Kelompok Usia",
        yaxis_title="Jumlah Balita",
        title_x=0.5,
        height=500,
        legend_title="Jenis Kelamin",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

    # Menampilkan tabel distribusi berdasarkan kelompok usia
    st.subheader("📋 Tabel Distribusi Data Berdasarkan Kelompok Usia")
    st.dataframe(distribusi_df, use_container_width=True)

    # Analisis Proporsi Jenis Kelamin
    st.subheader("📊 Proporsi Jenis Kelamin")
    # Gunakan filtered_df yang sudah ada dari filter sebelumnya
    jk_counts = filtered_df["jk"].value_counts().reset_index()
    jk_counts.columns = ["Jenis Kelamin", "Jumlah"]
    jk_counts["Jenis Kelamin"] = jk_counts["Jenis Kelamin"].replace({"L": "Laki-laki", "P": "Perempuan"})
    jk_counts["Persentase"] = (jk_counts["Jumlah"] / jk_counts["Jumlah"].sum() * 100).round(2)

    # Visualisasi Pie Chart
    fig_jk = px.pie(jk_counts, 
                    values="Jumlah", 
                    names="Jenis Kelamin", 
                    title="Proporsi Jenis Kelamin Balita",
                    color="Jenis Kelamin",
                    color_discrete_map={"Laki-laki": "#1E90FF", "Perempuan": "#FF69B4"})
    fig_jk.update_traces(textposition="inside", textinfo="percent+label")
    fig_jk.update_layout(
        title_x=0.5,
        height=400,
        legend_title="Jenis Kelamin",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_jk, use_container_width=True)

    # Tampilkan tabel proporsi
    st.write("**Tabel Proporsi Jenis Kelamin**")
    jk_counts_display = jk_counts[["Jenis Kelamin", "Jumlah", "Persentase"]]
    jk_counts_display["Persentase"] = jk_counts_display["Persentase"].astype(str) + "%"
    st.dataframe(jk_counts_display, use_container_width=True)

    # Mapping usia_bulan ke usia_tahun_group
    def map_to_age_year(usia_bulan):
        if 0 <= usia_bulan <= 11:
            return "0 tahun"
        elif 12 <= usia_bulan <= 23:
            return "1 tahun"
        elif 24 <= usia_bulan <= 35:
            return "2 tahun"
        elif 36 <= usia_bulan <= 47:
            return "3 tahun"
        elif 48 <= usia_bulan <= 59:
            return "4 tahun"
        else:
            return "Tidak Diketahui"

    filtered_df["usia_tahun_group"] = filtered_df["usia_bulan"].apply(map_to_age_year)

    # Visualisasi Distribusi Berdasarkan Umur (Tahun)
    distribusi_tahun_df = filtered_df.groupby(["usia_tahun_group", "jk"]).agg({"nama_balita": "count"}).reset_index()
    distribusi_tahun_df = distribusi_tahun_df.pivot(index="usia_tahun_group", columns="jk", values="nama_balita").fillna(0)
    distribusi_tahun_df = distribusi_tahun_df.reset_index()

    fig_tahun = px.bar(distribusi_tahun_df, x="usia_tahun_group", y=["L", "P"],
                       title="Distribusi Data Berdasarkan Umur (Tahun) dan Jenis Kelamin",
                       labels={"value": "Jumlah Balita", "usia_tahun_group": "Umur (Tahun)"},
                       color_discrete_map={"L": "#1E90FF", "P": "#FF69B4"},
                       barmode="stack",
                       text_auto=True)
    fig_tahun.update_traces(textposition="auto", textfont=dict(size=12))
    fig_tahun.update_layout(
        xaxis_title="Umur (Tahun)",
        yaxis_title="Jumlah Balita",
        title_x=0.5,
        height=500,
        legend_title="Jenis Kelamin",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_tahun, use_container_width=True)

    # Menampilkan tabel distribusi berdasarkan tahun
    st.subheader("📋 Tabel Distribusi Data Berdasarkan Umur (Tahun)")
    st.dataframe(distribusi_tahun_df, use_container_width=True)

    # Analisis Tabel Proporsi Mismatches Posisi Pengukuran
    st.subheader("📋 Tabel Proporsi Mismatches Posisi Pengukuran")

    # Pastikan kolom cara_ukur ada
    if "cara_ukur" not in filtered_df.columns:
        st.error("Kolom 'cara_ukur' tidak ditemukan di dataset. Silakan periksa data.")
        return

    # Definisikan expected position berdasarkan kelompok usia
    def get_expected_position(age_group):
        if age_group in ["0-5 bulan", "6-11 bulan", "12-23 bulan"]:
            return "Terlentang"
        else:  # 24-35 bulan, 36-47 bulan, 48-59 bulan
            return "Berdiri"

    # Tambahkan kolom expected_position ke filtered_df
    filtered_df["expected_position"] = filtered_df["age_group"].apply(get_expected_position)

    # Hitung mismatch: jika cara_ukur tidak sama dengan expected_position
    filtered_df["is_mismatch"] = filtered_df["cara_ukur"] != filtered_df["expected_position"]

    # Buat tabel mismatch per periode
    mismatch_df = filtered_df.groupby(["periode", "age_group"]).agg(
        total=("nama_balita", "count"),
        mismatch=("is_mismatch", "sum")
    ).reset_index()

    # Hitung persentase mismatch
    mismatch_df["% Mismatch"] = (mismatch_df["mismatch"] / mismatch_df["total"] * 100).round(2)

    # Buat tabel mismatch keseluruhan (tanpa filter periode)
    mismatch_summary_df = mismatch_df.groupby("age_group").agg(
        total=("total", "sum"),
        mismatch=("mismatch", "sum")
    ).reset_index()
    mismatch_summary_df["Expected Position"] = mismatch_summary_df["age_group"].apply(get_expected_position)
    mismatch_summary_df["% Mismatch"] = (mismatch_summary_df["mismatch"] / mismatch_summary_df["total"] * 100).round(2).astype(str) + "%"

    # Ubah nama kolom untuk tampilan
    mismatch_summary_df = mismatch_summary_df.rename(columns={
        "age_group": "Age Group",
        "total": "Total",
        "mismatch": "Observed Mismatch"
    })

    # Tambahkan baris Total
    total_row = pd.DataFrame({
        "Age Group": ["Total"],
        "Expected Position": [""],
        "Total": [mismatch_summary_df["Total"].sum()],
        "Observed Mismatch": [mismatch_summary_df["Observed Mismatch"].sum()],
        "% Mismatch": [(mismatch_summary_df["Observed Mismatch"].sum() / mismatch_summary_df["Total"].sum() * 100).round(2).astype(str) + "%"]
    })

    # Gabungkan baris Total ke tabel
    mismatch_summary_df = pd.concat([mismatch_summary_df, total_row], ignore_index=True)

    # Tampilkan tabel
    st.dataframe(mismatch_summary_df, use_container_width=True)

    # Tambahkan keterangan (note) dengan "Catatan" dalam bold
    st.markdown("""
        <strong>Catatan</strong>: Mismatch berarti anak di bawah 24 bulan diukur dalam posisi berdiri (tinggi) atau anak 24 bulan atau lebih diukur dalam posisi terlentang (panjang recumbent), yang berlawanan dengan rekomendasi, meskipun memang ada Correction factor, insight tabel ini melihat seberapa konsisten kader dalam menjalankan instruksi pengukuran dengan benar.
    """, unsafe_allow_html=True)

    # Grafik Line Chart untuk Tren % Mismatch per Periode
    st.subheader("📈 Tren % Mismatch per Periode Waktu")
    if mismatch_df.empty or mismatch_df["periode"].nunique() <= 1:
        st.warning("⚠️ Tidak cukup data periode untuk menampilkan grafik tren. Pastikan ada lebih dari satu periode dalam dataset.")
    else:
        # Jika periode bukan datetime, gunakan sebagai string (kategori)
        if pd.api.types.is_datetime64_any_dtype(mismatch_df["periode"]):
            mismatch_df["periode"] = pd.to_datetime(mismatch_df["periode"], errors='coerce')
        else:
            mismatch_df["periode"] = mismatch_df["periode"].astype(str)

        # Buat line chart
        fig_trend = px.line(mismatch_df, 
                            x="periode", 
                            y="% Mismatch", 
                            color="age_group",
                            title="Tren Persentase Mismatch Posisi Pengukuran per Periode",
                            labels={"% Mismatch": "% Mismatch", "periode": "Periode Waktu", "age_group": "Kelompok Usia"},
                            markers=True)
        fig_trend.update_layout(
            xaxis_title="Periode Waktu",
            yaxis_title="% Mismatch",
            title_x=0.5,
            height=500,
            legend_title="Kelompok Usia",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        # Analisis Distribusi Digit Preferensi BB dan TB
    st.subheader("📊 Distribusi Digit Preferensi BB dan TB")

    # Pastikan kolom bb dan tinggi ada
    if "bb" not in filtered_df.columns or "tinggi" not in filtered_df.columns:
        st.error("Kolom 'bb' atau 'tinggi' tidak ditemukan di dataset. Silakan periksa data.")
        return

    # Hitung digit preferensi desimal untuk bb dan tinggi
    filtered_df["bb_decimal"] = (filtered_df["bb"] % 1).round(1)
    filtered_df["tinggi_decimal"] = (filtered_df["tinggi"] % 1).round(1)

    # Hitung proporsi untuk bb
    bb_decimal_counts = filtered_df["bb_decimal"].value_counts(normalize=True) * 100
    bb_decimal_df = pd.DataFrame({
        "Digit": bb_decimal_counts.index,
        "Proportion (%)": bb_decimal_counts.values
    }).sort_values("Digit")

    # Hitung proporsi untuk tinggi
    tinggi_decimal_counts = filtered_df["tinggi_decimal"].value_counts(normalize=True) * 100
    tinggi_decimal_df = pd.DataFrame({
        "Digit": tinggi_decimal_counts.index,
        "Proportion (%)": tinggi_decimal_counts.values
    }).sort_values("Digit")

    # Buat dua grafik berdampingan
    col1, col2 = st.columns(2)

    with col1:
        fig_bb = px.bar(bb_decimal_df, 
                        x="Proportion (%)", 
                        y="Digit", 
                        orientation="h",
                        title="Digit Preferensi Berat Badan (BB)",
                        labels={"Proportion (%)": "Proporsi (%)", "Digit": "Digit Desimal"})
        fig_bb.update_yaxes(tickvals=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
        fig_bb.update_layout(
            title_x=0.5,
            height=400,
            xaxis_title="Proporsi (%)",
            yaxis_title="Digit Desimal",
            showlegend=False
        )
        st.plotly_chart(fig_bb, use_container_width=True)

    with col2:
        fig_tinggi = px.bar(tinggi_decimal_df, 
                            x="Proportion (%)", 
                            y="Digit", 
                            orientation="h",
                            title="Digit Preferensi Tinggi Badan (TB)",
                            labels={"Proportion (%)": "Proporsi (%)", "Digit": "Digit Desimal"})
        fig_tinggi.update_yaxes(tickvals=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
        fig_tinggi.update_layout(
            title_x=0.5,
            height=400,
            xaxis_title="Proporsi (%)",
            yaxis_title="Digit Desimal",
            showlegend=False
        )
        st.plotly_chart(fig_tinggi, use_container_width=True)

    # Tambahkan keterangan
    st.markdown("""
        **Catatan**: Grafik ini menunjukkan distribusi digit preferensi desimal (0.0 hingga 0.9) untuk berat badan (BB) dan tinggi badan (TB). Proporsi yang tinggi pada digit tertentu menunjukkan adanya kecenderungan pengukuran yang tidak acak, yang dapat mengindikasikan bias dalam pengukuran.
    """, unsafe_allow_html=True)

        # Analisis Distribusi Metrik Berat Badan dan Tinggi Badan
    st.subheader("📊 Distribusi Metrik Berat Badan dan Tinggi Badan")

    # Pastikan kolom bb, tinggi, dan nik ada
    if "bb" not in filtered_df.columns or "tinggi" not in filtered_df.columns or "nik" not in filtered_df.columns:
        st.error("Kolom 'bb', 'tinggi', atau 'nik' tidak ditemukan di dataset. Silakan periksa data.")
        return

    # Ambil bagian integer dari bb dan tinggi
    filtered_df["bb_integer"] = filtered_df["bb"].astype(int)
    filtered_df["tinggi_integer"] = filtered_df["tinggi"].astype(int)

    # Hitung frekuensi berdasarkan nik untuk menghindari duplikat
    bb_freq = filtered_df.groupby("bb_integer")["nik"].nunique().reset_index(name="Frequency")
    tinggi_freq = filtered_df.groupby("tinggi_integer")["nik"].nunique().reset_index(name="Frequency")

    # Buat dua grafik berdampingan
    col1, col2 = st.columns(2)

    with col1:
        fig_bb_dist = px.bar(bb_freq, 
                             x="bb_integer", 
                             y="Frequency",
                             title="Distribusi Berat Badan (BB)",
                             labels={"bb_integer": "Berat Badan (kg) - Digit (integer)", "Frequency": "Frekuensi"},
                             text_auto=True)
        fig_bb_dist.update_traces(textposition="outside")
        fig_bb_dist.update_layout(
            title_x=0.5,
            height=400,
            xaxis_title="Berat Badan (kg) - Digit (integer)",
            yaxis_title="Frekuensi",
            showlegend=False
        )
        st.plotly_chart(fig_bb_dist, use_container_width=True)

    with col2:
        fig_tinggi_dist = px.bar(tinggi_freq, 
                                 x="tinggi_integer", 
                                 y="Frequency",
                                 title="Distribusi Tinggi Badan (TB)",
                                 labels={"tinggi_integer": "Tinggi Badan (cm) - Digit (integer)", "Frequency": "Frekuensi"},
                                 text_auto=True)
        fig_tinggi_dist.update_traces(textposition="outside")
        fig_tinggi_dist.update_layout(
            title_x=0.5,
            height=400,
            xaxis_title="Tinggi Badan (cm) - Digit (integer)",
            yaxis_title="Frekuensi",
            showlegend=False
        )
        st.plotly_chart(fig_tinggi_dist, use_container_width=True)

    # Tambahkan keterangan
    st.markdown("""
        **Catatan**: Grafik ini menunjukkan distribusi frekuensi integer dari berat badan (BB) dan tinggi badan (TB) berdasarkan jumlah individu unik (nik). Puncak frekuensi menunjukkan digit yang paling sering diukur, yang dapat mengindikasikan preferensi pengukuran.
    """, unsafe_allow_html=True)

# Fungsi placeholder untuk analisis lainnya
def show_distribusi_zscore_analysis(df):
    st.subheader("📈 Distribusi Z-Score Analysis")
# Tambahkan informasi dengan tone akademik, penjelasan untuk orang awam, dan background biru muda
    with st.expander("📜 Definisi dan Insight Analisis Distribusi Z-Score", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Insight Analisis Distribusi Z-Score

            Berikut adalah definisi operasional, metode analisis, serta insight dari tiga komponen utama dalam analisis distribusi Z-Score Elektronik Pencatatan dan Pelaporan Gizi Berbasis Masyarakat (EPPGBM). Informasi ini disusun untuk memberikan pemahaman mendalam tentang distribusi Z-Score dan implikasinya terhadap pemantauan status gizi anak balita, dengan penjelasan sederhana untuk memudahkan pemahaman.

            #### 1. Distribusi Z-Score Berdasarkan Indikator (BB/U, TB/U, BB/TB)
            - **Definisi Operasional:** Analisis ini menyajikan distribusi Z-Score untuk tiga indikator utama status gizi, yaitu Berat Badan menurut Umur (BB/U), Tinggi Badan menurut Umur (TB/U), dan Berat Badan menurut Tinggi Badan (BB/TB). Distribusi divisualisasikan dalam bentuk histogram dengan kurva kepadatan probabilitas untuk menggambarkan variasi Z-Score dalam populasi balita, dibandingkan dengan standar WHO (rata-rata=0, standar deviasi=1).  
            - **Metode Pengumpulan Data:** Data Z-Score diambil dari kolom `ZS_BBU`, `ZS_TBU`, dan `ZS_BBTB` dalam dataset, yang telah dihitung berdasarkan standar WHO. Dataset difilter berdasarkan periode pengukuran, puskesmas, dan kelurahan, dengan usia balita dibatasi pada rentang 0-59 bulan. Distribusi dihitung menggunakan histogram dengan normalisasi kepadatan probabilitas, dan kurva normal ditambahkan berdasarkan rata-rata dan standar deviasi data.  
            - **Insight Analisis:** Distribusi Z-Score memberikan gambaran variabilitas status gizi. Penyimpangan signifikan dari standar WHO (misalnya, rata-rata Z-Score < -1 atau > 1) dapat mengindikasikan masalah gizi seperti stunting (TB/U rendah), underweight (BB/U rendah), atau wasting (BB/TB rendah). Hal ini dapat menjadi sinyal untuk investigasi lebih lanjut, seperti evaluasi program gizi atau intervensi kesehatan masyarakat di wilayah tertentu.  
            - **Penjelasan Sederhana:** Grafik ini menunjukkan sebaran nilai Z-Score, yang mengukur seberapa jauh pertumbuhan anak dari standar WHO. Jika banyak anak memiliki Z-Score di bawah -1, artinya banyak anak yang pertumbuhannya di bawah rata-rata, misalnya terlalu pendiam atau kurus, dan perlu perhatian khusus.

            #### 2. Growth Chart Berdasarkan Standar WHO
            - **Definisi Operasional:** Analisis ini menyajikan Growth Chart untuk setiap indikator (BB/U, TB/U, BB/TB), dipisahkan berdasarkan jenis kelamin (laki-laki dan perempuan). Growth Chart menampilkan data aktual balita dalam bentuk scatter plot, dibandingkan dengan garis referensi standar deviasi (SD) WHO: SD-3, SD-2, SD-1, SD0, SD+1, SD+2, dan SD+3, yang dihitung menggunakan tabel LMS (Lambda-Mu-Sigma) dari WHO.  
            - **Rumus Perhitungan:** Nilai referensi SD dihitung menggunakan rumus LMS:  
            - Jika L ≠ 0, maka nilai = M × (1 + L × S × Z)^(1/L)  
            - Jika L = 0, maka nilai = M × e^(S × Z)  
            - **Penjelasan Sederhana:** Rumus ini digunakan untuk menghitung garis standar WHO berdasarkan data LMS (Lambda, Mu, Sigma). Nilai ini menunjukkan batas normal pertumbuhan anak, seperti berat atau tinggi badan yang ideal untuk usianya.  
            - **Metode Pengumpulan Data:** Data aktual diambil dari kolom `bb` (berat badan), `tinggi` (tinggi badan), dan `usia_bulan`, difilter berdasarkan jenis kelamin (`jk`). Tabel LMS diambil dari database untuk laki-laki (`WFA_boys`, `LFA_boys`, `WFH_boys`) dan perempuan (`WFA_girls`, `LFA_girls`, `WFH_girls`).  
            - **Insight Analisis:** Growth Chart memungkinkan visualisasi posisi pertumbuhan anak relatif terhadap standar WHO. Banyak titik data di bawah garis SD-2 (terutama untuk TB/U) mengindikasikan prevalensi stunting tinggi, sedangkan titik di atas SD+2 dapat menunjukkan risiko obesitas. Pemisahan berdasarkan jenis kelamin memungkinkan analisis yang lebih spesifik, mengingat perbedaan pertumbuhan alami antara laki-laki dan perempuan, sehingga intervensi dapat dirancang secara tepat sasaran.  
            - **Penjelasan Sederhana:** Grafik ini seperti peta pertumbuhan anak. Jika titik anak berada di bawah garis hijau (SD-2), artinya pertumbuhannya kurang dari standar, misalnya terlalu pendiam untuk usianya. Jika di atas garis kuning (SD+2), artinya anak mungkin kelebihan berat badan.

            #### 3. Distribusi Z-Score Berdasarkan Indikator dan Kelompok Usia
            - **Definisi Operasional:** Analisis ini mengelompokkan distribusi Z-Score berdasarkan indikator (BB/U, TB/U, BB/TB) dan kelompok usia (0-5 bulan, 6-11 bulan, 12-23 bulan, 24-35 bulan, 36-47 bulan, 48-59 bulan). Distribusi divisualisasikan dalam bentuk kurva kepadatan probabilitas untuk setiap kelompok usia, dibandingkan dengan kurva standar WHO.  
            - **Metode Pengumpulan Data:** Usia balita dihitung dalam bulan dari selisih tanggal pengukuran (`Tgl_ukur`) dan tanggal lahir (`Tgl_Lahir`), kemudian dikelompokkan menggunakan metode binning. Data Z-Score diambil dari kolom `ZS_BBU`, `ZS_TBU`, dan `ZS_BBTB`. Kurva kepadatan probabilitas dihitung menggunakan distribusi normal berdasarkan rata-rata dan standar deviasi data masing-masing kelompok usia.  
            - **Insight Analisis:** Distribusi Z-Score berdasarkan kelompok usia memungkinkan identifikasi pola status gizi pada tahap perkembangan yang berbeda. Z-Score TB/U yang rendah pada kelompok usia 0-5 bulan dapat mengindikasikan masalah gizi sejak dini, sedangkan Z-Score BB/TB yang tinggi pada kelompok usia 36-47 bulan dapat menjadi indikator risiko obesitas. Analisis ini membantu merancang intervensi spesifik untuk kelompok usia tertentu dan memantau efektivitas program gizi jangka panjang.  
            - **Penjelasan Sederhana:** Grafik ini membandingkan pertumbuhan anak di setiap kelompok usia. Jika kurva anak lebih ke kiri dari kurva WHO (berarti Z-Score rendah), artinya banyak anak di kelompok usia itu yang pertumbuhannya kurang, misalnya terlalu pendiam atau kurus. Jika ke kanan, artinya banyak yang kelebihan berat badan.

            </div>
        """, unsafe_allow_html=True)
    # Pastikan kolom Z-Score ada di dataset
    required_columns = ["ZS_BBU", "ZS_TBU", "ZS_BBTB"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"Kolom berikut tidak ditemukan di dataset: {', '.join(missing_columns)}. Silakan periksa data.")
        return

    # Filter Periode, Puskesmas, dan Kelurahan (menggunakan filter yang sama seperti sebelumnya)
    st.sidebar.subheader("🔍 Filter Data")
    if "periode" in df.columns:
        periode_options = ["All"] + sorted(df["periode"].dropna().unique().tolist())
        if not periode_options or len(periode_options) <= 1:
            st.sidebar.warning("⚠️ Kolom 'periode' tidak memiliki data unik yang valid selain 'All'. Periksa dataset.")
    else:
        periode_options = ["All"]
        st.sidebar.warning("⚠️ Kolom 'periode' tidak ditemukan di dataset. Filter default ke 'All'.")
    selected_periode = st.sidebar.selectbox("Pilih Periode Pengukuran", periode_options)

    puskesmas_options = ["All"] + sorted(df["puskesmas"].unique().tolist()) if "puskesmas" in df.columns else ["All"]
    kelurahan_options = ["All"] + sorted(df["kelurahan"].unique().tolist()) if "kelurahan" in df.columns else ["All"]
    selected_puskesmas = st.sidebar.selectbox("Pilih Puskesmas", puskesmas_options)
    selected_kelurahan = st.sidebar.selectbox("Pilih Kelurahan", kelurahan_options)

    # Filter dataset berdasarkan pilihan
    filtered_df = df.copy()
    if selected_periode != "All":
        filtered_df = filtered_df[filtered_df["periode"] == selected_periode]
    if selected_puskesmas != "All":
        filtered_df = filtered_df[filtered_df["puskesmas"] == selected_puskesmas]
    if selected_kelurahan != "All":
        filtered_df = filtered_df[filtered_df["kelurahan"] == selected_kelurahan]

    # Pastikan tidak ada data kosong di kolom Z-Score
    filtered_df = filtered_df.dropna(subset=["ZS_BBU", "ZS_TBU", "ZS_BBTB"])

    if filtered_df.empty:
        st.warning("⚠️ Tidak ada data yang sesuai dengan filter yang dipilih. Silakan sesuaikan filter.")
        return

    # Menghitung usia dalam bulan (jika belum ada)
    if "usia_bulan" not in filtered_df.columns:
        filtered_df["usia_bulan"] = ((pd.to_datetime(filtered_df["Tgl_ukur"]) - pd.to_datetime(filtered_df["Tgl_Lahir"])) / pd.Timedelta(days=30.4375)).astype(int)

    # Memastikan usia_bulan dalam rentang yang valid (0-59 bulan untuk balita)
    filtered_df = filtered_df[(filtered_df["usia_bulan"] >= 0) & (filtered_df["usia_bulan"] <= 59)]

    # Membuat kelompok usia dalam bulan
    bins_bulan = [-1, 5, 11, 23, 35, 47, 59]
    labels_bulan = ["0-5 bulan", "6-11 bulan", "12-23 bulan", "24-35 bulan", "36-47 bulan", "48-59 bulan"]
    filtered_df["age_group"] = pd.cut(filtered_df["usia_bulan"], bins=bins_bulan, labels=labels_bulan, right=True, include_lowest=True)

    # Fungsi untuk membuat grafik distribusi Z-Score
    def plot_zscore_distribution(zscore_data, title, indicator):
        # Hitung statistik dasar
        mean_zscore = zscore_data.mean()
        std_zscore = zscore_data.std()
        min_zscore = zscore_data.min()
        max_zscore = zscore_data.max()

        # Buat histogram untuk distribusi Z-Score
        fig = px.histogram(zscore_data, 
                           nbins=50, 
                           histnorm="probability density",
                           title=f"Distribusi Z-Score {indicator}",
                           labels={zscore_data.name: f"Z-Score ({indicator})", "count": "Jumlah Observasi"},
                           color_discrete_sequence=["#4682B4"])

        # Tambahkan kurva distribusi normal
        x_range = np.linspace(min_zscore, max_zscore, 100)
        normal_curve = norm.pdf(x_range, mean_zscore, std_zscore)
        fig.add_scatter(x=x_range, y=normal_curve, 
                        mode="lines", 
                        name="Distribusi Normal", 
                        line=dict(color="black", dash="dash"))

        # Tambahkan garis Median WHO (Z-Score = 0)
        fig.add_vline(x=0, line=dict(color="yellow", dash="dash"), name="Median WHO")

        # Update layout
        fig.update_layout(
            xaxis_title=f"Z-Score ({indicator})",
            yaxis_title="Probabilitas Densitas",
            title_x=0.5,
            height=500,
            legend_title="Legenda",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)

    # Grafik 1: Distribusi Z-Score BBU
    st.write("**Distribusi Z-Score Berat Badan menurut Umur (BB/U)**")
    plot_zscore_distribution(filtered_df["ZS_BBU"], "Distribusi Z-Score BBU", "BB/U")

    # Grafik 2: Distribusi Z-Score TBU
    st.write("**Distribusi Z-Score Tinggi Badan menurut Umur (TB/U)**")
    plot_zscore_distribution(filtered_df["ZS_TBU"], "Distribusi Z-Score TBU", "TB/U")

    # Grafik 3: Distribusi Z-Score BBTB
    st.write("**Distribusi Z-Score Berat Badan menurut Tinggi Badan (BB/TB)**")
    plot_zscore_distribution(filtered_df["ZS_BBTB"], "Distribusi Z-Score BBTB", "BB/TB")

    
def show_analisis_zscore_flag(df):
    st.subheader("⚠️ Analisis Z-Score Flag")

    # Tambahkan informasi dengan tone akademik, penjelasan untuk orang awam, dan background biru muda
    with st.expander("📜 Definisi dan Insight Analisis Z-Score Flag", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Insight Analisis Z-Score Flag

            Berikut adalah definisi operasional, metode analisis, serta insight dari analisis Z-Score Flag dalam Elektronik Pencatatan dan Pelaporan Gizi Berbasis Masyarakat (EPPGBM). Analisis ini bertujuan untuk mengidentifikasi data yang dianggap sebagai outlier (disebut "flag") berdasarkan pedoman WHO, dengan penjelasan sederhana untuk memudahkan pemahaman.

            #### Definisi Operasional
            Analisis Z-Score Flag mengidentifikasi data pengukuran balita yang memiliki nilai Z-Score di luar batas wajar menurut standar WHO. Batas ini digunakan untuk menandai data yang tidak realistis atau memerlukan perhatian khusus, yang mungkin disebabkan oleh kesalahan pengukuran atau kondisi kesehatan yang ekstrem. Indikator yang dianalisis meliputi:
            - **Berat Badan menurut Umur (BB/U):** Flag jika Z-Score < -6 atau > 5.
            - **Tinggi Badan menurut Umur (TB/U):** Flag jika Z-Score < -6 atau > 6.
            - **Berat Badan menurut Tinggi Badan (BB/TB):** Flag jika Z-Score < -5 atau > 5.

            #### Metode Pengumpulan Data
            Data Z-Score diambil dari kolom `ZS_BBU`, `ZS_TBU`, dan `ZS_BBTB` dalam dataset, yang telah dihitung berdasarkan standar WHO. Dataset difilter berdasarkan periode pengukuran, puskesmas, dan kelurahan, dengan usia balita dibatasi pada rentang 0-59 bulan. Data kemudian dikelompokkan berdasarkan kelompok usia (0-5 bulan, 6-11 bulan, 12-23 bulan, 24-35 bulan, 36-47 bulan, 48-59 bulan) untuk analisis lebih lanjut.

            #### Insight Analisis
            Data yang teridentifikasi sebagai flag menunjukkan potensi masalah, seperti kesalahan pengukuran oleh kader, alat ukur yang tidak terkalibrasi, atau kondisi kesehatan anak yang ekstrem (misalnya, malnutrisi berat atau obesitas). Jumlah flag yang tinggi pada indikator tertentu (misalnya, TB/U) dapat mengindikasikan perlunya pelatihan ulang kader atau pemeriksaan lebih lanjut terhadap anak-anak tersebut. Analisis ini membantu memastikan kualitas data sebelum digunakan untuk pengambilan keputusan lebih lanjut.

            #### Penjelasan Sederhana
            Z-Score Flag adalah cara untuk menemukan data yang "aneh" atau tidak wajar. Misalnya, jika Z-Score terlalu rendah (di bawah -6) atau terlalu tinggi (di atas 5), itu bisa berarti ada kesalahan saat mengukur berat atau tinggi anak, atau anak tersebut memang memiliki kondisi khusus yang perlu diperiksa lebih lanjut. Grafik dan tabel di bawah ini menunjukkan berapa banyak data yang bermasalah untuk setiap indikator.

            </div>
        """, unsafe_allow_html=True)

    # Pastikan kolom Z-Score ada di dataset
    required_columns = ["ZS_BBU", "ZS_TBU", "ZS_BBTB"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"Kolom berikut tidak ditemukan di dataset: {', '.join(missing_columns)}. Silakan periksa data.")
        return

    # Filter Periode, Puskesmas, dan Kelurahan (menggunakan filter yang sama seperti sebelumnya)
    st.sidebar.subheader("🔍 Filter Data")
    if "periode" in df.columns:
        periode_options = ["All"] + sorted(df["periode"].dropna().unique().tolist())
        if not periode_options or len(periode_options) <= 1:
            st.sidebar.warning("⚠️ Kolom 'periode' tidak memiliki data unik yang valid selain 'All'. Periksa dataset.")
    else:
        periode_options = ["All"]
        st.sidebar.warning("⚠️ Kolom 'periode' tidak ditemukan di dataset. Filter default ke 'All'.")
    selected_periode = st.sidebar.selectbox("Pilih Periode Pengukuran", periode_options)

    puskesmas_options = ["All"] + sorted(df["puskesmas"].unique().tolist()) if "puskesmas" in df.columns else ["All"]
    kelurahan_options = ["All"] + sorted(df["kelurahan"].unique().tolist()) if "kelurahan" in df.columns else ["All"]
    selected_puskesmas = st.sidebar.selectbox("Pilih Puskesmas", puskesmas_options)
    selected_kelurahan = st.sidebar.selectbox("Pilih Kelurahan", kelurahan_options)

    # Filter dataset berdasarkan pilihan
    filtered_df = df.copy()
    if selected_periode != "All":
        filtered_df = filtered_df[filtered_df["periode"] == selected_periode]
    if selected_puskesmas != "All":
        filtered_df = filtered_df[filtered_df["puskesmas"] == selected_puskesmas]
    if selected_kelurahan != "All":
        filtered_df = filtered_df[filtered_df["kelurahan"] == selected_kelurahan]

    # Pastikan tidak ada data kosong di kolom Z-Score
    filtered_df = filtered_df.dropna(subset=["ZS_BBU", "ZS_TBU", "ZS_BBTB"])

    if filtered_df.empty:
        st.warning("⚠️ Tidak ada data yang sesuai dengan filter yang dipilih. Silakan sesuaikan filter.")
        return

    # Menghitung usia dalam bulan (jika belum ada)
    if "usia_bulan" not in filtered_df.columns:
        filtered_df["usia_bulan"] = ((pd.to_datetime(filtered_df["Tgl_ukur"]) - pd.to_datetime(filtered_df["Tgl_Lahir"])) / pd.Timedelta(days=30.4375)).astype(int)

    # Memastikan usia_bulan dalam rentang yang valid (0-59 bulan untuk balita)
    filtered_df = filtered_df[(filtered_df["usia_bulan"] >= 0) & (filtered_df["usia_bulan"] <= 59)]

    # Membuat kelompok usia dalam bulan
    bins_bulan = [-1, 5, 11, 23, 35, 47, 59]
    labels_bulan = ["0-5 bulan", "6-11 bulan", "12-23 bulan", "24-35 bulan", "36-47 bulan", "48-59 bulan"]
    filtered_df["age_group"] = pd.cut(filtered_df["usia_bulan"], bins=bins_bulan, labels=labels_bulan, right=True, include_lowest=True)

    # Identifikasi Z-Score Flag berdasarkan pedoman WHO
    filtered_df["BBU_flag"] = (filtered_df["ZS_BBU"] < -6) | (filtered_df["ZS_BBU"] > 5)
    filtered_df["TBU_flag"] = (filtered_df["ZS_TBU"] < -6) | (filtered_df["ZS_TBU"] > 6)
    filtered_df["BBTB_flag"] = (filtered_df["ZS_BBTB"] < -5) | (filtered_df["ZS_BBTB"] > 5)

    # Subjudul untuk Tabel Z-Score Flag
    st.subheader("📋 Tabel Z-Score Flag per Indikator dan Kelompok Usia")

    # Buat tabel yang menunjukkan jumlah dan persentase data flagged per indikator dan kelompok usia
    flag_summary = filtered_df.groupby("age_group").agg(
        total=("nama_balita", "count"),
        BBU_flagged=("BBU_flag", "sum"),
        TBU_flagged=("TBU_flag", "sum"),
        BBTB_flagged=("BBTB_flag", "sum")
    ).reset_index()

    # Hitung persentase flagged
    flag_summary["BBU_%_Flagged"] = (flag_summary["BBU_flagged"] / flag_summary["total"] * 100).round(2).astype(str) + "%"
    flag_summary["TBU_%_Flagged"] = (flag_summary["TBU_flagged"] / flag_summary["total"] * 100).round(2).astype(str) + "%"
    flag_summary["BBTB_%_Flagged"] = (flag_summary["BBTB_flagged"] / flag_summary["total"] * 100).round(2).astype(str) + "%"

    # Ubah nama kolom untuk tampilan
    flag_summary_display = flag_summary.rename(columns={
        "age_group": "Kelompok Usia",
        "total": "Total Data",
        "BBU_flagged": "BB/U Flagged",
        "TBU_flagged": "TB/U Flagged",
        "BBTB_flagged": "BB/TB Flagged",
        "BBU_%_Flagged": "BB/U % Flagged",
        "TBU_%_Flagged": "TB/U % Flagged",
        "BBTB_%_Flagged": "BB/TB % Flagged"
    })

    # Tambahkan baris Total
    total_row = pd.DataFrame({
        "Kelompok Usia": ["Total"],
        "Total Data": [flag_summary["total"].sum()],
        "BB/U Flagged": [flag_summary["BBU_flagged"].sum()],
        "TB/U Flagged": [flag_summary["TBU_flagged"].sum()],
        "BB/TB Flagged": [flag_summary["BBTB_flagged"].sum()],
        "BB/U % Flagged": [(flag_summary["BBU_flagged"].sum() / flag_summary["total"].sum() * 100).round(2).astype(str) + "%"],
        "TB/U % Flagged": [(flag_summary["TBU_flagged"].sum() / flag_summary["total"].sum() * 100).round(2).astype(str) + "%"],
        "BB/TB % Flagged": [(flag_summary["BBTB_flagged"].sum() / flag_summary["total"].sum() * 100).round(2).astype(str) + "%"]
    })

    # Gabungkan baris Total ke tabel
    flag_summary_display = pd.concat([flag_summary_display, total_row], ignore_index=True)

    # Tampilkan tabel
    st.dataframe(flag_summary_display, use_container_width=True)

    # Tambahkan keterangan
    st.markdown("""
        **Catatan**: Tabel ini menunjukkan jumlah dan persentase data yang dianggap sebagai flag (outlier) berdasarkan pedoman WHO. Flag menunjukkan data yang berada di luar batas wajar, yang mungkin disebabkan oleh kesalahan pengukuran atau kondisi ekstrem.
    """, unsafe_allow_html=True)

    # Subjudul untuk Grafik Z-Score Flag
    st.subheader("📊 Visualisasi Z-Score Flag per Indikator dan Kelompok Usia")

    # Siapkan data untuk grafik (melt data untuk visualisasi)
    flag_melted = flag_summary.melt(id_vars=["age_group"], 
                                    value_vars=["BBU_flagged", "TBU_flagged", "BBTB_flagged"],
                                    var_name="Indikator", 
                                    value_name="Jumlah Flagged")

    # Ubah nama indikator untuk tampilan
    flag_melted["Indikator"] = flag_melted["Indikator"].replace({
        "BBU_flagged": "BB/U",
        "TBU_flagged": "TB/U",
        "BBTB_flagged": "BB/TB"
    })

    # Buat grafik batang bertumpuk
    fig_flag = px.bar(flag_melted, 
                      x="age_group", 
                      y="Jumlah Flagged", 
                      color="Indikator",
                      title="Jumlah Z-Score Flag per Indikator dan Kelompok Usia",
                      labels={"age_group": "Kelompok Usia", "Jumlah Flagged": "Jumlah Data Flagged"},
                      color_discrete_map={"BB/U": "#1E90FF", "TB/U": "#FF69B4", "BB/TB": "#32CD32"},
                      barmode="stack",
                      text_auto=True)

    # Update layout
    fig_flag.update_traces(textposition="auto", textfont=dict(size=12))
    fig_flag.update_layout(
        xaxis_title="Kelompok Usia",
        yaxis_title="Jumlah Data Flagged",
        title_x=0.5,
        height=500,
        legend_title="Indikator",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # Tampilkan grafik
    st.plotly_chart(fig_flag, use_container_width=True)

    # Tambahkan keterangan untuk grafik
    st.markdown("""
        **Catatan**: Grafik ini menunjukkan jumlah data yang dianggap sebagai flag (outlier) untuk setiap indikator (BB/U, TB/U, BB/TB), dikelompokkan berdasarkan kelompok usia. Warna yang berbeda mewakili indikator yang berbeda.
    """, unsafe_allow_html=True)

# Fungsi di lingkup global
def classify_ciaf(row):
    stunting = row["ZS_TBU"] < -2
    wasting = row["ZS_BBTB"] < -2
    underweight = row["ZS_BBU"] < -2

    if not stunting and not wasting and not underweight:
        return "A"  # Tidak ada kegagalan
    elif wasting and not stunting and not underweight:
        return "B"  # Hanya wasting
    elif wasting and underweight and not stunting:
        return "C"  # Wasting dan underweight
    elif wasting and underweight and stunting:
        return "D"  # Wasting, underweight, dan stunting
    elif not wasting and not stunting and underweight:
        return "E"  # Hanya underweight
    elif not wasting and stunting and not underweight:
        return "F"  # Hanya stunting
    elif not wasting and stunting and underweight:
        return "Y"  # Stunting dan underweight
    else:
        return "Unknown"  # Untuk kombinasi yang tidak sesuai
    
def show_analisis_trend_pertumbuhan(df):
    st.subheader("📉 Analisis Tren Pertumbuhan EPPGBM")

    # Bagian 1: Z-Score Summary Table (kode sebelumnya tetap sama)
    st.write("### Tabel Ringkasan Statistik Z-Score")

    # Tambahkan informasi dengan tone akademik, penjelasan untuk orang awam, dan background biru muda
    with st.expander("📜 Definisi dan Insight Tabel Ringkasan Statistik Z-Score", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Insight Tabel Ringkasan Statistik Z-Score

            Berikut adalah definisi operasional, metode analisis, serta insight dari tabel ringkasan statistik Z-Score dalam Elektronik Pencatatan dan Pelaporan Gizi Berbasis Masyarakat (EPPGBM). Tabel ini memberikan gambaran statistik tentang distribusi Z-Score untuk memantau status gizi anak balita, dengan penjelasan sederhana untuk memudahkan pemahaman.

            #### Definisi Operasional
            Tabel Ringkasan Statistik Z-Score menyajikan statistik deskriptif dari Z-Score untuk tiga indikator utama status gizi: Berat Badan menurut Umur (BB/U), Tinggi Badan menurut Umur (TB/U), dan Berat Badan menurut Tinggi Badan (BB/TB). Statistik yang dihitung meliputi:
            - **Jumlah Data (N):** Jumlah balita dalam setiap kelompok.
            - **Rata-rata (Mean):** Nilai rata-rata Z-Score, menunjukkan posisi rata-rata pertumbuhan dibandingkan standar WHO.
            - **Standar Deviasi:** Mengukur seberapa bervariasi Z-Score dalam kelompok tersebut.
            - **Kemiringan (Skewness):** Mengukur apakah distribusi Z-Score condong ke kiri (negatif) atau ke kanan (positif).
            - **Kurtosis:** Mengukur seberapa "tajam" atau "datar" distribusi Z-Score dibandingkan distribusi normal.

            Data dikelompokkan berdasarkan:
            - **Kelompok Usia:** 0-5 bulan, 6-11 bulan, 12-23 bulan, 24-35 bulan, 36-47 bulan, 48-59 bulan.
            - **Jenis Kelamin:** Laki-laki, Perempuan, dan Tidak Diketahui (jika ada data yang tidak valid).
            - **Area:** Berdasarkan puskesmas tempat pengukuran dilakukan.

            #### Metode Pengumpulan Data
            Data Z-Score diambil dari kolom `ZS_BBU`, `ZS_TBU`, dan `ZS_BBTB` dalam dataset, yang telah dihitung berdasarkan standar WHO. Dataset difilter berdasarkan periode pengukuran, puskesmas, dan kelurahan, dengan usia balita dibatasi pada rentang 0-59 bulan. Statistik dihitung menggunakan fungsi statistik standar untuk setiap kelompok.

            #### Insight Analisis
            Tabel ini memberikan gambaran tentang distribusi Z-Score di berbagai kelompok:
            - **Rata-rata Z-Score:** Jika rata-rata jauh di bawah 0 (misalnya, < -1), ini dapat mengindikasikan masalah gizi seperti stunting (TB/U rendah) atau underweight (BB/U rendah). Sebaliknya, rata-rata di atas 0 (misalnya, > 1) dapat menunjukkan risiko obesitas.
            - **Standar Deviasi:** Nilai yang tinggi menunjukkan variasi besar dalam status gizi, yang mungkin memerlukan intervensi yang lebih spesifik untuk kelompok tertentu.
            - **Kemiringan dan Kurtosis:** Distribusi yang sangat miring atau memiliki kurtosis tinggi dapat mengindikasikan adanya outlier atau data yang tidak normal, yang perlu diperiksa lebih lanjut untuk memastikan kualitas data.

            Analisis ini membantu mengidentifikasi kelompok yang memerlukan perhatian khusus, seperti kelompok usia atau area tertentu dengan masalah gizi yang signifikan.

            #### Penjelasan Sederhana
            Tabel ini seperti "laporan nilai" untuk pertumbuhan anak. Angka-angka di dalamnya menunjukkan seberapa baik atau buruk pertumbuhan anak dibandingkan standar WHO. Misalnya, jika rata-rata Z-Score untuk tinggi badan (TB/U) di suatu kelompok usia sangat rendah (misalnya, -2), artinya banyak anak di kelompok itu yang lebih pendiam dari standar, dan mungkin perlu bantuan gizi tambahan.

            </div>
        """, unsafe_allow_html=True)

    # Pastikan kolom Z-Score ada di dataset
    required_columns = ["ZS_BBU", "ZS_TBU", "ZS_BBTB"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"Kolom berikut tidak ditemukan di dataset: {', '.join(missing_columns)}. Silakan periksa data.")
        return

    # Filter Periode, Puskesmas, dan Kelurahan
    st.sidebar.subheader("🔍 Filter Data")
    if "periode" in df.columns:
        periode_options = ["All"] + sorted(df["periode"].dropna().unique().tolist())
        if not periode_options or len(periode_options) <= 1:
            st.sidebar.warning("⚠️ Kolom 'periode' tidak memiliki data unik yang valid selain 'All'. Periksa dataset.")
    else:
        periode_options = ["All"]
        st.sidebar.warning("⚠️ Kolom 'periode' tidak ditemukan di dataset. Filter default ke 'All'.")
    selected_periode = st.sidebar.selectbox("Pilih Periode Pengukuran", periode_options)

    puskesmas_options = ["All"] + sorted(df["puskesmas"].unique().tolist()) if "puskesmas" in df.columns else ["All"]
    kelurahan_options = ["All"] + sorted(df["kelurahan"].unique().tolist()) if "kelurahan" in df.columns else ["All"]
    selected_puskesmas = st.sidebar.selectbox("Pilih Puskesmas", puskesmas_options)
    selected_kelurahan = st.sidebar.selectbox("Pilih Kelurahan", kelurahan_options)

    # Filter dataset berdasarkan pilihan
    filtered_df = df.copy()
    if selected_periode != "All":
        filtered_df = filtered_df[filtered_df["periode"] == selected_periode]
    if selected_puskesmas != "All":
        filtered_df = filtered_df[filtered_df["puskesmas"] == selected_puskesmas]
    if selected_kelurahan != "All":
        filtered_df = filtered_df[filtered_df["kelurahan"] == selected_kelurahan]

    # Pastikan tidak ada data kosong di kolom Z-Score
    filtered_df = filtered_df.dropna(subset=["ZS_BBU", "ZS_TBU", "ZS_BBTB"])

    if filtered_df.empty:
        st.warning("⚠️ Tidak ada data yang sesuai dengan filter yang dipilih. Silakan sesuaikan filter.")
        return

    # Menghitung usia dalam bulan (jika belum ada)
    if "usia_bulan" not in filtered_df.columns:
        filtered_df["usia_bulan"] = ((pd.to_datetime(filtered_df["Tgl_ukur"]) - pd.to_datetime(filtered_df["Tgl_Lahir"])) / pd.Timedelta(days=30.4375)).astype(int)

    # Memastikan usia_bulan dalam rentang yang valid (0-59 bulan untuk balita)
    filtered_df = filtered_df[(filtered_df["usia_bulan"] >= 0) & (filtered_df["usia_bulan"] <= 59)]

    # Membuat kelompok usia dalam bulan
    bins_bulan = [-1, 5, 11, 23, 35, 47, 59]
    labels_bulan = ["0-5 bulan", "6-11 bulan", "12-23 bulan", "24-35 bulan", "36-47 bulan", "48-59 bulan"]
    filtered_df["age_group"] = pd.cut(filtered_df["usia_bulan"], bins=bins_bulan, labels=labels_bulan, right=True, include_lowest=True)

    # Ubah jenis kelamin menjadi label yang lebih jelas
    filtered_df["jk_label"] = filtered_df["jk"].replace({"L": "Laki-laki", "P": "Perempuan"})
    filtered_df["jk_label"] = filtered_df["jk_label"].fillna("Tidak Diketahui")

    # 1. Ringkasan berdasarkan Kelompok Usia
    age_group_summary = filtered_df.groupby("age_group").agg({
        "ZS_BBU": ["count", "mean", "std"],
        "ZS_TBU": ["mean", "std"],
        "ZS_BBTB": ["mean", "std"]
    }).reset_index()

    # Hitung skewness dan kurtosis menggunakan apply
    age_group_skew_kurt = filtered_df.groupby("age_group").agg({
        "ZS_BBU": [lambda x: x.skew(), lambda x: x.kurtosis()],
        "ZS_TBU": [lambda x: x.skew(), lambda x: x.kurtosis()],
        "ZS_BBTB": [lambda x: x.skew(), lambda x: x.kurtosis()]
    }).reset_index()

    # Gabungkan hasil
    age_group_summary.columns = [
        "Kelompok Usia",
        "Jumlah Data",
        "BB/U Rata-rata", "BB/U Standar Deviasi",
        "TB/U Rata-rata", "TB/U Standar Deviasi",
        "BB/TB Rata-rata", "BB/TB Standar Deviasi"
    ]
    age_group_skew_kurt.columns = [
        "Kelompok Usia",
        "BB/U Kemiringan", "BB/U Kurtosis",
        "TB/U Kemiringan", "TB/U Kurtosis",
        "BB/TB Kemiringan", "BB/TB Kurtosis"
    ]
    age_group_summary = age_group_summary.merge(age_group_skew_kurt, on="Kelompok Usia")

    # Tambahkan baris "Semua" (All)
    all_summary = filtered_df.agg({
        "ZS_BBU": ["count", "mean", "std", "skew", "kurtosis"],
        "ZS_TBU": ["mean", "std", "skew", "kurtosis"],
        "ZS_BBTB": ["mean", "std", "skew", "kurtosis"]
    }).T.reset_index()
    all_row = pd.DataFrame({
        "Kelompok Usia": ["Semua"],
        "Jumlah Data": [all_summary.iloc[0, 1]],
        "BB/U Rata-rata": [all_summary.iloc[0, 2]],
        "BB/U Standar Deviasi": [all_summary.iloc[0, 3]],
        "BB/U Kemiringan": [all_summary.iloc[0, 4]],
        "BB/U Kurtosis": [all_summary.iloc[0, 5]],
        "TB/U Rata-rata": [all_summary.iloc[1, 2]],
        "TB/U Standar Deviasi": [all_summary.iloc[1, 3]],
        "TB/U Kemiringan": [all_summary.iloc[1, 4]],
        "TB/U Kurtosis": [all_summary.iloc[1, 5]],
        "BB/TB Rata-rata": [all_summary.iloc[2, 2]],
        "BB/TB Standar Deviasi": [all_summary.iloc[2, 3]],
        "BB/TB Kemiringan": [all_summary.iloc[2, 4]],
        "BB/TB Kurtosis": [all_summary.iloc[2, 5]]
    })
    age_group_summary = pd.concat([all_row, age_group_summary], ignore_index=True)

    # 2. Ringkasan berdasarkan Jenis Kelamin
    jk_summary = filtered_df.groupby("jk_label").agg({
        "ZS_BBU": ["count", "mean", "std"],
        "ZS_TBU": ["mean", "std"],
        "ZS_BBTB": ["mean", "std"]
    }).reset_index()

    jk_skew_kurt = filtered_df.groupby("jk_label").agg({
        "ZS_BBU": [lambda x: x.skew(), lambda x: x.kurtosis()],
        "ZS_TBU": [lambda x: x.skew(), lambda x: x.kurtosis()],
        "ZS_BBTB": [lambda x: x.skew(), lambda x: x.kurtosis()]
    }).reset_index()

    jk_summary.columns = [
        "Jenis Kelamin",
        "Jumlah Data",
        "BB/U Rata-rata", "BB/U Standar Deviasi",
        "TB/U Rata-rata", "TB/U Standar Deviasi",
        "BB/TB Rata-rata", "BB/TB Standar Deviasi"
    ]
    jk_skew_kurt.columns = [
        "Jenis Kelamin",
        "BB/U Kemiringan", "BB/U Kurtosis",
        "TB/U Kemiringan", "TB/U Kurtosis",
        "BB/TB Kemiringan", "BB/TB Kurtosis"
    ]
    jk_summary = jk_summary.merge(jk_skew_kurt, on="Jenis Kelamin")

    # 3. Ringkasan berdasarkan Area (Puskesmas)
    area_summary = filtered_df.groupby("puskesmas").agg({
        "ZS_BBU": ["count", "mean", "std"],
        "ZS_TBU": ["mean", "std"],
        "ZS_BBTB": ["mean", "std"]
    }).reset_index()

    area_skew_kurt = filtered_df.groupby("puskesmas").agg({
        "ZS_BBU": [lambda x: x.skew(), lambda x: x.kurtosis()],
        "ZS_TBU": [lambda x: x.skew(), lambda x: x.kurtosis()],
        "ZS_BBTB": [lambda x: x.skew(), lambda x: x.kurtosis()]
    }).reset_index()

    area_summary.columns = [
        "Area (Puskesmas)",
        "Jumlah Data",
        "BB/U Rata-rata", "BB/U Standar Deviasi",
        "TB/U Rata-rata", "TB/U Standar Deviasi",
        "BB/TB Rata-rata", "BB/TB Standar Deviasi"
    ]
    area_skew_kurt.columns = [
        "Area (Puskesmas)",
        "BB/U Kemiringan", "BB/U Kurtosis",
        "TB/U Kemiringan", "TB/U Kurtosis",
        "BB/TB Kemiringan", "BB/TB Kurtosis"
    ]
    area_summary = area_summary.merge(area_skew_kurt, on="Area (Puskesmas)")

    # Gabungkan semua ringkasan
    age_group_summary.insert(0, "Kelompok", "Kelompok Usia")
    jk_summary.insert(0, "Kelompok", "Jenis Kelamin")
    area_summary.insert(0, "Kelompok", "Area")

    age_group_summary = age_group_summary.rename(columns={"Kelompok Usia": "Kategori"})
    jk_summary = jk_summary.rename(columns={"Jenis Kelamin": "Kategori"})
    area_summary = area_summary.rename(columns={"Area (Puskesmas)": "Kategori"})

    summary_table = pd.concat([age_group_summary, jk_summary, area_summary], ignore_index=True)

    # Bulatkan nilai numerik untuk tampilan
    numeric_cols = summary_table.select_dtypes(include=[float, int]).columns
    summary_table[numeric_cols] = summary_table[numeric_cols].round(2)

    # Tampilkan tabel
    st.dataframe(summary_table, use_container_width=True)

    # Tambahkan keterangan
    st.markdown("""
        **Catatan**: Tabel ini menunjukkan statistik deskriptif Z-Score untuk indikator BB/U, TB/U, dan BB/TB, dikelompokkan berdasarkan kelompok usia, jenis kelamin, dan area (puskesmas). Statistik ini membantu memahami distribusi status gizi di berbagai kelompok.
    """, unsafe_allow_html=True)

    # Bagian 2: Analisis CIAF (Composite Index of Anthropometric Failure)
    st.write("### Analisis Composite Index of Anthropometric Failure (CIAF)")

    # Tambahkan informasi tentang CIAF
    with st.expander("📜 Definisi dan Insight Analisis CIAF", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Insight Analisis CIAF

            Berikut adalah definisi operasional, metode analisis, serta insight dari Composite Index of Anthropometric Failure (CIAF) dalam Elektronik Pencatatan dan Pelaporan Gizi Berbasis Masyarakat (EPPGBM). Analisis ini memberikan gambaran komprehensif tentang beban gizi buruk pada anak balita.

            #### Definisi Operasional
            Composite Index of Anthropometric Failure (CIAF) adalah indeks komposit yang menggabungkan tiga indikator utama status gizi: stunting (tinggi badan menurut umur rendah), wasting (berat badan menurut tinggi badan rendah), dan underweight (berat badan menurut umur rendah). CIAF mengklasifikasikan anak ke dalam tujuh kategori:
            - **A:** Tidak ada kegagalan (normal).
            - **B:** Hanya wasting.
            - **C:** Wasting dan underweight.
            - **D:** Wasting, underweight, dan stunting.
            - **E:** Hanya underweight.
            - **F:** Hanya stunting.
            - **Y:** Stunting dan underweight.

            Anak yang termasuk dalam kategori B-Y dianggap mengalami kegagalan antropometri. Prevalensi CIAF dihitung sebagai persentase anak yang mengalami setidaknya satu kegagalan (kategori B-Y) dari total populasi.

            #### Metode Pengumpulan Data
            Data diambil dari kolom Z-Score (`ZS_BBU`, `ZS_TBU`, `ZS_BBTB`) dalam dataset EPPGBM. Kegagalan antropometri ditentukan berdasarkan standar WHO (Z-Score < -2). Data dikelompokkan berdasarkan kelompok usia, jenis kelamin, dan area (puskesmas) untuk analisis lebih lanjut.

            #### Insight Analisis
            CIAF memberikan gambaran yang lebih lengkap tentang beban gizi buruk dibandingkan indikator tunggal:
            - **Prevalensi Keseluruhan:** CIAF menunjukkan persentase anak yang mengalami setidaknya satu kegagalan antropometri, yang sering kali lebih tinggi daripada indikator tunggal seperti stunting atau underweight.
            - **Pola Kegagalan:** Distribusi anak di kategori B-Y membantu memahami apakah gizi buruk bersifat akut (wasting) atau kronis (stunting), serta seberapa banyak anak yang mengalami kegagalan ganda/tiga.
            - **Kelompok Rentan:** CIAF membantu mengidentifikasi kelompok yang paling membutuhkan intervensi, terutama anak-anak dengan kegagalan ganda/tiga, yang memiliki risiko morbiditas dan mortalitas lebih tinggi.

            Analisis ini dapat digunakan untuk mendukung kebijakan gizi, seperti menargetkan intervensi pada kelompok usia atau area tertentu dengan prevalensi CIAF yang tinggi.

            #### Penjelasan Sederhana
            CIAF seperti "detektor" yang menangkap semua masalah pertumbuhan anak, baik itu anak yang terlalu pendiam (stunting), terlalu kurus (wasting), atau berat badannya kurang (underweight). Dengan CIAF, kita bisa tahu berapa banyak anak yang bermasalah dan seberapa parah masalahnya, sehingga bisa membantu menentukan siapa yang paling butuh bantuan.

            </div>
        """, unsafe_allow_html=True)

    # Terapkan klasifikasi CIAF pada dataset
    filtered_df["CIAF_Category"] = filtered_df.apply(classify_ciaf, axis=1)

    # Hitung prevalensi CIAF (persentase anak dengan kegagalan antropometri, kategori B-Y)
    ciaf_prevalence = (filtered_df["CIAF_Category"] != "A").mean() * 100

    # Hitung distribusi kategori CIAF
    ciaf_distribution = filtered_df["CIAF_Category"].value_counts(normalize=True) * 100
    ciaf_distribution_df = pd.DataFrame({
        "Kategori CIAF": ciaf_distribution.index,
        "Persentase (%)": ciaf_distribution.values
    })

    # Tampilkan prevalensi keseluruhan CIAF
    st.write(f"**Prevalensi CIAF Keseluruhan:** {ciaf_prevalence:.2f}%")
    st.write("Prevalensi ini menunjukkan persentase anak yang mengalami setidaknya satu kegagalan antropometri (kategori B-Y).")

    # Tampilkan distribusi kategori CIAF
    st.write("#### Distribusi Kategori CIAF")
    st.dataframe(ciaf_distribution_df, use_container_width=True)

    # Hitung prevalensi CIAF berdasarkan kelompok usia
    ciaf_by_age = filtered_df.groupby("age_group").apply(lambda x: (x["CIAF_Category"] != "A").mean() * 100).reset_index()
    ciaf_by_age.columns = ["Kelompok Usia", "Prevalensi CIAF (%)"]

    # Hitung distribusi kategori CIAF berdasarkan kelompok usia
    ciaf_dist_by_age = filtered_df.groupby("age_group")["CIAF_Category"].value_counts(normalize=True).unstack().fillna(0) * 100

    # Hitung prevalensi CIAF berdasarkan jenis kelamin
    ciaf_by_jk = filtered_df.groupby("jk_label").apply(lambda x: (x["CIAF_Category"] != "A").mean() * 100).reset_index()
    ciaf_by_jk.columns = ["Jenis Kelamin", "Prevalensi CIAF (%)"]

    # Hitung prevalensi CIAF berdasarkan area (puskesmas)
    ciaf_by_area = filtered_df.groupby("puskesmas").apply(lambda x: (x["CIAF_Category"] != "A").mean() * 100).reset_index()
    ciaf_by_area.columns = ["Area (Puskesmas)", "Prevalensi CIAF (%)"]

    # Tambahkan kolom prevalensi Stunting, Wasting, dan Underweight
    # Pastikan kolom TBU, BBU, dan BBTB ada di dataset
    required_status_columns = ["TBU", "BBU", "BBTB"]
    missing_status_columns = [col for col in required_status_columns if col not in filtered_df.columns]
    if missing_status_columns:
        st.error(f"Kolom berikut tidak ditemukan di dataset: {', '.join(missing_status_columns)}. Silakan periksa data.")
        return

    # Hitung prevalensi Stunting (TBU: "Pendek" atau "Sangat Pendek")
    stunting_prevalence = filtered_df.groupby("puskesmas").apply(
        lambda x: (x["TBU"].isin(["Pendek", "Sangat Pendek"])).sum() / x["TBU"].notna().sum() * 100
    ).reset_index()
    stunting_prevalence.columns = ["Area (Puskesmas)", "Prevalensi Stunting (%)"]

    # Hitung prevalensi Underweight (BBU: "Kurang" atau "Sangat Kurang")
    underweight_prevalence = filtered_df.groupby("puskesmas").apply(
        lambda x: (x["BBU"].isin(["Kurang", "Sangat Kurang"])).sum() / x["BBU"].notna().sum() * 100
    ).reset_index()
    underweight_prevalence.columns = ["Area (Puskesmas)", "Prevalensi Underweight (%)"]

    # Hitung prevalensi Wasting (BBTB: "Gizi Buruk" atau "Gizi Kurang")
    wasting_prevalence = filtered_df.groupby("puskesmas").apply(
        lambda x: (x["BBTB"].isin(["Gizi Buruk", "Gizi Kurang"])).sum() / x["BBTB"].notna().sum() * 100
    ).reset_index()
    wasting_prevalence.columns = ["Area (Puskesmas)", "Prevalensi Wasting (%)"]

    # Gabungkan semua prevalensi ke dalam tabel ciaf_by_area
    ciaf_by_area = ciaf_by_area.merge(stunting_prevalence, on="Area (Puskesmas)", how="left")
    ciaf_by_area = ciaf_by_area.merge(underweight_prevalence, on="Area (Puskesmas)", how="left")
    ciaf_by_area = ciaf_by_area.merge(wasting_prevalence, on="Area (Puskesmas)", how="left")

    # Bulatkan semua nilai prevalensi ke dua desimal
    ciaf_by_area["Prevalensi CIAF (%)"] = ciaf_by_area["Prevalensi CIAF (%)"].round(2)
    ciaf_by_area["Prevalensi Stunting (%)"] = ciaf_by_area["Prevalensi Stunting (%)"].round(2)
    ciaf_by_area["Prevalensi Underweight (%)"] = ciaf_by_area["Prevalensi Underweight (%)"].round(2)
    ciaf_by_area["Prevalensi Wasting (%)"] = ciaf_by_area["Prevalensi Wasting (%)"].round(2)

    # Tampilkan tabel prevalensi CIAF berdasarkan kelompok
    st.write("#### Prevalensi CIAF Berdasarkan Kelompok Usia")
    st.dataframe(ciaf_by_age, use_container_width=True)

    st.write("#### Distribusi Kategori CIAF Berdasarkan Kelompok Usia")
    st.dataframe(ciaf_dist_by_age, use_container_width=True)

    st.write("#### Prevalensi CIAF Berdasarkan Jenis Kelamin")
    st.dataframe(ciaf_by_jk, use_container_width=True)

    st.write("#### Prevalensi CIAF Berdasarkan Area (Puskesmas)")
    st.dataframe(ciaf_by_area, use_container_width=True)

    # Tambahkan grafik visualisasi untuk Prevalensi CIAF Berdasarkan Area (Puskesmas)
    st.write("#### Grafik Perbandingan Prevalensi CIAF, Stunting, Underweight, dan Wasting Berdasarkan Area (Puskesmas)")

    # Tambahkan filter untuk memilih puskesmas
    puskesmas_options = sorted(ciaf_by_area["Area (Puskesmas)"].unique().tolist())
    selected_puskesmas = st.multiselect(
        "Pilih Area (Puskesmas) untuk Grafik",
        puskesmas_options,
        default=puskesmas_options  # Default: semua puskesmas dipilih
    )

    # Filter data berdasarkan puskesmas yang dipilih
    if not selected_puskesmas:
        st.warning("Silakan pilih setidaknya satu puskesmas untuk ditampilkan di grafik.")
    else:
        filtered_ciaf_by_area = ciaf_by_area[ciaf_by_area["Area (Puskesmas)"].isin(selected_puskesmas)]

        # Buat grafik grouped bar chart menggunakan Plotly
        fig = go.Figure()

        # Tambahkan batang untuk Prevalensi CIAF
        fig.add_trace(go.Bar(
            x=filtered_ciaf_by_area["Area (Puskesmas)"],
            y=filtered_ciaf_by_area["Prevalensi CIAF (%)"],
            name="CIAF",
            marker_color="blue",
            text=filtered_ciaf_by_area["Prevalensi CIAF (%)"],
            textposition="auto",
            texttemplate="%{text:.2f}%"
        ))

        # Tambahkan batang untuk Prevalensi Stunting
        fig.add_trace(go.Bar(
            x=filtered_ciaf_by_area["Area (Puskesmas)"],
            y=filtered_ciaf_by_area["Prevalensi Stunting (%)"],
            name="Stunting",
            marker_color="green",
            text=filtered_ciaf_by_area["Prevalensi Stunting (%)"],
            textposition="auto",
            texttemplate="%{text:.2f}%"
        ))

        # Tambahkan batang untuk Prevalensi Underweight
        fig.add_trace(go.Bar(
            x=filtered_ciaf_by_area["Area (Puskesmas)"],
            y=filtered_ciaf_by_area["Prevalensi Underweight (%)"],
            name="Underweight",
            marker_color="orange",
            text=filtered_ciaf_by_area["Prevalensi Underweight (%)"],
            textposition="auto",
            texttemplate="%{text:.2f}%"
        ))

        # Tambahkan batang untuk Prevalensi Wasting
        fig.add_trace(go.Bar(
            x=filtered_ciaf_by_area["Area (Puskesmas)"],
            y=filtered_ciaf_by_area["Prevalensi Wasting (%)"],
            name="Wasting",
            marker_color="red",
            text=filtered_ciaf_by_area["Prevalensi Wasting (%)"],
            textposition="auto",
            texttemplate="%{text:.2f}%"
        ))

        # Update layout
        fig.update_layout(
            title="Perbandingan Prevalensi CIAF, Stunting, Underweight, dan Wasting Berdasarkan Area (Puskesmas)",
            xaxis_title="Area (Puskesmas)",
            yaxis_title="Prevalensi (%)",
            barmode="group",  # Mode grouped bar chart
            xaxis_tickangle=-45,
            yaxis=dict(range=[0, 100]),
            showlegend=True,
            legend_title="Kategori",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="white",
            font=dict(size=12),
            height=500,
            margin=dict(b=150)  # Beri ruang lebih untuk label sumbu X
        )

        # Tampilkan grafik
        st.plotly_chart(fig, use_container_width=True)

    # Visualisasi Prevalensi CIAF berdasarkan Kelompok Usia menggunakan Plotly
    st.write("#### Grafik Prevalensi CIAF Berdasarkan Kelompok Usia")
    fig = px.bar(
        ciaf_by_age,
        x="Kelompok Usia",
        y="Prevalensi CIAF (%)",
        title="Prevalensi CIAF Berdasarkan Kelompok Usia",
        color="Kelompok Usia",
        color_discrete_sequence=px.colors.qualitative.Plotly,
        text="Prevalensi CIAF (%)",
    )

    fig.update_traces(
        texttemplate="%{text:.2f}%",
        textposition="auto",
        marker=dict(line=dict(color="#000000", width=1)),
    )

    fig.update_layout(
        xaxis_title="Kelompok Usia",
        yaxis_title="Prevalensi CIAF (%)",
        title_x=0.5,
        height=500,
        showlegend=True,
        legend_title="Kelompok Usia",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white",
        font=dict(size=12),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Insight berdasarkan hasil CIAF
    st.write("#### Insight dari Analisis CIAF")
    st.markdown("""
        - **Prevalensi Tinggi:** Jika prevalensi CIAF keseluruhan tinggi (misalnya, >50%), ini menunjukkan beban gizi buruk yang signifikan di populasi ini. Sebagai perbandingan, studi di Bogor District pada 2019 menunjukkan prevalensi CIAF sekitar 70%, yang mengindikasikan masalah gizi yang serius.
        - **Kelompok Rentan:** Kelompok usia atau area dengan prevalensi CIAF tertinggi, terutama yang memiliki banyak anak di kategori D (wasting, underweight, stunting), perlu menjadi prioritas intervensi. Anak-anak dengan kegagalan ganda/tiga memiliki risiko morbiditas dan mortalitas yang jauh lebih tinggi.
        - **Pola Kegagalan:** Jika kategori F (hanya stunting) atau Y (stunting dan underweight) mendominasi, ini menunjukkan masalah gizi kronis yang mungkin terkait dengan asupan gizi jangka panjang, sanitasi, atau pendidikan ibu. Jika kategori B (hanya wasting) atau C (wasting dan underweight) mendominasi, ini menunjukkan masalah gizi akut yang mungkin terkait dengan kekurangan pangan sementara atau penyakit.
        - **Implikasi Kebijakan:** Data CIAF dapat digunakan untuk mendukung program gizi lokal, seperti menargetkan intervensi pada puskesmas dengan prevalensi CIAF tertinggi. Misalnya, jika puskesmas memiliki prevalensi CIAF yang sangat tinggi, intervensi gizi tambahan dapat difokuskan di area tersebut.
    """, unsafe_allow_html=True)

    # Bagian 3: Analisis Longitudinal Pertumbuhan Balita
    st.write("### Analisis Longitudinal Pertumbuhan Balita")

    # Tambahkan informasi tentang analisis longitudinal
    with st.expander("📜 Definisi dan Insight Analisis Longitudinal", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Definisi Operasional dan Insight Analisis Longitudinal

            Berikut adalah definisi operasional, metode analisis, serta insight dari Analisis Longitudinal Pertumbuhan Balita dalam Elektronik Pencatatan dan Pelaporan Gizi Berbasis Masyarakat (EPPGBM). Analisis ini melacak pola pertumbuhan balita dari waktu ke waktu untuk memahami perkembangan status gizi mereka.

            #### Definisi Operasional
            Analisis Longitudinal Pertumbuhan Balita melacak perkembangan Z-Score tiga indikator utama status gizi—Berat Badan menurut Umur (BB/U), Tinggi Badan menurut Umur (TB/U), dan Berat Badan menurut Tinggi Badan (BB/TB)—dari periode pengukuran awal hingga periode terbaru. Analisis ini terdiri dari dua bagian:
            - **Analisis Per Individu:** Melacak pola pertumbuhan balita spesifik berdasarkan Nomor Induk Kependudukan (NIK).
            - **Tren Keseluruhan:** Menunjukkan pola rata-rata Z-Score untuk semua balita dari usia 0 hingga 60 bulan.

            Data diidentifikasi menggunakan NIK untuk memastikan pengukuran berulang pada balita yang sama (untuk analisis per individu). Pola pertumbuhan divisualisasikan terhadap umur balita (dalam bulan) dengan acuan standar WHO:
            - **Z-Score 0:** Median populasi sehat menurut standar WHO.
            - **Z-Score -2:** Batas bawah untuk underweight (BB/U), stunting (TB/U), atau wasting (BB/TB).

            #### Metode Pengumpulan Data
            Data diambil dari kolom `nik`, `periode`, `usia_bulan`, `ZS_BBU`, `ZS_TBU`, dan `ZS_BBTB` dalam dataset EPPGBM. Untuk analisis per individu, dataset difilter untuk memilih balita yang memiliki pengukuran di lebih dari satu periode, kemudian diurutkan berdasarkan periode. Untuk tren keseluruhan, Z-Score dirata-ratakan berdasarkan umur balita (dalam bulan) untuk semua balita.

            #### Insight Analisis
            Analisis ini memberikan gambaran tentang perkembangan status gizi balita dari waktu ke waktu:
            - **Analisis Per Individu:** Memungkinkan identifikasi pola pertumbuhan spesifik untuk setiap balita, seperti penurunan Z-Score yang signifikan atau pemulihan setelah intervensi.
            - **Tren Keseluruhan:** Memberikan gambaran umum tentang status gizi populasi balita, seperti apakah Z-Score rata-rata cenderung menurun pada usia tertentu (misalnya, saat transisi dari menyusui ke makanan padat).
            - **Kelompok Rentan:** Balita atau kelompok usia dengan Z-Score yang terus berada di bawah -2 pada salah satu atau semua indikator perlu menjadi prioritas intervensi.
            - **Intervensi:** Pola pertumbuhan yang menurun dapat diintervensi sejak dini, misalnya dengan pemberian makanan tambahan, edukasi gizi untuk ibu, atau perbaikan sanitasi.

            Analisis ini membantu mengidentifikasi balita atau kelompok usia yang membutuhkan intervensi gizi sejak dini untuk mencegah dampak jangka panjang seperti stunting atau morbiditas.

            #### Penjelasan Sederhana
            Analisis ini seperti "buku harian" pertumbuhan anak. Bagian pertama (per individu) melihat perkembangan masing-masing anak, sedangkan bagian kedua (tren keseluruhan) melihat gambaran besar untuk semua anak. Jika garis Z-Score terus di bawah garis merah (-2), artinya banyak anak bermasalah dan butuh bantuan segera.

            </div>
        """, unsafe_allow_html=True)

    # Pastikan kolom yang diperlukan ada di dataset
    required_longitudinal_columns = ["nik", "periode", "usia_bulan", "ZS_BBU", "ZS_TBU", "ZS_BBTB"]
    missing_longitudinal_columns = [col for col in required_longitudinal_columns if col not in filtered_df.columns]
    if missing_longitudinal_columns:
        st.error(f"Kolom berikut tidak ditemukan di dataset untuk analisis longitudinal: {', '.join(missing_longitudinal_columns)}. Silakan periksa data.")
        return

    # Filter balita yang memiliki data di lebih dari satu periode
    nik_counts = filtered_df["nik"].value_counts()
    longitudinal_niks = nik_counts[nik_counts > 1].index
    longitudinal_df = filtered_df[filtered_df["nik"].isin(longitudinal_niks)]

    if longitudinal_df.empty:
        st.warning("⚠️ Tidak ada data longitudinal yang ditemukan (tidak ada balita dengan pengukuran di lebih dari satu periode). Analisis per individu tidak dapat dilakukan.")
    else:
        # Urutkan data berdasarkan periode
        def parse_periode(periode_str):
            try:
                month, year = periode_str.split("_")
                month_num = {
                    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
                    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12
                }[month.lower()]  # Gunakan .lower() untuk menangani huruf besar/kecil
                return pd.to_datetime(f"{year}-{month_num:02d}-01")
            except:
                return pd.to_datetime("1900-01-01")  # Default untuk data yang tidak valid

        longitudinal_df = longitudinal_df.copy()
        longitudinal_df["periode_dt"] = longitudinal_df["periode"].apply(parse_periode)
        longitudinal_df = longitudinal_df.sort_values(["nik", "periode_dt"])

        # Pilih balita spesifik untuk visualisasi
        st.write("#### Pilih Balita untuk Analisis Longitudinal (Per Individu)")
        nik_options = ["All"] + sorted(longitudinal_df["nik"].unique().tolist())
        selected_nik = st.selectbox("Pilih NIK Balita", nik_options)

        if selected_nik == "All":
            st.warning("Silakan pilih NIK spesifik untuk melihat pola pertumbuhan individu.")
        else:
            # Filter data untuk balita yang dipilih
            balita_df = longitudinal_df[longitudinal_df["nik"] == selected_nik]

            # Pastikan data tidak kosong
            if balita_df.empty:
                st.warning(f"Tidak ada data untuk NIK {selected_nik}. Silakan pilih NIK lain.")
            else:
                # Visualisasi pola pertumbuhan
                st.write(f"#### Pola Pertumbuhan Balita (NIK: {selected_nik})")

                # Buat grafik garis menggunakan Plotly
                fig = go.Figure()

                # Tambahkan garis untuk ZS_BBU
                fig.add_trace(go.Scatter(
                    x=balita_df["usia_bulan"],
                    y=balita_df["ZS_BBU"],
                    mode="lines+markers",
                    name="BB/U (Z-Score)",
                    line=dict(color="blue"),
                    marker=dict(size=8)
                ))

                # Tambahkan garis untuk ZS_TBU
                fig.add_trace(go.Scatter(
                    x=balita_df["usia_bulan"],
                    y=balita_df["ZS_TBU"],
                    mode="lines+markers",
                    name="TB/U (Z-Score)",
                    line=dict(color="green"),
                    marker=dict(size=8)
                ))

                # Tambahkan garis untuk ZS_BBTB
                fig.add_trace(go.Scatter(
                    x=balita_df["usia_bulan"],
                    y=balita_df["ZS_BBTB"],
                    mode="lines+markers",
                    name="BB/TB (Z-Score)",
                    line=dict(color="orange"),
                    marker=dict(size=8)
                ))

                # Tambahkan garis acuan WHO
                fig.add_shape(
                    type="line",
                    x0=0,
                    x1=60,
                    y0=0,
                    y1=0,
                    line=dict(color="gray", dash="dash"),
                    name="Median WHO (Z=0)"
                )
                fig.add_shape(
                    type="line",
                    x0=0,
                    x1=60,
                    y0=-2,
                    y1=-2,
                    line=dict(color="red", dash="dash"),
                    name="Batas Bawah (Z=-2)"
                )

                # Update layout
                fig.update_layout(
                    title=f"Pola Pertumbuhan Balita (NIK: {selected_nik})",
                    xaxis_title="Umur (Bulan)",
                    yaxis_title="Z-Score",
                    xaxis=dict(range=[0, 60]),
                    yaxis=dict(range=[-3.5, 3.5]),
                    showlegend=True,
                    legend_title="Indikator",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    plot_bgcolor="white",
                    font=dict(size=12),
                    height=500,
                    annotations=[
                        dict(
                            x=62,
                            y=0,
                            text="Median WHO (Z=0)",
                            showarrow=False,
                            xanchor="left",
                            font=dict(color="gray")
                        ),
                        dict(
                            x=62,
                            y=-2,
                            text="Batas Bawah (Z=-2)",
                            showarrow=False,
                            xanchor="left",
                            font=dict(color="red")
                        )
                    ]
                )

                # Tampilkan grafik
                st.plotly_chart(fig, use_container_width=True)

                # Insight berdasarkan pola pertumbuhan
                st.write("#### Insight dari Pola Pertumbuhan (Per Individu)")
                st.markdown("""
                    - **BB/U (Berat Badan menurut Umur):** Jika Z-Score BB/U terus menurun dan berada di bawah -2, ini menunjukkan risiko underweight yang meningkat. Intervensi seperti pemberian makanan tambahan diperlukan.
                    - **TB/U (Tinggi Badan menurut Umur):** Jika Z-Score TB/U terus di bawah -2, ini mengindikasikan stunting yang berkelanjutan. Intervensi jangka panjang seperti edukasi gizi untuk ibu dan perbaikan sanitasi diperlukan.
                    - **BB/TB (Berat Badan menurut Tinggi Badan):** Jika Z-Score BB/TB di bawah -2, ini menunjukkan wasting (gizi buruk akut). Intervensi segera seperti pemberian terapi gizi diperlukan.
                    - **Rekomendasi Umum:** Jika salah satu atau semua indikator berada di bawah -2 untuk waktu yang lama, intervensi harus dimulai sejak dini, bahkan sejak ibu hamil, untuk mencegah dampak jangka panjang seperti stunting atau morbiditas.
                """, unsafe_allow_html=True)

    # Bagian Tren Keseluruhan
    st.write("#### Tren Keseluruhan Pertumbuhan Balita (Semua Balita)")

    # Hitung rata-rata Z-Score per umur (dalam bulan)
    trend_df = filtered_df.groupby("usia_bulan").agg({
        "ZS_BBU": "mean",
        "ZS_TBU": "mean",
        "ZS_BBTB": "mean"
    }).reset_index()

    # Pastikan data tidak kosong
    if trend_df.empty:
        st.warning("⚠️ Tidak ada data untuk menghitung tren keseluruhan. Silakan periksa data.")
    else:
        # Grafik 1: Tren ZS_BBU
        fig_bbu = go.Figure()
        fig_bbu.add_trace(go.Scatter(
            x=trend_df["usia_bulan"],
            y=trend_df["ZS_BBU"],
            mode="lines",
            name="Rata-rata BB/U (Z-Score)",
            line=dict(color="blue")
        ))
        fig_bbu.add_shape(
            type="line",
            x0=0,
            x1=60,
            y0=0,
            y1=0,
            line=dict(color="gray", dash="dash"),
            name="Median WHO (Z=0)"
        )
        fig_bbu.add_shape(
            type="line",
            x0=0,
            x1=60,
            y0=-2,
            y1=-2,
            line=dict(color="red", dash="dash"),
            name="Batas Bawah (Z=-2)"
        )
        fig_bbu.update_layout(
            title="Tren Rata-rata Z-Score BB/U (Berat Badan menurut Umur)",
            xaxis_title="Umur (Bulan)",
            yaxis_title="Z-Score",
            xaxis=dict(range=[0, 60]),
            yaxis=dict(range=[-3.5, 3.5]),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="white",
            font=dict(size=12),
            height=400,
            annotations=[
                dict(
                    x=62,
                    y=0,
                    text="Median WHO (Z=0)",
                    showarrow=False,
                    xanchor="left",
                    font=dict(color="gray")
                ),
                dict(
                    x=62,
                    y=-2,
                    text="Batas Bawah (Z=-2)",
                    showarrow=False,
                    xanchor="left",
                    font=dict(color="red")
                )
            ]
        )
        st.plotly_chart(fig_bbu, use_container_width=True)

        # Grafik 2: Tren ZS_TBU
        fig_tbu = go.Figure()
        fig_tbu.add_trace(go.Scatter(
            x=trend_df["usia_bulan"],
            y=trend_df["ZS_TBU"],
            mode="lines",
            name="Rata-rata TB/U (Z-Score)",
            line=dict(color="green")
        ))
        fig_tbu.add_shape(
            type="line",
            x0=0,
            x1=60,
            y0=0,
            y1=0,
            line=dict(color="gray", dash="dash"),
            name="Median WHO (Z=0)"
        )
        fig_tbu.add_shape(
            type="line",
            x0=0,
            x1=60,
            y0=-2,
            y1=-2,
            line=dict(color="red", dash="dash"),
            name="Batas Bawah (Z=-2)"
        )
        fig_tbu.update_layout(
            title="Tren Rata-rata Z-Score TB/U (Tinggi Badan menurut Umur)",
            xaxis_title="Umur (Bulan)",
            yaxis_title="Z-Score",
            xaxis=dict(range=[0, 60]),
            yaxis=dict(range=[-3.5, 3.5]),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="white",
            font=dict(size=12),
            height=400,
            annotations=[
                dict(
                    x=62,
                    y=0,
                    text="Median WHO (Z=0)",
                    showarrow=False,
                    xanchor="left",
                    font=dict(color="gray")
                ),
                dict(
                    x=62,
                    y=-2,
                    text="Batas Bawah (Z=-2)",
                    showarrow=False,
                    xanchor="left",
                    font=dict(color="red")
                )
            ]
        )
        st.plotly_chart(fig_tbu, use_container_width=True)

        # Grafik 3: Tren ZS_BBTB
        fig_bbtb = go.Figure()
        fig_bbtb.add_trace(go.Scatter(
            x=trend_df["usia_bulan"],
            y=trend_df["ZS_BBTB"],
            mode="lines",
            name="Rata-rata BB/TB (Z-Score)",
            line=dict(color="orange")
        ))
        fig_bbtb.add_shape(
            type="line",
            x0=0,
            x1=60,
            y0=0,
            y1=0,
            line=dict(color="gray", dash="dash"),
            name="Median WHO (Z=0)"
        )
        fig_bbtb.add_shape(
            type="line",
            x0=0,
            x1=60,
            y0=-2,
            y1=-2,
            line=dict(color="red", dash="dash"),
            name="Batas Bawah (Z=-2)"
        )
        fig_bbtb.update_layout(
            title="Tren Rata-rata Z-Score BB/TB (Berat Badan menurut Tinggi Badan)",
            xaxis_title="Umur (Bulan)",
            yaxis_title="Z-Score",
            xaxis=dict(range=[0, 60]),
            yaxis=dict(range=[-3.5, 3.5]),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="white",
            font=dict(size=12),
            height=400,
            annotations=[
                dict(
                    x=62,
                    y=0,
                    text="Median WHO (Z=0)",
                    showarrow=False,
                    xanchor="left",
                    font=dict(color="gray")
                ),
                dict(
                    x=62,
                    y=-2,
                    text="Batas Bawah (Z=-2)",
                    showarrow=False,
                    xanchor="left",
                    font=dict(color="red")
                )
            ]
        )
        st.plotly_chart(fig_bbtb, use_container_width=True)

        # Insight berdasarkan tren keseluruhan
        st.write("#### Insight dari Tren Keseluruhan")
        st.markdown("""
            - **BB/U (Berat Badan menurut Umur):** Jika tren rata-rata Z-Score BB/U menurun dan berada di bawah -2 pada usia tertentu (misalnya, 12-24 bulan), ini menunjukkan risiko underweight yang meningkat pada kelompok usia tersebut. Intervensi seperti pemberian makanan tambahan atau program gizi di posyandu dapat difokuskan pada kelompok usia ini.
            - **TB/U (Tinggi Badan menurut Umur):** Jika tren rata-rata Z-Score TB/U terus di bawah -2, ini mengindikasikan stunting yang meluas di populasi. Intervensi jangka panjang seperti edukasi gizi untuk ibu, peningkatan akses ke pangan bergizi, dan perbaikan sanitasi diperlukan.
            - **BB/TB (Berat Badan menurut Tinggi Badan):** Jika tren rata-rata Z-Score BB/TB di bawah -2, ini menunjukkan wasting (gizi buruk akut) yang meluas. Intervensi segera seperti pemberian terapi gizi atau makanan tambahan darurat diperlukan.
            - **Kelompok Usia Kritis:** Perhatikan kelompok usia di mana Z-Score rata-rata turun di bawah -2, karena ini adalah periode kritis yang memerlukan intervensi segera. Misalnya, jika Z-Score TB/U turun di bawah -2 pada usia 6-12 bulan, ini bisa terkait dengan transisi dari menyusui ke makanan padat yang kurang memadai.
            - **Rekomendasi Umum:** Tren keseluruhan ini dapat digunakan untuk merancang program gizi yang menargetkan kelompok usia tertentu atau area dengan masalah gizi yang signifikan (berdasarkan analisis CIAF sebelumnya).
        """, unsafe_allow_html=True)
        
def show_daftar_balita_bermasalah_gizi(df):
    st.write("## Daftar Balita Bermasalah Gizi")

    # Tambahkan informasi tentang daftar balita bermasalah gizi
    with st.expander("📜 Informasi tentang Daftar Balita Bermasalah Gizi", expanded=False):
        st.markdown("""
            <div style="background-color: #E6F0FA; padding: 20px; border-radius: 10px;">
            
            ### 📜 Informasi tentang Daftar Balita Bermasalah Gizi

            Rekapitulasi data balita bermasalah gizi ini disusun **khusus untuk kepentingan intervensi gizi** dalam rangka meningkatkan status gizi anak balita. Data ini bersifat rahasia dan hanya boleh digunakan oleh pihak yang berwenang, seperti Dinas Kesehatan, Puskesmas, atau petugas gizi yang memiliki izin resmi.

            #### Aspek Keamanan dan Privasi Data
            Penggunaan data ini harus sesuai dengan ketentuan **Undang-Undang Privasi Kesehatan** yang berlaku di Indonesia, termasuk Undang-Undang Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP). **Dilarang menyebarluaskan, mempublikasikan, atau menggunakan data tanpa sepengetahuan dan rekomendasi Dinas Kesehatan atau perizinan resmi dari Puskesmas**. Pelanggaran terhadap ketentuan ini dapat dikenakan sanksi administratif, gugatan perdata, atau pidana sesuai hukum yang berlaku.

            #### Isi Data
            Data ini memuat daftar balita bermasalah gizi berdasarkan kategori **Composite Index of Anthropometric Failure (CIAF)**, yang mengklasifikasikan kegagalan antropometri sebagai berikut:
            - **Kategori B:** Hanya wasting (berat badan menurut tinggi badan rendah, ZS_BBTB < -2).
            - **Kategori C:** Wasting dan underweight (berat badan menurut umur rendah, ZS_BBU < -2).
            - **Kategori D:** Wasting, underweight, dan stunting (tinggi badan menurut umur rendah, ZS_TBU < -2).
            - **Kategori E:** Hanya underweight.
            - **Kategori F:** Hanya stunting.
            - **Kategori Y:** Stunting dan underweight.

            Balita dalam kategori B-Y dianggap bermasalah gizi dan memerlukan intervensi segera. Data ini mencakup informasi seperti NIK, nama balita, jenis kelamin, tanggal lahir, nama orang tua, puskesmas, alamat, tanggal pengukuran, berat badan, tinggi badan, Z-Score, dan klasifikasi status gizi.

            #### Tujuan Penggunaan
            Data ini digunakan untuk:
            - Mengidentifikasi balita yang memerlukan intervensi gizi segera.
            - Merancang program intervensi yang tepat sasaran, seperti pemberian makanan tambahan, edukasi gizi untuk orang tua, atau perbaikan sanitasi.
            - Memantau perkembangan status gizi balita dari waktu ke waktu.

            **Peringatan:** Pengguna data bertanggung jawab penuh untuk menjaga kerahasiaan dan mencegah akses, penyebaran, atau penggunaan data yang tidak sah. Pastikan data hanya digunakan untuk kepentingan intervensi gizi dan sesuai dengan ketentuan hukum.

            </div>
        """, unsafe_allow_html=True)

    # Tambahkan filter untuk periode, puskesmas, dan kelurahan
    st.sidebar.subheader("🔍 Filter Data")
    # Filter Periode
    if "periode" in df.columns:
        periode_options = ["All"] + sorted(df["periode"].dropna().unique().tolist())
        if not periode_options or len(periode_options) <= 1:
            st.sidebar.warning("⚠️ Kolom 'periode' tidak memiliki data unik yang valid selain 'All'. Periksa dataset.")
    else:
        periode_options = ["All"]
        st.sidebar.warning("⚠️ Kolom 'periode' tidak ditemukan di dataset. Filter default ke 'All'.")
    selected_periode = st.sidebar.selectbox("Pilih Periode Pengukuran", periode_options)

    # Filter Puskesmas
    puskesmas_options = ["All"] + sorted(df["puskesmas"].unique().tolist()) if "puskesmas" in df.columns else ["All"]
    selected_puskesmas = st.sidebar.selectbox("Pilih Puskesmas", puskesmas_options)

    # Filter Kelurahan
    kelurahan_options = ["All"] + sorted(df["kelurahan"].unique().tolist()) if "kelurahan" in df.columns else ["All"]
    selected_kelurahan = st.sidebar.selectbox("Pilih Kelurahan", kelurahan_options)

    # Filter dataset berdasarkan pilihan
    filtered_df = df.copy()
    if selected_periode != "All":
        filtered_df = filtered_df[filtered_df["periode"] == selected_periode]
    if selected_puskesmas != "All":
        filtered_df = filtered_df[filtered_df["puskesmas"] == selected_puskesmas]
    if selected_kelurahan != "All":
        filtered_df = filtered_df[filtered_df["kelurahan"] == selected_kelurahan]

    # Pastikan kolom Z-Score yang diperlukan ada
    required_zscore_columns = ["ZS_BBU", "ZS_TBU", "ZS_BBTB"]
    missing_zscore_columns = [col for col in required_zscore_columns if col not in filtered_df.columns]
    if missing_zscore_columns:
        st.error(f"Kolom Z-Score berikut tidak ditemukan di dataset: {', '.join(missing_zscore_columns)}. Silakan periksa data.")
        return
    
    # Hitung CIAF_Category jika belum ada
    if "CIAF_Category" not in filtered_df.columns:
        filtered_df["CIAF_Category"] = filtered_df.apply(classify_ciaf, axis=1)

    # Pastikan semua kolom yang diperlukan ada di dataset
    required_columns = [
        "nik", "nama_balita", "jk", "Tgl_Lahir", "Nama_Ortu", "puskesmas", "alamat",
        "Tgl_ukur", "bb", "tinggi", "ZS_BBU", "BBU", "ZS_TBU", "TBU", "ZS_BBTB", "BBTB"
    ]
    missing_columns = [col for col in required_columns if col not in filtered_df.columns]
    if missing_columns:
        st.error(f"Kolom berikut tidak ditemukan di dataset: {', '.join(missing_columns)}. Silakan periksa data.")
        return

    # Filter balita bermasalah gizi (kategori B, C, D, E, F, Y)
    problem_categories = ["B", "C", "D", "E", "F", "Y"]
    problem_df = filtered_df[filtered_df["CIAF_Category"].isin(problem_categories)]

    if problem_df.empty:
        st.warning("⚠️ Tidak ada balita bermasalah gizi (kategori B-Y) dalam data yang difilter. Silakan periksa data atau filter.")
        return

    # Tampilkan peringatan dan checkbox untuk konfirmasi kebijakan privasi
    st.markdown("""
        <div style="background-color: #FFF3CD; padding: 15px; border-radius: 10px; border: 1px solid #FFECB3;">
        <strong>⚠️ Peringatan:</strong> Mengunduh data dan informasi individu bertaraf penggunaan, penyebaran, dan pengubahan data pribadi yang tidak sah dan tidak bertanggungjawab. Setiap orang yang menyalahgunakan data pribadi orang lain berpotensi bertanggung jawab secara hukum berupa sanksi administratif, gugatan perdata, atau pidana. Saya memahami risiko pengunduhan data, dan bertanggung jawab untuk menjaga dari akses, penyebaran, dan penggunaan data yang tidak sah terhadap data yang saya unduh.
        </div>
    """, unsafe_allow_html=True)

    agree_to_policy = st.checkbox("Saya setuju dengan kebijakan privasi dan bertanggung jawab atas penggunaan data yang saya unduh.")

    # Buat layout grid untuk tombol download
    st.write("### Unduh Daftar Balita Bermasalah Gizi Berdasarkan Kategori CIAF")
    categories = {
        "B": "Hanya Wasting",
        "C": "Wasting dan Underweight",
        "D": "Wasting, Underweight, dan Stunting",
        "E": "Hanya Underweight",
        "F": "Hanya Stunting",
        "Y": "Stunting dan Underweight"
    }

    # Buat grid 3 kolom (2 tombol per baris)
    cols = st.columns(3)
    for idx, (category, description) in enumerate(categories.items()):
        with cols[idx % 3]:
            # Buat card untuk setiap kategori
            st.markdown(
                f"""
                <div style="background-color: #F8F9FA; padding: 15px; border-radius: 10px; border: 1px solid #DEE2E6; text-align: center; margin-bottom: 10px;">
                    <h4 style="margin: 0; color: #343A40;">Kategori {category}</h4>
                    <p style="color: #6C757D;">{description}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Filter data untuk kategori ini
            category_df = problem_df[problem_df["CIAF_Category"] == category]

            if category_df.empty:
                st.info(f"Tidak ada data untuk Kategori {category}.")
            else:
                # Siapkan data untuk file Excel
                export_df = category_df[[
                    "nik", "nama_balita", "jk", "Tgl_Lahir", "Nama_Ortu", "puskesmas", "alamat",
                    "Tgl_ukur", "bb", "tinggi", "ZS_BBU", "BBU", "ZS_TBU", "TBU", "ZS_BBTB", "BBTB"
                ]].copy()

                # Tambahkan kolom nomor urut
                export_df.reset_index(drop=True, inplace=True)
                export_df.insert(0, "no", export_df.index + 1)

                # Ubah nama kolom sesuai permintaan
                export_df.columns = [
                    "No", "NIK", "Nama Balita", "Jenis Kelamin", "Tanggal Lahir", "Nama Orang Tua",
                    "Puskesmas", "Alamat", "Tanggal Ukur", "Berat Badan", "Tinggi Badan",
                    "ZScore BBU", "Klasifikasi BBU", "ZScore TBU", "Klasifikasi TBU",
                    "ZScore BBTB", "Klasifikasi BBTB"
                ]

                # Konversi DataFrame ke file Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    export_df.to_excel(writer, index=False, sheet_name=f"Kategori_{category}")
                    # Dapatkan workbook dan worksheet untuk styling (opsional)
                    workbook = writer.book
                    worksheet = writer.sheets[f"Kategori_{category}"]
                    # Atur lebar kolom otomatis (opsional)
                    for col_num, col_name in enumerate(export_df.columns):
                        max_len = max(
                            export_df[col_name].astype(str).map(len).max(),
                            len(col_name)
                        )
                        worksheet.set_column(col_num, col_num, max_len + 2)

                excel_data = output.getvalue()

                # Tombol download
                if agree_to_policy:
                    st.download_button(
                        label=f"Unduh Kategori {category}",
                        data=excel_data,
                        file_name=f"Daftar_Balita_Bermasalah_Gizi_Kategori_{category}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"download_{category}"
                    )
                else:
                    st.button(
                        label=f"Unduh Kategori {category}",
                        disabled=True,
                        help="Harap setujui kebijakan privasi terlebih dahulu."
                    )
# Sidebar untuk memilih submenu Analisis Longitudinal
def analisis_longitudinal_balita(df):
    st.subheader("📈 Analisis Longitudinal Balita")

    # 1. Validasi Awal dan Persiapan Data
    required_columns = ["nik", "periode", "puskesmas", "kelurahan", "ZS_TBU", "Tgl_ukur", "Tgl_Lahir"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"Kolom berikut tidak ditemukan di dataset: {', '.join(missing_columns)}. Silakan periksa data.")
        return

    # 2. Pilihan Periode Awal dan Akhir
    st.sidebar.subheader("🔍 Filter Periode Analisis Longitudinal")
    periode_options = sorted(df["periode"].dropna().unique().tolist())
    if len(periode_options) < 2:
        st.sidebar.warning("⚠️ Dataset hanya memiliki satu periode. Analisis longitudinal memerlukan minimal dua periode.")
        return

    periode_awal = st.sidebar.selectbox("Pilih Periode Awal", periode_options, index=0, key="periode_awal_longitudinal")
    periode_akhir_options = [p for p in periode_options if p > periode_awal]
    if not periode_akhir_options:
        st.sidebar.warning("⚠️ Tidak ada periode setelah periode awal yang dipilih. Silakan pilih periode awal yang lebih awal.")
        return
    periode_akhir = st.sidebar.selectbox("Pilih Periode Akhir", periode_akhir_options, index=len(periode_akhir_options)-1, key="periode_akhir_longitudinal")

    # 3. Filter Dataset Berdasarkan Periode
    df_filtered = df[df["periode"].isin([periode_awal, periode_akhir])].copy()

    # 4. Menghitung Usia dalam Bulan
    try:
        df_filtered["usia_bulan"] = ((pd.to_datetime(df_filtered["Tgl_ukur"]) - pd.to_datetime(df_filtered["Tgl_Lahir"])) / pd.Timedelta(days=30.4375)).astype(int)
        df_filtered["usia_bulan"] = df_filtered["usia_bulan"].fillna(0).clip(lower=0)
    except Exception as e:
        st.error(f"⚠️ Gagal menghitung usia_bulan: {str(e)}. Pastikan kolom 'Tgl_ukur' dan 'Tgl_Lahir' memiliki format tanggal yang valid.")
        return

    # 5. Filter Balita untuk Analisis Longitudinal
    nik_counts = df_filtered["nik"].value_counts()
    longitudinal_niks = nik_counts.index
    df_longitudinal = df_filtered[df_filtered["nik"].isin(longitudinal_niks)]

    # 6. Menambahkan Status Stunting
    df_longitudinal["is_stunting"] = (df_longitudinal["ZS_TBU"] < -2).fillna(False)

    # 7. Pisahkan Data untuk Periode Awal dan Akhir
    df_awal = df_longitudinal[df_longitudinal["periode"] == periode_awal]
    df_akhir = df_longitudinal[df_longitudinal["periode"] == periode_akhir]

    # 8. Filter Berdasarkan Puskesmas dan Kelurahan
    st.sidebar.subheader("🔍 Filter Lokasi")
    puskesmas_options = ["All"] + sorted(df_longitudinal["puskesmas"].unique().tolist())
    selected_puskesmas = st.sidebar.selectbox("Pilih Puskesmas", puskesmas_options, key="puskesmas_longitudinal")

    if selected_puskesmas != "All":
        kelurahan_options = ["All"] + sorted(df_longitudinal[df_longitudinal["puskesmas"] == selected_puskesmas]["kelurahan"].unique().tolist())
        selected_kelurahan = st.sidebar.selectbox("Pilih Kelurahan", kelurahan_options, key="kelurahan_longitudinal")
    else:
        selected_kelurahan = "All"

    if selected_puskesmas != "All":
        df_awal = df_awal[df_awal["puskesmas"] == selected_puskesmas]
        df_akhir = df_akhir[df_akhir["puskesmas"] == selected_puskesmas]
    if selected_kelurahan != "All":
        df_awal = df_awal[df_awal["kelurahan"] == selected_kelurahan]
        df_akhir = df_akhir[df_akhir["kelurahan"] == selected_kelurahan]

    # 9. Submenu Analisis
    st.sidebar.subheader("📊 Submenu Analisis Longitudinal")
    submenu_options = [
        "Analisis Tabulasi Data Longitudinal Balita Stunting",
        "Grafik Analisis Data Longitudinal Balita Stunting"
    ]
    selected_submenu = st.sidebar.radio("Pilih Submenu Analisis", submenu_options, key="submenu_longitudinal")

    # 10. Fungsi untuk Menghitung Selisih Bulan Antar Periode
    def calculate_month_diff(periode1, periode2):
        month_map = {
            "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
            "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12
        }
        try:
            month1, year1 = periode1.split("_")
            month2, year2 = periode2.split("_")
            m1 = month_map[month1.lower()]
            m2 = month_map[month2.lower()]
            y1, y2 = int(year1), int(year2)
            return (y2 * 12 + m2) - (y1 * 12 + m1)
        except:
            return 6

    month_diff = calculate_month_diff(periode_awal, periode_akhir)

    # Fungsi untuk mengelompokkan usia ke dalam kategori
    def categorize_age_group(age_in_months):
        if 0 <= age_in_months <= 5:
            return "0-5 bulan"
        elif 6 <= age_in_months <= 11:
            return "6-11 bulan"
        elif 12 <= age_in_months <= 23:
            return "12-23 bulan"
        elif 24 <= age_in_months <= 35:
            return "24-35 bulan"
        elif 36 <= age_in_months <= 47:
            return "36-47 bulan"
        elif 48 <= age_in_months <= 59:
            return "48-59 bulan"
        else:
            return "Lainnya"

    # Fungsi untuk menghitung distribusi kasus berdasarkan kelompok usia
    def calculate_age_distribution(df, stunting_col, group_by_col="puskesmas", category=""):
        if "usia_bulan" not in df.columns:
            return pd.DataFrame()

        df["age_group"] = df["usia_bulan"].apply(categorize_age_group)
        df_stunting = df[df[stunting_col] == True]
        age_dist = df_stunting.groupby([group_by_col, "age_group"]).size().unstack(fill_value=0)

        # Hitung total kasus per puskesmas (akan menjadi denominator)
        total_per_puskesmas = age_dist.sum(axis=1)

        # Hitung persentase berdasarkan total kasus per puskesmas
        age_dist_percentage = (age_dist.div(total_per_puskesmas, axis=0) * 100).round(2)

        # Buat DataFrame hasil
        result_df = pd.DataFrame()
        age_groups = ["0-5 bulan", "6-11 bulan", "12-23 bulan", "24-35 bulan", "36-47 bulan", "48-59 bulan"]
        for age_group in age_groups:
            if age_group in age_dist.columns:
                result_df[f"{age_group} (Jumlah)"] = age_dist[age_group]
                result_df[f"{age_group} (%)"] = age_dist_percentage[age_group].apply(lambda x: f"{x:.2f}%")
            else:
                result_df[f"{age_group} (Jumlah)"] = 0
                result_df[f"{age_group} (%)"] = "0.00%"

        # Tambahkan kolom Jumlah Total Current New Stunting Case hanya untuk New Stunting Cases
        if category == "New Stunting Cases":
            result_df["Jumlah Total Current New Stunting Case"] = total_per_puskesmas

        result_df = result_df.reset_index()

        # Tambahkan baris total
        total_row = pd.DataFrame(result_df.drop(columns=[group_by_col]).sum(numeric_only=True), columns=["Total"]).T
        total_row[group_by_col] = "Total"
        for col in result_df.columns:
            if "(%)" in col:
                # Perbaikan: Persentase untuk baris Total harus dihitung ulang
                total_jumlah = total_row["0-5 bulan (Jumlah)"].iloc[0] + total_row["6-11 bulan (Jumlah)"].iloc[0] + \
                               total_row["12-23 bulan (Jumlah)"].iloc[0] + total_row["24-35 bulan (Jumlah)"].iloc[0] + \
                               total_row["36-47 bulan (Jumlah)"].iloc[0] + total_row["48-59 bulan (Jumlah)"].iloc[0]
                if total_jumlah != 0:  # Hindari pembagian dengan 0
                    total_row[col] = (total_row[col.replace(" (%)", " (Jumlah)")] / total_jumlah * 100).apply(lambda x: f"{x:.2f}%")
                else:
                    total_row[col] = "0.00%"
        if category == "New Stunting Cases":
            total_row["Jumlah Total Current New Stunting Case"] = total_row["0-5 bulan (Jumlah)"]
        result_df = pd.concat([result_df, total_row], ignore_index=True)

        return result_df

    # Definisi fungsi calculate_stunting_metrics
    def calculate_stunting_metrics(df_awal, df_akhir, month_diff, group_by_col):
        # Hitung Current Stunting (jumlah stunting pada periode akhir per puskesmas)
        current_stunting = df_akhir[df_akhir["is_stunting"]].groupby(group_by_col).size()

        # Cek apakah df_awal kosong
        if df_awal.empty:
            st.warning("⚠️ Tidak ada data pada periode awal untuk filter yang dipilih. Analisis tidak dapat dilakukan.")
            return pd.DataFrame()

        # Cek apakah kolom usia_bulan ada di df_awal
        if "usia_bulan" not in df_awal.columns:
            st.error("⚠️ Kolom 'usia_bulan' tidak ditemukan di data periode awal. Silakan periksa data.")
            return pd.DataFrame()

        # Merge data awal dan akhir berdasarkan NIK
        merged_df = pd.merge(
            df_awal[["nik", "is_stunting", "usia_bulan", group_by_col]],
            df_akhir[["nik", "is_stunting", group_by_col]],
            on=["nik", group_by_col],
            how="outer",
            suffixes=("_awal", "_akhir")
        )

        # Isi NaN pada usia_bulan dengan 0
        merged_df["usia_bulan"] = merged_df["usia_bulan"].fillna(0).astype(int)

        # New Stunting Cases
        new_cases = merged_df[
            (merged_df["is_stunting_awal"].isna() | (merged_df["is_stunting_awal"] == False)) & 
            (merged_df["is_stunting_akhir"] == True)
        ].groupby(group_by_col).size()

        # Existing Stunting Cases
        existing_cases = merged_df[
            (merged_df["is_stunting_awal"] == True) & 
            (merged_df["is_stunting_akhir"] == True)
        ].groupby(group_by_col).size()

        # Dropout Stunting Cases
        dropout_cases = merged_df[
            (merged_df["is_stunting_awal"] == True) & 
            (merged_df["is_stunting_akhir"].isna()) & 
            ((merged_df["usia_bulan"] + month_diff) > 60)
        ].groupby(group_by_col).size()

        # Recovered Stunting Cases
        recovered_cases = merged_df[
            (merged_df["is_stunting_awal"] == True) & 
            (merged_df["is_stunting_akhir"] == False)
        ].groupby(group_by_col).size()

        # Gabungkan ke dalam DataFrame
        result_df = pd.DataFrame({
            "Puskesmas" if group_by_col == "puskesmas" else "Kelurahan": new_cases.index,
            "Current Stunting": current_stunting,
            "New Stunting Cases (Jumlah)": new_cases,
            "Existing Stunting Cases (Jumlah)": existing_cases,
            "Dropout Stunting Cases (Jumlah)": dropout_cases,
            "Recovered Stunting Cases (Jumlah)": recovered_cases
        }).fillna(0)

        # Hitung persentase berdasarkan Current Stunting per puskesmas (simpan sebagai float)
        result_df["New Stunting Cases (%)"] = (result_df["New Stunting Cases (Jumlah)"] / result_df["Current Stunting"] * 100).fillna(0)
        result_df["Existing Stunting Cases (%)"] = (result_df["Existing Stunting Cases (Jumlah)"] / result_df["Current Stunting"] * 100).fillna(0)
        result_df["Dropout Stunting Cases (%)"] = (result_df["Dropout Stunting Cases (Jumlah)"] / result_df["Current Stunting"] * 100).fillna(0)
        result_df["Recovered Stunting Cases (%)"] = (result_df["Recovered Stunting Cases (Jumlah)"] / result_df["Current Stunting"] * 100).fillna(0)

        # Tambahkan baris total
        total_row = pd.DataFrame({
            "Puskesmas" if group_by_col == "puskesmas" else "Kelurahan": ["Total"],
            "Current Stunting": [result_df["Current Stunting"].sum()],
            "New Stunting Cases (Jumlah)": [result_df["New Stunting Cases (Jumlah)"].sum()],
            "New Stunting Cases (%)": [result_df["New Stunting Cases (Jumlah)"].sum() / result_df["Current Stunting"].sum() * 100],
            "Existing Stunting Cases (Jumlah)": [result_df["Existing Stunting Cases (Jumlah)"].sum()],
            "Existing Stunting Cases (%)": [result_df["Existing Stunting Cases (Jumlah)"].sum() / result_df["Current Stunting"].sum() * 100],
            "Dropout Stunting Cases (Jumlah)": [result_df["Dropout Stunting Cases (Jumlah)"].sum()],
            "Dropout Stunting Cases (%)": [result_df["Dropout Stunting Cases (Jumlah)"].sum() / result_df["Current Stunting"].sum() * 100],
            "Recovered Stunting Cases (Jumlah)": [result_df["Recovered Stunting Cases (Jumlah)"].sum()],
            "Recovered Stunting Cases (%)": [result_df["Recovered Stunting Cases (Jumlah)"].sum() / result_df["Current Stunting"].sum() * 100]
        })

        result_df = pd.concat([result_df, total_row], ignore_index=True)

        return result_df

    # Definisi stunting_categories
    stunting_categories = [
        ("New Stunting Cases", "is_stunting_new", "Distribusi Kasus Stunting Baru"),
        ("Existing Stunting Cases", "is_stunting_existing", "Distribusi Kasus Stunting Lama"),
        ("Dropout Stunting Cases", "is_stunting_dropout", "Distribusi Kasus Stunting Dropout"),
        ("Recovered Stunting Cases", "is_stunting_recovered", "Distribusi Kasus Stunting Sembuh")
    ]

    # 11. Analisis Tabulasi Data Longitudinal (2a)
    if selected_submenu == "Analisis Tabulasi Data Longitudinal Balita Stunting":
        with st.expander("📜 Definisi dan Insight Analisis Tabulasi Longitudinal Stunting", expanded=False):
            st.markdown("""
            **Definisi Operasional**:
            - **New Stunting Cases**: Kasus stunting baru, yaitu balita yang tidak stunting pada periode awal tetapi menjadi stunting pada periode akhir.
            - **Existing Stunting Cases**: Kasus stunting yang sudah ada, yaitu balita yang stunting pada periode awal dan tetap stunting pada periode akhir.
            - **Dropout Stunting Cases**: Kasus stunting yang keluar dari kelompok usia balita (usia > 60 bulan pada periode akhir).
            - **Recovered Stunting Cases**: Kasus stunting yang sembuh, yaitu balita yang stunting pada periode awal tetapi tidak stunting pada periode akhir.
            - **Current Stunting**: Jumlah balita yang stunting pada periode akhir, digunakan sebagai denominator untuk persentase.

            **Metode Analisis**:
            - Analisis ini menggunakan NIK untuk melacak perubahan status stunting balita antar dua periode.
            - Persentase dihitung relatif terhadap Current Stunting pada periode akhir per puskesmas.

            **Insight**:
            - Tingginya New Stunting Cases menunjukkan perlunya intervensi pencegahan dini.
            - Tingginya Existing Stunting Cases menunjukkan kegagalan intervensi pada kasus stunting sebelumnya.
            - Recovered Stunting Cases yang tinggi mencerminkan keberhasilan program gizi.
            """)

        # Tentukan level analisis berdasarkan filter
        if selected_puskesmas == "All":
            group_by_col = "puskesmas"
            st.write(f"### Matriks Tabulasi Longitudinal Stunting (Semua Puskesmas, Periode {periode_awal} - {periode_akhir})")
        elif selected_kelurahan == "All":
            group_by_col = "kelurahan"
            st.write(f"### Matriks Tabulasi Longitudinal Stunting (Puskesmas: {selected_puskesmas}, Periode {periode_awal} - {periode_akhir})")
        else:
            group_by_col = "kelurahan"
            st.write(f"### Matriks Tabulasi Longitudinal Stunting (Puskesmas: {selected_puskesmas}, Kelurahan: {selected_kelurahan}, Periode {periode_awal} - {periode_akhir})")

        # Hitung metrik utama
        tabulation_df = calculate_stunting_metrics(df_awal, df_akhir, month_diff, group_by_col)

        # Cek apakah tabulation_df kosong
        if tabulation_df.empty:
            st.warning("⚠️ Tidak ada data yang dapat ditampilkan untuk filter yang dipilih.")
            return

        # Format persentase untuk tampilan tabel tanpa mengubah data asli
        display_df = tabulation_df.copy()
        for col in ["New Stunting Cases (%)", "Existing Stunting Cases (%)", "Dropout Stunting Cases (%)", "Recovered Stunting Cases (%)"]:
            display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}%")

        # Tampilkan tabel utama
        st.dataframe(display_df, use_container_width=True)

        # Tambahkan bagian distribusi berdasarkan kelompok usia
        st.subheader("📊 Distribusi Kasus Stunting Berdasarkan Kelompok Usia")

        # Buat DataFrame sementara untuk setiap kategori
        merged_df = pd.merge(
            df_awal[["nik", "is_stunting", "usia_bulan", group_by_col]],
            df_akhir[["nik", "is_stunting", "usia_bulan", group_by_col]],
            on=["nik", group_by_col],
            how="outer",
            suffixes=("_awal", "_akhir")
        )
        merged_df["usia_bulan_awal"] = merged_df["usia_bulan_awal"].fillna(0).astype(int)
        merged_df["usia_bulan_akhir"] = merged_df["usia_bulan_akhir"].fillna(0).astype(int)

        # Tambahkan kolom untuk masing-masing kategori
        merged_df["is_stunting_new"] = (merged_df["is_stunting_awal"].isna() | (merged_df["is_stunting_awal"] == False)) & (merged_df["is_stunting_akhir"] == True)
        merged_df["is_stunting_existing"] = (merged_df["is_stunting_awal"] == True) & (merged_df["is_stunting_akhir"] == True)
        merged_df["is_stunting_dropout"] = (merged_df["is_stunting_awal"] == True) & (merged_df["is_stunting_akhir"].isna()) & ((merged_df["usia_bulan_awal"] + month_diff) > 60)
        merged_df["is_stunting_recovered"] = (merged_df["is_stunting_awal"] == True) & (merged_df["is_stunting_akhir"] == False)

        # Gunakan usia dari periode akhir untuk New dan Existing, usia dari periode awal untuk Dropout dan Recovered
        merged_df["usia_bulan"] = merged_df.apply(
            lambda row: row["usia_bulan_akhir"] if row["is_stunting_new"] or row["is_stunting_existing"] else row["usia_bulan_awal"],
            axis=1
        )

        # Loop untuk setiap kategori stunting
        for category, col, title in stunting_categories:
            st.write(f"#### {title} Berdasarkan Kelompok Usia")

            # Hitung distribusi
            age_dist_df = calculate_age_distribution(merged_df, col, group_by_col, category=category)

            if age_dist_df.empty:
                st.warning(f"⚠️ Tidak ada data untuk {title.lower()}.")
                continue

            # Tampilkan tabel distribusi
            st.dataframe(age_dist_df, use_container_width=True)

            # Buat heatmap
            st.write(f"##### Heatmap {title}")
            columns_to_drop = [col for col in age_dist_df.columns if "(%)" in col or col == "Jumlah Total Current New Stunting Case"]
            heatmap_data = age_dist_df.drop(columns=columns_to_drop)
            heatmap_data = heatmap_data.set_index(group_by_col)
            heatmap_data = heatmap_data.drop("Total", errors="ignore")
            
            fig = go.Figure(data=go.Heatmap(
                z=heatmap_data.values,
                x=[col.replace(" (Jumlah)", "") for col in heatmap_data.columns],
                y=heatmap_data.index,
                colorscale="YlOrRd",
                text=heatmap_data.values,
                texttemplate="%{text}",
                textfont={"size": 12},
                hoverongaps=False
            ))
            fig.update_layout(
                title=f"Heatmap {title} (Jumlah Kasus)",
                xaxis_title="Kelompok Usia",
                yaxis_title=group_by_col.capitalize(),
                xaxis_tickangle=-45,
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

        # Tambahkan catatan
        st.markdown("""
        **Catatan**:
        - Tabel distribusi menunjukkan jumlah dan persentase kasus stunting per kelompok usia untuk setiap puskesmas.
        - Heatmap memvisualisasikan distribusi kasus, dengan warna yang lebih gelap menunjukkan jumlah kasus yang lebih tinggi.
        - Gunakan heatmap untuk mengidentifikasi kelompok usia dan puskesmas dengan kasus stunting tertinggi, sehingga intervensi dapat lebih terfokus.
        """, unsafe_allow_html=True)

    # 2b. Grafik Analisis Data Longitudinal Balita Stunting
    elif selected_submenu == "Grafik Analisis Data Longitudinal Balita Stunting":
        st.write(f"### Grafik Analisis Longitudinal Stunting (Periode {periode_awal} - {periode_akhir})")

        # Hitung metrik untuk visualisasi
        if selected_puskesmas == "All":
            group_by_col = "puskesmas"
            title_suffix = "Semua Puskesmas"
        elif selected_kelurahan == "All":
            group_by_col = "kelurahan"
            title_suffix = f"Puskesmas: {selected_puskesmas}"
        else:
            group_by_col = "kelurahan"
            title_suffix = f"Puskesmas: {selected_puskesmas}, Kelurahan: {selected_kelurahan}"

        tabulation_df = calculate_stunting_metrics(df_awal, df_akhir, month_diff, group_by_col)

        if tabulation_df.empty:
            st.warning("⚠️ Tidak ada data yang dapat ditampilkan untuk filter yang dipilih.")
            return

        # Grafik bar utama (persentase)
        categories = [
            ("New Stunting Cases (%)", "Kasus Stunting Baru", "blue"),
            ("Existing Stunting Cases (%)", "Kasus Stunting Lama", "green"),
            ("Dropout Stunting Cases (%)", "Kasus Stunting Dropout", "orange"),
            ("Recovered Stunting Cases (%)", "Kasus Stunting Sembuh", "purple")
        ]

        for col, title, color in categories:
            fig = go.Figure()
            plot_df = tabulation_df[tabulation_df["Puskesmas" if group_by_col == "puskesmas" else "Kelurahan"] != "Total"]
            y_values = plot_df[col].astype(float)
            fig.add_trace(go.Bar(
                x=plot_df["Puskesmas" if group_by_col == "puskesmas" else "Kelurahan"],
                y=y_values,
                name=title,
                marker_color=color,
                text=y_values.apply(lambda x: f"{x:.2f}%"),
                textposition="auto"
            ))
            fig.update_layout(
                title=f"{title} ({title_suffix})",
                xaxis_title=group_by_col.capitalize(),
                yaxis_title="Persentase (%)",
                xaxis_tickangle=-45,
                template="plotly_white",
                height=400,
                yaxis=dict(range=[0, 100])  # Batasi sumbu y ke 0-100%
            )
            st.plotly_chart(fig, use_container_width=True)

        # Tambahkan grafik distribusi usia (persentase)
        st.subheader("📊 Distribusi Kasus Stunting Berdasarkan Kelompok Usia (Grafik)")
        
        # Buat DataFrame sementara untuk setiap kategori
        merged_df = pd.merge(
            df_awal[["nik", "is_stunting", "usia_bulan", group_by_col]],
            df_akhir[["nik", "is_stunting", "usia_bulan", group_by_col]],
            on=["nik", group_by_col],
            how="outer",
            suffixes=("_awal", "_akhir")
        )
        merged_df["usia_bulan_awal"] = merged_df["usia_bulan_awal"].fillna(0).astype(int)
        merged_df["usia_bulan_akhir"] = merged_df["usia_bulan_akhir"].fillna(0).astype(int)

        merged_df["is_stunting_new"] = (merged_df["is_stunting_awal"].isna() | (merged_df["is_stunting_awal"] == False)) & (merged_df["is_stunting_akhir"] == True)
        merged_df["is_stunting_existing"] = (merged_df["is_stunting_awal"] == True) & (merged_df["is_stunting_akhir"] == True)
        merged_df["is_stunting_dropout"] = (merged_df["is_stunting_awal"] == True) & (merged_df["is_stunting_akhir"].isna()) & ((merged_df["usia_bulan_awal"] + month_diff) > 60)
        merged_df["is_stunting_recovered"] = (merged_df["is_stunting_awal"] == True) & (merged_df["is_stunting_akhir"] == False)

        merged_df["usia_bulan"] = merged_df.apply(
            lambda row: row["usia_bulan_akhir"] if row["is_stunting_new"] or row["is_stunting_existing"] else row["usia_bulan_awal"],
            axis=1
        )

        for category, col, title in stunting_categories:
            st.write(f"#### {title} Berdasarkan Kelompok Usia (Stacked Bar)")
            age_dist_df = calculate_age_distribution(merged_df, col, group_by_col, category=category)

            if age_dist_df.empty:
                st.warning(f"⚠️ Tidak ada data untuk {title.lower()}.")
                continue

            # Hapus baris Total dari age_dist_df sebelum plotting
            age_dist_df = age_dist_df[age_dist_df[group_by_col] != "Total"]

            # Buat stacked bar chart (persentase)
            columns_to_plot = [col for col in age_dist_df.columns if "(%)" in col]
            plot_data = age_dist_df.melt(id_vars=[group_by_col], value_vars=columns_to_plot)
            plot_data["value"] = plot_data["value"].str.replace("%", "").astype(float)

            # Custom labels untuk legenda
            plot_data["variable"] = plot_data["variable"].str.replace(" (%)", "")

            fig = px.bar(
                plot_data,
                x=group_by_col,
                y="value",
                color="variable",
                title=f"{title} per Kelompok Usia ({title_suffix})",
                labels={"value": "Persentase (%)", "variable": "Kelompok Usia"},
                height=600  # Tingkatkan tinggi grafik
            )
            fig.update_layout(
                xaxis_title=group_by_col.capitalize(),
                yaxis_title="Persentase (%)",
                xaxis_tickangle=-45,
                yaxis=dict(range=[0, 100], gridcolor="lightgray"),  # Batasi sumbu y ke 0-100% dan tambahkan grid
                xaxis=dict(tickfont=dict(size=10)),  # Kecilkan ukuran font label sumbu x
                legend_title="Kelompok Usia",
                template="plotly_white",
                bargap=0.2  # Tambahkan jarak antar bar
            )
            fig.update_traces(
                hovertemplate="%{x}<br>Kelompok Usia: %{fullData.name}<br>Persentase: %{y:.2f}%"
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
        **Catatan**: Grafik ini menunjukkan distribusi kasus stunting berdasarkan kategori longitudinal dan kelompok usia dalam persentase. Bar yang tinggi pada "Kasus Stunting Baru" atau "Kasus Stunting Lama" menunjukkan area yang memerlukan intervensi segera, sedangkan "Kasus Stunting Sembuh" mencerminkan keberhasilan program gizi.
        """, unsafe_allow_html=True)
        
def show_dashboard():
    st.title("📈 Dashboard EPPGBM")

    # Koneksi ke database data_eppgbm.db
    conn = sqlite3.connect("data_eppgbm.db")
    try:
        # Membaca data dari tabel data_eppgbm
        df = pd.read_sql_query("SELECT * FROM data_eppgbm", conn)

        # Pilihan submenu menggunakan radio button
        st.sidebar.header("🔍 Pilih Analisis")
        analysis_options = [
            "Informasi Data EPPGBM",
            "Distribusi Data EPPGBM",
            "Distribusi Z-Score Analysis",
            "Analisis Z-Score Flag",
            "Analisis Trend Pertumbuhan EPPGBM",
            "Daftar Balita Bermasalah",
            "Analisis Longitudinal Balita"
        ]
        selected_analysis = st.sidebar.radio("Pilih submenu:", analysis_options, index=0)

        # Logika untuk menampilkan analisis berdasarkan pilihan
        if selected_analysis == "Informasi Data EPPGBM":
            show_info_data_eppgbm(df)
        elif selected_analysis == "Distribusi Data EPPGBM":
            show_distribusi_data_eppgbm(df)
        elif selected_analysis == "Distribusi Z-Score Analysis":
            show_distribusi_zscore_analysis(df)
        elif selected_analysis == "Analisis Z-Score Flag":
            show_analisis_zscore_flag(df)
        elif selected_analysis == "Analisis Trend Pertumbuhan EPPGBM":
            show_analisis_trend_pertumbuhan(df)
        elif selected_analysis == "Daftar Balita Bermasalah":
            show_daftar_balita_bermasalah_gizi(df)
        elif selected_analysis == "Analisis Longitudinal Balita":
            analisis_longitudinal_balita (df)

    except Exception as e:
        st.warning("⚠️ Data belum tersedia atau terjadi kesalahan koneksi ke database.")
        st.error(f"Error: {e}")
    finally:
        conn.close()

    st.markdown(
        '<p style="text-align: center; font-size: 12px; color: grey;">'
        'made with ❤️ by <a href="mailto:dedik2urniawan@gmail.com">dedik2urniawan@gmail.com</a>'
        '</p>', unsafe_allow_html=True)
    
# Jalankan aplikasi
if __name__ == "__main__":
    show_dashboard()