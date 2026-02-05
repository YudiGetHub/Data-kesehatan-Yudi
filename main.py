import streamlit as st
import google.generativeai as genai
import fitz
import pandas as pd
import base64
import os
import matplotlib.pyplot as plt
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Global Health Tracker Yudi", layout="wide", page_icon="🏥")

# --- 2. SISTEM AI OTOMATIS (Mencegah Error 404) ---
def analisa_medis_yudi(teks):
    if not teks.strip(): return "Laporan tidak terbaca."
    
    # Mencoba berbagai versi model secara berurutan
    model_versions = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
    
    for v in model_versions:
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel(v)
            prompt = f"Sebagai asisten medis untuk Yudi, analisa teks ini. Fokus pada temuan lesi periventrikuler dan hipertrofi concha: {teks}"
            res = model.generate_content(prompt)
            return res.text
        except:
            continue
    return "🚨 Maaf, sistem AI sedang sibuk. Pastikan API Key Anda aktif di Google AI Studio."

# --- 3. FUNGSI DATABASE ---
def get_db(name, cols):
    if not os.path.exists(name):
        pd.DataFrame(columns=cols).to_csv(name, index=False)
    return pd.read_csv(name)

def save_db(df, name):
    df.to_csv(name, index=False)

# --- 4. TAMPILAN FITUR LENGKAP ---
def main():
    # Header Utama
    st.sidebar.title("🏥 Health Manager")
    # Menu Navigasi (Hanya Satu)
    menu = st.sidebar.radio("Navigasi Utama", ["Dashboard", "Penyimpanan Berkas", "Jadwal Kontrol", "Kondisi Tubuh"])

    # FITUR 1: DASHBOARD
    if menu == "Dashboard":
        st.title("🏠 Dashboard Kesehatan")
        df_f = get_db("fisik.csv", ["Tanggal", "BB", "TB", "Keluhan"])
        if not df_f.empty:
            st.subheader("Tren Berat Badan")
            st.line_chart(df_f.set_index('Tanggal')['BB'])
        else:
            st.info("Belum ada data fisik untuk ditampilkan.")

    # FITUR 2: PENYIMPANAN BERKAS (Analisa MRI/Lab)
    elif menu == "Penyimpanan Berkas":
        st.title("📁 Berkas Kesehatan & Analisa AI")
        df = get_db("berkas.csv", ["ID", "Tanggal", "Judul", "Analisa", "File_Data"])
        
        with st.form("upload_form", clear_on_submit=True):
            tgl, jdl = st.date_input("Tanggal"), st.text_input("Judul Berkas")
            f = st.file_uploader("Upload PDF", type="pdf")
            if st.form_submit_button("Simpan & Analisa"):
                if f:
                    with st.spinner("AI sedang menganalisa laporan Mas Yudi..."):
                        b64 = base64.b64encode(f.read()).decode('utf-8')
                        doc = fitz.open(stream=base64.b64decode(b64), filetype="pdf")
                        txt = "".join([p.get_text() for p in doc])
                        hasil_ai = analisa_medis_yudi(txt)
                        nid = str(int(datetime.now().timestamp()))
                        new = pd.DataFrame([[nid, str(tgl), jdl, hasil_ai, b64]], columns=df.columns)
                        save_db(pd.concat([df, new]), "berkas.csv")
                        st.success("Analisa Berhasil!"); st.rerun()

        for _, r in df.sort_values("Tanggal", ascending=False).iterrows():
            with st.expander(f"📄 {r['Judul']} ({r['Tanggal']})"):
                st.write(f"**Analisa AI:** {r['Analisa']}")
                if st.button("Hapus", key=f"del_{r['ID']}"):
                    save_db(df[df['ID'] != r['ID']], "berkas.csv"); st.rerun()

    # FITUR 3: JADWAL KONTROL
    elif menu == "Jadwal Kontrol":
        st.title("📅 Jadwal Kontrol RS")
        df_j = get_db("jadwal.csv", ["Tanggal", "RS", "Tujuan"])
        with st.form("jadwal_form"):
            t1, t2, t3 = st.date_input("Tanggal"), st.text_input("Rumah Sakit"), st.text_input("Keperluan")
            if st.form_submit_button("Tambah Jadwal"):
                save_db(pd.concat([df_j, pd.DataFrame([[str(t1), t2, t3]], columns=df_j.columns)]), "jadwal.csv")
                st.rerun()
        st.table(df_j)

    # FITUR 4: KONDISI TUBUH
    elif menu == "Kondisi Tubuh":
        st.title("📏 Catatan Kondisi Fisik")
        df_f = get_db("fisik.csv", ["Tanggal", "BB", "TB", "Keluhan"])
        with st.form("fisik_form"):
            d1, d2, d3 = st.date_input("Tanggal"), st.number_input("BB (kg)"), st.number_input("TB (cm)")
            d4 = st.text_area("Keluhan")
            if st.form_submit_button("Simpan"):
                save_db(pd.concat([df_f, pd.DataFrame([[str(d1), d2, d3, d4]], columns=df_f.columns)]), "fisik.csv")
                st.rerun()
        st.dataframe(df_f)

if __name__ == "__main__":
    main()
                        
