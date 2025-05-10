#!/usr/bin/env python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button, Label, RadioSet, RadioButton, Input
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen, ModalScreen
import os
import subprocess
import asyncio
import re

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

def get_swap_status():
    """获取当前swap状态信息"""
    result = run_command(['swapon', '--show'])
    if result['status_code'] != 0:
        return {"error": "无法获取swap信息"}
    
    swap_info = result['stdout'].strip()
    if not swap_info:
        return {"enabled": False, "message": "当前系统未启用swap"}
    
    return {"enabled": True, "message": "当前系统已启用swap", "details": swap_info}

def get_swap_file_path():
    """获取swap文件路径"""
    # 先检查/etc/fstab文件中的swap配置
    try:
        with open('/etc/fstab', 'r') as f:
            for line in f.readlines():
                if 'swap' in line and not line.strip().startswith('#'):
                    parts = line.split()
                    if parts and len(parts) > 1:
                        return parts[0]  # 返回swap文件或分区路径
    except Exception:
        pass
    
    # 如果从fstab找不到，尝试从swapon --show获取
    result = run_command(['swapon', '--show'])
    if result['status_code'] == 0:
        lines = result['stdout'].strip().split('\n')
        if len(lines) > 1:  # 有标题行和数据行
            parts = lines[1].split()
            if parts:
                return parts[0]  # 第一列通常是文件名
    
    return None

def get_swap_size():
    """获取当前swap大小(MB)"""
    swap_path = get_swap_file_path()
    if not swap_path:
        return 0
    
    # 如果是分区，使用fdisk查看
    if swap_path.startswith('/dev/'):
        result = run_command(['blockdev', '--getsize64', swap_path])
        if result['status_code'] == 0:
            try:
                size_bytes = int(result['stdout'].strip())
                return size_bytes // (1024 * 1024)  # 转换为MB
            except ValueError:
                return 0
    else:
        # 如果是文件，使用du命令
        result = run_command(['du', '-m', swap_path])
        if result['status_code'] == 0:
            try:
                size_str = result['stdout'].strip().split()[0]
                return int(size_str)
            except (ValueError, IndexError):
                return 0
    
    return 0

def toggle_swap_in_fstab(enable=True):
    """在fstab中启用或禁用swap"""
    fstab_path = '/etc/fstab'
    swap_line = None
    swap_line_index = -1

    # 读取/etc/fstab文件内容
    try:
        with open(fstab_path, 'r') as f:
            lines = f.readlines()

        # 查找swap配置行
        for i, line in enumerate(lines):
            if 'swap' in line:
                swap_line = line
                swap_line_index = i
                break

        # 如果swap配置不存在，返回错误
        if swap_line is None:
            return False, "未找到swap配置!"

        # 修改fstab文件来启用或禁用swap
        if enable:
            # 启用swap：确保swap行没有注释掉
            if swap_line.startswith('#'):
                lines[swap_line_index] = swap_line[1:]  # 移除注释
        else:
            # 禁用swap：注释掉swap行
            if not swap_line.startswith('#'):
                lines[swap_line_index] = '#' + swap_line

        # 写回修改后的fstab文件
        with open(fstab_path, 'w') as f:
            f.writelines(lines)

        return True, "修改成功"
    except Exception as e:
        return False, f"修改fstab文件失败: {str(e)}"

async def create_swap_file(path='/swapfile', size_mb=2048):
    """创建新的swap文件"""
    try:
        # 创建swap文件
        result = await asyncio.to_thread(run_command, ['dd', 'if=/dev/zero', f'of={path}', 'bs=1M', f'count={size_mb}'])
        if result['status_code'] != 0:
            return False, f"创建swap文件失败: {result['stderr']}"
        
        # 设置权限
        result = await asyncio.to_thread(run_command, ['chmod', '600', path])
        if result['status_code'] != 0:
            return False, f"设置swap文件权限失败: {result['stderr']}"
        
        # 格式化为swap
        result = await asyncio.to_thread(run_command, ['mkswap', path])
        if result['status_code'] != 0:
            return False, f"格式化swap文件失败: {result['stderr']}"
        
        # 检查fstab中是否已有swap配置
        has_swap_config = False
        fstab_path = '/etc/fstab'
        
        try:
            with open(fstab_path, 'r') as f:
                lines = f.readlines()
                
            for line in lines:
                if 'swap' in line:
                    has_swap_config = True
                    break
            
            # 如果没有swap配置，添加配置到fstab
            if not has_swap_config:
                with open(fstab_path, 'a') as f:
                    f.write(f"\n{path} none swap sw 0 0\n")
        except Exception as e:
            return False, f"修改fstab文件失败: {str(e)}"
        
        return True, f"成功创建swap文件: {path}，大小: {size_mb}MB"
    except Exception as e:
        return False, f"创建swap文件时发生错误: {str(e)}"

