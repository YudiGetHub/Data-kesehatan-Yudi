import os
import streamlit as st
import pandas as pd
import google.generativeai as genai
import fitz  # PyMuPDF
import matplotlib.pyplot as plt
from datetime import datetime
import base64

# --- KONFIGURASI DASAR ---
st.set_page_config(page_title="Health Tracker Yudi", layout="wide", page_icon="🏥")

# MASUKKAN API KEY BARU MAS DI SINI
# Saran: Buat key baru di AI Studio karena yang lama sudah kena Warning
GOOGLE_API_KEY = "AIzaSyD-RW-ll6GfgyoBjcM55a6HPBZSIHB4NTA" 

try:
    genai.configure(api_key=GOOGLE_API_KEY)
except:
    st.error("Konfigurasi API Key Gagal. Periksa koneksi atau kunci Anda.")

# --- FUNGSI DATABASE ---
def load_db(file_name, columns):
    if not os.path.exists(file_name):
        df = pd.DataFrame(columns=columns)
        df.to_csv(file_name, index=False)
        return df
    try:
        df = pd.read_csv(file_name)
        if 'ID' in df.columns: df['ID'] = df['ID'].astype(str)
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
        st.title("🔐 Login Sistem Kesehatan Yudi")
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.button("Masuk"):
            if user == "admin" and pw == "yudi123":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Akses Ditolak")
        st.stop()

# --- FUNGSI ANALISA AI (PERBAIKAN TOTAL) ---
def analisa_ai(teks):
    if not teks.strip():
        return "Teks dokumen tidak terbaca (PDF Scan/Gambar)."
    
    # Gunakan model tanpa prefix 'models/' untuk kompatibilitas lebih baik
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Analisa hasil medis ini untuk Yudi secara singkat dan jelas: {teks}"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # Jika gagal, coba gunakan model alternatif
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(f"Analisa medis singkat: {teks}")
            return response.text
        except:
            return f"Analisa Gagal. Error: {str(e)}. Pastikan API Key Mas Yudi tidak dinonaktifkan oleh Google."

# --- 1. DASHBOARD ---
def show_dashboard():
    st.title("🏠 Dashboard Utama")
    df_fisik = load_db("data_fisik.csv", ["Tanggal", "BB", "TB", "Keluhan"])
    df_berkas = load_db("berkas.csv", ["ID", "Tanggal", "Judul", "Jenis", "Analisa", "File_Data"])
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("📈 Tren Berat & Tinggi Badan")
        if not df_fisik.empty:
            df_fisik['Tanggal'] = pd.to_datetime(df_fisik['Tanggal'])
            df_fisik = df_fisik.sort_values('Tanggal')
            fig, ax1 = plt.subplots(figsize=(10, 5))
            ax1.plot(df_fisik['Tanggal'], df_fisik['BB'], 'r-o', label='BB (kg)')
            ax1.set_ylabel('Berat (kg)', color='r')
            ax2 = ax1.twinx()
            ax2.plot(df_fisik['Tanggal'], df_fisik['TB'], 'b-s', label='TB (cm)')
            ax2.set_ylabel('Tinggi (cm)', color='b')
            plt.title("Grafik Kesehatan")
            st.pyplot(fig)
        else: st.info("Belum ada data grafik.")

    with col2:
        st.subheader("🧠 Analisa MRI Terakhir")
        mri = df_berkas[df_berkas['Jenis'] == 'MRI'].sort_values('Tanggal', ascending=False).head(1)
        if not mri.empty:
            st.success(f"📌 {mri['Judul'].values[0]}")
            st.write(mri['Analisa'].values[0])
        else: st.info("Tidak ada data MRI.")

