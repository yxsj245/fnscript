#!/usr/bin/env python
import os
import subprocess
import tempfile
import sys
import argparse

# 尝试导入textual库，如果不存在则设置标志
HAS_TEXTUAL = True
try:
    from textual.app import App, ComposeResult
    from textual.widgets import (
        Header, Footer, Static, Button, 
        Label, RadioSet, RadioButton
    )
    from textual.containers import Container, Horizontal, Vertical
    from textual.screen import Screen, ModalScreen
    import asyncio
except ImportError:
    HAS_TEXTUAL = False
    # 如果没有textual但尝试无参数运行，我们需要提示用户
    if len(sys.argv) == 1:
        print("错误: 未安装textual库，无法启动图形界面。")
        print("您可以通过命令行参数使用此脚本的核心功能:")
        print("  查看当前设置:  python Powermanagement.py -s")
        print("  设置合盖动作:  python Powermanagement.py --lid [ignore|poweroff]")
        print("  设置电源动作:  python Powermanagement.py --power [ignore|poweroff]")
        print("  同时设置两项:  python Powermanagement.py --lid [ignore|poweroff] --power [ignore|poweroff]")
        print("  查看帮助:      python Powermanagement.py -h")
        sys.exit(1)

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

# 文件路径
CONFIG_FILE = "/etc/systemd/logind.conf"

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

def read_config_file():
    """读取配置文件内容"""
    try:
        with open(CONFIG_FILE, 'r') as file:
            return file.readlines()
    except Exception:
        return []

def write_config_file(lines):
    """写入配置文件内容"""
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
            temp_file = temp.name
            temp.writelines(lines)
        
        # 使用sudo命令将临时文件复制到目标位置
        command = f"cp {temp_file} {CONFIG_FILE} && rm {temp_file}"
        result = run_as_root(command)
        
        return result['status_code'] == 0
    except Exception as e:
        print(f"写入配置文件时出错: {str(e)}")
        return False

def get_current_settings():
    """获取当前设置"""
    lines = read_config_file()
    lid_switch = "ignore"  # 默认值
    external_power = "ignore"  # 默认值
    
    for line in lines:
        if line.strip().startswith("HandleLidSwitch="):
            lid_switch = line.strip().split("=")[1]
        elif line.strip().startswith("HandleLidSwitchExternalPower="):
            external_power = line.strip().split("=")[1]
    
    return lid_switch, external_power

def modify_lid_switch_setting(lines, action):
    """修改合盖时的设置"""
    modified = False
    for i, line in enumerate(lines):
        if "HandleLidSwitch=" in line:
            lines[i] = f"HandleLidSwitch={action}\n"
            modified = True
            break
    
    if not modified:
        lines.append(f"HandleLidSwitch={action}\n")
    
    return lines

def modify_external_power_setting(lines, action):
    """修改外部电源设置"""
    modified = False
    for i, line in enumerate(lines):
        if "HandleLidSwitchExternalPower=" in line:
            lines[i] = f"HandleLidSwitchExternalPower={action}\n"
            modified = True
            break
    
    if not modified:
        lines.append(f"HandleLidSwitchExternalPower={action}\n")
    
    return lines

