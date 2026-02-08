import datetime
import io
import math
import sqlite3

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

GSHEET_ID_DEFAULT = "1lK97xi4nSpyNoTNNCR2daOnXJfCgZkW9sh4o9ZrbJIc"
GSHEET_WORKSHEET = "pkp_klarifikasi"


def _load_data(table_name="data_pkp", db_path="rcs_data.db"):
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ Gagal memuat data PKP: {e}")
        return pd.DataFrame()


def _col_map(df):
    return {c.lower().strip(): c for c in df.columns}


def _get_col(df, name):
    return _col_map(df).get(name.lower().strip())


def _load_klarifikasi(tahun, puskesmas, indikator, db_path="rcs_data.db"):
    try:
        conn = sqlite3.connect(db_path)
        query = """
            SELECT * FROM pkp_klarifikasi
            WHERE tahun = ? AND puskesmas = ? AND indikator = ?
            ORDER BY updated_at DESC
            LIMIT 1
        """
        row = pd.read_sql_query(query, conn, params=[tahun, puskesmas, indikator])
        conn.close()
        return row
    except Exception:
        return pd.DataFrame()


def _get_gsheet_client():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except Exception:
        return None

    if "gcp_service_account" not in st.secrets:
        return None

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return gspread.authorize(creds)


@st.cache_resource
def _get_gsheet():
    client = _get_gsheet_client()
    if client is None:
        return None
    sheet_id = st.secrets.get("pkp_gsheet_id", GSHEET_ID_DEFAULT)
    sh = client.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(GSHEET_WORKSHEET)
    except Exception:
        ws = sh.add_worksheet(title=GSHEET_WORKSHEET, rows=100, cols=10)
        ws.append_row(
            [
                "tahun",
                "puskesmas",
                "indikator",
                "total_sasaran",
                "target_persen",
                "target_sasaran",
                "pencapaian",
                "nilai_kerja",
                "updated_at",
            ]
        )
    return ws


def _load_klarifikasi_gs(tahun, puskesmas, indikator):
    df = _load_all_klarifikasi_gs()
    if df.empty:
        return df
    df = df[(df["tahun"] == str(tahun)) & (df["puskesmas"] == str(puskesmas)) & (df["indikator"] == str(indikator))]
    if df.empty:
        return df
    df = df.sort_values("updated_at", ascending=False).head(1)
    return df


def _save_klarifikasi_gs(row_df):
    ws = _get_gsheet()
    if ws is None:
        return False
    row = row_df.loc[0].to_dict()
    ws.append_row(
        [
            row["tahun"],
            row["puskesmas"],
            row["indikator"],
            row["total_sasaran"],
            row["target_persen"],
            row["target_sasaran"],
            row["pencapaian"],
            row["nilai_kerja"],
            row["updated_at"],
        ]
    )
    return True