async def change_swap_size(new_size_mb):
    """调整swap文件大小（仅适用于文件形式的swap，不适用于分区）"""
    # 获取当前swap文件路径
    swap_path = get_swap_file_path()
    if not swap_path:
        # 如果不存在swap文件，创建一个新的
        return await create_swap_file('/swapfile', new_size_mb)
    
    # 如果是分区，不支持调整大小
    if swap_path.startswith('/dev/'):
        return False, "不支持调整swap分区大小，仅支持调整swap文件大小"
    
    try:
        # 先关闭swap
        result = await asyncio.to_thread(run_command, ['swapoff', '-a'])
        if result['status_code'] != 0:
            return False, f"关闭swap失败: {result['stderr']}"
        
        # 删除旧的swap文件
        result = await asyncio.to_thread(run_command, ['rm', '-f', swap_path])
        if result['status_code'] != 0:
            return False, f"删除旧swap文件失败: {result['stderr']}"
        
        # 创建新的swap文件
        result = await asyncio.to_thread(run_command, ['dd', 'if=/dev/zero', f'of={swap_path}', 'bs=1M', f'count={new_size_mb}'])
        if result['status_code'] != 0:
            return False, f"创建swap文件失败: {result['stderr']}"
        
        # 设置权限
        result = await asyncio.to_thread(run_command, ['chmod', '600', swap_path])
        if result['status_code'] != 0:
            return False, f"设置swap文件权限失败: {result['stderr']}"
        
        # 格式化为swap
        result = await asyncio.to_thread(run_command, ['mkswap', swap_path])
        if result['status_code'] != 0:
            return False, f"格式化swap文件失败: {result['stderr']}"
        
        # 重新启用所有swap
        result = await asyncio.to_thread(run_command, ['swapon', '-a'])
        if result['status_code'] != 0:
            return False, f"启用swap失败: {result['stderr']}"
        
        return True, f"swap大小已成功调整为{new_size_mb}MB"
    except Exception as e:
        return False, f"调整swap大小时发生错误: {str(e)}"

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

