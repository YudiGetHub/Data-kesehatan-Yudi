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
GOOGLE_API_KEY = "PASTE_API_KEY_ANDA_DI_SINI"
genai.configure(api_key=GOOGLE_API_KEY)

# --- FUNGSI DATABASE ---
def load_db(file_name, columns):
    if not os.path.exists(file_name):
        df = pd.DataFrame(columns=columns)
        df.to_csv(file_name, index=False)
        return df
    return pd.read_csv(file_name)

def save_db(df, file_name):
    df.to_csv(file_name, index=False)

# --- SISTEM KEAMANAN (LOGIN) ---
def login_system():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.title("🔐 Global Health Access")
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            user = st.text_input("Username", key="login_user")
            pw = st.text_input("Password", type="password", key="login_pw")
            if st.button("Masuk"):
                if user == "admin" and pw == "yudi123": # Contoh simpel, bisa dikembangkan
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Akun tidak ditemukan atau password salah")
        
        with tab2:
            st.info("Fitur pendaftaran akun baru untuk publik sedang disiapkan.")
        st.stop()

# --- FUNGSI ANALISA AI ---
def analisa_ai(teks):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(f"Analisa ringkas berkas kesehatan ini: {teks}")
        return response.text
    except:
        return "Gagal menganalisa dokumen."

# --- UI COMPONENT: DASHBOARD ---
def show_dashboard():
    st.title("🏠 Dashboard Utama")
    
    # Load semua data
    df_jadwal = load_db("jadwal_rs.csv", ["ID", "Tanggal", "Poli", "Tindakan", "Catatan", "Status"])
    df_fisik = load_db("data_fisik.csv", ["Tanggal", "BB", "TB", "Keluhan"])
    df_berkas = load_db("berkas.csv", ["Tanggal", "Judul", "Jenis", "Analisa"])

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📈 Grafik BB & TB")
        if not df_fisik.empty:
            df_fisik['Tanggal'] = pd.to_datetime(df_fisik['Tanggal'])
            df_fisik = df_fisik.sort_values('Tanggal')
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(df_fisik['Tanggal'], df_fisik['BB'], label='Berat Badan (kg)', color='#FF4B4B', marker='o')
            ax.plot(df_fisik['Tanggal'], df_fisik['TB'], label='Tinggi Badan (cm)', color='#1C83E1', marker='s')
            plt.xticks(rotation=45)
            ax.legend()
            st.pyplot(fig)
        else:
            st.info("Belum ada data fisik untuk grafik.")

        st.subheader("📝 Jadwal Mendatang")
        mendatang = df_jadwal[df_jadwal['Status'] == 'Belum Terlaksana'].head(3)
        if not mendatang.empty:
            st.table(mendatang[['Tanggal', 'Poli', 'Tindakan']])
        else:
            st.write("Tidak ada jadwal terdekat.")

    with col2:
        st.subheader("🧠 Analisa MRI Terakhir")
        mri_terakhir = df_berkas[df_berkas['Jenis'] == 'MRI'].head(1)
        if not mri_terakhir.empty:
            st.success(f"📌 {mri_terakhir['Judul'].values[0]}")
            st.write(mri_terakhir['Analisa'].values[0])
        else:
            st.info("Belum ada analisa MRI.")

