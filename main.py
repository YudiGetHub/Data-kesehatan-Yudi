import streamlit as st
import google.generativeai as genai
import fitz
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Health Tracker Yudi", layout="wide")

# --- KONEKSI KE SECRETS (OTOMATIS) ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Kunci API tidak ditemukan di Secrets Streamlit!")
    st.stop()

# --- FUNGSI ANALISA MEDIS ---
def jalankan_analisa(file_pdf):
    try:
        doc = fitz.open(stream=file_pdf.read(), filetype="pdf")
        teks = "".join([halaman.get_text() for halaman in doc])
        if not teks.strip():
            return "Teks dokumen tidak terbaca. Pastikan PDF bukan hasil scan foto."
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        # Fokus analisa sesuai riwayat kesehatan Mas Yudi
        prompt = f"Analisa medis ringkas untuk pasien Yudi: {teks}. Jelaskan temuan terkait lesi atau concha nasalis."
        respon = model.generate_content(prompt)
        return respon.text
    except Exception as e:
        return f"Gagal analisa: {str(e)}"

# --- MENU NAVIGASI TUNGGAL ---
st.sidebar.title("🏥 Health Manager")
menu = st.sidebar.radio("Pilih Menu", ["Dashboard", "Analisa Berkas", "Data Fisik"])

if menu == "Dashboard":
    st.title("🏠 Dashboard Kesehatan")
    st.write("Selamat datang kembali, Mas Yudi. Pilih menu di samping untuk mulai.")

elif menu == "Analisa Berkas":
    st.title("📁 Analisa Hasil Medis")
    berkas = st.file_uploader("Upload PDF MRI/Lab", type="pdf")
    if berkas and st.button("Mulai Analisa"):
        with st.spinner("AI sedang menganalisa dokumen..."):
            hasil = jalankan_analisa(berkas)
            st.info(hasil)

elif menu == "Data Fisik":
    st.title("📏 Catatan Fisik")
    st.write("Fitur pencatatan berat badan dan tinggi badan.")
