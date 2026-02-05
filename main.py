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

# API KEY MAS YUDI (SUDAH TERPASANG)
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
        st.title("🔐 Login Global Health Access")
        st.markdown("---")
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.button("Masuk"):
            if user == "admin" and pw == "yudi123":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Username atau Password salah")
        st.stop()

# --- FUNGSI ANALISA AI (ANTI 404) ---
def analisa_ai(teks):
    if not teks.strip():
        return "Teks dokumen tidak terbaca. Pastikan PDF bukan hasil scan gambar murni."
    
    # Mencoba beberapa variasi nama model untuk menghindari error 404
    model_names = ['gemini-1.5-flash', 'models/gemini-1.5-flash']
    
    last_error = ""
    for name in model_names:
        try:
            model = genai.GenerativeModel(name)
            prompt = (
                f"Anda adalah asisten medis. Analisa hasil pemeriksaan medis ini untuk pasien bernama Yudi "
                f"secara ringkas dan dalam Bahasa Indonesia: {teks}. Jelaskan temuan pentingnya."
            )
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            last_error = str(e)
            continue
            
    return f"Gagal analisa. Error: {last_error}. Pastikan API Key aktif."

# --- 1. DASHBOARD ---
def show_dashboard():
    st.title("🏠 Dashboard")
    df_fisik = load_db("data_fisik.csv", ["Tanggal", "BB", "TB", "Keluhan"])
    df_berkas = load_db("berkas.csv", ["ID", "Tanggal", "Judul", "Jenis", "Analisa", "File_Data"])
    df_jadwal = load_db("jadwal_rs.csv", ["ID", "Tanggal", "Poli", "Tindakan", "Catatan", "Status"])
    
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("📈 Grafik Kesehatan (BB & TB)")
        if not df_fisik.empty:
            df_fisik['Tanggal'] = pd.to_datetime(df_fisik['Tanggal'])
            df_fisik = df_fisik.sort_values('Tanggal')
            fig, ax1 = plt.subplots(figsize=(10, 5))
            
            # Sumbu Y kiri untuk BB
            ax1.set_xlabel('Tanggal')
            ax1.set_ylabel('Berat Badan (kg)', color='red')
            ax1.plot(df_fisik['Tanggal'], df_fisik['BB'], label='BB', color='red', marker='o', linewidth=2)
            ax1.tick_params(axis='y', labelcolor='red')
            
            # Sumbu Y kanan untuk TB
            ax2 = ax1.twinx()
            ax2.set_ylabel('Tinggi Badan (cm)', color='blue')
            ax2.plot(df_fisik['Tanggal'], df_fisik['TB'], label='TB', color='blue', marker='s', linewidth=2)
            ax2.tick_params(axis='y', labelcolor='blue')
            
            plt.title("Tren Berat & Tinggi Badan Mas Yudi")
            fig.tight_layout()
            st.pyplot(fig)
        else:
            st.info("Data fisik belum tersedia untuk membuat grafik.")

    with c2:
        st.subheader("📅 Jadwal Mendatang")
        mendatang = df_jadwal[df_jadwal['Status'] == 'Belum Terlaksana'].sort_values('Tanggal').head(2)
        if not mendatang.empty:
            for _, r in mendatang.iterrows():
                st.warning(f"**{r['Tanggal']}**\n{r['Poli']} - {r['Tindakan']}")
        else:
            st.write("Tidak ada jadwal terdekat.")
        
        st.divider()
        st.subheader("🧠 Analisa MRI Terakhir")
        mri = df_berkas[df_berkas['Jenis'] == 'MRI'].sort_values('Tanggal', ascending=False).head(1)
        if not mri.empty:
            st.success(f"📌 {mri['Judul'].values[0]}")
            st.write(mri['Analisa'].values[0])
        else: 
            st.info("Belum ada analisa MRI tersimpan.")

# --- 2. JADWAL KONTROL ---
def show_jadwal():
    st.title("📅 Jadwal Kontrol")
    cols = ["ID", "Tanggal", "Poli", "Tindakan", "Catatan", "Status"]
    df = load_db("jadwal_rs.csv", cols)
    
    with st.expander("➕ Tambah Jadwal Kontrol Baru"):
        with st.form("f_jadwal", clear_on_submit=True):
            d1, d2 = st.date_input("Tanggal Kontrol"), st.text_input("Nama Poli")
            d3, d4 = st.text_input("Tindakan"), st.text_area("Catatan")
            if st.form_submit_button("Simpan Jadwal"):
                nid = str(int(datetime.now().timestamp()))
                nr = pd.DataFrame([[nid, str(d1), d2, d3, d4, "Belum Terlaksana"]], columns=cols)
                save_db(pd.concat([df, nr]), "jadwal_rs.csv"); st.rerun()

    t1, t2 = st.tabs(["🗓 Akan Datang", "✅ Sudah Terlaksana"])
    with t1:
        df_a = df[df['Status'] == 'Belum Terlaksana']
        if df_a.empty: st.info("Tidak ada jadwal mendatang.")
        for i, r in df_a.iterrows():
            c1, c2 = st.columns([4, 1])
            c1.write(f"📅 **{r['Tanggal']}** | {r['Poli']}")
            if c2.button("🔍 Detail", key=f"d_{r['ID']}"):
                st.session_state[f"view_j_{r['ID']}"] = not st.session_state.get(f"view_j_{r['ID']}", False)
            if st.session_state.get(f"view_j_{r['ID']}", False):
                st.info(f"**Tindakan:** {r['Tindakan']}\n\n**Catatan:** {r['Catatan']}")
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("✅ Tandai Selesai", key=f"s_{r['ID']}"):
                    df.loc[df['ID'] == r['ID'], 'Status'] = 'Sudah Terlaksana'
                    save_db(df, "jadwal_rs.csv"); st.rerun()
                if col_btn2.button("🗑️ Hapus Jadwal", key=f"h_{r['ID']}"):
                    save_db(df[df['ID'] != r['ID']], "jadwal_rs.csv"); st.rerun()
            st.divider()
    with t2:
        df_s = df[df['Status'] == 'Sudah Terlaksana']
        for i, r in df_s.iterrows():
            cc1, cc2 = st.columns([4, 1])
            cc1.write(f"✅ {r['Tanggal']} - {r['Poli']}")
            if cc2.button("🗑️ Hapus", key=f"del_s_{r['ID']}"):
                save_db(df[df['ID'] != r['ID']], "jadwal_rs.csv"); st.rerun()

