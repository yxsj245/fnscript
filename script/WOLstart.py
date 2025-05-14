#!/usr/bin/env python
import os
import subprocess
import sys
import argparse

# 尝试导入textual库，如果不可用则使用命令行模式
try:
    from textual.app import App, ComposeResult
    from textual.widgets import Header, Footer, Static, Button, Label, Select, Input
    from textual.containers import Container, Horizontal, Vertical
    from textual.screen import Screen, ModalScreen
    import asyncio
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

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
                                          stderr=subprocess.PIPE, text=True)
        else:
            process_result = subprocess.run(command, check=True, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, text=True)
            
        result['stdout'] = process_result.stdout
        return result
    except subprocess.CalledProcessError as e:
        result['status_code'] = 1
        result['stderr'] = e.stderr
        if isinstance(result['stderr'], bytes):
            result['stderr'] = result['stderr'].decode(errors='ignore')
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
        print(f"{RED}获取 {interface} WOL状态失败: {result['stderr']}{RESET}")
        return "未知"
    
    wol_status_char = "未知"
    for line in result['stdout'].split("\n"):
        if "Wake-on:" in line: # 确保匹配的是 Wake-on: 行
            try:
                # 通常 Wake-on: g 或者 Wake-on: d
                status_part = line.split("Wake-on:")[1].strip()
                if status_part:
                    wol_status_char = status_part[0] # 取第一个字符，如 g 或 d
                break 
            except IndexError:
                pass # 如果分割失败，保持未知
    return wol_status_char

# 命令行功能实现
def cli_list_interfaces():
    """列出所有物理网络接口"""
    interfaces = get_network_interfaces()
    if not interfaces:
        print(f"{YELLOW}未找到物理网络接口。{RESET}")
        return
    print(f"{BOLD}可用的物理网络接口:{RESET}")
    for iface in interfaces:
        print(f"- {iface}")

def cli_check_wol_status(interface):
    """检查指定接口的WOL状态"""
    print(f"{BLUE}正在检查接口 {interface} 的WOL状态...{RESET}")
    status_char = check_wol_status(interface)
    
    if status_char == 'g':
        print(f"接口 {GREEN}{interface}{RESET} 的WOL状态: {GREEN}已启用 (g){RESET}")
    elif status_char == 'd':
        print(f"接口 {RED}{interface}{RESET} 的WOL状态: {RED}已禁用 (d){RESET}")
    elif status_char == "未知":
        print(f"接口 {YELLOW}{interface}{RESET} 的WOL状态: {YELLOW}未知 (无法获取或解析){RESET}")
    else: # 其他字符，例如 p, u, m, b, a, s
        print(f"接口 {YELLOW}{interface}{RESET} 的WOL状态: {YELLOW}支持, 但当前为: {status_char}{RESET}")

def cli_prevent_wol_auto_restore(interface: str):
    """防止NetworkManager等自动恢复WOL设置 (CLI版本)"""
    try:
        nm_check = run_command("which nmcli", shell=True)
        if nm_check['status_code'] != 0:
            print(f"{YELLOW}未检测到NetworkManager，跳过自动恢复配置。{RESET}")
            return True # 视为成功，因为没有NM来干扰

        nm_dir = "/etc/NetworkManager/conf.d"
        nm_file = f"{nm_dir}/90-disable-wol-{interface}.conf"
        
        # 确认目录存在
        # 使用 sudo 创建目录
        dir_check_cmd = f"sudo mkdir -p {nm_dir}"
        print(f"执行: {dir_check_cmd}")
        dir_check = run_command(dir_check_cmd, shell=True)
        if dir_check['status_code'] != 0:
            print(f"{RED}创建目录 {nm_dir} 失败: {dir_check['stderr']}{RESET}")
            return False
            
        # 创建配置文件内容
        config_content = f"[connection]\nmatch-device=interface-name:{interface}\nethernet.wake-on-lan=0"
        # 使用 sudo tee 写入文件
        write_cmd = f"echo -e '{config_content}' | sudo tee {nm_file}"
        print(f"执行: {write_cmd}")
        write_result = run_command(write_cmd, shell=True)
        if write_result['status_code'] != 0:
            print(f"{RED}创建NetworkManager配置文件 {nm_file} 失败: {write_result['stderr']}{RESET}")
            return False
            
        # 重启NetworkManager服务
        restart_cmd = "sudo systemctl restart NetworkManager"
        print(f"执行: {restart_cmd}")
        restart_result = run_command(restart_cmd, shell=True)
        if restart_result['status_code'] !=0:
            print(f"{YELLOW}重启 NetworkManager 可能失败或权限不足: {restart_result['stderr']}. 请手动重启以使更改生效。{RESET}")
            # 即使重启失败，配置文件已写入，所以不立即返回False
        
        print(f"{GREEN}已配置NetworkManager以防止接口 {interface} 自动恢复WOL设置。{RESET}")
        return True
    except Exception as e:
        print(f"{RED}配置NetworkManager时发生意外错误: {str(e)}{RESET}")
        return False

