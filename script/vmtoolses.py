#!/usr/bin/env python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button, Label
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

def run_command(command):
    """执行命令并返回结果"""
    result = {
        'status_code': 0,
        'stdout': '',
        'stderr': ''
    }

    try:
        process_result = subprocess.run(command, check=True, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
        result['stdout'] = process_result.stdout.decode()
        return result
    except subprocess.CalledProcessError as e:
        result['status_code'] = 1
        result['stderr'] = e.stderr.decode()
        return result

def check_package_installed(package_name):
    """检查软件包是否已安装"""
    try:
        result = subprocess.run(
            ["dpkg-query", "-W", "-f='${Status}'", package_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return "install ok installed" in result.stdout
    except subprocess.CalledProcessError:
        return False

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
class VMToolsApp(App):
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
    
    #status-container {
        width: 100%;
        height: auto;
        margin: 1;
        border: solid $primary;
        padding: 1;
    }
    
    #status-label {
        margin: 1;
        padding: 1;
        text-align: center;
    }
    
    #action-buttons {
        width: 100%;
        height: auto;
        margin: 1;
        padding: 1;
    }
    
    #action-buttons Button {
        margin: 1;
        min-width: 30;
        min-height: 3;
    }
    
    #vmware-install {
        background: $success-darken-1;
        color: $text;
        border: tall $success;
    }
    
    #vmware-install:hover {
        background: $success;
    }
    
    #qemu-install {
        background: $success-darken-1;
        color: $text;
        border: tall $success;
    }
    
    #qemu-install:hover {
        background: $success;
    }
    
    #update-tool {
        background: $primary-darken-1;
        color: $text;
        border: tall $primary;
    }
    
    #update-tool:hover {
        background: $primary;
    }
    
    #uninstall-tool {
        background: $error-darken-1;
        color: $text;
        border: tall $error;
    }
    
    #uninstall-tool:hover {
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
    """

    BINDINGS = [
        ("q", "quit", "退出"),
        ("escape", "quit", "退出"),
        ("r", "refresh", "刷新状态"),
    ]

    def __init__(self):
        super().__init__()
        self.open_vm_tools_installed = False
        self.qemu_guest_agent_installed = False
        self.current_tool = None
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()
        
        with Container(id="main-container"):
            yield Label("[b]虚拟机工具管理[/b]", id="title")
            
            with Container(id="status-container"):
                yield Label("正在检查安装状态...", id="status-label")
            
            with Container(id="action-buttons"):
                # 这些按钮会根据安装状态在mount时动态显示
                yield Button("安装 VMware 平台工具", id="vmware-install", disabled=True)
                yield Button("安装 QEMU/KVM 平台工具", id="qemu-install", disabled=True)
                yield Button("更新工具", id="update-tool", disabled=True)
                yield Button("卸载工具", id="uninstall-tool", disabled=True)
            
            # 状态输出
            yield Static("准备就绪，请选择操作。", id="status")
    
    def on_mount(self) -> None:
        """组件挂载后执行，初始化状态"""
        self.update_tools_status()
    
    def action_refresh(self) -> None:
        """刷新工具安装状态"""
        self.update_tools_status()
    
    def update_tools_status(self) -> None:
        """更新工具安装状态"""
        status = self.query_one("#status")
        status.update("正在检查工具安装状态...")
        
        # 创建异步任务
        asyncio.create_task(self.do_update_tools_status())
    
    async def do_update_tools_status(self) -> None:
        """异步检查工具安装状态"""
        status_label = self.query_one("#status-label")
        status = self.query_one("#status")
        
        # 检查工具是否已安装
        self.open_vm_tools_installed = await asyncio.to_thread(check_package_installed, "open-vm-tools")
        self.qemu_guest_agent_installed = await asyncio.to_thread(check_package_installed, "qemu-guest-agent")
        
        # 如果两个工具都已安装，选择open-vm-tools作为当前工具
        if self.open_vm_tools_installed and self.qemu_guest_agent_installed:
            self.current_tool = "open-vm-tools"
            status_label.update("[yellow]检测到两个工具均已安装，优先操作 open-vm-tools[/yellow]")
        elif self.open_vm_tools_installed:
            self.current_tool = "open-vm-tools"
            status_label.update("[green]VMware 平台工具 (open-vm-tools) 已安装[/green]")
        elif self.qemu_guest_agent_installed:
            self.current_tool = "qemu-guest-agent"
            status_label.update("[green]QEMU/KVM 平台工具 (qemu-guest-agent) 已安装[/green]")
        else:
            self.current_tool = None
            status_label.update("[red]未检测到已安装的虚拟机工具[/red]")
        
        # 根据安装状态更新按钮可用性
        vmware_install_btn = self.query_one("#vmware-install")
        qemu_install_btn = self.query_one("#qemu-install")
        update_btn = self.query_one("#update-tool")
        uninstall_btn = self.query_one("#uninstall-tool")
        
        if self.open_vm_tools_installed or self.qemu_guest_agent_installed:
            vmware_install_btn.disabled = True
            qemu_install_btn.disabled = True
            update_btn.disabled = False
            uninstall_btn.disabled = False
        else:
            vmware_install_btn.disabled = False
            qemu_install_btn.disabled = False
            update_btn.disabled = True
            uninstall_btn.disabled = True
        
        status.update("工具状态已更新")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击事件处理"""
        button_id = event.button.id
        
        if button_id == "vmware-install":
            self.install_vmware_tools()
        elif button_id == "qemu-install":
            self.install_qemu_tools()
        elif button_id == "update-tool":
            self.update_tools()
        elif button_id == "uninstall-tool":
            self.uninstall_tools()
    
    def install_vmware_tools(self) -> None:
        """安装VMware工具"""
        def confirm_callback():
            asyncio.create_task(self.do_install_tool("open-vm-tools"))
        
        self.push_screen(ConfirmDialog("确认要安装VMware平台工具 (open-vm-tools) 吗？", confirm_callback))
    
    def install_qemu_tools(self) -> None:
        """安装QEMU工具"""
        def confirm_callback():
            asyncio.create_task(self.do_install_tool("qemu-guest-agent"))
        
        self.push_screen(ConfirmDialog("确认要安装QEMU/KVM平台工具 (qemu-guest-agent) 吗？", confirm_callback))
    
    def update_tools(self) -> None:
        """更新已安装的工具"""
        tool_name = "VMware工具" if self.current_tool == "open-vm-tools" else "QEMU/KVM工具"
        
        def confirm_callback():
            asyncio.create_task(self.do_update_tool(self.current_tool))
        
        self.push_screen(ConfirmDialog(f"确认要更新已安装的{tool_name}吗？", confirm_callback))
    
    def uninstall_tools(self) -> None:
        """卸载工具"""
        tool_name = "VMware工具" if self.current_tool == "open-vm-tools" else "QEMU/KVM工具"
        
        def confirm_callback():
            asyncio.create_task(self.do_uninstall_tool(self.current_tool))
        
        self.push_screen(ConfirmDialog(f"确认要卸载{tool_name}吗？", confirm_callback))
    
    async def do_install_tool(self, tool: str) -> None:
        """异步安装工具"""
        status = self.query_one("#status")
        status.update(f"[blue]正在安装 {tool}...[/blue]")
        
        # 执行安装命令
        result = await asyncio.to_thread(run_command, ["sudo", "apt", "install", "-y", tool])
        if result['status_code'] != 0:
            error_message = f"安装 {tool} 失败！\n错误信息: {result['stderr']}"
            status.update(f"[red]{error_message}[/red]")
            self.push_screen(ErrorDialog(error_message))
            return
        
        success_message = f"{tool} 已成功安装！"
        status.update(f"[green]{success_message}[/green]")
        self.push_screen(SuccessDialog(success_message))
        
        # 更新界面
        await asyncio.sleep(1)
        self.update_tools_status()
    
    async def do_update_tool(self, tool: str) -> None:
        """异步更新工具"""
        status = self.query_one("#status")
        status.update(f"[blue]正在更新 {tool}...[/blue]")
        
        # 执行更新命令
        result = await asyncio.to_thread(run_command, ["sudo", "apt", "install", "--only-upgrade", "-y", tool])
        if result['status_code'] != 0:
            error_message = f"更新 {tool} 失败！\n错误信息: {result['stderr']}"
            status.update(f"[red]{error_message}[/red]")
            self.push_screen(ErrorDialog(error_message))
            return
        
        success_message = f"{tool} 已成功更新！"
        status.update(f"[green]{success_message}[/green]")
        self.push_screen(SuccessDialog(success_message))
        
        # 更新界面
        await asyncio.sleep(1)
        self.update_tools_status()
    
    async def do_uninstall_tool(self, tool: str) -> None:
        """异步卸载工具"""
        status = self.query_one("#status")
        status.update(f"[blue]正在卸载 {tool}...[/blue]")
        
        # 执行卸载命令
        result = await asyncio.to_thread(run_command, ["sudo", "apt", "remove", "-y", tool])
        if result['status_code'] != 0:
            error_message = f"卸载 {tool} 失败！\n错误信息: {result['stderr']}"
            status.update(f"[red]{error_message}[/red]")
            self.push_screen(ErrorDialog(error_message))
            return
        
        # 执行完全清理
        result = await asyncio.to_thread(run_command, ["sudo", "dpkg", "--purge", tool])
        if result['status_code'] != 0:
            error_message = f"清理 {tool} 失败！\n错误信息: {result['stderr']}"
            status.update(f"[red]{error_message}[/red]")
            self.push_screen(ErrorDialog(error_message))
            return
        
        success_message = f"{tool} 已成功卸载！"
        status.update(f"[green]{success_message}[/green]")
        self.push_screen(SuccessDialog(success_message))
        
        # 更新界面
        await asyncio.sleep(1)
        self.update_tools_status()

if __name__ == "__main__":
    app = VMToolsApp()
    app.run() 