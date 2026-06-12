import os
from datetime import datetime
import json
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.utils import get_color_from_hex, platform
from kivy.graphics import Color, RoundedRectangle
from kivy.network.urlrequest import UrlRequest # Firebase iletişimi için
from openpyxl import Workbook

# 🚨 BURAYA 1. ADIMDA KOPYALADIĞIN KENDİ FIREBASE URL'SİNİ YAZ (Sonunda / işareti olsun)
FIREBASE_URL = "https://kacis-seti-takip-default-rtdb.europe-west1.firebasedatabase.app/"

# Renk Paleti
ARKA_PLAN = get_color_from_hex("#1E2022")       
ISG_SARISI = get_color_from_hex("#F39C12")      
FORM_RENGI = get_color_from_hex("#2C3E50")      
YAZI_RENGI = get_color_from_hex("#ECF0F1")      
BUTON_YESIL = get_color_from_hex("#27AE60")     
BUTON_MAVI = get_color_from_hex("#2980B9")      
BUTON_KIRMIZI = get_color_from_hex("#C0392B")    

# Aktif giriş yapan kullanıcıyı akılda tutmak için global değişken
AKTIF_KULLANICI = "Bilinmeyen"

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

# --- 1. EKRAN: BULUT TABANLI GİRİŞ EKRANI ---
class GirisEkrani(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        duzen = BoxLayout(orientation='vertical', padding=40, spacing=15)
        
        duzen.add_widget(Label(
            text="🚨\nKAÇIŞ SETİ TAKİP\nBULUT SİSTEMİ GİRİŞİ", 
            font_size='24sp', bold=True, color=ISG_SARISI, halign="center", size_hint_y=0.3
        ))
        
        form_alani = RenkliKutu(bg_color=FORM_RENGI, orientation='vertical', padding=15, spacing=10, size_hint_y=0.4)
        self.input_kullanici = TextInput(hint_text="Kullanıcı Adı", multiline=False, font_size='16sp', write_tab=False)
        self.input_sifre = TextInput(hint_text="Şifre", password=True, multiline=False, font_size='16sp', write_tab=False)
        self.lbl_hata = Label(text="Lütfen giriş yapın.\n(İlk açılışta buluttan kullanıcı doğrulanır)", color=YAZI_RENGI, font_size='13sp', size_hint_y=0.2, halign="center")
        
        form_alani.add_widget(self.input_kullanici)
        form_alani.add_widget(self.input_sifre)
        form_alani.add_widget(self.lbl_hata)
        duzen.add_widget(form_alani)
        
        btn_giris = Button(text="SİSTEME GİRİŞ YAP", background_normal='', background_color=ISG_SARISI, color=(0,0,0,1), bold=True, font_size='16sp', size_hint_y=0.1)
        btn_giris.bind(on_press=self.bulut_giris_kontrol)
        duzen.add_widget(btn_giris)
        duzen.add_widget(BoxLayout(size_hint_y=0.2))
        self.add_widget(duzen)

    def bulut_giris_kontrol(self, instance):
        global AKTIF_KULLANICI
        kullanici = self.input_kullanici.text.strip().lower()
        sifre = self.input_sifre.text.strip()
        
        if not kullanici or not sifre:
            self.lbl_hata.text = "HATA: Alanlar boş bırakılamaz!"
            self.lbl_hata.color = BUTON_KIRMIZI
            return
            
        self.lbl_hata.text = "Bulut bağlantısı kuruluyor..."
        self.lbl_hata.color = ISG_SARISI
        
        # Firebase'den kullanıcıları çekip kontrol ediyoruz
        req_url = f"{FIREBASE_URL}kullanicilar/{kullanici}.json"
        
        def on_success(req, result):
            global AKTIF_KULLANICI
            if result and result.get("sifre") == sifre:
                AKTIF_KULLANICI = kullanici
                self.lbl_hata.text = "Giriş Başarılı!"
                self.lbl_hata.color = BUTON_YESIL
                self.manager.current = 'ana_ekran'
                # Ana ekrandaki listeyi otomatik yenile
                self.manager.get_screen('ana_ekran').tum_listele_click(None)
            else:
                # Kolaylık olsun diye: Eğer bulutta hiç kullanıcı yoksa ilk girişte admin oluşturur
                if kullanici == "admin" and sifre == "1234":
                    self.ilk_kullaniciyi_olustur()
                else:
                    self.lbl_hata.text = "HATA: Kullanıcı adı veya şifre yanlış!"
                    self.lbl_hata.color = BUTON_KIRMIZI
                    
        def on_failure(req, result):
            self.lbl_hata.text = "Buluta bağlanılamadı! İnternetinizi kontrol edin."
            self.lbl_hata.color = BUTON_KIRMIZI

        UrlRequest(req_url, on_success=on_success, on_failure=on_failure, on_error=on_failure)

    def ilk_kullaniciyi_olustur(self):
        # Eğer Firebase bomboşsa sistem kilitlenmesin diye otomatik admin tanımlama fonksiyonu
        admin_data = json.dumps({"sifre": "1234", "rol": "yonetici"})
        UrlRequest(f"{FIREBASE_URL}kullanicilar/admin.json", req_method='PUT', req_body=admin_data,
                   on_success=lambda r, v: setattr(self.lbl_hata, 'text', "İlk kurulum yapıldı! Tekrar Giriş Yapın."))

# --- 2. EKRAN: BULUT TABANLI ANA TAKİP EKRANI ---
class AnaTakipEkrani(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.secili_kayit_id = None
        self.tum_bulut_verisi = {} # Arama ve listeleme için yerel kopya
        
        ana_duzen = BoxLayout(orientation='vertical', padding=15, spacing=10)
        
        self.lbl_durum = Label(text="BULUT PANELİ | CANLI BAĞLANTI", size_hint_y=0.05, color=ISG_SARISI, bold=True, font_size='14sp')
        ana_duzen.add_widget(self.lbl_durum)
        
        form_kartı = RenkliKutu(bg_color=FORM_RENGI, orientation='vertical', padding=10, spacing=6, size_hint_y=0.32)
        self.input_firma = TextInput(hint_text="Firma Adı (* Zorunlu)", multiline=False, font_size='14sp')
        self.input_tc = TextInput(hint_text="TC Kimlik No", multiline=False, font_size='14sp', input_filter='int')
        self.input_ad = TextInput(hint_text="Personel Adı Soyadı (* Zorunlu)", multiline=False, font_size='14sp')
        self.input_seri = TextInput(hint_text="Cihaz Seri No (* Zorunlu)", multiline=False, font_size='14sp')
        self.input_skt = TextInput(hint_text="Son Kullanma Tarihi (GG.AA.YYYY) (* Zorunlu)", multiline=False, font_size='14sp')
        
        form_kartı.add_widget(self.input_firma)
        form_kartı.add_widget(self.input_tc)
        form_kartı.add_widget(self.input_ad)
        form_kartı.add_widget(self.input_seri)
        form_kartı.add_widget(self.input_skt)
        ana_duzen.add_widget(form_kartı)
        
        islem_butonlari = BoxLayout(orientation='horizontal', size_hint_y=0.06, spacing=8)
        self.btn_ekle = Button(text="BULUTA KAYDET", background_normal='', background_color=BUTON_YESIL, font_size='13sp', bold=True)
        self.btn_ekle.bind(on_press=self.personel_ekle_click)
        self.btn_guncelle = Button(text="GÜNCELLE", background_normal='', background_color=BUTON_MAVI, font_size='13sp', bold=True)
        self.btn_guncelle.bind(on_press=self.personel_guncelle_click)
        self.btn_sil = Button(text="SİL", background_normal='', background_color=BUTON_KIRMIZI, font_size='13sp', bold=True)
        self.btn_sil.bind(on_press=self.personel_sil_click)
        
        islem_butonlari.add_widget(self.btn_ekle)
        islem_butonlari.add_widget(self.btn_guncelle)
        islem_butonlari.add_widget(self.btn_sil)
        ana_duzen.add_widget(islem_butonlari)
        
        arama_duzeni = BoxLayout(orientation='horizontal', spacing=8, size_hint_y=0.06)
        self.input_arama = TextInput(hint_text="Cihaz Seri No veya İsim yazıp ARA'ya basın...", multiline=False, font_size='14sp', size_hint_x=0.75)
        btn_ara = Button(text="ARA", background_normal='', background_color=ISG_SARISI, font_size='13sp', bold=True, size_hint_x=0.25, color=(0,0,0,1))
        btn_ara.bind(on_press=self.arama_yap_click)
        arama_duzeni.add_widget(self.input_arama)
        arama_duzeni.add_widget(btn_ara)
        ana_duzen.add_widget(arama_duzeni)
        
        liste_buton_duzeni = BoxLayout(orientation='horizontal', size_hint_y=0.06, spacing=8)
        btn_tum_liste = Button(text="Yenile / Listele", background_normal='', background_color=get_color_from_hex("#7F8C8D"), font_size='12sp', bold=True)
        btn_tum_liste.bind(on_press=self.tum_listele_click)
        btn_kritik_liste = Button(text="⚡ Kritik Olanlar", background_normal='', background_color=get_color_from_hex("#D35400"), font_size='12sp', bold=True)
        btn_kritik_liste.bind(on_press=self.kritik_listele_click)
        btn_excel = Button(text="📊 Excel Çıktısı", background_normal='', background_color=get_color_from_hex("#27AE60"), font_size='12sp', bold=True)
        btn_excel.bind(on_press=self.excel_cikti_al_click)
        
        liste_buton_duzeni.add_widget(btn_tum_liste)
        liste_buton_duzeni.add_widget(btn_kritik_liste)
        liste_buton_duzeni.add_widget(btn_excel)
        ana_duzen.add_widget(liste_buton_duzeni)
        
        liste_kartı = RenkliKutu(bg_color=get_color_from_hex("#2C3E50"), orientation='vertical', padding=10, size_hint_y=0.45)
        scroll = ScrollView(bar_width=8)
        self.lbl_liste = Label(text="Veriler yükleniyor...", size_hint_y=None, halign="left", valign="top", font_size='13sp', color=YAZI_RENGI)
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
        self.secili_kayit_id = None

    def zorunlu_alan_kontrolu(self):
        if (not self.input_firma.text.strip() or not self.input_ad.text.strip() or 
            not self.input_seri.text.strip() or not self.input_skt.text.strip()):
            return False
        return True

    def personel_ekle_click(self, instance):
        global AKTIF_KULLANICI
        if not self.zorunlu_alan_kontrolu():
            self.lbl_durum.text = "HATA: Zorunlu alanları doldurun!"
            self.lbl_durum.color = BUTON_KIRMIZI
            return
            
        yeni_kayit = {
            "firma": self.input_firma.text.strip(),
            "tc_no": self.input_tc.text.strip(),
            "ad_soyad": self.input_ad.text.strip(),
            "seri_no": self.input_seri.text.strip(),
            "son_kullanma": self.input_skt.text.strip(),
            "ekleyen_kullanici": AKTIF_KULLANICI # Hangi kullanıcı ekledi?
        }
        
        # POST metodu bulutta otomatik benzersiz bir ID oluşturur
        UrlRequest(f"{FIREBASE_URL}kayitlar.json", req_method='POST', req_body=json.dumps(yeni_kayit),
                   on_success=self.islem_basarili, on_failure=self.islem_hatali)

    def personel_guncelle_click(self, instance):
        if not self.secili_kayit_id:
            self.lbl_durum.text = "HATA: Önce ARA kısmından bir kayıt seçin!"
            self.lbl_durum.color = BUTON_KIRMIZI
            return
        if not self.zorunlu_alan_kontrolu():
            return
            
        guncel_kayit = {
            "firma": self.input_firma.text.strip(),
            "tc_no": self.input_tc.text.strip(),
            "ad_soyad": self.input_ad.text.strip(),
            "seri_no": self.input_seri.text.strip(),
            "son_kullanma": self.input_skt.text.strip(),
            "ekleyen_kullanici": AKTIF_KULLANICI
        }
        # PATCH metodu sadece ilgili ID'deki veriyi günceller
        UrlRequest(f"{FIREBASE_URL}kayitlar/{self.secili_kayit_id}.json", req_method='PATCH', req_body=json.dumps(guncel_kayit),
                   on_success=self.islem_basarili, on_failure=self.islem_hatali)

    def personel_sil_click(self, instance):
        if not self.secili_kayit_id:
            self.lbl_durum.text = "HATA: Silinecek kaydı seçmediniz!"
            self.lbl_durum.color = BUTON_KIRMIZI
            return
        # DELETE metodu buluttan kaydı tamamen siler
        UrlRequest(f"{FIREBASE_URL}kayitlar/{self.secili_kayit_id}.json", req_method='DELETE',
                   on_success=self.islem_basarili, on_failure=self.islem_hatali)

    def islem_basarili(self, req, result):
        self.lbl_durum.text = "İŞLEM BAŞARILI: Bulut güncellendi."
        self.lbl_durum.color = BUTON_YESIL
        self.formu_temizle()
        self.tum_listele_click(None)

    def islem_hatali(self, req, result):
        self.lbl_durum.text = "BULUT HATASI: Bağlantı kesilmiş olabilir."
        self.lbl_durum.color = BUTON_KIRMIZI

    def tum_listele_click(self, instance):
        self.lbl_liste.text = "Buluttan canlı veriler çekiliyor..."
        UrlRequest(f"{FIREBASE_URL}kayitlar.json", on_success=self.listeleme_yap, on_failure=self.islem_hatali)

    def listeleme_yap(self, req, result):
        if not result:
            self.lbl_liste.text = "Bulut veritabanında henüz hiç kayıt yok."
            self.tum_bulut_verisi = {}
            return
            
        self.tum_bulut_verisi = result
        rapor = f"--- TÜM PERSONEL BULUT LİSTESİ ({len(result)} Kayıt) ---\n\n"
        for k_id, v in result.items():
            rapor += f"🔑 Bulut ID: {k_id[-6:]} | 👤 {v.get('ad_soyad')} | 🏢 {v.get('firma')}\n  🆔 TC: {v.get('tc_no')} | 📦 Seri No: {v.get('seri_no')} | 📅 SKT: {v.get('son_kullanma')}\n  👷 Sorumlu: {v.get('ekleyen_kullanici','-')}\n\n"
        self.lbl_liste.text = rapor

    def arama_yap_click(self, instance):
        kriter = self.input_arama.text.strip().lower()
        if not kriter or not self.tum_bulut_verisi:
            self.lbl_liste.text = "Arama yapmak için kriter girin veya önce listeyi yenileyin."
            return
            
        bulunanlar = []
        for k_id, v in self.tum_bulut_verisi.items():
            if (kriter in v.get('ad_soyad','').lower() or 
                kriter in v.get('seri_no','').lower() or 
                kriter in v.get('tc_no','')):
                bulunanlar.append((k_id, v))
                
        if not bulunanlar:
            self.lbl_liste.text = f"'{kriter}' kriterine uygun bulutta veri bulunamadı."
            self.secili_kayit_id = None
            return
            
        if len(bulunanlar) == 1:
            k_id, v = bulunanlar[0]
            self.secili_kayit_id = k_id
            self.input_firma.text = v.get('firma','')
            self.input_tc.text = v.get('tc_no','')
            self.input_ad.text = v.get('ad_soyad','')
            self.input_seri.text = v.get('seri_no','')
            self.input_skt.text = v.get('son_kullanma','')
            self.lbl_durum.text = f"DÜZENLEME MODU AKTİF"
            self.lbl_durum.color = ISG_SARISI
            
        rapor = f"--- ARAMA SONUÇLARI ({len(bulunanlar)} Kayıt) ---\n\n"
        for k_id, v in bulunanlar:
            rapor += f"🔑 Bulut ID: {k_id[-6:]} | 👤 {v.get('ad_soyad')} | 🏢 {v.get('firma')}\n  🆔 TC: {v.get('tc_no')} | 📦 Seri No: {v.get('seri_no')} | 📅 SKT: {v.get('son_kullanma')}\n\n"
        self.lbl_liste.text = rapor

    def kritik_listele_click(self, instance):
        if not self.tum_bulut_verisi:
            self.lbl_liste.text = "Lütfen önce listeyi yenileyin."
            return
        bugun = datetime.now()
        rapor = ""
        sayac = 0
        for k_id, v in self.tum_bulut_verisi.items():
            try:
                skt_tarih = datetime.strptime(v.get('son_kullanma'), "%d.%m.%Y")
                kalan_gun = (skt_tarih - bugun).days
                if kalan_gun <= 30:
                    sayac += 1
                    durum = f"❌ SÜRESİ GEÇMİŞ!" if kalan_gun < 0 else f"⏳ Son {kalan_gun} gün!"
                    rapor += f"👤 {v.get('ad_soyad')} | 🏢 {v.get('firma')}\n  📦 Seri No: {v.get('seri_no')} | 📅 SKT: {v.get('son_kullanma')}\n  🚨 DURUM: {durum}\n\n"
            except:
                pass
        self.lbl_liste.text = f"--- 🚨 KRİTİK DURUM ({sayac} Cihaz) ---\n\n" + (rapor if rapor else "Bulutta kritik süreli cihaz yok.")

    def excel_cikti_al_click(self, instance):
        if not self.tum_bulut_verisi:
            return
        wb = Workbook()
        ws = wb.active
        ws.title = "Bulut Kacis Seti Listesi"
        ws.append(["Bulut ID", "Firma Adı", "TC Kimlik No", "Personel Adı Soyadı", "Kaçış Seti Seri No", "Son Kullanma Tarihi", "Ekleyen Sorumlu"])
        
        for k_id, v in self.tum_bulut_verisi.items():
            ws.append([k_id, v.get('firma'), v.get('tc_no'), v.get('ad_soyad'), v.get('seri_no'), v.get('son_kullanma'), v.get('ekleyen_kullanici')])
            
        try:
            if platform == 'android':
                from android.storage import primary_external_storage_path
                kayit_yolu = os.path.join(primary_external_storage_path(), 'Download', 'Bulut_Kacis_Seti_Raporu.xlsx')
            else:
                kayit_yolu = 'Bulut_Kacis_Seti_Raporu.xlsx'
            wb.save(kayit_yolu)
            self.lbl_durum.text = "Excel İndirilenlere Kaydedildi!"
            self.lbl_durum.color = BUTON_YESIL
        except Exception as e:
            self.lbl_durum.text = "Excel Hatası!"

class BulutKacisApp(App):
    def build(self):
        self.title = "Bulut Kaçış Seti Takip Sistemi"
        sm = ScreenManager()
        sm.add_widget(GirisEkrani(name='giris_ekrani'))
        sm.add_widget(AnaTakipEkrani(name='ana_ekran')) # Burayı 'ana_ekran' olarak düzelttik
        sm.current = 'giris_ekrani'
        return sm

if __name__ == "__main__":
    Window.clearcolor = ARKA_PLAN
    BulutKacisApp().run()
