"""Anten RET seri numarası ayrıştırma ve tekilleştirme kuralları (Desen A, B, C, D, E)."""
import re
from dataclasses import dataclass

_BAND = r"(?P<band>[RYB]\d)"

# Desen A: 0 + bant + çekirdek seri + 2 haneli alt birim  ->  0R2CB194000286908
PATTERN_A = re.compile(rf"^0{_BAND}(?P<core>[A-Z0-9]+)(?P<idx>\d{{2}})$", re.IGNORECASE)
# Desen B: 2 haneli indeks + çekirdek seri + -bant  ->  03CB2631000DC4-R2
PATTERN_B = re.compile(rf"^(?P<idx>\d{{2}})(?P<core>[A-Z0-9]+)-{_BAND}$", re.IGNORECASE)
# Desen C: bant- + 2 haneli indeks + çekirdek seri  ->  R2-03CB2631000DC4
PATTERN_C = re.compile(rf"^{_BAND}-(?P<idx>\d{{2}})(?P<core>[A-Z0-9]+)$", re.IGNORECASE)
# Desen D: KA anten  ->  E4K0655417-XX
PATTERN_D = re.compile(r"^(?P<core>[A-Z0-9]+)-XX$", re.IGNORECASE)
# Desen E: Huawei çoklu RET, gövde + yön (L/R) + bant  ->  N3467LA3297190Rr2
# Gövdenin orta haneleri her RET motorunda farklı olabilir; gruplama Antenna Serial Number ile yapılır.
PATTERN_E = re.compile(r"^(?P<core>[A-Z0-9]+?)(?P<side>[LR])(?P<band>[RBY]\d)$", re.IGNORECASE)
# KA üreticili ama -XX eki olmayan seriler; varsa sondaki bant eki (-Y2) atılır
_KA_SERIAL = re.compile(rf"^(?P<core>[A-Z0-9]+?)(?:-{_BAND})?$", re.IGNORECASE)


@dataclass(frozen=True)
class RetSerial:
    pattern: str              # "A", "B", "C", "D" veya "KA"
    core: str                 # bant/indeks ekleri atılmış çekirdek seri
    band: str | None = None
    index: int | None = None
    ka: bool = False


def parse_serial(serial: str, vendor: str = "") -> RetSerial | None:
    """Seri numarası bir RET desenine uyuyorsa ayrıştırır, uymuyorsa None döner."""
    sn = (serial or "").strip().upper()
    if not sn:
        return None
    ka_vendor = (vendor or "").strip().upper() == "KA"

    m = PATTERN_D.match(sn)
    if m:
        return RetSerial("D", m["core"], ka=True)
    for name, pattern in (("A", PATTERN_A), ("B", PATTERN_B), ("C", PATTERN_C)):
        m = pattern.match(sn)
        if m:
            return RetSerial(name, m["core"], m["band"].upper(), int(m["idx"]), ka=ka_vendor)
    if ka_vendor:
        m = _KA_SERIAL.match(sn)
        if m:
            return RetSerial("KA", m["core"], m["band"], ka=True)
    # Desen E yalnızca Huawei antenler için: optik modül seri noları da benzer eklerle bitebiliyor
    m = PATTERN_E.match(sn) if (vendor or "").strip().upper() == "HUAWEI" else None
    if m:
        return RetSerial("E", m["core"], m["band"].upper())
    return None


def group_key(p: RetSerial, antenna_serial: str = "", sector: str = "") -> str:
    """Aynı sahadaki fiziksel anteni belirleyen anahtar.

    Desen E (Huawei) için sırasıyla Antenna Serial Number, sektör (AntennaDeviceName=..._ANT1)
    ve son çare olarak gövdenin ilk 7 karakteri kullanılır; diğer desenlerde çekirdek seri.
    """
    if p.pattern != "E":
        return p.core
    if antenna_serial.strip():
        return f"E|ASN|{antenna_serial.strip().upper()}"
    if sector.strip():
        return f"E|SEKTOR|{sector.strip().upper()}|{p.core[:7]}"
    return f"E|ONEK|{p.core[:7]}"


def antenna_type(band_count: int) -> str:
    """Farklı bant sayısına göre anten tipi: <=4 -> 4x, 5-6 -> 6x, >=7 -> 8x."""
    if band_count >= 7:
        return "8x"
    if band_count >= 5:
        return "6x"
    return "4x"


def summarize_group(parts: list[RetSerial], antenna_serial: str = "") -> tuple[str, str]:
    """Aynı sahada aynı antene ait alt birimlerden (temsilci seri no, anten tipi) üretir."""
    core = parts[0].core
    a_indexes = [p.index for p in parts if p.pattern == "A"]
    if parts[0].pattern == "E":
        # Huawei: Antenna Serial Number varsa o, yoksa ekleri atılmış en yüksek seri
        serial = antenna_serial.strip() or max(p.core for p in parts)
    elif a_indexes:
        serial = f"{core}{max(a_indexes):02d}"
    else:
        serial = core
    if any(p.ka for p in parts):
        return serial, "KA"
    return serial, antenna_type(len({p.band for p in parts if p.band}))
