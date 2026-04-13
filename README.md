小鱼 AIKey Vault (API 密钥保险箱)
小鱼 AIKey Vault 是一款专为 AI 开发者和安全从业者设计的轻量级 API 密钥管理工具。它不仅提供美观的图形化界面，更通过本地强加密技术保障您的 API 资产安全，防止敏感信息泄露。

✨ 核心特性
🛡️ 本地加密存储：采用 cryptography (Fernet) 对配置文件进行全程加密，即便文件被拖走也无法轻易破解。

🔐 双重安全验证：

启动密码：防止他人非法开启软件。

自定义找回：支持安全问题找回，兼顾安全性与容错性。
<img width="618" height="468" alt="image" src="https://github.com/user-attachments/assets/c9bbac57-f5e5-4131-ae54-1d0e997e925d" />

🚀 多协议支持：预设 OpenAI、Anthropic、Gemini、DeepSeek、硅基流动等主流平台，支持自定义 Base URL。

<img width="2688" height="1533" alt="image" src="https://github.com/user-attachments/assets/28100de2-e8de-4c1b-bff3-15b4a9a8d449" />

🛠️ 自动化模型抓取：一键获取供应商最新模型列表，支持模型名称置顶、搜索过滤及手动增删。


📋 快捷分发：支持一键复制 API Key 或代码段，大幅提升开发效率。

📂 数据交互：支持 CSV 格式的批量导入与导出，方便备份与迁移。

🎨 Gemini Blue 主题：深邃专业的 UI 设计，支持 Treeview 树形管理，供应商与 Key 逻辑清晰。

📸 功能截图
(建议在此处上传您的软件截图)

密钥管理中心：清晰展示各供应商下的 Key 状态及到期提醒。

录入界面：灵活的模型勾选与搜索功能。

验证界面：简洁的启动登录框。

🛠️ 安装与运行
环境要求
Python 3.8 或更高版本

依赖库：tkinter, cryptography, requests, wmi (Windows 专用)
