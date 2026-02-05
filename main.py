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
                    st.error("Username atau Password salah")
        with tab2:
            st.info("Pendaftaran akun baru sedang dikembangkan.")
        st.stop()

# --- ANALISA AI ---
def analisa_ai(teks):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(f"Analisa ringkas hasil medis ini untuk pasien Yudi: {teks}")
        return response.text
    except Exception as e:
        return f"Gagal analisa: {str(e)}"

# --- 1. DASHBOARD ---
def show_dashboard():
    st.title("🏠 Dashboard Kesehatan Utama")
    df_jadwal = load_db("jadwal_rs.csv", ["ID", "Tanggal", "Poli", "Tindakan", "Catatan", "Status"])
    df_fisik = load_db("data_fisik.csv", ["Tanggal", "BB", "TB", "Keluhan"])
    df_berkas = load_db("berkas.csv", ["ID", "Tanggal", "Judul", "Jenis", "Analisa", "File_Data"])

    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("📈 Tren Grafik BB & TB")
        if not df_fisik.empty:
            df_fisik['Tanggal'] = pd.to_datetime(df_fisik['Tanggal'])
            df_fisik = df_fisik.sort_values('Tanggal')
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(df_fisik['Tanggal'], df_fisik['BB'], label='BB (kg)', color='red', marker='o')
            ax.plot(df_fisik['Tanggal'], df_fisik['TB'], label='TB (cm)', color='blue', marker='s')
            plt.xticks(rotation=45)
            ax.legend(); ax.grid(True, alpha=0.3)
            st.pyplot(fig)
        else:
            st.info("Data fisik belum tersedia.")

    with c2:
        st.subheader("📅 Jadwal Kontrol Terdekat")
        mendatang = df_jadwal[df_jadwal['Status'] == 'Belum Terlaksana'].sort_values('Tanggal').head(2)
        if not mendatang.empty:
            for _, r in mendatang.iterrows():
                st.warning(f"**{r['Tanggal']}**\n\n{r['Poli']} - {r['Tindakan']}")
        
        st.divider()
        st.subheader("🧠 Hasil Analisa MRI Terakhir")
        mri = df_berkas[df_berkas['Jenis'] == 'MRI'].sort_values('Tanggal', ascending=False).head(1)
        if not mri.empty:
            st.success(f"📌 {mri['Judul'].values[0]}")
            st.write(mri['Analisa'].values[0])
        else:
            st.info("Belum ada data MRI.")

# --- 2. JADWAL KONTROL ---
def show_jadwal():
    st.title("📅 Jadwal Kontrol")
    cols = ["ID", "Tanggal", "Poli", "Tindakan", "Catatan", "Status"]
    df = load_db("jadwal_rs.csv", cols)

    with st.expander("➕ Tambah Jadwal Baru"):
        with st.form("f_jadwal", clear_on_submit=True):
            d1 = st.date_input("Tanggal")
            d2 = st.text_input("Nama Poli")
            d3 = st.text_input("Tindakan")
            d4 = st.text_area("Catatan")
            if st.form_submit_button("Simpan"):
                new_row = pd.DataFrame([[str(int(datetime.now().timestamp())), str(d1), d2, d3, d4, "Belum Terlaksana"]], columns=cols)
                save_db(pd.concat([df, new_row]), "jadwal_rs.csv"); st.rerun()

    t1, t2 = st.tabs(["Akan Datang", "Sudah Terlaksana"])
    with t1:
        df_a = df[df['Status'] == 'Belum Terlaksana']
        for i, r in df_a.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.write(f"📅 **{r['Tanggal']}** - {r['Poli']}")
                if c2.button("✅ Selesai", key=f"s_{r['ID']}"):
                    df.loc[df['ID'] == r['ID'], 'Status'] = 'Sudah Terlaksana'
                    save_db(df, "jadwal_rs.csv"); st.rerun()
                if c3.button("🔍 Detail", key=f"d_{r['ID']}"):
                    st.info(f"**Tindakan:** {r['Tindakan']}\n\n**Catatan:** {r['Catatan']}")
                    cd1, cd2 = st.columns(2)
                    if cd1.button("🗑️ Hapus", key=f"h_{r['ID']}"):
                        save_db(df[df['ID'] != r['ID']], "jadwal_rs.csv"); st.rerun()
                    if cd2.button("Tutup", key=f"c_{r['ID']}"): st.rerun()
            st.divider()
    with t2:
        st.table(df[df['Status'] == 'Sudah Terlaksana'][['Tanggal', 'Poli', 'Tindakan']])

