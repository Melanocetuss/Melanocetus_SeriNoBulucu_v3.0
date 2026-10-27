"""Veri klasöründeki envanter dosyalarını okuyup SeriNoRaporu.xlsx raporunu üretir."""
import csv
import glob
import os
import re
import time

import pandas as pd
import xlsxwriter
from xlsxwriter.exceptions import FileCreateError

from ret_parser import group_key, parse_serial, summarize_group

SITE_COL = "NEName"
SN_COL = "SN(Bar Code)"
VENDOR_COL = "Vendor Name"
ASN_COL = "Antenna Serial Number"
UNIT_POS_COL = "Unit Position"
MODEL_COLS = ("Antenna Model Number", "Board Type", "Rack Type")
SKIP_TYPES = {"hostver"}
COLUMNS = ["RET Mi?", "Anten Tipi", "SITE ID", "Seri No", "Ekipman", "Model", "Üretici"]
EXCEL_MAX_ROWS = 1_048_576


def _noop(oran, mesaj=None):
    pass


def find_files(data_dir):
    dosyalar = []
    for ext in ("*.csv", "*.xlsx", "*.xls"):
        dosyalar += glob.glob(os.path.join(data_dir, ext))
    # Excel'in açık dosyalar için bıraktığı ~$ kilit dosyalarını atla
    return sorted(d for d in dosyalar if not os.path.basename(d).startswith("~$"))


def equipment_type(path):
    m = re.match(r"Inventory_([A-Za-z]+)_", os.path.basename(path))
    return m.group(1) if m else os.path.splitext(os.path.basename(path))[0]


def detect_separator(path):
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        baslik = f.readline()
    return ";" if baslik.count(";") > baslik.count(",") else ","


def _wanted(col):
    return col in (SITE_COL, SN_COL, VENDOR_COL, ASN_COL, UNIT_POS_COL, *MODEL_COLS)


def _has_trailing_empty_headers(path, sep):
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
        baslik = next(csv.reader(f, delimiter=sep), [])
    return bool(baslik) and baslik[-1] == ""


def _read_split_tab_csv(path, sep):
    """Başında TAB olan hücrelerin ("\\t-1") boş hücre + değer olarak ikiye bölündüğü
    dışa aktarımları okur: her boş hücre sonraki hücreyle birleştirilerek sütunlar hizalanır."""
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.reader(f, delimiter=sep)
        baslik = next(reader)
        while baslik and baslik[-1] == "":
            baslik.pop()
        secili = [i for i, c in enumerate(baslik) if _wanted(c)]
        satirlar = []
        for row in reader:
            while row and row[-1] == "":
                row.pop()
            birlesik, i = [], 0
            while i < len(row):
                if row[i] == "" and i + 1 < len(row):
                    birlesik.append(row[i + 1])
                    i += 2
                else:
                    birlesik.append(row[i])
                    i += 1
            if len(birlesik) < len(baslik):
                birlesik += [""] * (len(baslik) - len(birlesik))
            elif len(birlesik) > len(baslik):
                continue  # hizalanamayan satırı atla
            satirlar.append([birlesik[i] for i in secili])
    return pd.DataFrame(satirlar, columns=[baslik[i] for i in secili], dtype=str)


def read_inventory(path):
    """Dosyadan saha/seri/üretici/model sütunlarını okur; seri sütunu yoksa None döner."""
    if path.lower().endswith(".csv"):
        sep = detect_separator(path)
        if _has_trailing_empty_headers(path, sep):
            df = _read_split_tab_csv(path, sep)
        else:
            df = pd.read_csv(path, sep=sep, dtype=str, usecols=_wanted, on_bad_lines="skip",
                             encoding="utf-8-sig", encoding_errors="replace", low_memory=False)
    else:
        df = pd.read_excel(path, dtype=str)
        df = df[[c for c in df.columns if _wanted(c)]]
    if SITE_COL not in df or SN_COL not in df:
        return None

    def sutun(ad):
        return df[ad] if ad in df else pd.Series("", index=df.index)

    model_col = next((c for c in MODEL_COLS if c in df), None)
    out = pd.DataFrame({
        "site": sutun(SITE_COL),
        "sn": sutun(SN_COL),
        "vendor": sutun(VENDOR_COL),
        "model": sutun(model_col) if model_col else "",
        "asn": sutun(ASN_COL),
        "sector": sutun(UNIT_POS_COL),
    }).fillna("").astype(str)
    out = out.apply(lambda c: c.str.strip())
    # Unit Position içinden sektör/anten adı: AntennaDeviceName=MNS012_195_ANT1_y3_... -> MNS012_195_ANT1
    out["sector"] = out["sector"].str.extract(r"AntennaDeviceName=(.+?_ANT\d+)", flags=re.IGNORECASE)[0].fillna("")
    out = out[out["sn"] != ""].drop_duplicates()
    out["ekipman"] = equipment_type(path)
    return out


