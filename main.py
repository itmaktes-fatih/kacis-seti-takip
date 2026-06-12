import sqlite3
import os
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen  # Ekran yönetimi için
from kivy.utils import get_color_from_hex, platform
from kivy.graphics import Color, RoundedRectangle
from openpyxl import Workbook

# Renk Paleti (Endüstriyel İSG Teması)
ARKA_PLAN = get_color_from_hex("#1E2022")       # Koyu Antrasit
ISG_SARISI = get_color_from_hex("#F39C12")      # Dräger / Emniyet Sarısı
FORM_RENGI = get_color_from_hex("#2C3E50")      # Koyu Mavi/Gri Form Kartı
YAZI_RENGI = get_color_from_hex("#ECF0F1")      # Beyaza Yakın Gri
BUTON_YESIL = get_color_from_hex("#27AE60")     # Kaydet
BUTON_MAVI = get_color_from_hex("#2980B9")      # Güncelle
BUTON_KIRMIZI = get_color_from_hex("#C0392B")    # Sil

# --- ANDROID UYUMLU GÜVENLİ DOSYA YOLU ---
def get_db_path():
    try:
        return os.path.join(App.get_running_app().user_data_dir, "kacis_setleri_v2.db")
    except Exception:
        return "kacis_setleri_v2.db"