# --- 3. PENYIMPANAN BERKAS ---
def show_berkas():
    st.title("📁 Penyimpanan Berkas")
    cols = ["ID", "Tanggal", "Judul", "Jenis", "Analisa", "File_Data"]
    df = load_db("berkas.csv", cols)

    with st.expander("➕ Upload Berkas Baru"):
        with st.form("up_b"):
            d1 = st.date_input("Tanggal Berkas")
            d2 = st.text_input("Judul")
            d3 = st.selectbox("Jenis", ["MRI", "Lab", "Resep", "Lainnya"])
            f = st.file_uploader("Pilih PDF", type="pdf")
            if st.form_submit_button("Simpan & Analisa"):
                if f:
                    b64_pdf = base64.b64encode(f.read()).decode('utf-8')
                    doc = fitz.open(stream=base64.b64decode(b64_pdf), filetype="pdf")
                    txt = "".join([p.get_text() for p in doc])
                    ana = analisa_ai(txt)
                    new_id = str(int(datetime.now().timestamp()))
                    new_row = pd.DataFrame([[new_id, str(d1), d2, d3, ana, b64_pdf]], columns=cols)
                    save_db(pd.concat([df, new_row]), "berkas.csv"); st.rerun()

    for i, r in df.sort_values("Tanggal", ascending=False).iterrows():
        with st.container():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"📄 **{r['Judul']}** ({r['Tanggal']})")
            c2.write(f"🏷️ {r['Jenis']}")
            if c3.button("🔍 Detail Berkas", key=f"db_{r['ID']}"):
                st.session_state[f"v_{r['ID']}"] = True
            
            if st.session_state.get(f"v_{r['ID']}", False):
                st.markdown(f"**Hasil Analisa AI:**\n{r['Analisa']}")
                # Tombol Buka Berkas
                pdf_display = f'<iframe src="data:application/pdf;base64,{r["File_Data"]}" width="100%" height="600" type="application/pdf"></iframe>'
                st.markdown(pdf_display, unsafe_allow_html=True)
                
                cd1, cd2 = st.columns(2)
                if cd1.button("🗑️ Hapus Berkas", key=f"hb_{r['ID']}"):
                    save_db(df[df['ID'] != r['ID']], "berkas.csv"); st.rerun()
                if cd2.button("Tutup", key=f"cb_{r['ID']}"):
                    st.session_state[f"v_{r['ID']}"] = False; st.rerun()
        st.divider()

# --- 4. KONDISI TUBUH ---
def show_fisik():
    st.title("📏 Kondisi Tubuh")
    cols = ["Tanggal", "BB", "TB", "Keluhan"]
    df = load_db("data_fisik.csv", cols)
    with st.form("f_fisik"):
        c1, c2 = st.columns(2)
        d1 = c1.date_input("Tanggal")
        d2 = c1.number_input("BB (kg)", step=0.1)
        d3 = c2.number_input("TB (cm)", step=0.1)
        d4 = st.text_area("Keluhan")
        if st.form_submit_button("Simpan"):
            new_row = pd.DataFrame([[str(d1), d2, d3, d4]], columns=cols)
            save_db(pd.concat([df, new_row]), "data_fisik.csv"); st.rerun()
    st.dataframe(df.sort_values("Tanggal", ascending=False), use_container_width=True)

# --- UTAMA ---
def main():
    login_system()
    st.sidebar.title("🏥 Health Global Yudi")
    m = st.sidebar.radio("Navigasi", ["Dashboard", "Jadwal Kontrol", "Penyimpanan Berkas", "Kondisi Tubuh"])
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False; st.rerun()
    
    if m == "Dashboard": show_dashboard()
    elif m == "Jadwal Kontrol": show_jadwal()
    elif m == "Penyimpanan Berkas": show_berkas()
    elif m == "Kondisi Tubuh": show_fisik()

if __name__ == "__main__":
    main()
                           
