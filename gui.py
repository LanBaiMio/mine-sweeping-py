import os
import sys
import sqlite3
import hashlib
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
import threading
import queue
import subprocess
from openai import OpenAI
from config import ROWS, COLS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class Database:
    def __init__(self, db_name='mine_sweeping.db'):
        self.conn = sqlite3.connect(db_name)
        self._create_tables()
    
    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                auto_login INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                detail TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN auto_login INTEGER DEFAULT 0')
            self.conn.commit()
        except sqlite3.OperationalError:
            pass
        
        self.conn.commit()
    
    def register(self, username, password, auto_login=False):
        cursor = self.conn.cursor()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        try:
            cursor.execute('''
                INSERT INTO users (username, password_hash, created_at, auto_login)
                VALUES (?, ?, ?, ?)
            ''', (username, password_hash, datetime.now().isoformat(), 1 if auto_login else 0))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def set_auto_login(self, user_id, auto_login):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET auto_login = ? WHERE id = ?', (1 if auto_login else 0, user_id))
        self.conn.commit()
    
    def get_auto_login_user(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, username, password_hash FROM users WHERE auto_login = 1 LIMIT 1')
        return cursor.fetchone()
    
    def login(self, username, password):
        cursor = self.conn.cursor()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute('''
            SELECT id, username, created_at FROM users
            WHERE username = ? AND password_hash = ?
        ''', (username, password_hash))
        return cursor.fetchone()
    
    def add_operation(self, user_id, action, detail=''):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO operations (user_id, action, detail, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (user_id, action, detail, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_operations(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT action, detail, timestamp FROM operations
            WHERE user_id = ? ORDER BY timestamp DESC
        ''', (user_id,))
        return cursor.fetchall()
    
    def get_user_stats(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM operations WHERE user_id = ?', (user_id,))
        count = cursor.fetchone()[0]
        return count

class LoginWindow:
    def __init__(self, root, on_login):
        self.root = root
        self.root.title('扫雷AI助手 - 登录')
        self.root.geometry('400x350')
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.on_login = on_login
        self.db = Database()
        
        self._setup_ui()
    
    def _setup_ui(self):
        frame = ttk.Frame(self.root, padding=30)
        frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(frame, text='💣 扫雷AI助手', font=('Segoe UI', 24, 'bold'))
        title_label.pack(pady=(0, 30))
        
        ttk.Label(frame, text='用户名').pack(anchor=tk.W)
        self.username_entry = ttk.Entry(frame, font=('Segoe UI', 12), width=30)
        self.username_entry.pack(pady=(5, 15))
        
        ttk.Label(frame, text='密码').pack(anchor=tk.W)
        self.password_entry = ttk.Entry(frame, show='*', font=('Segoe UI', 12), width=30)
        self.password_entry.pack(pady=(5, 20))
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text='登录', command=self._login).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ttk.Button(button_frame, text='注册', command=self._show_register).pack(side=tk.RIGHT, fill=tk.X, expand=True)
    
    def _login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showwarning('提示', '请输入用户名和密码')
            return
        
        user = self.db.login(username, password)
        if user:
            from datetime import datetime
            with open('log.txt', 'a', encoding='utf-8') as f:
                f.write(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] 用户登录 - {username}\n')
            self.root.destroy()
            self.on_login(user)
        else:
            messagebox.showerror('错误', '用户名或密码错误')
    
    def _show_register(self):
        self.root.withdraw()
        register_root = tk.Tk()
        RegisterWindow(register_root, self.root)

class RegisterWindow:
    def __init__(self, root, parent_root):
        self.root = root
        self.parent_root = parent_root
        self.root.title('扫雷AI助手 - 注册')
        self.root.geometry('400x350')
        self.root.resizable(False, False)
        self.db = Database()
        
        self._setup_ui()
    
    def _setup_ui(self):
        frame = ttk.Frame(self.root, padding=30)
        frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(frame, text='🚀 用户注册', font=('Segoe UI', 20, 'bold'))
        title_label.pack(pady=(0, 30))
        
        ttk.Label(frame, text='用户名').pack(anchor=tk.W)
        self.username_entry = ttk.Entry(frame, font=('Segoe UI', 12), width=30)
        self.username_entry.pack(pady=(5, 15))
        
        ttk.Label(frame, text='密码').pack(anchor=tk.W)
        self.password_entry = ttk.Entry(frame, show='*', font=('Segoe UI', 12), width=30)
        self.password_entry.pack(pady=(5, 15))
        
        self.auto_login_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text='注册后自动登录', variable=self.auto_login_var).pack(anchor=tk.W, pady=(0, 20))
        
        ttk.Button(frame, text='注册', command=self._register).pack(fill=tk.X)
        ttk.Button(frame, text='返回登录', command=self._back).pack(fill=tk.X, pady=(10, 0))
    
    def _register(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showwarning('提示', '请输入用户名和密码')
            return
        
        if len(username) < 3:
            messagebox.showwarning('提示', '用户名至少需要3个字符')
            return
        
        if len(password) < 6:
            messagebox.showwarning('提示', '密码至少需要6个字符')
            return
        
        if self.db.register(username, password, self.auto_login_var.get()):
            messagebox.showinfo('成功', '注册成功！')
            if self.auto_login_var.get():
                from datetime import datetime
                with open('log.txt', 'a', encoding='utf-8') as f:
                    f.write(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] 用户登录 - {username}\n')
                user = self.db.login(username, password)
                if user:
                    self.root.destroy()
                    self.parent_root.destroy()
                    main_root = tk.Tk()
                    MainWindow(main_root, user)
            else:
                self._back()
        else:
            messagebox.showerror('错误', '用户名已存在')
    
    def _back(self):
        self.root.destroy()
        self.parent_root.deiconify()

class MainWindow:
    def __init__(self, root, user):
        self.root = root
        self.user = user
        self.root.title(f'扫雷AI助手 - {user[1]}')
        self.root.geometry('800x600')
        self.root.minsize(600, 450)
        self.root.attributes('-topmost', True)
        
        self.db = Database()
        self.log_queue = queue.Queue()
        
        self._setup_ui()
        self._start_log_processor()
    
    def _setup_ui(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        self._create_home_tab()
        self._create_history_tab()
        self._create_about_tab()
        self._create_settings_tab()
        
        self.root.bind('<MouseWheel>', self._handle_mouse_wheel)
    
    def _handle_mouse_wheel(self, e):
        current_tab = self.notebook.index(self.notebook.select())
        about_index = self.notebook.index(self.about_frame)
        settings_index = self.notebook.index(self.settings_frame)
        
        if current_tab == about_index and hasattr(self, 'about_canvas'):
            self.about_canvas.yview_scroll(int(-1*(e.delta/120)), 'units')
        elif current_tab == settings_index and hasattr(self, 'settings_canvas'):
            self.settings_canvas.yview_scroll(int(-1*(e.delta/120)), 'units')
    
    def _create_home_tab(self):
        home_frame = ttk.Frame(self.notebook)
        self.notebook.add(home_frame, text='主页')
        
        header_frame = ttk.Frame(home_frame, padding=20)
        header_frame.pack(fill=tk.X)
        
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(fill=tk.X)
        
        ttk.Label(title_frame, text='💣 扫雷AI助手', font=('Segoe UI', 20, 'bold')).pack(side=tk.LEFT)
        
        self.minesweeper_link = ttk.Label(title_frame, text='🔗 在线扫雷', font=('Segoe UI', 11), foreground='#2E86DE', cursor='hand2')
        self.minesweeper_link.pack(side=tk.RIGHT)
        self.minesweeper_link.bind('<Button-1>', lambda e: self._open_minesweeper())
        
        ttk.Label(header_frame, text=f'欢迎回来，{self.user[1]}！', font=('Segoe UI', 12)).pack(anchor=tk.W, pady=(5, 0))
        
        self.saolei_running = False
        
        control_frame = ttk.Frame(home_frame, padding=20)
        control_frame.pack(fill=tk.X)
        
        ttk.Label(control_frame, text='启动控制', font=('Segoe UI', 14, 'bold')).pack(anchor=tk.W, pady=(0, 15))
        
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X)
        
        self.start_button = ttk.Button(button_frame, text='▶ 启动扫雷程序', command=self._toggle_saolei, style='Accent.TButton')
        self.start_button.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        
        self.stop_button = ttk.Button(button_frame, text='⏹ 停止程序', command=self._stop_saolei, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        log_frame = ttk.Frame(home_frame, padding=20)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(log_frame, text='操作日志', font=('Segoe UI', 14, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, font=('Consolas', 12))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.insert(tk.END, '欢迎使用本程序\n')
        self.log_text.insert(tk.END, '-' * 60 + '\n')
    
    def _open_minesweeper(self):
        import webbrowser
        webbrowser.open('https://www.minesweeper.cn/')
    
    def _create_history_tab(self):
        history_frame = ttk.Frame(self.notebook)
        self.notebook.add(history_frame, text='历史记录')
        
        header_frame = ttk.Frame(history_frame, padding=20)
        header_frame.pack(fill=tk.X)
        
        header_inner = ttk.Frame(header_frame)
        header_inner.pack(fill=tk.X)
        
        ttk.Label(header_inner, text='� 日志记录', font=('Segoe UI', 18, 'bold')).pack(side=tk.LEFT)
        
        refresh_btn = ttk.Button(header_inner, text='🔄 刷新日志', command=self._refresh_history)
        refresh_btn.pack(side=tk.RIGHT)
        
        log_frame = ttk.Frame(history_frame, padding=(20, 0, 20, 20))
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text_widget = scrolledtext.ScrolledText(log_frame, font=('Consolas', 11))
        self.log_text_widget.pack(fill=tk.BOTH, expand=True)
        
        self._refresh_history()
    
    def _create_about_tab(self):
        about_frame = ttk.Frame(self.notebook)
        self.notebook.add(about_frame, text='关于')
        
        canvas = tk.Canvas(about_frame)
        scrollbar = ttk.Scrollbar(about_frame, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        
        scroll_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=scroll_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.about_canvas = canvas
        self.about_frame = about_frame
        
        content = '''📋 项目背景

扫雷AI助手是一个基于深度学习的自动扫雷系统，旨在帮助玩家自动完成扫雷游戏。
项目使用卷积神经网络(CNN)来识别屏幕上的扫雷棋盘，结合逻辑推理算法实现自动点击和标记。

📝 使用步骤

1. 在设置中配置扫雷游戏区域的坐标参数：
   - 将鼠标先后放在游戏区域最左上角和最右下角，点击1获取坐标按钮，分别获取游戏区域的左上角和右下角坐标。以便进行CNN识别。
2. 点击"保存"按钮保存配置。
3. （可选）在设置中配置大模型API参数。
4. 主页点击右上角链接打开扫雷游戏网页，点击启动扫雷程序按钮。
5. 点击C键和S键确认CNN识别正确。
6. 点击B键开始AI自动扫雷；或者手动进行游戏，当遇到不确定的情况时，按A键执行一次推理。
7. （可选）按L键调用大模型api求解，当前局势保存在situation.txt文件中。
8. （可选）按R键将当前局面截图，CNN识别对应状态并将对应结果保存到文件夹中供强化CNN训练。
9. 按Q键结束AI扫雷程序。

✅ 项目功能

- 自动识别扫雷棋盘上的数字、未翻开的格子、旗子、地雷等。
- 基于逻辑推理算法，自动点击和标记地雷。
- 支持自定义扫雷游戏区域的坐标参数。
- 可选的大模型API调用，用于求解扫雷局面。
- 支持死局随机点击

💻 开发环境及依赖

- Trae
Python==3.10

numpy==1.26.4
matplotlib==3.8.4
Pillow==10.2.0
pyautogui==0.9.54
pynput==1.7.6
requests==2.31.0
openai==2.45.0
tensorflow==2.15.0
keras==2.15.0

🧠 模型来源

项目使用的CNN模型 recognize_new 是通过自定义训练数据集训练得到的。
训练数据包含扫雷游戏中各种状态的格子图像（数字0-8、未翻开格子、旗子、地雷等），
使用TensorFlow和Keras框架构建卷积神经网络进行训练。

'''
        
        ttk.Label(scroll_frame, text=content, font=('Segoe UI', 11), justify=tk.LEFT, padding=20).pack(anchor=tk.W)
    
    def _create_settings_tab(self):
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text='设置')
        
        canvas = tk.Canvas(settings_frame)
        scrollbar = ttk.Scrollbar(settings_frame, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        
        scroll_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=scroll_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.settings_canvas = canvas
        self.settings_frame = settings_frame
        
        ttk.Label(scroll_frame, text='用户信息', font=('Segoe UI', 14, 'bold'), padding=(20, 10, 20, 5)).pack(anchor=tk.W)
        info_frame = ttk.Frame(scroll_frame, padding=(30, 0, 20, 15))
        info_frame.pack(fill=tk.X)
        
        ttk.Label(info_frame, text=f'用户名：{self.user[1]}', font=('Segoe UI', 12)).pack(anchor=tk.W)
        ttk.Label(info_frame, text=f'注册时间：{self.user[2]}', font=('Segoe UI', 12)).pack(anchor=tk.W)
        
        ttk.Label(scroll_frame, text='界面设置', font=('Segoe UI', 14, 'bold'), padding=(20, 10, 20, 5)).pack(anchor=tk.W)
        ui_frame = ttk.Frame(scroll_frame, padding=(30, 0, 20, 15))
        ui_frame.pack(fill=tk.X)
        
        self.topmost_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ui_frame, text='界面始终置顶', variable=self.topmost_var, command=self._toggle_topmost).pack(anchor=tk.W)
        
        ttk.Label(scroll_frame, text='游戏设置', font=('Segoe UI', 14, 'bold'), padding=(20, 10, 20, 5)).pack(anchor=tk.W)
        game_frame = ttk.Frame(scroll_frame, padding=(30, 0, 20, 15))
        game_frame.pack(fill=tk.X)
        
        from config import BG_REGION_EASY, BG_REGION_MEDIUM, BG_REGION_HARD, BG_REGION_CUSTOM
        
        def region_to_str(region):
            if region and len(region) == 4:
                return ', '.join(map(str, region))
            return ''
        
        from config import CURRENT_MODE
        
        mode_list = ['基础模式', '中级模式', '专家模式', '自定义模式']
        current_mode_name = mode_list[CURRENT_MODE] if 0 <= CURRENT_MODE < len(mode_list) else '基础模式'
        
        ttk.Label(game_frame, text='选择模式').pack(anchor=tk.W)
        self.mode_var = tk.StringVar(value=current_mode_name)
        mode_combo = ttk.Combobox(game_frame, textvariable=self.mode_var, values=mode_list, state='readonly', width=57)
        mode_combo.pack(pady=(3, 8))
        
        ttk.Label(game_frame, text='坐标获取工具', font=('Segoe UI', 11, 'bold')).pack(anchor=tk.W, pady=(15, 5))
        coord_btn_frame = ttk.Frame(game_frame)
        coord_btn_frame.pack(fill=tk.X)
        
        self.coords_running = False
        self.start_coords_btn = ttk.Button(coord_btn_frame, text='▶ 启动坐标获取工具', command=self._toggle_get_coords, style='Accent.TButton')
        self.start_coords_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.stop_coords_btn = ttk.Button(coord_btn_frame, text='⏹ 停止工具', command=self._stop_get_coords, state=tk.DISABLED)
        self.stop_coords_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(game_frame, text='  使用说明：启动工具后，将鼠标移动到游戏区域左上角按"1"，再移动到右下角按"1"', font=('Segoe UI', 10), foreground='#666').pack(anchor=tk.W, pady=(3, 0))
        
        ttk.Label(game_frame, text='基础模式 BG_REGION (x, y, w, h)').pack(anchor=tk.W, pady=(15, 0))
        self.easy_region_var = tk.StringVar(value=region_to_str(BG_REGION_EASY))
        ttk.Entry(game_frame, textvariable=self.easy_region_var, width=60).pack(pady=(3, 8))
        ttk.Label(game_frame, text='  基础模式说明：9行9列，初次使用必须设置', font=('Segoe UI', 10), foreground='#666').pack(anchor=tk.W)
        
        ttk.Label(game_frame, text='中级模式 BG_REGION (x, y, w, h)').pack(anchor=tk.W, pady=(10, 0))
        self.medium_region_var = tk.StringVar(value=region_to_str(BG_REGION_MEDIUM))
        ttk.Entry(game_frame, textvariable=self.medium_region_var, width=60).pack(pady=(3, 8))
        ttk.Label(game_frame, text='  中级模式说明：16行16列，初次使用必须设置', font=('Segoe UI', 10), foreground='#666').pack(anchor=tk.W)
        
        ttk.Label(game_frame, text='专家模式 BG_REGION (x, y, w, h)').pack(anchor=tk.W, pady=(10, 0))
        self.hard_region_var = tk.StringVar(value=region_to_str(BG_REGION_HARD))
        ttk.Entry(game_frame, textvariable=self.hard_region_var, width=60).pack(pady=(3, 8))
        ttk.Label(game_frame, text='  专家模式说明：16行30列，初次使用必须设置', font=('Segoe UI', 10), foreground='#666').pack(anchor=tk.W)
        
        ttk.Label(game_frame, text='自定义模式 BG_REGION (x, y, w, h)').pack(anchor=tk.W, pady=(10, 0))
        self.custom_region_var = tk.StringVar(value=region_to_str(BG_REGION_CUSTOM))
        ttk.Entry(game_frame, textvariable=self.custom_region_var, width=60).pack(pady=(3, 8))
        ttk.Label(game_frame, text='  自定义模式说明：可选设置，用于非标准尺寸棋盘', font=('Segoe UI', 10), foreground='#666').pack(anchor=tk.W)
        
        ttk.Label(scroll_frame, text='API设置', font=('Segoe UI', 14, 'bold'), padding=(20, 10, 20, 5)).pack(anchor=tk.W)
        api_frame = ttk.Frame(scroll_frame, padding=(30, 0, 20, 15))
        api_frame.pack(fill=tk.X)
        
        from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL_NAME
        
        ttk.Label(api_frame, text='LLM API地址').pack(anchor=tk.W)
        self.api_base_var = tk.StringVar(value=LLM_API_BASE)
        ttk.Entry(api_frame, textvariable=self.api_base_var, width=50).pack(pady=(5, 10))
        
        ttk.Label(api_frame, text='API密钥').pack(anchor=tk.W)
        self.api_key_var = tk.StringVar(value=LLM_API_KEY)
        ttk.Entry(api_frame, textvariable=self.api_key_var, show='*', width=50).pack(pady=(5, 10))
        
        ttk.Label(api_frame, text='模型名称').pack(anchor=tk.W)
        self.model_name_var = tk.StringVar(value=LLM_MODEL_NAME)
        ttk.Entry(api_frame, textvariable=self.model_name_var, width=50).pack(pady=(5, 15))
        
        ttk.Button(scroll_frame, text='保存设置', command=self._save_settings, padding=(20, 0)).pack(padx=20, pady=10)
    
    def _refresh_history(self):
        if hasattr(self, 'log_text_widget'):
            self.log_text_widget.delete(1.0, tk.END)
            try:
                with open('log.txt', 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.log_text_widget.insert(tk.END, content)
                    self.log_text_widget.see(tk.END)
            except FileNotFoundError:
                pass
    
    def _save_settings(self):
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.py')
        
        def str_to_region(s):
            if not s.strip():
                return '()'
            try:
                parts = [int(x.strip()) for x in s.split(',')]
                if len(parts) == 4:
                    return f'({parts[0]}, {parts[1]}, {parts[2]}, {parts[3]})'
            except ValueError:
                pass
            return '()'
        
        easy_region = str_to_region(self.easy_region_var.get())
        medium_region = str_to_region(self.medium_region_var.get())
        hard_region = str_to_region(self.hard_region_var.get())
        custom_region = str_to_region(self.custom_region_var.get())
        
        api_base = self.api_base_var.get().strip()
        api_key = self.api_key_var.get().strip()
        model_name = self.model_name_var.get().strip()
        
        mode_map = {'基础模式': 0, '中级模式': 1, '专家模式': 2, '自定义模式': 3}
        current_mode = mode_map.get(self.mode_var.get(), 0)
        
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content = content.replace(
            f'CURRENT_MODE = {self._get_int_value(content, "CURRENT_MODE")}',
            f'CURRENT_MODE = {current_mode}'
        )
        
        content = content.replace(
            f'BG_REGION_EASY = {self._get_region_str(content, "BG_REGION_EASY")}',
            f'BG_REGION_EASY = {easy_region}'
        )
        content = content.replace(
            f'BG_REGION_MEDIUM = {self._get_region_str(content, "BG_REGION_MEDIUM")}',
            f'BG_REGION_MEDIUM = {medium_region}'
        )
        content = content.replace(
            f'BG_REGION_HARD = {self._get_region_str(content, "BG_REGION_HARD")}',
            f'BG_REGION_HARD = {hard_region}'
        )
        content = content.replace(
            f'BG_REGION_CUSTOM = {self._get_region_str(content, "BG_REGION_CUSTOM")}',
            f'BG_REGION_CUSTOM = {custom_region}'
        )
        
        content = content.replace(
            f'LLM_API_BASE = {self._get_quoted_str(content, "LLM_API_BASE")}',
            f'LLM_API_BASE = \'{api_base}\''
        )
        content = content.replace(
            f'LLM_API_KEY = {self._get_quoted_str(content, "LLM_API_KEY")}',
            f'LLM_API_KEY = \'{api_key}\''
        )
        content = content.replace(
            f'LLM_MODEL_NAME = {self._get_quoted_str(content, "LLM_MODEL_NAME")}',
            f'LLM_MODEL_NAME = \'{model_name}\''
        )
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        messagebox.showinfo('成功', '设置已保存')
    
    def _get_region_str(self, content, var_name):
        import re
        match = re.search(f'{var_name} = \\(([^)]*)\\)', content)
        if match:
            return f'({match.group(1)})'
        return '()'
    
    def _get_int_value(self, content, var_name):
        import re
        match = re.search(f'{var_name} = (\\d+)', content)
        if match:
            return match.group(1)
        return '0'
    
    def _parse_and_set_region(self, line):
        import re
        match = re.search(r'BG_REGION = \((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)', line)
        if match:
            x, y, w, h = match.groups()
            region_str = f'{x}, {y}, {w}, {h}'
            
            mode = self.mode_var.get()
            if mode == '基础模式':
                self.root.after(0, lambda: self.easy_region_var.set(region_str))
            elif mode == '中级模式':
                self.root.after(0, lambda: self.medium_region_var.set(region_str))
            elif mode == '专家模式':
                self.root.after(0, lambda: self.hard_region_var.set(region_str))
            elif mode == '自定义模式':
                self.root.after(0, lambda: self.custom_region_var.set(region_str))
            
            self._log(f'已自动填入{mode}的BG_REGION')
    
    def _get_quoted_str(self, content, var_name):
        import re
        match = re.search(f'{var_name} = [\'"]([^\'"]*)[\'"]', content)
        if match:
            return f'\'{match.group(1)}\''
        return "''"
    
    def _toggle_topmost(self):
        self.root.attributes('-topmost', self.topmost_var.get())
    
    def _log(self, message):
        self.log_queue.put(message)
        from datetime import datetime
        log_entry = f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] 操作日志 - {message}\n'
        with open('log.txt', 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        if hasattr(self, 'log_text_widget'):
            self.log_text_widget.insert(tk.END, log_entry)
            self.log_text_widget.see(tk.END)
    
    def _start_log_processor(self):
        def process():
            while True:
                try:
                    message = self.log_queue.get(timeout=1)
                    self.log_text.insert(tk.END, message + '\n')
                    self.log_text.see(tk.END)
                except queue.Empty:
                    pass
        
        threading.Thread(target=process, daemon=True).start()
    
    def _run_saolei_func(self, func_name):
        def run():
            import sys
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            log_queue = self.log_queue
            class LogRedirector:
                def write(self, text):
                    if text.strip():
                        log_queue.put(text.strip())
                def flush(self):
                    pass
            sys.stdout = LogRedirector()
            sys.stderr = LogRedirector()
            
            try:
                import saolei
                if func_name == 'game_once':
                    saolei.game_once()
                    self._log('单次推理完成')
                    self.db.add_operation(self.user[0], '单次推理')
                elif func_name == 'game_all':
                    self._log('开始自动游戏...')
                    saolei.game_all()
                    self._log('自动游戏结束')
                    self.db.add_operation(self.user[0], '自动游戏')
                elif func_name == 'save_and_analyze':
                    board = saolei.get_cnn_board(saolei.model)
                    with open('situation.txt', 'w') as f:
                        for row in board:
                            f.write(' '.join(map(str, row)) + '\n')
                    self._log('预测结果已保存到situation.txt')
                    self.db.add_operation(self.user[0], '保存分析', '已保存到situation.txt')
                    
                    from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL_NAME, ROWS, COLS
                    if LLM_API_BASE and LLM_API_KEY and LLM_MODEL_NAME:
                        try:
                            board_str = '\n'.join(' '.join(map(str, row)) for row in board)
                            prompt = f"""这是一个扫雷游戏的棋盘状态，共{ROWS}行{COLS}列。
数字含义：
- -2：未翻开的格子
- -1：标记为旗子的格子
- 0-8：周围地雷数量
- 9：已翻开的地雷
{board_str}
请分析这个扫雷局面，给出可以确定是地雷的格子位置（行号,列号，从1开始）"""

                            client = OpenAI(api_key=os.getenv(f"{LLM_API_KEY}"),base_url=LLM_API_BASE)
                            completion = client.chat.completions.create(
                            model=LLM_MODEL_NAME,
                            messages=[f'{{"role": "user", "content": "{prompt}"}}'])
                            self._log(completion.choices[0].message.content)
                        except Exception as e:
                            self._log(f'调用大模型失败：{e}')
                else:
                    self._log('未配置大模型API参数，请在config.py中填写LLM_API_BASE、LLM_API_KEY和LLM_MODEL_NAME')
            except Exception as e:
                self._log(f'调用大模型失败：{e}')
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
        
        threading.Thread(target=run, daemon=True).start()
    
    def _game_once(self):
        self._run_saolei_func('game_once')
    
    def _game_all(self):
        self._run_saolei_func('game_all')
    
    def _save_and_analyze(self):
        self._run_saolei_func('save_and_analyze')
    
    def _toggle_saolei(self):
        if not self.saolei_running:
            self._start_saolei()
        else:
            self._stop_saolei()
    
    def _start_saolei(self):
        self.saolei_running = True
        self.start_button.config(text='⏹ 停止运行')
        self.stop_button.config(state=tk.NORMAL)
        self._log('正在启动扫雷程序...')
        
        import subprocess
        import sys
        import os
        
        saolei_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saolei.py')
        self.saolei_process = subprocess.Popen(
            [sys.executable, saolei_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        def read_stdout():
            while self.saolei_process.poll() is None:
                try:
                    line = self.saolei_process.stdout.readline()
                    if line:
                        self._log(line.strip())
                except Exception:
                    break
        
        def read_stderr():
            while self.saolei_process.poll() is None:
                try:
                    line = self.saolei_process.stderr.readline()
                    if line:
                        self._log(line.strip())
                except Exception:
                    break
        
        def wait_process():
            self.saolei_process.wait()
            
            remaining_out = self.saolei_process.stdout.read()
            if remaining_out:
                for line in remaining_out.strip().split('\n'):
                    self._log(line)
            
            remaining_err = self.saolei_process.stderr.read()
            if remaining_err:
                for line in remaining_err.strip().split('\n'):
                    self._log(line)
            
            self.saolei_running = False
            self.start_button.config(text='▶ 启动扫雷程序')
            self.stop_button.config(state=tk.DISABLED)
            self._log('扫雷程序已停止')
        
        threading.Thread(target=read_stdout, daemon=True).start()
        threading.Thread(target=read_stderr, daemon=True).start()
        threading.Thread(target=wait_process, daemon=True).start()
    
    def _stop_saolei(self):
        if hasattr(self, 'saolei_process') and self.saolei_process.poll() is None:
            self.saolei_process.terminate()
            self.saolei_process.wait()
            self._log('扫雷程序已强制停止')
        
        self.saolei_running = False
        self.start_button.config(text='▶ 启动扫雷程序')
        self.stop_button.config(state=tk.DISABLED)
    
    def _toggle_get_coords(self):
        if not self.coords_running:
            self._start_get_coords()
        else:
            self._stop_get_coords()
    
    def _start_get_coords(self):
        self.coords_running = True
        self.start_coords_btn.config(text='⏹ 停止坐标获取工具')
        self.stop_coords_btn.config(state=tk.NORMAL)
        self._log('正在启动坐标获取工具...')
        

        
        coords_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'get_coords.py')
        self.coords_process = subprocess.Popen(
            [sys.executable, coords_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        def read_coords_output():
            while self.coords_process.poll() is None:
                try:
                    line = self.coords_process.stdout.readline()
                    if line:
                        self._log(line.strip())
                        self._parse_and_set_region(line)
                except Exception:
                    break
            
            remaining_out = self.coords_process.stdout.read()
            if remaining_out:
                for line in remaining_out.strip().split('\n'):
                    self._log(line)
                    self._parse_and_set_region(line)
            
            remaining_err = self.coords_process.stderr.read()
            if remaining_err:
                for line in remaining_err.strip().split('\n'):
                    self._log(line)
            
            self.coords_running = False
            self.start_coords_btn.config(text='▶ 启动坐标获取工具')
            self.stop_coords_btn.config(state=tk.DISABLED)
            self._log('坐标获取工具已停止')
        
        threading.Thread(target=read_coords_output, daemon=True).start()
    
    def _stop_get_coords(self):
        if hasattr(self, 'coords_process') and self.coords_process.poll() is None:
            self.coords_process.terminate()
            self.coords_process.wait()
            self._log('坐标获取工具已强制停止')
        
        self.coords_running = False
        self.start_coords_btn.config(text='▶ 启动坐标获取工具')
        self.stop_coords_btn.config(state=tk.DISABLED)

def main():
    db = Database()
    auto_user = db.get_auto_login_user()
    
    if auto_user:
        from datetime import datetime
        with open('log.txt', 'a', encoding='utf-8') as f:
            f.write(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] 用户登录 - {auto_user[1]}\n')
        root = tk.Tk()
        app = MainWindow(root, auto_user)
        root.mainloop()
        return
    
    def on_login(user):
        root = tk.Tk()
        app = MainWindow(root, user)
        root.mainloop()
    
    login_root = tk.Tk()
    login_app = LoginWindow(login_root, on_login)
    login_root.mainloop()

if __name__ == '__main__':
    main()