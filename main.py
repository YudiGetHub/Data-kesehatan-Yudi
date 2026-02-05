import os
import streamlit as st
import pandas as pd
import google.generativeai as genai
import fitz  # PyMuPDF
import matplotlib.pyplot as plt
from datetime import datetime

# --- KONFIGURASI DASAR ---
st.set_page_config(page_title="Global Health Tracker", layout="wide", page_icon="🌐")

# API KEY
GOOGLE_API_KEY = "AIzaSyBJIlWMYddlRWhynYw-PJ1AFWO4xVATV1M"
genai.configure(api_key=GOOGLE_API_KEY)

# --- FUNGSI DATABASE ---
def load_db(file_name, columns):
    if not os.path.exists(file_name):
        df = pd.DataFrame(columns=columns)
        df.to_csv(file_name, index=False)
        return df
    try:
        df = pd.read_csv(file_name)
        # Pastikan kolom ID selalu string agar tidak error saat hapus
        if 'ID' in df.columns:
            df['ID'] = df['ID'].astype(str)
        return df
    except:
        return pd.DataFrame(columns=columns)

def save_db(df, file_name):
    df.to_csv(file_name, index=False)

# --- SISTEM LOGIN ---
def login_system():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.title("🔐 Global Health Access")
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            user = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            if st.button("Masuk"):
                if user == "admin" and pw == "yudi123":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Akun tidak ditemukan atau password salah")
        
        with tab2:
            st.info("Fitur pendaftaran akun baru sedang disiapkan.")
        st.stop()

# --- FUNGSI ANALISA AI ---
def analisa_ai(teks):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(f"Analisa ringkas berkas kesehatan ini dalam bahasa Indonesia: {teks}")
        return response.text
    except:
        return "Gagal menganalisa dokumen."

# --- 1. DASHBOARD ---
def show_dashboard():
    st.title("🏠 Dashboard Utama")
    
    df_jadwal = load_db("jadwal_rs.csv", ["ID", "Tanggal", "Poli", "Tindakan", "Catatan", "Status"])
    df_fisik = load_db("data_fisik.csv", ["Tanggal", "BB", "TB", "Keluhan"])
    df_berkas = load_db("berkas.csv", ["Tanggal", "Judul", "Jenis", "Analisa"])

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📈 Grafik Kesehatan (BB & TB)")
        if not df_fisik.empty:
            df_fisik['Tanggal'] = pd.to_datetime(df_fisik['Tanggal'])
            df_fisik = df_fisik.sort_values('Tanggal')
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(df_fisik['Tanggal'], df_fisik['BB'], label='Berat Badan (kg)', color='#FF4B4B', marker='o', linewidth=2)
            ax.plot(df_fisik['Tanggal'], df_fisik['TB'], label='Tinggi Badan (cm)', color='#1C83E1', marker='s', linewidth=2)
            plt.xticks(rotation=45)
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.legend()
            st.pyplot(fig)
        else:
            st.info("Data grafik belum tersedia. Silakan isi di menu Kondisi Tubuh.")

    with col2:
        st.subheader("📅 Jadwal Terdekat")
        mendatang = df_jadwal[df_jadwal['Status'] == 'Belum Terlaksana'].sort_values('Tanggal').head(3)
        if not mendatang.empty:
            for _, r in mendatang.iterrows():
                st.warning(f"**{r['Tanggal']}**\n\n{r['Poli']} - {r['Tindakan']}")
        else:
            st.write("Tidak ada jadwal dalam waktu dekat.")

        st.divider()
        st.subheader("🧠 Analisa MRI Terakhir")
        mri_terakhir = df_berkas[df_berkas['Jenis'] == 'MRI'].sort_values('Tanggal', ascending=False).head(1)
        if not mri_terakhir.empty:
            st.success(f"📌 {mri_terakhir['Judul'].values[0]}")
            st.write(mri_terakhir['Analisa'].values[0])
        else:
            st.info("Belum ada analisa berkas MRI.")

