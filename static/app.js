"use strict";

const $ = (id) => document.getElementById(id);

const EXAMPLE = [
  "k*2 (yo k2tog)*3 k*2",
  "p*10",
  "(k2tog yo)*5",
  "k2tog*5",
  "yo*5 k*5",
].join("\n");

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function render(data) {
  const box = $("result");
  box.innerHTML = "";

  const banner = el("div", "banner " + (data.ok ? "ok" : "bad"));
  if (data.ok) {
    banner.textContent = `✅ 全部 ${data.rows.length} 行校验通过，最终 ${data.final} 针。`;
  } else {
    const msg = data.error ? data.error.message || String(data.error) : "校验失败";
    banner.textContent =
      "❌ " + msg + (data.unprocessed > 0 ? `（后续 ${data.unprocessed} 行未推算）` : "");
  }
  box.appendChild(banner);

  if (!data.rows || data.rows.length === 0) return;

  const table = el("table");
  const head = el("tr");
  ["行", "指令", "入针", "消耗", "出针", "状态"].forEach((h) =>
    head.appendChild(el("th", "", h))
  );
  table.appendChild(head);

  for (const r of data.rows) {
    const tr = el("tr", r.status === "ok" ? "ok" : "bad");
    if (r.error) tr.title = r.error;
    tr.appendChild(el("td", "num", String(r.row)));
    tr.appendChild(el("td", "code", r.input));
    tr.appendChild(el("td", "num", String(r.in)));
    tr.appendChild(el("td", "num", r.consume != null ? String(r.consume) : "—"));
    tr.appendChild(el("td", "num", r.out != null ? String(r.out) : "—"));
    tr.appendChild(el("td", "status", r.status === "ok" ? "✓ 通过" : "✗ 出错"));
    table.appendChild(tr);
  }
  box.appendChild(table);
}

function renderFailure(message) {
  const box = $("result");
  box.innerHTML = "";
  box.appendChild(el("div", "banner bad", "❌ " + message));
}

async function validate() {
  const startRaw = $("start").value.trim();
  const rows = $("rows").value.split("\n").map((s) => s.trim()).filter(Boolean);
  if (!/^\d+$/.test(startRaw) || Number(startRaw) <= 0) {
    renderFailure("起针数必须是正整数。");
    return;
  }
  if (rows.length === 0) {
    renderFailure("请至少输入一行指令。");
    return;
  }
  try {
    const res = await fetch("/api/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ start: Number(startRaw), rows }),
    });
    render(await res.json());
  } catch (err) {
    renderFailure("无法连接服务器，请稍后重试。");
  }
}

let timer = null;
function scheduleValidate() {
  clearTimeout(timer);
  timer = setTimeout(() => {
    if ($("rows").value.trim()) validate();
  }, 400);
}

$("validateBtn").addEventListener("click", validate);
$("exampleBtn").addEventListener("click", () => {
  $("start").value = "10";
  $("rows").value = EXAMPLE;
  validate();
});
$("clearBtn").addEventListener("click", () => {
  $("rows").value = "";
  $("result").innerHTML = "";
});
$("rows").addEventListener("input", scheduleValidate);
$("start").addEventListener("input", scheduleValidate);
$("rows").addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") validate();
});
