import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
import pandas as pd
import base64
import os
import matplotlib.pyplot as plt
from datetime import datetime

# --- 1. KONFIGURASI KEAMANAN & SELF-HEALING ---
st.set_page_config(page_title="Global Health Tracker Yudi", layout="wide", page_icon="🏥")

def inisialisasi_ai():
    """Fungsi otomatis untuk konfigurasi AI tanpa hardcoded key"""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            return True
        else:
            st.warning("⚠️ API Key belum dikonfigurasi di Streamlit Secrets.")
            return False
    except Exception as e:
        st.error(f"Kesalahan Inisialisasi: {e}")
        return False

# --- 2. LOGIKA DATABASE OTOMATIS ---
def get_db(file_name, columns):
    if not os.path.exists(file_name):
        pd.DataFrame(columns=columns).to_csv(file_name, index=False)
    try:
        return pd.read_csv(file_name)
    except:
        # Perbaikan otomatis jika file CSV korup
        df = pd.DataFrame(columns=columns)
        df.to_csv(file_name, index=False)
        return df

def save_db(df, file_name):
    df.to_csv(file_name, index=False)

# --- 3. ANALISA AI DENGAN PENANGANAN ERROR ---
def analisa_medis_ai(teks):
    if not teks.strip():
        return "Teks dokumen tidak terbaca. Pastikan PDF bukan hasil scan gambar murni."
    
    # Mencoba model terbaru secara otomatis
    model_list = ['gemini-1.5-flash', 'gemini-1.5-pro']
    for model_name in model_list:
        try:
            model = genai.GenerativeModel(model_name)
            prompt = f"Analisa medis ringkas untuk pasien Yudi: {teks}. Jelaskan temuan utama dan saran."
            response = model.generate_content(prompt)
            return response.text
        except:
            continue
    return "AI gagal merespons. Pastikan API Key di Secrets sudah benar dan aktif."

# --- 4. TAMPILAN HALAMAN ---
def show_dashboard():
    st.header("🏠 Dashboard Kesehatan Mas Yudi")
    df_f = get_db("fisik.csv", ["Tanggal", "BB", "TB", "Keluhan"])
    df_b = get_db("berkas.csv", ["ID", "Tanggal", "Judul", "Jenis", "Analisa", "File_Data"])
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("📈 Tren BB & TB")
        if not df_f.empty:
            df_f['Tanggal'] = pd.to_datetime(df_f['Tanggal'])
            df_f = df_f.sort_values('Tanggal')
            fig, ax1 = plt.subplots()
            ax1.plot(df_f['Tanggal'], df_f['BB'], 'r-o', label='BB (kg)')
            ax2 = ax1.twinx()
            ax2.plot(df_f['Tanggal'], df_f['TB'], 'b-s', label='TB (cm)')
            st.pyplot(fig)
        else: st.info("Belum ada data fisik.")
    
    with col2:
        st.subheader("🧠 MRI Terakhir")
        mri = df_b[df_b['Jenis'] == 'MRI'].sort_values('Tanggal', ascending=False).head(1)
        if not mri.empty:
            st.success(f"📌 {mri['Judul'].values[0]}")
            st.write(mri['Analisa'].values[0])

def show_berkas():
    st.header("📁 Berkas & Analisa AI")
    df = get_db("berkas.csv", ["ID", "Tanggal", "Judul", "Jenis", "Analisa", "File_Data"])
    
    with st.expander("➕ Upload Berkas Baru"):
        with st.form("up", clear_on_submit=True):
            d1, d2 = st.date_input("Tanggal"), st.text_input("Judul")
            d3 = st.selectbox("Jenis", ["MRI", "Lab", "Resep"])
            f = st.file_uploader("Upload PDF", type="pdf")
            if st.form_submit_button("Simpan & Analisa"):
                if f:
                    b64 = base64.b64encode(f.read()).decode('utf-8')
                    doc = fitz.open(stream=base64.b64decode(b64), filetype="pdf")
                    txt = "".join([p.get_text() for p in doc])
                    ana = analisa_medis_ai(txt)
                    nid = str(int(datetime.now().timestamp()))
                    new = pd.DataFrame([[nid, str(d1), d2, d3, ana, b64]], columns=df.columns)
                    save_db(pd.concat([df, new]), "berkas.csv")
                    st.success("Analisa Selesai!"); st.rerun()

    for i, r in df.sort_values("Tanggal", ascending=False).iterrows():
        with st.container():
            c1, c2 = st.columns([4, 1])
            c1.write(f"📄 **{r['Judul']}** ({r['Tanggal']})")
            if c2.button("Buka", key=f"v_{r['ID']}"):
                st.session_state[f"show_{r['ID']}"] = not st.session_state.get(f"show_{r['ID']}", False)
            if st.session_state.get(f"show_{r['ID']}", False):
                st.info(f"**Analisa AI:**\n{r['Analisa']}")
                pdf_view = f'<iframe src="data:application/pdf;base64,{r["File_Data"]}" width="100%" height="500"></iframe>'
                st.markdown(pdf_view, unsafe_allow_html=True)
                if st.button("Hapus", key=f"h_{r['ID']}"):
                    save_db(df[df['ID'] != r['ID']], "berkas.csv"); st.rerun()
        st.divider()

# --- 5. LOGIKA NAVIGASI UTAMA ---
def main():
    if not inisialisasi_ai():
        st.info("💡 Petunjuk: Masukkan GEMINI_API_KEY di menu Settings > Secrets pada Streamlit Cloud.")
        st.stop()
    
    st.sidebar.title("🏥 Navigasi")
    menu = st.sidebar.radio("Pilih Menu", ["Dashboard", "Berkas Medis", "Update Fisik"])
    
    if menu == "Dashboard": show_dashboard()
    elif menu == "Berkas Medis": show_berkas()
    elif menu == "Update Fisik":
        st.header("📏 Update Kondisi Fisik")
        df = get_db("fisik.csv", ["Tanggal", "BB", "TB", "Keluhan"])
        with st.form("fisik_form"):
            tgl, bb, tb = st.date_input("Tanggal"), st.number_input("BB"), st.number_input("TB")
            kl = st.text_area("Keluhan")
            if st.form_submit_button("Simpan"):
                save_db(pd.concat([df, pd.DataFrame([[str(tgl), bb, tb, kl]], columns=df.columns)]), "fisik.csv")
                st.success("Data disimpan!"); st.rerun()

if __name__ == "__main__":
    main()
                          
