#!/usr/bin/env python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button, Label, RadioSet, RadioButton
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
CYAN = "\033[36m"

# 工具函数
def clear_screen():
    """清空终端屏幕"""
    os.system('clear' if os.name == 'posix' else 'cls')

def detect_platform():
    """自动检测主板平台 (Intel 或 AMD)"""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read().lower()
        if 'intel' in cpuinfo:
            return "Intel"
        elif 'amd' in cpuinfo:
            return "AMD"
    except Exception:
        pass
    return "Unknown"

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

def modify_grub_file(platform):
    """修改 grub 配置文件中的 GRUB_CMDLINE_LINUX_DEFAULT"""
    grub_file_path = "/etc/default/grub"
    if platform.lower() == "intel":
        new_grub_line = 'GRUB_CMDLINE_LINUX_DEFAULT="quiet i915.force_probe=7d55 intel_iommu=on iommu=pt"'
    elif platform.lower() == "amd":
        new_grub_line = 'GRUB_CMDLINE_LINUX_DEFAULT="quiet i915.force_probe=7d55 amd_iommu=on iommu=pt"'
    else:
        return False, "无效的平台类型，请选择 Intel 或 AMD"

    try:
        with open(grub_file_path, 'r') as grub_file:
            grub_lines = grub_file.readlines()

        for i, line in enumerate(grub_lines):
            if line.startswith("GRUB_CMDLINE_LINUX_DEFAULT"):
                grub_lines[i] = new_grub_line + "\n"
                break

        with open(grub_file_path, 'w') as grub_file:
            grub_file.writelines(grub_lines)

        return True, "grub 配置文件已成功修改！"
    except Exception as e:
        return False, f"修改 grub 配置文件失败: {str(e)}"

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

class IOMMUApp(App):
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
    
    #platform-container {
        width: 100%;
        height: auto;
        margin: 1;
        border: solid $primary;
        padding: 1;
    }
    
    #detected-platform {
        margin: 1;
        padding: 1;
        text-style: bold;
    }
    
    #platform-selection {
        margin: 1;
        padding: 1;
    }
    
    #action-container {
        width: 100%;
        height: auto;
        margin: 1;
        padding: 1;
    }
    
    #apply-button {
        background: $success-darken-1;
        color: $text;
        border: tall $success;
        margin: 1;
        min-width: 30;
        min-height: 3;
    }
    
    #apply-button:hover {
        background: $success;
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
    
    RadioSet {
        background: $surface-darken-1;
        border: solid $primary;
        padding: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "退出"),
        ("escape", "quit", "退出"),
    ]

    def __init__(self):
        super().__init__()
        self.detected_platform = detect_platform()
        self.selected_platform = self.detected_platform

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()
        
        with Container(id="main-container"):
            yield Label("[b]IOMMU 配置工具[/b]", id="title")
            
            with Container(id="platform-container"):
                if self.detected_platform != "Unknown":
                    yield Label(f"检测到您的平台为: [b]{self.detected_platform}[/b]", id="detected-platform")
                else:
                    yield Label("无法自动检测平台类型，请手动选择", id="detected-platform")
                
                with RadioSet(id="platform-selection"):
                    yield RadioButton("Intel", value=self.detected_platform == "Intel")
                    yield RadioButton("AMD", value=self.detected_platform == "AMD")
            
            with Container(id="action-container"):
                yield Button("应用 IOMMU 配置", id="apply-button")
            
            # 状态输出
            yield Static("准备就绪，请选择平台并应用配置。", id="status")

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """处理平台选择变更"""
        self.selected_platform = "Intel" if event.index == 0 else "AMD"
        status = self.query_one("#status")
        status.update(f"已选择平台: [b]{self.selected_platform}[/b]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击事件处理"""
        if event.button.id == "apply-button":
            self.apply_iommu_config()
    
    def apply_iommu_config(self) -> None:
        """应用IOMMU配置"""
        platform = self.selected_platform
        
        # 显示确认对话框
        confirmation_message = f"确认要为 {platform} 平台启用 IOMMU 吗？这将修改 grub 配置并更新系统。"
        
        def confirm_callback():
            self.start_iommu_config(platform)
        
        self.push_screen(ConfirmDialog(confirmation_message, confirm_callback))
    
    def start_iommu_config(self, platform):
        """开始配置IOMMU"""
        status = self.query_one("#status")
        status.update(f"[blue]正在为 {platform} 平台配置 IOMMU...[/blue]")
        
        # 创建异步任务
        asyncio.create_task(self.do_iommu_config(platform))
    
    async def do_iommu_config(self, platform):
        """异步执行IOMMU配置"""
        status = self.query_one("#status")
        
        # 修改grub文件
        success, message = await asyncio.to_thread(modify_grub_file, platform)
        if not success:
            status.update(f"[red]{message}[/red]")
            self.show_error_dialog(message)
            return
        
        status.update(f"[green]{message}[/green]")
        status.update("[blue]正在重载 grub...[/blue]")
        
        # 更新grub
        result = await asyncio.to_thread(run_command, ['update-grub'])
        if result['status_code'] != 0:
            error_message = f"update-grub 执行失败！\n错误信息: {result['stderr']}"
            status.update(f"[red]{error_message}[/red]")
            self.show_error_dialog(error_message)
            return
        
        status.update("[green]grub 更新成功！[/green]")
        status.update("[blue]正在更新 RAM 磁盘，预计需要 1-3 分钟...[/blue]")
        
        # 更新initramfs
        result = await asyncio.to_thread(run_command, ['update-initramfs', '-u', '-k', 'all'])
        if result['status_code'] != 0:
            error_message = f"update-initramfs -u -k all 执行失败！\n错误信息: {result['stderr']}"
            status.update(f"[red]{error_message}[/red]")
            self.show_error_dialog(error_message)
            return
        
        success_message = "执行成功！IOMMU 配置已完成。请重启系统以使更改生效，并确认虚拟化已开启。"
        status.update(f"[green]{success_message}[/green]")
        self.show_success_dialog(success_message)
    
    def show_success_dialog(self, message: str) -> None:
        """显示成功对话框"""
        self.push_screen(SuccessDialog(message))
    
    def show_error_dialog(self, message: str) -> None:
        """显示错误对话框"""
        self.push_screen(ErrorDialog(message))

if __name__ == "__main__":
    app = IOMMUApp()
    app.run() 