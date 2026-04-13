小鱼 AIKey Vault (API 密钥保险箱)
小鱼 AIKey Vault 是一款专为 AI 开发者和安全从业者设计的轻量级纯本地化 API 密钥管理工具。它不仅提供美观的图形化界面，更通过本地强加密技术保障您的 API 资产安全，防止敏感信息泄露。

✨ 核心特性
🛡️ 本地加密存储：采用 cryptography (Fernet) 对配置文件进行全程加密，即便文件被拖走也无法轻易破解。

🔐 双重安全验证：

启动密码：首次启动软件需设置密码，防止他人非法开启软件。

自定义找回：支持安全问题自定义，支持找回，兼顾安全性与容错性。
<img width="618" height="468" alt="image" src="https://github.com/user-attachments/assets/c9bbac57-f5e5-4131-ae54-1d0e997e925d" />

🚀 多协议支持：预设 OpenAI、Anthropic、Gemini、DeepSeek、硅基流动等主流平台，默认填写数据，支持自定义 Base URL。
<img width="2688" height="1533" alt="image" src="https://github.com/user-attachments/assets/28100de2-e8de-4c1b-bff3-15b4a9a8d449" />

🛠️ 自动化模型抓取：一键获取供应商最新模型列表，支持模型名称置顶、搜索过滤、调整上下行及手动增删。
<img width="2733" height="1555" alt="image" src="https://github.com/user-attachments/assets/d3a6e4b4-12fd-427e-888a-80ae34364634" />

📋 快捷分发：支持一键复制 API Key 或代码段，大幅提升开发效率。

<img width="2696" height="1151" alt="image" src="https://github.com/user-attachments/assets/452583db-f032-42cc-970c-38c923e11ddb" />

<img width="2653" height="1451" alt="image" src="https://github.com/user-attachments/assets/75ae7a72-623c-4c72-a175-95c03967b678" />

📂 数据交互：支持 CSV 格式的批量导入与导出，方便备份与迁移，请自行对导出文件加密哦。
<img width="1443" height="366" alt="image" src="https://github.com/user-attachments/assets/0aa089e3-e1a6-44ea-86bc-2dadede633fc" />


🎨 Gemini Blue 主题：深邃专业的 UI 设计，支持 Treeview 树形管理，供应商与 Key 逻辑清晰。
<img width="2690" height="1666" alt="image" src="https://github.com/user-attachments/assets/d01b4d0e-19d7-412d-bc3c-cc5824349c08" />

API key支持修改，修改后跳转到录入/修改界面。支持对模型检测连通性，正常可用模型显示绿色，不可用则是红色
<img width="2695" height="1548" alt="image" src="https://github.com/user-attachments/assets/25f75f78-43ca-4c54-8c82-21a8020d28a7" />


🛠️ 安装与运行
环境要求
Python 3.8 或更高版本
依赖库：tkinter, cryptography, requests, wmi (Windows 专用)
