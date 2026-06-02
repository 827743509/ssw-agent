# SSW Agent Web

Vue3 二次元风格问答页面，直连当前仓库的 LangGraph 智能体。

## 开发运行

```powershell
cd web
npm install
npm run dev
```

默认访问地址为 `http://127.0.0.1:5173`。

## 后端依赖

前端默认连接 `http://127.0.0.1:2024` 的 LangGraph API。请在仓库根目录启动：

```powershell
langgraph dev
```

如需修改 API 地址，复制 `.env.example` 为 `.env` 并设置：

```powershell
VITE_LANGGRAPH_API_URL=http://127.0.0.1:2024
```

## 支持的智能体

- `supervisor`
- `text_to_sql_agent`
- `default_agent`

这些 ID 与仓库根目录的 `langgraph.json` 保持一致。