def veritabanini_hazirla():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    # birim ve gorev alanları kaldırıldı, sicil_no yerine tc_no eklendi
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS personeller (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        firma TEXT,
        tc_no TEXT,
        ad_soyad TEXT,
        seri_no TEXT,
        son_kullanma TEXT
    )
    """)
    conn.commit()
    conn.close()

class RenkliKutu(BoxLayout):
    def __init__(self, bg_color, radius=[10], **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=radius)
        self.bind(pos=self.guncelle, size=self.guncelle)
        
    def guncelle(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

# --- 1. EKRAN: KULLANICI GİRİŞ EKRANI ---
class GirisEkrani(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Ana dikey düzen
        duzen = BoxLayout(orientation='vertical', padding=40, spacing=15)
        
        # Logo / Başlık Alanı
        duzen.add_widget(Label(
            text="🚨\nKAÇIŞ SETİ TAKİP\nSİSTEMİ GİRİŞİ", 
            font_size='24sp', 
            bold=True, 
            color=ISG_SARISI, 
            halign="center",
            size_hint_y=0.3
        ))
        
        # Giriş Form Kartı
        form_alani = RenkliKutu(bg_color=FORM_RENGI, orientation='vertical', padding=15, spacing=10, size_hint_y=0.4)
        
        self.input_kullanici = TextInput(hint_text="Kullanıcı Adı", multiline=False, font_size='16sp', write_tab=False)
        self.input_sifre = TextInput(hint_text="Şifre", password=True, multiline=False, font_size='16sp', write_tab=False)
        
        self.lbl_hata = Label(text="Lütfen bilgilerinizi giriniz.", color=YAZI_RENGI, font_size='13sp', size_hint_y=0.2)
        
        form_alani.add_widget(self.input_kullanici)
        form_alani.add_widget(self.input_sifre)
        form_alani.add_widget(self.lbl_hata)
        duzen.add_widget(form_alani)
        
        # Giriş Butonu
        btn_giris = Button(
            text="SİSTEME GİRİŞ YAP", 
            background_normal='', 
            background_color=ISG_SARISI, 
            color=(0,0,0,1), 
            bold=True, 
            font_size='16sp', 
            size_hint_y=0.1
        )
        btn_giris.bind(on_press=self.sistem_giris_kontrol)
        duzen.add_widget(btn_giris)
        
        # Boşluk dengeleyici
        duzen.add_widget(BoxLayout(size_hint_y=0.2))
        
        self.add_widget(duzen)

    def sistem_giris_kontrol(self, instance):
        # Şantiye personeli veya İSG sorumlusu için varsayılan giriş bilgileri
        kullanici_adi = self.input_kullanici.text.strip()
        sifre = self.input_sifre.text.strip()
        
        if kullanici_adi == "admin" and sifre == "1234":
            self.lbl_hata.text = "Giriş Başarılı!"
            self.lbl_hata.color = BUTON_YESIL
            # Ana takip ekranına geçiş yap
            self.manager.current = 'ana_ekran'
        else:
            self.lbl_hata.text = "HATA: Kullanıcı adı veya şifre yanlış!"
            self.lbl_hata.color = BUTON_KIRMIZI


# --- 2. EKRAN: ANA TAKİP EKRANI ---
class AnaTakipEkrani(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.secili_personel_id = None
        
        ana_duzen = BoxLayout(orientation='vertical', padding=15, spacing=10)
        
        # --- Üst Durum Çubuğu ---
        self.lbl_durum = Label(
            text="YÖNETİM PANELİ | KAYIT VE SORGULAMA", 
            size_hint_y=0.05, 
            color=ISG_SARISI,
            bold=True,
            font_size='14sp'
        )
        ana_duzen.add_widget(self.lbl_durum)
        
        # --- Form Kartı (Sadeleştirilmiş Yeni Alanlar) ---
        form_kartı = RenkliKutu(bg_color=FORM_RENGI, orientation='vertical', padding=10, spacing=6, size_hint_y=0.32)
        
        self.input_firma = TextInput(hint_text="Firma Adı (* Zorunlu)", multiline=False, font_size='14sp', background_color=(0.95,0.95,0.95,1))
        self.input_tc = TextInput(hint_text="TC Kimlik No", multiline=False, font_size='14sp', background_color=(0.95,0.95,0.95,1), input_filter='int')
        self.input_ad = TextInput(hint_text="Personel Adı Soyadı (* Zorunlu)", multiline=False, font_size='14sp', background_color=(0.95,0.95,0.95,1))
        self.input_seri = TextInput(hint_text="Cihaz Seri No (* Zorunlu)", multiline=False, font_size='14sp', background_color=(0.95,0.95,0.95,1))
        self.input_skt = TextInput(hint_text="Son Kullanma Tarihi (GG.AA.YYYY) (* Zorunlu)", multiline=False, font_size='14sp', background_color=(0.95,0.95,0.95,1))
        
        form_kartı.add_widget(self.input_firma)
        form_kartı.add_widget(self.input_tc)
        form_kartı.add_widget(self.input_ad)
        form_kartı.add_widget(self.input_seri)
        form_kartı.add_widget(self.input_skt)
        ana_duzen.add_widget(form_kartı)
        
        # --- Yönetim Butonları ---
        islem_butonlari = BoxLayout(orientation='horizontal', size_hint_y=0.06, spacing=8)
        self.btn_ekle = Button(text="KAYDET", background_normal='', background_color=BUTON_YESIL, font_size='13sp', bold=True)
        self.btn_ekle.bind(on_press=self.personel_ekle_click)
        
        self.btn_guncelle = Button(text="GÜNCELLE", background_normal='', background_color=BUTON_MAVI, font_size='13sp', bold=True)
        self.btn_guncelle.bind(on_press=self.personel_guncelle_click)
        
        self.btn_sil = Button(text="SİL", background_normal='', background_color=BUTON_KIRMIZI, font_size='13sp', bold=True)
        self.btn_sil.bind(on_press=self.personel_sil_click)
        
        islem_butonlari.add_widget(self.btn_ekle)
        islem_butonlari.add_widget(self.btn_guncelle)
        islem_butonlari.add_widget(self.btn_sil)
        ana_duzen.add_widget(islem_butonlari)
        
        # --- Arama Çubuğu ---
        arama_duzeni = BoxLayout(orientation='horizontal', spacing=8, size_hint_y=0.06)
        self.input_arama = TextInput(hint_text="ID, TC, İsim veya Seri No ile ara...", multiline=False, font_size='14sp', size_hint_x=0.75, background_color=(1,1,1,1))
        btn_ara = Button(text="ARA", background_normal='', background_color=ISG_SARISI, font_size='13sp', bold=True, size_hint_x=0.25, color=(0,0,0,1))
        btn_ara.bind(on_press=self.arama_yap_click)
        arama_duzeni.add_widget(self.input_arama)
        arama_duzeni.add_widget(btn_ara)
        ana_duzen.add_widget(arama_duzeni)
        
        # --- Alt Raporlama Butonları ---
        liste_buton_duzeni = BoxLayout(orientation='horizontal', size_hint_y=0.06, spacing=8)
        btn_tum_liste = Button(text="Tüm Liste", background_normal='', background_color=get_color_from_hex("#7F8C8D"), font_size='12sp', bold=True)
        btn_tum_liste.bind(on_press=self.tum_listele_click)
        
        btn_kritik_liste = Button(text="⚡ Kritik Olanlar", background_normal='', background_color=get_color_from_hex("#D35400"), font_size='12sp', bold=True)
        btn_kritik_liste.bind(on_press=self.kritik_listele_click)
        
        btn_excel = Button(text="📊 Excel Çıktısı", background_normal='', background_color=get_color_from_hex("#27AE60"), font_size='12sp', bold=True)
        btn_excel.bind(on_press=self.excel_cikti_al_click)
        
        liste_buton_duzeni.add_widget(btn_tum_liste)
        liste_buton_duzeni.add_widget(btn_kritik_liste)
        liste_buton_duzeni.add_widget(btn_excel)
        ana_duzen.add_widget(liste_buton_duzeni)
        
        # --- Rapor / Liste Ekranı Kartı ---
        liste_kartı = RenkliKutu(bg_color=get_color_from_hex("#2C3E50"), orientation='vertical', padding=10, size_hint_y=0.45)
        scroll = ScrollView(bar_width=8)
        self.lbl_liste = Label(
            text="Sonuçlar ve personel listesi bu panelde gösterilir...", 
            size_hint_y=None, 
            halign="left", 
            valign="top",
            font_size='13sp',
            color=YAZI_RENGI
        )
        self.lbl_liste.bind(texture_size=self.lbl_liste.setter('size'))
        scroll.add_widget(self.lbl_liste)
        liste_kartı.add_widget(scroll)
        ana_duzen.add_widget(liste_kartı)
        
        self.add_widget(ana_duzen)

    def formu_temizle(self):
        self.input_firma.text = ""
        self.input_tc.text = ""
        self.input_ad.text = ""
        self.input_seri.text = ""
        self.input_skt.text = ""
        self.secili_personel_id = None

    def zorunlu_alan_kontrolu(self):
        """İstenen alanların doluluğunu denetler."""
        if (not self.input_firma.text.strip() or 
            not self.input_ad.text.strip() or 
            not self.input_seri.text.strip() or 
            not self.input_skt.text.strip()):
            return False
        return True

    def personel_ekle_click(self, instance):
        if not self.zorunlu_alan_kontrolu():
            self.lbl_durum.text = "HATA: Firma, Ad Soyad, Seri No ve SKT alanları ZORUNLUDUR!"
            self.lbl_durum.color = BUTON_KIRMIZI
            return
            
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO personeller (firma, tc_no, ad_soyad, seri_no, son_kullanma)
        VALUES (?, ?, ?, ?, ?)
        """, (self.input_firma.text, self.input_tc.text, self.input_ad.text, self.input_seri.text, self.input_skt.text))
        conn.commit()
        conn.close()
        
        self.lbl_durum.text = f"BAŞARILI: {self.input_ad.text} kaydedildi."
        self.lbl_durum.color = ISG_SARISI
        self.formu_temizle()
        self.tum_listele_click(None)

    def personel_guncelle_click(self, instance):
        if not self.secili_personel_id:
            self.lbl_durum.text = "HATA: Önce arama yapıp bir personel seçmelisiniz!"
            self.lbl_durum.color = BUTON_KIRMIZI
            return
            
        if not self.zorunlu_alan_kontrolu():
            self.lbl_durum.text = "HATA: Güncelleme için zorunlu alanları boş bırakamazsınız!"
            self.lbl_durum.color = BUTON_KIRMIZI
            return
            
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE personeller 
        SET firma=?, tc_no=?, ad_soyad=?, seri_no=?, son_kullanma=?
        WHERE id=?
        """, (self.input_firma.text, self.input_tc.text, self.input_ad.text, self.input_seri.text, self.input_skt.text, self.secili_personel_id))
        conn.commit()
        conn.close()
        
        self.lbl_durum.text = "GÜNCELLENDİ: Personel ve cihaz bilgileri yenilendi."
        self.lbl_durum.color = ISG_SARISI
        self.formu_temizle()
        self.tum_listele_click(None)

    def personel_sil_click(self, instance):
        if not self.secili_personel_id:
            self.lbl_durum.text = "HATA: Önce arama yapıp silinecek personeli seçmelisiniz!"
            self.lbl_durum.color = BUTON_KIRMIZI
            return
            
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("DELETE FROM personeller WHERE id=?", (self.secili_personel_id,))
        conn.commit()
        conn.close()
        
        self.lbl_durum.text = "SİLİNDİ: Personel kaydı sistemden kaldırıldı."
        self.lbl_durum.color = BUTON_KIRMIZI
        self.formu_temizle()
        self.tum_listele_click(None)

    def arama_yap_click(self, instance):
        kriter = self.input_arama.text.strip()
        if not kriter:
            self.lbl_liste.text = "Lütfen aramak için geçerli bir kriter yazın."
            return
            
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT id, firma, tc_no, ad_soyad, seri_no, son_kullanma FROM personeller
        WHERE id = ? OR tc_no LIKE ? OR ad_soyad LIKE ? OR seri_no LIKE ?
        """, (kriter, f"%{kriter}%", f"%{kriter}%", f"%{kriter}%"))
        sonuclar = cursor.fetchall()
        conn.close()
        
        if not sonuclar:
            self.lbl_liste.text = f"'{kriter}' aramasına uygun kayıt bulunamadı."
            self.secili_personel_id = None
            return
            
        if len(sonuclar) == 1:
            p = sonuclar[0]
            self.secili_personel_id = p[0]
            self.input_firma.text = p[1] if p[1] else ""
            self.input_tc.text = p[2] if p[2] else ""
            self.input_ad.text = p[3] if p[3] else ""
            self.input_seri.text = p[4] if p[4] else ""
            self.input_skt.text = p[5] if p[5] else ""
            self.lbl_durum.text = f"DÜZENLEME MODU: ID {p[0]} ({p[3]}) seçildi."
            self.lbl_durum.color = ISG_SARISI
        else:
            self.secili_personel_id = None
            self.lbl_durum.text = "Birden fazla kayıt bulundu! Lütfen net bir ID veya TC yazarak aratın."
            self.lbl_durum.color = BUTON_MAVI
            
        rapor = f"--- ARAMA SONUÇLARI ({len(sonuclar)} Kayıt) ---\n\n"
        for p in sonuclar:
            rapor += f"🔑 ID: {p[0]} | 👤 {p[3]} | 🏢 {p[1]}\n  🆔 TC: {p[2]} | 📦 Seri No: {p[4]} | 📅 SKT: {p[5]}\n\n"
        
        self.lbl_liste.text = rapor

    def tum_listele_click(self, instance):
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("SELECT id, firma, tc_no, ad_soyad, seri_no, son_kullanma FROM personeller")
        personeller = cursor.fetchall()
        conn.close()
        
        if not personeller:
            self.lbl_liste.text = "Sistemde henüz kayıtlı personel bulunmuyor."
            return
            
        rapor = f"--- TÜM PERSONEL LİSTESİ ({len(personeller)} Kişi) ---\n\n"
        for p in personeller:
            rapor += f"🔑 ID: {p[0]} | 👤 {p[3]} | 🏢 {p[1]}\n  🆔 TC: {p[2]} | 📦 Seri No: {p[4]} | 📅 SKT: {p[5]}\n\n"
            
        self.lbl_liste.text = rapor

    def kritik_listele_click(self, instance):
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("SELECT id, firma, tc_no, ad_soyad, seri_no, son_kullanma FROM personeller")
        personeller = cursor.fetchall()
        conn.close()
        
        bugun = datetime.now()
        rapor = ""
        sayac = 0
        
        for p in personeller:
            id_no, firma, tc, ad, seri, skt_metin = p[0], p[1], p[2], p[3], p[4], p[5]
            try:
                skt_tarih = datetime.strptime(skt_metin, "%d.%m.%Y")
                kalan_gun = (skt_tarih - bugun).days
                
                if kalan_gun <= 30:
                    sayac += 1
                    if kalan_gun < 0:
                        durum = f"❌ SÜRESİ GEÇMİŞ! ({abs(kalan_gun)} gün önce)"
                    else:
                        durum = f"⏳ Son {kalan_gun} gün!"
                    
                    rapor += f"🔑 ID: {id_no} | 👤 {ad} - 🏢 {firma}\n  📦 Seri No: {seri} | 📅 SKT: {skt_metin}\n  🚨 DURUM: {durum}\n\n"
            except ValueError:
                rapor += f"❌ Hatalı Tarih Formatı: ID {id_no} - {ad} ({skt_metin})\n\n"
                
        if not rapor:
            self.lbl_liste.text = "Harika! Son 30 günde süresi dolacak maske/cihaz bulunamadı."
        else:
            self.lbl_liste.text = f"--- 🚨 KRİTİK DURUMDAKİLER ({sayac} Cihaz) ---\n\n" + rapor

    def excel_cikti_al_click(self, instance):
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("SELECT id, firma, tc_no, ad_soyad, seri_no, son_kullanma FROM personeller")
        personeller = cursor.fetchall()
        conn.close()
        
        if not personeller:
            self.lbl_durum.text = "HATA: Aktarılacak kayıt yok!"
            self.lbl_durum.color = BUTON_KIRMIZI
            return
            
        wb = Workbook()
        ws = wb.active
        ws.title = "Kacis Seti Listesi"
        
        ws.append(["Sıra No (ID)", "Firma Adı", "TC Kimlik No", "Personel Adı Soyadı", "Kaçış Seti Seri No", "Son Kullanma Tarihi"])
        for p in personeller:
            ws.append(list(p))
            
        try:
            if platform == 'android':
                from android.storage import primary_external_storage_path
                download_dir = os.path.join(primary_external_storage_path(), 'Download')
                if not os.path.exists(download_dir):
                    os.makedirs(download_dir)
                kayit_yolu = os.path.join(download_dir, 'Kacis_Seti_Raporu.xlsx')
            else:
                kayit_yolu = 'Kacis_Seti_Raporu.xlsx'
                
            wb.save(kayit_yolu)
            self.lbl_liste.text = f"--- 📊 EXCEL BAŞARIYLA OLUŞTURULDU ---\n\nDosya kaydedildi.\nYol: {kayit_yolu}"
            self.lbl_durum.text = "Excel başarıyla kaydedildi!"
            self.lbl_durum.color = ISG_SARISI
        except Exception as e:
            self.lbl_liste.text = f"Excel oluşturulamadı:\n{str(e)}"
            self.lbl_durum.text = "Hata!"
            self.lbl_durum.color = BUTON_KIRMIZI


