#!/usr/bin/env python
import os
import subprocess
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
        print("  转换磁盘映像:  python qcowtools.py -s <源文件路径> [-t <目标文件名>] [-f <目标格式>]")
        print("  查看帮助:      python qcowtools.py -h")
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


# 工具函数
def clear_screen():
    """清空终端屏幕"""
    os.system('clear' if os.name == 'posix' else 'cls')


def run_command(command):
    """直接执行命令并返回执行结果，包括状态码和标准输出/错误"""
    result = {
        'status_code': 0,  # 默认状态码为 0 (正常执行)
        'stdout': '',  # 正常执行信息输出
        'stderr': ''  # 错误执行信息输出
    }

    try:
        # 执行命令并等待执行完成
        process_result = subprocess.run(command, check=True, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)

        # 获取标准输出内容
        result['stdout'] = process_result.stdout.decode()
        return result
    except subprocess.CalledProcessError as e:
        # 捕获异常，获取错误信息
        result['status_code'] = 1  # 设置状态码为 1，表示执行失败
        result['stderr'] = e.stderr.decode()
        return result


# qemu-img 转换函数
def convert_image(source_path, target_name=None, target_format='qcow2'):
    """使用 qemu-img 工具转换磁盘映像格式"""
    # 如果目标名称为空，使用默认目标文件名
    if not target_name:
        target_name = os.path.splitext(os.path.basename(source_path))[0] + '.' + target_format

    # 获取文件所在路径
    target_path = os.path.join(os.path.dirname(source_path), target_name)

    # 构造 qemu-img 命令
    command = ['qemu-img', 'convert', '-O', target_format, source_path, target_path]

    # 执行命令并返回结果
    return run_command(command)


# 命令行直接执行转换的函数
def cli_convert_image(source_path, target_name=None, target_format='qcow2'):
    """通过命令行直接转换磁盘映像
    
    Args:
        source_path (str): 源文件路径
        target_name (str, optional): 目标文件名，如果为None则自动生成
        target_format (str, optional): 目标格式，默认为qcow2
        
    Returns:
        bool: 是否成功转换
    """
    # 验证输入
    if not source_path:
        print("错误：请输入源文件路径！")
        return False
    
    # 确保文件路径存在
    if not os.path.isfile(source_path):
        print(f"错误：源文件不存在！路径：{source_path}")
        return False
    
    # 计算目标路径（用于显示）
    if not target_name:
        target_name = os.path.splitext(os.path.basename(source_path))[0] + '.' + target_format
    
    target_path = os.path.join(os.path.dirname(source_path), target_name)
    
    print(f"正在转换中,请稍后...(预计1分钟内完成)")
    
    # 执行转换
    result = convert_image(source_path, target_name, target_format)
    
    if result['status_code'] == 0:
        print(f"转换成功！目标文件路径：{target_path}")
        return True
    else:
        if 'Unknown file format' in result['stderr']:
            print(f"转换失败\n错误输出:未知文件格式\n建议操作：请确认输入的转换类型")
        else:
            print(f"转换失败！错误信息：{result['stderr']}")
        return False


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='QEMU 磁盘映像转换工具')
    parser.add_argument('-s', '--source', 
                        help='源文件路径')
    parser.add_argument('-t', '--target', 
                        help='目标文件名（可选，默认自动生成）')
    parser.add_argument('-f', '--format', default='qcow2',
                        help='目标格式（可选，默认为qcow2）')
    return parser.parse_args()


