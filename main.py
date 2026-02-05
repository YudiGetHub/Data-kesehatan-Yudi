import os
import streamlit as st
import pandas as pd
import google.generativeai as genai
import fitz
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# --- KONFIGURASI ---
st.set_page_config(page_title="Health Tracker Yudi", layout="wide", page_icon="🏥")

# Masukkan API Key Mas Yudi di sini
GOOGLE_API_KEY = "PASTE_API_KEY_ANDA_DI_SINI"
genai.configure(api_key=GOOGLE_API_KEY)

# --- FUNGSI DATABASE (PERBAIKAN) ---
def load_data(file_name, columns):
    """Memastikan file ada dan kolomnya sesuai"""
    if not os.path.exists(file_name):
        df = pd.DataFrame(columns=columns)
        df.to_csv(file_name, index=False)
        return df
    try:
        df = pd.read_csv(file_name)
        # Pastikan kolom sesuai, jika tidak, reset
        if list(df.columns) != columns:
            df = pd.DataFrame(columns=columns)
            df.to_csv(file_name, index=False)
        return df
    except:
        return pd.DataFrame(columns=columns)

def save_data(df, file_name):
    df.to_csv(file_name, index=False)

# --- UI CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 10px; }
    .detail-box { 
        padding: 20px; 
        border: 2px solid #4A90E2; 
        border-radius: 15px; 
        background-color: #f0f8ff; 
        margin-top: 10px;
        margin-bottom: 15px; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- HALAMAN JADWAL RS ---
def jadwal_rs_page():
    st.header("📅 Manajemen Jadwal RS")
    
    file_jadwal = "jadwal_rs.csv"
    # Kolom yang Mas Yudi minta: Tanggal, Jenis Kunjungan, Keterangan
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
                new_id = str(int(datetime.now().timestamp()))
                new_row = pd.DataFrame([[new_id, tgl.strftime("%Y-%m-%d"), jenis, ket]], columns=kolom_jadwal)
                df_jadwal = pd.concat([df_jadwal, new_row], ignore_index=True)
                save_data(df_jadwal, file_jadwal)
                st.success("Jadwal berhasil disimpan!")
                st.rerun()

    st.divider()

    # 2. Daftar Jadwal
    st.subheader("🗓 Daftar Perjanjian")
    
    if df_jadwal.empty:
        st.info("Belum ada jadwal yang tersimpan.")
    else:
        # Urutkan dari tanggal terbaru
        df_jadwal = df_jadwal.sort_values(by="Tanggal", ascending=True)
        
        for index, row in df_jadwal.iterrows():
            row_id = str(row['ID'])
            with st.container():
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.write(f"📅 **{row['Tanggal']}**")
                c2.write(f"🏷️ {row['Jenis_Kunjungan']}")
                
                # Gunakan Session State untuk kontrol buka-tutup detail
                if c3.button("Lihat Detail", key=f"btn_{row_id}"):
                    st.session_state[f"show_{row_id}"] = not st.session_state.get(f"show_{row_id}", False)

                if st.session_state.get(f"show_{row_id}", False):
                    st.markdown(f"""
                    <div class="detail-box">
                        <h4 style='margin-top:0;'>Info Detail</h4>
                        <hr>
                        <p><strong>Tanggal:</strong> {row['Tanggal']}</p>
                        <p><strong>Jenis Kunjungan:</strong> {row['Jenis_Kunjungan']}</p>
                        <p><strong>Keterangan:</strong><br>{row['Keterangan']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    cdel1, cdel2 = st.columns([1, 4])
                    if cdel1.button("🗑️ Hapus", key=f"del_{row_id}"):
                        df_jadwal = df_jadwal.drop(index)
                        save_data(df_jadwal, file_jadwal)
                        st.warning("Jadwal dihapus!")
                        st.rerun()
                    if cdel2.button("Tutup Detail", key=f"cls_{row_id}"):
                        st.session_state[f"show_{row_id}"] = False
                        st.rerun()
                st.write("---")

# --- HALAMAN UTAMA & NAVIGASI ---
def main():
    st.sidebar.title(f"Health Tracker Yudi")
    menu = st.sidebar.selectbox("Menu Utama", ["Dashboard", "Jadwal RS", "Analisa MRI", "Catat Gejala"])

    if menu == "Dashboard":
        st.title("🏠 Dashboard Utama")
        st.write(f"Selamat datang, Mas Yudi. Hari ini adalah {datetime.now().strftime('%d %B %Y')}")
        st.info("Gunakan menu di samping untuk mengelola data kesehatan Anda.")
    elif menu == "Jadwal RS":
        jadwal_rs_page()
    elif menu == "Analisa MRI":
        st.title("🧠 Analisa MRI (AI)")
        st.write("Fitur ini sedang dalam pengembangan untuk integrasi Gemini.")
    elif menu == "Catat Gejala":
        st.title("📝 Catat Kondisi Fisik")
        st.write("Fitur pencatatan harian.")

if __name__ == "__main__":
    main()
                     
