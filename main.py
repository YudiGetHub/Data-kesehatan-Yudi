import os
import streamlit as st
import pandas as pd
import google.generativeai as genai
import fitz  # PyMuPDF
import matplotlib.pyplot as plt
from datetime import datetime
import base64

# --- KONFIGURASI DASAR ---
st.set_page_config(page_title="Global Health Tracker Yudi", layout="wide", page_icon="🏥")

# GANTI DENGAN API KEY GEMINI MAS YUDI
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
        st.title("🔐 Login Sistem Kesehatan")
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.button("Masuk"):
            if user == "admin" and pw == "yudi123":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Username atau Password salah")
        st.stop()

# --- FUNGSI ANALISA AI (PERBAIKAN ERROR 404) ---
def analisa_ai(teks):
    if not teks.strip():
        return "Teks dokumen tidak terbaca. Pastikan PDF bukan hasil scan gambar murni."
    try:
        # Menggunakan nama model yang lebih spesifik untuk menghindari error 404
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        prompt = (
            f"Anda adalah asisten medis. Analisa hasil pemeriksaan medis ini untuk pasien bernama Yudi "
            f"secara ringkas dan dalam Bahasa Indonesia: {teks}. Jelaskan poin pentingnya."
        )
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gagal analisa: {str(e)}"

# --- 1. DASHBOARD ---
def show_dashboard():
    st.title("🏠 Dashboard")
    df_fisik = load_db("data_fisik.csv", ["Tanggal", "BB", "TB", "Keluhan"])
    df_berkas = load_db("berkas.csv", ["ID", "Tanggal", "Judul", "Jenis", "Analisa", "File_Data"])
    
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("📈 Grafik Kesehatan (BB & TB)")
        if not df_fisik.empty:
            df_fisik['Tanggal'] = pd.to_datetime(df_fisik['Tanggal'])
            df_fisik = df_fisik.sort_values('Tanggal')
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(df_fisik['Tanggal'], df_fisik['BB'], label='BB (kg)', color='red', marker='o')
            ax.plot(df_fisik['Tanggal'], df_fisik['TB'], label='TB (cm)', color='blue', marker='s')
            ax.legend(); ax.grid(True, alpha=0.3)
            st.pyplot(fig)
        else: st.info("Belum ada data fisik.")

    with c2:
        st.subheader("🧠 MRI Terakhir")
        mri = df_berkas[df_berkas['Jenis'] == 'MRI'].sort_values('Tanggal', ascending=False).head(1)
        if not mri.empty:
            st.success(f"📌 {mri['Judul'].values[0]}")
            st.write(mri['Analisa'].values[0])
        else: st.info("Belum ada analisa MRI.")

# --- 2. JADWAL KONTROL ---
def show_jadwal():
    st.title("📅 Jadwal Kontrol")
    cols = ["ID", "Tanggal", "Poli", "Tindakan", "Catatan", "Status"]
    df = load_db("jadwal_rs.csv", cols)
    
    with st.expander("➕ Tambah Jadwal Baru"):
        with st.form("f_jadwal", clear_on_submit=True):
            d1, d2 = st.date_input("Tanggal"), st.text_input("Poli")
            d3, d4 = st.text_input("Tindakan"), st.text_area("Catatan")
            if st.form_submit_button("Simpan"):
                nid = str(int(datetime.now().timestamp()))
                nr = pd.DataFrame([[nid, str(d1), d2, d3, d4, "Belum Terlaksana"]], columns=cols)
                save_db(pd.concat([df, nr]), "jadwal_rs.csv"); st.rerun()

    t1, t2 = st.tabs(["Akan Datang", "Selesai"])
    with t1:
        for i, r in df[df['Status'] == 'Belum Terlaksana'].iterrows():
            c1, c2 = st.columns([4, 1])
            c1.write(f"📅 **{r['Tanggal']}** | {r['Poli']}")
            if c2.button("🔍 Detail", key=f"d_{r['ID']}"):
                st.session_state[f"view_j_{r['ID']}"] = not st.session_state.get(f"view_j_{r['ID']}", False)
            
            if st.session_state.get(f"view_j_{r['ID']}", False):
                st.info(f"Tindakan: {r['Tindakan']}\n\nCatatan: {r['Catatan']}")
                if st.button("✅ Selesai", key=f"s_{r['ID']}"):
                    df.loc[df['ID'] == r['ID'], 'Status'] = 'Sudah Terlaksana'
                    save_db(df, "jadwal_rs.csv"); st.rerun()
                if st.button("🗑️ Hapus", key=f"h_{r['ID']}"):
                    save_db(df[df['ID'] != r['ID']], "jadwal_rs.csv"); st.rerun()
            st.divider()

