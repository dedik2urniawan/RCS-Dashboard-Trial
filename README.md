# RCS Dashboard

**RCS Dashboard** adalah aplikasi berbasis web yang dikembangkan untuk menganalisis dan memvisualisasikan indikator kesehatan masyarakat di Indonesia dengan basis data pada Platform SIGIZI-KESGA [SIGZI Web APP](https://sigizikesga.kemkes.go.id/login_sisfo/), dengan fokus pada data balita, ibu hamil, remaja putri, dan evaluasi program gizi berbasis masyarakat (EPPGBM). Aplikasi ini dibangun menggunakan **Streamlit** untuk antarmuka pengguna interaktif, **SQLite** sebagai basis data, dan pustaka visualisasi seperti **Plotly** dan **Matplotlib**. Proyek ini bertujuan untuk memberikan wawasan berbasis data kepada pemangku kepentingan di bidang kesehatan, khususnya Dinas Kesehatan dan Puskesmas.

Proyek ini saat ini **on progress**, dengan beberapa modul sudah selesai dan di-deploy ke [Streamlit Community Cloud](https://streamlit.io/cloud), sementara modul lainnya masih dalam tahap pengembangan.

---

## **Fitur Utama**

### **Fitur yang Sudah Selesai**
1. **Dashboard Indikator Balita Gizi (`dashboard_balita_gizi.py`)**
   - **Fungsi**: Analisis mendalam indikator gizi balita, termasuk kepatuhan pelaporan, kelengkapan data, pertumbuhan & perkembangan, ASI eksklusif & MPASI, masalah gizi, tatalaksana balita bermasalah gizi, dan suplementasi zat gizi mikro.
   - **Visualisasi**: Bar chart, line chart, dan metrik interaktif menggunakan Plotly.
   - **Fitur Tambahan**: Filter data (bulan, puskesmas, kelurahan), tabel rekapitulasi, dan generasi laporan PDF menggunakan `reportlab`.
   - **Status**: 100% selesai dan terintegrasi dalam aplikasi utama.

2. **Upload Data (`upload_data.py`)**
   - **Fungsi**: Memungkinkan pengguna (khususnya `admin_dinkes`) mengunggah file Excel ke database SQLite (`rcs_data.db`).
   - **Jenis Data**: Mendukung upload untuk Balita Gizi, Balita KIA, Ibu Hamil, Remaja Putri, EPPGBM, dan Dataset Desa (referensi).
   - **Fitur Tambahan**: Petunjuk teknis, link template Google Drive, dan validasi format file.
   - **Status**: 100% selesai dan berfungsi sebagai modul pendukung semua dashboard.

3. **Autentikasi dan Navigasi (`app.py`)**
   - **Fungsi**: Mengatur autentikasi pengguna (login/logout), manajemen sesi dengan timeout (30 menit), dan navigasi antar dashboard.
   - **Role**: Mendukung `admin_dinkes` (akses penuh) dan `admin_puskesmas` (akses terbatas).
   - **Status**: 100% selesai sebagai backbone aplikasi.

### **Fitur dalam Pengembangan**
1. **Dashboard Indikator Balita KIA (`dashboard_balita_kia.py`)**
   - **Progress**: Saat ini hanya placeholder dengan visualisasi sederhana (bar chart distribusi balita per wilayah).
   - **Rencana**: Menambahkan filter, analisis kepatuhan & kelengkapan, metrik spesifik KIA (misalnya kepemilikan buku KIA, imunisasi), dan laporan PDF.
   - **Status**: ~10% selesai.

2. **Dashboard Indikator Ibu Hamil (`dashboard_ibuhamil.py`)**
   - **Progress**: Belum dimulai.
   - **Rencana**: Analisis indikator seperti kunjungan antenatal, suplementasi zat besi, dan status gizi ibu hamil.
   - **Status**: 0% selesai.

3. **Dashboard Indikator Remaja Putri (`dashboard_remaja.py`)**
   - **Progress**: Belum dimulai.
   - **Rencana**: Analisis suplementasi tablet tambah darah, status anemia, dan edukasi gizi.
   - **Status**: 0% selesai.

4. **Dashboard EPPGBM (`dashboard_eppgbm.py`)**
   - **Progress**: Belum dimulai.
   - **Rencana**: Evaluasi program gizi berbasis masyarakat dengan metrik spesifik (misalnya cakupan intervensi gizi).
   - **Status**: 0% selesai.

---

## **Arsitektur Teknis**

### **Stack Teknologi**
- **Frontend**: Streamlit (UI interaktif)
- **Backend**: Python 3.8+
- **Database**: SQLite (`rcs_data.db`)
- **Data Processing**: Pandas
- **Visualisasi**: Plotly, Matplotlib
- **PDF Generation**: ReportLab
- **Deployment**: Streamlit Community Cloud

### **Struktur Direktori**
```
rcs_dashboard/
├── app.py                # Entry point aplikasi
├── dashboard_balita_gizi.py  # Dashboard Balita Gizi (selesai)
├── dashboard_balita_kia.py   # Dashboard Balita KIA (on progress)
├── dashboard_ibuhamil.py     # Dashboard Ibu Hamil (TBD)
├── dashboard_remaja.py       # Dashboard Remaja Putri (TBD)
├── dashboard_eppgbm.py       # Dashboard EPPGBM (TBD)
├── upload_data.py        # Modul upload data (selesai)
├── auth.py               # Modul autentikasi (asumsi ada)
├── rcs_data.db           # Database SQLite (contoh)
└── README.md             # Dokumentasi proyek
```

### **Alur Data**
1. **Input**: Pengguna mengunggah file Excel melalui `upload_data.py`, disimpan ke `rcs_data.db`.
2. **Processing**: Data diambil dari SQLite, difilter, dan dianalisis di masing-masing dashboard.
3. **Output**: Visualisasi interaktif, tabel rekapitulasi, dan laporan PDF ditampilkan di UI Streamlit.

---

## **Instalasi dan Penggunaan**

### **Prasyarat**
- Python 3.8 atau lebih tinggi
- Git (untuk cloning repository)

### **Langkah Instalasi**
1. Clone repository:
   ```bash
   git clone https://github.com/[username]/rcs_dashboard.git
   cd rcs_dashboard
   ```
2. Buat virtual environment (opsional, direkomendasikan):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```
3. Install dependensi:
   ```bash
   pip install -r requirements.txt
   ```
   *(Catatan: Tambahkan file `requirements.txt` dengan daftar pustaka seperti `streamlit`, `pandas`, `sqlite3`, `plotly`, `matplotlib`, `reportlab`.)*
4. Jalankan aplikasi:
   ```bash
   streamlit run app.py
   ```

### **Contoh Penggunaan**
1. Buka browser di `http://localhost:8501`.
2. Login dengan kredensial (default: sesuaikan di `auth.py`).
3. Pilih menu di sidebar untuk mengakses dashboard atau upload data.

---

## **Deployment**

Aplikasi ini telah di-deploy ke **Streamlit Community Cloud** untuk uji coba. Akses di:  
🔗 [RCS Dashboard](https://rcs-dashboard-trial.streamlit.app/) 

### **Status Deploy**
- **Versi**: Trial deploy dengan fokus pada `dashboard_balita_gizi.py` dan `upload_data.py`.
- **Fitur Aktif**: Dashboard Balita Gizi, Upload Data, dan autentikasi.
- **Fitur Non-Aktif**: Dashboard Balita KIA, Ibu Hamil, Remaja Putri, dan EPPGBM masih placeholder atau belum diimplementasikan.

---

## **Kontribusi**

Kami menyambut kontribusi dari komunitas! Untuk berkontribusi:
1. Fork repository ini.
2. Buat branch baru (`git checkout -b feature/nama-fitur`).
3. Commit perubahan (`git commit -m "Menambahkan fitur X"`).
4. Push ke branch Anda (`git push origin feature/nama-fitur`).
5. Buat Pull Request.

---

## **To-Do List**
- [x] Selesaikan `dashboard_balita_gizi.py`.
- [x] Implementasi `upload_data.py`.
- [ ] Kembangkan `dashboard_balita_kia.py` dengan analisis lengkap.
- [ ] Buat `dashboard_ibuhamil.py`.
- [ ] Buat `dashboard_remaja.py`.
- [ ] Buat `dashboard_eppgbm.py`.
- [ ] Optimasi performa dan tambahkan caching untuk visualisasi besar.
- [ ] Dokumentasi API atau fungsi internal (jika diperlukan).

---

## **Kontak**
Dikembangkan oleh: [Dedik Kurniawan](mailto:dedik2urniawan@gmail.com)  
Untuk pertanyaan atau dukungan, silakan hubungi melalui email atau buka issue di repository ini.

---

**Made with ❤️ for better health insights in Indonesia.**

---