def _save_klarifikasi(row_df, db_path="rcs_data.db"):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pkp_klarifikasi (
            tahun TEXT,
            puskesmas TEXT,
            indikator TEXT,
            total_sasaran REAL,
            target_persen REAL,
            target_sasaran REAL,
            pencapaian REAL,
            nilai_kerja REAL,
            updated_at TEXT
        )
        """
    )
    conn.execute(
        "DELETE FROM pkp_klarifikasi WHERE tahun = ? AND puskesmas = ? AND indikator = ?",
        (
            row_df.loc[0].get("tahun") or row_df.loc[0].get("Tahun"),
            row_df.loc[0].get("puskesmas") or row_df.loc[0].get("Puskesmas"),
            row_df.loc[0].get("indikator") or row_df.loc[0].get("Indikator"),
        ),
    )
    row_df.to_sql("pkp_klarifikasi", conn, if_exists="append", index=False)
    conn.close()


@st.cache_data(ttl=60)
def _load_all_klarifikasi_gs():
    ws = _get_gsheet()
    if ws is None:
        return pd.DataFrame()
    try:
        values = ws.get_all_records()
    except Exception:
        return pd.DataFrame()
    if not values:
        return pd.DataFrame()
    df = pd.DataFrame(values)
    if "indikator" not in df.columns:
        return pd.DataFrame()
    df["source"] = "gsheet"
    return df


def _load_all_klarifikasi_sqlite(db_path="rcs_data.db"):
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM pkp_klarifikasi", conn)
        conn.close()
        if df.empty:
            return df
        df["source"] = "sqlite"
        return df
    except Exception:
        return pd.DataFrame()


def _reset_klarifikasi_gs(tahun="ALL", puskesmas="ALL", indikator="ALL"):
    ws = _get_gsheet()
    if ws is None:
        return False
    values = ws.get_all_records()
    if not values:
        return True
    df = pd.DataFrame(values)
    if "indikator" not in df.columns:
        return False

    def _match(row):
        ok = True
        if tahun != "ALL":
            ok = ok and str(row["tahun"]) == str(tahun)
        if puskesmas != "ALL":
            ok = ok and str(row["puskesmas"]) == str(puskesmas)
        if indikator != "ALL":
            ok = ok and str(row["indikator"]) == str(indikator)
        return ok

    remaining = [r for r in values if not _match(r)]
    ws.clear()
    ws.append_row(
        [
            "tahun",
            "puskesmas",
            "indikator",
            "total_sasaran",
            "target_persen",
            "target_sasaran",
            "pencapaian",
            "nilai_kerja",
            "updated_at",
        ]
    )
    if remaining:
        ws.append_rows([list(r.values()) for r in remaining])
    return True


def _reset_klarifikasi_sqlite(tahun="ALL", puskesmas="ALL", indikator="ALL", db_path="rcs_data.db"):
    try:
        conn = sqlite3.connect(db_path)
        where = []
        params = []
        if tahun != "ALL":
            where.append("tahun = ?")
            params.append(str(tahun))
        if puskesmas != "ALL":
            where.append("puskesmas = ?")
            params.append(str(puskesmas))
        if indikator != "ALL":
            where.append("indikator = ?")
            params.append(str(indikator))
        if where:
            query = "DELETE FROM pkp_klarifikasi WHERE " + " AND ".join(where)
        else:
            query = "DELETE FROM pkp_klarifikasi"
        conn.execute(query, params)
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False
def show_dashboard():
    st.title("📄 Laporan Analisis PKP (Penilaian Kinerja Puskesmas)")

    df = _load_data()
    if df.empty:
        st.warning("⚠️ Data PKP belum tersedia. Silakan unggah dataset PKP terlebih dahulu.")
        return

    col_tahun = _get_col(df, "tahun") or _get_col(df, "Tahun")
    col_puskesmas = _get_col(df, "puskesmas") or _get_col(df, "Puskesmas")

    if not col_tahun or not col_puskesmas:
        st.error("❌ Kolom 'tahun' atau 'Puskesmas' tidak ditemukan di data_pkp.")
        return

    st.subheader("🔍 Filter Data")
    col1, col2 = st.columns(2)
    with col1:
        tahun_options = ["ALL"] + sorted(df[col_tahun].astype(str).unique().tolist())
        tahun_filter = st.selectbox("📅 Pilih Tahun", tahun_options, key="pkp_tahun")
    with col2:
        puskesmas_options = ["ALL"] + sorted(df[col_puskesmas].astype(str).unique().tolist())
        puskesmas_filter = st.multiselect(
            "🏥 Pilih Puskesmas (bisa lebih dari 1)",
            puskesmas_options,
            default=["ALL"],
            key="pkp_puskesmas",
        )

    filtered_df = df.copy()
    if tahun_filter != "ALL":
        filtered_df = filtered_df[filtered_df[col_tahun].astype(str) == str(tahun_filter)]
    if puskesmas_filter:
        if "ALL" not in puskesmas_filter:
            filtered_df = filtered_df[filtered_df[col_puskesmas].astype(str).isin([str(x) for x in puskesmas_filter])]

    if filtered_df.empty:
        st.warning("⚠️ Tidak ada data sesuai filter yang dipilih.")
        return

    def _klarifikasi_table(title, indikator_key, total_sasaran, target_persen, target_sasaran, pencapaian, nilai_kerja):
        st.subheader(title)
        st.caption("Gunakan tabel di bawah untuk menyesuaikan nilai (klarifikasi). Klik Finalisasi untuk menyimpan.")

        single_puskesmas = (
            puskesmas_filter
            and "ALL" not in puskesmas_filter
            and len(puskesmas_filter) == 1
        )
        if not single_puskesmas:
            st.info("Klarifikasi hanya tersedia jika memilih 1 puskesmas saja.")

        edit_key = f"pkp_klarifikasi_edit_{indikator_key}"
        if edit_key not in st.session_state:
            st.session_state[edit_key] = False

        if st.button("Tambah Nilai Klarifikasi", key=f"pkp_add_klarifikasi_{indikator_key}", disabled=not single_puskesmas):
            st.session_state[edit_key] = True

        target_sasaran_round = math.ceil(target_sasaran) if target_sasaran is not None else 0
        nilai_kerja_pct = round(float(nilai_kerja) * 100, 1) if nilai_kerja is not None else 0
        base_row = {
            "Tahun": str(tahun_filter),
            "Puskesmas": str(puskesmas_filter[0]) if single_puskesmas else "ALL",
            "Indikator": indikator_key,
            "Total Sasaran": float(total_sasaran),
            "% Target": float(target_persen * 100),
            "Target Sasaran": float(target_sasaran_round),
            "Pencapaian": float(pencapaian),
            "% Nilai Kinerja": float(nilai_kerja_pct),
            "Aksi Klarifikasi": "Edit",
        }

        stored = pd.DataFrame()
        if single_puskesmas:
            stored = _load_klarifikasi_gs(str(tahun_filter), str(puskesmas_filter[0]), indikator_key)
            if stored.empty:
                stored = _load_klarifikasi(str(tahun_filter), str(puskesmas_filter[0]), indikator_key)

        if not stored.empty:
            row0 = stored.iloc[0]
            base_row.update(
                {
                    "Total Sasaran": float(row0["total_sasaran"]),
                    "% Target": float(row0["target_persen"]) * 100,
                    "Target Sasaran": float(math.ceil(row0["target_sasaran"])),
                    "Pencapaian": float(row0["pencapaian"]),
                    "% Nilai Kinerja": float(round(row0["nilai_kerja"] * 100, 1)),
                }
            )

        edit_df = st.data_editor(
            pd.DataFrame([base_row]),
            num_rows="fixed",
            use_container_width=True,
            key=f"pkp_klarifikasi_editor_{indikator_key}",
            disabled=not st.session_state[edit_key] or not single_puskesmas,
        )

        if st.button("Finalisasi", key=f"pkp_finalize_{indikator_key}", disabled=not single_puskesmas):
            row = edit_df.iloc[0].to_dict()
            save_row = pd.DataFrame(
                [
                    {
                        "tahun": row["Tahun"],
                        "puskesmas": row["Puskesmas"],
                        "indikator": row["Indikator"],
                        "total_sasaran": float(row["Total Sasaran"]),
                        "target_persen": float(row["% Target"]) / 100,
                        "target_sasaran": float(math.ceil(row["Target Sasaran"])),
                        "pencapaian": float(row["Pencapaian"]),
                        "nilai_kerja": float(row["% Nilai Kinerja"]) / 100,
                        "updated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                    }
                ]
            )
            if not _save_klarifikasi_gs(save_row):
                _save_klarifikasi(save_row)
            st.session_state[edit_key] = False
            st.success("Klarifikasi berhasil disimpan.")

    kpi_rows = []
    tab1, tab2 = st.tabs(["Indikator Kinerja PKP", "Visualisasi Kinerja"])

    with tab1:
            st.subheader("👩‍⚕️ Pelayanan Kesehatan Ibu Hamil")
            st.markdown("#### Indikator Kinerja: Ibu hamil mendapat suplementasi gizi")
            st.markdown(
                """
        **Definisi Operasional**  
        Persentase ibu hamil yang mendapat suplementasi gizi minimal 180 tablet selama kehamilan dibandingkan jumlah ibu hamil pada periode pelaporan.

        **Rumus Perhitungan**  
        `(Jumlah ibu hamil mendapat minimal 180 tablet TTD sampai bulan ini + Jumlah ibu hamil mendapat minimal 180 tablet MMS sampai bulan ini) / Jumlah sasaran ibu hamil × 100%`

        **Sumber Data**  
        Laporan Program Ibu Hamil (SIGIZI-KESGA) – Laporan Tahunan / TW.
                """
            )

            col_total_sasaran = _get_col(filtered_df, "Jumlah_sasaran_ibu_hamil")
            col_mms = _get_col(filtered_df, "Jumlah_ibu_hamil_mendapat_minimal_180_tablet_MMS")
            col_ttd = _get_col(filtered_df, "Jumlah_ibu_hamil_mendapat_minimal_180_tablet_TTD")

            missing = [c for c in [col_total_sasaran, col_mms, col_ttd] if c is None]
            if missing:
                st.error("❌ Kolom wajib untuk indikator ibu hamil tidak lengkap di data_pkp.")
                return

            total_sasaran = pd.to_numeric(filtered_df[col_total_sasaran], errors="coerce").sum()
            pencapaian = (
                pd.to_numeric(filtered_df[col_mms], errors="coerce").sum()
                + pd.to_numeric(filtered_df[col_ttd], errors="coerce").sum()
            )
            target_persen = 0.90
            target_sasaran = total_sasaran * target_persen
            nilai_kerja = (pencapaian / target_sasaran) if target_sasaran else 0
            nilai_kerja = 1 if nilai_kerja >= 1 else nilai_kerja

            st.subheader("📊 Score Card")
            cols = st.columns(3)
            cols[0].metric("Target", f"{target_persen * 100:.0f}%")
            cols[1].metric("Total Sasaran", f"{total_sasaran:.0f} Ibu Hamil")
            cols[2].metric("Target Sasaran", f"{target_sasaran:.0f}")
            cols2 = st.columns(3)
            cols2[0].metric("Pencapaian", f"{pencapaian:.0f}")
            cols2[1].metric("% Nilai Kinerja", f"{nilai_kerja * 100:.2f}%")

            _klarifikasi_table("Nilai Klarifikasi Puskesmas - Suplementasi Gizi", "suplementasi_gizi", total_sasaran, target_persen, target_sasaran, pencapaian, nilai_kerja)
            kpi_rows.append({
                    "indikator": "suplementasi_gizi",
                    "target_persen": target_persen,
                    "total_sasaran": total_sasaran,
                    "target_sasaran": target_sasaran,
                    "pencapaian": pencapaian,
                    "nilai_kerja": nilai_kerja,
                })


            st.markdown("---")
            st.markdown("#### Indikator Kinerja: Ibu hamil KEK mendapat makanan tambahan")
            st.markdown(
                """
        **Definisi Operasional**  
        Persentase ibu hamil risiko KEK (bumil KEK) yang mendapat PMT lokal dibandingkan jumlah ibu hamil risiko KEK pada periode pelaporan.

        **Rumus Perhitungan**  
        `Jumlah ibu hamil KEK yang mendapat PMT lokal / Jumlah ibu hamil risiko KEK × 100%`

        **Sumber Data**  
        Laporan Program Ibu Hamil (SIGIZI-KESGA) – Laporan Tahunan / TW.
                """
            )

            col_kek_sasaran = _get_col(filtered_df, "Jumlah_ibu_hamil_risiko_KEK_bumil_KEK")
            col_kek_pmt = _get_col(filtered_df, "Jumlah_ibu_hamil_KEK_mendapat_PMT")

            missing_kek = [c for c in [col_kek_sasaran, col_kek_pmt] if c is None]
            if missing_kek:
                st.error("❌ Kolom wajib untuk indikator ibu hamil KEK tidak lengkap di data_pkp.")
                return

            total_kek_sasaran = pd.to_numeric(filtered_df[col_kek_sasaran], errors="coerce").sum()
            kek_pencapaian = pd.to_numeric(filtered_df[col_kek_pmt], errors="coerce").sum()
            kek_target_persen = 0.84
            kek_target_sasaran = total_kek_sasaran * kek_target_persen
            kek_nilai_kerja = (kek_pencapaian / kek_target_sasaran) if kek_target_sasaran else 0
            kek_nilai_kerja = 1 if kek_nilai_kerja >= 1 else kek_nilai_kerja

            st.subheader("📊 Score Card (Ibu Hamil KEK)")
            cols = st.columns(3)
            cols[0].metric("Target", f"{kek_target_persen * 100:.0f}%")
            cols[1].metric("Total Sasaran", f"{total_kek_sasaran:.0f} Ibu Hamil")
            cols[2].metric("Target Sasaran", f"{kek_target_sasaran:.0f}")
            cols2 = st.columns(3)
            cols2[0].metric("Pencapaian", f"{kek_pencapaian:.0f}")
            cols2[1].metric("% Nilai Kinerja", f"{kek_nilai_kerja * 100:.2f}%")

            _klarifikasi_table("Nilai Klarifikasi Puskesmas - Ibu Hamil KEK", "kek_pmt", total_kek_sasaran, kek_target_persen, kek_target_sasaran, kek_pencapaian, kek_nilai_kerja)
            kpi_rows.append({
                    "indikator": "kek_pmt",
                    "target_persen": kek_target_persen,
                    "total_sasaran": total_kek_sasaran,
                    "target_sasaran": kek_target_sasaran,
                    "pencapaian": kek_pencapaian,
                    "nilai_kerja": kek_nilai_kerja,
                })


            st.markdown("---")
            st.subheader("👶 Pelayanan Kesehatan Bayi")
            st.markdown("#### Indikator Kinerja: Bayi usia 6 bulan mendapat ASI Eksklusif")
            st.markdown(
                """
        **Definisi Operasional**  
        Jumlah bayi usia sampai 6 bulan yang mendapat ASI eksklusif dibagi jumlah bayi usia 0–6 bulan yang ada, dikali 100%.

        **Rumus Perhitungan**  
        `Jumlah bayi usia 0–5 bulan yang mendapat ASI eksklusif berdasarkan recall 24 jam / Jumlah bayi usia 0–5 bulan yang direcall × 100%`

        **Sumber Data**  
        Laporan Program – Balita Gizi – Laporan Tahunan / TW (SIGIZI-KESGA).
                """
            )

            col_bayi_6 = _get_col(filtered_df, "Jumlah_bayi_usia_6_bulan")
            col_asi_eks = _get_col(filtered_df, "Jumlah_bayi_Asi_Eksklusif_sampai_6_bulan")

            missing_bayi = [c for c in [col_bayi_6, col_asi_eks] if c is None]
            if missing_bayi:
                st.error("❌ Kolom wajib untuk indikator ASI eksklusif tidak lengkap di data_pkp.")
                return

            total_bayi_6 = pd.to_numeric(filtered_df[col_bayi_6], errors="coerce").sum()
            asi_pencapaian = pd.to_numeric(filtered_df[col_asi_eks], errors="coerce").sum()
            asi_target_persen = 0.61
            asi_target_sasaran = total_bayi_6 * asi_target_persen
            asi_nilai_kerja = (asi_pencapaian / asi_target_sasaran) if asi_target_sasaran else 0
            asi_nilai_kerja = 1 if asi_nilai_kerja >= 1 else asi_nilai_kerja

            st.subheader("📊 Score Card (ASI Eksklusif)")
            cols = st.columns(3)
            cols[0].metric("Target", f"{asi_target_persen * 100:.0f}%")
            cols[1].metric("Total Sasaran", f"{total_bayi_6:.0f} Bayi")
            cols[2].metric("Target Sasaran", f"{asi_target_sasaran:.0f}")
            cols2 = st.columns(3)
            cols2[0].metric("Pencapaian", f"{asi_pencapaian:.0f}")
            cols2[1].metric("% Nilai Kinerja", f"{asi_nilai_kerja * 100:.2f}%")

            _klarifikasi_table("Nilai Klarifikasi Puskesmas - ASI Eksklusif", "asi_eksklusif", total_bayi_6, asi_target_persen, asi_target_sasaran, asi_pencapaian, asi_nilai_kerja)
            kpi_rows.append({
                    "indikator": "asi_eksklusif",
                    "target_persen": asi_target_persen,
                    "total_sasaran": total_bayi_6,
                    "target_sasaran": asi_target_sasaran,
                    "pencapaian": asi_pencapaian,
                    "nilai_kerja": asi_nilai_kerja,
                })


            st.markdown("---")
            st.subheader("🧒 Pelayanan Kesehatan Balita")
            st.markdown("#### Indikator Kinerja: Anak 6–23 bulan mendapatkan MP-ASI")
            st.markdown(
                """
        **Definisi Operasional**  
        Jumlah anak usia 6–23 bulan yang mendapat MP-ASI dibagi jumlah anak usia 6–23 bulan yang diwawancara, dikali 100%.

        **Rumus Perhitungan**  
        `Jumlah anak usia 6–23 bulan yang mendapat MP-ASI / Jumlah anak usia 6–23 bulan yang diwawancara × 100%`

        **Sumber Data**  
        Laporan Program – Balita Gizi – Laporan Tahunan / TW (SIGIZI-KESGA).
                """
            )

            col_mpasi_sasaran = _get_col(filtered_df, "MPASI__Sasaran")
            col_mpasi_baik = _get_col(filtered_df, "Jumlah_Balita_MPASI_Baik")

            missing_mpasi = [c for c in [col_mpasi_sasaran, col_mpasi_baik] if c is None]
            if missing_mpasi:
                st.error("❌ Kolom wajib untuk indikator MP-ASI tidak lengkap di data_pkp.")
                return

            total_mpasi_sasaran = pd.to_numeric(filtered_df[col_mpasi_sasaran], errors="coerce").sum()
            mpasi_pencapaian = pd.to_numeric(filtered_df[col_mpasi_baik], errors="coerce").sum()
            mpasi_target_persen = 0.73
            mpasi_target_sasaran = total_mpasi_sasaran * mpasi_target_persen
            mpasi_nilai_kerja = (mpasi_pencapaian / mpasi_target_sasaran) if mpasi_target_sasaran else 0
            mpasi_nilai_kerja = 1 if mpasi_nilai_kerja >= 1 else mpasi_nilai_kerja

            st.subheader("📊 Score Card (MP-ASI)")
            cols = st.columns(3)
            cols[0].metric("Target", f"{mpasi_target_persen * 100:.0f}%")
            cols[1].metric("Total Sasaran", f"{total_mpasi_sasaran:.0f} Balita")
            cols[2].metric("Target Sasaran", f"{mpasi_target_sasaran:.0f}")
            cols2 = st.columns(3)
            cols2[0].metric("Pencapaian", f"{mpasi_pencapaian:.0f}")
            cols2[1].metric("% Nilai Kinerja", f"{mpasi_nilai_kerja * 100:.2f}%")

            _klarifikasi_table("Nilai Klarifikasi Puskesmas - MP-ASI", "mpasi", total_mpasi_sasaran, mpasi_target_persen, mpasi_target_sasaran, mpasi_pencapaian, mpasi_nilai_kerja)
            kpi_rows.append({
                    "indikator": "mpasi",
                    "target_persen": mpasi_target_persen,
                    "total_sasaran": total_mpasi_sasaran,
                    "target_sasaran": mpasi_target_sasaran,
                    "pencapaian": mpasi_pencapaian,
                    "nilai_kerja": mpasi_nilai_kerja,
                })


            st.markdown("---")
            st.markdown("#### Indikator Kinerja: Pemberian Suplementasi Vitamin A pada Balita Usia 6–59 Bulan")
            st.markdown(
                """
        **Definisi Operasional**  
        Jumlah bayi 6–11 bulan mendapat kapsul vitamin A dibagi jumlah bayi 6–11 bulan dikali 100%  
        ditambah jumlah anak 12–59 bulan mendapat kapsul vitamin A dibagi jumlah anak 12–59 bulan dikali 100%.

        **Rumus Perhitungan**  
        `(Jumlah bayi 6–11 bulan mendapat Vitamin A / Jumlah bayi 6–11 bulan) + (Jumlah anak 12–59 bulan mendapat Vitamin A / Jumlah anak 12–59 bulan)` (dalam %).

        **Sumber Data**  
        Laporan Program – Balita Gizi – Laporan Tahunan / TW (SIGIZI-KESGA).
                """
            )

            col_bayi_6_11 = _get_col(filtered_df, "Jumlah_bayi_6-11_bulan")
            col_bayi_6_11_vit = _get_col(filtered_df, "Jumlah_bayi_6-11_bulan_mendapat_Vitamin_A")
            col_anak_12_59 = _get_col(filtered_df, "Jumlah_anak_12-59_bulan")
            col_anak_12_59_vit = _get_col(filtered_df, "Jumlah_anak_12-59_bulan_mendapat_Vitamin_A")

            missing_vit = [c for c in [col_bayi_6_11, col_bayi_6_11_vit, col_anak_12_59, col_anak_12_59_vit] if c is None]
            if missing_vit:
                st.error("❌ Kolom wajib untuk indikator Vitamin A tidak lengkap di data_pkp.")
                return

            total_vit_sasaran = (
                pd.to_numeric(filtered_df[col_bayi_6_11], errors="coerce").sum()
                + pd.to_numeric(filtered_df[col_anak_12_59], errors="coerce").sum()
            )
            vit_pencapaian = (
                pd.to_numeric(filtered_df[col_bayi_6_11_vit], errors="coerce").sum()
                + pd.to_numeric(filtered_df[col_anak_12_59_vit], errors="coerce").sum()
            )
            vit_target_persen = 0.91
            vit_target_sasaran = total_vit_sasaran * vit_target_persen
            vit_nilai_kerja = (vit_pencapaian / vit_target_sasaran) if vit_target_sasaran else 0
            vit_nilai_kerja = 1 if vit_nilai_kerja >= 1 else vit_nilai_kerja

            st.subheader("📊 Score Card (Vitamin A)")
            cols = st.columns(3)
            cols[0].metric("Target", f"{vit_target_persen * 100:.0f}%")
            cols[1].metric("Total Sasaran", f"{total_vit_sasaran:.0f} Balita")
            cols[2].metric("Target Sasaran", f"{vit_target_sasaran:.0f}")
            cols2 = st.columns(3)
            cols2[0].metric("Pencapaian", f"{vit_pencapaian:.0f}")
            cols2[1].metric("% Nilai Kinerja", f"{vit_nilai_kerja * 100:.2f}%")

            _klarifikasi_table("Nilai Klarifikasi Puskesmas - Vitamin A", "vitamin_a", total_vit_sasaran, vit_target_persen, vit_target_sasaran, vit_pencapaian, vit_nilai_kerja)
            kpi_rows.append({
                    "indikator": "vitamin_a",
                    "target_persen": vit_target_persen,
                    "total_sasaran": total_vit_sasaran,
                    "target_sasaran": vit_target_sasaran,
                    "pencapaian": vit_pencapaian,
                    "nilai_kerja": vit_nilai_kerja,
                })


            st.markdown("---")
            st.markdown("#### Indikator Kinerja: Pemberian tambahan asupan gizi bagi balita gizi kurang")
            st.markdown(
                """
        **Definisi Operasional**  
        Jumlah balita gizi kurang yang mendapat tambahan asupan gizi dibagi jumlah seluruh balita gizi kurang, dikali 100%.

        **Rumus Perhitungan**  
        `Jumlah balita gizi kurang usia 6–59 bulan yang mendapatkan PMT lokal / Jumlah balita usia 6–59 bulan gizi kurang × 100%`

        **Sumber Data**  
        Laporan Program – Balita Gizi – Laporan Tahunan / TW (SIGIZI-KESGA).
                """
            )

            col_gizi_kurang = _get_col(filtered_df, "Jumlah_balita_usia_6-59_bulan_gizi_kurang")
            col_pmt_lokal = _get_col(filtered_df, "Jumlah_balita_gizi_kurang_usia_6-59_bulan_yang_mendapatkan_PMT_Lokal")

            missing_pmt = [c for c in [col_gizi_kurang, col_pmt_lokal] if c is None]
            if missing_pmt:
                st.error("❌ Kolom wajib untuk indikator PMT balita gizi kurang tidak lengkap di data_pkp.")
                return

            total_gizi_kurang = pd.to_numeric(filtered_df[col_gizi_kurang], errors="coerce").sum()
            pmt_pencapaian = pd.to_numeric(filtered_df[col_pmt_lokal], errors="coerce").sum()
            pmt_target_persen = 0.65
            pmt_target_sasaran = total_gizi_kurang * pmt_target_persen
            pmt_nilai_kerja = (pmt_pencapaian / pmt_target_sasaran) if pmt_target_sasaran else 0
            pmt_nilai_kerja = 1 if pmt_nilai_kerja >= 1 else pmt_nilai_kerja

            st.subheader("📊 Score Card (PMT Balita Gizi Kurang)")
            cols = st.columns(3)
            cols[0].metric("Target", f"{pmt_target_persen * 100:.0f}%")
            cols[1].metric("Total Sasaran", f"{total_gizi_kurang:.0f} Balita")
            cols[2].metric("Target Sasaran", f"{pmt_target_sasaran:.0f}")
            cols2 = st.columns(3)
            cols2[0].metric("Pencapaian", f"{pmt_pencapaian:.0f}")
            cols2[1].metric("% Nilai Kinerja", f"{pmt_nilai_kerja * 100:.2f}%")

            _klarifikasi_table("Nilai Klarifikasi Puskesmas - PMT Balita Gizi Kurang", "pmt_gizi_kurang", total_gizi_kurang, pmt_target_persen, pmt_target_sasaran, pmt_pencapaian, pmt_nilai_kerja)
            kpi_rows.append({
                    "indikator": "pmt_gizi_kurang",
                    "target_persen": pmt_target_persen,
                    "total_sasaran": total_gizi_kurang,
                    "target_sasaran": pmt_target_sasaran,
                    "pencapaian": pmt_pencapaian,
                    "nilai_kerja": pmt_nilai_kerja,
                })


            st.markdown("---")
            st.markdown("#### Indikator Kinerja: Balita gizi buruk mendapat perawatan sesuai standar tatalaksana gizi buruk")
            st.markdown(
                """
        **Definisi Operasional**  
        Jumlah balita gizi buruk (bayi 0–5 bulan + balita 6–59 bulan) yang mendapat perawatan sesuai standar dibagi jumlah seluruh kasus gizi buruk, dikali 100%.

        **Rumus Perhitungan**  
        `(Jumlah kasus gizi buruk bayi 0–5 bulan mendapat perawatan + Jumlah kasus gizi buruk balita 6–59 bulan mendapat perawatan) / (Jumlah kasus gizi buruk bayi 0–5 bulan + Jumlah kasus gizi buruk balita 6–59 bulan) × 100%`

        **Sumber Data**  
        Laporan Program – Balita Gizi – Laporan Tahunan / TW (SIGIZI-KESGA).
                """
            )

            col_gb_05 = _get_col(filtered_df, "Jumlah_kasus_gizi_buruk_bayi_0-5_Bulan")
            col_gb_05_rawat = _get_col(filtered_df, "Jumlah_Kasus_gizi_buruk_bayi_0-5_Bulan_mendapat_perawatan")
            col_gb_659 = _get_col(filtered_df, "Jumlah_kasus_gizi_buruk_Balita_6-59_Bulan")
            col_gb_659_rawat = _get_col(filtered_df, "Jumlah_Kasus_Gizi_Buruk_Balita_6-59_Bulan_mendapat_perawatan")

            missing_gb = [c for c in [col_gb_05, col_gb_05_rawat, col_gb_659, col_gb_659_rawat] if c is None]
            if missing_gb:
                st.error("❌ Kolom wajib untuk indikator perawatan gizi buruk tidak lengkap di data_pkp.")
                return

            total_gb = (
                pd.to_numeric(filtered_df[col_gb_05], errors="coerce").sum()
                + pd.to_numeric(filtered_df[col_gb_659], errors="coerce").sum()
            )
            gb_pencapaian = (
                pd.to_numeric(filtered_df[col_gb_05_rawat], errors="coerce").sum()
                + pd.to_numeric(filtered_df[col_gb_659_rawat], errors="coerce").sum()
            )
            gb_target_persen = 0.91
            gb_target_sasaran = total_gb * gb_target_persen
            gb_nilai_kerja = (gb_pencapaian / gb_target_sasaran) if gb_target_sasaran else 0
            gb_nilai_kerja = 1 if gb_nilai_kerja >= 1 else gb_nilai_kerja

            st.subheader("📊 Score Card (Perawatan Gizi Buruk)")
            cols = st.columns(3)
            cols[0].metric("Target", f"{gb_target_persen * 100:.0f}%")
            cols[1].metric("Total Sasaran", f"{total_gb:.0f} Balita")
            cols[2].metric("Target Sasaran", f"{gb_target_sasaran:.0f}")
            cols2 = st.columns(3)
            cols2[0].metric("Pencapaian", f"{gb_pencapaian:.0f}")
            cols2[1].metric("% Nilai Kinerja", f"{gb_nilai_kerja * 100:.2f}%")

            _klarifikasi_table("Nilai Klarifikasi Puskesmas - Perawatan Gizi Buruk", "perawatan_gizi_buruk", total_gb, gb_target_persen, gb_target_sasaran, gb_pencapaian, gb_nilai_kerja)
            kpi_rows.append({
                    "indikator": "perawatan_gizi_buruk",
                    "target_persen": gb_target_persen,
                    "total_sasaran": total_gb,
                    "target_sasaran": gb_target_sasaran,
                    "pencapaian": gb_pencapaian,
                    "nilai_kerja": gb_nilai_kerja,
                })


            st.markdown("---")
            st.subheader("🥗 Program Gizi")
            st.markdown("#### Indikator Kinerja: Stunting")
            st.markdown(
                """
        **Definisi Operasional**  
        Jumlah balita pendek dan sangat pendek dibagi jumlah balita yang diukur panjang/tinggi badan, dikali 100%.

        **Rumus Perhitungan**  
        `Jumlah kasus balita sangat pendek + pendek (TB/U) / Jumlah balita diukur × 100%`

        **Sumber Data**  
        Pelayanan Kesehatan – Rekap Status Gizi (sudah diverifikasi).
                """
            )

            col_sasaran_timbang = _get_col(filtered_df, "Sasaran Balita Timbang")
            col_stunting = _get_col(filtered_df, "Stunting")

            missing_stunt = [c for c in [col_sasaran_timbang, col_stunting] if c is None]
            if missing_stunt:
                st.error("❌ Kolom wajib untuk indikator Stunting tidak lengkap di data_pkp.")
                return

            total_timbang = pd.to_numeric(filtered_df[col_sasaran_timbang], errors="coerce").sum()
            stunting_pencapaian = pd.to_numeric(filtered_df[col_stunting], errors="coerce").sum()
            stunting_target_persen = 0.156
            stunting_target_sasaran = total_timbang * stunting_target_persen

            stunting_rate = (stunting_pencapaian / total_timbang * 100) if total_timbang else 0
            if stunting_rate <= 2.5:
                stunting_nilai_kerja = 1.0
            elif stunting_rate <= 10:
                stunting_nilai_kerja = 0.901
            elif stunting_rate <= 20:
                stunting_nilai_kerja = 0.801
            elif stunting_rate <= 30:
                stunting_nilai_kerja = 0.701
            else:
                stunting_nilai_kerja = 0.70

            st.subheader("📊 Score Card (Stunting)")
            cols = st.columns(3)
            cols[0].metric("Target", f"{stunting_target_persen * 100:.1f}%")
            cols[1].metric("Total Sasaran", f"{total_timbang:.0f} Balita")
            cols[2].metric("Target Sasaran", f"{stunting_target_sasaran:.1f}")
            cols2 = st.columns(3)
            cols2[0].metric("Pencapaian", f"{stunting_pencapaian:.0f}")
            cols2[1].metric("% Nilai Kinerja", f"{stunting_nilai_kerja * 100:.1f}%")

            _klarifikasi_table("Nilai Klarifikasi Puskesmas - Stunting", "stunting", total_timbang, stunting_target_persen, stunting_target_sasaran, stunting_pencapaian, stunting_nilai_kerja)
            kpi_rows.append({
                    "indikator": "stunting",
                    "target_persen": stunting_target_persen,
                    "total_sasaran": total_timbang,
                    "target_sasaran": stunting_target_sasaran,
                    "pencapaian": stunting_pencapaian,
                    "nilai_kerja": stunting_nilai_kerja,
                })


            st.markdown("---")
            st.markdown("#### Indikator Kinerja: Underweight")
            st.markdown(
                """
        **Definisi Operasional**  
        Jumlah balita BB kurang dan sangat kurang dibagi jumlah balita yang diukur berat badannya, dikali 100%.

        **Rumus Perhitungan**  
        `Jumlah kasus balita BB Sangat Kurang + Sangat Kurang (BB/U) / Jumlah balita diukur × 100%`

        **Sumber Data**  
        Pelayanan Kesehatan – Rekap Status Gizi (sudah diverifikasi).
                """
            )

            col_underweight = _get_col(filtered_df, "Underweight")
            missing_under = [c for c in [col_sasaran_timbang, col_underweight] if c is None]
            if missing_under:
                st.error("❌ Kolom wajib untuk indikator Underweight tidak lengkap di data_pkp.")
                return

            under_pencapaian = pd.to_numeric(filtered_df[col_underweight], errors="coerce").sum()
            under_target_persen = 0.15
            under_target_sasaran = total_timbang * under_target_persen
            under_nilai_kerja = (under_pencapaian / under_target_sasaran) if under_target_sasaran else 0
            under_nilai_kerja = 1 if under_nilai_kerja >= 1 else under_nilai_kerja

            st.subheader("📊 Score Card (Underweight)")
            cols = st.columns(3)
            cols[0].metric("Target", f"{under_target_persen * 100:.0f}%")
            cols[1].metric("Total Sasaran", f"{total_timbang:.0f} Balita")
            cols[2].metric("Target Sasaran", f"{under_target_sasaran:.1f}")
            cols2 = st.columns(3)
            cols2[0].metric("Pencapaian", f"{under_pencapaian:.0f}")
            cols2[1].metric("% Nilai Kinerja", f"{under_nilai_kerja * 100:.1f}%")

            _klarifikasi_table("Nilai Klarifikasi Puskesmas - Underweight", "underweight", total_timbang, under_target_persen, under_target_sasaran, under_pencapaian, under_nilai_kerja)
            kpi_rows.append({
                    "indikator": "underweight",
                    "target_persen": under_target_persen,
                    "total_sasaran": total_timbang,
                    "target_sasaran": under_target_sasaran,
                    "pencapaian": under_pencapaian,
                    "nilai_kerja": under_nilai_kerja,
                })


            st.markdown("---")
            st.markdown("#### Indikator Kinerja: Wasting")
            st.markdown(
                """
        **Definisi Operasional**  
        Jumlah balita gizi kurang dan gizi buruk dibagi jumlah balita yang diukur berat badan dan panjang/tinggi badan, dikali 100%.

        **Rumus Perhitungan**  
        `Jumlah kasus balita gizi buruk + gizi kurang (BB/TB) / Jumlah balita diukur × 100%`

        **Sumber Data**  
        Pelayanan Kesehatan – Rekap Status Gizi (sudah diverifikasi).
                """
            )

            col_wasting = _get_col(filtered_df, "Wasting")
            missing_waste = [c for c in [col_sasaran_timbang, col_wasting] if c is None]
            if missing_waste:
                st.error("❌ Kolom wajib untuk indikator Wasting tidak lengkap di data_pkp.")
                return

            waste_pencapaian = pd.to_numeric(filtered_df[col_wasting], errors="coerce").sum()
            waste_target_persen = 0.08
            waste_target_sasaran = total_timbang * waste_target_persen
            waste_nilai_kerja = (waste_pencapaian / waste_target_sasaran) if waste_target_sasaran else 0
            waste_nilai_kerja = 1 if waste_nilai_kerja >= 1 else waste_nilai_kerja

            st.subheader("📊 Score Card (Wasting)")
            cols = st.columns(3)
            cols[0].metric("Target", f"{waste_target_persen * 100:.0f}%")
            cols[1].metric("Total Sasaran", f"{total_timbang:.0f} Balita")
            cols[2].metric("Target Sasaran", f"{waste_target_sasaran:.1f}")
            cols2 = st.columns(3)
            cols2[0].metric("Pencapaian", f"{waste_pencapaian:.0f}")
            cols2[1].metric("% Nilai Kinerja", f"{waste_nilai_kerja * 100:.1f}%")

            _klarifikasi_table("Nilai Klarifikasi Puskesmas - Wasting", "wasting", total_timbang, waste_target_persen, waste_target_sasaran, waste_pencapaian, waste_nilai_kerja)
            kpi_rows.append({
                    "indikator": "wasting",
                    "target_persen": waste_target_persen,
                    "total_sasaran": total_timbang,
                    "target_sasaran": waste_target_sasaran,
                    "pencapaian": waste_pencapaian,
                    "nilai_kerja": waste_nilai_kerja,
                })


            st.markdown("---")
            st.subheader("🧑‍🎓 Pelayanan Kesehatan Anak Usia Sekolah")
            st.markdown("#### Indikator Kinerja: Remaja putri mengonsumsi tablet tambah darah")
            st.markdown(
                """
        **Definisi Operasional**  
        Jumlah remaja putri SMP/Sederajat kelas 7 dan SMA/Sederajat kelas 10 yang mengonsumsi tablet tambah darah dibagi jumlah sasaran jumlah siswi SMP dan SMA sederajat, dikali 100%.

        **Rumus Perhitungan**  
        `Jumlah remaja putri mengonsumsi TTD sesuai standar / Jumlah sasaran remaja putri × 100%`

        **Sumber Data**  
        Laporan Program – Rematri – Laporan Tahunan / TW (SIGIZI-KESGA).
                """
            )

            col_rematri_sasaran = _get_col(filtered_df, "Jumlah_sasaran_rematri")
            col_rematri_ttd = _get_col(filtered_df, "Jumlah_Rematri_mengkonsumsi_TTD_sesuai_standar")

            missing_rematri = [c for c in [col_rematri_sasaran, col_rematri_ttd] if c is None]
            if missing_rematri:
                st.warning("Kolom wajib untuk indikator Remaja Putri TTD tidak lengkap di data_pkp. Indikator dilewati.")
            else:
                total_rematri = pd.to_numeric(filtered_df[col_rematri_sasaran], errors="coerce").sum()
                rematri_pencapaian = pd.to_numeric(filtered_df[col_rematri_ttd], errors="coerce").sum()
                rematri_target_persen = 0.65
                rematri_target_sasaran = total_rematri * rematri_target_persen
                rematri_nilai_kerja = (rematri_pencapaian / rematri_target_sasaran) if rematri_target_sasaran else 0
                rematri_nilai_kerja = 1 if rematri_nilai_kerja >= 1 else rematri_nilai_kerja

                st.subheader("📊 Score Card (Remaja Putri TTD)")
                cols = st.columns(3)
                cols[0].metric("Target", f"{rematri_target_persen * 100:.0f}%")
                cols[1].metric("Total Sasaran", f"{total_rematri:.0f} Remaja Putri")
                cols[2].metric("Target Sasaran", f"{rematri_target_sasaran:.1f}")
                cols2 = st.columns(3)
                cols2[0].metric("Pencapaian", f"{rematri_pencapaian:.0f}")
                cols2[1].metric("% Nilai Kinerja", f"{rematri_nilai_kerja * 100:.1f}%")

                _klarifikasi_table("Nilai Klarifikasi Puskesmas - Remaja Putri TTD", "rematri_ttd", total_rematri, rematri_target_persen, rematri_target_sasaran, rematri_pencapaian, rematri_nilai_kerja)
                kpi_rows.append({
                        "indikator": "rematri_ttd",
                        "target_persen": rematri_target_persen,
                        "total_sasaran": total_rematri,
                        "target_sasaran": rematri_target_sasaran,
                        "pencapaian": rematri_pencapaian,
                        "nilai_kerja": rematri_nilai_kerja,
                    })


            st.markdown("---")
            st.subheader("Ringkasan Klarifikasi Puskesmas")
            st.caption("Ringkasan ini menggabungkan data klarifikasi. Jika ada perubahan di Google Sheet, data tersebut diprioritaskan dibanding SQLite.")

            gs_all = _load_all_klarifikasi_gs()
            sql_all = _load_all_klarifikasi_sqlite()

            if gs_all.empty and sql_all.empty:
                st.info("Belum ada data klarifikasi.")
            else:
                def _normalize(df):
                    if df.empty:
                        return df
                    df = df.copy()
                    for col in ["tahun", "puskesmas", "indikator"]:
                        if col in df.columns:
                            df[col] = df[col].astype(str)
                    return df

                gs_all = _normalize(gs_all)
                sql_all = _normalize(sql_all)

                key_cols = ["tahun", "puskesmas", "indikator"]
                has_keys_gs = not gs_all.empty and all(c in gs_all.columns for c in key_cols)
                has_keys_sql = not sql_all.empty and all(c in sql_all.columns for c in key_cols)

                if has_keys_gs and has_keys_sql:
                    sql_all = sql_all[~sql_all.set_index(key_cols).index.isin(gs_all.set_index(key_cols).index)]

                merged = pd.concat([gs_all, sql_all], ignore_index=True)

                col1, col2, col3 = st.columns(3)
                with col1:
                    tahun_opts = ["ALL"] + sorted(merged["tahun"].unique().tolist())
                    tahun_sum = st.selectbox("Tahun", tahun_opts, key="pkp_sum_tahun")
                with col2:
                    puskesmas_opts = ["ALL"] + sorted(merged["puskesmas"].unique().tolist())
                    puskesmas_sum = st.selectbox("Puskesmas", puskesmas_opts, key="pkp_sum_puskesmas")
                with col3:
                    indikator_opts = ["ALL"] + sorted(merged["indikator"].unique().tolist())
                    indikator_sum = st.selectbox("Indikator", indikator_opts, key="pkp_sum_indikator")

                with st.expander("Reset Nilai Klarifikasi (opsional)", expanded=False):
                    st.caption("Gunakan fitur ini untuk menghapus nilai klarifikasi sesuai filter di atas. Hati-hati, tindakan ini tidak bisa dibatalkan.")
                    confirm_reset = st.checkbox("Saya paham dan ingin menghapus data sesuai filter", value=False, key="pkp_confirm_reset")
                    if st.button("Reset Data Klarifikasi", disabled=not confirm_reset, key="pkp_reset_btn"):
                        ok_gs = _reset_klarifikasi_gs(tahun_sum, puskesmas_sum, indikator_sum)
                        ok_sql = _reset_klarifikasi_sqlite(tahun_sum, puskesmas_sum, indikator_sum)
                        if ok_gs and ok_sql:
                            st.success("Data klarifikasi berhasil dihapus sesuai filter.")
                            st.cache_data.clear()
                        else:
                            st.warning("Sebagian data tidak terhapus. Coba ulang atau periksa koneksi GSheet/SQLite.")

                summary_df = merged.copy()
                if tahun_sum != "ALL":
                    summary_df = summary_df[summary_df["tahun"] == str(tahun_sum)]
                if puskesmas_sum != "ALL":
                    summary_df = summary_df[summary_df["puskesmas"] == str(puskesmas_sum)]
                if indikator_sum != "ALL":
                    summary_df = summary_df[summary_df["indikator"] == str(indikator_sum)]

                if summary_df.empty:
                    st.info("Tidak ada data sesuai filter.")
                else:
                    display_cols = [
                        "tahun",
                        "puskesmas",
                        "indikator",
                        "total_sasaran",
                        "target_persen",
                        "target_sasaran",
                        "pencapaian",
                        "nilai_kerja",
                        "updated_at",
                        "source",
                    ]
                    for col in display_cols:
                        if col not in summary_df.columns:
                            summary_df[col] = ""

                    summary_df = summary_df[display_cols]
                    if "target_sasaran" in summary_df.columns:
                        summary_df["target_sasaran"] = summary_df["target_sasaran"].apply(lambda x: math.ceil(x) if str(x) not in ["", "nan", "None"] else x)
                    if "nilai_kerja" in summary_df.columns:
                        summary_df["nilai_kerja"] = summary_df["nilai_kerja"].apply(lambda x: round(float(x) * 100, 1) if str(x) not in ["", "nan", "None"] else x)

                    summary_df = summary_df.sort_values(["tahun", "puskesmas", "indikator", "updated_at"], ascending=[False, True, True, False])

                    def _highlight_source(row):
                        if str(row.get("source", "")).lower() == "gsheet":
                            return ["background-color: #E3F2FD"] * len(row)
                        return [""] * len(row)

                    styled_summary = summary_df.style.apply(_highlight_source, axis=1)
                    st.dataframe(styled_summary, use_container_width=True)

                    csv_bytes = summary_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "Download Ringkasan (CSV)",
                        data=csv_bytes,
                        file_name="ringkasan_klarifikasi_pkp.csv",
                        mime="text/csv",
                    )

                    xlsx_buffer = io.BytesIO()
                    with pd.ExcelWriter(xlsx_buffer, engine="xlsxwriter") as writer:
                        summary_df.to_excel(writer, index=False, sheet_name="Ringkasan")
                    st.download_button(
                        "Download Ringkasan (Excel)",
                        data=xlsx_buffer.getvalue(),
                        file_name="ringkasan_klarifikasi_pkp.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

    with tab2:
        st.subheader("Visualisasi Kinerja")
        st.caption("Ringkasan visual kinerja tiap indikator berdasarkan target, pencapaian, dan nilai kerja.")

        if not kpi_rows:
            st.info("Belum ada data indikator untuk divisualisasikan.")
            return

        kpi_df = pd.DataFrame(kpi_rows)
        kpi_df["pencapaian_pct"] = (kpi_df["pencapaian"] / kpi_df["target_sasaran"]).replace([float("inf")], 0).fillna(0) * 100
        kpi_df["nilai_kerja_pct"] = kpi_df["nilai_kerja"] * 100

        st.subheader("Ringkasan Indikator")
        st.dataframe(kpi_df, use_container_width=True)

        st.subheader("% Nilai Kerja per Indikator")
        chart_df = kpi_df.set_index("indikator")[["nilai_kerja_pct"]].sort_values("nilai_kerja_pct", ascending=False)
        st.bar_chart(chart_df)

        st.subheader("% Pencapaian vs Target per Indikator")
        chart_df2 = kpi_df.set_index("indikator")[["pencapaian_pct"]].sort_values("pencapaian_pct", ascending=False)
        st.bar_chart(chart_df2)

        top = kpi_df.sort_values("nilai_kerja_pct", ascending=False).head(3)
        bottom = kpi_df.sort_values("nilai_kerja_pct", ascending=True).head(3)
        st.markdown("**Insight Cepat**")
        st.markdown(f"- Tertinggi: {', '.join(top['indikator'].tolist())}")
        st.markdown(f"- Terendah: {', '.join(bottom['indikator'].tolist())}")

        st.markdown("---")
        st.subheader("Heatmap Indikator vs Puskesmas")
        gs_all = _load_all_klarifikasi_gs()
        sql_all = _load_all_klarifikasi_sqlite()
        merged = pd.concat([gs_all, sql_all], ignore_index=True)
        if merged.empty:
            st.info("Belum ada data klarifikasi untuk visualisasi.")
        else:
            merged = merged.copy()
            merged["nilai_kerja_pct"] = merged["nilai_kerja"].astype(float) * 100
            heat = merged.pivot_table(
                index="puskesmas",
                columns="indikator",
                values="nilai_kerja_pct",
                aggfunc="mean",
                fill_value=0,
            )
            fig_heat = px.imshow(
                heat,
                text_auto=True,
                aspect="auto",
                color_continuous_scale="YlGnBu",
                title="Heatmap Nilai Kinerja (%)"
            )
            st.plotly_chart(fig_heat, use_container_width=True)

            st.subheader("Tabel Indikator vs Puskesmas")
            st.dataframe(heat.reset_index(), use_container_width=True)

        st.markdown("---")
        st.subheader("KPI Gauge per Indikator")
        if not kpi_rows:
            st.info("Belum ada data indikator untuk divisualisasikan.")
        else:
            indikator_sel = st.selectbox("Pilih Indikator", kpi_df["indikator"].tolist(), key="kpi_gauge_indikator")
            row = kpi_df[kpi_df["indikator"] == indikator_sel].iloc[0]
            fig_gauge = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=row["nilai_kerja_pct"],
                    title={"text": f"Nilai Kerja {indikator_sel} (%)"},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": "#1976D2"},
                        "steps": [
                            {"range": [0, 60], "color": "#FFCDD2"},
                            {"range": [60, 80], "color": "#FFF9C4"},
                            {"range": [80, 100], "color": "#C8E6C9"},
                        ],
                    },
                )
            )
            st.plotly_chart(fig_gauge, use_container_width=True)

        st.markdown("---")
        st.subheader("Ranking Puskesmas per Indikator")
        indikator_rank = st.selectbox("Pilih Indikator (Ranking)", kpi_df["indikator"].tolist(), key="kpi_rank_indikator")
        merged = pd.concat([gs_all, sql_all], ignore_index=True)
        if merged.empty:
            st.info("Belum ada data klarifikasi untuk ranking.")
        else:
            merged = merged.copy()
            merged["nilai_kerja_pct"] = merged["nilai_kerja"].astype(float) * 100
            rank_df = merged[merged["indikator"] == indikator_rank].copy()
            if rank_df.empty:
                st.info("Tidak ada data untuk indikator ini.")
            else:
                rank_df = rank_df.sort_values("nilai_kerja_pct", ascending=False)
                st.dataframe(rank_df[["puskesmas", "tahun", "nilai_kerja_pct", "updated_at", "source"]], use_container_width=True)