# --- 3. PENYIMPANAN BERKAS ---
def show_berkas():
    st.title("📁 Penyimpanan Berkas")
    cols = ["ID", "Tanggal", "Judul", "Jenis", "Analisa", "File_Data"]
    df = load_db("berkas.csv", cols)
    
    with st.expander("➕ Upload PDF Baru"):
        with st.form("up_b"):
            d1, d2 = st.date_input("Tanggal"), st.text_input("Judul")
            d3 = st.selectbox("Jenis", ["MRI", "Lab", "Resep", "Lainnya"])
            f = st.file_uploader("Upload PDF", type="pdf")
            if st.form_submit_button("Simpan & Analisa"):
                if f:
                    b64 = base64.b64encode(f.read()).decode('utf-8')
                    doc = fitz.open(stream=base64.b64decode(b64), filetype="pdf")
                    txt = "".join([p.get_text() for p in doc])
                    ana = analisa_ai(txt)
                    nid = str(int(datetime.now().timestamp()))
                    nr = pd.DataFrame([[nid, str(d1), d2, d3, ana, b64]], columns=cols)
                    save_db(pd.concat([df, nr]), "berkas.csv"); st.rerun()

    for i, r in df.sort_values("Tanggal", ascending=False).iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"📄 **{r['Judul']}** ({r['Tanggal']})")
        if c3.button("🔍 Buka", key=f"v_{r['ID']}"):
            st.session_state[f"view_b_{r['ID']}"] = not st.session_state.get(f"view_b_{r['ID']}", False)
        
        if st.session_state.get(f"view_b_{r['ID']}", False):
            st.markdown(f"**Analisa AI:**\n{r['Analisa']}")
            pdf_code = f'<iframe src="data:application/pdf;base64,{r["File_Data"]}" width="100%" height="500"></iframe>'
            st.markdown(pdf_code, unsafe_allow_html=True)
            if st.button("🗑️ Hapus Berkas", key=f"hb_{r['ID']}"):
                save_db(df[df['ID'] != r['ID']], "berkas.csv"); st.rerun()
        st.divider()

# --- 4. KONDISI TUBUH ---
def show_fisik():
    st.title("📏 Kondisi Tubuh")
    cols = ["Tanggal", "BB", "TB", "Keluhan"]
    df = load_db("data_fisik.csv", cols)
    with st.form("f_f"):
        c1, c2 = st.columns(2)
        d1 = c1.date_input("Tanggal")
        bb = c1.number_input("BB (kg)", step=0.1)
        tb = c2.number_input("TB (cm)", step=0.1)
        kl = st.text_area("Keluhan")
        if st.form_submit_button("Simpan"):
            nr = pd.DataFrame([[str(d1), bb, tb, kl]], columns=cols)
            save_db(pd.concat([df, nr]), "data_fisik.csv"); st.rerun()
    st.dataframe(df.sort_values("Tanggal", ascending=False))

# --- MAIN ---
def main():
    login_system()
    st.sidebar.title("🏥 Menu")
    m = st.sidebar.radio("Navigasi", ["Dashboard", "Jadwal Kontrol", "Penyimpanan Berkas", "Kondisi Tubuh"])
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False; st.rerun()
    if m == "Dashboard": show_dashboard()
    elif m == "Jadwal Kontrol": show_jadwal()
    elif m == "Penyimpanan Berkas": show_berkas()
    elif m == "Kondisi Tubuh": show_fisik()

if __name__ == "__main__":
    main()
    
