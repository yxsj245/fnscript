#!/usr/bin/env python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button, Label, Select, Input
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen, ModalScreen
import os
import subprocess
import asyncio

# 定义颜色常量（保留以兼容原始代码）
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

# 工具函数
def clear_screen():
    """清空终端屏幕"""
    os.system('clear' if os.name == 'posix' else 'cls')

def run_command(command, shell=False):
    """执行命令并返回结果"""
    result = {
        'status_code': 0,
        'stdout': '',
        'stderr': ''
    }

    try:
        if shell:
            process_result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
        else:
            process_result = subprocess.run(command, check=True, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
            
        result['stdout'] = process_result.stdout.decode()
        return result
    except subprocess.CalledProcessError as e:
        result['status_code'] = 1
        result['stderr'] = e.stderr.decode()
        return result

def get_network_interfaces():
    """获取设备的物理网卡名称（支持多种常见命名格式）"""
    result = run_command("ls /sys/class/net", shell=True)
    if result['status_code'] != 0:
        return []
    
    all_interfaces = result['stdout'].strip().split("\n")
    # 过滤出物理网卡，支持多种命名格式
    # ens*: 新版内核根据设备名称和位置命名
    # enp*: 新版内核根据PCI总线位置命名
    # eth*: 传统命名
    # em*: 部分服务器命名
    physical_interfaces = []
    for iface in all_interfaces:
        # 排除回环接口和虚拟接口
        if (iface.startswith("ens") or 
            iface.startswith("enp") or 
            iface.startswith("eth") or 
            iface.startswith("em")):
            # 额外验证这是物理接口
            if os.path.exists(f"/sys/class/net/{iface}/device"):
                physical_interfaces.append(iface)
    
    return physical_interfaces

def check_wol_status(interface):
    """检查指定网卡的 Wake-on-LAN 状态"""
    result = run_command(f"ethtool {interface}", shell=True)
    if result['status_code'] != 0:
        return "未知"
    
    # 打印完整的ethtool输出以便诊断
    print(f"ethtool {interface} 输出:\n{result['stdout']}")
    
    wol_status = "未知"
    for line in result['stdout'].split("\n"):
        if "Wake-on" in line:
            try:
                wol_status = line.split(":")[1].strip()
                print(f"识别到Wake-on状态值: '{wol_status}'")
            except Exception as e:
                print(f"解析Wake-on状态时出错: {str(e)}")
    
    return wol_status

# 确认对话框
class ConfirmDialog(ModalScreen):
    """确认对话框"""
    
    def __init__(self, message: str, action_callback=None):
        super().__init__()
        self.message = message
        self.action_callback = action_callback
    
    def compose(self) -> ComposeResult:
        with Container(id="dialog-container"):
            yield Label(f"[yellow]{self.message}[/yellow]", id="dialog-title")
            with Horizontal(id="dialog-buttons"):
                yield Button("确认", id="confirm", variant="primary")
                yield Button("取消", id="cancel", variant="error")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm" and self.action_callback:
            self.dismiss(True)
            self.action_callback()
        else:
            self.dismiss(False)

# 成功提示对话框
class SuccessDialog(ModalScreen):
    """成功提示对话框"""
    
    def __init__(self, message: str):
        super().__init__()
        self.message = message
    
    def compose(self) -> ComposeResult:
        with Container(id="dialog-container"):
            yield Label(f"[green]{self.message}[/green]", id="dialog-title")
            with Horizontal(id="dialog-buttons"):
                yield Button("确定", id="ok", variant="primary")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(True)

# 错误提示对话框
class ErrorDialog(ModalScreen):
    """错误提示对话框"""
    
    def __init__(self, message: str):
        super().__init__()
        self.message = message
    
    def compose(self) -> ComposeResult:
        with Container(id="dialog-container"):
            yield Label(f"[red]{self.message}[/red]", id="dialog-title")
            with Horizontal(id="dialog-buttons"):
                yield Button("确定", id="ok", variant="primary")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(True)

# 主应用
class WOLApp(App):
    CSS = """
    Screen {
        background: $surface;
    }
    
    #title {
        dock: top;
        text-align: center;
        text-style: bold;
        background: $accent;
        color: $text;
        padding: 1;
        margin-bottom: 1;
    }
    
    #main-container {
        width: 100%;
        height: auto;
        padding: 1;
    }
    
    #interface-container {
        width: 100%;
        height: auto;
        margin: 1;
        border: solid $primary;
        padding: 1;
    }
    
    #interface-label {
        margin-bottom: 1;
    }
    
    #interface-select {
        width: 100%;
        margin-bottom: 1;
    }
    
    #status-container {
        width: 100%;
        height: auto;
        margin: 1;
        border: solid $primary;
        padding: 1;
    }
    
    #wol-status {
        margin: 1;
        padding: 1;
    }
    
    #action-buttons {
        width: 100%;
        height: auto;
        margin: 1;
        padding: 1;
    }
    
    #enable-wol, #disable-wol {
        margin: 1;
        min-width: 30;
        min-height: 3;
    }
    
    #enable-wol {
        background: $success-darken-1;
        color: $text;
        border: tall $success;
    }
    
    #enable-wol:hover {
        background: $success;
    }
    
    #disable-wol {
        background: $error-darken-1;
        color: $text;
        border: tall $error;
    }
    
    #disable-wol:hover {
        background: $error;
    }
    
    #status {
        height: auto;
        min-height: 3;
        margin: 1;
        padding: 1;
        border: solid $accent;
        background: $surface-darken-1;
    }
    
    /* 对话框样式 */
    #dialog-container {
        width: 60%;
        height: auto;
        padding: 2;
        background: $surface;
        border: thick $accent;
        margin: 1 0;
    }
    
    /* 成功对话框样式 */
    SuccessDialog #dialog-container {
        border: thick $success;
    }
    
    /* 错误对话框样式 */
    ErrorDialog #dialog-container {
        border: thick $error;
    }
    
    /* 确认对话框样式 */
    ConfirmDialog #dialog-container {
        border: thick $warning;
    }
    
    #dialog-title {
        text-align: center;
        width: 100%;
        margin-bottom: 2;
    }
    
    #dialog-buttons {
        align: center middle;
        width: 100%;
    }
    
    #dialog-buttons Button {
        margin: 0 2;
        min-width: 10;
    }
    
    /* 按钮样式增强 */
    Button {
        background: $primary;
        border: tall $primary-lighten-2;
        padding: 1 2;
    }
    
    Button:hover {
        background: $primary-lighten-1;
    }
    
    Button#confirm {
        background: $success-darken-1;
        border: tall $success;
    }
    
    Button#confirm:hover {
        background: $success;
    }
    
    Button#cancel {
        background: $error-darken-1;
        border: tall $error;
    }
    
    Button#cancel:hover {
        background: $error;
    }
    
    Button#ok {
        background: $primary-darken-1;
        border: tall $primary;
    }
    
    Button#ok:hover {
        background: $primary;
    }
    
    /* 修复Textual 3.2.0中Select的样式问题 */
    Select {
        background: $boost;
        border: tall $primary;
    }
    """

    BINDINGS = [
        ("q", "quit", "退出"),
        ("escape", "quit", "退出"),
        ("r", "refresh", "刷新状态"),
    ]

    def __init__(self):
        super().__init__()
        self.interfaces = []
        self.selected_interface = None
        self.wol_status = "未知"
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()
        
        with Container(id="main-container"):
            yield Label("[b]网络唤醒（Wake-on-LAN）配置工具[/b]", id="title")
            
            with Container(id="interface-container"):
                yield Label("加载网络接口中...", id="interface-label")
                # Select组件会在异步加载接口信息后添加
                yield Select(id="interface-select", options=[("加载中...", "loading")], disabled=True)
            
            with Container(id="status-container"):
                yield Label("Wake-on-LAN 状态: 未知", id="wol-status")
            
            with Container(id="action-buttons"):
                yield Button("启用 Wake-on-LAN", id="enable-wol", disabled=True)
                yield Button("禁用 Wake-on-LAN", id="disable-wol", disabled=True)
            
            # 状态输出
            yield Static("准备就绪，请选择网络接口。", id="status")
    
    def on_mount(self) -> None:
        """组件挂载后执行，初始化状态"""
        self.load_interfaces()
    
    def action_refresh(self) -> None:
        """刷新网络接口状态"""
        self.load_interfaces()
    
    def load_interfaces(self) -> None:
        """加载网络接口列表"""
        status = self.query_one("#status")
        status.update("正在加载网络接口...")
        
        # 创建异步任务
        asyncio.create_task(self.do_load_interfaces())
    
    async def do_load_interfaces(self) -> None:
        """异步加载网络接口列表"""
        interface_label = self.query_one("#interface-label")
        status = self.query_one("#status")
        
        # 获取网络接口列表
        self.interfaces = await asyncio.to_thread(get_network_interfaces)
        
        # 打印调试信息
        print(f"找到接口: {self.interfaces}")
        
        # 更新界面
        if not self.interfaces:
            interface_label.update("[red]未找到物理网口！[/red]")
            # 更新已有的Select组件而不是移除再添加
            interface_select = self.query_one("#interface-select")
            interface_select.options = [("未找到网络接口", "none")]
            interface_select.value = "none"  # 显式设置值
            interface_select.disabled = True
            self.query_one("#enable-wol").disabled = True
            self.query_one("#disable-wol").disabled = True
            status.update("[red]未找到可用的网络接口[/red]")
            
            # 强制刷新界面
            self.force_ui_refresh()
            return
        
        # 构建接口选项
        options = [(f"{iface}", iface) for iface in self.interfaces]
        print(f"创建选项: {options}")
        
        try:
            # 清空Select组件并重新创建，避免更新问题
            old_select = self.query_one("#interface-select")
            old_select.remove()
            
            # 创建新的Select组件
            new_select = Select(id="interface-select", options=options)
            await self.mount(new_select, before="#status-container")
            
            # 设置初始值
            if options:
                self.selected_interface = options[0][1]
                new_select.value = self.selected_interface
                print(f"设置初始值: {self.selected_interface}")
            
            interface_label.update("[green]可用的网络接口：[/green]")
            
            # 强制刷新界面
            self.force_ui_refresh()
            
            # 选择第一个接口并获取状态
            if options:
                await self.update_wol_status(self.selected_interface)
            
            status.update("网络接口加载完成")
        except Exception as e:
            # 处理可能的异常
            print(f"更新界面时出错: {str(e)}")
            status.update(f"[red]加载网络接口时出错: {str(e)}[/red]")
    
    def force_ui_refresh(self):
        """强制刷新UI，不与Textual内部方法冲突"""
        self.refresh_css()
        try:
            # 强制重绘屏幕
            self.screen.refresh()
        except:
            pass
    
    async def update_wol_status(self, interface: str) -> None:
        """更新WOL状态显示"""
        if not interface:
            return
        
        wol_status_label = self.query_one("#wol-status")
        status = self.query_one("#status")
        
        status.update(f"正在检查 {interface} 的 Wake-on-LAN 状态...")
        
        try:
            # 获取WOL状态
            self.wol_status = await asyncio.to_thread(check_wol_status, interface)
            print(f"接口 {interface} 的WOL状态: '{self.wol_status}'")
            
            # 清理状态字符串，删除可能的额外空格
            clean_status = self.wol_status.strip().lower()
            
            # 明确的状态检测逻辑
            is_enabled = 'g' in clean_status
            
            # 检查状态是否明确是'd'或其他非g值(如'd'、'pumbg'等)
            print(f"清理后的状态字符串: '{clean_status}'")
            print(f"是否包含'g': {is_enabled}")
            
            # 更新界面
            if is_enabled:
                print("结论: WOL已启用")
                wol_status_label.update(f"Wake-on-LAN 状态: [green]已启用[/green] ({self.wol_status})")
                self.query_one("#enable-wol").disabled = True
                self.query_one("#disable-wol").disabled = False
            else:
                print("结论: WOL已禁用")
                wol_status_label.update(f"Wake-on-LAN 状态: [red]已禁用[/red] ({self.wol_status})")
                self.query_one("#enable-wol").disabled = False
                self.query_one("#disable-wol").disabled = True
            
            status.update(f"{interface} 的 Wake-on-LAN 状态已更新")
        except Exception as e:
            print(f"获取WOL状态时出错: {str(e)}")
            wol_status_label.update(f"Wake-on-LAN 状态: [red]获取失败[/red]")
            status.update(f"[red]获取 {interface} 的 Wake-on-LAN 状态失败: {str(e)}[/red]")
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """处理接口选择变更"""
        # Textual 3.2.0中可能没有event.select属性，改用其他方法
        # 只考虑界面上唯一的Select组件
        self.selected_interface = event.value
        if self.selected_interface and self.selected_interface != "none" and self.selected_interface != "loading":
            # 创建一个异步任务来处理状态更新
            asyncio.create_task(self.update_wol_status(self.selected_interface))
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击事件处理"""
        button_id = event.button.id
        
        if button_id == "enable-wol":
            # 不再使用确认对话框，直接执行
            asyncio.create_task(self.do_set_wol(self.selected_interface, True))
        elif button_id == "disable-wol":
            # 不再使用确认对话框，直接执行
            asyncio.create_task(self.do_set_wol(self.selected_interface, False))
    
    async def do_set_wol(self, interface: str, enable: bool) -> None:
        """异步设置WOL状态"""
        status = self.query_one("#status")
        mode = "g" if enable else "d"
        action_text = "启用" if enable else "禁用"
        
        status.update(f"[blue]正在为 {interface} {action_text} Wake-on-LAN...[/blue]")
        
        # 设置WOL状态
        cmd = f"ethtool -s {interface} wol {mode}"
        result = await asyncio.to_thread(run_command, cmd, True)
        if result['status_code'] != 0:
            error_message = f"{action_text} Wake-on-LAN 失败！\n错误信息: {result['stderr']}"
            status.update(f"[red]{error_message}[/red]")
            return
        
        # 设置完成后直接更新界面状态，不等待实际状态检查
        wol_status_label = self.query_one("#wol-status")
        if enable:
            wol_status_label.update(f"Wake-on-LAN 状态: [green]已启用[/green] (g)")
            self.query_one("#enable-wol").disabled = True
            self.query_one("#disable-wol").disabled = False
        else:
            wol_status_label.update(f"Wake-on-LAN 状态: [red]已禁用[/red] (d)")
            self.query_one("#enable-wol").disabled = False
            self.query_one("#disable-wol").disabled = True
        
        # 设置自动启动
        cron_job = f"@reboot /sbin/ethtool -s {interface} wol g"

        # 对于启用操作，添加crontab项
        if enable:
            # 自动方式添加到crontab
            result = await asyncio.to_thread(run_command, "crontab -l", True)
            cron_content = result['stdout'] if result['status_code'] == 0 else ""
            
            # 检查是否已存在
            if cron_job not in cron_content:
                # 添加到crontab
                cmd = f'(crontab -l; echo "{cron_job}") | crontab -'
                result = await asyncio.to_thread(run_command, cmd, True)
                if result['status_code'] != 0:
                    error_message = f"添加到crontab失败！\n错误信息: {result['stderr']}"
                    status.update(f"[red]{error_message}[/red]")
                    return
        else:
            # 从crontab移除
            cmd = f"crontab -l | grep -v \"ethtool -s {interface} wol g\" | crontab -"
            result = await asyncio.to_thread(run_command, cmd, True)
            if result['status_code'] != 0:
                error_message = f"从crontab移除设置失败！\n错误信息: {result['stderr']}"
                status.update(f"[red]{error_message}[/red]")
                return
            
            # 对于禁用操作，追加NetworkManager配置以防止设置被恢复
            await self.prevent_wol_auto_restore(interface)
        
        # 更新状态信息，不显示成功对话框
        status.update(f"已完成 {interface} 的 Wake-on-LAN {action_text}操作")
        
        # 延迟一段时间后再重新检查状态，以确保更改已生效
        await asyncio.sleep(1)
        await self.update_wol_status(interface)
    
    async def prevent_wol_auto_restore(self, interface: str) -> None:
        """防止NetworkManager等自动恢复WOL设置"""
        try:
            # 检查NetworkManager是否存在
            nm_check = await asyncio.to_thread(run_command, "which nmcli", shell=True)
            if nm_check['status_code'] != 0:
                print("未检测到NetworkManager，跳过配置")
                return
            
            # 尝试创建NetworkManager配置文件
            nm_dir = "/etc/NetworkManager/conf.d"
            nm_file = f"{nm_dir}/90-disable-wol-{interface}.conf"
            
            # 确认目录存在
            dir_check = await asyncio.to_thread(run_command, f"sudo mkdir -p {nm_dir}", shell=True)
            if dir_check['status_code'] != 0:
                print(f"创建目录 {nm_dir} 失败")
                return
            
            # 创建配置文件
            config_content = f"""[device-{interface}]
ethernet.wake-on-lan=0
"""
            
            # 写入配置文件
            write_cmd = f"echo '{config_content}' | sudo tee {nm_file}"
            write_result = await asyncio.to_thread(run_command, write_cmd, shell=True)
            if write_result['status_code'] != 0:
                print(f"创建NetworkManager配置文件失败: {write_result['stderr']}")
                return
            
            # 重启NetworkManager服务
            restart_cmd = "sudo systemctl restart NetworkManager"
            await asyncio.to_thread(run_command, restart_cmd, shell=True)
            
            print(f"已配置NetworkManager防止自动恢复WOL设置")
        except Exception as e:
            print(f"配置NetworkManager出错: {str(e)}")

if __name__ == "__main__":
    app = WOLApp()
    app.run() 