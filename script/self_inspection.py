#!/usr/bin/env python
import os
import subprocess
import psutil
import time
import signal
import sys
import argparse

# 尝试导入textual库，如果不存在则设置标志
HAS_TEXTUAL = True
try:
    from textual.app import App, ComposeResult
    from textual.widgets import Header, Footer, Static, Button, Label, Input
    from textual.containers import Container, Horizontal, Vertical
    from textual.screen import Screen, ModalScreen
    import asyncio
except ImportError:
    HAS_TEXTUAL = False
    # 如果没有textual但尝试无参数运行，我们需要提示用户
    if len(sys.argv) == 1:
        print("错误: 未安装textual库，无法启动图形界面。")
        print("您可以通过命令行参数使用此脚本的核心功能:")
        print("  内存测试:  python self_inspection.py --memory")
        print("  CPU测试:   python self_inspection.py --cpu [测试时长(秒)]")
        print("  查看帮助:  python self_inspection.py -h")
        sys.exit(1)

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

# 全局变量存储当前运行的进程
current_process = None

# 工具函数
def clear_screen():
    """清空终端屏幕"""
    os.system('clear' if os.name == 'posix' else 'cls')

def get_test_memory():
    """计算可用于测试的内存 (剩余内存的 97%)"""
    available_memory = psutil.virtual_memory().available // (1024 * 1024)  # 获取可用内存 (MB)
    return int(available_memory * 0.97)  # 取 97% 进行测试

def check_memory_usage():
    """检查当前内存使用情况"""
    return psutil.virtual_memory().percent

def run_command(command):
    """执行命令并返回结果"""
    global current_process
    
    result = {
        'status_code': 0,
        'stdout': '',
        'stderr': ''
    }

    try:
        # 保存进程引用以便后续可以终止
        current_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # 等待进程完成
        stdout, stderr = current_process.communicate()
        
        # 获取返回码
        result['status_code'] = current_process.returncode
        result['stdout'] = stdout
        result['stderr'] = stderr
        
        # 清除当前进程引用
        current_process = None
        
        return result
    except Exception as e:
        if current_process:
            try:
                current_process.terminate()
            except:
                pass
            current_process = None
        
        result['status_code'] = 1
        result['stderr'] = str(e)
        return result

def stop_current_process():
    """停止当前正在运行的进程"""
    global current_process
    if current_process:
        try:
            current_process.terminate()
            # 给进程一点时间来终止
            time.sleep(0.5)
            # 如果进程还在运行，强制结束
            if current_process.poll() is None:
                current_process.kill()
            return True
        except Exception:
            return False
        finally:
            current_process = None
    return False

# 命令行直接执行内存测试的函数
def cli_memory_test():
    """通过命令行直接执行内存测试"""
    memory_usage = check_memory_usage()
    
    if memory_usage > 80:
        print(f"警告: 当前系统内存使用率已达 {memory_usage}%!")
        print("建议关闭一些软件后再运行，继续运行可能检测效果不够准确")
        print("是否继续? (y/n)")
        response = input().strip().lower()
        if response != 'y':
            print("操作已取消")
            return False
    
    print("建议关闭所有docker容器以及停用所有应用程序以保证检测的准确性。")
    print("是否继续? (y/n)")
    response = input().strip().lower()
    if response != 'y':
        print("操作已取消")
        return False
    
    mem_size = f"{get_test_memory()}M"
    print("正在运行内存测试，请勿进行其它操作，如果运行过程中出现死机重启则大概率为内存问题。")
    print("整个测试过程预计 30-120 分钟 具体根据内存大小，如果需要终止测试请按Ctrl+C。")
    
    try:
        # 设置信号处理器以便可以通过Ctrl+C终止测试
        def signal_handler(sig, frame):
            print("\n测试已被用户终止")
            stop_current_process()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # 执行测试
        result = run_command(["sudo", "memtester", mem_size, "1"])
        
        if result['status_code'] == 0:
            print("内存测试完成！未发现问题。")
            return True
        else:
            print(f"内存测试失败！错误信息：{result['stderr']}")
            return False
    
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        return False

