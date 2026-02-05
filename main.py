import os
import streamlit as st
import pandas as pd
import google.generativeai as genai
import fitz  # PyMuPDF
import matplotlib.pyplot as plt
from datetime import datetime
import base64

# --- 1. KONFIGURASI DASAR ---
st.set_page_config(page_title="Health Manager Yudi", layout="wide", page_icon="🏥")

# PENTING: Segera ganti dengan API Key baru yang tidak kena 'Warning'
GOOGLE_API_KEY = "AIzaSyBJIlWMYddlRWhynYw-PJ1AFWO4xVATV1M"
genai.configure(api_key=GOOGLE_API_KEY)

# --- 2. FUNGSI DATABASE ---
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

# --- 3. FUNGSI ANALISA AI (FAIL-SAFE) ---
def analisa_ai(teks):
    if not teks.strip():
        return "Teks dokumen tidak terbaca. Pastikan PDF bukan hasil scan gambar."
    
    # Mencoba model flash, jika gagal 404 otomatis coba model pro
    for model_name in ['gemini-1.5-flash', 'gemini-1.5-pro']:
        try:
            model = genai.GenerativeModel(model_name)
            res = model.generate_content(f"Analisa medis ringkas untuk Yudi: {teks}")
            return res.text
        except Exception as e:
            if "404" in str(e): continue
            return f"Gagal analisa: {str(e)}"
    return "Semua model AI gagal merespons. Cek kembali API Key Anda."

# --- 4. TAMPILAN HALAMAN ---
def show_dashboard():
    st.title("🏠 Dashboard")
    df_f = load_db("data_fisik.csv", ["Tanggal", "BB", "TB", "Keluhan"])
    df_b = load_db("berkas.csv", ["ID", "Tanggal", "Judul", "Jenis", "Analisa", "File_Data"])
    
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("📈 Grafik BB & TB")
        if not df_f.empty:
            df_f['Tanggal'] = pd.to_datetime(df_f['Tanggal'])
            df_f = df_f.sort_values('Tanggal')
            fig, ax1 = plt.subplots(figsize=(10, 5))
            ax1.plot(df_f['Tanggal'], df_f['BB'], 'r-o', label='BB (kg)')
            ax1.set_ylabel('Berat (kg)', color='r')
            ax2 = ax1.twinx()
            ax2.plot(df_f['Tanggal'], df_f['TB'], 'b-s', label='TB (cm)')
            ax2.set_ylabel('Tinggi (cm)', color='b')
            st.pyplot(fig)
        else: st.info("Data fisik kosong.")
    with c2:
        st.subheader("🧠 MRI Terakhir")
        mri = df_b[df_b['Jenis'] == 'MRI'].sort_values('Tanggal', ascending=False).head(1)
        if not mri.empty:
            st.success(f"📌 {mri['Judul'].values[0]}")
            st.write(mri['Analisa'].values[0])

def show_berkas():
    st.title("📁 Penyimpanan Berkas")
    df = load_db("berkas.csv", ["ID", "Tanggal", "Judul", "Jenis", "Analisa", "File_Data"])
    
    with st.expander("➕ Tambah Berkas"):
        with st.form("up", clear_on_submit=True):
            d1, d2 = st.date_input("Tanggal"), st.text_input("Judul")
            d3 = st.selectbox("Jenis", ["MRI", "Lab", "Lainnya"])
            f = st.file_uploader("PDF Only", type="pdf")
            if st.form_submit_button("Simpan & Analisa"):
                if f:
                    b64 = base64.b64encode(f.read()).decode('utf-8')
                    doc = fitz.open(stream=base64.b64decode(b64), filetype="pdf")
                    txt = "".join([p.get_text() for p in doc])
                    ana = analisa_ai(txt)
                    nid = str(int(datetime.now().timestamp()))
                    new = pd.DataFrame([[nid, str(d1), d2, d3, ana, b64]], columns=df.columns)
                    save_db(pd.concat([df, new]), "berkas.csv"); st.rerun()

    for _, r in df.sort_values("Tanggal", ascending=False).iterrows():
        c1, c2 = st.columns([4, 1])
        c1.write(f"📄 **{r['Judul']}** ({r['Tanggal']})")
        if c2.button("Buka", key=f"v_{r['ID']}"):
            st.session_state[f"show_{r['ID']}"] = not st.session_state.get(f"show_{r['ID']}", False)
        if st.session_state.get(f"show_{r['ID']}", False):
            st.info(f"**Analisa AI:** {r['Analisa']}")
            pdf = f'<iframe src="data:application/pdf;base64,{r["File_Data"]}" width="100%" height="500"></iframe>'
            st.markdown(pdf, unsafe_allow_html=True)
            if st.button("Hapus", key=f"h_{r['ID']}"):
                save_db(df[df['ID'] != r['ID']], "berkas.csv"); st.rerun()
        st.divider()

# --- 5. MAIN NAVIGASI (Hanya Satu) ---
def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        st.title("🔐 Login")
        u, p = st.text_input("User"), st.text_input("Pass", type="password")
        if st.button("Masuk"):
            if u == "admin" and p == "yudi123":
                st.session_state.logged_in = True; st.rerun()
        return

    st.sidebar.title("🏥 Health Manager")
    menu = st.sidebar.radio("Menu Utama", ["Dashboard", "Berkas Kesehatan", "Kondisi Fisik", "Jadwal RS"])
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False; st.rerun()

    if menu == "Dashboard": show_dashboard()
    elif menu == "Berkas Kesehatan": show_berkas()
    # Tambahkan fungsi show_fisik dan show_jadwal di sini sesuai kebutuhan

if __name__ == "__main__":
    main()
  
