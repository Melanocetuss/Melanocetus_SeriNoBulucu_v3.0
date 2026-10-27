import glob
import os
import queue
import sys
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageTk

from rapor import build_report

# .exe olarak çalışırken: Data ve raporlar .exe'nin yanında, img ise paketin içinde (_MEIPASS)
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
    KAYNAK_DIR = getattr(sys, "_MEIPASS", APP_DIR)
else:
    APP_DIR = KAYNAK_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(APP_DIR, "Data")
IMG_DIR = os.path.join(KAYNAK_DIR, "img")
UYGULAMA_ADI = "Melanocetus Tools Seri Numarası Bulucu v3.0"
TUM_RAPOR_ADI = "ALL_INVENTORY_SeriNoRaporu.xlsx"
ARAMA_RAPOR_ADI = "Search_INVENTORY_SeriNoRaporu.xlsx"

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

SOLUK_YAZI = ("gray40", "gray65")
TEMALAR = {"Açık": "light", "Koyu": "dark", "Sistem": "system"}


def logo_bul():
    """img klasöründeki ilk .png / .jpg / .ico dosyasını döner."""
    for ext in ("png", "jpg", "jpeg", "ico"):
        bulunan = sorted(glob.glob(os.path.join(IMG_DIR, f"*.{ext}")))
        if bulunan:
            return bulunan[0]
    return None


def sayi(n):
    return f"{n:,}".replace(",", ".")