def verify_config_changes(expected_lid_value, expected_power_value):
    """验证配置文件是否成功修改"""
    try:
        # 读取当前配置
        current_lid, current_power = get_current_settings()
        
        # 检查是否与预期值匹配
        lid_match = current_lid == expected_lid_value
        power_match = current_power == expected_power_value
        
        return {
            'success': lid_match and power_match,
            'lid_match': lid_match,
            'power_match': power_match,
            'current_lid': current_lid,
            'current_power': current_power
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def restart_systemd_logind():
    """重启systemd-logind服务"""
    return run_as_root("systemctl restart systemd-logind")

def cli_show_settings():
    """显示当前电源管理设置"""
    lid_switch, external_power = get_current_settings()
    
    print(f"当前电源管理设置:")
    print(f"  笔记本合盖时: {'关机' if lid_switch == 'poweroff' else '不做任何反应'} ({lid_switch})")
    print(f"  电源适配器移除时: {'关机' if external_power == 'poweroff' else '不做任何操作'} ({external_power})")
    
    return True

def cli_apply_settings(lid_value=None, power_value=None):
    """应用电源管理设置
    
    Args:
        lid_value (str): 合盖动作设置 (ignore 或 poweroff)
        power_value (str): 电源适配器移除动作设置 (ignore 或 poweroff)
        
    Returns:
        bool: 是否成功应用设置
    """
    # 如果两个值都是None，则不做任何操作
    if lid_value is None and power_value is None:
        print("错误: 未指定任何设置，操作已取消")
        return False
    
    # 读取当前设置
    current_lid, current_power = get_current_settings()
    
    # 如果某个值为None，则使用当前设置
    lid_value = lid_value if lid_value is not None else current_lid
    power_value = power_value if power_value is not None else current_power
    
    print(f"准备应用以下设置:")
    print(f"  笔记本合盖时: {'关机' if lid_value == 'poweroff' else '不做任何反应'} ({lid_value})")
    print(f"  电源适配器移除时: {'关机' if power_value == 'poweroff' else '不做任何操作'} ({power_value})")
    
    # 确认操作
    print("确认应用这些设置吗？(y/n)")
    response = input().strip().lower()
    if response != 'y':
        print("操作已取消")
        return False
    
    print("正在应用设置...")
    
    # 读取配置文件
    lines = read_config_file()
    print(f"读取配置文件: 找到 {len(lines)} 行内容")
    
    # 修改设置
    lines = modify_lid_switch_setting(lines, lid_value)
    lines = modify_external_power_setting(lines, power_value)
    
    # 写入配置文件
    print("正在写入配置文件...")
    success = write_config_file(lines)
    
    if not success:
        print("错误: 写入配置文件失败")
        return False
    
    print("配置文件已成功写入")
    
    # 验证配置更改
    verify_result = verify_config_changes(lid_value, power_value)
    
    if not verify_result.get('success', False):
        print("警告: 配置可能未正确应用")
        if 'error' in verify_result:
            print(f"错误详情: {verify_result['error']}")
        else:
            print(f"当前合盖设置: {verify_result.get('current_lid', '未知')}")
            print(f"当前电源设置: {verify_result.get('current_power', '未知')}")
    
    # 重启服务
    print("正在重启服务...")
    result = restart_systemd_logind()
    
    if result['status_code'] != 0:
        print(f"错误: 重启服务失败: {result['stderr']}")
        return False
    
    print("服务已成功重启")
    
    # 再次验证配置
    verify_result = verify_config_changes(lid_value, power_value)
    
    if verify_result.get('success', False):
        print("设置已成功应用并重启服务！")
        return True
    else:
        print("警告: 服务已重启，但配置可能未正确应用。请检查系统设置。")
        return False

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='电源管理设置工具')
    parser.add_argument('-s', '--show', action='store_true',
                        help='显示当前电源管理设置')
    parser.add_argument('--lid', choices=['ignore', 'poweroff'],
                        help='设置笔记本合盖时的动作 (ignore: 不做任何反应, poweroff: 关机)')
    parser.add_argument('--power', choices=['ignore', 'poweroff'],
                        help='设置电源适配器移除时的动作 (ignore: 不做任何操作, poweroff: 关机)')
    parser.add_argument('-f', '--force', action='store_true',
                        help='强制执行，不需要确认')
    return parser.parse_args()

