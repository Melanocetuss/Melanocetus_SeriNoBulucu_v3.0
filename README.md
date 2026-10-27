<p align="center">
  <img src="img/MelanocetusV2.jpg" alt="Melanocetus Tools logosu" width="200">
</p>

<h1 align="center">Melanocetus Tools - Seri Numarası Bulucu v3.0</h1>

<p align="center">
  Telekom envanter dışa aktarımlarından seri numarası raporu üreten, RET antenleri tekilleştiren masaüstü uygulaması.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white" alt="Windows">
  <img src="https://img.shields.io/badge/Lisans-MIT-green" alt="MIT Lisansı">
</p>

---

## 👤 Geliştirici

**Cesur Alphan Ellik - Melanocetus**

---

## ✨ Özellikler

- **RET tekilleştirme:** Çok bantlı bir antenin her iç dizisi (R1, R2, Y1–Y4, B1, B2) ayrı bir RET seri numarası raporlar. Program aynı sahadaki aynı antene ait bu alt birimleri birleştirir ve **her fiziksel anten için tek satır** yazar.
- **Anten tipi algılama (4x / 6x / 8x / KA):** Antende bulunan farklı bant sayısına göre otomatik sınıflandırma:

  | Anten Tipi | Kural |
  |---|---|
  | `4x` | En fazla 4 farklı bant |
  | `6x` | 5–6 farklı bant |
  | `8x` | 7 veya daha fazla farklı bant |
  | `KA` | Seri `-XX` ile bitiyor veya üretici KA |

- **Desen tanıma (CommScope, KA ve Huawei):**

  | Desen | Örnek alt birim serisi | Raporda yazılan Seri No |
  |---|---|---|
  | A | `0R2CB194000286908` | `CB194000286908` |
  | B | `03CB2631000DC4-R2` | `CB2631000DC4` |
  | C | `R2-03CB2631000DC4` | `CB2631000DC4` |
  | D (KA) | `E4K0655417-XX` | `E4K0655417` |
  | E (Huawei) | `N3467LA3297190Rr2` | Antenna Serial Number (ör. `LR234N060503`) |

  Huawei antenlerde her RET motorunun serisi farklı olabildiği için gruplama `Antenna Serial Number` ile yapılır. Bu bilgi yoksa `Unit Position` alanındaki anten/sektör adı kullanılır.
- **SITE ID eşleştirme:** Her kayıt, envanterdeki `NEName` alanından alınan saha koduyla raporlanır.
- **İki çalışma modu:**
  - 🔍 **Aranan Serileri Raporla:** Yalnızca kutuya yapıştırılan serileri arar → `Search_INVENTORY_SeriNoRaporu.xlsx`. Ham alt birim serisi, temiz seri veya Huawei Antenna Serial Number girilebilir; hepsi aynı anteni bulur. Bulunamayan seriler ayrı bir sayfada listelenir.
  - 📦 **Tüm Envanteri Raporla:** Tüm Antenna, Board ve Cabinet envanterini işler → `ALL_INVENTORY_SeriNoRaporu.xlsx`.
- **Sağlam veri okuma:** `,` / `;` ayırıcıları otomatik tanınır, birden fazla dışa aktarım birleştirilir, tekrar eden satırlar silinir. Hücreleri kaymış bozuk CSV dışa aktarımları otomatik onarılır. `HostVer` dosyaları atlanır.
- **Modern arayüz:** CustomTkinter ile açık/koyu/sistem teması, veri ve çıktı klasörü seçimi, ilerleme çubuğu, işlem günlüğü ve tek tıkla raporu açma.
- **Biçimli Excel çıktısı:** Kalın ve renkli başlık satırı, sabitlenmiş başlık, otomatik sütun genişliği ve filtreler.

### Rapor kolonları

| Kolon | Açıklama |
|---|---|
| `RET Mi?` | RET anten ise `Evet`, diğer ekipmanlar için `Hayır` |
| `Anten Tipi` | `4x`, `6x`, `8x` veya `KA` (RET değilse boş) |
| `SITE ID` | Saha kodu (`NEName`) |
| `Seri No` | Tekilleştirilmiş, temiz seri numarası |
| `Ekipman` / `Model` / `Üretici` | Envanter türü, model ve üretici bilgisi |

---

## 📁 Klasör Yapısı

```
├── SeriNoBulucuV2_0.py      # Uygulama (CustomTkinter arayüzü)
├── rapor.py                 # Dosya okuma, tekilleştirme ve Excel çıktısı
├── ret_parser.py            # RET desenleri (A–E) ve anten tipi kuralları
├── test_ret_parser.py       # Birim testleri
├── img/                     # Logo
├── Data/                    # Envanter dosyaları (Git'e yüklenmez)
├── Melanocetus_SeriNoBulucu_v3.0_Kullanim_Kilavuzu.pdf
├── requirements.txt         # Çalışma bağımlılıkları
├── requirements-dev.txt     # Derleme bağımlılıkları (PyInstaller)
└── LICENSE
```

`Data/` klasörüne şebeke yönetim sisteminden alınan envanter dışa aktarımları konur:

```
Data/
├── Inventory_Antenna_YYYYMMDD_HHMMSS.csv
├── Inventory_Board_YYYYMMDD_HHMMSS.csv
└── Inventory_Cabinet_YYYYMMDD_HHMMSS.csv
```

> ⚠️ `Data/` içeriği gizli saha bilgisi içerdiği için `.gitignore` ile hariç tutulur. Depoda yalnızca boş klasör (`Data/.gitkeep`) bulunur.

---

## 🚀 Kurulum ve Çalıştırma

### Seçenek 1: Hazır `.exe` (Python gerekmez)

1. [Releases](../../releases) sayfasından `Melanocetus_SeriNoBulucu_v3.0.exe` dosyasını indirin.
2. `.exe` dosyasının yanına bir `Data` klasörü oluşturun ve envanter dosyalarını içine kopyalayın.
3. `.exe` dosyasına çift tıklayın. Windows SmartScreen uyarısı çıkarsa **Ek bilgi → Yine de çalıştır** seçin.

Raporlar varsayılan olarak `.exe`'nin bulunduğu klasöre kaydedilir. Bu, uygulamadaki **Çıktı klasörü** alanından değiştirilebilir.

### Seçenek 2: Python kaynak kodundan

Python 3.10 veya üzeri gerekir.

```bash
git clone <depo-adresi>
cd <depo-klasörü>
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python SeriNoBulucuV2_0.py
```

Birim testleri:

```bash
python -m unittest test_ret_parser -v
```

### `.exe` derleme

```bash
pip install -r requirements-dev.txt
python -m PyInstaller --noconfirm --noconsole --onefile --name "Melanocetus_SeriNoBulucu_v3.0" --collect-all customtkinter --hidden-import openpyxl --add-data "img;img" --icon "img/MelanocetusV2.jpg" SeriNoBulucuV2_0.py
```

Derlenen dosya `dist/Melanocetus_SeriNoBulucu_v3.0.exe` konumunda oluşur. Logo `.exe`'nin içine gömülür; `Data` klasörü ve raporlar `.exe`'nin bulunduğu klasöre göre çözümlenir.

---

## 📖 Kullanım Kılavuzu

Son kullanıcılar için adım adım Türkçe kılavuz: [`Melanocetus_SeriNoBulucu_v3.0_Kullanim_Kilavuzu.pdf`](Melanocetus_SeriNoBulucu_v3.0_Kullanim_Kilavuzu.pdf)

---

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır.
© 2026 **Cesur Alphan Ellik - Melanocetus**
