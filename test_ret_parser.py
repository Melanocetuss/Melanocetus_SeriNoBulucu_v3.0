import unittest

from ret_parser import antenna_type, group_key, parse_serial, summarize_group


HUAWEI_8X = ["N3467LA3297190Rr2", "N3467LA3302164Lb1", "N3467LA3304182Lr1", "N3467LA3299175Rb2",
             "N3467LA330314CLy2", "N3467LA3300159Ry4", "N3467LA3301116Ly1", "N3467LA329812CRy3"]


class ParseSerialTest(unittest.TestCase):
    def test_pattern_a(self):
        p = parse_serial("0R2CB194000286908")
        self.assertEqual((p.pattern, p.core, p.band, p.index), ("A", "CB1940002869", "R2", 8))

    def test_pattern_b(self):
        p = parse_serial("03CB2631000DC4-R2")
        self.assertEqual((p.pattern, p.core, p.band, p.index), ("B", "CB2631000DC4", "R2", 3))

    def test_pattern_c(self):
        p = parse_serial("Y4-01CB2631000DC4")
        self.assertEqual((p.pattern, p.core, p.band, p.index), ("C", "CB2631000DC4", "Y4", 1))

    def test_pattern_d(self):
        p = parse_serial("E4K0655417-XX")
        self.assertEqual((p.pattern, p.core, p.ka), ("D", "E4K0655417", True))

    def test_ka_vendor_without_xx(self):
        self.assertEqual(parse_serial("CSH1543431-Y2", "KA").core, "CSH1543431")
        self.assertTrue(parse_serial("CSF3869249", " KA ").ka)

    def test_pattern_e_huawei(self):
        p = parse_serial("N3467LA3297190Rr2", "Huawei")
        self.assertEqual((p.pattern, p.core, p.band), ("E", "N3467LA3297190", "R2"))
        self.assertEqual(parse_serial("n3467la330314cly2", "huawei").core, "N3467LA330314C")
        self.assertEqual(parse_serial("N3467LA3297190RR2", "Huawei").band, "R2")

    def test_non_ret(self):
        for sn in ("", "  ", "M1433G7016S66720y", "2102311UWT10P2100275", "AS4XRM0000088-3Y1", "UAMA3J01LR1"):
            self.assertIsNone(parse_serial(sn, "Huawei" if sn != "UAMA3J01LR1" else ""), sn)


class SummarizeGroupTest(unittest.TestCase):
    def group(self, serials, vendor=""):
        return summarize_group([parse_serial(s, vendor) for s in serials])

    def test_pattern_a_8x_uses_highest_suffix(self):
        serials = ["0R2CB194000286908", "0Y3CB194000286904", "0B2CB194000286902", "0Y2CB194000286906",
                   "0Y4CB194000286901", "0R1CB194000286905", "0B1CB194000286903"]
        self.assertEqual(self.group(serials), ("CB194000286908", "8x"))

    def test_pattern_b_6x(self):
        serials = ["03CB2631000DC4-R2", "08CB2631000DC4-R1", "01CB2631000DC4-Y4",
                   "07CB2631000DC4-Y2", "10CB2631000DC4-Y1", "04CB2631000DC4-Y3"]
        self.assertEqual(self.group(serials), ("CB2631000DC4", "6x"))

    def test_pattern_c_6x(self):
        serials = ["R2-03CB2631000DC4", "R1-08CB2631000DC4", "Y4-01CB2631000DC4",
                   "Y2-07CB2631000DC4", "Y1-10CB2631000DC4", "Y3-04CB2631000DC4"]
        self.assertEqual(self.group(serials), ("CB2631000DC4", "6x"))

    def test_4x_and_ka(self):
        self.assertEqual(self.group(["00CB1-R1", "00CB1-Y1", "00CB1-Y2", "00CB1-B1"]), ("CB1", "4x"))
        self.assertEqual(self.group(["E4K0655417-XX"]), ("E4K0655417", "KA"))

    def test_pattern_e_grouping(self):
        parts = [parse_serial(s, "Huawei") for s in HUAWEI_8X]
        self.assertEqual(summarize_group(parts, "LR234N060503"), ("LR234N060503", "8x"))
        self.assertEqual(summarize_group(parts), ("N3467LA3304182", "8x"))
        self.assertEqual(group_key(parts[0], " lr234n060503 "), "E|ASN|LR234N060503")
        self.assertEqual(group_key(parts[0], "", "MNS012_195_ANT1"), "E|SEKTOR|MNS012_195_ANT1|N3467LA")
        self.assertEqual(group_key(parts[0]), "E|ONEK|N3467LA")
        self.assertEqual(group_key(parse_serial("03CB2631000DC4-R2"), "X"), "CB2631000DC4")

    def test_antenna_type_thresholds(self):
        self.assertEqual([antenna_type(n) for n in (1, 4, 5, 6, 7, 8)], ["4x", "4x", "6x", "6x", "8x", "8x"])


