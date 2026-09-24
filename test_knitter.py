import unittest

from knitter import ParseError, parse_row, validate_rows


class TestParse(unittest.TestCase):
    def test_atoms(self):
        self.assertEqual(parse_row("k"), (1, 1))
        self.assertEqual(parse_row("p"), (1, 1))
        self.assertEqual(parse_row("yo"), (0, 1))
        self.assertEqual(parse_row("k2tog"), (2, 1))

    def test_sequence_and_separators(self):
        self.assertEqual(parse_row("k k p"), (3, 3))
        self.assertEqual(parse_row("k, k; p"), (3, 3))
        self.assertEqual(parse_row("K2TOG  YO"), (2, 2))  # 大小写不敏感

    def test_groups_and_nesting(self):
        # yo(0→1) + k2tog(2→1)：每组消耗 2 产出 2，×3 = (6, 6)
        self.assertEqual(parse_row("(yo k2tog)*3"), (6, 6))
        self.assertEqual(parse_row("((k yo)*2 p)*2"), (6, 10))
        self.assertEqual(parse_row("k*2 (yo k2tog)*3 k*2"), (10, 10))

    def test_huge_repeat_not_expanded(self):
        # 不展开重复项，巨额倍数也应瞬间完成
        self.assertEqual(parse_row("(k yo)*1000000"), (1000000, 2000000))

    def test_illegal_input_rejected(self):
        for bad in [
            "x",        # 非法记号
            "(k",       # 缺少右括号
            "k)",       # 多余右括号
            "()",       # 空括号
            "",         # 空指令
            "k*",       # 缺少倍数
            "(k)*",     # 缺少倍数
            "k*0",      # 非正整数倍数
            "k*-1",     # 负数倍数
            "k2",       # 裸数字
            "k 3",      # 裸数字
            "k*2.5",    # 小数倍数
        ]:
            with self.assertRaises(ParseError, msg=bad):
                parse_row(bad)


class TestValidate(unittest.TestCase):
    def test_all_ok(self):
        r = validate_rows(10, ["k*2 (yo k2tog)*3 k*2", "p*10", "k2tog*5"])
        self.assertTrue(r["ok"])
        self.assertIsNone(r["error"])
        self.assertEqual(r["final"], 5)
        self.assertEqual([row["in"] for row in r["rows"]], [10, 10, 10])
        self.assertEqual([row["out"] for row in r["rows"]], [10, 10, 5])

    def test_overconsume_marks_row_and_diff(self):
        r = validate_rows(10, ["k*10", "k2tog*6", "p*5"])
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["row"], 2)
        self.assertIn("还差 2 针", r["error"]["message"])
        # 错误行不继续推算：只处理到第 2 行
        self.assertEqual(len(r["rows"]), 2)
        self.assertEqual(r["unprocessed"], 1)

    def test_underconsume_marks_row_and_diff(self):
        r = validate_rows(10, ["k*8"])
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["row"], 1)
        self.assertIn("剩余 2 针", r["error"]["message"])

    def test_parse_error_stops_propagation(self):
        r = validate_rows(4, ["k*4", "oops", "k*4"])
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["row"], 2)
        self.assertIn("非法记号", r["error"]["message"])
        self.assertEqual(r["unprocessed"], 1)

    def test_chain_uses_previous_output(self):
        # 第 1 行产出 5 针，第 2 行可用针数即为 5
        r = validate_rows(10, ["k2tog*5", "(yo k2tog)*2 k"])
        self.assertTrue(r["ok"])
        self.assertEqual(r["rows"][1]["in"], 5)
        self.assertEqual(r["final"], 5)


if __name__ == "__main__":
    unittest.main()
