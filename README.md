# 编织说明逐行针数校验

一个用 **Python Flask + 原生 JavaScript** 实现的编织说明（knitting pattern）逐行针数校验工具。
输入起针数与每行指令，自动推算每行的入针 / 消耗 / 出针，并在针数对不上时指出**首个错误的行号与差额**。

## 指令语法

| 记号 | 含义 | 消耗 → 产出 |
|------|------|------------|
| `k` | 下针 | 1 → 1 |
| `p` | 上针 | 1 → 1 |
| `yo` | 挂线加针 | 0 → 1 |
| `k2tog` | 两针并一针 | 2 → 1 |
| `(指令序列)*次数` | 重复组，**可嵌套**，倍数须为正整数 | 按乘法累积 |

- 不区分大小写；空格、逗号、分号可作分隔符。
- 单个指令也可带倍数，如 `k*3` 表示 3 针下针。
- 解析只做 `(消耗, 产出)` 的乘法累积，**绝不展开重复项**，`(k yo)*1000000` 也能瞬时完成。
- 非法记号（如 `x`、`k2`）、非正整数倍数（`*0`、`*-1`、`*2.5`）、括号不配对都会被拒绝并给出位置提示。

## 校验规则

1. 第 1 行的可用针数 = 起针数；之后每行的可用针数 = 上一行的产出。
2. 每行指令的**消耗必须恰好等于可用针数**：
   - 消耗 > 可用：报错“还差 N 针”；
   - 消耗 < 可用：报错“剩余 N 针未编织”。
3. 出错行之后**不再继续推算**，页面展示已验证行的进出针数与首个错误。

## 快速开始

### 方式一：Docker Compose（推荐，一键安装依赖并启动）

```bash
docker compose up --build
```

### 方式二：Docker

```bash
docker build -t knit-check .
docker run --rm -p 8000:8000 knit-check
```

### 方式三：本地运行

```bash
pip install -r requirements.txt
python app.py
```

## 访问地址与端口

- 访问地址：**http://localhost:8000**
- 默认端口：**8000**
- 修改端口：
  - Compose：改 `docker-compose.yml` 中的 `ports`，如 `"9000:8000"` 把宿主机端口换成 9000；
  - 本地运行：用环境变量 `PORT`，如 `PORT=9000 python app.py`。

无需其他配置；所有依赖（Flask、gunicorn）由 `requirements.txt` 锁定，容器内由 gunicorn 提供服务。

## API

`POST /api/validate`，请求体为 JSON：

```json
{ "start": 10, "rows": ["k*2 (yo k2tog)*3 k*2", "p*10"] }
```

响应示例（出错时）：

```json
{
  "ok": false,
  "start": 10,
  "rows": [
    { "row": 1, "input": "...", "in": 10, "consume": 10, "out": 10, "status": "ok" },
    { "row": 2, "input": "p*12", "in": 10, "consume": 12, "status": "error",
      "error": "第 2 行：需消耗 12 针，但本行只有 10 针可用，还差 2 针" }
  ],
  "error": { "row": 2, "message": "第 2 行：……还差 2 针" },
  "unprocessed": 0,
  "final": null
}
```

## 运行测试

```bash
python3 -m unittest test_knitter -v
```

## 项目结构

```
├── app.py               # Flask 入口：页面路由 + /api/validate
├── knitter.py           # 解析器与逐行校验核心（不展开重复项）
├── test_knitter.py      # 单元测试
├── requirements.txt     # 依赖锁定
├── Dockerfile           # 镜像构建（gunicorn 启动）
├── docker-compose.yml   # 一键启动
└── static/              # 前端（原生 JS，无构建步骤）
    ├── index.html
    ├── app.js
    └── style.css
```