# --- 3. PENYIMPANAN BERKAS ---
def show_berkas():
    st.title("📁 Penyimpanan Berkas Penting")
    cols = ["ID", "Tanggal", "Judul", "Jenis", "Analisa", "File_Data"]
    df = load_db("berkas.csv", cols)
    
    with st.expander("➕ Upload Berkas PDF Baru"):
        with st.form("up_b"):
            d1, d2 = st.date_input("Tanggal Berkas"), st.text_input("Judul Berkas")
            d3 = st.selectbox("Jenis Berkas", ["MRI", "Lab", "Resep", "Lainnya"])
            f = st.file_uploader("Upload File (PDF)", type="pdf")
            if st.form_submit_button("Simpan & Jalankan Analisa AI"):
                if f:
                    with st.spinner("Sedang menganalisa dengan AI..."):
                        b64 = base64.b64encode(f.read()).decode('utf-8')
                        doc = fitz.open(stream=base64.b64decode(b64), filetype="pdf")
                        txt = "".join([p.get_text() for p in doc])
                        ana = analisa_ai(txt)
                        nid = str(int(datetime.now().timestamp()))
                        nr = pd.DataFrame([[nid, str(d1), d2, d3, ana, b64]], columns=cols)
                        save_db(pd.concat([df, nr]), "berkas.csv"); st.rerun()

    for i, r in df.sort_values("Tanggal", ascending=False).iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"📄 **[{r['Jenis']}]** {r['Judul']} ({r['Tanggal']})")
        if c3.button("🔍 Buka & Analisa", key=f"v_{r['ID']}"):
            st.session_state[f"view_b_{r['ID']}"] = not st.session_state.get(f"view_b_{r['ID']}", False)
        if st.session_state.get(f"view_b_{r['ID']}", False):
            st.success(f"**Hasil Analisa AI:**\n\n{r['Analisa']}")
            pdf_code = f'<iframe src="data:application/pdf;base64,{r["File_Data"]}" width="100%" height="600"></iframe>'
            st.markdown(pdf_code, unsafe_allow_html=True)
            if st.button("🗑️ Hapus Berkas Ini Secara Permanen", key=f"hb_{r['ID']}"):
                save_db(df[df['ID'] != r['ID']], "berkas.csv"); st.rerun()
        st.divider()

# --- 4. PENCATATAN KONDISI TUBUH ---
def show_fisik():
    st.title("📏 Pencatatan Kondisi Tubuh")
    cols = ["Tanggal", "BB", "TB", "Keluhan"]
    df = load_db("data_fisik.csv", cols)
    with st.form("f_f"):
        c1, c2 = st.columns(2)
        d1 = c1.date_input("Tanggal Pencatatan")
        bb = c1.number_input("Berat Badan (kg)", step=0.1)
        tb = c2.number_input("Tinggi Badan (cm)", step=0.1)
        kl = st.text_area("Apa yang dirasakan saat ini? (Keluhan)")
        if st.form_submit_button("Simpan Data Fisik"):
            nr = pd.DataFrame([[str(d1), bb, tb, kl]], columns=cols)
            save_db(pd.concat([df, nr]), "data_fisik.csv"); st.rerun()
    st.subheader("Riwayat Data Fisik")
    st.dataframe(df.sort_values("Tanggal", ascending=False), use_container_width=True)

# --- FUNGSI UTAMA ---
def main():
    login_system()
    st.sidebar.title("🌍 Navigasi Menu")
    m = st.sidebar.radio("Pilih Halaman:", ["Dashboard", "Jadwal Kontrol", "Penyimpanan Berkas", "Kondisi Tubuh"])
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Keluar (Logout)"):
        st.session_state.logged_in = False; st.rerun()
    
    if m == "Dashboard": show_dashboard()
    elif m == "Jadwal Kontrol": show_jadwal()
    elif m == "Penyimpanan Berkas": show_berkas()
    elif m == "Kondisi Tubuh": show_fisik()

if __name__ == "__main__":
    main()
            