# 命令行直接执行CPU测试的函数
def cli_cpu_test(duration=60):
    """通过命令行直接执行CPU测试
    
    Args:
        duration (int): 测试持续时间（秒），默认为60秒
    """
    try:
        duration = int(duration)
        if duration <= 0:
            print("错误: 测试时长必须大于0")
            return False
    except ValueError:
        print("错误: 测试时长必须是一个有效的整数")
        return False
    
    print(f"正在进行 CPU 压测，持续 {duration} 秒...如需提前结束测试，请按Ctrl+C。")
    
    try:
        # 设置信号处理器以便可以通过Ctrl+C终止测试
        def signal_handler(sig, frame):
            print("\n测试已被用户终止")
            stop_current_process()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # 执行测试
        result = run_command(["stress", "--cpu", "4", "--timeout", str(duration)])
        
        if result['status_code'] == 0:
            print("CPU 压测完成！未发现问题。")
            return True
        else:
            print(f"CPU 压测失败！错误信息：{result['stderr']}")
            return False
    
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        return False

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='系统健康检测工具')
    parser.add_argument('--memory', action='store_true',
                        help='执行内存测试')
    parser.add_argument('--cpu', nargs='?', const=60, type=int,
                        help='执行CPU压测，可选参数为测试时长(秒)，默认为60秒')
    return parser.parse_args()