# --- 2. JADWAL KONTROL ---
def show_jadwal():
    st.title("📅 Jadwal Kontrol")
    cols = ["ID", "Tanggal", "Poli", "Tindakan", "Catatan", "Status"]
    df = load_db("jadwal_rs.csv", cols)

    with st.expander("➕ Tambah Jadwal Baru"):
        with st.form("input_jadwal", clear_on_submit=True):
            t1 = st.date_input("Tanggal Kontrol")
            t2 = st.text_input("Nama Poli")
            t3 = st.text_input("Tindakan")
            t4 = st.text_area("Catatan")
            if st.form_submit_button("Simpan"):
                new_id = str(int(datetime.now().timestamp()))
                new_row = pd.DataFrame([[new_id, str(t1), t2, t3, t4, "Belum Terlaksana"]], columns=cols)
                df = pd.concat([df, new_row], ignore_index=True)
                save_db(df, "jadwal_rs.csv")
                st.success("Tersimpan!"); st.rerun()

    t_akan, t_selesai = st.tabs(["🗓 Akan Datang", "✅ Sudah Terlaksana"])
    
    with t_akan:
        df_a = df[df['Status'] == 'Belum Terlaksana'].copy()
        for i, r in df_a.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.write(f"**{r['Tanggal']}** | {r['Poli']}")
                if c2.button("✅ Selesai", key=f"d_{r['ID']}"):
                    df.loc[df['ID'] == r['ID'], 'Status'] = 'Sudah Terlaksana'
                    save_db(df, "jadwal_rs.csv"); st.rerun()
                if c3.button("🔍 Detail", key=f"det_{r['ID']}"):
                    st.session_state[f"view_{r['ID']}"] = True
                
                if st.session_state.get(f"view_{r['ID']}", False):
                    st.info(f"**Tindakan:** {r['Tindakan']}\n\n**Catatan:** {r['Catatan']}")
                    cd1, cd2 = st.columns(2)
                    if cd1.button("🗑️ Hapus", key=f"del_{r['ID']}"):
                        df = df[df['ID'] != r['ID']]
                        save_db(df, "jadwal_rs.csv"); st.rerun()
                    if cd2.button("Tutup", key=f"cls_{r['ID']}"):
                        st.session_state[f"view_{r['ID']}"] = False; st.rerun()
            st.divider()

    with t_selesai:
        df_s = df[df['Status'] == 'Sudah Terlaksana'].copy()
        for i, r in df_s.iterrows():
            cc1, cc2 = st.columns([4, 1])
            cc1.write(f"✅ {r['Tanggal']} - {r['Poli']} ({r['Tindakan']})")
            if cc2.button("🗑️ Hapus", key=f"del_s_{r['ID']}"):
                df = df[df['ID'] != r['ID']]
                save_db(df, "jadwal_rs.csv"); st.rerun()

# --- 3. BERKAS PENTING ---
def show_berkas():
    st.title("📁 Penyimpanan Berkas")
    cols = ["Tanggal", "Judul", "Jenis", "Analisa"]
    df = load_db("berkas.csv", cols)

    with st.expander("➕ Upload Berkas Baru"):
        with st.form("up_berkas"):
            d1 = st.date_input("Tanggal Berkas")
            d2 = st.text_input("Judul Berkas")
            d3 = st.selectbox("Jenis", ["MRI", "Lab", "Resep", "Lainnya"])
            f = st.file_uploader("Upload PDF", type="pdf")
            if st.form_submit_button("Simpan & Analisa"):
                text_ana = "Tidak ada teks untuk dianalisa."
                if f:
                    doc = fitz.open(stream=f.read(), filetype="pdf")
                    text_ana = analisa_ai("".join([p.get_text() for p in doc]))
                new_r = pd.DataFrame([[str(d1), d2, d3, text_ana]], columns=cols)
                df = pd.concat([df, new_r], ignore_index=True)
                save_db(df, "berkas.csv"); st.success("Terupload!"); st.rerun()

    df = df.sort_values("Tanggal", ascending=False)
    for i, r in df.iterrows():
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.write(f"📄 **{r['Judul']}** ({r['Tanggal']})")
            col2.write(f"🏷️ {r['Jenis']}")
            if col3.button("🔍 Analisa", key=f"ana_{i}"):
                st.write(r['Analisa'])
        st.divider()

# --- 4. KONDISI TUBUH ---
def show_fisik():
    st.title("📏 Catat Kondisi Tubuh")
    cols = ["Tanggal", "BB", "TB", "Keluhan"]
    df = load_db("data_fisik.csv", cols)

    with st.form("fisik_form"):
        c1, c2 = st.columns(2)
        d1 = c1.date_input("Tanggal")
        d2 = c1.number_input("Berat Badan (kg)", step=0.1)
        d3 = c2.number_input("Tinggi Badan (cm)", step=0.1)
        d4 = st.text_area("Apa yang dirasakan saat ini?")
        if st.form_submit_button("Simpan Kondisi"):
            new_row = pd.DataFrame([[str(d1), d2, d3, d4]], columns=cols)
            df = pd.concat([df, new_row], ignore_index=True)
            save_db(df, "data_fisik.csv"); st.success("Data Tersimpan!"); st.rerun()

    st.subheader("Riwayat Catatan")
    st.dataframe(df.sort_values("Tanggal", ascending=False), use_container_width=True)

# --- NAVIGASI UTAMA ---
def main():
    login_system()
    st.sidebar.title("🏥 Health Global")
    menu = st.sidebar.radio("Navigasi Utama", ["Dashboard", "Jadwal Kontrol", "Penyimpanan Berkas", "Kondisi Tubuh"])
    
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

    if menu == "Dashboard": show_dashboard()
    elif menu == "Jadwal Kontrol": show_jadwal()
    elif menu == "Penyimpanan Berkas": show_berkas()
    elif menu == "Kondisi Tubuh": show_fisik()

if __name__ == "__main__":
    main()
            