def cli_set_wol_status(interface, enable):
    """启用或禁用指定接口的WOL (CLI版本)"""
    action = "启用" if enable else "禁用"
    mode = "g" if enable else "d"
    
    print(f"{BLUE}正在为接口 {interface} {action} WOL...{RESET}")
    
    # 设置WOL状态
    cmd = f"sudo ethtool -s {interface} wol {mode}"
    print(f"执行: {cmd}")
    result = run_command(cmd, shell=True)
    if result['status_code'] != 0:
        print(f"{RED}{action}WOL失败: {result['stderr']}{RESET}")
        return False
    
    print(f"{GREEN}接口 {interface} 的WOL已成功{action}。{RESET}")
    
    # 配置自启动 (crontab)
    cron_job_enable = f"@reboot /sbin/ethtool -s {interface} wol g"
    # 先移除旧的该接口的WOL crontab 条目，避免重复
    cron_remove_cmd = f"(crontab -l 2>/dev/null | grep -v \"ethtool -s {interface} wol \" ; echo \"\" ) | crontab -"
    print(f"执行: {cron_remove_cmd}")
    run_command(cron_remove_cmd, shell=True) # 忽略错误，可能crontab为空

    if enable:
        cron_add_cmd = f"(crontab -l 2>/dev/null; echo \"{cron_job_enable}\") | crontab -"
        print(f"执行: {cron_add_cmd}")
        result = run_command(cron_add_cmd, shell=True)
        if result['status_code'] != 0:
            print(f"{RED}添加WOL自启动项到crontab失败: {result['stderr']}{RESET}")
        else:
            print(f"{GREEN}已添加WOL自启动项到crontab。{RESET}")
    else: # 禁用时，我们已经移除了所有相关的cron job
        print(f"{GREEN}已从crontab移除 {interface} 的WOL自启动项 (如有)。{RESET}")
        # 对于禁用操作，尝试配置NetworkManager
        if not cli_prevent_wol_auto_restore(interface):
            print(f"{YELLOW}警告: 可能无法完全阻止NetworkManager或其他服务自动恢复WOL设置。{RESET}")
            
    return True

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="网络唤醒 (Wake-on-LAN) 配置工具")
    parser.add_argument("--list-interfaces", action="store_true", help="列出可用的物理网络接口")
    parser.add_argument("--status", metavar="INTERFACE", help="检查指定网络接口的WOL状态")
    parser.add_argument("--enable", metavar="INTERFACE", help="为指定网络接口启用WOL")
    parser.add_argument("--disable", metavar="INTERFACE", help="为指定网络接口禁用WOL")
    parser.add_argument("--gui", action="store_true", help="启动图形用户界面 (如果textual可用)")
    return parser.parse_args()

def cli_main():
    """命令行模式主函数"""
    args = parse_arguments()

    if args.gui:
        if TEXTUAL_AVAILABLE:
            print(f"{BLUE}正在启动图形界面...{RESET}")
            app = WOLApp()
            app.run()
        else:
            print(f"{RED}错误: textual库未安装，无法启动图形界面。{RESET}")
            print(f"{YELLOW}请使用其他命令行参数或安装textual: pip install textual{RESET}")
        return

    if args.list_interfaces:
        cli_list_interfaces()
    elif args.status:
        cli_check_wol_status(args.status)
    elif args.enable:
        cli_set_wol_status(args.enable, True)
    elif args.disable:
        cli_set_wol_status(args.disable, False)
    else:
        # 如果没有提供有效参数 (除了 --gui)
        if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] == "--gui" and not TEXTUAL_AVAILABLE) :
             print(f"{YELLOW}未提供操作参数。使用 -h 或 --help 查看帮助。{RESET}")
             if not TEXTUAL_AVAILABLE:
                 print(f"{YELLOW}图形界面不可用 (textual 未安装)。{RESET}")
        elif not TEXTUAL_AVAILABLE and not any([args.list_interfaces, args.status, args.enable, args.disable]):
            # 如果textual不可用且没有其他有效参数
            print(f"{YELLOW}未提供有效操作参数。使用 -h 或 --help 查看帮助。{RESET}")
            print(f"{YELLOW}图形界面不可用 (textual 未安装)。{RESET}")

