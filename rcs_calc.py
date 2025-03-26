import streamlit as st
from streamlit.components import v1 as components

def show_rcs_calculator(sub_menu):
    if sub_menu == "RCS Calc versi 1.0.0":
        # Subheader untuk informasi
        st.subheader("📋 Informasi RCS Calculator: Latar Belakang dan Keunggulan Sistem")

        # Informasi dengan gaya profesional
        st.markdown("""
            <div style="background-color: #F9F9F9; padding: 20px; border-radius: 10px; border-left: 6px solid #1976D2; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                <p style="font-size: 16px; color: #333; line-height: 1.6; font-family: Arial, sans-serif;">
                    <strong>RCS Calculator</strong> adalah alat analisis berbasis platform Spreadsheet yang dikembangkan untuk mendukung pemrosesan data kesehatan masyarakat dengan performa tinggi. Sistem ini dirancang oleh tim Dinas Kesehatan Kabupaten Malang untuk memenuhi kebutuhan pengolahan data gizi berbasis masyarakat, dengan fokus pada efisiensi, keamanan, dan fleksibilitas data. RCS Calculator memungkinkan pengumpulan data secara real-time, analisis cepat, dan visualisasi yang mendukung pengambilan keputusan strategis.
                </p>
                <p style="font-size: 16px; color: #333; line-height: 1.6; font-family: Arial, sans-serif;">
                    Berbeda dengan pendekatan tradisional, RCS Calculator tidak menggunakan sintaksis formula per sel, melainkan memanfaatkan <strong>Query Database Functions</strong> untuk mempercepat pemrosesan data dari tingkat Puskesmas hingga Kabupaten. Sistem ini terintegrasi dengan API untuk visualisasi data, memungkinkan pembaruan real-time pada setiap sel di spreadsheet dengan latensi hanya 2-3 menit per tabel. Data yang dihasilkan dapat diakses melalui dashboard terpadu, baik melalui perangkat mobile maupun desktop, memberikan fleksibilitas bagi pengguna di berbagai tingkat administrasi kesehatan.
                </p>
                <p style="font-size: 16px; color: #333; line-height: 1.6; font-family: Arial, sans-serif;">
                    RCS Calculator versi 1.0.0 mendukung analisis lanjutan dengan pemrograman R melalui <strong>WHO Anthro Analyzer</strong>, memungkinkan penilaian status gizi anak balita sesuai standar global. Fitur ini dirancang untuk menjadi <strong>bridging media</strong> antara data catatan berbasis masyarakat (seperti Posyandu) dan data cross-sectional Puskesmas, meskipun masih memiliki beberapa kekurangan yang sedang diperbaiki pada versi berikutnya. Dengan pendekatan ini, RCS Calculator bertujuan menjadi alat strategis bagi pengambil keputusan di tingkat lokal untuk memantau, mengevaluasi, dan meningkatkan program gizi masyarakat.
                </p>
            </div>
        """, unsafe_allow_html=True)

        # Subheader untuk iframe
        st.markdown("### RCS Calculator Versi 1.0.0")

        # URL iframe untuk digunakan di tombol "Buka di Tab Baru"
        iframe_url = "https://lookerstudio.google.com/embed/reporting/b7531ab9-3985-49e0-9019-be3e6a5b2a3f/page/p_g13c6xv3dd"

        # Iframe dengan ID untuk JavaScript
        iframe_code = f"""
        <div>
            <iframe id="rcs-iframe" width="100%" height="338" src="{iframe_url}" frameborder="0" style="border:0" allowfullscreen sandbox="allow-storage-access-by-user-activation allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"></iframe>
        </div>
        <script>
            function toggleFullscreen() {{
                var iframe = document.getElementById("rcs-iframe");
                if (iframe.requestFullscreen) {{
                    iframe.requestFullscreen();
                }} else if (iframe.mozRequestFullScreen) {{ /* Firefox */
                    iframe.mozRequestFullScreen();
                }} else if (iframe.webkitRequestFullscreen) {{ /* Chrome, Safari & Opera */
                    iframe.webkitRequestFullscreen();
                }} else if (iframe.msRequestFullscreen) {{ /* IE/Edge */
                    iframe.msRequestFullscreen();
                }}
            }}
        </script>
        """
        components.html(iframe_code, height=338)

        # Tombol untuk fullscreen dan buka di tab baru
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown(
                """
                <button onclick="toggleFullscreen()" style="background-color: #1976D2; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;">
                    Tampilkan Fullscreen
                </button>
                """,
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                f"""
                <a href="{iframe_url}" target="_blank">
                    <button style="background-color: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;">
                        Buka di Tab Baru
                    </button>
                </a>
                """,
                unsafe_allow_html=True
            )

        # Catatan tentang fullscreen
        st.markdown("""
            <small style="color: grey;">
                Catatan: Jika tombol "Tampilkan Fullscreen" tidak berfungsi karena batasan keamanan browser atau Looker Studio, gunakan tombol "Buka di Tab Baru" untuk melihat dashboard dalam tampilan lebih besar.
            </small>
        """, unsafe_allow_html=True)

    elif sub_menu == "RCS Calc versi 1.0.1":
        st.markdown("### RCS Calculator Versi 1.0.1")
        st.info("Fitur ini sedang dalam tahap pengembangan dan akan segera diluncurkan. Kami menghargai kesabaran Anda dalam menunggu pembaruan ini.")