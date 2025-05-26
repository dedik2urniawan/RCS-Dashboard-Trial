import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import numpy as np
from sklearn.linear_model import LinearRegression
from scipy.stats import pearsonr
import semopy

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

# Fungsi untuk menghitung rasio/persentase dengan penanganan pembagian nol
def calculate_ratio(numerator, denominator):
    return np.where(denominator > 0, (numerator / denominator) * 100, 0)

# Fungsi untuk filter data
def filter_data(df, tahun, bulan, puskesmas, kelurahan):
    filtered_df = df.copy()
    if tahun and tahun != "ALL":
        filtered_df = filtered_df[filtered_df['Tahun'] == int(tahun)]
    if bulan and bulan != "ALL":
        filtered_df = filtered_df[filtered_df['Bulan'] == int(bulan)]
    if puskesmas and puskesmas != "ALL":
        filtered_df = filtered_df[filtered_df['Puskesmas'] == puskesmas]
    if kelurahan and kelurahan != "ALL":
        filtered_df = filtered_df[filtered_df['Kelurahan'] == kelurahan]
    return filtered_df

# Fungsi untuk menghitung koefisien regresi
def calculate_path_coefficient(X, y):
    if len(X) < 2 or len(y) < 2:
        return 0
    X = X.values.reshape(-1, 1)
    y = y.values
    model = LinearRegression()
    model.fit(X, y)
    return model.coef_[0]

# Fungsi untuk menghitung koefisien korelasi Pearson
def calculate_correlation_coefficient(X, y):
    if len(X) < 2 or len(y) < 2:
        return 0
    r, _ = pearsonr(X, y)
    return r

# Fungsi untuk membuat path diagram menggunakan Sankey
def create_path_diagram(coefficients, correlations):
    nodes = [
        "TTD", "Anemia", "KEK", "BBLR", "PBLR", 
        "IMD", "ASI Eksklusif", "MPASI", "Underweight", 
        "Wasting", "Stunting"
    ]
    node_indices = {node: idx for idx, node in enumerate(nodes)}

    links = [
        {"source": "TTD", "target": "KEK", "value": abs(coefficients["TTD_KEK"]), "path_coef": coefficients["TTD_KEK"], "corr_coef": correlations["TTD_KEK"]},
        {"source": "Anemia", "target": "KEK", "value": abs(coefficients["Anemia_KEK"]), "path_coef": coefficients["Anemia_KEK"], "corr_coef": correlations["Anemia_KEK"]},
        {"source": "KEK", "target": "BBLR", "value": abs(coefficients["KEK_BBLR"]), "path_coef": coefficients["KEK_BBLR"], "corr_coef": correlations["KEK_BBLR"]},
        {"source": "KEK", "target": "PBLR", "value": abs(coefficients["KEK_PBLR"]), "path_coef": coefficients["KEK_PBLR"], "corr_coef": correlations["KEK_PBLR"]},
        {"source": "BBLR", "target": "Underweight", "value": abs(coefficients["BBLR_Underweight"]), "path_coef": coefficients["BBLR_Underweight"], "corr_coef": correlations["BBLR_Underweight"]},
        {"source": "PBLR", "target": "Underweight", "value": abs(coefficients["PBLR_Underweight"]), "path_coef": coefficients["PBLR_Underweight"], "corr_coef": correlations["PBLR_Underweight"]},
        {"source": "IMD", "target": "Underweight", "value": abs(coefficients["IMD_Underweight"]), "path_coef": coefficients["IMD_Underweight"], "corr_coef": correlations["IMD_Underweight"]},
        {"source": "ASI Eksklusif", "target": "Underweight", "value": abs(coefficients["ASI_Underweight"]), "path_coef": coefficients["ASI_Underweight"], "corr_coef": correlations["ASI_Underweight"]},
        {"source": "MPASI", "target": "Underweight", "value": abs(coefficients["MPASI_Underweight"]), "path_coef": coefficients["MPASI_Underweight"], "corr_coef": correlations["MPASI_Underweight"]},
        {"source": "Underweight", "target": "Wasting", "value": abs(coefficients["Underweight_Wasting"]), "path_coef": coefficients["Underweight_Wasting"], "corr_coef": correlations["Underweight_Wasting"]},
        {"source": "Wasting", "target": "Stunting", "value": abs(coefficients["Wasting_Stunting"]), "path_coef": coefficients["Wasting_Stunting"], "corr_coef": correlations["Wasting_Stunting"]}
    ]

    source = [node_indices[link["source"]] for link in links]
    target = [node_indices[link["target"]] for link in links]
    value = [link["value"] for link in links]
    labels = [f"{link['source']} → {link['target']}: Path = {link['path_coef']:.2f}, r = {link['corr_coef']:.2f}" for link in links]

    fig = go.Figure(data=[go.Sankey(
        node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=nodes, color="blue"),
        link=dict(source=source, target=target, value=value, label=labels, color="rgba(0, 0, 255, 0.5)")
    )])

    fig.update_layout(
        title_text="Path Diagram SEM: Hubungan Antar Variabel Gizi",
        font_size=10,
        height=600
    )
    return fig