# 以下是基于textual的GUI代码
if TEXTUAL_AVAILABLE:
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
            self.wol_status_char = "未知" # 改为存储字符 g, d 等
        
        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            yield Footer()
            
            with Container(id="main-container"):
                yield Label("[b]网络唤醒（Wake-on-LAN）配置工具[/b]", id="title")
                
                with Container(id="interface-container"):
                    yield Label("加载网络接口中...", id="interface-label")
                    yield Select(id="interface-select", options=[("加载中...", "loading")], disabled=True)
                
                with Container(id="status-container"):
                    yield Label("Wake-on-LAN 状态: 未知", id="wol-status")
                
                with Container(id="action-buttons"):
                    yield Button("启用 Wake-on-LAN", id="enable-wol", disabled=True)
                    yield Button("禁用 Wake-on-LAN", id="disable-wol", disabled=True)
                
                yield Static("准备就绪，请选择网络接口。", id="status")
        
        def on_mount(self) -> None:
            self.load_interfaces()
        
        def action_refresh(self) -> None:
            self.load_interfaces()
        
        def load_interfaces(self) -> None:
            status = self.query_one("#status")
            status.update("正在加载网络接口...")
            asyncio.create_task(self.do_load_interfaces())
        
        async def do_load_interfaces(self) -> None:
            interface_label = self.query_one("#interface-label")
            status = self.query_one("#status")
            interface_select = self.query_one(Select) # 直接获取Select实例

            self.interfaces = await asyncio.to_thread(get_network_interfaces)
            
            if not self.interfaces:
                interface_label.update("[red]未找到物理网口！[/red]")
                interface_select.set_options([("未找到网络接口", "none")])
                interface_select.value = "none"
                interface_select.disabled = True
                self.query_one("#enable-wol").disabled = True
                self.query_one("#disable-wol").disabled = True
                status.update("[red]未找到可用的网络接口[/red]")
                return
            
            options = [(f"{iface}", iface) for iface in self.interfaces]
            interface_select.set_options(options) # 使用 set_options 更新选项
            
            if options:
                # 确保 Select 的 value 在 options 中
                initial_interface = options[0][1]
                interface_select.value = initial_interface # 这会自动触发 on_select_changed
                self.selected_interface = initial_interface
                await self.update_wol_status_display(initial_interface) # 手动调用一次以确保初始状态正确显示
            
            interface_label.update("[green]可用的网络接口：[/green]")
            interface_select.disabled = False
            status.update("网络接口加载完成")

        async def update_wol_status_display(self, interface: str) -> None:
            if not interface or interface == "none" or interface == "loading":
                self.query_one("#wol-status").update("Wake-on-LAN 状态: 未选择接口")
                self.query_one("#enable-wol").disabled = True
                self.query_one("#disable-wol").disabled = True
                return

            wol_status_label = self.query_one("#wol-status")
            status_widget = self.query_one("#status") # Renamed from 'status' to avoid conflict
            
            status_widget.update(f"正在检查 {interface} 的 Wake-on-LAN 状态...")
            
            self.wol_status_char = await asyncio.to_thread(check_wol_status, interface)
            
            if self.wol_status_char == 'g':
                wol_status_label.update(f"Wake-on-LAN 状态: [green]已启用 (g)[/green]")
                self.query_one("#enable-wol").disabled = True
                self.query_one("#disable-wol").disabled = False
            elif self.wol_status_char == 'd':
                wol_status_label.update(f"Wake-on-LAN 状态: [red]已禁用 (d)[/red]")
                self.query_one("#enable-wol").disabled = False
                self.query_one("#disable-wol").disabled = True
            elif self.wol_status_char == "未知":
                wol_status_label.update(f"Wake-on-LAN 状态: [yellow]未知[/yellow]")
                self.query_one("#enable-wol").disabled = True # 或者 False，取决于是否允许尝试启用
                self.query_one("#disable-wol").disabled = True
            else: # p, u, m, b, a, s 等
                wol_status_label.update(f"Wake-on-LAN 状态: [yellow]支持, 当前: {self.wol_status_char}[/yellow]")
                self.query_one("#enable-wol").disabled = False # 允许启用
                self.query_one("#disable-wol").disabled = False # 允许禁用 (变回 d)

            status_widget.update(f"{interface} 的 Wake-on-LAN 状态已更新")

        def on_select_changed(self, event: Select.Changed) -> None:
            self.selected_interface = str(event.value) #确保是字符串
            if self.selected_interface and self.selected_interface not in ["none", "loading"]:
                asyncio.create_task(self.update_wol_status_display(self.selected_interface))
            else: # 如果选择的是 "none" 或 "loading"
                self.query_one("#wol-status").update("Wake-on-LAN 状态: 未选择接口")
                self.query_one("#enable-wol").disabled = True
                self.query_one("#disable-wol").disabled = True
        
        def on_button_pressed(self, event: Button.Pressed) -> None:
            button_id = event.button.id
            
            if not self.selected_interface or self.selected_interface in ["none", "loading"]:
                self.query_one("#status").update("[red]请先选择一个有效的网络接口。[/red]")
                return

            if button_id == "enable-wol":
                asyncio.create_task(self.do_set_wol_gui(self.selected_interface, True))
            elif button_id == "disable-wol":
                asyncio.create_task(self.do_set_wol_gui(self.selected_interface, False))
        
        async def do_set_wol_gui(self, interface: str, enable: bool) -> None:
            """异步设置WOL状态 (GUI版本)"""
            status_widget = self.query_one("#status")
            mode = "g" if enable else "d"
            action_text = "启用" if enable else "禁用"
            
            status_widget.update(f"[blue]正在为 {interface} {action_text} Wake-on-LAN...[/blue]")
            
            cmd = f"sudo ethtool -s {interface} wol {mode}"
            result = await asyncio.to_thread(run_command, cmd, True)

            if result['status_code'] != 0:
                error_message = f"{action_text} Wake-on-LAN 失败！\n错误信息: {result['stderr']}"
                status_widget.update(f"[red]{error_message}[/red]")
                self.push_screen(ErrorDialog(error_message))
                return
            
            # 更新界面按钮和状态显示
            await self.update_wol_status_display(interface) # 这会根据新状态更新按钮
            
            # 配置自启动 (crontab) 和 NetworkManager
            cron_job_enable = f"@reboot /sbin/ethtool -s {interface} wol g"
            
            # 先移除旧的该接口的WOL crontab 条目
            cron_remove_cmd = f"(crontab -l 2>/dev/null | grep -v \"ethtool -s {interface} wol \" ; echo \"\" ) | crontab -"
            await asyncio.to_thread(run_command, cron_remove_cmd, shell=True)

            if enable:
                cron_add_cmd = f"(crontab -l 2>/dev/null; echo \"{cron_job_enable}\") | crontab -"
                cron_result = await asyncio.to_thread(run_command, cron_add_cmd, shell=True)
                if cron_result['status_code'] == 0:
                    self.push_screen(SuccessDialog(f"已为接口 {interface} {action_text} WOL并设置开机自启。"))
                else:
                    self.push_screen(ErrorDialog(f"为接口 {interface} {action_text} WOL成功，但设置开机自启失败: {cron_result['stderr']}"))
            else: # 禁用
                # 确保NetworkManager不会恢复设置
                nm_success = await asyncio.to_thread(cli_prevent_wol_auto_restore, interface) #复用CLI函数逻辑
                if nm_success:
                     self.push_screen(SuccessDialog(f"已为接口 {interface} {action_text} WOL，并已移除自启/配置NM。"))
                else:
                     self.push_screen(SuccessDialog(f"已为接口 {interface} {action_text} WOL，但NM配置可能未完全成功。"))
            
            status_widget.update(f"已完成 {interface} 的 Wake-on-LAN {action_text}操作")
            # 再次刷新状态确保一致性
            await asyncio.sleep(0.5) # 短暂等待 ethtool 生效
            await self.update_wol_status_display(interface)

if __name__ == "__main__":
    # 检查是否有命令行参数或者textual是否不可用
    # sys.argv[0] 是脚本名, 所以 len(sys.argv) > 1 表示有参数
    if len(sys.argv) > 1 and sys.argv[1] != '--gui':
        cli_main()
    elif sys.argv[1:] == ['--gui'] and TEXTUAL_AVAILABLE: # 明确请求GUI且可用
        app = WOLApp()
        app.run()
    elif not TEXTUAL_AVAILABLE: # Textual 不可用，强制CLI
        # 如果没有其他参数，cli_main会打印帮助信息
        cli_main()
    else: # 默认情况：无参数且Textual可用，则启动GUI
        app = WOLApp()
        app.run() 