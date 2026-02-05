import os
import streamlit as st
import pandas as pd
import google.generativeai as genai
import fitz
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# --- CONFIGURASI ---
st.set_page_config(page_title="Health Tracker Yudi", layout="wide", page_icon="🏥")

# Masukkan API Key Mas Yudi di sini
GOOGLE_API_KEY = "PASTE_API_KEY_ANDA_DI_SINI"
genai.configure(api_key=GOOGLE_API_KEY)

# --- FUNGSI DATABASE ---
def load_data(file_name, columns):
    if not os.path.exists(file_name):
        df = pd.DataFrame(columns=columns)
        df.to_csv(file_name, index=False)
        return df
    return pd.read_csv(file_name)

def save_data(df, file_name):
    df.to_csv(file_name, index=False)

# --- UI CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 10px; }
    .detail-box { padding: 15px; border: 1px solid #ddd; border-radius: 10px; background-color: white; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- HALAMAN JADWAL RS ---
def jadwal_rs_page():
    st.header("📅 Manajemen Jadwal RS")
    
    file_jadwal = "jadwal_rs.csv"
    kolom_jadwal = ["ID", "Tanggal", "Jenis_Kunjungan", "Keterangan"]
    df_jadwal = load_data(file_jadwal, kolom_jadwal)

    # 1. Form Input
    with st.expander("➕ Tambah Perjanjian Baru", expanded=False):
        with st.form("form_jadwal"):
            tgl = st.date_input("Tanggal Kunjungan", datetime.now())
            jenis = st.selectbox("Jenis Kunjungan", ["Kontrol Rutin", "Konsultasi Spesialis", "Cek Lab / Radiologi", "Tindakan / Operasi", "Lainnya"])
            ket = st.text_area("Keterangan", placeholder="Contoh: Kontrol pasca MRI di RS...")
            submit = st.form_submit_button("Simpan Perjanjian")
            
            if submit:
                new_id = int(datetime.now().timestamp())
                new_row = pd.DataFrame([[new_id, tgl.strftime("%Y-%m-%d"), jenis, ket]], columns=kolom_jadwal)
                df_jadwal = pd.concat([df_jadwal, new_row], ignore_index=True)
                save_data(df_jadwal, file_jadwal)
                st.success("Jadwal berhasil disimpan!")
                st.rerun()

    st.divider()

    # 2. Daftar Jadwal
    st.subheader("🗓 Daftar Perjanjian Terdaftar")
    
    if df_jadwal.empty:
        st.info("Belum ada jadwal yang dibuat.")
    else:
        # Urutkan berdasarkan tanggal terdekat
        df_jadwal = df_jadwal.sort_values(by="Tanggal")
        
        for index, row in df_jadwal.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([2, 2, 1])
                col1.write(f"📅 **{row['Tanggal']}**")
                col2.write(f"🏷️ {row['Jenis_Kunjungan']}")
                
                # Tombol Detail
                if col3.button("Lihat Detail", key=f"det_{row['ID']}"):
                    st.session_state[f"show_detail_{row['ID']}"] = True

                # Area Detail (Muncul jika tombol ditekan)
                if st.session_state.get(f"show_detail_{row['ID']}", False):
                    st.markdown(f"""
                    <div class="detail-box">
                        <p><strong>Tanggal:</strong> {row['Tanggal']}</p>
                        <p><strong>Jenis:</strong> {row['Jenis_Kunjungan']}</p>
                        <p><strong>Keterangan:</strong> {row['Keterangan']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col_d1, col_d2 = st.columns([1, 4])
                    if col_d1.button("🗑️ Hapus", key=f"del_{row['ID']}"):
                        df_jadwal = df_jadwal.drop(index)
                        save_data(df_jadwal, file_jadwal)
                        st.warning("Jadwal telah dihapus.")
                        st.rerun()
                    if col_d2.button("Tutup", key=f"close_{row['ID']}"):
                        st.session_state[f"show_detail_{row['ID']}"] = False
                        st.rerun()
                st.write("---")

# --- SIDEBAR NAVIGASI ---
def main():
    st.sidebar.title(f"Halo, Mas Yudi! 👋")
    menu = st.sidebar.selectbox("Menu Utama", ["Dashboard", "Jadwal RS", "Analisa MRI", "Catat Gejala"])

    if menu == "Dashboard":
        st.title("🏠 Dashboard Kesehatan")
        st.write("Selamat datang kembali. Gunakan menu di samping untuk mengelola data kesehatan Anda.")
        # Bisa ditambah ringkasan jadwal terdekat di sini
    elif menu == "Jadwal RS":
        jadwal_rs_page()
    elif menu == "Analisa MRI":
        st.title("🧠 Analisa MRI (AI)")
        st.info("Fitur ini menggunakan Gemini AI untuk membantu membaca hasil laboratorium.")
        # Tambahkan fungsi upload MRI Mas di sini
    elif menu == "Catat Gejala":
        st.title("📝 Catat Gejala & Fisik")
        st.write("Fitur untuk mencatat kondisi harian.")

if __name__ == "__main__":
    main()
df_jadwal = fix_and_load_data("jadwal_rs.csv", ["Tanggal", "Tujuan_Tindakan", "Tipe", "Catatan"])
df_obat = fix_and_load_data("data_obat.csv", ["Nama", "Dosis", "Waktu"])
df_gejala = fix_and_load_data("data_gejala.csv", ["Tanggal", "Keluhan_Mandiri", "Diagnosa_Dokter", "BB", "TB"])
df_analisis = fix_and_load_data("riwayat_analisis.csv", ["Tgl_Analisis", "Tgl_Berkas", "File", "Hasil"])

# --- 5. FUNGSI ANALISA AI ---
def jalankan_analisa_ai(file_path, file_name):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        if file_name.lower().endswith('.pdf'):
            doc = fitz.open(file_path)
            txt = "".join([p.get_text() for p in doc]); 
            prompt = f"Tgl berkas (YYYY-MM-DD) di baris 1, lalu ringkas diagnosa medis: {txt}"
            resp = model.generate_content(prompt)
        else:
            with open(file_path, "rb") as f: img_data = f.read()
            img = {"mime_type": "image/jpeg", "data": img_data}
            resp = model.generate_content(["Tgl berkas (YYYY-MM-DD) di baris 1, lalu ringkas diagnosa medis.", img])
        
        hasil = resp.text
        tgl_b = hasil.split('\n')[0][:10]
        new_entry = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), tgl_b, file_name, hasil]], columns=df_analisis.columns)
        save_data(pd.concat([df_analisis, new_entry], ignore_index=True), "riwayat_analisis.csv")
        return hasil
    except Exception as e: return f"Error: {e}"

# --- 6. SIDEBAR ---
st.sidebar.title("🏥 Health Assistant")
st.sidebar.write(f"**Nama:** Nur Wahyudi")
page = st.sidebar.selectbox("Menu:", ["🏠 Dashboard Utama", "📈 Catat Kondisi & Fisik", "💊 Jadwal Minum Obat", "📁 Brankas & Analisa AI", "📅 Jadwal RS & Tindakan"])

# --- HALAMAN 1: DASHBOARD (LAYOUT DIUBAH) ---
if page == "🏠 Dashboard Utama":
    st.title("🏠 Ringkasan Kesehatan")
    
    # ATAS: Informasi Teks (Dibuat 2 Kolom)
    col_info1, col_info2 = st.columns(2)
    
    with col_info1:
        st.subheader("📅 Jadwal Terdekat")
        if not df_jadwal.empty:
            df_jadwal['Tanggal'] = pd.to_datetime(df_jadwal['Tanggal'])
            mndtg = df_jadwal[df_jadwal['Tanggal'] >= pd.Timestamp.now().normalize()].sort_values('Tanggal')
            if not mndtg.empty: 
                st.success(f"**{mndtg.iloc[0]['Tipe']}**: {mndtg.iloc[0]['Tujuan_Tindakan']}\n\n📅 {mndtg.iloc[0]['Tanggal'].strftime('%d %B %Y')}")
            else: st.write("Tidak ada jadwal terdekat.")
        
        st.subheader("💊 Obat Hari Ini")
        if not df_obat.empty:
            for _, r in df_obat.iterrows():
                st.warning(f"**{r['Nama']}** ({r['Dosis']}) - {r['Waktu']}")
        else: st.write("Belum ada daftar obat.")

    with col_info2:
        st.subheader("🧠 Diagnosa Dokter Terakhir")
        if not df_gejala.empty:
            # Ambil record terbaru dari Catat Kondisi
            last_g = df_gejala.sort_values('Tanggal').iloc[-1]
            st.info(f"**Hasil Konsultasi:**\n\n{last_g['Diagnosa_Dokter']}")
        else: st.write("Belum ada catatan diagnosa.")

        st.subheader("📂 Analisis MRI (AI)")
        if not df_analisis.empty:
            st.info(f"**Ringkasan Terakhir:**\n\n{df_analisis.iloc[-1]['Hasil']}")
        else: st.write("Belum ada riwayat MRI.")

    st.divider()

    # BAWAH: Grafik Fisik (Pindah ke Bawah)
    st.subheader("⚖️ Tren Fisik: Berat Badan & Tinggi Badan")
    if not df_gejala.empty:
        df_gejala['Tanggal'] = pd.to_datetime(df_gejala['Tanggal'])
        df_p = df_gejala.sort_values('Tanggal')
        
        fig, ax = plt.subplots(figsize=(10, 4))
        # Garis BB (Merah)
        ax.plot(df_p['Tanggal'], df_p['BB'], marker='o', color='#ff4b4b', label='Berat Badan (kg)', linewidth=2.5)
        # Garis TB (Biru)
        ax.plot(df_p['Tanggal'], df_p['TB'], marker='s', color='#007bff', label='Tinggi Badan (cm)', linewidth=2.5)
        
        # Format Sumbu X (Hanya Bulan)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        
        ax.set_ylim(20, 200) # Range statis agar grafik linear terlihat
        ax.legend(loc='upper right')
        ax.grid(True, linestyle='--', alpha=0.3)
        st.pyplot(fig)
    else:
        st.info("Data fisik belum tersedia untuk ditampilkan dalam grafik.")

# --- HALAMAN 2: CATAT KONDISI & FISIK ---
elif page == "📈 Catat Kondisi & Fisik":
    st.title("📈 Catat Gejala & Ukuran Fisik")
    with st.form("form_fisik"):
        c1, c2 = st.columns(2)
        tgl = c1.date_input("Tanggal Pemeriksaan", datetime.now())
        bb = c2.number_input("Berat Badan (kg)", 20.0, 150.0, 65.0)
        tb = c2.number_input("Tinggi Badan (cm)", 50.0, 250.0, 165.0)
        keluhan = st.text_area("Keluhan Mandiri", placeholder="Apa yang Anda rasakan?")
        diagnosa = st.text_area("Diagnosa Dokter", placeholder="Apa kata dokter saat pemeriksaan?")
        if st.form_submit_button("Simpan"):
            new_g = pd.DataFrame([[tgl, keluhan, diagnosa, bb, tb]], columns=df_gejala.columns)
            save_data(pd.concat([df_gejala, new_g], ignore_index=True), "data_gejala.csv")
            st.success("Berhasil disimpan!"); st.rerun()

    st.subheader("📜 Riwayat Perjalanan Penyakit")
    if not df_gejala.empty:
        for i, r in df_gejala.iloc[::-1].iterrows():
            with st.expander(f"📅 {r['Tanggal']} | BB: {r['BB']}kg | TB: {r['TB']}cm"):
                st.write(f"**Keluhan:** {r['Keluhan_Mandiri']}")
                st.write(f"**Diagnosa Dokter:** {r['Diagnosa_Dokter']}")
                if st.button("Hapus", key=f"del_g_{i}"):
                    save_data(df_gejala.drop(i), "data_gejala.csv"); st.rerun()

# --- HALAMAN LAINNYA (TETAP SAMA) ---
elif page == "📁 Brankas & Analisa AI":
    st.title("📁 Brankas Dokumen")
    up = st.file_uploader("Upload File", type=["pdf", "jpg", "png"])
    if up:
        with open(os.path.join("uploads", up.name), "wb") as f: f.write(up.getbuffer())
        st.success("Tersimpan!")
    files = os.listdir("uploads")
    for f in files:
        c_f, c_b = st.columns([3, 1])
        c_f.write(f"📄 {f}")
        if c_b.button("Analisa AI", key=f):
            with st.spinner("Menganalisa..."):
                jalankan_analisa_ai(os.path.join("uploads", f), f); st.rerun()

elif page == "📅 Jadwal RS & Tindakan":
    st.title("📅 Jadwal RS")
    with st.form("f_rs"):
        tgl = st.date_input("Tanggal"); tp = st.selectbox("Jenis", ["MRI", "Kontrol", "Operasi"]); tj = st.text_input("Tujuan")
        if st.form_submit_button("Simpan"):
            save_data(pd.concat([df_jadwal, pd.DataFrame([[tgl, tj, tp, "N/A"]], columns=df_jadwal.columns)]), "jadwal_rs.csv"); st.rerun()
    for i, r in df_jadwal.iterrows():
        st.write(f"**{r['Tipe']}** - {r['Tujuan_Tindakan']} ({r['Tanggal']})")
        if st.button("Hapus", key=f"d_rs_{i}"): save_data(df_jadwal.drop(i), "jadwal_rs.csv"); st.rerun()

elif page == "💊 Jadwal Minum Obat":
    st.title("💊 Obat")
    with st.form("f_o"):
        n = st.text_input("Nama"); d = st.text_input("Dosis"); w = st.selectbox("Waktu", ["Pagi", "Siang", "Malam"])
        if st.form_submit_button("Tambah"):
            save_data(pd.concat([df_obat, pd.DataFrame([[n, d, w]], columns=df_obat.columns)]), "data_obat.csv"); st.rerun()
    st.table(df_obat)
