import os
from datetime import datetime
import json
import threading 
import requests 
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.utils import get_color_from_hex, platform
from kivy.graphics import Color, RoundedRectangle
from kivy.core.window import Window
from kivy.clock import Clock 
from openpyxl import Workbook

# 🚨 GÜVENLİ İNTERNET BAĞLANTISI (SSL) YAMASI:
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()

# 🚨 FIREBASE URL ADRESİN:
FIREBASE_URL = "https://kacis-seti-takip-default-rtdb.europe-west1.firebasedatabase.app/"

# Renk Paleti
ARKA_PLAN = get_color_from_hex("#1E2022")       
ISG_SARISI = get_color_from_hex("#F39C12")      
FORM_RENGI = get_color_from_hex("#2C3E50")      
YAZI_RENGI = get_color_from_hex("#ECF0F1")      
BUTON_YESIL = get_color_from_hex("#27AE60")     
BUTON_MAVI = get_color_from_hex("#2980B9")      
BUTON_KIRMIZI = get_color_from_hex("#C0392B")    
BUTON_PASIF = get_color_from_hex("#7F8C8D") # Yetkisiz butonlar için soluk renk

# Global değişkenler
AKTIF_KULLANICI = "Bilinmeyen"
KULLANICI_ROLÜ = "personel" # yonetici veya personel
KULLANICI_FIRMASI = ""      # Personelin sadece işlem yapabileceği kilitli firma

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
        self.lbl_hata = Label(text="Lütfen giriş yapın.\n(Personeller sadece atandığı firmayı yönetebilir)", color=YAZI_RENGI, font_size='13sp', size_hint_y=0.2, halign="center")
        
        form_alani.add_widget(self.input_kullanici)
        form_alani.add_widget(self.input_sifre)
        form_alani.add_widget(self.lbl_hata)
        duzen.add_widget(form_alani)
        
        btn_giris = Button(text="SİSTEME GİRİŞ YAP", background_normal='', background_color=ISG_SARISI, color=(0,0,0,1), bold=True, font_size='16sp', size_hint_y=0.1)
        btn_giris.bind(on_press=self.bulut_giris_kontrol_thread)
        duzen.add_widget(btn_giris)
        duzen.add_widget(BoxLayout(size_hint_y=0.2))
        self.add_widget(duzen)

    def bulut_giris_kontrol_thread(self, instance):
        threading.Thread(target=self.bulut_giris_kontrol).start()

    def bulut_giris_kontrol(self):
        global AKTIF_KULLANICI, KULLANICI_ROLÜ, KULLANICI_FIRMASI
        kullanici = self.input_kullanici.text.strip().lower()
        sifre = self.input_sifre.text.strip()
        
        if not kullanici or not sifre:
            Clock.schedule_once(lambda dt: self.HataSetEt("HATA: Alanlar boş bırakılamaz!", BUTON_KIRMIZI))
            return
            
        Clock.schedule_once(lambda dt: self.HataSetEt("Bulut bağlantısı kuruluyor...", ISG_SARISI))
        
        req_url = f"{FIREBASE_URL}kullanicilar/{kullanici}.json"
        
        try:
            response = requests.get(req_url, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result and isinstance(result, dict) and result.get("sifre") == sifre:
                    AKTIF_KULLANICI = kullanici
                    KULLANICI_ROLÜ = result.get("rol", "personel")
                    KULLANICI_FIRMASI = result.get("firma", "") # Kullanıcının yetkili olduğu firma
                    Clock.schedule_once(self.GirisBasariliGecis)
                else:
                    if kullanici == "admin" and sifre == "1234":
                        self.ilk_kullaniciyi_olustur()
                    else:
                        Clock.schedule_once(lambda dt: self.HataSetEt("HATA: Kullanıcı adı veya şifre yanlış!", BUTON_KIRMIZI))
            else:
                Clock.schedule_once(lambda dt: self.HataSetEt("Bulut hatası! Sunucu yanıt vermedi.", BUTON_KIRMIZI))
        except Exception as e:
            Clock.schedule_once(lambda dt: self.HataSetEt(f"Bağlantı Hatası: {str(e)[:30]}", BUTON_KIRMIZI))

    def HataSetEt(self, metin, renk):
        self.lbl_hata.text = metin
        self.lbl_hata.color = renk

    def GirisBasariliGecis(self, dt):
        self.lbl_hata.text = "Giriş Başarılı!"
        self.lbl_hata.color = BUTON_YESIL
        
        ana_sayfa = self.manager.get_screen('ana_ekran')
        ana_sayfa.görünüm_ayarla() 
        
        self.manager.current = 'ana_ekran'
        if hasattr(ana_sayfa, 'tum_listele_click_thread'):
            ana_sayfa.tum_listele_click_thread(None)
                    
    def ilk_kullaniciyi_olustur(self):
        try:
            admin_data = {"sifre": "1234", "rol": "yonetici", "firma": "Tüm Firmalar"}
            requests.put(f"{FIREBASE_URL}kullanicilar/admin.json", json=admin_data, timeout=10)
            Clock.schedule_once(lambda dt: self.HataSetEt("İlk kurulum yapıldı! Tekrar Giriş Yapın.", BUTON_YESIL))
        except:
            Clock.schedule_once(lambda dt: self.HataSetEt("İlk kurulum başarısız oldu!", BUTON_KIRMIZI))

# --- 2. EKRAN: BULUT TABANLI ANA TAKİP EKRANI (SINIRLANDIRILMIŞ YETKİLER) ---
class AnaTakipEkrani(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.secili_kayit_id = None
        self.tum_bulut_verisi = {} 
        
        self.ana_duzen = BoxLayout(orientation='vertical', padding=10, spacing=8)
        
        # Üst Bilgi Başlığı
        self.lbl_durum = Label(text="BULUT PANELİ | CANLI BAĞLANTI", size_hint_y=0.04, color=ISG_SARISI, bold=True, font_size='13sp')
        self.ana_duzen.add_widget(self.lbl_durum)
        
        # 1. FORM ALANI: Kaçış Seti Giriş Kartı
        form_kartı = RenkliKutu(bg_color=FORM_RENGI, orientation='vertical', padding=8, spacing=5, size_hint_y=0.28)
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
        self.ana_duzen.add_widget(form_kartı)
        
        # 2. İŞLEM BUTONLARI (Dinamik olarak kilitlenebilir hale getirildi)
        islem_butonlari = BoxLayout(orientation='horizontal', size_hint_y=0.05, spacing=6)
        self.btn_ekle = Button(text="BULUTA KAYDET", background_normal='', background_color=BUTON_YESIL, font_size='12sp', bold=True)
        self.btn_ekle.bind(on_press=lambda inst: threading.Thread(target=self.personel_ekle_click).start())
        self.btn_guncelle = Button(text="GÜNCELLE", background_normal='', background_color=BUTON_MAVI, font_size='12sp', bold=True)
        self.btn_guncelle.bind(on_press=lambda inst: threading.Thread(target=self.personel_guncelle_click).start())
        self.btn_sil = Button(text="SİL", background_normal='', background_color=BUTON_KIRMIZI, font_size='12sp', bold=True)
        self.btn_sil.bind(on_press=lambda inst: threading.Thread(target=self.personel_sil_click).start())
        
        islem_butonlari.add_widget(self.btn_ekle)
        islem_butonlari.add_widget(self.btn_guncelle)
        islem_butonlari.add_widget(self.btn_sil)
        self.ana_duzen.add_widget(islem_butonlari)
        
        # 3. ARAMA ÇUBUĞU
        arama_duzeni = BoxLayout(orientation='horizontal', spacing=6, size_hint_y=0.05)
        self.input_arama = TextInput(hint_text="Seri No veya İsim yazıp ARA...", multiline=False, font_size='14sp', size_hint_x=0.75)
        btn_ara = Button(text="ARA", background_normal='', background_color=ISG_SARISI, font_size='12sp', bold=True, size_hint_x=0.25, color=(0,0,0,1))
        btn_ara.bind(on_press=self.arama_yap_click)
        arama_duzeni.add_widget(self.input_arama)
        arama_duzeni.add_widget(btn_ara)
        self.ana_duzen.add_widget(arama_duzeni)
        
        # 4. LİSTELEME BUTONLARI
        liste_buton_duzeni = BoxLayout(orientation='horizontal', size_hint_y=0.05, spacing=6)
        btn_tum_liste = Button(text="Yenile/Listele", background_normal='', background_color=get_color_from_hex("#7F8C8D"), font_size='11sp', bold=True)
        btn_tum_liste.bind(on_press=self.tum_listele_click_thread)
        btn_kritik_liste = Button(text="⚡ Kritik Olanlar", background_normal='', background_color=get_color_from_hex("#D35400"), font_size='11sp', bold=True)
        btn_kritik_liste.bind(on_press=self.kritik_listele_click)
        btn_excel = Button(text="📊 Excel Çıktısı", background_normal='', background_color=get_color_from_hex("#27AE60"), font_size='11sp', bold=True)
        btn_excel.bind(on_press=self.excel_cikti_al_click)
        
        liste_buton_duzeni.add_widget(btn_tum_liste)
        liste_buton_duzeni.add_widget(btn_kritik_liste)
        liste_buton_duzeni.add_widget(btn_excel)
        self.ana_duzen.add_widget(liste_buton_duzeni)
        
        # 5. VERİ LİSTELEME ALANI
        liste_kartı = RenkliKutu(bg_color=get_color_from_hex("#2C3E50"), orientation='vertical', padding=8, size_hint_y=0.35)
        scroll = ScrollView(bar_width=8)
        self.lbl_liste = Label(text="Veriler yükleniyor...", size_hint_y=None, halign="left", valign="top", font_size='13sp', color=YAZI_RENGI)
        self.lbl_liste.bind(texture_size=self.lbl_liste.setter('size'))
        scroll.add_widget(self.lbl_liste)
        liste_kartı.add_widget(scroll)
        self.ana_duzen.add_widget(liste_kartı)

        # 👑 6. ADMİN ÖZEL PANELİ (Firma kısıtlaması parametresi eklendi)
        self.admin_paneli = RenkliKutu(bg_color=get_color_from_hex("#111D2A"), orientation='vertical', padding=6, spacing=4, size_hint_y=0.23)
        self.admin_paneli.add_widget(Label(text="⚙️ YÖNETİCİ KULLANICI YÖNETİM PANELİ", font_size='11sp', bold=True, color=ISG_SARISI))
        
        admin_input_duzen = BoxLayout(orientation='horizontal', spacing=5)
        self.input_yeni_kullanici = TextInput(hint_text="Yeni Kullanıcı Adı", multiline=False, font_size='12sp')
        self.input_yeni_sifre = TextInput(hint_text="Şifre", multiline=False, font_size='12sp')
        self.input_yeni_firma = TextInput(hint_text="Atanacak Firma Adı", multiline=False, font_size='12sp') # 🆕 Firma Atama Alanı
        admin_input_duzen.add_widget(self.input_yeni_kullanici)
        admin_input_duzen.add_widget(self.input_yeni_sifre)
        admin_input_duzen.add_widget(self.input_yeni_firma)
        self.admin_paneli.add_widget(admin_input_duzen)
        
        admin_btn_duzen = BoxLayout(orientation='horizontal', spacing=5)
        btn_kul_ekle = Button(text="KULLANICI EKLE (FİRMALI)", background_normal='', background_color=BUTON_YESIL, font_size='11sp', bold=True)
        btn_kul_ekle.bind(on_press=lambda inst: threading.Thread(target=self.kullanici_ekle_click).start())
        btn_kul_sil = Button(text="KULLANICI SİL", background_normal='', background_color=BUTON_KIRMIZI, font_size='11sp', bold=True)
        btn_kul_sil.bind(on_press=lambda inst: threading.Thread(target=self.kullanici_sil_click).start())
        
        admin_btn_duzen.add_widget(btn_kul_ekle)
        admin_btn_duzen.add_widget(btn_kul_sil)
        self.admin_paneli.add_widget(admin_btn_duzen)
        
        self.add_widget(self.ana_duzen)

    def görünüm_ayarla(self):
        global KULLANICI_ROLÜ, AKTIF_KULLANICI, KULLANICI_FIRMASI
        if self.admin_paneli in self.ana_duzen.children:
            self.ana_duzen.remove_widget(self.admin_paneli)
            
        if KULLANICI_ROLÜ == "yonetici":
            self.lbl_durum.text = f"YÖNETİCİ PANELİ | AKTİF: {AKTIF_KULLANICI.upper()}"
            self.lbl_durum.color = ISG_SARISI
            self.ana_duzen.children[0].size_hint_y = 0.20 
            self.ana_duzen.add_widget(self.admin_paneli)
            
            # Yönetici her butonu kullanabilir ve firmayı değiştirebilir
            self.input_firma.readonly = False
            self.btn_guncelle.disabled = False
            self.btn_guncelle.background_color = BUTON_MAVI
            self.btn_sil.disabled = False
            self.btn_sil.background_color = BUTON_KIRMIZI
        else:
            self.lbl_durum.text = f"FİRMA SINIRLI PERSONEL PANELİ | AKTİF: {AKTIF_KULLANICI.upper()}"
            self.lbl_durum.color = YAZI_RENGI
            self.ana_duzen.children[0].size_hint_y = 0.43 
            
            # 🆕 1. KRİTİK DEĞİŞİKLİK: Firma kilitleniyor, kullanıcı değiştiremez!
            self.input_firma.text = KULLANICI_FIRMASI
            self.input_firma.readonly = True
            
            # 🆕 2. KRİTİK DEĞİŞİKLİK: Güncelleme ve Silme tamamen kapatılıyor!
            self.btn_guncelle.disabled = True
            self.btn_guncelle.background_color = BUTON_PASIF
            self.btn_sil.disabled = True
            self.btn_sil.background_color = BUTON_PASIF

    # --- KULLANICI YÖNETİM FONKSİYONLARI (SADECE ADMİN) ---
    def kullanici_ekle_click(self):
        yeni_k = self.input_yeni_kullanici.text.strip().lower()
        yeni_s = self.input_yeni_sifre.text.strip()
        yeni_f = self.input_yeni_firma.text.strip() # Atanan firma verisi alındı
        
        if not yeni_k or not yeni_s or not yeni_f:
            Clock.schedule_once(lambda dt: self.DurumGuncelle("HATA: Kul. adı, şifre ve firma boş bırakılamaz!", BUTON_KIRMIZI))
            return
            
        kullanici_verisi = {"sifre": yeni_s, "rol": "personel", "firma": yeni_f}
        try:
            res = requests.put(f"{FIREBASE_URL}kullanicilar/{yeni_k}.json", json=kullanici_verisi, timeout=10)
            if res.status_code == 200:
                Clock.schedule_once(lambda dt: self.DurumGuncelle(f"BAŞARILI: '{yeni_k}' ({yeni_f}) eklendi.", BUTON_YESIL))
                Clock.schedule_once(lambda dt: self.admin_form_temizle())
        except:
            Clock.schedule_once(lambda dt: self.DurumGuncelle("Kullanıcı buluta eklenemedi!", BUTON_KIRMIZI))

    def kullanici_sil_click(self):
        sil_k = self.input_yeni_kullanici.text.strip().lower()
        if not sil_k:
            Clock.schedule_once(lambda dt: self.DurumGuncelle("HATA: Silinecek kullanıcı adını yazın!", BUTON_KIRMIZI))
            return
        if sil_k == "admin":
            Clock.schedule_once(lambda dt: self.DurumGuncelle("HATA: Ana admin hesabı silinemez!", BUTON_KIRMIZI))
            return
            
        try:
            res = requests.delete(f"{FIREBASE_URL}kullanicilar/{sil_k}.json", timeout=10)
            if res.status_code == 200:
                Clock.schedule_once(lambda dt: self.DurumGuncelle(f"SİLİNDİ: '{sil_k}' hesabı kapatıldı.", BUTON_YESIL))
                Clock.schedule_once(lambda dt: self.admin_form_temizle())
        except:
            Clock.schedule_once(lambda dt: self.DurumGuncelle("Kullanıcı buluttan silinemedi!", BUTON_KIRMIZI))

    def admin_form_temizle(self):
        self.input_yeni_kullanici.text = ""
        self.input_yeni_sifre.text = ""
        self.input_yeni_firma.text = ""

    # --- ESKİ KAÇIŞ SETİ STANDART FONKSİYONLARI ---
    def DurumGuncelle(self, metin, renk):
        self.lbl_durum.text = metin
        self.lbl_durum.color = renk

    def formu_temizle(self):
        global KULLANICI_ROLÜ, KULLANICI_FIRMASI
        # Personel ise formu temizlerken kendi firması silinmesin, kilitli kalsın
        if KULLANICI_ROLÜ != "yonetici":
            self.input_firma.text = KULLANICI_FIRMASI
        else:
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

    def personel_ekle_click(self):
        global AKTIF_KULLANICI, KULLANICI_ROLÜ
        if not self.zorunlu_alan_kontrolu():
            Clock.schedule_once(lambda dt: self.DurumGuncelle("HATA: Zorunlu alanları doldurun!", BUTON_KIRMIZI))
            return
            
        girilen_isim = self.input_ad.text.strip().lower()
        
        # 🚨 MÜKERRER KAYIT ENGELLEME KONTROLÜ
        # Eğer işlem yapan kişi admin (yonetici) DEĞİLSE isim kontrolü yapar:
        if KULLANICI_ROLÜ != "yonetici" and self.tum_bulut_verisi:
            for k_id, v in self.tum_bulut_verisi.items():
                if v.get('ad_soyad', '').strip().lower() == girilen_isim:
                    Clock.schedule_once(lambda dt: self.DurumGuncelle("🚫 ENGELLENDİ: Bu personel adına zaten bir kayıt var!", BUTON_KIRMIZI))
                    return

        yeni_kayit = {
            "firma": self.input_firma.text.strip(),
            "tc_no": self.input_tc.text.strip(),
            "ad_soyad": self.input_ad.text.strip(),
            "seri_no": self.input_seri.text.strip(),
            "son_kullanma": self.input_skt.text.strip(),
            "ekleyen_kullanici": AKTIF_KULLANICI 
        }
        
        try:
            res = requests.post(f"{FIREBASE_URL}kayitlar.json", json=yeni_kayit, timeout=10)
            if res.status_code == 200:
                Clock.schedule_once(self.islem_basarili)
            else:
                Clock.schedule_once(lambda dt: self.DurumGuncelle("BULUT HATASI: Kayıt yapılamadı.", BUTON_KIRMIZI))
        except:
            Clock.schedule_once(lambda dt: self.DurumGuncelle("BULUT HATASI: İnternet yok.", BUTON_KIRMIZI))

    def personel_guncelle_click(self):
        # Eğer bir açık bulunup buraya basılırsa diye emniyet kilidi:
        global KULLANICI_ROLÜ
        if KULLANICI_ROLÜ != "yonetici":
            return
            
        if not self.secili_kayit_id:
            Clock.schedule_once(lambda dt: self.DurumGuncelle("HATA: Önce ARA kısmından bir kayıt seçin!", BUTON_KIRMIZI))
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
        try:
            res = requests.patch(f"{FIREBASE_URL}kayitlar/{self.secili_kayit_id}.json", json=guncel_kayit, timeout=10)
            if res.status_code == 200:
                Clock.schedule_once(self.islem_basarili)
        except:
            Clock.schedule_once(lambda dt: self.DurumGuncelle("BULUT HATASI!", BUTON_KIRMIZI))

    def personel_sil_click(self):
        # Emniyet kilidi
        global KULLANICI_ROLÜ
        if KULLANICI_ROLÜ != "yonetici":
            return
            
        if not self.secili_kayit_id:
            Clock.schedule_once(lambda dt: self.DurumGuncelle("HATA: Silinecek kaydı seçmediniz!", BUTON_KIRMIZI))
            return
        try:
            res = requests.delete(f"{FIREBASE_URL}kayitlar/{self.secili_kayit_id}.json", timeout=10)
            if res.status_code == 200:
                Clock.schedule_once(self.islem_basarili)
        except:
            Clock.schedule_once(lambda dt: self.DurumGuncelle("BULUT HATASI!", BUTON_KIRMIZI))

    def islem_basarili(self, dt):
        self.lbl_durum.text = "İŞLEM BAŞARILI: Bulut güncellendi."
        self.lbl_durum.color = BUTON_YESIL
        self.formu_temizle()
        self.tum_listele_click_thread(None)

    def tum_listele_click_thread(self, instance):
        self.lbl_liste.text = "Buluttan canlı veriler çekiliyor..."
        threading.Thread(target=self.tum_listele_click).start()

    def tum_listele_click(self):
        try:
            res = requests.get(f"{FIREBASE_URL}kayitlar.json", timeout=10)
            result = res.json()
            Clock.schedule_once(lambda dt: self.listeleme_yap(result))
        except:
            Clock.schedule_once(lambda dt: self.DurumGuncelle("Veri çekme hatası!", BUTON_KIRMIZI))

    def listeleme_yap(self, result):
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
            
            # 🆕 PERSONEL İÇİN GÜNCELLEME KİLİDİ: 
            # Personel aramada bir kayda tıklasa bile form alanları kilitli kalacak/güncelleyemeyecek
            global KULLANICI_ROLÜ
            if KULLANICI_ROLÜ == "yonetici":
                self.secili_kayit_id = k_id
                self.input_firma.text = v.get('firma','')
                self.input_tc.text = v.get('tc_no','')
                self.input_ad.text = v.get('ad_soyad','')
                self.input_seri.text = v.get('seri_no','')
                self.input_skt.text = v.get('son_kullanma','')
                self.lbl_durum.text = f"DÜZENLEME MODU AKTİF"
                self.lbl_durum.color = ISG_SARISI
            else:
                self.lbl_durum.text = f"KAYIT İNCELENİYOR (GÜNCELLEME YETKİNİZ YOK)"
                self.lbl_durum.color = BUTON_PASIF
            
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
        sm.add_widget(AnaTakipEkrani(name='ana_ekran'))
        sm.current = 'giris_ekrani'
        return sm

if __name__ == "__main__":
    Window.clearcolor = ARKA_PLAN
    BulutKacisApp().run()