def normalize_queries(serials):
    """Aranan serileri büyük harfe çevirir; RET desenine uyanlar için çekirdek seriyi de ekler.

    Dönüş: {aranan seri: eşleşebileceği anahtarlar kümesi}
    """
    sorgular = {}
    for s in serials:
        q = s.strip().upper()
        if q:
            p = parse_serial(q)
            sorgular[q] = {q, p.core} if p else {q}
    return sorgular


def build_report_frame(inv, sorgular=None):
    """RET serilerini (saha, çekirdek seri) bazında tekilleştirip rapor tablosunu üretir.

    sorgular verilirse yalnızca eşleşen anten/ekipman satırları döner. Eşleşen bir RET'in
    tipi, aynı sahadaki tüm kardeş alt birimlerine bakılarak belirlenir.
    Dönüş: (rapor, bulunamayan seriler listesi)
    """
    parsed = [parse_serial(sn, v) for sn, v in zip(inv["sn"], inv["vendor"])]
    is_ret = pd.Series([p is not None for p in parsed], index=inv.index)

    gruplar, bilgi, anahtarlar = {}, {}, {}
    for row, p in zip(inv[is_ret].itertuples(index=False), (p for p in parsed if p is not None)):
        key = (row.site, group_key(p, row.asn, row.sector))
        gruplar.setdefault(key, []).append(p)
        bilgi.setdefault(key, row)
        # Arama için: ham alt birim serisi, çekirdek seri, (Desen A) çekirdek + indeks, (Desen E) Antenna Serial Number
        grup_anahtari = anahtarlar.setdefault(key, set())
        grup_anahtari |= {p.core, row.sn.upper()}
        if p.pattern == "A":
            grup_anahtari.add(f"{p.core}{p.index:02d}")
        elif p.pattern == "E" and row.asn:
            grup_anahtari.add(row.asn.upper())

    ret_satirlari, ret_anahtarlari = [], []
    for key, parcalar in gruplar.items():
        row = bilgi[key]
        seri, tip = summarize_group(parcalar, row.asn)
        ret_satirlari.append(("Evet", tip, row.site, seri, row.ekipman, row.model, row.vendor))
        ret_anahtarlari.append(anahtarlar[key] | {seri})
    ret_df = pd.DataFrame(ret_satirlari, columns=COLUMNS)

    normal = inv[~is_ret]
    bulunamayan = []
    if sorgular is not None:
        aranan = set().union(*sorgular.values())
        ret_eslesen = [bool(k & aranan) for k in ret_anahtarlari]
        ret_df = ret_df[pd.Series(ret_eslesen, index=ret_df.index, dtype=bool)]
        normal = normal[normal["sn"].str.upper().isin(aranan)]
        bulunan = set(normal["sn"].str.upper())
        for k, eslesti in zip(ret_anahtarlari, ret_eslesen):
            if eslesti:
                bulunan |= k & aranan
        bulunamayan = [q for q, varyantlar in sorgular.items() if not varyantlar & bulunan]

    normal_df = pd.DataFrame({
        "RET Mi?": "Hayır", "Anten Tipi": "", "SITE ID": normal["site"], "Seri No": normal["sn"],
        "Ekipman": normal["ekipman"], "Model": normal["model"], "Üretici": normal["vendor"],
    }, columns=COLUMNS)

    rapor = pd.concat([ret_df, normal_df], ignore_index=True).drop_duplicates()
    rapor = rapor.sort_values(["SITE ID", "RET Mi?", "Ekipman", "Seri No"], ignore_index=True)
    return rapor, bulunamayan