# 输入对话框
class InputDialog(ModalScreen):
    """输入对话框"""
    
    def __init__(self, message: str, default_value: str = "", action_callback=None):
        super().__init__()
        self.message = message
        self.default_value = default_value
        self.action_callback = action_callback
    
    def compose(self) -> ComposeResult:
        with Container(id="dialog-container"):
            yield Label(f"[blue]{self.message}[/blue]", id="dialog-title")
            yield Input(value=self.default_value, id="input-field")
            with Horizontal(id="dialog-buttons"):
                yield Button("确认", id="confirm", variant="primary")
                yield Button("取消", id="cancel", variant="error")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm" and self.action_callback:
            input_value = self.query_one("#input-field", Input).value
            self.dismiss(input_value)
            self.action_callback(input_value)
        else:
            self.dismiss(None)

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
class SwapManagerApp(App):
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
    
    #swap-info-container {
        width: 100%;
        height: auto;
        margin: 1;
        border: solid $primary;
        padding: 1;
    }
    
    #swap-status, #swap-size-info {
        margin: 1;
        padding: 1;
    }
    
    #action-buttons {
        width: 100%;
        height: auto;
        margin: 1;
        padding: 1;
    }
    
    #enable-swap, #disable-swap, #change-size {
        margin: 1;
        min-width: 30;
        min-height: 3;
    }
    
    #enable-swap {
        background: $success-darken-1;
        color: $text;
        border: tall $success;
    }
    
    #enable-swap:hover {
        background: $success;
    }
    
    #disable-swap {
        background: $error-darken-1;
        color: $text;
        border: tall $error;
    }
    
    #disable-swap:hover {
        background: $error;
    }
    
    #change-size {
        background: $primary-darken-1;
        color: $text;
        border: tall $primary;
    }
    
    #change-size:hover {
        background: $primary;
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
    
    /* 输入对话框样式 */
    InputDialog #dialog-container {
        border: thick $primary;
    }
    
    #dialog-title {
        text-align: center;
        width: 100%;
        margin-bottom: 2;
    }
    
    #input-field {
        margin-bottom: 1;
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
        self.swap_enabled = False
        self.swap_size = 0
        self.swap_path = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()
        
        with Container(id="main-container"):
            yield Label("[b]Swap 管理工具[/b]", id="title")
            
            with Container(id="swap-info-container"):
                yield Label("加载中...", id="swap-status")
                yield Label("", id="swap-size-info")
            
            with Container(id="action-buttons"):
                yield Button("启用 Swap", id="enable-swap")
                yield Button("禁用 Swap", id="disable-swap")
                yield Button("修改 Swap 大小", id="change-size")
            
            # 状态输出
            yield Static("准备就绪，请选择操作。", id="status")
    
    def on_mount(self) -> None:
        """组件挂载后执行，初始化状态"""
        self.update_swap_info()
    
    def action_refresh(self) -> None:
        """刷新Swap状态"""
        self.update_swap_info()
    
    def update_swap_info(self) -> None:
        """更新Swap信息显示"""
        status = self.query_one("#status")
        status.update("正在获取Swap信息...")
        
        # 创建异步任务更新信息
        asyncio.create_task(self.do_update_swap_info())
    
    async def do_update_swap_info(self) -> None:
        """异步更新Swap信息"""
        swap_status = await asyncio.to_thread(get_swap_status)
        swap_label = self.query_one("#swap-status")
        size_label = self.query_one("#swap-size-info")
        status = self.query_one("#status")
        
        self.swap_enabled = swap_status.get("enabled", False)
        
        if "error" in swap_status:
            swap_label.update(f"[red]错误: {swap_status['error']}[/red]")
            status.update("[red]获取Swap信息失败[/red]")
            return
        
        if self.swap_enabled:
            swap_label.update(f"[green]Swap状态: 已启用[/green]")
            enable_btn = self.query_one("#enable-swap")
            enable_btn.disabled = True
            disable_btn = self.query_one("#disable-swap")
            disable_btn.disabled = False
        else:
            swap_label.update(f"[yellow]Swap状态: 已禁用[/yellow]")
            enable_btn = self.query_one("#enable-swap")
            enable_btn.disabled = False
            disable_btn = self.query_one("#disable-swap")
            disable_btn.disabled = True
        
        # 获取Swap大小
        self.swap_size = await asyncio.to_thread(get_swap_size)
        self.swap_path = await asyncio.to_thread(get_swap_file_path)
        
        if self.swap_path:
            size_label.update(f"Swap路径: [b]{self.swap_path}[/b], 大小: [b]{self.swap_size}MB[/b]")
            change_size_btn = self.query_one("#change-size")
            # 仅允许修改文件形式的swap大小
            change_size_btn.disabled = self.swap_path.startswith('/dev/')
        else:
            size_label.update("未检测到Swap分区或文件")
            change_size_btn = self.query_one("#change-size")
            change_size_btn.disabled = True
        
        status.update("Swap信息已更新")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击事件处理"""
        button_id = event.button.id
        
        if button_id == "enable-swap":
            self.enable_swap()
        elif button_id == "disable-swap":
            self.disable_swap()
        elif button_id == "change-size":
            self.show_change_size_dialog()
    
    def enable_swap(self) -> None:
        """启用Swap"""
        def confirm_callback():
            asyncio.create_task(self.do_toggle_swap(True))
        
        self.push_screen(ConfirmDialog("确认要启用Swap吗？", confirm_callback))
    
    def disable_swap(self) -> None:
        """禁用Swap"""
        def confirm_callback():
            asyncio.create_task(self.do_toggle_swap(False))
        
        self.push_screen(ConfirmDialog("确认要禁用Swap吗？这可能会影响系统在内存不足时的性能。", confirm_callback))
    
    async def do_toggle_swap(self, enable: bool) -> None:
        """异步执行启用/禁用Swap"""
        status = self.query_one("#status")
        action_text = "启用" if enable else "禁用"
        status.update(f"[blue]正在{action_text} Swap...[/blue]")
        
        # 修改fstab
        success, message = await asyncio.to_thread(toggle_swap_in_fstab, enable)
        if not success:
            status.update(f"[red]{message}[/red]")
            self.push_screen(ErrorDialog(message))
            return
        
        # 根据需要执行swapon或swapoff
        command = ['swapon', '-a'] if enable else ['swapoff', '-a']
        result = await asyncio.to_thread(run_command, command)
        
        # 如果启用swap失败，可能是因为swap文件不存在，尝试创建
        if result['status_code'] != 0 and enable and "No such file or directory" in result['stderr']:
            status.update("[yellow]未找到swap文件，正在创建新的swap文件...[/yellow]")
            
            # 显示对话框请求用户输入swap大小
            def size_callback(value):
                try:
                    size = int(value)
                    if size <= 0:
                        self.push_screen(ErrorDialog("Swap大小必须大于0MB"))
                        return
                    
                    asyncio.create_task(self.create_new_swap(size))
                except ValueError:
                    self.push_screen(ErrorDialog("请输入有效的数字"))
            
            self.push_screen(InputDialog("请输入要创建的Swap大小(MB)", "2048", size_callback))
            return
        
        if result['status_code'] != 0:
            error_message = f"{action_text} Swap失败！\n错误信息: {result['stderr']}"
            status.update(f"[red]{error_message}[/red]")
            self.push_screen(ErrorDialog(error_message))
            return
        
        success_message = f"Swap已成功{action_text}！"
        status.update(f"[green]{success_message}[/green]")
        self.push_screen(SuccessDialog(success_message))
        
        # 更新界面信息
        await asyncio.sleep(1)  # 等待一小段时间确保系统状态已更新
        self.update_swap_info()
    
    async def create_new_swap(self, size_mb: int) -> None:
        """创建新的swap文件并启用"""
        status = self.query_one("#status")
        status.update(f"[blue]正在创建大小为{size_mb}MB的swap文件...[/blue]")
        
        success, message = await create_swap_file('/swapfile', size_mb)
        if not success:
            status.update(f"[red]{message}[/red]")
            self.push_screen(ErrorDialog(message))
            return
        
        # 启用swap
        result = await asyncio.to_thread(run_command, ['swapon', '-a'])
        if result['status_code'] != 0:
            error_message = f"启用新创建的Swap失败！\n错误信息: {result['stderr']}"
            status.update(f"[red]{error_message}[/red]")
            self.push_screen(ErrorDialog(error_message))
            return
        
        status.update(f"[green]{message}[/green]")
        self.push_screen(SuccessDialog(f"{message}\nSwap已成功启用！"))
        
        # 更新界面信息
        await asyncio.sleep(1)
        self.update_swap_info()
    
    def show_change_size_dialog(self) -> None:
        """显示修改Swap大小对话框"""
        def input_callback(value):
            try:
                size = int(value)
                if size <= 0:
                    self.push_screen(ErrorDialog("Swap大小必须大于0MB"))
                    return
                
                asyncio.create_task(self.do_change_swap_size(size))
            except ValueError:
                self.push_screen(ErrorDialog("请输入有效的数字"))
        
        default_size = str(self.swap_size) if self.swap_size > 0 else "2048"
        self.push_screen(InputDialog("请输入新的Swap大小(MB)", default_size, input_callback))
    
    async def do_change_swap_size(self, new_size_mb: int) -> None:
        """异步执行修改Swap大小"""
        status = self.query_one("#status")
        status.update(f"[blue]正在修改Swap大小为{new_size_mb}MB...[/blue]")
        
        success, message = await change_swap_size(new_size_mb)
        if not success:
            status.update(f"[red]{message}[/red]")
            self.push_screen(ErrorDialog(message))
            return
        
        status.update(f"[green]{message}[/green]")
        self.push_screen(SuccessDialog(message))
        
        # 更新界面信息
        await asyncio.sleep(1)  # 等待一小段时间确保系统状态已更新
        self.update_swap_info()

if __name__ == "__main__":
    app = SwapManagerApp()
    app.run() 