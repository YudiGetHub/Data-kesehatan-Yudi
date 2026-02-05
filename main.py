import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
import pandas as pd
import base64
import os
import matplotlib.pyplot as plt
from datetime import datetime

# --- 1. CONFIG & THEME ---
st.set_page_config(page_title="Global Health Tracker Yudi", layout="wide", page_icon="🏥")

# --- 2. AUTO-CHOICE AI SYSTEM (ANTI-404) ---
def inisialisasi_ai():
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return True
    return False

def analisa_medis_auto(teks):
    if not teks.strip(): return "Teks tidak terbaca."
    
    # Daftar model dari yang tercanggih sampai yang paling stabil
    model_choices = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
    
    for model_name in model_choices:
        try:
            model = genai.GenerativeModel(model_name)
            prompt = f"Analisa medis ringkas untuk Yudi: {teks}. Fokus pada lesi periventrikuler dan concha nasalis."
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            # Jika error 404 atau lainnya, lanjut coba model berikutnya
            continue
            
    return "🚨 Semua model AI (Flash/Pro) gagal merespons. Silakan periksa apakah API Key Mas Yudi di Secrets sudah benar-benar aktif."

# --- 3. DATABASE ENGINE ---
def get_db(name, cols):
    if not os.path.exists(name):
        pd.DataFrame(columns=cols).to_csv(name, index=False)
    return pd.read_csv(name)

def save_db(df, name):
    df.to_csv(name, index=False)

# --- 4. HALAMAN APLIKASI ---
def show_dashboard():
    st.title("🏠 Dashboard Kesehatan")
    df_f = get_db("fisik.csv", ["Tanggal", "BB", "TB", "Keluhan"])
    df_b = get_db("berkas.csv", ["ID", "Tanggal", "Judul", "Jenis", "Analisa", "File_Data"])
    
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("📈 Grafik Kondisi Fisik")
        if not df_f.empty:
            df_f['Tanggal'] = pd.to_datetime(df_f['Tanggal'])
            df_f = df_f.sort_values('Tanggal')
            fig, ax1 = plt.subplots(figsize=(10, 4))
            ax1.plot(df_f['Tanggal'], df_f['BB'], 'r-o', label='BB (kg)')
            ax2 = ax1.twinx()
            ax2.plot(df_f['Tanggal'], df_f['TB'], 'b-s', label='TB (cm)')
            st.pyplot(fig)
        else: st.info("Data fisik belum ada.")
    with c2:
        st.subheader("🧠 Info MRI Terakhir")
        mri = df_b[df_b['Jenis'] == 'MRI'].sort_values('Tanggal', ascending=False).head(1)
        if not mri.empty:
            st.success(f"📌 {mri['Judul'].values[0]}")
            st.write(mri['Analisa'].values[0][:200] + "...")
        else: st.info("Belum ada data MRI.")

def show_berkas():
    st.title("📁 Berkas & Analisa AI")
    df = get_db("berkas.csv", ["ID", "Tanggal", "Judul", "Jenis", "Analisa", "File_Data"])
    
    with st.expander("➕ Upload PDF Baru"):
        with st.form("up", clear_on_submit=True):
            d1, d2, d3 = st.date_input("Tanggal"), st.text_input("Judul"), st.selectbox("Jenis", ["MRI", "Lab", "Resep"])
            f = st.file_uploader("Upload PDF", type="pdf")
            if st.form_submit_button("Simpan & Analisa"):
                if f:
                    with st.spinner("AI sedang memilih model terbaik..."):
                        b64 = base64.b64encode(f.read()).decode('utf-8')
                        doc = fitz.open(stream=base64.b64decode(b64), filetype="pdf")
                        txt = "".join([p.get_text() for p in doc])
                        ana = analisa_medis_auto(txt)
                        nid = str(int(datetime.now().timestamp()))
                        new = pd.DataFrame([[nid, str(d1), d2, d3, ana, b64]], columns=df.columns)
                        save_db(pd.concat([df, new]), "berkas.csv"); st.rerun()

    for _, r in df.sort_values("Tanggal", ascending=False).iterrows():
        with st.expander(f"📄 {r['Judul']} ({r['Tanggal']})"):
            st.write(f"**Analisa:** {r['Analisa']}")
            pdf_data = f'<iframe src="data:application/pdf;base64,{r["File_Data"]}" width="100%" height="400"></iframe>'
            st.markdown(pdf_data, unsafe_allow_html=True)
            if st.button("Hapus", key=f"del_{r['ID']}"):
                save_db(df[df['ID'] != r['ID']], "berkas.csv"); st.rerun()

def show_jadwal():
    st.title("📅 Jadwal Kontrol RS")
    df = get_db("jadwal.csv", ["ID", "Tanggal", "RS", "Tujuan"])
    with st.form("j_f"):
        t1, t2, t3 = st.date_input("Tanggal"), st.text_input("RS/Poli"), st.text_input("Tujuan")
        if st.form_submit_button("Tambah Jadwal"):
            nid = str(int(datetime.now().timestamp()))
            save_db(pd.concat([df, pd.DataFrame([[nid, str(t1), t2, t3]], columns=df.columns)]), "jadwal.csv"); st.rerun()
    st.table(df)

# --- 5. MAIN NAVIGATION ---
def main():
    if not inisialisasi_ai():
        st.error("API Key tidak ditemukan di Secrets!")
        return

    st.sidebar.title("🏥 Health App Yudi")
    menu = st.sidebar.radio("Menu Utama", ["Dashboard", "Berkas Medis", "Jadwal RS", "Data Fisik"])

    if menu == "Dashboard": show_dashboard()
    elif menu == "Berkas Medis": show_berkas()
    elif menu == "Jadwal RS": show_jadwal()
    elif menu == "Data Fisik":
        st.title("📏 Catat Kondisi Fisik")
        df = get_db("fisik.csv", ["Tanggal", "BB", "TB", "Keluhan"])
        with st.form("f"):
            d1, d2, d3 = st.date_input("Tanggal"), st.number_input("BB (kg)"), st.number_input("TB (cm)")
            d4 = st.text_area("Keluhan")
            if st.form_submit_button("Simpan"):
                save_db(pd.concat([df, pd.DataFrame([[str(d1), d2, d3, d4]], columns=df.columns)]), "fisik.csv"); st.rerun()
        st.dataframe(df)

if __name__ == "__main__":
    main()
            