# 只有在导入了textual库的情况下才定义这些类
if HAS_TEXTUAL:
    # 添加成功提示对话框
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


    # 添加错误提示对话框
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


    class QcowToolsApp(App):
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
        
        #form-container {
            width: 100%;
            height: auto;
            margin: 1;
            border: solid $primary;
            padding: 1;
        }
        
        .form-label {
            text-style: bold;
            margin-bottom: 1;
            color: $text;
        }
        
        .form-field {
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
        
        #convert {
            background: $success;
            border: tall $success-lighten-2;
        }
        
        #clear {
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
            yield Header(show_clock=True)
            yield Footer()
            
            with Container(id="main-container"):
                yield Label("[b]QEMU 磁盘映像转换工具[/b]", id="title")
                
                with Container(id="form-container"):
                    yield Label("请输入源文件路径(右键需要转换文件的详细信息复制原始路径)：", classes="form-label")
                    yield Input(placeholder="例如: /path/to/source.img", id="source-path", classes="form-field")
                    
                    yield Label("请输入转换后的文件名称（例如:is.qcow2。您可以不写后缀，因为Linux不通过后缀名判断文件类型，但为了直观，我们推荐您写个后缀。）：", classes="form-label")
                    yield Input(placeholder="例如: converted.qcow2（留空则自动生成）", id="target-name", classes="form-field")
                    
                    yield Label("请输入转换的格式（默认使用qcow2）：", classes="form-label")
                    yield Input(placeholder="例如: qcow2", value="qcow2", id="target-format", classes="form-field")
                
                # 状态输出
                yield Static("准备就绪，请输入转换信息。", id="status")
            
            # 固定在底部的操作栏
            with Container(id="action-bar"):
                yield Button("开始转换", id="convert", variant="primary")
                yield Button("清空输入", id="clear", variant="success")

        def on_button_pressed(self, event: Button.Pressed) -> None:
            """按钮点击事件处理"""
            button_id = event.button.id
            
            if button_id == "convert":
                self.convert_image()
            elif button_id == "clear":
                self.clear_inputs()
        
        def clear_inputs(self) -> None:
            """清空所有输入框"""
            self.query_one("#source-path", Input).value = ""
            self.query_one("#target-name", Input).value = ""
            self.query_one("#target-format", Input).value = "qcow2"
            self.query_one("#status").update("已清空所有输入。")
        
        def convert_image(self) -> None:
            """开始转换图像"""
            # 获取输入值
            source_path = self.query_one("#source-path", Input).value
            target_name = self.query_one("#target-name", Input).value or None
            target_format = self.query_one("#target-format", Input).value or "qcow2"
            
            status = self.query_one("#status")
            
            # 验证输入
            if not source_path:
                status.update("[red]错误：请输入源文件路径！[/red]")
                self.show_error_dialog("请输入源文件路径！")
                return
            
            # 确保文件路径存在
            if not os.path.isfile(source_path):
                status.update(f"[red]错误：源文件不存在！路径：{source_path}[/red]")
                self.show_error_dialog(f"源文件不存在！\n路径：{source_path}")
                return
            
            # 更新状态
            status.update(f"[blue]正在转换中,请稍后...(预计1分钟内完成)[/blue]")
            
            # 创建异步任务
            asyncio.create_task(self.do_convert(source_path, target_name, target_format))
        
        async def do_convert(self, source_path, target_name, target_format):
            """异步执行转换操作"""
            status = self.query_one("#status")
            
            try:
                # 计算目标路径（用于显示）
                if not target_name:
                    target_name = os.path.splitext(os.path.basename(source_path))[0] + '.' + target_format
                
                target_path = os.path.join(os.path.dirname(source_path), target_name)
                
                # 在异步中执行转换
                result = await asyncio.to_thread(convert_image, source_path, target_name, target_format)
                
                if result['status_code'] == 0:
                    success_message = f"转换成功！目标文件路径：{target_path}"
                    status.update(f"[green]{success_message}[/green]")
                    self.show_success_dialog(success_message)
                else:
                    if 'Unknown file format' in result['stderr']:
                        error_message = f"转换失败\n错误输出:未知文件格式\n建议操作：请确认输入的转换类型"
                    else:
                        error_message = f"转换失败！错误信息：{result['stderr']}"
                    
                    status.update(f"[red]{error_message}[/red]")
                    self.show_error_dialog(error_message)
            
            except Exception as e:
                error_message = f"转换过程中发生错误: {str(e)}"
                status.update(f"[red]{error_message}[/red]")
                self.show_error_dialog(error_message)
        
        def show_success_dialog(self, message: str) -> None:
            """显示成功对话框"""
            self.push_screen(SuccessDialog(message))
        
        def show_error_dialog(self, message: str) -> None:
            """显示错误对话框"""
            self.push_screen(ErrorDialog(message))


if __name__ == "__main__":
    args = parse_arguments()
    
    # 如果指定了命令行参数，则直接执行相应功能
    if args.source:
        success = cli_convert_image(args.source, args.target, args.format)
        sys.exit(0 if success else 1)
    
    # 如果没有指定命令行参数，则启动图形界面（如果textual可用）
    if HAS_TEXTUAL:
        app = QcowToolsApp()
        app.run()
    else:
        # 这种情况不应该发生，因为在导入时已经处理了，但为了代码完整性保留
        print("错误: 未安装textual库，无法启动图形界面。")
        print("您可以通过命令行参数使用此脚本的核心功能:")
        print("  转换磁盘映像:  python qcowtools.py -s <源文件路径> [-t <目标文件名>] [-f <目标格式>]")
        print("  查看帮助:      python qcowtools.py -h")
        sys.exit(1) 