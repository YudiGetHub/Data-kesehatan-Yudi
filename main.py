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

# API KEY MAS YUDI (Pastikan Mas sudah membuat Key Baru jika yang lama kena Warning)
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
        st.info("Selamat datang kembali, Mas Yudi.")
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.button("Masuk"):
            if user == "admin" and pw == "yudi123":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Username atau Password salah")
        st.stop()

# --- FUNGSI ANALISA AI (ANTI 404 & MULTI-MODEL) ---
def analisa_ai(teks):
    if not teks.strip():
        return "Gagal membaca teks. Pastikan PDF berisi teks digital, bukan hasil foto/scan gambar."
    
    # Daftar model yang akan dicoba satu per satu jika gagal (Fail-Safe)
    daftar_model = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
    
    for nama_model in daftar_model:
        try:
            model = genai.GenerativeModel(nama_model)
            prompt = (
                f"Analisa secara medis, ringkas, dan jelas dalam Bahasa Indonesia untuk pasien bernama Yudi: {teks}. "
                "Fokus pada temuan abnormal dan berikan langkah tindak lanjut yang disarankan."
            )
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            # Jika error 404 (model tidak ditemukan), coba model berikutnya di daftar
            if "404" in str(e):
                continue
            else:
                return f"Gagal analisa: {str(e)}"
    
    return "Maaf, semua model AI Google (Flash/Pro) saat ini tidak merespons API Key Anda. Periksa kembali status API Key di Google AI Studio."

# --- 1. DASHBOARD ---
def show_dashboard():
    st.title("🏠 Dashboard Kesehatan")
    df_fisik = load_db("data_fisik.csv", ["Tanggal", "BB", "TB", "Keluhan"])
    df_berkas = load_db("berkas.csv", ["ID", "Tanggal", "Judul", "Jenis", "Analisa", "File_Data"])
    df_jadwal = load_db("jadwal_rs.csv", ["ID", "Tanggal", "Poli", "Tindakan", "Catatan", "Status"])

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("📈 Tren Kondisi Fisik")
        if not df_fisik.empty:
            df_fisik['Tanggal'] = pd.to_datetime(df_fisik['Tanggal'])
            df_fisik = df_fisik.sort_values('Tanggal')
            fig, ax1 = plt.subplots(figsize=(10, 5))
            ax1.set_xlabel('Tanggal')
            ax1.set_ylabel('Berat Badan (kg)', color='tab:red')
            ax1.plot(df_fisik['Tanggal'], df_fisik['BB'], color='tab:red', marker='o', label='BB')
            ax1.tick_params(axis='y', labelcolor='tab:red')

            ax2 = ax1.twinx()
            ax2.set_ylabel('Tinggi Badan (cm)', color='tab:blue')
            ax2.plot(df_fisik['Tanggal'], df_fisik['TB'], color='tab:blue', marker='s', label='TB')
            ax2.tick_params(axis='y', labelcolor='tab:blue')
            
            fig.tight_layout()
            st.pyplot(fig)
        else:
            st.info("Belum ada data fisik untuk grafik.")

    with col2:
        st.subheader("📅 Jadwal RS Terdekat")
        mendatang = df_jadwal[df_jadwal['Status'] == 'Belum Terlaksana'].sort_values('Tanggal').head(2)
        if not mendatang.empty:
            for _, r in mendatang.iterrows():
                st.warning(f"**{r['Tanggal']}**\n{r['Poli']} - {r['Tindakan']}")
        
        st.divider()
        st.subheader("🧠 Temuan MRI Terakhir")
        mri = df_berkas[df_berkas['Jenis'] == 'MRI'].sort_values('Tanggal', ascending=False).head(1)
        if not mri.empty:
            st.success(f"📌 {mri['Judul'].values[0]}")
            st.write(mri['Analisa'].values[0])
        else:
            st.info("Data MRI belum tersedia.")

