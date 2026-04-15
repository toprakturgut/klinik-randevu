import streamlit as st
from supabase import create_client, Client
import pandas as pd
import datetime
import time

# --- 1. GÜVENLİK (KURŞUNGEÇİRMEZ VERSİYON) ---
def sifre_kontrol():
    # .get() metodu sayesinde "sifre_onayi bulunamadı" hatasını sonsuza dek yok ettik
    if not st.session_state.get("sifre_onayi", False):
        st.title("🔒 Klinik Giriş")
        dogru_sifre = st.secrets["credentials"]["sifre"]
        girilen_sifre = st.text_input("Şifre", type="password")
        if st.button("Giriş Yap"):
            if girilen_sifre == dogru_sifre:
                st.session_state["sifre_onayi"] = True
                st.rerun()
            else:
                st.error("Hatalı şifre!")
        st.stop()

sifre_kontrol()

# --- 2. SUPABASE BAĞLANTISI ---
@st.cache_resource
def init_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_connection()

def verileri_cek():
    # Supabase'den verileri çek ve Pandas DataFrame'e çevir
    response = supabase.table("randevular").select("*").execute()
    return pd.DataFrame(response.data)

# --- 3. ARAYÜZ ---
st.set_page_config(page_title="Klinik Randevu Sistemi", layout="wide")
st.title("Klinik Randevu Yönetimi")

tab_takvim, tab_ekle = st.tabs(["📅 Randevu Takvimi", "➕ Yeni Randevu Ekle"])

df = verileri_cek()

# TABLOLAR İÇİN MAKYAJ (GÖRÜNTÜ) AYARLARI
sutun_isimleri = {
    "id": None, # ID sütununu gizler
    "hasta_adi": "Hasta Adı",
    "tedavi": "Tedavi Yöntemi",
    "tarih": "Tarih",
    "saat": "Saat"
}

with tab_takvim:
    st.header("Randevu Kayıtları")
    gorunum = st.radio("Görünüm Seçin:", ["Haftalık Takvim", "Aylık Liste/İptal", "Tüm Geçmiş"], horizontal=True)
    
    if df.empty:
        st.info("Sistemde henüz kayıt bulunmuyor.")
    else:
        if gorunum == "Haftalık Takvim":
            secilen_tarih = st.date_input("Hafta seçin:", datetime.date.today())
            pazartesi = secilen_tarih - datetime.timedelta(days=secilen_tarih.weekday())
            tarihler = [(pazartesi + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
            gun_isimleri = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
            kolonlar = [f"{gun_isimleri[i]} ({tarihler[i]})" for i in range(7)]
            saatler = [f"{str(i).zfill(2)}:00" for i in range(8, 24)]
            
            tablo = pd.DataFrame(index=saatler, columns=kolonlar).fillna("-")
            
            for _, row in df.iterrows():
                if str(row['tarih']) in tarihler:
                    col_idx = tarihler.index(str(row['tarih']))
                    tablo.at[row['saat'], kolonlar[col_idx]] = f"{row['hasta_adi']} ({row['tedavi']})"
            st.dataframe(tablo, use_container_width=True)

        elif gorunum == "Aylık Liste/İptal":
            st.markdown("👇 **İptal etmek için satıra tıklayın ve butona basın:**")
            
            # column_config=sutun_isimleri kısmını ekledik
            secim = st.dataframe(df, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", column_config=sutun_isimleri)
            
            if len(secim.selection.rows) > 0:
                satir = secim.selection.rows[0]
                silinecek_id = int(df.iloc[satir]['id'])
                if st.button("Seçili Randevuyu İptal Et", type="primary"):
                    supabase.table("randevular").delete().eq("id", silinecek_id).execute()
                    st.success("Randevu başarıyla iptal edildi!")
                    time.sleep(1.5)
                    st.rerun()

        elif gorunum == "Tüm Geçmiş":
            # column_config=sutun_isimleri kısmını ekledik
            st.dataframe(df.sort_values(by=["tarih", "saat"]), use_container_width=True, hide_index=True, column_config=sutun_isimleri)

with tab_ekle:
    st.header("Yeni Randevu Oluştur")
    with st.form("ekle_form", clear_on_submit=True):
        h_ad = st.text_input("Hasta Adı")
        ted = st.selectbox("Tedavi Yöntemi", ["Pilates", "Manuel Terapi"])
        tar = st.date_input("Randevu Tarihi", datetime.date.today())
        saat = st.selectbox("Randevu Saati", [f"{str(i).zfill(2)}:00" for i in range(8, 24)])
        
        if st.form_submit_button("Randevuyu Kaydet"):
            if not h_ad.strip():
                st.error("Lütfen hasta adı giriniz!")
            else:
                if not df.empty and not df[(df['tarih'] == str(tar)) & (df['saat'] == saat)].empty:
                    st.error("Dikkat! Bu saatte başka bir randevu mevcut.")
                else:
                    supabase.table("randevular").insert({
                        "hasta_adi": h_ad,
                        "tedavi": ted,
                        "tarih": str(tar),
                        "saat": saat
                    }).execute()
                    st.success("Randevu başarıyla eklendi!")
                    time.sleep(1.5)
                    st.rerun()
