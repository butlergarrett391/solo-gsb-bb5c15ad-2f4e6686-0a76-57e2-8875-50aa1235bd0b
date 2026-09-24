"""编织指令解析与逐行针数校验核心逻辑。

指令集（不区分大小写）：
  k      下针：消耗 1 针，产出 1 针
  p      上针：消耗 1 针，产出 1 针
  yo     挂线加针：消耗 0 针，产出 1 针
  k2tog  两针并一针：消耗 2 针，产出 1 针

语法：
  行   := 序列
  序列 := 项+
  项   := 原子 [ '*' 正整数 ] | '(' 序列 ')' [ '*' 正整数 ]
  原子 := 'k' | 'p' | 'yo' | 'k2tog'

括号可任意嵌套；'*' 后的倍数必须是正整数。
解析时只对 (消耗, 产出) 做乘法累积，绝不展开重复项，
因此 (k yo)*1000000 也能在常数时间内完成。
"""

ATOMS = {
    "k": (1, 1),
    "p": (1, 1),
    "yo": (0, 1),
    "k2tog": (2, 1),
}

MAX_MULTIPLIER = 1_000_000  # 倍数上限，防止无意义的天文数字


class ParseError(Exception):
    """指令解析错误。message 为人类可读信息，pos 为 0 起始的字符位置。"""

    def __init__(self, message, pos=None):
        super().__init__(message)
        self.message = message
        self.pos = pos


def _tokenize(text):
    """把一行指令切成记号流：ATOM / LPAREN / RPAREN / STAR / NUM。"""
    s = text.lower()
    tokens = []
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        if ch.isspace() or ch in ",;":
            i += 1
        elif s.startswith("k2tog", i):
            tokens.append(("ATOM", "k2tog", i))
            i += 5
        elif s.startswith("yo", i):
            tokens.append(("ATOM", "yo", i))
            i += 2
        elif ch == "k" or ch == "p":
            tokens.append(("ATOM", ch, i))
            i += 1
        elif ch == "(":
            tokens.append(("LPAREN", ch, i))
            i += 1
        elif ch == ")":
            tokens.append(("RPAREN", ch, i))
            i += 1
        elif ch == "*":
            tokens.append(("STAR", ch, i))
            i += 1
        elif ch.isdigit():
            j = i
            while j < n and s[j].isdigit():
                j += 1
            tokens.append(("NUM", int(s[i:j]), i))
            i = j
        else:
            raise ParseError(f"非法记号 '{ch}'（第 {i + 1} 个字符）", i)
    return tokens


class _Parser:
    """递归下降解析器，直接累积 (消耗, 产出)，不展开重复项。"""

    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0

    def _peek(self):
        if self.i < len(self.tokens):
            return self.tokens[self.i]
        return (None, None, None)

    def parse_row(self):
        consume, produce = self._parse_seq(top=True)
        kind, value, pos = self._peek()
        if kind is not None:
            raise ParseError(f"意外的记号 '{value}'（第 {pos + 1} 个字符）", pos)
        return consume, produce

    def _parse_seq(self, top):
        consume = produce = 0
        items = 0
        while True:
            kind, value, pos = self._peek()
            if kind is None:
                if not top:
                    raise ParseError("缺少右括号 ')'")
                break
            if kind == "RPAREN":
                if top:
                    raise ParseError(f"多余的右括号 ')'（第 {pos + 1} 个字符）", pos)
                break
            c, p = self._parse_item()
            consume += c
            produce += p
            items += 1
        if items == 0:
            raise ParseError("指令不能为空" if top else "括号内不能为空")
        return consume, produce

    def _parse_item(self):
        kind, value, pos = self._peek()
        if kind == "ATOM":
            self.i += 1
            consume, produce = ATOMS[value]
        elif kind == "LPAREN":
            self.i += 1
            consume, produce = self._parse_seq(top=False)
            kind2, _, _ = self._peek()
            if kind2 != "RPAREN":
                raise ParseError("缺少右括号 ')'")
            self.i += 1
        elif kind == "NUM":
            raise ParseError(
                f"意外的数字 '{value}'（第 {pos + 1} 个字符），"
                "重复请写成 指令*次数 或 (指令序列)*次数",
                pos,
            )
        else:
            raise ParseError(f"意外的记号 '{value}'（第 {pos + 1} 个字符）", pos)
        return self._apply_multiplier(consume, produce)

    def _apply_multiplier(self, consume, produce):
        kind, _, _ = self._peek()
        if kind != "STAR":
            return consume, produce
        self.i += 1
        kind2, value2, pos2 = self._peek()
        if kind2 != "NUM":
            raise ParseError("'*' 后必须紧跟正整数倍数", pos2)
        self.i += 1
        if value2 <= 0:
            raise ParseError("倍数必须为正整数（不能为 0）", pos2)
        if value2 > MAX_MULTIPLIER:
            raise ParseError(f"倍数过大（上限 {MAX_MULTIPLIER}）", pos2)
        return consume * value2, produce * value2


def parse_row(text):
    """解析一行指令，返回 (消耗针数, 产出针数)。非法输入抛出 ParseError。"""
    return _Parser(_tokenize(text)).parse_row()


def validate_rows(start, rows):
    """逐行校验针数。

    start 为起针数（正整数），rows 为非空指令字符串列表。
    上一行的产出即下一行的可用针数；每行消耗必须恰好等于可用针数，
    否则标出行号与差额。出错行之后不再继续推算。

    返回 dict：
      ok          全部通过时为 True
      rows        已处理行明细（含出错行）
      error       首个错误 {"row", "message"}，无错误为 None
      unprocessed 因出错而未推算的行数
      final       全部通过时的最终针数
    """
    results = []
    available = start
    first_error = None
    for idx, line in enumerate(rows, 1):
        entry = {"row": idx, "input": line, "in": available}
        try:
            consume, produce = parse_row(line)
        except ParseError as exc:
            entry.update(status="error", error=f"第 {idx} 行：{exc.message}")
            results.append(entry)
            first_error = {"row": idx, "message": entry["error"]}
            break
        entry["consume"] = consume
        if consume > available:
            entry.update(
                status="error",
                error=f"第 {idx} 行：需消耗 {consume} 针，但本行只有 "
                f"{available} 针可用，还差 {consume - available} 针",
            )
            results.append(entry)
            first_error = {"row": idx, "message": entry["error"]}
            break
        if consume < available:
            entry.update(
                status="error",
                error=f"第 {idx} 行：只消耗了 {consume} 针，本行共有 "
                f"{available} 针可用，剩余 {available - consume} 针未编织",
            )
            results.append(entry)
            first_error = {"row": idx, "message": entry["error"]}
            break
        entry.update(status="ok", out=produce)
        results.append(entry)
        available = produce
    return {
        "ok": first_error is None,
        "start": start,
        "rows": results,
        "error": first_error,
        "unprocessed": len(rows) - len(results),
        "final": available if first_error is None else None,
    }