class SearchTest(unittest.TestCase):
    def setUp(self):
        import pandas as pd
        a = ["0R2CB194000286908", "0Y3CB194000286904", "0B2CB194000286902", "0Y2CB194000286906",
             "0Y4CB194000286901", "0R1CB194000286905", "0B1CB194000286903"]
        b = ["03CB2631000DC4-R2", "08CB2631000DC4-R1", "01CB2631000DC4-Y4", "07CB2631000DC4-Y2"]
        rows = [("SITE1", sn, "CB") for sn in a] + [("SITE2", sn, "CB") for sn in b]
        rows += [("SITE3", "E4K0655417-XX", "KA"), ("SITE3", "2102311UWT10P2100275", "Huawei")]
        rows = [r + ("", "") for r in rows]
        rows += [("SITE4", sn, "Huawei", "LR234N060503", "SITE4_1_ANT1") for sn in HUAWEI_8X]
        rows += [("SITE4", "N3467LA1111111Ry1", "Huawei", "", "SITE4_2_ANT1"),
                 ("SITE4", "N3467LA2222222Ly3", "Huawei", "", "SITE4_2_ANT1")]
        self.inv = pd.DataFrame(rows, columns=["site", "sn", "vendor", "asn", "sector"]).assign(
            model="", ekipman="Antenna")

    def search(self, *serials):
        from rapor import build_report_frame, normalize_queries
        rapor, bulunamayan = build_report_frame(self.inv, normalize_queries(serials))
        return [tuple(r) for r in rapor[["Anten Tipi", "SITE ID", "Seri No"]].values], bulunamayan

    def test_raw_and_clean_serials_group_with_siblings(self):
        for q in ("0Y3CB194000286904", "CB194000286908", "CB1940002869", "cb194000286905"):
            self.assertEqual(self.search(q), ([("8x", "SITE1", "CB194000286908")], []), q)
        for q in ("07CB2631000DC4-Y2", "CB2631000DC4", "Y1-10CB2631000DC4"):
            self.assertEqual(self.search(q), ([("4x", "SITE2", "CB2631000DC4")], []), q)

    def test_ka_normal_and_missing(self):
        rapor, bulunamayan = self.search("E4K0655417", "2102311UWT10P2100275", "YOK123", "0R1CB194000286905")
        self.assertEqual(rapor, [("8x", "SITE1", "CB194000286908"), ("KA", "SITE3", "E4K0655417"),
                                 ("", "SITE3", "2102311UWT10P2100275")])
        self.assertEqual(bulunamayan, ["YOK123"])


    def test_huawei_single_all_or_antenna_serial(self):
        beklenen = ([("8x", "SITE4", "LR234N060503")], [])
        self.assertEqual(self.search("N3467LA3297190Rr2"), beklenen)
        self.assertEqual(self.search("lr234n060503"), beklenen)
        self.assertEqual(self.search(*HUAWEI_8X), beklenen)
        self.assertEqual(self.search("N3467LA2222222LY3"), ([("4x", "SITE4", "N3467LA2222222")], []))


if __name__ == "__main__":
    unittest.main()