class SeriNoUygulamasi(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(UYGULAMA_ADI)
        self.geometry("1120x820")
        self.minsize(980, 740)
        self.olaylar = queue.Queue()
        self.logo_yolu = logo_bul()
        mevcut = [y for y in (os.path.join(APP_DIR, ad) for ad in (TUM_RAPOR_ADI, ARAMA_RAPOR_ADI))
                  if os.path.exists(y)]
        self.son_rapor = max(mevcut, key=os.path.getmtime) if mevcut else None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._kenar_cubugu()
        self._ana_panel()
        self._pencere_ikonu()
        self.after(100, self._olaylari_isle)

    # --- Arayüz (GUI) Kurulumu ---
    def _kenar_cubugu(self):
        bar = ctk.CTkFrame(self, width=250, corner_radius=0)
        bar.grid(row=0, column=0, sticky="nsw")
        bar.grid_rowconfigure(3, weight=1)
        bar.grid_columnconfigure(0, weight=1)

        if self.logo_yolu:
            img = Image.open(self.logo_yolu)
            img.thumbnail((190, 190))
            self.logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            ctk.CTkLabel(bar, image=self.logo_img, text="").grid(row=0, column=0, padx=30, pady=(32, 14))

        ctk.CTkLabel(bar, text="Melanocetus Tools", font=ctk.CTkFont(size=21, weight="bold")).grid(
            row=1, column=0, padx=24)
        ctk.CTkLabel(bar, text="v3.0  ·  Seri Numarası Bulucu", text_color=SOLUK_YAZI).grid(
            row=2, column=0, padx=24, pady=(2, 0))

        ctk.CTkLabel(bar, text="Görünüm", text_color=SOLUK_YAZI, anchor="w").grid(
            row=4, column=0, padx=24, pady=(0, 6), sticky="ew")
        tema = ctk.CTkSegmentedButton(bar, values=list(TEMALAR),
                                      command=lambda secim: ctk.set_appearance_mode(TEMALAR[secim]))
        tema.set("Sistem")
        tema.grid(row=5, column=0, padx=24, pady=(0, 24), sticky="ew")

    def _ana_panel(self):
        ana = ctk.CTkFrame(self, fg_color="transparent")
        ana.grid(row=0, column=1, sticky="nsew", padx=32, pady=28)
        ana.grid_columnconfigure(0, weight=1)
        ana.grid_rowconfigure(3, weight=1)
        kalin = ctk.CTkFont(size=14, weight="bold")

        ctk.CTkLabel(ana, text=UYGULAMA_ADI, font=ctk.CTkFont(size=25, weight="bold")).grid(
            row=0, column=0, sticky="w")
        ctk.CTkLabel(ana, text="Girilen serileri arayın ya da tüm envanteri dışa aktarın. RET seri numaraları "
                               "anten bazında tekilleştirilir ve 4x / 6x / 8x / KA olarak sınıflandırılır.",
                     text_color=SOLUK_YAZI, wraplength=700, justify="left").grid(
            row=1, column=0, sticky="w", pady=(4, 18))

        # Klasör seçimi kartı: veri (girdi) ve çıktı klasörleri
        kart = ctk.CTkFrame(ana, corner_radius=12)
        kart.grid(row=2, column=0, sticky="ew")
        kart.grid_columnconfigure(1, weight=1)
        self.klasor = ctk.StringVar(value=DATA_DIR)
        self.cikti_klasoru = ctk.StringVar(value=APP_DIR)
        self.klasor_widgetlari = []
        satirlar = (("Veri klasörü", self.klasor, "Envanter Dosyalarının Bulunduğu Klasörü Seçin"),
                    ("Çıktı klasörü", self.cikti_klasoru, "Raporların Kaydedileceği Klasörü Seçin"))
        for i, (etiket, degisken, baslik) in enumerate(satirlar):
            ust, alt_bosluk = (16 if i == 0 else 0), (10 if i == 0 else 16)
            ctk.CTkLabel(kart, text=etiket, font=kalin, anchor="w", width=110).grid(
                row=i, column=0, sticky="w", padx=(20, 14), pady=(ust, alt_bosluk))
            entry = ctk.CTkEntry(kart, textvariable=degisken, height=38)
            entry.grid(row=i, column=1, sticky="ew", padx=(0, 10), pady=(ust, alt_bosluk))
            btn = ctk.CTkButton(kart, text="Gözat…", width=110, height=38, corner_radius=8,
                                command=lambda d=degisken, b=baslik: self._klasor_sec(d, b))
            btn.grid(row=i, column=2, padx=(0, 20), pady=(ust, alt_bosluk))
            self.klasor_widgetlari += [entry, btn]

        # Seri girişi (sol) ve işlem günlüğü (sağ)
        icerik = ctk.CTkFrame(ana, fg_color="transparent")
        icerik.grid(row=3, column=0, sticky="nsew", pady=(18, 0))
        icerik.grid_columnconfigure(0, weight=2, uniform="icerik")
        icerik.grid_columnconfigure(1, weight=3, uniform="icerik")
        icerik.grid_rowconfigure(1, weight=1)

        seri_baslik = ctk.CTkFrame(icerik, fg_color="transparent")
        seri_baslik.grid(row=0, column=0, sticky="ew", padx=(0, 16), pady=(0, 6))
        seri_baslik.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(seri_baslik, text="Aranacak seriler", font=kalin).grid(row=0, column=0, sticky="w")
        self.lbl_seri_sayisi = ctk.CTkLabel(seri_baslik, text="0 seri", text_color=SOLUK_YAZI)
        self.lbl_seri_sayisi.grid(row=0, column=1, sticky="w", padx=10)
        ctk.CTkButton(seri_baslik, text="Temizle", width=80, height=28, corner_radius=8,
                      fg_color="transparent", border_width=1, text_color=("gray10", "gray90"),
                      command=self._serileri_temizle).grid(row=0, column=2, sticky="e")
        self.text_seri = ctk.CTkTextbox(icerik, corner_radius=10, font=ctk.CTkFont(family="Consolas", size=13))
        self.text_seri.grid(row=1, column=0, sticky="nsew", padx=(0, 16))
        self.text_seri.bind("<KeyRelease>", lambda _: self._seri_sayisini_guncelle())
        self.text_seri.bind("<<Paste>>", lambda _: self.after(10, self._seri_sayisini_guncelle))

        ctk.CTkLabel(icerik, text="İşlem günlüğü", font=kalin).grid(row=0, column=1, sticky="w", pady=(0, 6))
        self.log = ctk.CTkTextbox(icerik, corner_radius=10, font=ctk.CTkFont(family="Consolas", size=13),
                                  state="disabled", wrap="word")
        self.log.grid(row=1, column=1, sticky="nsew")

        # İşlem butonları ve ilerleme çubuğu
        islem = ctk.CTkFrame(ana, fg_color="transparent")
        islem.grid(row=4, column=0, sticky="ew", pady=(18, 0))
        islem.grid_columnconfigure(2, weight=1)
        self.btn_ara = ctk.CTkButton(islem, text="🔍  Aranan Serileri Raporla", height=46, corner_radius=10,
                                     font=kalin, command=lambda: self._baslat(arama=True))
        self.btn_ara.grid(row=0, column=0, padx=(0, 12))
        self.btn_tum = ctk.CTkButton(islem, text="📦  Tüm Envanteri Raporla", height=46, corner_radius=10,
                                     font=kalin, fg_color=("#2E7D4F", "#2E7D4F"),
                                     hover_color=("#25663F", "#25663F"),
                                     command=lambda: self._baslat(arama=False))
        self.btn_tum.grid(row=0, column=1, padx=(0, 20))
        self.progress = ctk.CTkProgressBar(islem, height=12, corner_radius=6)
        self.progress.set(0)
        self.progress.grid(row=0, column=2, sticky="ew")
        self.lbl_yuzde = ctk.CTkLabel(islem, text="%0", width=48, anchor="e", text_color=SOLUK_YAZI)
        self.lbl_yuzde.grid(row=0, column=3, padx=(10, 0))

        # Alt satır: durum ve raporu aç
        alt = ctk.CTkFrame(ana, fg_color="transparent")
        alt.grid(row=5, column=0, sticky="ew", pady=(14, 0))
        alt.grid_columnconfigure(0, weight=1)
        self.lbl_durum = ctk.CTkLabel(alt, text="Hazır", text_color=SOLUK_YAZI, anchor="w")
        self.lbl_durum.grid(row=0, column=0, sticky="ew")
        self.btn_ac = ctk.CTkButton(alt, text="📊  Raporu Aç", width=150, height=38, corner_radius=8,
                                    fg_color="transparent", border_width=2,
                                    text_color=("gray10", "gray90"), command=self._raporu_ac)
        self.btn_ac.grid(row=0, column=1)
        if not self.son_rapor:
            self.btn_ac.configure(state="disabled")

    def _pencere_ikonu(self):
        if not self.logo_yolu:
            return
        try:
            if self.logo_yolu.lower().endswith(".ico"):
                # customtkinter kendi ikonunu ~200 ms sonra atadığı için biraz geciktiriyoruz
                self.after(250, lambda: self.iconbitmap(self.logo_yolu))
            else:
                self.ikon = ImageTk.PhotoImage(Image.open(self.logo_yolu).resize((64, 64)))
                self.after(250, lambda: self.iconphoto(False, self.ikon))
        except Exception:
            pass

    # --- İşlemler ---
    def _log_yaz(self, mesaj):
        self.log.configure(state="normal")
        self.log.insert("end", mesaj + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _girilen_seriler(self):
        return [s.strip() for s in self.text_seri.get("1.0", "end").split("\n") if s.strip()]

    def _seri_sayisini_guncelle(self):
        self.lbl_seri_sayisi.configure(text=f"{sayi(len(self._girilen_seriler()))} seri")

    def _serileri_temizle(self):
        self.text_seri.delete("1.0", "end")
        self._seri_sayisini_guncelle()

    def _klasor_sec(self, degisken, baslik):
        mevcut = degisken.get().strip()
        klasor = filedialog.askdirectory(title=baslik, initialdir=mevcut if os.path.isdir(mevcut) else APP_DIR)
        if klasor:
            degisken.set(os.path.normpath(klasor))

    def _calisiyor(self, durum):
        hal = "disabled" if durum else "normal"
        for widget in (self.btn_ara, self.btn_tum, *self.klasor_widgetlari):
            widget.configure(state=hal)
        self.btn_ac.configure(state="disabled" if durum or not self.son_rapor else "normal")

    def _baslat(self, arama):
        klasor = self.klasor.get().strip()
        if not os.path.isdir(klasor):
            messagebox.showwarning("Uyarı", "Lütfen geçerli bir veri klasörü seçin.")
            return
        seriler = None
        if arama:
            seriler = self._girilen_seriler()
            if not seriler:
                messagebox.showwarning("Uyarı", "Lütfen en az bir seri numarası girin (her satıra bir tane).")
                return
        cikti_klasoru = self.cikti_klasoru.get().strip()
        try:
            os.makedirs(cikti_klasoru, exist_ok=True)
        except (OSError, ValueError):
            messagebox.showwarning("Uyarı", "Lütfen geçerli bir çıktı klasörü seçin.")
            return
        cikti = os.path.join(cikti_klasoru, ARAMA_RAPOR_ADI if arama else TUM_RAPOR_ADI)

        self._calisiyor(True)
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.progress.set(0)
        self.lbl_yuzde.configure(text="%0")
        self.lbl_durum.configure(text="İşleniyor…")
        if arama:
            self._log_yaz(f"🔍 {sayi(len(seriler))} seri için arama başlatıldı")
        else:
            self._log_yaz("📦 Tüm envanter raporlanıyor")
        self._log_yaz(f"📁 {klasor}")
        threading.Thread(target=self._calistir, args=(klasor, cikti, seriler), daemon=True).start()

    def _calistir(self, klasor, cikti, seriler):
        # Arka plan iş parçacığı: arayüze yalnızca kuyruk üzerinden haber verir
        try:
            ozet = build_report(klasor, cikti,
                                lambda oran, mesaj: self.olaylar.put(("ilerleme", oran, mesaj)), seriler)
            self.olaylar.put(("bitti", ozet, cikti))
        except Exception as e:
            self.olaylar.put(("hata", str(e)))

    def _olaylari_isle(self):
        try:
            while True:
                olay = self.olaylar.get_nowait()
                if olay[0] == "ilerleme":
                    _, oran, mesaj = olay
                    if oran is not None:
                        self.progress.set(oran)
                        self.lbl_yuzde.configure(text=f"%{int(oran * 100)}")
                    if mesaj:
                        self._log_yaz(mesaj)
                elif olay[0] == "bitti":
                    self._bitti(olay[1], olay[2])
                else:
                    self._calisiyor(False)
                    self.lbl_durum.configure(text="Hata oluştu")
                    self._log_yaz(f"❌ {olay[1]}")
                    messagebox.showerror("Hata", olay[1])
        except queue.Empty:
            pass
        self.after(100, self._olaylari_isle)

    def _bitti(self, ozet, cikti):
        self.son_rapor = cikti
        self._calisiyor(False)
        ad = os.path.basename(cikti)
        tipler = ", ".join(f"{tip}: {sayi(n)}" for tip, n in sorted(ozet["tipler"].items()))
        self._log_yaz("")
        self._log_yaz(f"✅ Rapor hazır: {sayi(ozet['satir'])} satır, {sayi(ozet['ret'])} RET anten"
                      + (f" ({tipler})" if tipler else ""))
        if ozet["aranan"] is not None:
            self._log_yaz(f"🔎 Aranan: {sayi(ozet['aranan'])} · bulunamayan: {sayi(ozet['bulunamayan'])}"
                          + (" (\"Bulunamayan Seriler\" sayfasında)" if ozet["bulunamayan"] else ""))
        self._log_yaz(f"⏱ {ozet['sure']:.1f} sn  →  {cikti}")
        self.lbl_durum.configure(text=f"Son rapor: {ad} · {sayi(ozet['satir'])} satır")

        mesaj = f"{ad} oluşturuldu ({sayi(ozet['satir'])} satır)."
        if ozet["bulunamayan"]:
            mesaj += f"\n{sayi(ozet['bulunamayan'])} seri hiçbir dosyada bulunamadı."
        if messagebox.askyesno("Rapor Hazır", mesaj + "\n\nRaporu şimdi açmak ister misiniz?"):
            self._raporu_ac()

    def _raporu_ac(self):
        if self.son_rapor and os.path.exists(self.son_rapor):
            os.startfile(self.son_rapor)


if __name__ == "__main__":
    SeriNoUygulamasi().mainloop()