# 只有在导入了textual库的情况下才定义这些类
if HAS_TEXTUAL:
    # 添加确认对话框
    class ConfirmDialog(ModalScreen):
        """确认对话框"""
        
        def __init__(self, message: str):
            super().__init__()
            self.message = message
            self.on_dismiss = None  # 添加on_dismiss回调属性
        
        def compose(self) -> ComposeResult:
            with Container(id="dialog-container"):
                yield Label(f"[b]{self.message}[/b]", id="dialog-title")
                with Horizontal(id="dialog-buttons"):
                    yield Button("确认", id="confirm", variant="primary")
                    yield Button("取消", id="cancel", variant="error")
        
        def on_button_pressed(self, event: Button.Pressed) -> None:
            confirmed = event.button.id == "confirm"
            self.dismiss(confirmed)
            # 调用回调函数
            if self.on_dismiss:
                self.on_dismiss(confirmed)

    # 添加成功提示对话框
    class SuccessDialog(ModalScreen):
        """成功提示对话框"""
        
        def __init__(self, message: str):
            super().__init__()
            self.message = message
            self.on_dismiss = None  # 添加on_dismiss回调属性
        
        def compose(self) -> ComposeResult:
            with Container(id="dialog-container"):
                yield Label(f"[green]{self.message}[/green]", id="dialog-title")
                with Horizontal(id="dialog-buttons"):
                    yield Button("确定", id="ok", variant="primary")
        
        def on_button_pressed(self, event: Button.Pressed) -> None:
            self.dismiss(True)
            # 调用回调函数
            if self.on_dismiss:
                self.on_dismiss(True)

    # 添加错误提示对话框
    class ErrorDialog(ModalScreen):
        """错误提示对话框"""
        
        def __init__(self, message: str):
            super().__init__()
            self.message = message
            self.on_dismiss = None  # 添加on_dismiss回调属性
        
        def compose(self) -> ComposeResult:
            with Container(id="dialog-container"):
                yield Label(f"[red]{self.message}[/red]", id="dialog-title")
                with Horizontal(id="dialog-buttons"):
                    yield Button("确定", id="ok", variant="primary")
        
        def on_button_pressed(self, event: Button.Pressed) -> None:
            self.dismiss(True)
            # 调用回调函数
            if self.on_dismiss:
                self.on_dismiss(True)

    # 风险提示屏幕，改用普通Screen而不是单独的Screen类
    class PowerManagementApp(App):
        CSS = """
        Screen {
            background: $surface;
        }
        
        #title, #warning-title {
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
        
        #lid-settings, #power-settings {
            width: 100%;
            height: auto;
            margin: 1;
            border: solid $primary;
            padding: 1;
        }
        
        #lid-label, #power-label {
            text-style: bold;
            margin-bottom: 1;
        }
        
        #action-bar {
            dock: bottom;
            height: 5;
            background: $surface-darken-2;
            border-top: solid $primary;
            layout: horizontal;
            content-align: center middle;
            padding: 1;
        }
        
        #action-bar Button {
            margin: 0 2;
            min-width: 20;
            min-height: 3;
        }
        
        #apply {
            background: $success;
            border: tall $success-lighten-2;
        }
        
        #refresh {
            background: $primary;
            border: tall $primary-lighten-2;
        }
        
        #status {
            height: auto;
            min-height: 3;
            margin: 1;
            padding: 1;
            border: solid $accent;
            background: $surface-darken-1;
        }
        
        #warning-text, #safe-text {
            margin: 1;
            padding: 1;
        }
        
        RadioSet {
            background: $boost;
            border: tall $primary;
            padding: 1;
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
        
        #dialog-title {
            text-align: center;
            width: 100%;
            margin-bottom: 2;
        }
        
        #dialog-buttons {
            align: center middle;
            width: 100%;
        }
        """

        BINDINGS = [
            ("q", "quit", "退出"),
            ("escape", "quit", "退出"),
        ]

        def compose(self) -> ComposeResult:
            # Header 和 Footer 由 PowerManagementScreen 提供
            # 不再显示风险提示
            yield from () 
        
        def on_mount(self) -> None:
            """应用挂载时执行"""
            # 直接显示主界面
            self.push_screen(PowerManagementScreen())
        
        def on_button_pressed(self, event: Button.Pressed) -> None:
            """按钮点击事件处理"""
            # 由于风险提示已删除，此处的按钮逻辑不再需要
            # if event.button.id == "continue":
            #     # 隐藏风险提示
            #     self.query_one("#warning-container").remove()
            #     # 显示主界面
            #     self.push_screen(PowerManagementScreen())
            # elif event.button.id == "exit":
            #     self.exit()
            pass # 保留方法结构，但无操作

    # 电源管理主屏幕
    class PowerManagementScreen(Screen):
        BINDINGS = [("escape", "app.pop_screen", "返回")]
        
        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            
            with Container(id="main-container"):
                yield Label("[b]电源管理设置[/b]", id="title")
                
                # 笔记本合盖设置
                with Vertical(id="lid-settings"):
                    yield Label("笔记本合盖时操作:", id="lid-label")
                    with RadioSet(id="lid-action"):
                        yield RadioButton("不做任何反应 (ignore)", value=True)
                        yield RadioButton("关机 (poweroff)")
                
                # 电源适配器设置
                with Vertical(id="power-settings"):
                    yield Label("电源适配器移除时操作:", id="power-label")
                    with RadioSet(id="power-action"):
                        yield RadioButton("不做任何操作 (ignore)", value=True)
                        yield RadioButton("关机 (poweroff)")
                
                # 状态输出
                yield Static("准备就绪，请选择设置选项。", id="status")
            
            # 固定在底部的操作栏
            with Container(id="action-bar"):
                yield Button("应用设置", id="apply", variant="primary")
                yield Button("刷新设置", id="refresh", variant="success")
            
            yield Footer()
        
        def on_mount(self) -> None:
            """当屏幕挂载时，加载当前设置"""
            # 确保所有组件可见
            self.ensure_buttons_visibility()
            
            # 加载当前设置
            self.run_async(self.load_current_settings())
        
        def run_async(self, coro):
            """运行异步任务并防止返回主菜单"""
            task = asyncio.create_task(coro)
            task.add_done_callback(self.handle_task_result)
        
        def handle_task_result(self, task):
            """处理异步任务结果"""
            try:
                # 获取任务结果，如果有异常会在这里抛出
                task.result()
            except Exception as e:
                # 记录异常
                try:
                    status = self.query_one("#status")
                    status.update(f"[red]任务执行出错: {str(e)}[/red]")
                except:
                    pass
        
        def ensure_buttons_visibility(self) -> None:
            """确保按钮可见"""
            try:
                # 确保操作栏可见
                action_bar = self.query_one("#action-bar")
                action_bar.styles.visibility = "visible"
                
                # 确保按钮可见
                apply_button = self.query_one("#apply")
                refresh_button = self.query_one("#refresh")
                
                apply_button.styles.visibility = "visible"
                refresh_button.styles.visibility = "visible"
                
                # 强制更新显示
                action_bar.refresh()
                apply_button.refresh()
                refresh_button.refresh()
                
                # 打印调试信息到状态区
                status = self.query_one("#status")
                status.update("[blue]操作栏已更新，请尝试操作[/blue]")
            except Exception as e:
                # 如果出现错误，记录到状态区
                try:
                    status = self.query_one("#status")
                    status.update(f"[red]更新按钮可见性时出错: {str(e)}[/red]")
                except:
                    pass
        
        async def load_current_settings(self) -> None:
            """加载当前设置"""
            try:
                lid_switch, external_power = await asyncio.to_thread(get_current_settings)
                
                # 更新单选按钮组
                lid_action = self.query_one("#lid-action", RadioSet)
                power_action = self.query_one("#power-action", RadioSet)
                
                # 获取RadioSet中的所有RadioButton
                lid_buttons = lid_action.query("RadioButton")
                power_buttons = power_action.query("RadioButton")
                
                # 设置合盖操作
                if lid_switch == "poweroff":
                    # 选择第二个按钮 (关机)
                    if len(lid_buttons) > 1:
                        lid_buttons[1].value = True
                else:
                    # 选择第一个按钮 (ignore)
                    if len(lid_buttons) > 0:
                        lid_buttons[0].value = True
                
                # 设置电源适配器操作
                if external_power == "poweroff":
                    # 选择第二个按钮 (关机)
                    if len(power_buttons) > 1:
                        power_buttons[1].value = True
                else:
                    # 选择第一个按钮 (ignore)
                    if len(power_buttons) > 0:
                        power_buttons[0].value = True
                
                self.query_one("#status").update("已加载当前设置。")
            except Exception as e:
                self.query_one("#status").update(f"[red]加载设置时出错: {str(e)}[/red]")
        
        def on_button_pressed(self, event: Button.Pressed) -> None:
            """按钮点击事件处理"""
            # 记录按钮点击事件
            button_id = event.button.id
            self.query_one("#status").update(f"[blue]按钮 '{button_id}' 被点击[/blue]")
            
            # 确保按钮可见
            self.ensure_buttons_visibility()
            
            # 处理不同的按钮
            if button_id == "refresh":
                # 创建异步任务并等待完成
                self.run_async(self.load_current_settings())
            elif button_id == "apply":
                # 创建异步任务并等待完成
                self.run_async(self.confirm_apply_settings())
        
        async def confirm_apply_settings(self) -> None:
            """确认应用设置"""
            try:
                # 获取用户选择
                lid_action = self.query_one("#lid-action", RadioSet)
                power_action = self.query_one("#power-action", RadioSet)
                
                # 获取选中的RadioButton
                lid_selected = None
                power_selected = None
                
                for button in lid_action.query("RadioButton"):
                    if button.value:
                        lid_selected = button.label.plain
                        break
                
                for button in power_action.query("RadioButton"):
                    if button.value:
                        power_selected = button.label.plain
                        break
                
                # 转换为配置值
                lid_value = "poweroff" if lid_selected and "poweroff" in lid_selected else "ignore"
                power_value = "poweroff" if power_selected and "poweroff" in power_selected else "ignore"
                
                # 更新状态
                status = self.query_one("#status")
                status.update(f"[blue]准备应用设置: 合盖={lid_value}, 电源={power_value}[/blue]")
                
                # 构建确认消息
                message = f"确认应用以下设置？\n\n笔记本合盖时: {'关机' if lid_value == 'poweroff' else '不做任何反应'}\n电源适配器移除时: {'关机' if power_value == 'poweroff' else '不做任何操作'}"
                
                # 使用push_screen而不是push_screen_wait，并设置回调函数
                dialog = ConfirmDialog(message)
                
                # 定义回调函数
                def on_dialog_dismiss(dismissed: bool) -> None:
                    if dismissed:
                        # 用户确认，应用设置
                        self.run_async(self.apply_settings(lid_value, power_value))
                
                # 显示对话框并设置回调
                dialog.on_dismiss = on_dialog_dismiss
                self.app.push_screen(dialog)
                
            except Exception as e:
                status = self.query_one("#status")
                status.update(f"[red]显示确认对话框时出错: {str(e)}[/red]")
        
        async def apply_settings(self, lid_value=None, power_value=None) -> None:
            """应用设置"""
            status = self.query_one("#status", Static)
            
            try:
                # 如果没有传入值，则获取用户选择
                if lid_value is None or power_value is None:
                    lid_action = self.query_one("#lid-action", RadioSet)
                    power_action = self.query_one("#power-action", RadioSet)
                    
                    # 获取选中的RadioButton
                    lid_selected = None
                    power_selected = None
                    
                    for button in lid_action.query("RadioButton"):
                        if button.value:
                            lid_selected = button.label.plain
                            break
                    
                    for button in power_action.query("RadioButton"):
                        if button.value:
                            power_selected = button.label.plain
                            break
                    
                    # 转换为配置值
                    lid_value = "poweroff" if lid_selected and "poweroff" in lid_selected else "ignore"
                    power_value = "poweroff" if power_selected and "poweroff" in power_selected else "ignore"
                
                status.update(f"[blue]正在应用设置...\n笔记本合盖时: {lid_value}\n电源适配器移除时: {power_value}[/blue]")
                
                # 显示配置文件路径
                status.update(f"[blue]配置文件路径: {CONFIG_FILE}[/blue]")
                
                # 检查配置文件是否存在
                if os.path.exists(CONFIG_FILE):
                    status.update(f"[blue]配置文件存在，准备读取...[/blue]")
                else:
                    status.update(f"[yellow]配置文件不存在，将创建新文件...[/yellow]")
                
                # 读取配置文件
                lines = await asyncio.to_thread(read_config_file)
                status.update(f"[blue]读取配置文件: 找到 {len(lines)} 行内容[/blue]")
                
                # 修改设置
                original_lines = lines.copy()
                lines = await asyncio.to_thread(modify_lid_switch_setting, lines, lid_value)
                lines = await asyncio.to_thread(modify_external_power_setting, lines, power_value)
                
                # 显示修改前后的差异
                status.update(f"[blue]已修改配置内容，准备写入文件...\n原始行数: {len(original_lines)}\n修改后行数: {len(lines)}[/blue]")
                
                # 使用临时文件和sudo写入配置
                temp_file = tempfile.mktemp()
                with open(temp_file, 'w') as f:
                    f.writelines(lines)
                
                status.update(f"[blue]已创建临时文件: {temp_file}[/blue]")
                
                # 使用sudo复制临时文件到目标位置
                command = f"cp {temp_file} {CONFIG_FILE}"
                status.update(f"[blue]执行命令: {command}[/blue]")
                
                result = await asyncio.to_thread(run_as_root, command)
                
                if result['status_code'] != 0:
                    error_message = f"写入配置文件失败: {result['stderr']}"
                    status.update(f"[red]{error_message}[/red]")
                    # 显示错误对话框
                    self.show_error_dialog(error_message)
                    self.ensure_buttons_visibility()  # 确保按钮可见
                    return
                
                # 删除临时文件
                try:
                    os.remove(temp_file)
                    status.update(f"[blue]临时文件已删除[/blue]")
                except:
                    status.update(f"[yellow]临时文件删除失败，但不影响配置应用[/yellow]")
                
                status.update(f"[green]配置已成功写入，正在验证更改...[/green]")
                
                # 验证配置更改
                verify_result = await asyncio.to_thread(verify_config_changes, lid_value, power_value)
                
                if not verify_result.get('success', False):
                    # 如果验证失败，显示详细信息
                    if 'error' in verify_result:
                        error_message = f"验证配置失败: {verify_result['error']}"
                    else:
                        error_message = f"配置未成功应用\n当前合盖设置: {verify_result.get('current_lid', '未知')}\n当前电源设置: {verify_result.get('current_power', '未知')}"
                    status.update(f"[yellow]{error_message}[/yellow]")
                    # 继续尝试重启服务
                
                status.update(f"[green]正在重启服务...[/green]")
                
                # 重启服务
                result = await asyncio.to_thread(restart_systemd_logind)
                
                if result['status_code'] != 0:
                    error_message = f"重启服务失败: {result['stderr']}"
                    status.update(f"[red]{error_message}[/red]")
                    # 显示错误对话框
                    self.show_error_dialog(error_message)
                else:
                    # 再次验证配置
                    verify_result = await asyncio.to_thread(verify_config_changes, lid_value, power_value)
                    
                    if verify_result.get('success', False):
                        success_message = "设置已成功应用并重启服务！"
                        status.update(f"[green]{success_message}[/green]")
                        # 显示成功对话框
                        self.show_success_dialog(success_message)
                    else:
                        # 如果验证仍然失败，但服务重启成功
                        warning_message = "服务已重启，但配置可能未正确应用。请检查系统设置。"
                        status.update(f"[yellow]{warning_message}[/yellow]")
                        self.show_success_dialog(warning_message)
                
                # 确保按钮可见
                self.ensure_buttons_visibility()
            
            except Exception as e:
                error_message = f"应用设置时出错: {str(e)}"
                status.update(f"[red]{error_message}[/red]")
                # 显示错误对话框
                self.show_error_dialog(error_message)
                # 确保按钮可见
                self.ensure_buttons_visibility()
        
        def show_success_dialog(self, message: str) -> None:
            """显示成功对话框"""
            dialog = SuccessDialog(message)
            self.app.push_screen(dialog)
        
        def show_error_dialog(self, message: str) -> None:
            """显示错误对话框"""
            dialog = ErrorDialog(message)
            self.app.push_screen(dialog)

if __name__ == "__main__":
    args = parse_arguments()
    
    # 如果指定了命令行参数，则直接执行相应功能
    if args.show:
        cli_show_settings()
        sys.exit(0)
    
    if args.lid is not None or args.power is not None:
        success = cli_apply_settings(args.lid, args.power)
        sys.exit(0 if success else 1)
    
    # 如果没有指定命令行参数，则启动图形界面（如果textual可用）
    if HAS_TEXTUAL:
        app = PowerManagementApp()
        app.run()
    else:
        # 这种情况不应该发生，因为在导入时已经处理了，但为了代码完整性保留
        print("错误: 未安装textual库，无法启动图形界面。")
        print("您可以通过命令行参数使用此脚本的核心功能:")
        print("  查看当前设置:  python Powermanagement.py -s")
        print("  设置合盖动作:  python Powermanagement.py --lid [ignore|poweroff]")
        print("  设置电源动作:  python Powermanagement.py --power [ignore|poweroff]")
        print("  同时设置两项:  python Powermanagement.py --lid [ignore|poweroff] --power [ignore|poweroff]")
        print("  查看帮助:      python Powermanagement.py -h")
        sys.exit(1) 