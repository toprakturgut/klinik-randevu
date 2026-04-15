import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import time

# --- 1. GÜVENLİK ---
def sifre_kontrol():
    if "sifre_onayi" not in st.session_state:
        st.session_state["sifre_onayi"] = False
    if not st.session_state["sifre_onayi"]:
        st.title("🔒 Klinik Giriş")
        # Şifreyi koddan değil, Secrets'tan çekiyoruz
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

# --- 2. AYARLAR VE BAĞLANTI ---
st.set_page_config(page_title="Klinik Randevu Sistemi", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

def verileri_cek():
    # Sayfadaki ilk satırı başlık olarak alarak oku
    return conn.read(ttl="0s")

# --- 3. ARAYÜZ ---
st.title("Klinik Randevu Yönetimi")
tab_takvim, tab_ekle = st.tabs(["📅 Randevu Takvimi", "➕ Yeni Randevu Ekle"])

df = verileri_cek()

with tab_takvim:
    st.header("Randevu Kayıtları")
    gorunum = st.radio("Görünüm Seçin:", ["Haftalık Takvim", "Aylık Liste/İptal", "Tüm Geçmiş"], horizontal=True)
    
    if df.empty:
        st.info("Henüz kayıt bulunmuyor.")
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
            # Pandas ID kolonunu gösterme ama seçim için kullan
            secim = st.dataframe(df, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
            if len(secim.selection.rows) > 0:
                idx = secim.selection.rows[0]
                if st.button("Seçili Randevuyu İptal Et", type="primary"):
                    yeni_df = df.drop(df.index[idx])
                    conn.update(data=yeni_df)
                    st.success("İptal edildi!")
                    time.sleep(1)
                    st.rerun()

        elif gorunum == "Tüm Geçmiş":
            st.dataframe(df.sort_values(by=["tarih", "saat"]), use_container_width=True, hide_index=True)

with tab_ekle:
    st.header("Yeni Randevu")
    with st.form("ekle_form", clear_on_submit=True):
        h_ad = st.text_input("Hasta Adı")
        ted = st.selectbox("Tedavi", ["Pilates", "Manuel Terapi"])
        tar = st.date_input("Tarih", datetime.date.today())
        saat = st.selectbox("Saat", [f"{str(i).zfill(2)}:00" for i in range(8, 24)])
        
        if st.form_submit_button("Kaydet"):
            if not h_ad:
                st.error("Lütfen hasta adı girin!")
            else:
                # Çakışma kontrolü
                if not df[(df['tarih'] == str(tar)) & (df['saat'] == saat)].empty:
                    st.error("Bu saatte başka bir randevu var!")
                else:
                    yeni_data = pd.DataFrame([{"id": len(df)+1, "hasta_adi": h_ad, "tedavi": ted, "tarih": str(tar), "saat": saat}])
                    guncel_df = pd.concat([df, yeni_data], ignore_index=True)
                    conn.update(data=guncel_df)
                    st.success("Randevu başarıyla eklendi!")
                    time.sleep(1)
                    st.rerun()
