import tkinter as tk
import sys
from tkinter import ttk, messagebox, filedialog, scrolledtext
import json, csv, threading, requests
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from cryptography.fernet import Fernet
import base64
import os
import hashlib

# ====================== 主题配置 ======================
class GeminiBlueTheme:
    BG_SIDEBAR = "#1A3B5D"
    BG_MAIN = "#F8F9FA"
    ACCENT = "#1A73E8"
    BORDER_COLOR = "#2D3748"
    TEXT_ON_DARK = "#FFFFFF"
    TEXT_MAIN = "#2D3748"
    INPUT_BG = "#FFFFFF"
    SUCCESS_GREEN = "#28A745"

# 建议：实际分发时，Key 可以根据机器特征生成，这里演示使用固定 Key
# 只有持有此 Key 的软件才能解密配置文件
FERNET_KEY = b'uV9_S6_8WvO1_Lp96G6-5P_8u_z7J3_8u-z7J3_8u-Y=' # 需 32 字节 Base64
cipher = Fernet(FERNET_KEY)

class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        # 创建 Canvas，确保背景色一致，移除高亮边框以防像素偏移
        self.canvas = tk.Canvas(self, bg=GeminiBlueTheme.INPUT_BG, 
                                highlightthickness=0,
                                bd=0)
        
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        
        # 内部框架使用 tk.Frame
        self.scrollable_frame = tk.Frame(self.canvas, bg=GeminiBlueTheme.INPUT_BG)

        # 核心逻辑：内容改变时更新滚动区域
        self.scrollable_frame.bind("<Configure>", self._update_scroll_region)
        
        # 画布尺寸改变时，让内部框架宽度等于画布宽度
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.window_id, width=e.width))

        # 关键：放置在 0,0 坐标，锚点为西北(nw)
        self.window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # 鼠标滚动绑定（仅在进入区域时生效）
        self.canvas.bind("<Enter>", lambda _: self.canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.canvas.bind("<Leave>", lambda _: self.canvas.unbind_all("<MouseWheel>"))

    def _update_scroll_region(self, event=None):
        """动态计算滚动区域"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event):
        # 向上滚 event.delta > 0，向下滚 < 0
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


class AIKeyManager:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("A小鱼 AIKey Vault v9.3")
        self.root.geometry("1820x1020")
        self.root.configure(bg=GeminiBlueTheme.BG_MAIN)

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_styles()

        # 获取可执行文件所在目录，确保配置文件跟着软件位置
        if getattr(sys, 'frozen', False):
            # 打包成exe后的路径
            self.config_dir = Path(sys.executable).parent / ".ai_key_manager_v8"
        else:
            # 开发模式下的路径
            self.config_dir = Path(__file__).parent / ".ai_key_manager_v8"
        self.config_file = self.config_dir / "config_v8.json"
        self.config_dir.mkdir(exist_ok=True)


        # 编辑上下文
        self.editing_context = None

        # 变量
        self.provider_var = tk.StringVar()
        self.base_url_var = tk.StringVar()
        self.type_var = tk.StringVar(value="openai")
        self.note_var = tk.StringVar()
        self.m_search_var = tk.StringVar()

        # 时间字段
        self.create_time_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.expire_days_var = tk.StringVar(value="30")

        self.full_model_list: List[str] = []
        self.model_vars: Dict[str, tk.BooleanVar] = {}

        self.presets = {
            "OpenAI": {"type": "openai", "base_url": "https://api.openai.com/v1", "models": ["gpt-4o", "gpt-4o-mini"]},
            "DeepSeek": {"type": "openai", "base_url": "https://api.deepseek.com/v1", "models": ["deepseek-chat", "deepseek-reasoner"]},
            "硅基流动 (SiliconFlow)": {"type": "openai", "base_url": "https://api.siliconflow.cn/v1", "models": ["deepseek-ai/DeepSeek-V3", "Qwen/Qwen2.5-72B-Instruct"]},
            "阿里通义 (DashScope)": {"type": "openai", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "models": ["qwen-max", "qwen-plus", "qwen-turbo"]},
            "腾讯混元 (Hunyuan)": {"type": "openai", "base_url": "https://api.hunyuan.cloud.tencent.com/v1", "models": ["hunyuan-pro"]},
            "字节跳动 (Ark/Doubao)": {"type": "openai", "base_url": "https://ark.cn-beijing.volces.com/api/v3", "models": ["doubao-pro-128k"]},
            "百度文心 (Yiyan)": {"type": "openai", "base_url": "https://qianfan.baidubce.com/v2", "models": ["ernie-4.0-turbo-8k"]},
            "智谱 GLM": {"type": "openai", "base_url": "https://open.bigmodel.cn/api/paas/v4/", "models": ["glm-4-plus"]},
            "月之暗面 (Kimi)": {"type": "openai", "base_url": "https://api.moonshot.cn/v1", "models": ["moonshot-v1-8k"]},
            "MiniMax (国内)": {"type": "openai", "base_url": "https://api.minimaxi.com/v1", "models": ["MiniMax-M2.7", "MiniMax-M2.5"]},
            "Anthropic (Claude)": {"type": "anthropic", "base_url": "https://api.anthropic.com/v1", "models": ["claude-3-5-sonnet-20241022"]},
            "Google (Gemini)": {"type": "gemini", "base_url": "https://generativelanguage.googleapis.com/v1beta", "models": ["gemini-1.5-pro"]},
            "Ollama (本地)": {"type": "openai", "base_url": "http://localhost:11434/v1", "models": ["llama3.1", "llama3", "gemma2", "mistral", "phi3"]},
        }
        self.load_config()
        self.create_ui()
        self.refresh_tree()

        
        # 在窗口进入主循环前进行验证
        self.root.after(100, self.check_auth)

        

    def check_auth(self):
        """启动权限检查"""
        if "auth_hash" not in self.config:
            self.setup_initial_auth()
        else:
            self.show_login_dialog()

    def hash_val(self, val):
        return hashlib.sha256((val + "secure_salt").encode()).hexdigest()

    def setup_initial_auth(self):
        """首次运行：设置密码 + 确认密码 + 自定义找回问题和答案"""
        setup_win = tk.Toplevel(self.root)
        setup_win.title("初始化安全设置")
        setup_win.geometry("450x480")
        setup_win.grab_set()
        setup_win.resizable(False, False)

        tk.Label(setup_win, text="首次使用，请设置启动密码", 
                 font=("微软雅黑", 12, "bold")).pack(pady=(20, 15))

        # 密码
        tk.Label(setup_win, text="设置启动密码 (至少6位):", font=("微软雅黑", 10)).pack(anchor="w", padx=40, pady=(10, 2))
        pw_ent = tk.Entry(setup_win, show="*", width=32, font=("微软雅黑", 10))
        pw_ent.pack(pady=(0, 8))

        # 确认密码
        tk.Label(setup_win, text="确认启动密码:", font=("微软雅黑", 10)).pack(anchor="w", padx=40, pady=(5, 2))
        pw_confirm_ent = tk.Entry(setup_win, show="*", width=32, font=("微软雅黑", 10))
        pw_confirm_ent.pack(pady=(0, 15))

        # 自定义找回问题
        tk.Label(setup_win, text="设置找回问题（很重要！用于忘记密码/修改问题）:", font=("微软雅黑", 10)).pack(anchor="w", padx=40, pady=(10, 2))
        q_ent = tk.Entry(setup_win, width=38, font=("微软雅黑", 10))
        q_ent.pack(pady=(0, 8))
        q_ent.insert(0, "我最喜欢的人是？")  # 默认示例

        # 找回答案
        tk.Label(setup_win, text="设置找回答案:", font=("微软雅黑", 10)).pack(anchor="w", padx=40, pady=(5, 2))
        a_ent = tk.Entry(setup_win, width=38, font=("微软雅黑", 10))
        a_ent.pack(pady=(0, 25))

        def save_auth():
            pw1 = pw_ent.get().strip()
            pw2 = pw_confirm_ent.get().strip()
            question = q_ent.get().strip()
            answer = a_ent.get().strip()

            if len(pw1) < 6:
                messagebox.showwarning("提示", "密码长度至少需要6位！")
                return
            if pw1 != pw2:
                messagebox.showwarning("提示", "两次输入的密码不一致，请重新输入！")
                pw_confirm_ent.delete(0, tk.END)
                pw_confirm_ent.focus()
                return
            if not question or not answer:
                messagebox.showwarning("提示", "找回问题和找回答案不能为空！")
                return

            # 保存到 config
            self.config["auth_hash"] = self.hash_val(pw1)
            self.config["recovery_q"] = question
            self.config["recovery_hash"] = self.hash_val(answer)

            self.save_config()
            setup_win.destroy()
            messagebox.showinfo("设置成功", "安全设置已保存！\n\n请牢记您的密码、找回问题和答案。")
            
            # 设置完成后自动显示登录窗口
            self.root.after(300, self.show_login_dialog)

        tk.Button(setup_win, text="保存并启动", 
                  command=save_auth, 
                  bg=GeminiBlueTheme.ACCENT, 
                  fg="white",
                  font=("微软雅黑", 10, "bold"),
                  width=18, height=2).pack(pady=10)

        setup_win.protocol("WM_DELETE_WINDOW", self.root.quit)
    
    def show_login_dialog(self):
        """登录界面 + 找回密码（支持回车登录 + 重置密码时二次确认 + 修改找回问题）"""
        self.root.withdraw()
        login_win = tk.Toplevel(self.root)
        login_win.title("身份验证")
        login_win.geometry("420x360")
        login_win.grab_set()
        login_win.resizable(False, False)

        tk.Label(login_win, text="请输入启动密码", 
                 font=("微软雅黑", 11, "bold")).pack(pady=(30, 15))

        pw_ent = tk.Entry(login_win, show="*", width=30, font=("微软雅黑", 10))
        pw_ent.pack(pady=8)

        # ==================== 回车登录功能 ====================
        def on_enter_key(event=None):
            do_login()

        pw_ent.bind("<Return>", on_enter_key)   # 绑定回车键

        def do_login():
            password = pw_ent.get().strip()
            if self.hash_val(password) == self.config.get("auth_hash"):
                login_win.destroy()
                self.root.deiconify()
            else:
                messagebox.showerror("登录失败", "密码错误，请重试")
                pw_ent.delete(0, tk.END)
                pw_ent.focus()

        def recover_password():
            """找回密码 → 重置密码 + 可选修改找回问题（需验证旧答案）"""
            q = self.config.get("recovery_q", "请设置找回问题")
            
            from tkinter import simpledialog
            
            # 第一步：验证旧答案
            ans = simpledialog.askstring("找回密码", f"问题：{q}\n\n请输入答案：")
            if ans is None:          # 用户取消
                return
            if not ans.strip() or self.hash_val(ans.strip()) != self.config.get("recovery_hash"):
                messagebox.showerror("找回失败", "答案不正确！")
                return

            # 第二步：重置密码窗口
            reset_win = tk.Toplevel(login_win)
            reset_win.title("重置启动密码")
            reset_win.geometry("450x420")
            reset_win.grab_set()
            reset_win.resizable(False, False)

            tk.Label(reset_win, text="重置启动密码", 
                     font=("微软雅黑", 12, "bold")).pack(pady=(20, 5))
            tk.Label(reset_win, text="请设置新的启动密码", 
                     font=("微软雅黑", 10)).pack(pady=(0, 15))

            # 新密码
            tk.Label(reset_win, text="请输入新密码（至少6位）:", font=("微软雅黑", 10)).pack(anchor="w", padx=40, pady=(10, 2))
            new_pw_ent = tk.Entry(reset_win, show="*", width=32, font=("微软雅黑", 10))
            new_pw_ent.pack(pady=(0, 10))

            # 确认新密码
            tk.Label(reset_win, text="请再次输入新密码:", font=("微软雅黑", 10)).pack(anchor="w", padx=40, pady=(5, 2))
            confirm_pw_ent = tk.Entry(reset_win, show="*", width=32, font=("微软雅黑", 10))
            confirm_pw_ent.pack(pady=(0, 20))

            # 是否修改找回问题
            modify_var = tk.BooleanVar(value=False)
            tk.Checkbutton(reset_win, text="我想要修改找回问题和答案", 
                           variable=modify_var, font=("微软雅黑", 10)).pack(anchor="w", padx=40, pady=10)

            def submit_reset():
                new_pw = new_pw_ent.get().strip()
                confirm_pw = confirm_pw_ent.get().strip()

                if len(new_pw) < 6:
                    messagebox.showwarning("提示", "新密码长度至少需要6位！")
                    return
                if new_pw != confirm_pw:
                    messagebox.showwarning("提示", "两次输入的密码不一致，请重新输入！")
                    confirm_pw_ent.delete(0, tk.END)
                    confirm_pw_ent.focus()
                    return

                # 更新密码
                self.config["auth_hash"] = self.hash_val(new_pw)

                # 如果勾选了修改找回问题
                if modify_var.get():
                    new_q = simpledialog.askstring("新找回问题", "请输入新的找回问题：", 
                                                   initialvalue=self.config.get("recovery_q", ""))
                    new_a = simpledialog.askstring("新找回答案", "请输入新的找回答案：")
                    
                    if new_q and new_a and new_q.strip() and new_a.strip():
                        self.config["recovery_q"] = new_q.strip()
                        self.config["recovery_hash"] = self.hash_val(new_a.strip())
                    else:
                        messagebox.showwarning("提示", "问题或答案不能为空，将保留原有设置")

                self.save_config()

                messagebox.showinfo("操作成功", "密码已重置成功！\n找回设置已按你的选择更新。")
                
                reset_win.destroy()
                login_win.destroy()
                self.show_login_dialog()

            tk.Button(reset_win, text="确认重置", 
                      command=submit_reset,
                      bg=GeminiBlueTheme.ACCENT, 
                      fg="white",
                      font=("微软雅黑", 10, "bold"),
                      width=16, height=2).pack(pady=20)

            reset_win.protocol("WM_DELETE_WINDOW", reset_win.destroy)

        # ==================== 按钮区域 ====================
        btn_frame = tk.Frame(login_win)
        btn_frame.pack(pady=30)

        tk.Button(btn_frame, text="进入软件", command=do_login,
                  width=15, bg=GeminiBlueTheme.ACCENT, fg="white", 
                  font=("微软雅黑", 10, "bold")).pack(side="left", padx=15)
        
        tk.Button(btn_frame, text="忘记密码？", command=recover_password,
                  relief="flat", fg="#666666", font=("微软雅黑", 10)).pack(side="left", padx=15)

        login_win.protocol("WM_DELETE_WINDOW", self.root.quit)
    
    def configure_styles(self):
        self.style.configure(".", background=GeminiBlueTheme.BG_MAIN, font=("微软雅黑", 10))
        self.style.configure("Side.TFrame", background=GeminiBlueTheme.BG_SIDEBAR)
        self.style.configure("Side.TLabel", background=GeminiBlueTheme.BG_SIDEBAR, foreground=GeminiBlueTheme.TEXT_ON_DARK)
        self.style.configure("Action.TButton", foreground="white", background=GeminiBlueTheme.ACCENT, font=("微软雅黑", 9, "bold"))
        self.style.configure("Treeview", rowheight=36, borderwidth=0)
        self.style.configure("Treeview.Heading", font=("微软雅黑", 10, "bold"))

    def create_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_manager = ttk.Frame(self.notebook)
        self.tab_input = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_manager, text="🔑 密钥管理中心")
        self.notebook.add(self.tab_input, text="✏️ API 录入/修改")
        
        # 添加隐藏帮助 tab
        self.tab_help = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_help, text="📖 帮助")
        
        # 添加帮助内容
        help_text = """使用说明：

1. 密钥管理中心：
   - 查看和管理所有已保存的 API Key （置顶、删除、上下移动、导入导出）
   - 模型名称前的圆点查看模型状态（绿色=有效，红色=无效，需点击对应模型的行测试连通性）
   - 鼠标左键点击可复制相关信息（单个值or全部信息）

2. API 录入/修改：
   - 选择预设供应商或自定义配置
   - 填写 API Key 和模型信息
   - 点击 "✨ 抓取模型" 获取最新模型列表

3. 账号密码：
   - 重新打开点击忘记密码可修改密码或更改密保问题
   - 忘记密保问题和密码将无法打开软件

4. 安全提醒：
   - 本工具会将 API Key 保存在本地配置文件中（隐藏文件夹下）
   - 请妥善保管您的配置文件，不要误删哦
   - 定期测试 API Key 的有效性"""
        
        help_label = tk.Label(self.tab_help, text=help_text, font=("微软雅黑", 10), justify="left")
        help_label.pack(padx=20, pady=20, fill="both", expand=True)
        
        self.notebook.select(self.tab_manager)

        self.create_input_tab()
        self.create_manager_tab()

    # ====================== API 录入/修改 Tab ======================
    def create_input_tab(self):
        left_frame = ttk.Frame(self.tab_input, style="Side.TFrame", padding=20)
        left_frame.pack(fill="both", expand=True)

        self.form_title = ttk.Label(left_frame, text="API 配置录入", font=("微软雅黑", 14, "bold"), style="Side.TLabel")
        self.form_title.pack(anchor="w", pady=(0, 15))

        form_f = ttk.Frame(left_frame, style="Side.TFrame")
        form_f.pack(fill="x")

        ttk.Label(form_f, text="供应商", style="Side.TLabel").pack(anchor="w", pady=(5, 2))
        self.prov_cb = ttk.Combobox(form_f, textvariable=self.provider_var,
                                    values=list(self.presets.keys()) + ["自定义"], state="readonly")
        self.prov_cb.pack(fill="x", pady=(0, 8), ipady=3)
        self.prov_cb.bind("<<ComboboxSelected>>", self.on_preset_selected)

        ttk.Label(form_f, text="接口地址 (Base URL)", style="Side.TLabel").pack(anchor="w", pady=(5, 2))
        tk.Entry(form_f, textvariable=self.base_url_var, bg=GeminiBlueTheme.INPUT_BG,
                 relief="solid", borderwidth=1, font=("微软雅黑", 10)).pack(fill="x", pady=(0, 8), ipady=3)

        ttk.Label(form_f, text="协议类型", style="Side.TLabel").pack(anchor="w", pady=(5, 2))
        ttk.Combobox(form_f, textvariable=self.type_var, values=["openai", "anthropic", "gemini"],
                     state="readonly").pack(fill="x", pady=(0, 8), ipady=3)

        ttk.Label(form_f, text="备注", style="Side.TLabel").pack(anchor="w", pady=(5, 2))
        tk.Entry(form_f, textvariable=self.note_var, bg=GeminiBlueTheme.INPUT_BG,
                 relief="solid", borderwidth=1, font=("微软雅黑", 10)).pack(fill="x", pady=(0, 8), ipady=3)

        # 时间字段
        time_f = ttk.Frame(left_frame, style="Side.TFrame")
        time_f.pack(fill="x", pady=10)

        ttk.Label(time_f, text="录入时间", style="Side.TLabel").pack(anchor="w", side="left", padx=(0, 10))
        ttk.Entry(time_f, textvariable=self.create_time_var, width=22, state="readonly").pack(side="left", padx=(0, 30))

        ttk.Label(time_f, text="到期天数", style="Side.TLabel").pack(anchor="w", side="left", padx=(0, 10))
        ttk.Spinbox(time_f, from_=0, to=3650, textvariable=self.expire_days_var, width=10).pack(side="left", padx=(0, 5))
        ttk.Label(time_f, text="天", style="Side.TLabel").pack(side="left")

        ttk.Label(left_frame, text="API Keys (一行一个)", style="Side.TLabel").pack(anchor="w", pady=(10, 2))
        self.keys_text = tk.Text(left_frame, height=6, relief="solid", borderwidth=1, font=("Consolas", 10), undo=True)
        self.keys_text.pack(fill="x", pady=(0, 10))

        # --- 模型选择区域 ---
        ttk.Label(left_frame, text="模型选择", style="Side.TLabel").pack(anchor="w", pady=(5, 2))
        
        # 顶部工具栏（抓取、全选、反选）
        m_tools = ttk.Frame(left_frame, style="Side.TFrame")
        m_tools.pack(fill="x", pady=(0, 5))
        ttk.Button(m_tools, text="✨ 获取模型", command=self.fetch_latest_models).pack(side="left", padx=2)
        ttk.Button(m_tools, text="全选", command=lambda: self.toggle_all_models(True)).pack(side="left", padx=2)
        ttk.Button(m_tools, text="取消全选", command=lambda: self.toggle_all_models(False)).pack(side="left", padx=2)

        # --- 修改部分：搜索框与添加按钮组合 ---
        m_search_frame = ttk.Frame(left_frame, style="Side.TFrame")
        m_search_frame.pack(fill="x", pady=5)

        self.m_search_ent = tk.Entry(m_search_frame, textvariable=self.m_search_var, 
                                     relief="solid", borderwidth=1, font=("微软雅黑", 9))
        self.m_search_ent.pack(side="left", fill="x", expand=True, ipady=3)
        self.m_search_var.trace_add("write", self.filter_models)

        # 新增手动添加、删除按钮
        ttk.Button(m_search_frame, text="➖", width=3, 
                   command=self.remove_custom_model).pack(side="right", padx=2)
        ttk.Button(m_search_frame, text="➕", width=3, 
                   command=self.add_custom_model).pack(side="right", padx=2)
        # ------------------------------------

        self.model_scroll = ScrollableFrame(left_frame)
        # 确保 fill="both" 和 expand=True，但在 pack 之前可以指定一个高度
        self.model_scroll.pack(fill="both", expand=True, pady=(0, 10))
        
        # 强制 Canvas 的最小显示高度，但内部内容会通过 NW 锚点置顶
        self.model_scroll.canvas.config(height=250)        
        self.model_inner = self.model_scroll.scrollable_frame
         
         # 关键点：确保 model_inner 本身不会在容器内居中
        # self.model_inner.pack_propagate(False) # 如果有固定高度的话

        btn_f = ttk.Frame(left_frame, style="Side.TFrame")
        btn_f.pack(fill="x", pady=10)
        ttk.Button(btn_f, text="💾 保存/更新", style="Action.TButton", command=self.save_provider).pack(side="right", padx=5)
        ttk.Button(btn_f, text="🧹 清空表单", command=self.clear_form).pack(side="right", padx=5)
    
    def add_custom_model(self):
        """手动添加自定义模型名并置顶"""
        model_name = self.m_search_var.get().strip()
        if not model_name:
            return

        # 1. 如果已存在，将其移动到最上方并勾选
        if model_name in self.model_vars:
            for widget in self.model_inner.winfo_children():
                if widget.cget("text") == model_name:
                    widget.pack_forget()
                    widget.pack(fill="x", padx=5, side="top", anchor="nw")
            self.model_vars[model_name].set(True)
        else:
            # 2. 如果不存在，创建新的 Checkbutton 并置顶
            var = tk.BooleanVar(value=True)
            self.model_vars[model_name] = var
            self.full_model_list.insert(0, model_name)

            cb = tk.Checkbutton(self.model_inner, text=model_name, variable=var,
                                bg=GeminiBlueTheme.INPUT_BG, 
                                activebackground=GeminiBlueTheme.INPUT_BG,
                                anchor="w", pady=2)
        
            # 重新排版实现置顶
            old_widgets = self.model_inner.winfo_children()
            for w in old_widgets:
                if w != cb:
                    w.pack_forget()
        
            cb.pack(fill="x", padx=5, side="top", anchor="nw") 
            for w in old_widgets:
                if w != cb:
                    w.pack(fill="x", padx=5, side="top", anchor="nw")

        self.m_search_var.set("")
        self.update_scroll_region()


    def update_scroll_region(self):
        """动态更新模型列表的滚动区域，防止出现多余空白"""
        # 让 Tkinter 更新布局以便获取准确的尺寸
        self.model_inner.update_idletasks()
        # 获取所有子组件的高度总和
        req_height = self.model_inner.winfo_reqheight()
        # 更新 canvas 的滚动范围为实际内容高度
        self.model_scroll.canvas.configure(scrollregion=(0, 0, 0, req_height))
    
    def remove_custom_model(self):
        """删除当前搜索框中匹配的模型""" 
        model_name = self.m_search_var.get().strip()
        if not model_name:
            messagebox.showwarning("提示", "请在搜索框输入要删除的模型名称")
            return
    
        if model_name in self.model_vars:
            # 从逻辑数据中移除
            del self.model_vars[model_name]
            if model_name in self.full_model_list:
                self.full_model_list.remove(model_name)
            
        # 从界面 UI 中销毁 
            for widget in self.model_inner.winfo_children():
                if widget.cget("text") == model_name:
                    widget.destroy()
                    break
        
            self.m_search_var.set("")
            self.update_scroll_region()
        else:
            messagebox.showinfo("提示", f"未找到模型: {model_name}")
    
    
    def create_manager_tab(self):
        right_frame = ttk.Frame(self.tab_manager, padding=20)
        right_frame.pack(fill="both", expand=True)

        ttk.Label(right_frame, text="密钥管理中心", font=("微软雅黑", 14, "bold")).pack(anchor="w", pady=(0, 15))

        # 工具栏部分
        db_tools = ttk.Frame(right_frame)
        db_tools.pack(fill="x", pady=(0, 10))
        ttk.Button(db_tools, text="⚡ 测试连通性", style="Action.TButton", command=self.test_selected_key).pack(side="left", padx=3)
        ttk.Button(db_tools, text="⚡ 测试全部模型", style="Action.TButton", command=self.test_all_models).pack(side="left", padx=3)
        ttk.Button(db_tools, text="🔽 全部收起", command=self.collapse_all).pack(side="left", padx=3)
        ttk.Button(db_tools, text="🔼 全部展开", command=self.expand_all).pack(side="left", padx=3)
        ttk.Separator(db_tools, orient="vertical").pack(side="left", fill="y", padx=12)
        ttk.Button(db_tools, text="📥 导入 CSV", command=self.import_csv).pack(side="left", padx=3)
        ttk.Button(db_tools, text="📤 导出 CSV", command=self.export_csv).pack(side="left", padx=3)

        # --- 新增：滚动容器 ---
        tree_container = ttk.Frame(right_frame)
        tree_container.pack(fill="both", expand=True)

        cols = ("url", "type", "key", "note", "model_info", "create_time", "expire_time", "copy_info", "copy_code")
        self.tree = ttk.Treeview(tree_container, columns=cols, show="tree headings", height=28)

        # --- 新增：滚动条组件 ---
        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 添加标签样式
        self.tree.tag_configure("valid_model", foreground="green")
        self.tree.tag_configure("invalid_model", foreground="red")
        self.tree.tag_configure("provider", background="#f0f0f0")
        self.tree.tag_configure("key_item", background="#f9f9f9")
        
        # 布局：表格在左，滚动条在右
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.heading("#0", text="供应商 / Key")
        self.tree.heading("url", text="Base URL")
        self.tree.heading("type", text="协议")
        self.tree.heading("key", text="API Key")
        self.tree.heading("note", text="备注")
        self.tree.heading("model_info", text="模型")
        self.tree.heading("create_time", text="录入时间")
        self.tree.heading("expire_time", text="到期时间")
        self.tree.heading("copy_info", text="复制（简）")
        self.tree.heading("copy_code", text="复制代码")

        self.tree.column("#0", width=190)
        self.tree.column("url", width=200)
        self.tree.column("type", width=80)
        self.tree.column("key", width=180)
        self.tree.column("note", width=140)
        self.tree.column("model_info", width=120)
        self.tree.column("create_time", width=110)
        self.tree.column("expire_time", width=110)
        self.tree.column("copy_info", width=100, anchor="center")
        self.tree.column("copy_code", width=100, anchor="center")

        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<ButtonRelease-1>", self.on_tree_click)
        self.tree.bind("<Button-3>", self.show_context_menu)
         
         # --- 新增：鼠标滚轮绑定 ---
        self.tree.bind("<MouseWheel>", self._on_tree_mousewheel)  # Windows
        self.tree.bind("<Button-4>", self._on_tree_mousewheel)   # Linux
        self.tree.bind("<Button-5>", self._on_tree_mousewheel)   # Linux

        # 右键菜单
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="📝 修改该 Key", command=self.enter_edit_mode)
        self.context_menu.add_command(label="🔝 置顶该 Key", command=self.move_to_top)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑 删除该项", command=self.delete_selected)
    
    def _on_tree_mousewheel(self, event):
        """处理 Treeview 的鼠标滚轮事件"""
        if event.num == 4 or event.delta > 0:
            self.tree.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.tree.yview_scroll(1, "units")

    def expand_all(self):
        """全部展开：遍历所有节点并展开"""
        def _expand(item):
            self.tree.item(item, open=True)
            for child in self.tree.get_children(item):
                _expand(child)
        
        for root_item in self.tree.get_children(""):
            _expand(root_item)

    def collapse_all(self):
        for item in self.tree.get_children():
            self.tree.item(item, open=False)

    def move_to_top(self):
        sel = self.tree.selection()
        if not sel: return
        item_id = sel[0]
        if "Key #" not in self.tree.item(item_id)["text"]: return
        parent = self.tree.parent(item_id)
        if parent:
            self.tree.move(item_id, parent, 0)
            messagebox.showinfo("成功", "已置顶该 Key")

    def show_context_menu(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        
        self.tree.selection_set(item_id)
        item_data = self.tree.item(item_id)
        parent_id = self.tree.parent(item_id)
        
        # 清空旧菜单项
        self.context_menu.delete(0, tk.END)
        
        # --- 情况 1：点击的是供应商行 (最顶层) ---
        if not parent_id:
            self.context_menu.add_command(label="🔝 置顶供应商", command=lambda: self.move_item(item_id, "top"))
            self.context_menu.add_command(label="🔼 上移一位", command=lambda: self.move_item(item_id, "up"))
            self.context_menu.add_command(label="🔽 下移一位", command=lambda: self.move_item(item_id, "down"))
            self.context_menu.add_separator()
            self.context_menu.add_command(label="🗑 删除供应商", command=self.delete_selected)

        # --- 情况 2：点击的是 Key 行 (第二层) ---
        elif "Key #" in item_data["text"]:
            self.context_menu.add_command(label="📝 修改该 Key", command=self.enter_edit_mode)
            self.context_menu.add_separator()
            self.context_menu.add_command(label="🔝 置顶该 Key", command=lambda: self.move_item(item_id, "top"))
            self.context_menu.add_command(label="🔼 上移一位", command=lambda: self.move_item(item_id, "up"))
            self.context_menu.add_command(label="🔽 下移一位", command=lambda: self.move_item(item_id, "down"))
            self.context_menu.add_separator()
            self.context_menu.add_command(label="🗑 删除该 Key", command=self.delete_selected)

        # --- 情况 3：点击的是模型行 (第三层) ---
        else:
            # 获取模型名称（在 values 的第 5 列，索引为 4）
            try:
                m_name = item_data["values"][4]
            except:
                m_name = "该模型"

            self.context_menu.add_command(label="🔝 置顶该模型", command=lambda: self.move_item(item_id, "top"))
            self.context_menu.add_command(label="🔼 上移一位", command=lambda: self.move_item(item_id, "up"))
            self.context_menu.add_command(label="🔽 下移一位", command=lambda: self.move_item(item_id, "down"))
            self.context_menu.add_separator()
            # 这里的删除会自动识别出是删除模型
            self.context_menu.add_command(label=f"🗑 删除模型: {m_name}", command=self.delete_selected)

        # 弹出菜单
        self.context_menu.post(event.x_root, event.y_root)
    
    def move_item(self, item_id, direction):
        parent_id = self.tree.parent(item_id)
        item_text = self.tree.item(item_id)["text"]
        
        # --- A. 移动供应商 (最顶层) ---
        if not parent_id:
            p_names = list(self.config["providers"].keys())
            idx = p_names.index(item_text)
            new_idx = self._get_new_index(idx, len(p_names), direction)
            if new_idx == idx: return
            
            # 重新构建字典以保持顺序
            p_names.insert(new_idx, p_names.pop(idx))
            self.config["providers"] = {name: self.config["providers"][name] for name in p_names}

        # --- B. 移动 Key (第二层) ---
        elif "Key #" in item_text:
            p_name = self.tree.item(parent_id)["text"]
            keys_data = self.config["providers"][p_name]["keys_data"]
            idx = int(item_text.replace("Key #", "")) - 1
            new_idx = self._get_new_index(idx, len(keys_data), direction)
            if new_idx == idx: return
            
            keys_data.insert(new_idx, keys_data.pop(idx))

        # --- C. 移动模型 (最底层) ---
        else:
            key_id = parent_id
            p_id = self.tree.parent(key_id)
            p_name = self.tree.item(p_id)["text"]
            key_idx = int(self.tree.item(key_id)["text"].replace("Key #", "")) - 1
            
            models = self.config["providers"][p_name]["keys_data"][key_idx]["models"]
            model_name = self.tree.item(item_id)["values"][4]
            idx = models.index(model_name)
            new_idx = self._get_new_index(idx, len(models), direction)
            if new_idx == idx: return
            
            models.insert(new_idx, models.pop(idx))

        self.save_config()
        self.refresh_tree()

    def _get_new_index(self, current_idx, total_count, direction):
        if direction == "top": return 0
        if direction == "up": return max(0, current_idx - 1)
        if direction == "down": return min(total_count - 1, current_idx + 1)
        return current_idx
    
    def enter_edit_mode(self):
        sel = self.tree.selection()
        if not sel: return
        item_id = sel[0]
        item_text = self.tree.item(item_id)["text"]
        pid = self.tree.parent(item_id)
        p_name = self.tree.item(pid)["text"]
        idx = int(item_text.replace("Key #", "")) - 1

        p_data = self.config["providers"][p_name]
        k_info = p_data["keys_data"][idx]

        self.editing_context = (p_name, idx)

        self.form_title.config(text=f"正在修改：{p_name} - {item_text}", foreground=GeminiBlueTheme.ACCENT)
        self.provider_var.set(p_name)
        self.base_url_var.set(p_data.get("base_url", ""))
        self.type_var.set(p_data.get("type", "openai"))
        self.note_var.set(k_info.get("note", ""))
        self.create_time_var.set(k_info.get("create_time", datetime.now().strftime("%Y-%m-%d %H:%M")))
        self.expire_days_var.set(str(k_info.get("expire_days", 30)))

        self.keys_text.delete("1.0", tk.END)
        self.keys_text.insert("1.0", k_info["key"])

        self.update_model_list(k_info.get("models", []), pre_selected=k_info.get("models"))
        self.notebook.select(self.tab_input)

    # ====================== 保存逻辑 ======================
    def save_provider(self):
        name = self.provider_var.get().strip()
        url = self.base_url_var.get().strip()
        keys = [k.strip() for k in self.keys_text.get("1.0", tk.END).splitlines() if k.strip()]
        selected_models = [m for m, v in self.model_vars.items() if v.get()]

        if not name or not keys:
            messagebox.showwarning("提示", "供应商名称和 API Key 不能为空")
            return

        providers = self.config.setdefault("providers", {})

        create_time = self.create_time_var.get()
        #expire_days = int(self.expire_days_var.get()) if self.expire_days_var.get().isdigit() else 0
        raw_expire = self.expire_days_var.get().strip()
        expire_days = int(raw_expire) if raw_expire.isdigit() else 0

        if self.editing_context:
            old_p_name, old_idx = self.editing_context
            if old_p_name != name:
                providers[old_p_name]["keys_data"].pop(old_idx)
                if not providers[old_p_name]["keys_data"]:
                    del providers[old_p_name]

            if name not in providers:
                providers[name] = {"base_url": url, "type": self.type_var.get(), "keys_data": []}

            new_entry = {
                "key": keys[0],
                "models": selected_models,
                "note": self.note_var.get().strip(),
                "create_time": create_time,
                "expire_days": expire_days
            }

            if old_p_name == name:
                providers[name]["keys_data"][old_idx] = new_entry
            else:
                providers[name]["keys_data"].append(new_entry)

            self.editing_context = None
        else:
            if name not in providers:
                providers[name] = {"base_url": url, "type": self.type_var.get(), "keys_data": []}

            p = providers[name]
            p.update({"base_url": url, "type": self.type_var.get()})

            for k in keys:
                found = False
                for item in p["keys_data"]:
                    if item.get("key") == k:
                        item.update({
                            "models": selected_models,
                            "note": self.note_var.get().strip(),
                            "create_time": create_time,
                            "expire_days": expire_days
                        })
                        found = True
                        break
                if not found:
                    p["keys_data"].append({
                        "key": k,
                        "models": selected_models,
                        "note": self.note_var.get().strip(),
                        "create_time": create_time,
                        "expire_days": expire_days
                    })

        self.save_config()
        self.refresh_tree()
        messagebox.showinfo("成功", f"供应商「{name}」保存成功")
        self.clear_form()
        self.notebook.select(self.tab_manager)

    def clear_form(self):
        self.editing_context = None
        self.form_title.config(text="API 配置录入", foreground=GeminiBlueTheme.TEXT_ON_DARK)
        self.provider_var.set("")
        self.base_url_var.set("")
        self.note_var.set("")
        self.create_time_var.set(datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.expire_days_var.set("30")
        self.keys_text.delete("1.0", tk.END)
        self.model_vars.clear()
        self.update_model_list([])
    
    def on_preset_selected(self, event=None):
        name = self.provider_var.get()
        if name in self.presets:
            preset = self.presets[name]
            self.base_url_var.set(preset["base_url"])
            self.type_var.set(preset["type"])
            # 更新模型列表
            self.update_model_list(preset["models"], pre_selected=preset["models"])
        elif name == "自定义":
            self.base_url_var.set("")
            self.update_model_list([])
    
    # 在类初始化或全局位置生成/获取密钥
    # 注意：实际分发时，密钥可以基于机器硬件特征生成，防止直接拷贝文件到别处使用
    def get_cipher(self):
        key = b'your-secret-base64-encoded-key-here=' # 建议通过特定算法生成
        return Fernet(key)

    def save_config(self):
        try:
            # 转换为 JSON 字节流
            raw_json = json.dumps(self.config, ensure_ascii=False, indent=4).encode('utf-8')
            # 加密
            encrypted_data = cipher.encrypt(raw_json)
            with open(self.config_file, "wb") as f:
                f.write(encrypted_data)
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def load_config(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, "rb") as f:
                    encrypted_data = f.read()
                # 解密
                decrypted_data = cipher.decrypt(encrypted_data)
                self.config = json.loads(decrypted_data.decode('utf-8'))
            except:
                # 如果解密失败或文件损坏，初始化空配置
                self.config = {"providers": {}}
        else:
            self.config = {"providers": {}}

    # ====================== 管理中心逻辑 ======================
    def refresh_tree(self):
        # 1. 记录当前已经展开的节点 (以供应商名或 Key 标识名为 key)
        expanded_nodes = set()
        for item in self.tree.get_children():
            # 记录展开的供应商
            if self.tree.item(item, "open"):
                p_name = self.tree.item(item, "text")
                expanded_nodes.add(p_name)
                # 记录该供应商下展开的 Key
                for kid in self.tree.get_children(item):
                    if self.tree.item(kid, "open"):
                        k_name = self.tree.item(kid, "text")
                        expanded_nodes.add(f"{p_name}_{k_name}")

        # 2. 清空树
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 3. 重新填充数据
        for p_name, p_data in self.config.get("providers", {}).items():
            # 恢复供应商展开状态
            is_p_open = p_name in expanded_nodes
            parent = self.tree.insert("", "end", text=p_name, open=is_p_open,
                                     values=(p_data.get("base_url", ""), p_data.get("type", ""), "", "",
                                             f"{len(p_data.get('keys_data', []))} Keys", "", "", "", ""),
                                     tags=("provider",))

            for idx, k_data in enumerate(p_data.get("keys_data", [])):
                key_text = f"Key #{idx+1}"
                
                # --- 修改此处：处理过期天数的显示 ---
                days = k_data.get('expire_days', 0)
                try:
                    days_int = int(days)
                    expire_str = "永久" if days_int <= 0 else f"{days_int} 天"
                except:
                    expire_str = "永久"
                # ----------------------------------

                key_display = k_data["key"][:12] + "..." if len(k_data["key"]) > 12 else k_data["key"]
                note_display = k_data.get("note", "")[:20] + "..." if len(k_data.get("note", "")) > 20 else k_data.get("note", "")
                
                is_k_open = f"{p_name}_{key_text}" in expanded_nodes
                kid = self.tree.insert(parent, "end", text=key_text, open=is_k_open,
                                      values=("", "", key_display, note_display,
                                              f"{len(k_data.get('models', []))} 模型",
                                              k_data.get("create_time", ""), 
                                              expire_str, "", ""),
                                      tags=("key_item",)) # 使用处理后的 expire_str

                # 获取测试过的模型状态
                tested_models = k_data.get("tested_models", {})
                
                for model in k_data.get("models", []):
                    # 根据测试状态添加标识
                    model_status = tested_models.get(model)
                    if model_status is True:
                        # 绿色圆点表示模型有效
                        model_display = f"● {model}"
                        self.tree.insert(kid, "end", text="",
                                         values=("", "", "", "", model_display, "", "", "📋 复制（简）", "📝 复制代码"))
                        # 设置绿色文本
                        item_id = self.tree.get_children(kid)[-1]
                        self.tree.item(item_id, tags=("valid_model",))
                    elif model_status is False:
                        # 红色圆点表示模型无效
                        model_display = f"● {model}"
                        self.tree.insert(kid, "end", text="",
                                         values=("", "", "", "", model_display, "", "", "📋 复制（简）", "📝 复制代码"))
                        # 设置红色文本
                        item_id = self.tree.get_children(kid)[-1]
                        self.tree.item(item_id, tags=("invalid_model",))
                    else:
                        # 未检测过的模型，没有圆点
                        model_display = model
                        self.tree.insert(kid, "end", text="",
                                         values=("", "", "", "", model_display, "", "", "📋 复制（简）", "📝 复制代码"))

    def on_tree_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        
        col = self.tree.identify_column(event.x)
        item_data = self.tree.item(item_id)
        parent_id = self.tree.parent(item_id)
        
        # --- 逻辑 A：如果点击的是顶层供应商行 ---
        if not parent_id:
            p_name = item_data["text"]
            p_data = self.config["providers"].get(p_name, {})
            if col == "#1": # 点击的是 Base URL 列
                self.root.clipboard_clear()
                self.root.clipboard_append(p_data.get("base_url", ""))
            return

        # --- 逻辑 B：区分【Key 行】和【单个模型行】 ---
        item_text = item_data["text"]
        
        if not item_text:  # 这是最底层的【单个模型行】，其 text 为空
            # 这种情况下，模型名称存储在 values 的第 5 列（索引 #5）
            if col == "#5":
                # 提取模型名称，去除状态圆点
                model_display = item_data["values"][4]
                if model_display.startswith("● "):
                    model_name = model_display[2:]
                else:
                    model_name = model_display
                self.root.clipboard_clear()
                self.root.clipboard_append(model_name)
            
            # 如果在模型行点击了其他列（如复制简、复制代码），仍需定位到所属 Key
            curr_key_node = parent_id
        else:
            # 这种情况下，点击的是【Key 行】
            curr_key_node = item_id

        # 向上获取供应商名称和 Key 信息
        p_node = self.tree.parent(curr_key_node)
        p_name = self.tree.item(p_node)["text"]
        p_data = self.config["providers"][p_name]
        
        try:
            idx = int(self.tree.item(curr_key_node)["text"].replace("Key #", "")) - 1
            k_info = p_data["keys_data"][idx]
        except: return

        # --- 逻辑 C：基于列的通用操作 ---
        if col == "#1":   # Base URL
            self.root.clipboard_clear()
            self.root.clipboard_append(p_data.get("base_url", ""))
            
        elif col == "#3": # API Key
            self.root.clipboard_clear()
            self.root.clipboard_append(k_info["key"])
            
        elif col == "#5" and item_text: # 仅当点击【Key 行】的模型列时，复制全部模型
            all_models = ", ".join(k_info.get("models", []))
            self.root.clipboard_clear()
            self.root.clipboard_append(all_models)
            
        elif col == "#8": # 复制（简）
            self.copy_config_info(curr_key_node)
            
        elif col == "#9": # 复制代码
            self.show_code_popup(item_id) # 这里的代码示例需要具体的模型名，传入 item_id 正确

    def copy_cell(self, item_id, field):
        self.tree.selection_set(item_id)
        curr = item_id
        while self.tree.parent(curr) and "Key #" not in self.tree.item(curr)["text"]:
            curr = self.tree.parent(curr)

        if "Key #" not in self.tree.item(curr)["text"]:
            return

        p_name = self.tree.item(self.tree.parent(curr))["text"]
        p_data = self.config["providers"][p_name]
        idx = int(self.tree.item(curr)["text"].replace("Key #", "")) - 1
        k_info = p_data["keys_data"][idx]

        if field == "key":
            text = k_info["key"]
            tip = "API Key 已复制"
        else:
            text = p_data.get("base_url", "")
            tip = "Base URL 已复制"

        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("复制成功", tip)

    def copy_model_name(self, item_id):
        self.tree.selection_set(item_id)
        values = self.tree.item(item_id)["values"]
        if len(values) > 4 and values[4]:
            # 提取模型名称，去除状态圆点
            model_display = values[4]
            # 检查是否以圆点开头
            if model_display.startswith("● "):
                model_name = model_display[2:]
            else:
                model_name = model_display
            self.root.clipboard_clear()
            self.root.clipboard_append(model_name)
            messagebox.showinfo("复制成功", f"模型名称已复制：{model_name}")

    def copy_config_info(self, item_id):
        # 确定 Key 节点
        curr = item_id
        while self.tree.parent(curr) and "Key #" not in self.tree.item(curr)["text"]:
            curr = self.tree.parent(curr)
            
        if "Key #" not in self.tree.item(curr)["text"]:
            return

        kid = curr
        pid = self.tree.parent(kid)
        p_name = self.tree.item(pid)["text"]
        p_data = self.config["providers"][p_name]
        idx = int(self.tree.item(kid)["text"].replace("Key #", "")) - 1
        k_info = p_data["keys_data"][idx]
         # 处理过期时间文字
        raw_days = k_info.get('expire_days', 0)
        try:
            days_val = int(raw_days)
            expire_text = "永久" if days_val <= 0 else f"{days_val} 天"
        except:
            expire_text = "永久"
        
        info = f"""供应商：{p_name}
URL：{p_data.get('base_url', '')}
协议：{p_data.get('type', '')}
API Key：{k_info['key']}
备注：{k_info.get('note', '（无）')}
录入时间：{k_info.get('create_time', '')}
到期时间：{k_info.get('expire_days', 0)} 天

模型列表：
""" + "\n".join([f"  • {m}" for m in k_info.get('models', [])])

        # 执行复制
        self.root.clipboard_clear()
        self.root.clipboard_append(info)

        # 仅显示详情窗口，不再弹出“复制成功”的提示框
        pop = tk.Toplevel(self.root)
        pop.title(f"配置详情 - {p_name}")
        pop.geometry("720x580")
        txt = scrolledtext.ScrolledText(pop, font=("微软雅黑", 10), padx=15, pady=15, wrap=tk.WORD)
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", info)
        txt.config(state="disabled")

    def show_code_popup(self, item_id):
        item = self.tree.item(item_id)
        values = item.get('values', [])
        if len(values) < 5: return
        # 提取模型名称，去除状态圆点
        model_display = values[4]
        if model_display.startswith("● "):
            m_name = model_display[2:]
        else:
            m_name = model_display

        kid = self.tree.parent(item_id)
        pid = self.tree.parent(kid)
        p_name = self.tree.item(pid)["text"]
        p_data = self.config["providers"][p_name]
        idx = int(self.tree.item(kid)["text"].replace("Key #", "")) - 1
        key_val = p_data["keys_data"][idx]["key"]
        base_url = p_data.get('base_url', '')

        code = f"""import requests

url = '{base_url.rstrip('/')}/chat/completions'
headers = {{
    'Authorization': 'Bearer {key_val}',
    'Content-Type': 'application/json'
}}
payload = {{
    'model': '{m_name}',
    'messages': [{{'role': 'user', 'content': 'Hello!'}}],
    'temperature': 0.7
}}

response = requests.post(url, json=payload)
print(response.json())
"""

        pop = tk.Toplevel(self.root)
        pop.title(f"代码示例 - {m_name}")
        pop.geometry("760x560")
        txt = scrolledtext.ScrolledText(pop, font=("Consolas", 10), padx=15, pady=15)
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", code)
        txt.config(state="disabled")

    def test_selected_key(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showwarning("提示", "请选中 Key 行或模型行")

        item_id = sel[0]
        item = self.tree.item(item_id)

        if "Key #" in item["text"]:
            key_node = item_id
            model_name = None
        else:
            key_node = self.tree.parent(item_id)
            model_name = item["values"][4] if len(item["values"]) > 4 else None

        if "Key #" not in self.tree.item(key_node)["text"]:
            return messagebox.showwarning("提示", "请选中 Key 或模型行")

        p_name = self.tree.item(self.tree.parent(key_node))["text"]
        p_data = self.config["providers"][p_name]
        idx = int(self.tree.item(key_node)["text"].replace("Key #", "")) - 1
        key = p_data["keys_data"][idx]["key"]
        test_model = model_name or (p_data["keys_data"][idx].get("models", ["gpt-3.5-turbo"])[0])

        def run():
            try:
                r = requests.post(
                    f"{p_data['base_url'].rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": test_model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10},
                    timeout=15
                )
                if r.status_code == 200:
                    msg = f"✅ 有效（模型: {test_model}）"
                    # 标记模型为可用
                    if "tested_models" not in p_data["keys_data"][idx]:
                        p_data["keys_data"][idx]["tested_models"] = {}
                    p_data["keys_data"][idx]["tested_models"][test_model] = True
                    self.save_config()
                    self.refresh_tree()
                else:
                    msg = f"❌ 失败 (HTTP {r.status_code})"
                    # 标记模型为不可用
                    if "tested_models" not in p_data["keys_data"][idx]:
                        p_data["keys_data"][idx]["tested_models"] = {}
                    p_data["keys_data"][idx]["tested_models"][test_model] = False
                    self.save_config()
                    self.refresh_tree()
                self.root.after(0, lambda: messagebox.showinfo("测试结果", msg))
            except Exception as e:
                # 标记模型为不可用
                if "tested_models" not in p_data["keys_data"][idx]:
                    p_data["keys_data"][idx]["tested_models"] = {}
                p_data["keys_data"][idx]["tested_models"][test_model] = False
                self.save_config()
                self.refresh_tree()
                self.root.after(0, lambda: messagebox.showerror("测试失败", f"错误：{str(e)}"))

        threading.Thread(target=run, daemon=True).start()

    def test_all_models(self):
        """测试所有模型的连通性"""
        # 显示加载中提示
        loading_win = tk.Toplevel(self.root)
        loading_win.title("测试中")
        loading_win.geometry("400x150")
        loading_win.resizable(False, False)
        
        # 居中显示
        loading_win.update_idletasks()
        width = loading_win.winfo_width()
        height = loading_win.winfo_height()
        x = (loading_win.winfo_screenwidth() // 2) - (width // 2)
        y = (loading_win.winfo_screenheight() // 2) - (height // 2)
        loading_win.geometry(f"{width}x{height}+{x}+{y}")
        
        status_label = ttk.Label(loading_win, text="准备测试所有模型...", font=("微软雅黑", 10))
        status_label.pack(pady=20)
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(loading_win, variable=progress_var, length=300)
        progress_bar.pack(pady=10)
        
        loading_win.update()
        
        def run():
            total_models = 0
            tested_models = 0
            success_count = 0
            failure_count = 0
            
            # 计算总模型数
            for p_name, p_data in self.config.get("providers", {}).items():
                for k_data in p_data.get("keys_data", []):
                    total_models += len(k_data.get("models", []))
            
            if total_models == 0:
                self.root.after(0, lambda: messagebox.showinfo("提示", "没有模型需要测试"))
                self.root.after(0, loading_win.destroy)
                return
            
            # 测试所有模型
            for p_name, p_data in self.config.get("providers", {}).items():
                base_url = p_data.get("base_url", "").strip()
                if not base_url:
                    continue
                
                for k_idx, k_data in enumerate(p_data.get("keys_data", [])):
                    api_key = k_data.get("key", "").strip()
                    if not api_key:
                        continue
                    
                    models = k_data.get("models", [])
                    for model in models:
                        # 更新状态
                        tested_models += 1
                        progress = (tested_models / total_models) * 100
                        self.root.after(0, lambda p=progress, m=model: (
                            progress_var.set(p),
                            status_label.config(text=f"测试中：{m}")
                        ))
                        
                        try:
                            # 测试模型连通性
                            response = requests.post(
                                f"{base_url.rstrip('/')}/chat/completions",
                                headers={"Authorization": f"Bearer {api_key}"},
                                json={"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10},
                                timeout=15
                            )
                            
                            # 标记模型状态
                            if "tested_models" not in k_data:
                                k_data["tested_models"] = {}
                            
                            if response.status_code == 200:
                                k_data["tested_models"][model] = True
                                success_count += 1
                            else:
                                k_data["tested_models"][model] = False
                                failure_count += 1
                        except Exception as e:
                            # 标记模型为不可用
                            if "tested_models" not in k_data:
                                k_data["tested_models"] = {}
                            k_data["tested_models"][model] = False
                            failure_count += 1
            
            # 保存配置
            self.save_config()
            
            # 更新树显示
            self.root.after(0, self.refresh_tree)
            
            # 显示测试结果
            result_msg = f"测试完成！\n\n"
            result_msg += f"总模型数：{total_models}\n"
            result_msg += f"成功：{success_count}\n"
            result_msg += f"失败：{failure_count}"
            self.root.after(0, lambda: messagebox.showinfo("测试结果", result_msg))
            
            # 关闭加载窗口
            self.root.after(0, loading_win.destroy)
        
        threading.Thread(target=run, daemon=True).start()

    def show_toast(self, msg):
        print(msg)  # 可后续替换为状态栏

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel: return
        item_id = sel[0]
        item_text = self.tree.item(item_id)["text"]
        parent_id = self.tree.parent(item_id)
        
        # --- 逻辑 1：删除供应商 (最顶层) ---
        if not parent_id:
            if messagebox.askyesno("确认", f"确定要删除供应商「{item_text}」及其下所有 Key 吗？"):
                del self.config["providers"][item_text]

        # --- 逻辑 2：删除 Key (第二层) ---
        elif "Key #" in item_text:
            p_name = self.tree.item(parent_id)["text"]
            idx = int(item_text.replace("Key #", "")) - 1
            if messagebox.askyesno("确认", f"确定要删除 {p_name} 的该条 Key 吗？"):
                self.config["providers"][p_name]["keys_data"].pop(idx)

        # --- 逻辑 3：删除模型 (最底层/第三层) ---
        else:
            model_name = self.tree.item(item_id)["values"][4]
            key_node = parent_id
            p_node = self.tree.parent(key_node)
            p_name = self.tree.item(p_node)["text"]
            key_idx = int(self.tree.item(key_node)["text"].replace("Key #", "")) - 1
            
            if messagebox.askyesno("确认", f"确定要移除模型「{model_name}」吗？"):
                self.config["providers"][p_name]["keys_data"][key_idx]["models"].remove(model_name)

        # 统一保存并刷新
        self.save_config()
        self.refresh_tree()

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV 文件", "*.csv")])
        if not path: return
        try:
            imported_count = 0
            skipped_count = 0
            
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    p = row.get("供应商", "").strip()
                    if not p: continue
                    
                    api_key = row.get("API Key", "").strip()
                    if not api_key: continue
                    
                    if p not in self.config["providers"]:
                        self.config["providers"][p] = {"base_url": row.get("URL", ""), "type": row.get("协议", "openai"), "keys_data": []}
                    
                    # 检查是否已经存在相同的 API Key
                    existing_keys = [k["key"] for k in self.config["providers"][p]["keys_data"]]
                    if api_key in existing_keys:
                        skipped_count += 1
                        continue
                    
                    # 添加新的 API Key
                    self.config["providers"][p]["keys_data"].append({
                        "key": api_key,
                        "models": row.get("模型列表", "").split("|") if row.get("模型列表") else [],
                        "note": row.get("备注", ""),
                        "create_time": row.get("录入时间", ""),
                        "expire_days": int(row.get("到期天数", 0)) if row.get("到期天数") else 0
                    })
                    imported_count += 1
            
            self.save_config()
            self.refresh_tree()
            messagebox.showinfo("成功", f"CSV 导入完成\n成功导入: {imported_count} 个 Key\n跳过重复: {skipped_count} 个 Key")
        except Exception as e:
            messagebox.showerror("导入失败", str(e))

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV 文件", "*.csv")])
        if not path: return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["供应商", "URL", "协议", "API Key", "备注", "模型列表", "录入时间", "到期天数"])
                for p, d in self.config.get("providers", {}).items():
                    for k in d.get("keys_data", []):
                        writer.writerow([
                            p, d.get("base_url", ""), d.get("type", ""), k.get("key", ""),
                            k.get("note", ""), "|".join(k.get("models", [])),
                            k.get("create_time", ""), k.get("expire_days", 0)
                        ])
            messagebox.showinfo("成功", "CSV 导出完成")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    def update_model_list(self, models: List[str], pre_selected: List[str] = None):
    # 清除旧的复选框 
        for widget in self.model_inner.winfo_children():
            widget.destroy()
    
        self.full_model_list = models
        self.model_vars = {}
    
    # 重新填充模型
        for model in models:
            var = tk.BooleanVar(value=(pre_selected and model in pre_selected))
            self.model_vars[model] = var
            # 统一使用 side="top" 和 anchor="w" 确保从上往下排列 
            cb = tk.Checkbutton(self.model_inner, text=model, variable=var, 
                                bg=GeminiBlueTheme.INPUT_BG, 
                                activebackground=GeminiBlueTheme.INPUT_BG,
                                anchor="w")
            cb.pack(fill="x", padx=5, side="top", anchor="nw")

    def filter_models(self, *args):
        search_term = self.m_search_var.get().lower()
        for widget in self.model_inner.winfo_children():
            if search_term in widget.cget("text").lower():
                widget.pack(fill="x", padx=5)
            else:
                widget.pack_forget()

    def toggle_all_models(self, state: bool):
        for var in self.model_vars.values():
            var.set(state)

    def fetch_latest_models(self):
        """尝试抓取模型列表（对 MiniMax、豆包等不支持 /models 的厂商会友好提示）"""
        base_url = self.base_url_var.get().strip()
        keys_text = self.keys_text.get("1.0", tk.END).strip()
        
        if not base_url or not keys_text:
            messagebox.showwarning("提示", "请先填写 Base URL 和至少一个 API Key")
            return

        # 取第一个 Key 进行测试
        key = [k.strip() for k in keys_text.splitlines() if k.strip()][0]

        # 显示加载中提示
        loading_win = tk.Toplevel(self.root)
        loading_win.title("加载中")
        loading_win.geometry("300x100")
        loading_win.resizable(False, False)
        
        # 居中显示
        loading_win.update_idletasks()
        width = loading_win.winfo_width()
        height = loading_win.winfo_height()
        x = (loading_win.winfo_screenwidth() // 2) - (width // 2)
        y = (loading_win.winfo_screenheight() // 2) - (height // 2)
        loading_win.geometry(f"{width}x{height}+{x}+{y}")
        
        ttk.Label(loading_win, text="正在获取最新模型列表...", font=("微软雅黑", 10)).pack(pady=20)
        loading_win.update()

        try:
            response = requests.get(
                f"{base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {key}"},
                timeout=12
            )

            if response.status_code == 200:
                data = response.json()
                models = [m.get("id") for m in data.get("data", []) if m.get("id")]
                if models:
                    # 清空现有模型列表
                    self.model_vars.clear()
                    # 更新模型列表
                    self.update_model_list(models, pre_selected=models)
                    messagebox.showinfo("抓取成功", f"成功获取 {len(models)} 个模型")
                    return
                else:
                    messagebox.showinfo("结果", "接口返回成功，但没有模型数据")
            else:
                messagebox.showwarning("抓取失败",
                    f"HTTP {response.status_code}\n\n"
                    f"该模型厂商目前不支持自动获取模型列表。\n"
                    f"建议直接在下方手动添加模型，或使用预设。")
        except Exception as e:
            messagebox.showerror("抓取失败",
                f"请求出错：{str(e)}\n\n"
                f"提示：该模型厂商暂不支持 /v1/models 接口，推荐手动添加模型。")
        finally:
            loading_win.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AIKeyManager(root)
    root.mainloop()