# --- 2. JADWAL KONTROL (PERBAIKAN FITUR HAPUS) ---
def show_jadwal():
    st.title("📅 Jadwal Kontrol")
    cols = ["ID", "Tanggal", "Poli", "Tindakan", "Catatan", "Status"]
    df = load_db("jadwal_rs.csv", cols)

    with st.expander("➕ Tambah Jadwal Baru"):
        with st.form("form_jadwal", clear_on_submit=True):
            d1, d2 = st.date_input("Tanggal"), st.text_input("Poli/RS")
            d3, d4 = st.text_input("Tujuan/Tindakan"), st.text_area("Catatan")
            if st.form_submit_button("Simpan"):
                new_id = str(int(datetime.now().timestamp()))
                new_row = pd.DataFrame([[new_id, str(d1), d2, d3, d4, "Belum Terlaksana"]], columns=cols)
                save_db(pd.concat([df, new_row]), "jadwal_rs.csv"); st.rerun()

    t1, t2 = st.tabs(["Akan Datang", "Selesai"])
    with t1:
        df_a = df[df['Status'] == 'Belum Terlaksana']
        for _, r in df_a.iterrows():
            c1, c2 = st.columns([4, 1])
            c1.write(f"📅 **{r['Tanggal']}** | {r['Poli']} ({r['Tindakan']})")
            if c2.button("🔍 Detail", key=f"det_{r['ID']}"):
                st.session_state[f"vj_{r['ID']}"] = not st.session_state.get(f"vj_{r['ID']}", False)
            if st.session_state.get(f"vj_{r['ID']}", False):
                st.info(f"Catatan: {r['Catatan']}")
                b1, b2 = st.columns(2)
                if b1.button("✅ Selesai", key=f"ok_{r['ID']}"):
                    df.loc[df['ID'] == r['ID'], 'Status'] = 'Sudah Terlaksana'
                    save_db(df, "jadwal_rs.csv"); st.rerun()
                if b2.button("🗑️ Hapus", key=f"del_{r['ID']}"):
                    save_db(df[df['ID'] != r['ID']], "jadwal_rs.csv"); st.rerun()
            st.divider()
    with t2:
        st.dataframe(df[df['Status'] == 'Sudah Terlaksana'])

# --- 3. BERKAS (FITUR BUKA & HAPUS) ---
def show_berkas():
    st.title("📁 Berkas & Analisa AI")
    cols = ["ID", "Tanggal", "Judul", "Jenis", "Analisa", "File_Data"]
    df = load_db("berkas.csv", cols)

    with st.expander("➕ Upload PDF Hasil Medis"):
        with st.form("up_berkas"):
            d1, d2 = st.date_input("Tanggal Berkas"), st.text_input("Nama/Judul Berkas")
            d3 = st.selectbox("Kategori", ["MRI", "Lab", "Resep", "Lainnya"])
            f = st.file_uploader("Pilih File PDF", type="pdf")
            if st.form_submit_button("Simpan & Analisa"):
                if f:
                    with st.spinner("AI sedang membaca berkas..."):
                        b64 = base64.b64encode(f.read()).decode('utf-8')
                        doc = fitz.open(stream=base64.b64decode(b64), filetype="pdf")
                        txt = "".join([p.get_text() for p in doc])
                        ana = analisa_ai(txt)
                        nid = str(int(datetime.now().timestamp()))
                        new_row = pd.DataFrame([[nid, str(d1), d2, d3, ana, b64]], columns=cols)
                        save_db(pd.concat([df, new_row]), "berkas.csv"); st.rerun()

    for _, r in df.sort_values("Tanggal", ascending=False).iterrows():
        with st.container():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"📄 **{r['Judul']}** ({r['Tanggal']})")
            c2.write(f"🏷️ {r['Jenis']}")
            if c3.button("🔍 Buka", key=f"open_{r['ID']}"):
                st.session_state[f"vb_{r['ID']}"] = not st.session_state.get(f"vb_{r['ID']}", False)
            if st.session_state.get(f"vb_{r['ID']}", False):
                st.markdown(f"**Analisa AI:**\n{r['Analisa']}")
                pdf_viewer = f'<iframe src="data:application/pdf;base64,{r["File_Data"]}" width="100%" height="500"></iframe>'
                st.markdown(pdf_viewer, unsafe_allow_html=True)
                if st.button("🗑️ Hapus Berkas", key=f"hb_{r['ID']}"):
                    save_db(df[df['ID'] != r['ID']], "berkas.csv"); st.rerun()
        st.divider()

# --- 4. KONDISI TUBUH ---
def show_fisik():
    st.title("📏 Catat Kondisi Fisik")
    cols = ["Tanggal", "BB", "TB", "Keluhan"]
    df = load_db("data_fisik.csv", cols)
    with st.form("form_fisik"):
        d1 = st.date_input("Tanggal")
        c1, c2 = st.columns(2)
        d2 = c1.number_input("Berat Badan (kg)", step=0.1)
        d3 = c2.number_input("Tinggi Badan (cm)", step=0.1)
        d4 = st.text_area("Keluhan/Perasaan hari ini")
        if st.form_submit_button("Simpan Data"):
            save_db(pd.concat([df, pd.DataFrame([[str(d1), d2, d3, d4]], columns=cols)]), "data_fisik.csv"); st.rerun()
    st.dataframe(df.sort_values("Tanggal", ascending=False))

# --- MAIN ---
def main():
    login_system()
    st.sidebar.title("🏥 Health Manager")
    m = st.sidebar.radio("Navigasi", ["Dashboard", "Jadwal Kontrol", "Penyimpanan Berkas", "Kondisi Tubuh"])
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False; st.rerun()
    if m == "Dashboard": show_dashboard()
    elif m == "Jadwal Kontrol": show_jadwal()
    elif m == "Penyimpanan Berkas": show_berkas()
    elif m == "Kondisi Tubuh": show_fisik()

if __name__ == "__main__":
    main()

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
        