# 只有在导入了textual库的情况下才定义这些类
if HAS_TEXTUAL:
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

    class SystemHealthApp(App):
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
        
        #menu-container {
            width: 100%;
            height: auto;
            margin: 1;
            border: solid $primary;
            padding: 1;
        }
        
        .menu-button {
            margin: 1;
            min-width: 30;
            min-height: 3;
            background: $primary;
            color: $text;
            border: tall $primary-lighten-2;
        }
        
        #memory-test {
            background: $success-darken-1;
            color: $text;
            border: tall $success;
        }
        
        #cpu-test {
            background: $warning-darken-1;
            color: $text;
            border: tall $warning;
        }
        
        #stop-test {
            background: $error-darken-1;
            color: $text;
            border: tall $error;
            margin: 1;
            min-width: 30;
            min-height: 3;
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
        
        Button#cancel, Button#stop-test {
            background: $error-darken-1;
            border: tall $error;
        }
        
        Button#cancel:hover, Button#stop-test:hover {
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
            ("ctrl+c", "stop_test", "停止测试"),
        ]

        def __init__(self):
            super().__init__()
            self.is_testing = False

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            yield Footer()
            
            with Container(id="main-container"):
                yield Label("[b]系统健康检测工具[/b]", id="title")
                
                with Container(id="menu-container"):
                    yield Button("内存检测 (使用 memtester)", id="memory-test", classes="menu-button")
                    yield Button("CPU 压测", id="cpu-test", classes="menu-button")
                    yield Button("停止当前测试", id="stop-test", disabled=True)
                
                # 状态输出
                yield Static("准备就绪，请选择检测项目。", id="status")

        def on_button_pressed(self, event: Button.Pressed) -> None:
            """按钮点击事件处理"""
            button_id = event.button.id
            
            if button_id == "memory-test":
                self.start_memory_test()
            elif button_id == "cpu-test":
                self.start_cpu_test()
            elif button_id == "stop-test":
                self.stop_test()
        
        def action_stop_test(self) -> None:
            """键盘快捷键停止测试"""
            self.stop_test()
        
        def stop_test(self) -> None:
            """停止当前测试"""
            if not self.is_testing:
                return
            
            status = self.query_one("#status")
            status.update("[yellow]正在停止测试...[/yellow]")
            
            # 停止当前进程
            if stop_current_process():
                status.update("[green]测试已停止。[/green]")
                self.show_success_dialog("测试已成功停止。")
            else:
                status.update("[red]无法停止测试，可能测试已经完成。[/red]")
            
            # 更新界面状态
            self.is_testing = False
            
            # 使用try/except捕获可能的NoMatches异常
            try:
                stop_button = self.query_one("#stop-test", Button)
                if stop_button:
                    stop_button.disabled = True
                
                memory_button = self.query_one("#memory-test", Button)
                if memory_button:
                    memory_button.disabled = False
                
                cpu_button = self.query_one("#cpu-test", Button)
                if cpu_button:
                    cpu_button.disabled = False
            except Exception as e:
                # 记录错误但不中断程序
                print(f"更新按钮状态时出错: {str(e)}")
        
        def start_memory_test(self) -> None:
            """开始内存测试"""
            status = self.query_one("#status")
            memory_usage = check_memory_usage()
            
            if memory_usage > 80:
                warning_message = f"警告: 当前系统内存使用率已达 {memory_usage}%!\n建议关闭一些软件后再运行，继续运行可能检测效果不够准确"
                status.update(f"[yellow]{warning_message}[/yellow]")
                
                # 显示确认对话框
                def confirm_callback():
                    self.show_memory_test_warning()
                
                self.push_screen(ConfirmDialog(warning_message, confirm_callback))
            else:
                self.show_memory_test_warning()
        
        def show_memory_test_warning(self):
            """显示内存测试警告"""
            warning = "建议关闭所有docker容器以及停用所有应用程序以保证检测的准确性。"
            status = self.query_one("#status")
            status.update(f"[red]{warning}[/red]")
            
            def confirm_callback():
                self.run_memory_test()
            
            self.push_screen(ConfirmDialog(warning, confirm_callback))
        
        def run_memory_test(self) -> None:
            """执行内存测试"""
            status = self.query_one("#status")
            mem_size = f"{get_test_memory()}M"
            
            message = "正在运行内存测试，请勿进行其它操作，如果运行过程中出现死机重启则大概率为内存问题。整个测试过程预计 30-120 分钟 具体根据内存大小，如果需要终止测试请按Ctrl+C或点击停止按钮。"
            status.update(f"[blue]{message}[/blue]")
            
            # 更新界面状态
            self.is_testing = True
            
            # 使用try/except捕获可能的NoMatches异常
            try:
                stop_button = self.query_one("#stop-test", Button)
                if stop_button:
                    stop_button.disabled = False
                
                memory_button = self.query_one("#memory-test", Button)
                if memory_button:
                    memory_button.disabled = True
                
                cpu_button = self.query_one("#cpu-test", Button)
                if cpu_button:
                    cpu_button.disabled = True
            except Exception as e:
                # 记录错误但不中断程序
                print(f"更新按钮状态时出错: {str(e)}")
            
            # 创建异步任务
            asyncio.create_task(self.do_memory_test(mem_size))
        
        async def do_memory_test(self, mem_size):
            """异步执行内存测试"""
            status = self.query_one("#status")
            
            try:
                # 在异步中执行测试
                result = await asyncio.to_thread(run_command, ["sudo", "memtester", mem_size, "1"])
                
                if result['status_code'] == 0:
                    success_message = "内存测试完成！未发现问题。"
                    status.update(f"[green]{success_message}[/green]")
                    self.show_success_dialog(success_message)
                else:
                    # 检查是否是被用户手动终止的
                    if current_process is None and not result['stderr']:
                        status.update("[yellow]测试已被用户终止。[/yellow]")
                    else:
                        error_message = f"内存测试失败！错误信息：{result['stderr']}"
                        status.update(f"[red]{error_message}[/red]")
                        self.show_error_dialog(error_message)
            
            except Exception as e:
                error_message = f"测试过程中发生错误: {str(e)}"
                status.update(f"[red]{error_message}[/red]")
                self.show_error_dialog(error_message)
            finally:
                # 恢复界面状态
                self.is_testing = False
                
                # 使用try/except捕获可能的NoMatches异常
                try:
                    stop_button = self.query_one("#stop-test", Button)
                    if stop_button:
                        stop_button.disabled = True
                    
                    memory_button = self.query_one("#memory-test", Button)
                    if memory_button:
                        memory_button.disabled = False
                    
                    cpu_button = self.query_one("#cpu-test", Button)
                    if cpu_button:
                        cpu_button.disabled = False
                except Exception as e:
                    # 记录错误但不中断程序
                    print(f"更新按钮状态时出错: {str(e)}")
        
        def start_cpu_test(self) -> None:
            """开始CPU测试"""
            def input_callback(duration):
                if duration and duration.isdigit() and int(duration) > 0:
                    self.run_cpu_test(duration)
                else:
                    self.show_error_dialog("请输入有效的时间（秒）！")
            
            self.push_screen(InputDialog("请输入 CPU 压测时长 (秒):", "60", input_callback))
        
        def run_cpu_test(self, duration):
            """执行CPU测试"""
            status = self.query_one("#status")
            
            message = f"正在进行 CPU 压测，持续 {duration} 秒...如需提前结束测试，请按Ctrl+C或点击停止按钮。"
            status.update(f"[blue]{message}[/blue]")
            
            # 更新界面状态
            self.is_testing = True
            
            # 使用try/except捕获可能的NoMatches异常
            try:
                stop_button = self.query_one("#stop-test", Button)
                if stop_button:
                    stop_button.disabled = False
                
                memory_button = self.query_one("#memory-test", Button)
                if memory_button:
                    memory_button.disabled = True
                
                cpu_button = self.query_one("#cpu-test", Button)
                if cpu_button:
                    cpu_button.disabled = True
            except Exception as e:
                # 记录错误但不中断程序
                print(f"更新按钮状态时出错: {str(e)}")
            
            # 创建异步任务
            asyncio.create_task(self.do_cpu_test(duration))
        
        async def do_cpu_test(self, duration):
            """异步执行CPU测试"""
            status = self.query_one("#status")
            
            try:
                # 在异步中执行测试
                result = await asyncio.to_thread(run_command, ["stress", "--cpu", "4", "--timeout", duration])
                
                if result['status_code'] == 0:
                    success_message = "CPU 压测完成！未发现问题。"
                    status.update(f"[green]{success_message}[/green]")
                    self.show_success_dialog(success_message)
                else:
                    # 检查是否是被用户手动终止的
                    if current_process is None and not result['stderr']:
                        status.update("[yellow]测试已被用户终止。[/yellow]")
                    else:
                        error_message = f"CPU 压测失败！错误信息：{result['stderr']}"
                        status.update(f"[red]{error_message}[/red]")
                        self.show_error_dialog(error_message)
            
            except Exception as e:
                error_message = f"测试过程中发生错误: {str(e)}"
                status.update(f"[red]{error_message}[/red]")
                self.show_error_dialog(error_message)
            finally:
                # 恢复界面状态
                self.is_testing = False
                
                # 使用try/except捕获可能的NoMatches异常
                try:
                    stop_button = self.query_one("#stop-test", Button)
                    if stop_button:
                        stop_button.disabled = True
                    
                    memory_button = self.query_one("#memory-test", Button)
                    if memory_button:
                        memory_button.disabled = False
                    
                    cpu_button = self.query_one("#cpu-test", Button)
                    if cpu_button:
                        cpu_button.disabled = False
                except Exception as e:
                    # 记录错误但不中断程序
                    print(f"更新按钮状态时出错: {str(e)}")
        
        def show_success_dialog(self, message: str) -> None:
            """显示成功对话框"""
            self.push_screen(SuccessDialog(message))
        
        def show_error_dialog(self, message: str) -> None:
            """显示错误对话框"""
            self.push_screen(ErrorDialog(message))

if __name__ == "__main__":
    args = parse_arguments()
    
    # 如果指定了命令行参数，则直接执行相应功能
    if args.memory:
        cli_memory_test()
        sys.exit(0)
    
    if args.cpu is not None:
        cli_cpu_test(args.cpu)
        sys.exit(0)
    
    # 如果没有指定命令行参数，则启动图形界面（如果textual可用）
    if HAS_TEXTUAL:
        app = SystemHealthApp()
        app.run()
    else:
        # 这种情况不应该发生，因为在导入时已经处理了，但为了代码完整性保留
        print("错误: 未安装textual库，无法启动图形界面。")
        print("您可以通过命令行参数使用此脚本的核心功能:")
        print("  内存测试:  python self_inspection.py --memory")
        print("  CPU测试:   python self_inspection.py --cpu [测试时长(秒)]")
        print("  查看帮助:  python self_inspection.py -h")
        sys.exit(1) 