def _sayfa_yaz(wb, ad, df, baslik, progress=_noop):
    ws = wb.add_worksheet(ad)
    for i, col in enumerate(df.columns):
        en_uzun = df[col].str.len().max() if len(df) else 0
        ws.set_column(i, i, min(max(len(col), 0 if pd.isna(en_uzun) else int(en_uzun)) + 3, 60))
    ws.set_row(0, 20)
    ws.write_row(0, 0, df.columns, baslik)
    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, len(df), len(df.columns) - 1)

    toplam = max(len(df), 1)
    for r, degerler in enumerate(df.itertuples(index=False, name=None), start=1):
        ws.write_row(r, 0, degerler)
        if r % 25000 == 0:
            progress(r / toplam)


def write_excel(rapor, path, progress=_noop, bulunamayan=None):
    if len(rapor) + 1 > EXCEL_MAX_ROWS:
        raise ValueError(f"Rapor {len(rapor):,} satır; Excel sınırı olan {EXCEL_MAX_ROWS:,} satırı aşıyor.")
    wb = xlsxwriter.Workbook(path, {"constant_memory": True})
    baslik = wb.add_format({"bold": True, "bg_color": "#DCE6F1", "font_color": "#1F3864",
                            "bottom": 1, "bottom_color": "#8EA9DB", "valign": "vcenter"})
    _sayfa_yaz(wb, "Seri No Raporu", rapor, baslik, progress)
    if bulunamayan:
        _sayfa_yaz(wb, "Bulunamayan Seriler", pd.DataFrame({"Aranan Seri No": bulunamayan}), baslik)
    try:
        wb.close()
    except FileCreateError as e:
        raise PermissionError(f"{os.path.basename(path)} yazılamadı. Dosya Excel'de açıksa kapatıp tekrar deneyin.") from e


def build_report(data_dir, output_path, progress=_noop, serials=None):
    """Klasördeki dosyaları işleyip raporu yazar; özet bilgileri döner.

    serials verilirse yalnızca bu seriler (ve RET kardeşleri) raporlanır, yoksa tüm envanter.
    progress(oran, mesaj) çağrılarıyla 0..1 arası ilerleme ve durum mesajları bildirilir.
    """
    baslangic = time.time()
    sorgular = normalize_queries(serials) if serials is not None else None
    if sorgular is not None and not sorgular:
        raise ValueError("Aranacak seri numarası girilmedi.")
    dosyalar = find_files(data_dir)
    if not dosyalar:
        raise FileNotFoundError("Seçilen klasörde CSV veya Excel dosyası bulunamadı.")

    toplam_boyut = sum(os.path.getsize(d) for d in dosyalar) or 1
    okunan_boyut, parcalar, islenen = 0, [], 0
    for dosya in dosyalar:
        ad = os.path.basename(dosya)
        if equipment_type(dosya).lower() in SKIP_TYPES:
            progress(okunan_boyut / toplam_boyut * 0.7, f"⏭ {ad} atlandı")
        else:
            progress(okunan_boyut / toplam_boyut * 0.7, f"📄 {ad} okunuyor…")
            try:
                df = read_inventory(dosya)
                if df is None:
                    progress(None, f"⏭ {ad} atlandı (SITE ID / seri no sütunu yok)")
                else:
                    parcalar.append(df)
                    islenen += 1
                    progress(None, f"✅ {ad}: {len(df):,} kayıt".replace(",", "."))
            except Exception as e:
                progress(None, f"❌ {ad} okunamadı: {e}")
        okunan_boyut += os.path.getsize(dosya)

    if not parcalar:
        raise ValueError("İşlenebilecek envanter dosyası bulunamadı.")

    if sorgular is None:
        progress(0.72, "🔄 RET seri numaraları tekilleştiriliyor…")
    else:
        progress(0.72, f"🔎 {len(sorgular):,} seri aranıyor, RET kardeşleri gruplanıyor…".replace(",", "."))
    envanter = pd.concat(parcalar, ignore_index=True).drop_duplicates()
    rapor, bulunamayan = build_report_frame(envanter, sorgular)

    progress(0.8, f"💾 {os.path.basename(output_path)} yazılıyor…")
    write_excel(rapor, output_path, lambda oran: progress(0.8 + oran * 0.2, None), bulunamayan)
    progress(1.0, None)

    return {
        "dosya": islenen,
        "satir": len(rapor),
        "ret": int((rapor["RET Mi?"] == "Evet").sum()),
        "tipler": rapor["Anten Tipi"][rapor["Anten Tipi"] != ""].value_counts().to_dict(),
        "aranan": len(sorgular) if sorgular is not None else None,
        "bulunamayan": len(bulunamayan),
        "sure": time.time() - baslangic,
    }
