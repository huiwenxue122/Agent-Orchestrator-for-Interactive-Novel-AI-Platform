# 殊途 (Shutu) — 互动小说 AI 平台（中文简介）

> **「殊途同归」** — 人人可书写自己的故事线。

产品愿景、系统架构与 MVP 路线见 **[README_E.md](./README_E.md)**（英文产品文档）。

编排器技术细节与 LangGraph 说明见 **[README.md](./README.md)**（主文档，英文）及 **[docs/ORCHESTRATOR_DESIGN.md](./docs/ORCHESTRATOR_DESIGN.md)**。

---

## 快速命令（仓库根目录）

```bash
pip install -r requirements.txt
PYTHONPATH=backend python -c "
from app.services.orchestrator import invoke_new_turn
r = invoke_new_turn('s', {'session_id': 's', 'current_node_id': 'root'})
print(r.get('hints'))
"
```

导出结构图（Mermaid 文本）：

```bash
PYTHONPATH=backend python backend/scripts/print_orchestrator_mermaid.py
```

---

## License

See repository.