# Fungsi utama dashboard
def show_dashboard():
    st.subheader("📈 Analisis Composite: Structural Equation Modeling (SEM)")

    # Tambahkan pesan pengembangan sebagai informasi (opsional)
    st.info("Fitur ini masih dalam tahap pengembangan. Beberapa hasil mungkin belum sepenuhnya akurat. Kami menghargai kesabaran Anda dalam menunggu pembaruan ini.")

    # Memuat data dari database
    df_ibuhamil = load_data("data_ibuhamil")
    df_balita_kia = load_data("data_balita_kia")
    df_balita_gizi = load_data("data_balita_gizi")

    if df_ibuhamil.empty or df_balita_kia.empty or df_balita_gizi.empty:
        st.error("⚠️ Salah satu atau semua data tidak tersedia. Pastikan tabel 'data_ibuhamil', 'data_balita_kia', dan 'data_balita_gizi' ada di database.")
        return

    # Filter data
    st.subheader("🔎 Filter Data")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        tahun_options = ["ALL"] + sorted(df_ibuhamil['Tahun'].astype(str).unique().tolist())
        tahun = st.selectbox("📅 Tahun", tahun_options, key="tahun_composite")
    with col2:
        bulan_options = ["ALL"] + [str(i) for i in range(1, 13)]
        bulan = st.selectbox("🗓️ Bulan", bulan_options, key="bulan_composite")
    with col3:
        puskesmas_options = ["ALL"] + sorted(df_ibuhamil['Puskesmas'].unique().tolist())
        puskesmas = st.selectbox("🏥 Puskesmas", puskesmas_options, key="puskesmas_composite")
    with col4:
        filtered_kelurahan = df_ibuhamil
        if puskesmas != "ALL":
            filtered_kelurahan = filtered_kelurahan[filtered_kelurahan['Puskesmas'] == puskesmas]
        kelurahan_options = ["ALL"] + sorted(filtered_kelurahan['Kelurahan'].unique().tolist())
        kelurahan = st.selectbox("🏘️ Kelurahan", kelurahan_options, key="kelurahan_composite")

    # Terapkan filter pada semua dataset
    df_ibuhamil_filtered = filter_data(df_ibuhamil, tahun, bulan, puskesmas, kelurahan)
    df_balita_kia_filtered = filter_data(df_balita_kia, tahun, bulan, puskesmas, kelurahan)
    df_balita_gizi_filtered = filter_data(df_balita_gizi, tahun, bulan, puskesmas, kelurahan)

    if df_ibuhamil_filtered.empty or df_balita_kia_filtered.empty or df_balita_gizi_filtered.empty:
        st.warning("⚠️ Tidak ada data setelah filter diterapkan. Silakan sesuaikan filter.")
        return

    # Gabungkan data berdasarkan kolom filter (Tahun, Bulan, Puskesmas, Kelurahan)
    merge_cols = ["Tahun", "Bulan", "Puskesmas", "Kelurahan"]
    merged_df = df_ibuhamil_filtered.merge(
        df_balita_kia_filtered, on=merge_cols, how="inner"
    ).merge(
        df_balita_gizi_filtered, on=merge_cols, how="inner"
    )

    if merged_df.empty:
        st.warning("⚠️ Tidak ada data yang cocok setelah penggabungan. Pastikan data di semua tabel memiliki nilai yang sesuai untuk filter.")
        return

    # Hitung rasio/persentase untuk variabel SEM dengan denominasi baru
    merged_df["TTD"] = calculate_ratio(
        merged_df["Jumlah_ibu_hamil_mengonsumsi_minimal_180_tablet_TTD"],
        merged_df["Jumlah_Sasaran_Ibu_Hamil"]
    )
    merged_df["Anemia"] = calculate_ratio(
        merged_df["Jumlah_ibu_hamil_anemia"],
        merged_df["Jumlah_ibu_hamil_periksa_Hb"]
    )
    merged_df["KEK"] = calculate_ratio(
        merged_df["Jumlah_ibu_hamil_risiko_KEK"],
        merged_df["Jumlah_ibu_hamil_diukur_LILA_IMT"]
    )
    merged_df["BBLR"] = calculate_ratio(
        merged_df["Jumlah_bayi_BBLR"],
        merged_df["Jumlah_bayi_baru_lahir_hidup"]
    )
    merged_df["PBLR"] = calculate_ratio(
        merged_df["Jumlah_Bayi_PBLR"],
        merged_df["Jumlah_bayi_baru_lahir_hidup"]
    )
    merged_df["IMD"] = calculate_ratio(
        merged_df["Jumlah_Bayi_Mendapat_IMD"],
        merged_df["Jumlah_bayi_baru_lahir_bulan_ini_B"]
    )
    merged_df["ASI_Eksklusif"] = calculate_ratio(
        merged_df["Jumlah_Bayi_Asi_Eksklusif_sampai_6_bulan"],
        merged_df["Jumlah_Bayi_usia_0-5_bulan_yang_direcall"]
    )
    merged_df["MPASI"] = calculate_ratio(
        merged_df["Jumlah_anak_usia_6-23_bulan_yang_mendapat_MPASI_baik"],
        merged_df["Jumlah_anak_usia_6-23_bulan_yang_diwawancarai"]
    )
    merged_df["Underweight"] = calculate_ratio(
        merged_df["Jumlah_balita_underweight"],
        merged_df["Jumlah_balita_ditimbang"]
    )
    merged_df["Stunting"] = calculate_ratio(
        merged_df["Jumlah_balita_stunting"],
        merged_df["Jumlah_balita_diukur_PBTB"]
    )
    merged_df["Wasting"] = calculate_ratio(
        merged_df["Jumlah_balita_wasting"],
        merged_df["Jumlah_balita_ditimbang_dan_diukur"]
    )

    # Hitung koefisien jalur (path coefficients) dan koefisien korelasi
    coefficients = {}
    correlations = {}
    # TTD -> KEK
    coefficients["TTD_KEK"] = calculate_path_coefficient(merged_df["TTD"], merged_df["KEK"])
    correlations["TTD_KEK"] = calculate_correlation_coefficient(merged_df["TTD"], merged_df["KEK"])
    # Anemia -> KEK
    coefficients["Anemia_KEK"] = calculate_path_coefficient(merged_df["Anemia"], merged_df["KEK"])
    correlations["Anemia_KEK"] = calculate_correlation_coefficient(merged_df["Anemia"], merged_df["KEK"])
    # KEK -> BBLR
    coefficients["KEK_BBLR"] = calculate_path_coefficient(merged_df["KEK"], merged_df["BBLR"])
    correlations["KEK_BBLR"] = calculate_correlation_coefficient(merged_df["KEK"], merged_df["BBLR"])
    # KEK -> PBLR
    coefficients["KEK_PBLR"] = calculate_path_coefficient(merged_df["KEK"], merged_df["PBLR"])
    correlations["KEK_PBLR"] = calculate_correlation_coefficient(merged_df["KEK"], merged_df["PBLR"])
    # BBLR -> Underweight
    coefficients["BBLR_Underweight"] = calculate_path_coefficient(merged_df["BBLR"], merged_df["Underweight"])
    correlations["BBLR_Underweight"] = calculate_correlation_coefficient(merged_df["BBLR"], merged_df["Underweight"])
    # PBLR -> Underweight
    coefficients["PBLR_Underweight"] = calculate_path_coefficient(merged_df["PBLR"], merged_df["Underweight"])
    correlations["PBLR_Underweight"] = calculate_correlation_coefficient(merged_df["PBLR"], merged_df["Underweight"])
    # IMD -> Underweight
    coefficients["IMD_Underweight"] = calculate_path_coefficient(merged_df["IMD"], merged_df["Underweight"])
    correlations["IMD_Underweight"] = calculate_correlation_coefficient(merged_df["IMD"], merged_df["Underweight"])
    # ASI Eksklusif -> Underweight
    coefficients["ASI_Underweight"] = calculate_path_coefficient(merged_df["ASI_Eksklusif"], merged_df["Underweight"])
    correlations["ASI_Underweight"] = calculate_correlation_coefficient(merged_df["ASI_Eksklusif"], merged_df["Underweight"])
    # MPASI -> Underweight
    coefficients["MPASI_Underweight"] = calculate_path_coefficient(merged_df["MPASI"], merged_df["Underweight"])
    correlations["MPASI_Underweight"] = calculate_correlation_coefficient(merged_df["MPASI"], merged_df["Underweight"])
    # Underweight -> Wasting
    coefficients["Underweight_Wasting"] = calculate_path_coefficient(merged_df["Underweight"], merged_df["Wasting"])
    correlations["Underweight_Wasting"] = calculate_correlation_coefficient(merged_df["Underweight"], merged_df["Wasting"])
    # Wasting -> Stunting
    coefficients["Wasting_Stunting"] = calculate_path_coefficient(merged_df["Wasting"], merged_df["Stunting"])
    correlations["Wasting_Stunting"] = calculate_correlation_coefficient(merged_df["Wasting"], merged_df["Stunting"])

    # Buat path diagram
    st.subheader("🗺️ Path Diagram SEM")
    fig = create_path_diagram(coefficients, correlations)
    st.plotly_chart(fig, use_container_width=True)

    # Tambahkan keterangan untuk path diagram
    st.markdown("""
    **Catatan Path Diagram:**
    - Diagram di atas menunjukkan hubungan antar variabel dengan koefisien jalur (Path) dan koefisien korelasi (r).
    - Koefisien jalur (Path) menunjukkan kekuatan hubungan langsung dari regresi linear.
    - Koefisien korelasi (r) menunjukkan kekuatan dan arah hubungan linear (positif atau negatif).
    - Nilai r mendekati 1 atau -1 menunjukkan korelasi kuat, sedangkan mendekati 0 menunjukkan korelasi lemah.
    """)

    # Analisis SEM menggunakan semopy
    st.subheader("📊 Analisis SEM dengan semopy (Estimasi Parameter dan Goodness-of-Fit)")
    try:
        # Definisikan model SEM dalam sintaks semopy
        model_spec = """
        # Variabel eksogen (TTD dan Anemia memengaruhi KEK)
        KEK ~ TTD + Anemia
        # Variabel endogen (KEK memengaruhi BBLR dan PBLR)
        BBLR ~ KEK
        PBLR ~ KEK
        # Variabel endogen (BBLR, PBLR, IMD, ASI, MPASI memengaruhi Underweight)
        Underweight ~ BBLR + PBLR + IMD + ASI_Eksklusif + MPASI
        # Variabel endogen (Underweight memengaruhi Wasting)
        Wasting ~ Underweight
        # Variabel endogen (Wasting memengaruhi Stunting)
        Stunting ~ Wasting
        """

        # Siapkan data untuk semopy
        sem_data = merged_df[["TTD", "Anemia", "KEK", "BBLR", "PBLR", "IMD", "ASI_Eksklusif", "MPASI", "Underweight", "Wasting", "Stunting"]].dropna()

        if len(sem_data) < 2:
            st.warning("⚠️ Data tidak cukup untuk analisis SEM dengan semopy. Minimal 2 baris data yang lengkap diperlukan.")
            return

        # Buat dan estimasi model SEM
        model = semopy.Model(model_spec)
        model.fit(sem_data)

        # Tampilkan hasil estimasi parameter
        st.subheader("📋 Hasil Estimasi Parameter")
        params = model.inspect()
        st.write(params)

        # Tampilkan goodness-of-fit menggunakan calc_stats
        st.subheader("📈 Uji Goodness-of-Fit")
        try:
            from semopy import calc_stats
            stats = calc_stats(model)
            st.write("**Ukuran Kebaikan Pemasangan (Fit Measures):**")
            for key, value in stats.items():
                if key in ['chisq', 'df', 'pvalue', 'rmsea', 'cfi', 'tli']:  # Filter hanya metrik yang relevan
                    st.write(f"- {key}: {value:.4f}")
        except AttributeError:
            st.warning("⚠️ Informasi goodness-of-fit tidak tersedia secara langsung. Gunakan 'model.inspect()' untuk parameter saja.")

        # Tambahkan interpretasi sederhana
        st.markdown("""
        **Interpretasi:**
        - **Chi-Square**: Nilai kecil dengan p-value > 0.05 menunjukkan model cocok dengan data.
        - **RMSEA**: Nilai < 0.05 menunjukkan pemasangan yang sangat baik, < 0.08 menunjukkan pemasangan yang cukup baik.
        - **CFI/TLI**: Nilai > 0.90 menunjukkan pemasangan yang baik.
        (Catatan: Nilai ini mungkin tidak tersedia jika data atau model tidak memadai.)
        """)

    except Exception as e:
        st.error(f"❌ Error dalam analisis SEM dengan semopy: {e}")
        st.warning("Pastikan data lengkap dan library semopy terinstal dengan benar. Coba perbarui semopy dengan 'pip install --upgrade semopy'.")

    # Tambahkan keterangan untuk semopy
    st.markdown("""
    **Catatan SEM dengan semopy:**
    - Analisis ini menggunakan Maximum Likelihood (default) untuk estimasi parameter.
    - Hasil parameter menunjukkan koefisien jalur yang diestimasi dengan standar error dan p-value.
    - Uji goodness-of-fit mungkin terbatas tergantung pada versi semopy dan data yang digunakan.
    """)