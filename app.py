"""Flask 入口：提供页面与 /api/validate 校验接口。"""

import os

from flask import Flask, jsonify, request, send_from_directory

from knitter import validate_rows

app = Flask(__name__, static_folder="static", static_url_path="")

MAX_ROWS = 500        # 单次最多校验的行数
MAX_LINE_LEN = 2000   # 单行指令最大长度
MAX_START = 1_000_000  # 起针数上限


def _err(message, status=400):
    return jsonify({"ok": False, "error": {"row": None, "message": message}}), status


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.post("/api/validate")
def api_validate():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _err("请求体必须是 JSON 对象")

    start_raw = data.get("start")
    if isinstance(start_raw, bool):
        start = None
    elif isinstance(start_raw, int):
        start = start_raw
    elif isinstance(start_raw, str) and start_raw.strip().isdigit():
        start = int(start_raw.strip())
    else:
        start = None
    if start is None or start <= 0:
        return _err("起针数必须是正整数")
    if start > MAX_START:
        return _err(f"起针数过大（上限 {MAX_START}）")

    rows_raw = data.get("rows")
    if not isinstance(rows_raw, list) or any(not isinstance(r, str) for r in rows_raw):
        return _err("rows 必须是字符串数组")
    rows = [r.strip() for r in rows_raw]
    rows = [r for r in rows if r]  # 忽略空行
    if not rows:
        return _err("请至少输入一行指令")
    if len(rows) > MAX_ROWS:
        return _err(f"行数过多（上限 {MAX_ROWS} 行）")
    if any(len(r) > MAX_LINE_LEN for r in rows):
        return _err(f"存在超长指令行（上限 {MAX_LINE_LEN} 字符）")

    return jsonify(validate_rows(start, rows))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
