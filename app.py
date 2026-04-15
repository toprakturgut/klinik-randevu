import streamlit as st
import sqlite3
import pandas as pd
import datetime
import time

# --- 1. GÜVENLİK: ŞİFRE EKRANI ---
def sifre_kontrol():
    if "sifre_onayi" not in st.session_state:
        st.session_state["sifre_onayi"] = False

    if not st.session_state["sifre_onayi"]:
        st.title("🔒 Klinik Giriş")
        st.warning("Lütfen erişim şifresini giriniz.")
        
        # Buradaki şifreyi istediğin bir şeyle değiştir (örn: Klinik2026)
        girilen_sifre = st.text_input("Şifre", type="password")
        
        if st.button("Giriş Yap"):
            if girilen_sifre == "Klinik2026": 
                st.session_state["sifre_onayi"] = True
                st.rerun()
            else:
                st.error("Hatalı şifre!")
        st.stop()

sifre_kontrol()

# --- 2. VERİTABANI VE AYARLAR ---
def init_db():
    conn = sqlite3.connect('randevular.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS randevular (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hasta_adi TEXT,
            tedavi TEXT,
            tarih TEXT,
            saat TEXT
        )
    ''')
    conn.commit()
    return conn

conn = init_db()

st.set_page_config(page_title="Klinik Randevu Sistemi", layout="wide")
st.title("Klinik Randevu Yönetimi")

tab_takvim, tab_ekle = st.tabs(["📅 Randevu Takvimi", "➕ Yeni Randevu Ekle"])

# --- SEKME 1: RANDEVU TAKVİMİ (SİLME ÖZELLİĞİ İÇİNDE) ---
with tab_takvim:
    st.header("Randevu Kayıtları")
    gorunum = st.radio("Görünüm Seçin:", ["Haftalık Takvim", "Aylık Liste", "Günlük Filtre", "Tüm Geçmiş"], horizontal=True)
    st.markdown("---")
    
    # HAFTALIK MATRİS (SADECE GÖRÜNTÜLEME)
    if gorunum == "Haftalık Takvim":
        st.subheader("Haftalık Randevu Tablosu")
        secilen_tarih = st.date_input("Hafta seçmek için bir gün işaretleyin:", datetime.date.today())
        pazartesi = secilen_tarih - datetime.timedelta(days=secilen_tarih.weekday())
        pazar = pazartesi + datetime.timedelta(days=6)
        st.info(f"Gösterilen Hafta: **{pazartesi.strftime('%d.%m.%Y')} - {pazar.strftime('%d.%m.%Y')}**")
        
        df_hafta = pd.read_sql_query(f"SELECT tarih, saat, hasta_adi, tedavi FROM randevular WHERE tarih >= '{pazartesi}' AND tarih <= '{pazar}'", conn)
        saatler = [f"{str(i).zfill(2)}:00" for i in range(8, 24)]
        gun_isimleri = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        tarihler = [(pazartesi + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
        kolonlar = [f"{gun_isimleri[i]} ({tarihler[i]})" for i in range(7)]
        
        tablo = pd.DataFrame(index=saatler, columns=kolonlar).fillna("-")
        if not df_hafta.empty:
            for _, row in df_hafta.iterrows():
                if row['tarih'] in tarihler:
                    tablo.at[row['saat'], kolonlar[tarihler.index(row['tarih'])]] = f"{row['hasta_adi']} ({row['tedavi']})"
        st.dataframe(tablo, use_container_width=True)
        st.caption("💡 Randevu silmek için diğer görünümleri (Aylık, Günlük vb.) kullanıp satıra tıklayabilirsiniz.")

    # DİĞER GÖRÜNÜMLER (TIKLA-SİL ÖZELLİKLİ)
    else:
        if gorunum == "Aylık Liste":
            bugun = datetime.date.today()
            aylar = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
            c1, c2, _ = st.columns([1, 1, 2])
            secilen_ay = aylar.index(c1.selectbox("Ay", aylar, index=bugun.month-1)) + 1
            secilen_yil = c2.selectbox("Yıl", range(bugun.year-1, bugun.year+3), index=1)
            query = f"SELECT id, tarih AS 'Tarih', saat AS 'Saat', hasta_adi AS 'Hasta Adı', tedavi AS 'Tedavi' FROM randevular WHERE tarih LIKE '{secilen_yil}-{str(secilen_ay).zfill(2)}-%' ORDER BY tarih, saat"
        
        elif gorunum == "Günlük Filtre":
            t = st.date_input("Tarih seçin:", datetime.date.today())
            query = f"SELECT id, saat AS 'Saat', hasta_adi AS 'Hasta Adı', tedavi AS 'Tedavi' FROM randevular WHERE tarih='{t}' ORDER BY saat"
        
        else: # Tüm Geçmiş
            query = "SELECT id, tarih AS 'Tarih', saat AS 'Saat', hasta_adi AS 'Hasta Adı', tedavi AS 'Tedavi' FROM randevular ORDER BY tarih DESC, saat"

        df_view = pd.read_sql_query(query, conn)
        
        if df_view.empty:
            st.info("Kayıt bulunamadı.")
        else:
            st.markdown("👇 **İptal etmek için satıra tıklayın:**")
            secim = st.dataframe(df_view, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", column_config={"id": None})
            
            if len(secim.selection.rows) > 0:
                satir = secim.selection.rows[0]
                sil_id = int(df_view.iloc[satir]['id'])
                st.warning(f"⚠️ **{df_view.iloc[satir]['Hasta Adı']}** randevusunu silmek istediğinize emin misiniz?")
                if st.button("Evet, Sil", type="primary"):
                    conn.cursor().execute("DELETE FROM randevular WHERE id=?", (sil_id,))
                    conn.commit()
                    st.success("Silindi!")
                    time.sleep(1)
                    st.rerun()

# --- SEKME 2: YENİ RANDEVU EKLE ---
with tab_ekle:
    st.header("Yeni Randevu")
    with st.form("form", clear_on_submit=True):
        h_ad = st.text_input("Hasta Adı")
        ted = st.selectbox("Tedavi", ["Pilates", "Manuel Terapi"])
        tar = st.date_input("Tarih", datetime.date.today())
        saatler = [f"{str(i).zfill(2)}:00" for i in range(8, 24)]
        st_sec = st.selectbox("Saat", saatler)
        if st.form_submit_button("Kaydet"):
            if not h_ad: st.error("İsim girin!")
            else:
                c = conn.cursor()
                if c.execute("SELECT * FROM randevular WHERE tarih=? AND saat=?", (str(tar), st_sec)).fetchone():
                    st.error("Bu saat dolu!")
                else:
                    c.execute("INSERT INTO randevular (hasta_adi, tedavi, tarih, saat) VALUES (?,?,?,?)", (h_ad, ted, str(tar), st_sec))
                    conn.commit()
                    st.success("Eklendi!")
                    time.sleep(1)
                    st.rerun()