# --- UI COMPONENT: JADWAL KONTROL ---
def show_jadwal():
    st.title("📅 Jadwal Kontrol")
    cols_jadwal = ["ID", "Tanggal", "Poli", "Tindakan", "Catatan", "Status"]
    df = load_db("jadwal_rs.csv", cols_jadwal)

    with st.expander("➕ Tambah Jadwal Baru"):
        with st.form("input_jadwal"):
            tgl = st.date_input("Tanggal Kontrol")
            poli = st.text_input("Nama Poli")
            tindakan = st.text_input("Tindakan")
            catatan = st.text_area("Catatan")
            if st.form_submit_button("Simpan"):
                new_id = str(int(datetime.now().timestamp()))
                new_row = pd.DataFrame([[new_id, str(tgl), poli, tindakan, catatan, "Belum Terlaksana"]], columns=cols_jadwal)
                df = pd.concat([df, new_row], ignore_index=True)
                save_db(df, "jadwal_rs.csv")
                st.rerun()

    tab1, tab2 = st.tabs(["Akan Datang", "Sudah Terlaksana"])
    
    with tab1:
        for i, r in df[df['Status'] == 'Belum Terlaksana'].iterrows():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{r['Tanggal']}** - {r['Poli']}")
            if c2.button("✅ Selesai", key=f"done_{r['ID']}"):
                df.at[i, 'Status'] = 'Sudah Terlaksana'
                save_db(df, "jadwal_rs.csv")
                st.rerun()
            if c3.button("🔍 Detail", key=f"det_{r['ID']}"):
                st.info(f"Tindakan: {r['Tindakan']}\n\nCatatan: {r['Catatan']}")
                if st.button("🗑️ Hapus", key=f"del_{r['ID']}"):
                    df = df.drop(i)
                    save_db(df, "jadwal_rs.csv"); st.rerun()

    with tab2:
        st.table(df[df['Status'] == 'Sudah Terlaksana'][['Tanggal', 'Poli', 'Tindakan']])

# --- UI COMPONENT: BERKAS ---
def show_berkas():
    st.title("📁 Penyimpanan Berkas Penting")
    cols_berkas = ["Tanggal", "Judul", "Jenis", "Analisa"]
    df = load_db("berkas.csv", cols_berkas)

    with st.form("upload_berkas"):
        tgl = st.date_input("Tanggal Berkas")
        judul = st.text_input("Judul Berkas")
        jenis = st.selectbox("Jenis", ["MRI", "Lab", "Resep", "Lainnya"])
        file = st.file_uploader("Upload PDF", type="pdf")
        if st.form_submit_button("Upload"):
            analisa_text = "Analisa belum dijalankan."
            if file:
                doc = fitz.open(stream=file.read(), filetype="pdf")
                raw_text = "".join([p.get_text() for p in doc])
                analisa_text = analisa_ai(raw_text)
            
            new_row = pd.DataFrame([[str(tgl), judul, jenis, analisa_text]], columns=cols_berkas)
            df = pd.concat([df, new_row], ignore_index=True)
            save_db(df, "berkas.csv")
            st.success("Berkas Terupload!")

    st.dataframe(df.sort_values("Tanggal", ascending=False))

# --- UI COMPONENT: KONDISI TUBUH ---
def show_fisik():
    st.title("📏 Pencatatan Kondisi Tubuh")
    cols_fisik = ["Tanggal", "BB", "TB", "Keluhan"]
    df = load_db("data_fisik.csv", cols_fisik)

    with st.form("input_fisik"):
        tgl = st.date_input("Tanggal")
        bb = st.number_input("Berat Badan (kg)", step=0.1)
        tb = st.number_input("Tinggi Badan (cm)", step=0.1)
        keluhan = st.text_area("Apa yang dirasakan?")
        if st.form_submit_button("Simpan Data"):
            new_row = pd.DataFrame([[str(tgl), bb, tb, keluhan]], columns=cols_fisik)
            df = pd.concat([df, new_row], ignore_index=True)
            save_db(df, "data_fisik.csv")
            st.success("Data Tersimpan!")

# --- MAIN APP ---
def main():
    login_system()
    
    st.sidebar.title("🌍 Health Global")
    menu = st.sidebar.radio("Navigasi", ["Dashboard", "Jadwal Kontrol", "Berkas Penting", "Kondisi Tubuh"])
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    if menu == "Dashboard": show_dashboard()
    elif menu == "Jadwal Kontrol": show_jadwal()
    elif menu == "Berkas Penting": show_berkas()
    elif menu == "Kondisi Tubuh": show_fisik()

if __name__ == "__main__":
    main()
    