# --- 2. JADWAL RS (PERBAIKAN HAPUS) ---
def show_jadwal():
    st.title("📅 Jadwal RS")
    cols = ["ID", "Tanggal", "Poli", "Tindakan", "Catatan", "Status"]
    df = load_db("jadwal_rs.csv", cols)

    with st.form("input_jadwal", clear_on_submit=True):
        c1, c2 = st.columns(2)
        tgl = c1.date_input("Tanggal")
        poli = c2.text_input("Nama Poli / RS")
        tindakan = st.text_input("Tujuan (Contoh: DSA / Kontrol)")
        catatan = st.text_area("Catatan Tambahan")
        if st.form_submit_button("Simpan"):
            nid = str(int(datetime.now().timestamp()))
            nr = pd.DataFrame([[nid, str(tgl), poli, tindakan, catatan, "Belum Terlaksana"]], columns=cols)
            save_db(pd.concat([df, nr]), "jadwal_rs.csv"); st.rerun()

    st.subheader("Daftar Jadwal")
    for i, r in df.iterrows():
        with st.container():
            col_teks, col_btn = st.columns([4, 1])
            col_teks.write(f"📌 **{r['Tanggal']}** - {r['Poli']} ({r['Tindakan']})")
            if col_btn.button("Hapus", key=f"del_{r['ID']}"):
                df = df[df['ID'] != r['ID']]
                save_db(df, "jadwal_rs.csv"); st.rerun()
        st.divider()

# --- 3. BERKAS ---
def show_berkas():
    st.title("📁 Berkas Kesehatan")
    cols = ["ID", "Tanggal", "Judul", "Jenis", "Analisa", "File_Data"]
    df = load_db("berkas.csv", cols)

    with st.expander("➕ Tambah Berkas Baru"):
        with st.form("up_b"):
            d1, d2 = st.date_input("Tanggal"), st.text_input("Judul")
            d3 = st.selectbox("Jenis", ["MRI", "Lab", "Resep"])
            f = st.file_uploader("Upload PDF", type="pdf")
            if st.form_submit_button("Analisa & Simpan"):
                if f:
                    b64 = base64.b64encode(f.read()).decode('utf-8')
                    doc = fitz.open(stream=base64.b64decode(b64), filetype="pdf")
                    txt = "".join([p.get_text() for p in doc])
                    ana = analisa_ai(txt)
                    nid = str(int(datetime.now().timestamp()))
                    nr = pd.DataFrame([[nid, str(d1), d2, d3, ana, b64]], columns=cols)
                    save_db(pd.concat([df, nr]), "berkas.csv"); st.rerun()

    for i, r in df.iterrows():
        c1, c2 = st.columns([4, 1])
        c1.write(f"📄 {r['Judul']} ({r['Tanggal']})")
        if c2.button("Buka", key=f"view_{r['ID']}"):
            st.session_state[f"show_{r['ID']}"] = not st.session_state.get(f"show_{r['ID']}", False)
        
        if st.session_state.get(f"show_{r['ID']}", False):
            st.info(f"**Analisa AI:** {r['Analisa']}")
            pdf_display = f'<iframe src="data:application/pdf;base64,{r["File_Data"]}" width="100%" height="500"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
            if st.button("Hapus Berkas", key=f"hb_{r['ID']}"):
                save_db(df[df['ID'] != r['ID']], "berkas.csv"); st.rerun()
        st.divider()

# --- 4. FISIK ---
def show_fisik():
    st.title("📏 Kondisi Fisik")
    cols = ["Tanggal", "BB", "TB", "Keluhan"]
    df = load_db("data_fisik.csv", cols)
    with st.form("f_f"):
        d1, d2, d3 = st.date_input("Tanggal"), st.number_input("BB (kg)"), st.number_input("TB (cm)")
        d4 = st.text_area("Keluhan")
        if st.form_submit_button("Simpan"):
            save_db(pd.concat([df, pd.DataFrame([[str(d1), d2, d3, d4]], columns=cols)]), "data_fisik.csv"); st.rerun()
    st.dataframe(df)

# --- NAVIGASI ---
def main():
    login_system()
    menu = st.sidebar.radio("Menu", ["Dashboard", "Jadwal RS", "Berkas Kesehatan", "Kondisi Fisik"])
    if menu == "Dashboard": show_dashboard()
    elif menu == "Jadwal RS": show_jadwal()
    elif menu == "Berkas Kesehatan": show_berkas()
    elif menu == "Kondisi Fisik": show_fisik()

if __name__ == "__main__":
    main()
        