# --- SCREEN MANAGER (EKRAN YÖNETİCİSİ) ---
class KacisSetiApp(App):
    def build(self):
        veritabanini_hazirla()
        self.title = "Kaçış Seti Takip Sistemi"
        
        # Ekranları yöneten mekanizma
        sm = ScreenManager()
        
        # Ekranları tanımlayıp ekliyoruz
        sm.add_widget(GirisEkrani(name='giris_ekrani'))
        sm.add_widget(AnaTakipEkrani(name='ana_ekran'))
        
        return sm

if __name__ == "__main__":
    try:
        from kivy.core.window import Window
        Window.clearcolor = ARKA_PLAN
        KacisSetiApp().run()
    except Exception as e:
        import traceback
        from kivy.uix.popup import Popup
        from kivy.uix.textinput import TextInput
        from kivy.base import runTouchApp
        
        hata_mesaji = traceback.format_exc()
        kutu = TextInput(text=hata_mesaji, readonly=True, font_size='14sp', background_color=(0.1, 0.1, 0.1, 1), foreground_color=(1, 1, 1, 1))
        pencere = Popup(title='⚠️ UYGULAMA ÇÖKTÜ (EKRAN GÖRÜNTÜSÜ ALIN)', content=kutu, size_hint=(0.9, 0.9))
        pencere.open()
        runTouchApp(pencere)
