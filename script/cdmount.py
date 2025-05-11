#!/usr/bin/env python
from textual.app import App, ComposeResult
from textual.widgets import (
    Header, Footer, Static, Button, 
    Label, Select
)
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
import os
import subprocess
import glob
import asyncio

# 定义颜色常量
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

def run_as_root(command):
    """以 root 权限执行命令，并返回执行结果，包括状态码和标准输出/错误"""
    result = {
        'status_code': 0,  # 默认状态码为 0 (正常执行)
        'stdout': '', # 正常执行信息输出
        'stderr': '' # 错误执行信息输出
    }

    try:
        # 使用 sudo 执行命令并等待执行完成
        process_result = subprocess.run(['sudo', 'bash', '-c', command], check=True, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)

        # 获取标准输出内容
        result['stdout'] = process_result.stdout.decode()
        return result
    except subprocess.CalledProcessError as e:
        # 捕获异常，获取错误信息
        result['status_code'] = 1  # 设置状态码为 1，表示执行失败
        result['stderr'] = e.stderr.decode()
        return result

def detect_cd_drives():
    """动态检测系统中的所有 CD 驱动器（/dev/sr*）"""
    cd_drives = glob.glob('/dev/sr*')  # 查找所有 /dev/srX 的设备
    return cd_drives

def create_mount_path(cd_drive):
    """根据 CD 驱动器创建唯一的挂载路径"""
    # 提取驱动器名（如 sr0, sr1）
    drive_name = os.path.basename(cd_drive)
    # 创建挂载路径：/vol1/1000/CD_DVD/sr0
    mount_path = f"/vol1/1000/CD_DVD/{drive_name}"
    # 如果挂载目录不存在，则创建
    if not os.path.exists(mount_path):
        os.makedirs(mount_path)
    return mount_path

def mount_cd(cd_drive, mount_path):
    """挂载 CD 驱动器"""
    command = f"mount {cd_drive} {mount_path}"
    return run_as_root(command)

def eject_cd(selected_drive):
    """弹出 CD 驱动器"""
    command = f"eject {selected_drive}"
    return run_as_root(command)

# CD挂载主屏幕
class CDMountScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "返回")]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()
        
        with Container():
            yield Label("[b]CD/DVD挂载工具[/b]", id="title")
            
            # 驱动器选择区域
            with Vertical(id="drive-selection"):
                yield Label("请选择CD/DVD驱动器:", id="drive-label")
                yield Static("", id="drives-list")
                # 初始化Select组件时提供默认选项
                yield Select([(("正在检测驱动器...", "loading"))], id="drive-select")
            
            # 操作按钮区域
            with Horizontal(id="actions"):
                yield Button("挂载", id="mount", variant="primary")
                yield Button("弹出", id="eject", variant="warning")
                yield Button("刷新", id="refresh", variant="success")
            
            # 状态输出区域
            yield Static("准备就绪，请选择操作。", id="status")
    
    def on_mount(self) -> None:
        """当屏幕挂载时，检测CD驱动器"""
        self.refresh_drives()
    
    def refresh_drives(self) -> None:
        """刷新驱动器列表"""
        drives = detect_cd_drives()
        
        # 更新驱动器选择下拉框
        drive_select = self.query_one("#drive-select", Select)
        
        if drives:
            # 创建选择项
            options = [(drive, drive) for drive in drives]
            drive_select.set_options(options)
            self.query_one("#status").update("检测到CD/DVD驱动器，请选择操作。")
        else:
            drive_select.set_options([("无可用驱动器", "none")])
            self.query_one("#status").update("[red]未检测到CD/DVD驱动器。如果您是USB的驱动器，走的是USB外置存储，无需使用此脚本进行额外挂载。[/red]")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击事件处理"""
        if event.button.id == "refresh":
            self.refresh_drives()
        elif event.button.id == "mount":
            asyncio.create_task(self.mount_drive())
        elif event.button.id == "eject":
            asyncio.create_task(self.eject_drive())
    
    async def mount_drive(self) -> None:
        """挂载选中的驱动器"""
        drive_select = self.query_one("#drive-select", Select)
        status = self.query_one("#status", Static)
        
        if not drive_select.value or drive_select.value == "none":
            status.update("[red]请先选择一个有效的驱动器[/red]")
            return
        
        selected_drive = drive_select.value
        mount_path = create_mount_path(selected_drive)
        
        status.update(f"[blue]正在挂载 {selected_drive} 到 {mount_path}...[/blue]")
        
        # 在后台线程中执行挂载操作
        result = await asyncio.to_thread(mount_cd, selected_drive, mount_path)
        
        if result['status_code'] != 0:
            if "no medium found on" in result['stderr']:
                status.update(f"[yellow]挂载失败\n错误原因：找不到介质\n建议操作：请确认CD已正确放入DVD中后再次尝试[/yellow]")
            elif "already mounted on" in result['stderr']:
                status.update(f"[yellow]挂载失败\n错误原因：已安装\n建议操作：请先弹出CD[/yellow]")
            else:
                status.update(f"[red]挂载失败，错误输出\n{result['stderr']}\n请截图在github提交issue或联系作者排查[/red]")
        else:
            status.update(f"[green]挂载成功！路径：{mount_path}[/green]")
    
    async def eject_drive(self) -> None:
        """弹出选中的驱动器"""
        drive_select = self.query_one("#drive-select", Select)
        status = self.query_one("#status", Static)
        
        if not drive_select.value or drive_select.value == "none":
            status.update("[red]请先选择一个有效的驱动器[/red]")
            return
        
        selected_drive = drive_select.value
        
        status.update(f"[blue]正在弹出 {selected_drive}...[/blue]")
        
        # 在后台线程中执行弹出操作
        result = await asyncio.to_thread(eject_cd, selected_drive)
        
        if result['status_code'] != 0:
            status.update(f"[red]弹出失败，错误输出\n{result['stderr']}\n请截图在github提交issue或联系作者排查[/red]")
        else:
            status.update(f"[green]弹出成功！您可以删除挂载的文件夹[/green]")

# 主应用
class CDMountApp(App):
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
    
    #drive-selection {
        width: 100%;
        height: auto;
        margin: 1;
    }
    
    #drive-label {
        margin-bottom: 1;
    }
    
    #drives-list {
        margin-bottom: 1;
    }
    
    #actions {
        width: 100%;
        margin: 1;
    }
    
    Button {
        margin: 1 2;
    }
    
    #status {
        height: auto;
        min-height: 5;
        margin: 1;
        padding: 1;
        border: solid $accent;
        background: $surface-darken-1;
    }
    """

    BINDINGS = [
        ("q", "quit", "退出"),
        ("escape", "quit", "退出"),
    ]

    def compose(self) -> ComposeResult:
        # 直接显示主界面，不再有风险提示
        # Header 和 Footer 会在 CDMountScreen 中创建
        yield from () # 确保 compose 是一个生成器

    def on_mount(self) -> None:
        """应用挂载时执行"""
        # 直接显示主界面
        self.push_screen(CDMountScreen())
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击事件处理"""
        # 由于风险提示已删除，此处的按钮逻辑不再需要
        # if event.button.id == "continue":
        #     # 隐藏风险提示
        #     self.query_one("#warning-container").remove()
        #     # 显示主界面
        #     self.push_screen(CDMountScreen())
        # elif event.button.id == "exit":
        #     self.exit()
        pass # 保留方法结构，但无操作

if __name__ == "__main__":
    app = CDMountApp()
    app.run() 