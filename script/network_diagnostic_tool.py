#!/usr/bin/env python
import os
import subprocess
import sys
import argparse
import re
import ipaddress # For IP address manipulation and gateway inference
import logging

# --- 日志配置 ---
LOG_FILENAME = 'network_diag_tool.log'
# 获取当前脚本所在的目录，日志文件将创建在该目录下
# current_script_directory = os.path.dirname(os.path.abspath(__file__))
# log_file_path = os.path.join(current_script_directory, LOG_FILENAME)
# ^-- 上述方法在打包后可能不适用，直接使用文件名，将在当前工作目录创建日志

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(funcName)s - %(lineno)d - %(message)s',
    filename=LOG_FILENAME,
    filemode='w'  # 'w' 每次运行时覆盖日志, 'a' 为追加
)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO) # 控制台只输出 INFO 及以上级别
formatter = logging.Formatter('%(levelname)s: %(message)s')
console_handler.setFormatter(formatter)
# logging.getLogger('').addHandler(console_handler) # 如果需要在控制台也看到日志，取消此行注释

logging.info("网络诊断工具开始运行")

# Attempt to import textual
TEXTUAL_AVAILABLE = False
try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, VerticalScroll, Horizontal
    from textual.widgets import Header, Footer, Static, Button, Label, Select, Markdown, Input # 添加 Input
    from textual.screen import ModalScreen
    from textual.reactive import reactive
    import asyncio
    from textual.events import Key # 导入 Key 事件
    TEXTUAL_AVAILABLE = True
except ImportError:
    # Fallback if textual is not available and GUI is requested
    pass

# Color constants for CLI
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

# --- 推荐的 DNS 服务器 ---
PRIMARY_DNS = "223.5.5.5"
SECONDARY_DNS = "223.6.6.6"

# --- Helper Functions ---
def run_command(command, shell=False, text=True):
    """Executes a command and returns its output, status code, and error."""
    try:
        logging.debug(f"执行命令: {' '.join(command) if isinstance(command, list) else command}")
        process = subprocess.run(
            command,
            shell=shell,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=text
        )
        logging.debug(f"命令 '{command[0] if isinstance(command, list) else command.split()[0]}' stdout: {process.stdout.strip()}")
        if process.stderr.strip():
            logging.debug(f"命令 '{command[0] if isinstance(command, list) else command.split()[0]}' stderr: {process.stderr.strip()}")
        return process.stdout.strip(), process.stderr.strip(), process.returncode
    except subprocess.CalledProcessError as e:
        logging.error(f"命令 '{command[0] if isinstance(command, list) else command.split()[0]}' 执行失败. Code: {e.returncode}")
        logging.error(f"  Stdout: {e.stdout.strip() if e.stdout else ''}")
        logging.error(f"  Stderr: {e.stderr.strip() if e.stderr else str(e)}")
        return e.stdout.strip() if e.stdout else "", e.stderr.strip() if e.stderr else str(e), e.returncode
    except FileNotFoundError:
        logging.error(f"命令未找到: {command[0] if isinstance(command, list) else command.split()[0]}")
        return "", f"命令未找到: {command[0] if isinstance(command, list) else command.split()[0]}", 127

def get_network_interfaces_details():
    """
    获取网络接口的详细信息 (名称, IP/掩码, MAC, 网关, 类型)。
    返回一个字典: {接口名称: {详情}}
    """
    logging.debug("开始获取网络接口详情")
    interfaces = {}
    
    # 使用 'ip addr' 获取 IP 地址、MAC 地址和接口状态
    stdout, stderr, code = run_command(['ip', 'addr'])
    if code != 0:
        logging.error(f"执行 'ip addr' 失败: {stderr}")
        print(f"{RED}获取 IP 地址信息出错: {stderr}{RESET}") # 中文错误信息
        return interfaces
    logging.debug(f"'ip addr' 输出:\n{stdout}")

    current_iface_name = None # 使用一个更清晰的变量名
    for line_num, line in enumerate(stdout.splitlines()):
        stripped_line = line.strip()
        logging.debug(f"处理行 {line_num + 1} [current_iface: {current_iface_name}]: {stripped_line}")

        # --- BEGIN DEBUG BLOCK ---
        if line_num == 0: # 只对第一行执行一次硬编码测试，避免日志过多
            test_string = "1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue"
            # 使用与下面相同的正则表达式进行测试
            regex_to_test = r'^\d+:\s+(\S+):\s+<([^>]*)>.*'
            test_match = re.match(regex_to_test, test_string)
            if test_match:
                logging.debug(f"  硬编码测试字符串匹配成功: groups={test_match.groups()} using regex: {regex_to_test}")
            else:
                logging.debug(f"  硬编码测试字符串 '{test_string}' 匹配失败 using regex: {regex_to_test}")
        
        logging.debug(f"  尝试匹配实际行 (类型: {type(stripped_line)}, 内容 repr: {repr(stripped_line)}) using regex: r'^\d+:\s+(\S+):\s+<([^>]*)>.*'")
        # --- END DEBUG BLOCK ---

        # 尝试匹配接口定义行 (e.g., "1: lo: <...>")
        # 使用更具弹性的空格匹配 (\s+) 代替固定的单个空格
        match_interface_def = re.match(r'^\d+:\s+(\S+):\s+<([^>]*)>.*', stripped_line)

        if match_interface_def:
            iface_name = match_interface_def.group(1)
            iface_attrs = match_interface_def.group(2)
            logging.debug(f"  匹配到接口定义: {iface_name}, 属性: {iface_attrs}")
            
            current_iface_name = iface_name # 立即设置当前接口上下文

            if current_iface_name == 'lo':
                logging.debug(f"    跳过环回接口 {current_iface_name}, 重置上下文为 None")
                current_iface_name = None # 对于'lo'后续不处理其IP/MAC
                continue # 跳过lo接口的 further processing in this loop iteration for other properties
            
            # 为新接口（非lo）初始化条目
            interfaces[current_iface_name] = {
                'name': current_iface_name,
                'ips': [],
                'mac': None,
                'gateway': None, # 网关稍后从 'ip route' 获取
                'state': 'DOWN'
            }
            if 'UP' in iface_attrs.split(','):
                interfaces[current_iface_name]['state'] = 'UP'
                logging.debug(f"    接口 {current_iface_name} 状态设置为 UP")
            else:
                logging.debug(f"    接口 {current_iface_name} 状态为 DOWN 或未明确为 UP")
        
        elif current_iface_name: # 只有在当前有活动接口上下文时才尝试解析IP/MAC
            # 尝试匹配 MAC 地址 (link/ether)
            match_mac = re.search(r'link/ether (([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})', stripped_line)
            if match_mac:
                interfaces[current_iface_name]['mac'] = match_mac.group(1)
                logging.debug(f"    为接口 {current_iface_name} 设置 MAC: {match_mac.group(1)}")
            else:
                # 尝试匹配 IP 地址 (inet)
                match_ip = re.search(r'inet (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2})', stripped_line)
                if match_ip:
                    interfaces[current_iface_name]['ips'].append(match_ip.group(1))
                    logging.debug(f"    为接口 {current_iface_name} 添加 IP: {match_ip.group(1)}")
                else:
                    # 既不是接口定义，也不是MAC，也不是IP，但有上下文
                    logging.debug(f"    接口 {current_iface_name} 的其他信息行: {stripped_line}")
        else:
            # 没有当前接口上下文，也不是新的接口定义行
            logging.debug(f"    当前无活动接口 ({current_iface_name})，也不是新接口定义，跳过行: {stripped_line}")


    # 使用 'ip route show default' 获取默认网关信息
    stdout_route, stderr_route, code_route = run_command(['ip', 'route', 'show', 'default'])
    if code_route == 0 and stdout_route:
        logging.debug(f"'ip route show default' 输出:\n{stdout_route}")
        for line in stdout_route.splitlines():
            if match := re.search(r'default via (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) dev (\S+)', line):
                gw_ip = match.group(1)
                gw_dev = match.group(2)
                if gw_dev in interfaces:
                    interfaces[gw_dev]['gateway'] = gw_ip
                    # 对于同一子网上的其他接口，如果未明确设置，这可能也是它们的网关
                    # 这是一个简化处理；可能存在复杂的路由。
                    try:
                        gw_network = ipaddress.ip_interface(f"{interfaces[gw_dev]['ips'][0]}").network if interfaces[gw_dev]['ips'] else None
                        for if_name, if_data in interfaces.items():
                            if if_name != gw_dev and not if_data['gateway'] and if_data['ips']:
                                if_ip_obj = ipaddress.ip_interface(if_data['ips'][0])
                                if gw_network and if_ip_obj.network == gw_network:
                                     interfaces[if_name]['gateway'] = gw_ip # 如果在同一子网则分配
                    except Exception as e: # 捕获 ipaddress 可能产生的广泛错误
                        logging.warning(f"在为接口 {if_name} 推断网关时发生错误: {e}")
                        pass
    elif code_route != 0:
        logging.warning(f"执行 'ip route show default' 失败: {stderr_route}")


    # 尝试确定配置模式 (DHCP/静态) - 这是一个基本检查
    for if_name, data in interfaces.items():
        data['config_mode'] = '未知' # 默认
        logging.debug(f"尝试为接口 {if_name} 获取配置模式")

        if check_command_exists("nmcli"):
            conn_name_stdout, _, conn_name_code = run_command([
                'nmcli', '-g', 'GENERAL.CONNECTION', 'device', 'show', if_name
            ])
            
            resolved_method_from_conn = False
            if conn_name_code == 0 and conn_name_stdout and conn_name_stdout.strip():
                conn_name = conn_name_stdout.strip()
                logging.debug(f"接口 {if_name} 的活动连接配置文件为: {conn_name}")
                conn_show_stdout, _, conn_show_code = run_command([
                    'nmcli', '-t', 'connection', 'show', conn_name
                ])
                if conn_show_code == 0 and conn_show_stdout:
                    logging.debug(f"'nmcli connection show {conn_name}' 输出:\n{conn_show_stdout}")
                    method_line = next((line for line in conn_show_stdout.splitlines() if 'ipv4.method:' in line.lower()), None)
                    if method_line:
                        method = method_line.split(':')[1].lower()
                        logging.debug(f"  接口 {if_name} (连接 {conn_name}) 的 ipv4.method 为: {method}")
                        if 'auto' in method:
                            data['config_mode'] = 'DHCP'
                        elif 'manual' in method:
                            data['config_mode'] = '静态'
                        elif 'disabled' in method:
                            data['config_mode'] = '已禁用'
                        # else: config_mode 保持未知
                        logging.debug(f"  接口 {if_name} 配置模式根据连接配置文件设置为: {data['config_mode']}")
                        resolved_method_from_conn = True 
                    else:
                        logging.debug(f"  在连接配置文件 {conn_name} 中未找到 ipv4.method")
                else:
                    logging.warning(f"'nmcli connection show {conn_name}' 执行失败或无输出。")
            else:
                logging.debug(f"接口 {if_name} 未找到活动的 NetworkManager 连接配置文件。")

            # 如果通过 connection show 未能解析出方法，再尝试旧的 dev show (作为回退，尽管它在当前环境报错)
            # 或者直接跳过，依赖后续的ip addr判断
            # 当前，如果 resolved_method_from_conn 为 False，我们会让后续逻辑处理
            if not resolved_method_from_conn:
                logging.debug(f"未能从连接配置文件确定 {if_name} 的配置模式，尝试其他方法或回退。")
                # 旧的 nmcli dev show 逻辑，它在您的系统上会失败，但为了完整性可以保留或注释掉
                # logging.debug(f"尝试使用 'nmcli dev show {if_name}' 获取 IP4.METHOD (已知在某些环境会失败)")
                # nm_dev_stdout, nm_dev_stderr, nm_dev_code = run_command(['nmcli', '-t', '-f', 'IP4.METHOD', 'dev', 'show', if_name])
                # if nm_dev_code == 0 and nm_dev_stdout: ... (旧逻辑)
                # else: logging.warning(...) 
        else:
            logging.info("nmcli 命令不存在，跳过 NetworkManager 的配置模式检查。")

        # 基于 IP 地址的回退逻辑 (如果 config_mode 仍然是 '未知')
        if data['config_mode'] == '未知':
            logging.debug(f"接口 {if_name} 的 config_mode 仍为 '未知'，使用基于IP的回退逻辑。")
            if data['ips']: # 如果接口有IP地址
                # 如果有IP但NM未能确定为DHCP，倾向于认为是静态或手动配置
                logging.debug(f"  接口 {if_name} 有IP地址，NetworkManager 未明确其模式。假定为 静态/手动。")
                data['config_mode'] = '静态/手动' 
            else: # 如果接口没有IP地址
                # 如果没有IP且NM信息不可用或不明确，更可能是DHCP失败或未配置
                logging.debug(f"  接口 {if_name} 无IP地址，NetworkManager 未明确其模式。假定为 DHCP (可能失败或未配置)。")
                data['config_mode'] = 'DHCP (回退假设)'
        logging.info(f"接口 {if_name} 最终确定的配置模式: {data['config_mode']}")

    valid_interfaces = {k: v for k, v in interfaces.items() if k != 'lo'}
    logging.debug(f"获取到的接口详情: {valid_interfaces}")
    logging.debug("完成获取网络接口详情")
    return valid_interfaces


def get_dns_servers():
    """获取当前 DNS 服务器。"""
    # 首先尝试 systemd-resolve
    stdout, stderr, code = run_command(['resolvectl', 'dns'])
    if code == 0 and stdout:
        logging.debug(f"'resolvectl dns' 输出:\n{stdout}")
        # 格式: "Global: 1.1.1.1 8.8.8.8 Link 2 (eth0): 192.168.1.1 ..."
        # 我们关心的是有效的 DNS 服务器，通常在 "Global:" 或特定链接之后。
        # 为简单起见，获取列出的所有 IP。
        matches = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', stdout)
        if matches:
            # 如果本地/链路本地 DNS 不是主要的 (例如路由器充当 DNS 代理)，则过滤掉它们
            # 这是一种启发式方法。正确的方法是了解哪些 DNS 服务器正在被积极使用。
            # 目前，返回所有找到的唯一 IP。
            unique_dns = sorted(list(set(matches)))
            # 如果有全局 DNS，则优先使用
            if "Global:" in stdout:
                global_dns_line = stdout.split("Global:")[1].split("Link ")[0]
                global_dns = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', global_dns_line)
                if global_dns:
                    return sorted(list(set(global_dns)))
            return unique_dns
    elif code != 0:
        logging.warning(f"'resolvectl dns' 执行失败: {stderr}")

    # 回退到 /etc/resolv.conf
    try:
        with open('/etc/resolv.conf', 'r') as f:
            content = f.read()
        dns_servers = re.findall(r'^nameserver\s+(\S+)', content, re.MULTILINE)
        return dns_servers
    except FileNotFoundError:
        logging.warning("无法找到 /etc/resolv.conf 文件")
        return []

def ping_host(host, count=3, timeout_ms=1000):
    """Pings a host and returns success (bool), average latency (ms), and loss (%)."""
    # 注意: '-w' 用于设置总超时 (秒), '-W' 用于设置每次 ping 的超时 (秒)。
    # 对于毫秒级超时，我们可能需要调整或使用更精确的 ping 命令。
    # 标准 ping 超时通常以秒为单位。我们将使用 -W 1 (1 秒)。
    command = ['ping', '-c', str(count), '-W', '1', host]
    stdout, stderr, code = run_command(command)
    logging.debug(f"Ping stdout for {host}:\n{stdout}") # 记录完整的 ping 输出
    logging.debug(f"Ping stderr for {host}:\n{stderr}")
    logging.debug(f"Ping return code for {host}: {code}")

    if code != 0:
        # 即使 ping 命令失败，也记录一下stdout，可能包含有用信息
        return False, float('inf'), 100.0

    loss_match = re.search(r'(\d+)% packet loss', stdout)
    # Ubuntu ping输出: rtt min/avg/max/mdev = 0.045/0.049/0.053/0.003 ms
    # Alpine ping输出: round-trip min/avg/max = 0.045/0.049/0.053 ms
    # 确保这里是单反斜杠 \d
    rtt_regex = r'(min/avg/max(?:/mdev)?|round-trip min/avg/max) = (?:\d+\.\d+/)?(\d+\.\d+)(?:/\d+\.\d+)?(?:/\d+\.\d+)?'
    rtt_match = re.search(rtt_regex, stdout)
    logging.debug(f"RTT regex used: {rtt_regex}") # 移除日志中多余的引号

    avg_latency = float('inf') # 默认值
    loss = 100.0 # 默认值

    if loss_match:
        loss = float(loss_match.group(1))
        logging.debug(f"Parsed loss for {host}: {loss}% (from group: '{loss_match.group(1)}')")
    else:
        logging.warning(f"Could not parse packet loss for {host} from stdout.")

    if rtt_match:
        try:
            avg_rtt_str = rtt_match.group(2)
            logging.debug(f"RTT match groups for {host}: {rtt_match.groups()} (attempting to parse group 2: '{avg_rtt_str}')")
            avg_latency = float(avg_rtt_str)
            logging.debug(f"Successfully parsed avg_latency for {host}: {avg_latency} ms")
        except (IndexError, ValueError) as e:
            avg_rtt_str_val = avg_rtt_str if 'avg_rtt_str' in locals() else 'N/A' # 安全访问
            logging.error(f"Error parsing RTT for {host} from rtt_match.group(2) ('{avg_rtt_str_val}'). Error: {e}")
            # avg_latency 保持 float('inf')
    else:
        logging.warning(f"Could not parse RTT (min/avg/max) for {host} from stdout. rtt_match is None.")
    
    return loss < 100, avg_latency, loss # 如果有数据包成功返回则为 True

def curl_check(url="http://www.baidu.com"):
    """使用 curl 检查互联网连接性。"""
    # -s 静默模式, -S 显示错误, -L 跟随重定向, -I 仅请求头部, -m 超时
    command = ['curl', '-sSLI', '-m', '5', url] 
    stdout, stderr, code = run_command(command)
    if code == 0 and "HTTP/" in stdout: # 检查是否有任何 HTTP 响应
        # 进一步检查 2xx 或 3xx 状态码
        if re.search(r"HTTP/\d(\.\d)? (2\d\d|3\d\d)", stdout):
            return True, f"成功连接到 {url} (通过 curl)。"
        else:
            http_status_line = next((line for line in stdout.splitlines() if "HTTP/" in line), "未找到 HTTP 状态行")
            return False, f"已连接到 {url} 但收到非成功状态: {http_status_line} (通过 curl)。"
    return False, f"使用 curl 连接到 {url} 失败。代码: {code}, 错误: {stderr if stderr else '无特定错误输出。'}"

def check_command_exists(command_name):
    """检查指定的命令是否存在于系统中。"""
    logging.debug(f"检查命令 '{command_name}' 是否存在")
    try:
        subprocess.run([command_name, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        logging.debug(f"命令 '{command_name}' 存在。")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        try: # 有些命令可能没有 --version, 尝试 help
            subprocess.run([command_name, '--help'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            logging.debug(f"命令 '{command_name}' 存在 (通过 --help 检查)。")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logging.debug(f"命令 '{command_name}' 不存在。")
            return False

def try_set_dns(interface_name, dns_servers_to_set):
    """
    尝试为指定接口设置 DNS 服务器。
    返回一个元组 (success: bool, message: str)。
    如果 success 为 True，message 包含建议执行的命令。
    如果 success 为 False，message 包含错误或回退建议。
    """
    logging.info(f"尝试为接口 {interface_name} 生成设置 DNS 为 {dns_servers_to_set} 的命令")
    dns_str = " ".join(dns_servers_to_set)

    has_resolvectl = check_command_exists("resolvectl")
    has_nmcli = check_command_exists("nmcli")

    commands = []
    if has_resolvectl:
        # systemd-resolved
        # resolvectl dns <link> <addr>... (立即生效，可能临时)
        commands.append(['sudo', 'resolvectl', 'dns', interface_name] + dns_servers_to_set)
        # 提示信息可以由调用者根据执行结果添加
        logging.info(f"为 resolvectl 生成 DNS 设置命令: {commands}")
        return True, commands
    elif has_nmcli:
        # NetworkManager - 使用 con (connection) 相关命令
        logging.debug(f"尝试获取接口 {interface_name} 的 NetworkManager 连接配置文件名称")
        # stdout, stderr, code = run_command(['nmcli', '-t', '-f', 'NAME', 'c', 'show', '--active', 'dev', interface_name]) #  旧方法可能不直接
        # 更直接的方法获取连接名称:
        stdout_conn_name, stderr_conn_name, code_conn_name = run_command([
            'nmcli', '-g', 'GENERAL.CONNECTION', 'device', 'show', interface_name
        ])

        if code_conn_name == 0 and stdout_conn_name and stdout_conn_name.strip():
            conn_name = stdout_conn_name.strip()
            logging.info(f"找到接口 {interface_name} 的活动连接配置文件: {conn_name}")
            commands.append(['sudo', 'nmcli', 'con', 'mod', conn_name, 'ipv4.dns', dns_str])
            commands.append(['sudo', 'nmcli', 'con', 'mod', conn_name, 'ipv4.ignore-auto-dns', 'yes'])
            commands.append(['sudo', 'nmcli', 'con', 'down', conn_name])
            commands.append(['sudo', 'nmcli', 'con', 'up', conn_name])
            logging.info(f"为 nmcli (connection: {conn_name}) 生成 DNS 设置命令序列: {commands}")
            return True, commands
        else:
            logging.warning(
                f"无法确定接口 {interface_name} 的 NetworkManager 连接配置文件名称。 "
                f"Code: {code_conn_name}, Stdout: '{stdout_conn_name}', Stderr: '{stderr_conn_name}'. "
                f"将回退到尝试使用 'nmcli dev mod' (如果适用) 或失败。"
            )
            # 回退逻辑: 如果无法获取 conn_name，可以尝试之前的 dev mod (但可能效果不同或不适用所有情况)
            # 或者直接报告错误。为了更符合用户请求的 con mod 方式，这里我们将报告获取 conn_name 失败。
            error_msg = (
                f"{YELLOW}无法确定接口 {interface_name} 的 NetworkManager 活动连接配置文件。{RESET}\n"
                f"因此无法使用 'nmcli con mod' 系列命令进行 DNS 修改。\n"
                f"请确保接口由 NetworkManager 管理并且有一个活动的连接配置文件。"
            )
            return False, error_msg
    else:
        msg = (
            f"{YELLOW}系统中未找到 'resolvectl' 或 'nmcli' 命令。无法自动执行 DNS 设置。{RESET}\n"
            f"请手动配置 DNS。通常这涉及编辑 {BOLD}/etc/resolv.conf{RESET} (如果它不是由其他服务自动生成的)，\n"
            f"或者根据您的 Linux 发行版和网络管理工具 (如 netplan, ifupdown 等) 修改相应的配置文件。\n"
            f"建议的 DNS 服务器: {PRIMARY_DNS}, {SECONDARY_DNS}"
        )
        logging.warning("未找到 resolvectl 或 nmcli，无法自动生成 DNS 设置命令。")
        return False, msg

async def execute_sudo_commands_and_report(commands_to_run: list[list[str]], interface_name: str):
    """
    执行 sudo 命令列表并报告每个命令的结果。
    返回一个元组 (overall_success: bool, report_str: str)。
    """
    logging.info(f"准备执行为接口 {interface_name} 生成的修复命令: {commands_to_run}")
    report_parts = [f"开始为接口 {BOLD}{interface_name}{RESET} 执行自动修复命令:"]
    overall_success = True

    for i, command_args in enumerate(commands_to_run):
        cmd_str_display = " ".join(command_args)
        report_parts.append(f"\n{BOLD}执行命令 {i+1}/{len(commands_to_run)}:{RESET} {CYAN}{cmd_str_display}{RESET}")
        
        # 使用 asyncio.to_thread 运行阻塞的 run_command
        stdout, stderr, code = await asyncio.to_thread(run_command, command_args)
        
        if code == 0:
            report_parts.append(f"  {GREEN}成功。{RESET}")
            if stdout:
                report_parts.append(f"  {WHITE}输出:{RESET}\n{stdout}")
            if stderr: # 有些成功命令也可能有 stderr 输出 (例如警告)
                report_parts.append(f"  {YELLOW}警告/标准错误输出:{RESET}\n{stderr}")
        else:
            overall_success = False
            report_parts.append(f"  {RED}失败 (返回码: {code})。{RESET}")
            if stdout:
                report_parts.append(f"  {WHITE}标准输出:{RESET}\n{stdout}")
            if stderr:
                report_parts.append(f"  {RED}错误输出:{RESET}\n{stderr}")
            report_parts.append(f"  {YELLOW}由于命令 '{cmd_str_display}' 失败，后续命令可能不会产生预期效果。{RESET}")
            # 可以选择在这里中断，但为了完整性，我们继续执行并报告所有命令
            # break 

    if overall_success:
        report_parts.append(f"\n{GREEN}所有修复命令均已成功执行或未报告严重错误。{RESET}")
        report_parts.append(f"{YELLOW}请重新进行网络诊断以确认问题是否已解决。{RESET}")
    else:
        report_parts.append(f"\n{RED}部分或全部修复命令执行失败。{RESET}")
        report_parts.append(f"{YELLOW}请检查上面的输出以了解详细信息。您可能需要手动执行相关命令或检查权限。{RESET}")

    final_report = "\n".join(report_parts)
    logging.info(f"修复命令执行完毕。总体成功: {overall_success}. 报告:\n{final_report}")
    return overall_success, final_report

def try_set_dhcp(interface_name):
    """
    尝试为指定接口的 NetworkManager 连接配置文件设置为 DHCP (IPv4 和 IPv6)。
    返回一个元组 (success: bool, commands_or_error_msg: Union[List[List[str]], str])。
    """
    logging.info(f"尝试为接口 {interface_name} 生成切换到 DHCP 模式的命令")
    
    if not check_command_exists("nmcli"):
        logging.warning("nmcli 命令不存在，无法切换到 DHCP 模式。")
        return False, f"{YELLOW}nmcli 命令不存在，无法自动切换到 DHCP 模式。{RESET}"

    # 获取连接配置文件名称
    stdout_conn_name, stderr_conn_name, code_conn_name = run_command([
        'nmcli', '-g', 'GENERAL.CONNECTION', 'device', 'show', interface_name
    ])

    if code_conn_name == 0 and stdout_conn_name and stdout_conn_name.strip():
        conn_name = stdout_conn_name.strip()
        logging.info(f"找到接口 {interface_name} 的活动连接配置文件: {conn_name}，准备设置为 DHCP")
        commands = []
        commands.append(['sudo', 'nmcli', 'con', 'mod', conn_name, 'ipv4.method', 'auto'])
        commands.append(['sudo', 'nmcli', 'con', 'mod', conn_name, 'ipv4.dns', '"'])
        commands.append(['sudo', 'nmcli', 'con', 'mod', conn_name, 'ipv6.method', 'auto'])
        commands.append(['sudo', 'nmcli', 'con', 'down', conn_name])
        commands.append(['sudo', 'nmcli', 'con', 'up', conn_name])
        logging.info(f"为 nmcli (connection: {conn_name}) 生成切换到 DHCP 的命令序列: {commands}")
        return True, commands
    else:
        logging.warning(
            f"无法确定接口 {interface_name} 的 NetworkManager 连接配置文件名称。 "
            f"Code: {code_conn_name}, Stdout: '{stdout_conn_name}', Stderr: '{stderr_conn_name}'."
        )
        error_msg = (
            f"{YELLOW}无法确定接口 {interface_name} 的 NetworkManager 活动连接配置文件。{RESET}\n"
            f"因此无法自动切换到 DHCP 模式。\n"
            f"请确保接口由 NetworkManager 管理并且有一个活动的连接配置文件。"
        )
        return False, error_msg

def ping_check_ip_conflict(ip_address: str) -> bool:
    """
    通过发送 ping 来检查 IP 地址是否已在网络上使用。
    如果收到 ping 回复 (冲突)，则返回 True，否则返回 False。
    """
    logging.info(f"正在使用 ping 检查 IP {ip_address} 是否冲突。")
    try:
        # 使用 ping_host 发送少量 ping 包，并设置较短的超时时间。
        # 如果 ping_host 返回 True (表示 loss < 100%)，则认为 IP 地址被占用。
        # count=1, timeout_ms=500 (ping_host 内部会将 timeout_ms 用于 -W 参数，单位秒)
        # ping_host 的 -W 参数是以秒为单位，当前硬编码为1秒。count=1就足够了。
        is_reachable, _, _ = ping_host(ip_address, count=1) 
        
        if is_reachable:
            logging.warning(f"检测到 IP {ip_address} 冲突。Ping 成功。")
            return True # 冲突
        else:
            logging.info(f"未检测到 IP {ip_address} 冲突。Ping 失败或超时。")
            return False # 无冲突
    except Exception as e:
        # 如果 ping_host 本身执行出错 (例如命令找不到等)，为安全起见，也认为无冲突。
        logging.error(f"检查 IP {ip_address} 冲突时发生错误: {e}")
        return False # 假设无冲突

def try_set_static_ip(interface_name: str, ip_address: str, prefix: str, gateway: str | None, dns_servers: list[str] | None):
    """
    尝试为指定接口的 NetworkManager 连接配置文件设置静态 IP。
    返回一个元组 (success: bool, commands_or_error_msg: Union[List[List[str]], str])。
    """
    logging.info(f"尝试为接口 {interface_name} 生成设置静态 IP ({ip_address}/{prefix}) 的命令")

    if not check_command_exists("nmcli"):
        logging.warning("nmcli 命令不存在，无法设置静态 IP。")
        return False, f"{YELLOW}nmcli 命令不存在，无法自动设置静态 IP。{RESET}"

    # 获取连接配置文件名称
    stdout_conn_name, stderr_conn_name, code_conn_name = run_command([
        'nmcli', '-g', 'GENERAL.CONNECTION', 'device', 'show', interface_name
    ])

    if code_conn_name == 0 and stdout_conn_name and stdout_conn_name.strip():
        conn_name = stdout_conn_name.strip()
        logging.info(f"找到接口 {interface_name} 的活动连接配置文件: {conn_name}，准备设置为静态 IP")
        
        commands = []
        commands.append(['sudo', 'nmcli', 'con', 'mod', conn_name, 'ipv4.method', 'manual'])
        commands.append(['sudo', 'nmcli', 'con', 'mod', conn_name, 'ipv4.addresses', f"{ip_address}/{prefix}"])

        if gateway and gateway.strip():
            commands.append(['sudo', 'nmcli', 'con', 'mod', conn_name, 'ipv4.gateway', gateway.strip()])
            logging.debug(f"为连接 {conn_name} 设置网关: {gateway.strip()}")
        else:
            # 如果未提供网关，显式清除它
            commands.append(['sudo', 'nmcli', 'con', 'mod', conn_name, 'ipv4.gateway', '""'])
            logging.debug(f"为连接 {conn_name} 清除网关设置")

        if dns_servers:
            dns_str = " ".join(dns_servers)
            commands.append(['sudo', 'nmcli', 'con', 'mod', conn_name, 'ipv4.dns', dns_str])
            commands.append(['sudo', 'nmcli', 'con', 'mod', conn_name, 'ipv4.ignore-auto-dns', 'yes'])
            logging.debug(f"为连接 {conn_name} 设置 DNS: {dns_str} 和 ignore-auto-dns=yes")
        else:
            # 如果未提供 DNS 服务器，显式清除它们并设置 ignore-auto-dns
            commands.append(['sudo', 'nmcli', 'con', 'mod', conn_name, 'ipv4.dns', '""'])
            commands.append(['sudo', 'nmcli', 'con', 'mod', conn_name, 'ipv4.ignore-auto-dns', 'yes']) # 仍然是yes，因为是手动配置
            logging.debug(f"为连接 {conn_name} 清除 DNS 设置并设置 ignore-auto-dns=yes")
            
        commands.append(['sudo', 'nmcli', 'con', 'down', conn_name])
        commands.append(['sudo', 'nmcli', 'con', 'up', conn_name])
        
        logging.info(f"为 nmcli (connection: {conn_name}) 生成设置静态 IP 的命令序列: {commands}")
        return True, commands
    else:
        logging.warning(
            f"无法确定接口 {interface_name} 的 NetworkManager 连接配置文件名称。 "
            f"Code: {code_conn_name}, Stdout: '{stdout_conn_name}', Stderr: '{stderr_conn_name}'."
        )
        error_msg = (
            f"{YELLOW}无法确定接口 {interface_name} 的 NetworkManager 活动连接配置文件。{RESET}\n"
            f"因此无法自动设置静态 IP。\n"
            f"请确保接口由 NetworkManager 管理并且有一个活动的连接配置文件。"
        )
        return False, error_msg

# --- CLI Diagnostic Functions ---
def cli_diagnose_interface(if_name, if_details):
    results = []
    suggestions = []
    has_ip = bool(if_details.get('ips'))
    
    results.append(f"接口: {BOLD}{if_name}{RESET}")
    results.append(f"  MAC 地址: {if_details.get('mac', 'N/A')}")
    results.append(f"  状态: {GREEN if if_details.get('state') == 'UP' else YELLOW}{if_details.get('state', 'N/A')}{RESET}")
    results.append(f"  配置模式: {if_details.get('config_mode', '未知')}")

    if not has_ip:
        results.append(f"  IP 地址: {RED}未分配 IP 地址。{RESET}")
        if if_details.get('config_mode') == 'DHCP' or 'DHCP' in if_details.get('config_mode', ''):
            suggestions.append(f"{YELLOW}提示: 接口 {if_name} 处于 DHCP 模式。请确保网线已连接，路由器/DHCP 服务器工作正常，并且没有 MAC 地址过滤问题。{RESET}")
        elif if_details.get('config_mode') == '静态/手动':
            suggestions.append(f"{YELLOW}提示: 接口 {if_name} 似乎是静态配置但没有 IP。请检查其静态 IP 配置是否有误 (例如，在 /etc/network/interfaces, NetworkManager, 或 netplan 中)。{RESET}")
        else: # 未知或其他
             suggestions.append(f"{YELLOW}提示: 无法确定 IP 配置模式或未分配 IP。请检查 {if_name} 的物理连接和网络配置。{RESET}")
        return results, suggestions, False # 总体成功 = False

    results.append(f"  IP 地址: {GREEN}{', '.join(if_details['ips'])}{RESET}")
    
    # 2. 网关检查
    gateway_ip = if_details.get('gateway')
    if not gateway_ip:
        results.append(f"  网关: {YELLOW}此接口未配置或未检测到网关。{RESET}")
        # 尝试推断网关
        try:
            if_ip_obj = ipaddress.ip_interface(if_details['ips'][0])
            network = if_ip_obj.network
            # 常见的网关地址: x.x.x.1 或 x.x.x.254
            potential_gw1 = ipaddress.ip_address(network.network_address + 1)
            potential_gw254 = None
            if network.num_addresses > 2: # 避免用于 /31, /32 网络
                 potential_gw254 = ipaddress.ip_address(network.broadcast_address - 1)

            suggestions.append(f"{YELLOW}提示: 未找到网关。您的网络 {network} 的常见网关可能是 {potential_gw1}")
            if potential_gw254 and potential_gw1 != potential_gw254:
                 suggestions[-1] += f" 或 {potential_gw254}"
            suggestions[-1] += f"。{RESET}"
        except Exception as e:
            suggestions.append(f"{YELLOW}提示: 无法推断网关。请检查您网络的网关配置。{RESET}")
        return results, suggestions, False # 网关至关重要

    results.append(f"  网关: {gateway_ip}")
    gw_ping_ok, gw_latency, gw_loss = ping_host(gateway_ip)
    if gw_ping_ok:
        results.append(f"  网关 Ping ({gateway_ip}): {GREEN}成功{RESET} (延迟: {gw_latency:.2f}ms, 丢包: {gw_loss}%)")
    else:
        results.append(f"  网关 Ping ({gateway_ip}): {RED}失败{RESET}")
        suggestions.append(f"{YELLOW}提示: 网关 {gateway_ip} 无法访问。请检查网关设备、线缆连接和本地防火墙设置。确保 {if_name} 的 IP 设置 ({if_details['ips'][0]}) 对于当前网络是正确的。{RESET}")
        return results, suggestions, False

    # 3. DNS 检查
    current_dns_servers = get_dns_servers()
    if not current_dns_servers:
        results.append(f"  DNS 服务器: {RED}未配置 DNS 服务器。{RESET}")
        suggestions.append(f"{YELLOW}提示: 未找到 DNS 服务器。建议将 DNS 设置为 {PRIMARY_DNS} (首选) 和 {SECONDARY_DNS} (备用)。您可能需要在 /etc/resolv.conf、NetworkManager 或您的路由器中进行配置。{RESET}")
        # 提供设置 DNS 的选项 (CLI: y/n, GUI: 按钮)
        return results, suggestions, False 

    results.append(f"  DNS 服务器: {', '.join(current_dns_servers)}")
    dns_all_ok = True
    for i, dns_server in enumerate(current_dns_servers):
        dns_ping_ok, dns_latency, dns_loss = ping_host(dns_server)
        status_msg = f"  DNS {i+1} ({dns_server}): "
        if dns_ping_ok:
            if dns_latency <= 50: # 阈值调整为50ms
                status_msg += f"{GREEN}成功{RESET} (延迟: {dns_latency:.2f}ms, 丢包: {dns_loss}%)"
            else:
                status_msg += f"{YELLOW}缓慢{RESET} (延迟: {dns_latency:.2f}ms, 丢包: {dns_loss}%) - 考虑更换。"
                # 对于慢速 DNS 不再将 dns_all_ok 设置为 False，仅警告
        else:
            status_msg += f"{RED}失败{RESET}"
            dns_all_ok = False
        results.append(status_msg)
    
    if not dns_all_ok:
        suggestions.append(f"{YELLOW}提示: 一个或多个 DNS 服务器无法访问。建议更改/添加 DNS 为 {PRIMARY_DNS} 和 {SECONDARY_DNS}。{RESET}")
        # 提供设置 DNS 的选项
        return results, suggestions, False # DNS 故障对互联网访问至关重要

    # 4. 互联网连接性检查
    results.append(f"  互联网 (ping www.baidu.com):")
    baidu_ping_ok, baidu_latency, baidu_loss = ping_host("www.baidu.com")
    if baidu_ping_ok:
        results.append(f"    状态: {GREEN}成功{RESET} (延迟: {baidu_latency:.2f}ms, 丢包: {baidu_loss}%)")
        results.append(f"{GREEN}诊断完成。互联网连接似乎工作正常。{RESET}")
        return results, suggestions, True
    else:
        results.append(f"    状态: {RED}失败 (ping){RESET}")
        results.append(f"  互联网 (curl www.baidu.com):")
        curl_ok, curl_msg = curl_check("http://www.baidu.com") # 对 curl 测试使用 http
        if curl_ok:
            results.append(f"    状态: {GREEN}成功 (curl){RESET} - {curl_msg}")
            results.append(f"{YELLOW}诊断完成。通过 curl 可以连接互联网，但 ping 可能被阻止 (例如，被防火墙或 ICMP 规则阻止)。{RESET}")
            return results, suggestions, True
        else:
            results.append(f"    状态: {RED}失败 (curl){RESET} - {curl_msg}")
            suggestions.append(f"{YELLOW}提示: 无法连接到 www.baidu.com。请检查路由器/调制解调器的互联网连接 (例如，DSL/光纤状态、PPPoE拨号)，以及任何上游防火墙或 ISP 问题。{RESET}")
            return results, suggestions, False

def print_cli_results(results, suggestions):
    print("\n" + "-"*20 + " 诊断结果 " + "-"*20) # 中文标题
    for res in results:
        print(res)
    if suggestions:
        print("\n" + "-"*20 + " 建议 " + "-"*25) # 中文标题
        for sug in suggestions:
            print(sug)
    print("-"*(40 + len(" 诊断结果 "))) # 调整分隔线长度

# --- Textual GUI Components (if TEXTUAL_AVAILABLE) ---
if TEXTUAL_AVAILABLE:
    class OutputDisplay(Markdown):
        """一个用于显示格式化诊断输出的组件。"""
        pass

    class ConfirmModal(ModalScreen):
        """一个用于 Yes/No 问题的模态对话框。"""
        def __init__(self, prompt: str, callback) -> None:
            super().__init__()
            self.prompt = prompt
            self.callback = callback

        def compose(self) -> ComposeResult:
            yield Container(
                Label(self.prompt),
                Horizontal(
                    Button("是", variant="success", id="yes"), # 中文按钮
                    Button("否", variant="error", id="no"),   # 中文按钮
                    id="dialog-buttons",
                ),
                id="confirm-dialog",
            )

        def on_button_pressed(self, event: Button.Pressed) -> None:
            self.dismiss_with_result(event.button.id == "yes")
            if self.callback:
                asyncio.create_task(self.callback(event.button.id == "yes"))

    class SetStaticIPModal(ModalScreen):
        """用于输入静态IP配置的模态对话框。"""
        def __init__(self, prompt: str) -> None:
            super().__init__()
            self._prompt = prompt

        def compose(self) -> ComposeResult:
            yield Container(
                Label(self._prompt),
                Input(placeholder="IP 地址 (例如: 192.168.1.100)", id="ip_address"),
                Input(placeholder="子网前缀 (例如: 24)", id="prefix", type="integer"),
                Input(placeholder="网关 (可选，例如: 192.168.1.1)", id="gateway"),
                Input(placeholder="DNS 服务器 (可选, 逗号分隔, 例如: 223.5.5.5,1.1.1.1)", id="dns"),
                Horizontal(
                    Button("应用", variant="success", id="apply_static_ip"),
                    Button("取消", variant="error", id="cancel_static_ip"),
                    id="modal-buttons",
                ),
                id="set-static-ip-dialog",
            )

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "apply_static_ip":
                # 收集数据并关闭模态框
                data = {
                    "ip_address": self.query_one("#ip_address", Input).value,
                    "prefix": self.query_one("#prefix", Input).value,
                    "gateway": self.query_one("#gateway", Input).value,
                    "dns": self.query_one("#dns", Input).value,
                }
                # 简单的验证 (可以做得更复杂)
                if not data["ip_address"] or not data["prefix"]:
                    # 可以添加错误提示，例如更新一个Label
                    # self.query_one("#error_label", Label).update("IP地址和前缀不能为空!")
                    logging.warning("设置静态IP时，IP地址或前缀为空")
                    return # 保持模态框打开
                try:
                    int(data["prefix"]) # 确保前缀是数字
                except ValueError:
                    logging.warning("设置静态IP时，前缀不是有效数字")
                    return
                self.dismiss(data)
            elif event.button.id == "cancel_static_ip":
                self.dismiss(None)

    class NetworkDiagnosticsApp(App):
        # CSS_PATH = "network_diagnostics.tcss" # 不再需要，CSS将内联
        TITLE = "网络诊断工具" # 中文标题

        DEFAULT_CSS = """
#app-grid {
    layout: grid;
    grid-size: 2 1;
    grid-columns: 1fr 3fr; /* 接口选择区 25%, 结果区 75% */
    height: 100%;
}
#interface-selection-pane { padding: 1; border-right: solid $primary-lighten-2; }
#results-pane { padding: 1; }
.section-title { padding: 1 0; text-style: bold; }
#interface-select { width: 100%; margin-bottom: 1; }
#start-button { width: 100%; margin-bottom: 1; }
#fix-dns-button { width: 100%; margin-top: 1; margin-bottom: 1; } /* DNS修复按钮样式 */
#set-dhcp-button { width: 100%; margin-top: 1; margin-bottom: 1; } /* DHCP切换按钮样式 */
#set-static-ip-button { width: 100%; margin-top: 1; margin-bottom: 1; } /* 静态IP设置按钮样式 */
.hidden_button { display: none; } /* 用于初始隐藏按钮 */
#diagnostic-output-display, #suggestions-output-display, #fix-result-display, #dhcp-result-display, #static-ip-result-display {
    margin-top: 1;
    padding: 1;
    border: round $primary;
    min-height: 3; /* 调整最小高度以容纳内容 */
    height: auto; /* 允许其增长 */
}
#fix-result-display { /* 修复结果特定样式 */
    border: round $secondary; 
    background: $panel-darken-1;
}
ConfirmModal > Container {
    padding: 2;
    border: thick $primary;
    width: 50;
    height: auto;
    background: $surface;
    align: center middle;
}
#dialog-buttons {
    width: 100%;
    align: center middle;
    margin-top: 1;
}
#dialog-buttons > Button {
    margin: 0 1;
}
.small_text_info { color: $text-muted; margin-bottom: 1; } /* 移除 font-size */

/* SetStaticIPModal styles */
SetStaticIPModal > Container {
    padding: 1;
    border: thick $primary;
    width: 60;
    height: auto; /* Adjust height based on content */
    background: $surface;
    align: center middle;
}

SetStaticIPModal Input {
    margin-bottom: 1;
    width: 100%;
}

SetStaticIPModal #modal-buttons {
    margin-top: 1;
    width: 100%;
    align: center middle;
}

SetStaticIPModal #modal-buttons > Button {
    margin: 0 1;
}
"""

        interfaces_details = reactive({})
        selected_interface_name = reactive(None)
        diagnostic_output = reactive("")
        suggestions_output = reactive("")
        is_diagnosing = reactive(False)

        def compose(self) -> ComposeResult:
            yield Header()
            with Container(id="app-grid"):
                with VerticalScroll(id="interface-selection-pane"):
                    yield Label("选择网络接口:", id="interface-label") # 中文标签
                    yield Select([], id="interface-select", prompt="正在加载接口...") # 中文提示
                    yield Button("开始诊断", id="start-button", variant="primary") # 中文按钮
                with VerticalScroll(id="results-pane"):
                    yield Label("诊断结果:", classes="section-title") # 中文标签
                    yield OutputDisplay(id="diagnostic-output-display")
                    yield Label("建议:", classes="section-title") # 中文标签
                    yield OutputDisplay(id="suggestions-output-display")
                    yield Button("尝试修复 DNS", id="fix-dns-button", variant="warning", classes="hidden_button") # 中文按钮, 初始隐藏
                    yield Markdown("", id="fix-result-display") # 用于显示修复结果, 改为 Markdown
                    
                    yield Static("\n--- 其它操作 ---", classes="section-title")
                    yield Static("若您无法连接到特定设备或服务，可尝试此方法。", classes="small_text_info")
                    yield Static("确保上级路由/交换机已开启并正确配置了DHCP服务。", classes="small_text_info")
                    yield Button("尝试切换到 DHCP 模式", id="set-dhcp-button", variant="default")
                    yield Markdown("", id="dhcp-result-display")

                    yield Button("设置静态 IP 地址", id="set-static-ip-button", variant="default") # 新按钮
                    yield Markdown("", id="static-ip-result-display") # 新的结果显示区域

            yield Footer()

        async def on_mount(self) -> None:
            """应用启动时加载网络接口。"""
            # 之前创建 CSS 文件的逻辑已移除
            await self.load_interfaces()
            self.query_one(Select).focus()

        def on_key(self, event: Key) -> None:
            """处理按键事件。"""
            if event.key == "escape":
                self.exit()

        async def load_interfaces(self):
            logging.debug("开始加载接口到 TUI Select 组件")
            self.interfaces_details = await asyncio.to_thread(get_network_interfaces_details)
            logging.debug(f"从 get_network_interfaces_details 获取到的原始数据: {self.interfaces_details}")
            iface_select = self.query_one(Select)
            if self.interfaces_details:
                # 不再仅筛选 UP 状态的接口，显示所有获取到的物理接口（get_network_interfaces_details 已排除 lo）
                display_interfaces = [
                    (f"{details.get('name', name)} ({details.get('ips')[0] if details.get('ips') else '无 IP 地址'} - {details.get('state', 'N/A')})", name)
                        for name, details in self.interfaces_details.items()
                    ]
                logging.debug(f"准备设置到 Select 的接口选项: {display_interfaces}")

                if display_interfaces:
                    iface_select.set_options(display_interfaces)
                    # 仍然默认选择第一个，或考虑选择第一个有IP的接口（如果逻辑需要）
                    self.selected_interface_name = display_interfaces[0][1] 
                    logging.info(f"TUI 接口加载成功，已选择接口: {self.selected_interface_name}")
                else:
                    # 此情况理论上不应发生，因为 get_network_interfaces_details 至少应返回一些接口信息，除非完全没有网络接口
                    iface_select.set_options([("未找到任何网络接口", None)]) # 中文
                    logging.warning("未找到任何网络接口用于显示在 TUI Select中")
            else:
                iface_select.set_options([("加载接口出错", None)]) # 中文
                logging.error("加载接口出错，get_network_interfaces_details 返回空或None")
            logging.debug("完成加载接口到 TUI Select 组件")

        def on_select_changed(self, event: Select.Changed) -> None:
            if event.value is not None:
                self.selected_interface_name = event.value
                logging.info(f"TUI 用户选择接口: {self.selected_interface_name}") # 添加日志

        async def on_button_pressed(self, event: Button.Pressed) -> None:
            fix_dns_button = self.query_one("#fix-dns-button", Button)
            fix_result_display = self.query_one("#fix-result-display", Markdown) # 查询类型改为 Markdown

            if event.button.id == "start-button" and self.selected_interface_name and not self.is_diagnosing:
                logging.info(f"TUI 用户点击开始诊断按钮，目标接口: {self.selected_interface_name}") # 添加日志
                self.is_diagnosing = True
                event.button.disabled = True
                fix_dns_button.display = False # 诊断开始时隐藏修复按钮
                fix_result_display.update("")  # 清除旧的修复结果

                self.diagnostic_output = f"# 正在诊断 {self.selected_interface_name}...\\n" # 中文
                self.suggestions_output = ""
                
                if_details = self.interfaces_details.get(self.selected_interface_name)
                if not if_details:
                    self.diagnostic_output += "\n## 错误: 未找到接口详情。" # 中文
                    logging.error(f"开始诊断时未找到所选接口 {self.selected_interface_name} 的详情") # 添加日志
                    self.is_diagnosing = False
                    event.button.disabled = False
                    return

                # 在单独的线程中运行诊断以保持 UI 响应
                logging.debug(f"为接口 {self.selected_interface_name} 调用 run_full_diagnostics_for_gui")
                results, suggestions, overall_ok = await asyncio.to_thread(
                    self.run_full_diagnostics_for_gui, self.selected_interface_name, if_details
                )
                
                logging.debug(f"诊断完成. 结果: {results}, 建议: {suggestions}, 总体状态: {overall_ok}")
                # 更新 GUI (如果 run_full_diagnostics_for_gui 会发布更新，请确保这是线程安全的)
                # 目前，很简单：在最后更新。
                # 将 CLI 带颜色的输出转换为 Markdown 以用于 GUI
                md_results = "\n".join([self.cli_to_markdown(line) for line in results])
                md_suggestions = "\n".join([self.cli_to_markdown(line) for line in suggestions])

                self.query_one("#diagnostic-output-display", OutputDisplay).update(md_results)
                self.query_one("#suggestions-output-display", OutputDisplay).update(md_suggestions)
                logging.info(f"TUI 界面已更新诊断结果和建议")

                # 根据诊断结果决定是否显示修复DNS按钮
                dns_issue_in_suggestions = any(
                    "未配置 DNS 服务器" in sug or 
                    "一个或多个 DNS 服务器无法访问" in sug
                    for sug in suggestions # 这里用原始的 suggestions 列表
                )
                if dns_issue_in_suggestions and self.selected_interface_name:
                    fix_dns_button.display = True
                    logging.debug("检测到 DNS 问题，显示修复 DNS 按钮")
                else:
                    fix_dns_button.display = False
                    logging.debug("未检测到 DNS 问题或无选中接口，隐藏修复 DNS 按钮")

                self.is_diagnosing = False
                event.button.disabled = False

            elif event.button.id == "fix-dns-button" and self.selected_interface_name:
                logging.info(f"TUI 用户点击 '尝试修复 DNS' 按钮，接口: {self.selected_interface_name}")
                fix_dns_button.label = "正在执行修复..."
                fix_dns_button.disabled = True
                fix_result_display.update("正在尝试自动修复 DNS...")
                
                # 定义 ANSI escape pattern 以便后续使用
                ansi_escape_pattern = r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])'

                # try_set_dns 现在返回 (bool, Union[List[List[str]], str])
                gen_success, commands_or_msg = await asyncio.to_thread(
                    try_set_dns, self.selected_interface_name, [PRIMARY_DNS, SECONDARY_DNS]
                )
                
                if gen_success:
                    assert isinstance(commands_or_msg, list), "commands_or_msg should be a list of commands"
                    logging.debug(f"成功生成 DNS 修复命令: {commands_or_msg}")
                    # 现在执行这些命令
                    exec_success, report_str = await execute_sudo_commands_and_report(
                        commands_or_msg, self.selected_interface_name
                    )
                    cleaned_report = re.sub(ansi_escape_pattern, '', report_str) # 移除ANSI给Markdown
                    fix_result_display.update(cleaned_report)
                    if exec_success:
                        fix_dns_button.label = "修复命令已执行"
                    else:
                        fix_dns_button.label = "修复执行遇阻"
                else:
                    # commands_or_msg 是错误消息字符串
                    assert isinstance(commands_or_msg, str), "commands_or_msg should be an error string"
                    logging.error(f"无法生成 DNS 修复命令: {commands_or_msg}")
                    cleaned_message = re.sub(ansi_escape_pattern, '', commands_or_msg)
                    fix_result_display.update(f"**无法自动修复:**\n{cleaned_message}")
                    fix_dns_button.label = "修复无法进行"
                
                fix_dns_button.disabled = False # 重新启用按钮，无论结果如何

            elif event.button.id == "set-dhcp-button" and self.selected_interface_name:
                logging.info(f"TUI 用户点击 '尝试切换到 DHCP 模式' 按钮，接口: {self.selected_interface_name}")
                dhcp_button = self.query_one("#set-dhcp-button", Button)
                dhcp_result_display = self.query_one("#dhcp-result-display", Markdown)
                
                dhcp_button.label = "正在切换到 DHCP..."
                dhcp_button.disabled = True
                dhcp_result_display.update("正在尝试自动切换到 DHCP 模式...")

                ansi_escape_pattern = r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])' # 确保定义

                gen_success, commands_or_msg = await asyncio.to_thread(
                    try_set_dhcp, self.selected_interface_name
                )

                if gen_success:
                    assert isinstance(commands_or_msg, list)
                    logging.debug(f"成功生成 DHCP 切换命令: {commands_or_msg}")
                    exec_success, report_str = await execute_sudo_commands_and_report(
                        commands_or_msg, self.selected_interface_name
                    )
                    cleaned_report = re.sub(ansi_escape_pattern, '', report_str)
                    dhcp_result_display.update(cleaned_report)
                    if exec_success:
                        dhcp_button.label = "DHCP 切换命令已执行"
                    else:
                        dhcp_button.label = "DHCP 切换执行遇阻"
                else:
                    assert isinstance(commands_or_msg, str)
                    logging.error(f"无法生成 DHCP 切换命令: {commands_or_msg}")
                    cleaned_message = re.sub(ansi_escape_pattern, '', commands_or_msg)
                    dhcp_result_display.update(f"**无法自动切换到 DHCP:**\n{cleaned_message}")
                    dhcp_button.label = "DHCP 切换无法进行"
                
                dhcp_button.disabled = False
                # 可以在这里建议用户重新诊断
                # dhcp_result_display.append_markdown("\n建议重新运行诊断。")

            elif event.button.id == "set-static-ip-button" and self.selected_interface_name:
                logging.info(f"TUI 用户点击 '设置静态 IP 地址' 按钮，接口: {self.selected_interface_name}")
                # 定义回调函数，当模态框关闭时被调用
                async def static_ip_modal_callback(data: dict | None):
                    static_ip_result_display = self.query_one("#static-ip-result-display", Markdown)
                    ansi_escape_pattern = r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])' # 确保定义

                    if data:
                        logging.debug(f"从 SetStaticIPModal 收到数据: {data}")
                        ip_address = data.get("ip_address")
                        prefix = data.get("prefix")
                        gateway = data.get("gateway") if data.get("gateway", "").strip() else None
                        dns_input = data.get("dns")
                        dns_servers = [d.strip() for d in dns_input.split(',') if d.strip()] if dns_input else None

                        static_ip_result_display.update(f"正在检查IP {ip_address} 是否冲突...")
                        is_conflict = await asyncio.to_thread(ping_check_ip_conflict, ip_address)

                        if is_conflict:
                            conflict_msg = f"**警告：IP地址 {ip_address} 可能已被占用！**\n建议选择其他IP地址以避免网络冲突。是否仍要继续设置此IP？"
                            # (这里可以添加一个 ConfirmModal 进一步确认)
                            # 暂时直接中止并提示
                            static_ip_result_display.update(f"{RED}{conflict_msg.replace('**','')}{RESET}") # 简单显示，不带Markdown强调
                            logging.warning(f"静态IP设置中止，因为 {ip_address} 检测到冲突。")
                            return
                        
                        static_ip_result_display.update(f"IP {ip_address} 未检测到冲突。正在尝试设置静态IP...")
                        
                        gen_success, commands_or_msg = await asyncio.to_thread(
                            try_set_static_ip, self.selected_interface_name, 
                            ip_address, prefix, gateway, dns_servers
                        )

                        if gen_success:
                            assert isinstance(commands_or_msg, list)
                            logging.debug(f"成功生成静态IP设置命令: {commands_or_msg}")
                            exec_success, report_str = await execute_sudo_commands_and_report(
                                commands_or_msg, self.selected_interface_name
                            )
                            cleaned_report = re.sub(ansi_escape_pattern, '', report_str)
                            static_ip_result_display.update(cleaned_report)
                            # 可以在此建议用户重新诊断以查看更改
                        else:
                            assert isinstance(commands_or_msg, str)
                            logging.error(f"无法生成静态IP设置命令: {commands_or_msg}")
                            cleaned_message = re.sub(ansi_escape_pattern, '', commands_or_msg)
                            static_ip_result_display.update(f"**无法设置静态IP:**\n{cleaned_message}")
                    else:
                        logging.debug("SetStaticIPModal被取消或未返回数据")
                        static_ip_result_display.update("设置静态IP操作已取消。")
                
                self.push_screen(SetStaticIPModal(prompt="为接口 " + self.selected_interface_name + " 设置静态IP"), static_ip_modal_callback)

        def cli_to_markdown(self, cli_line: str) -> str:
            """将 CLI 带颜色的输出转换为简单的 Markdown。"""
            line = re.sub(r'\033\[[0-9;]*m', '', cli_line) # 移除 ANSI codes
            if "**" not in line and (line.strip().startswith("接口:") or line.strip().startswith("网关:") or line.strip().startswith("DNS 服务器:") or line.strip().startswith("互联网:")) : # 中文匹配
                line = f"**{line.strip()}**"
            if "成功" in line: # 中文匹配
                line = line.replace("成功", "<span style='color:green'>成功</span>")
            if "失败" in line: # 中文匹配
                line = line.replace("失败", "<span style='color:red'>失败</span>")
            if "缓慢" in line: # 中文匹配
                line = line.replace("缓慢", "<span style='color:orange'>缓慢</span>")
            if "提示:" in line: # 中文匹配
                line = f"_提示: {line.split('提示:')[1].strip()}_"
            return line + "  " # 确保 Markdown 换行

        def run_full_diagnostics_for_gui(self, if_name, if_details):
            """cli_diagnose_interface 的 GUI 版本封装，可能用于发布更新。"""
            logging.debug(f"run_full_diagnostics_for_gui: 开始为接口 {if_name} 执行 cli_diagnose_interface")
            # 在更复杂的应用中，这可以使用 self.call_from_thread 来增量更新 GUI
            results, suggestions, overall_ok = cli_diagnose_interface(if_name, if_details)
            logging.debug(f"run_full_diagnostics_for_gui: cli_diagnose_interface 完成. 结果行数: {len(results)}, 建议行数: {len(suggestions)}, 状态: {overall_ok}")
            return results, suggestions, overall_ok


        async def ask_confirmation_and_act(self, prompt: str, action_if_yes):
            """推送一个确认模态框，如果用户确认则执行操作。"""
            # 这是一个占位符，说明 GUI 操作将如何触发
            # 例如，设置 DNS：
            # if confirmed:
            #   self.diagnostic_output += "尝试设置 DNS (需要 sudo 权限)..."
            #   success, msg = await asyncio.to_thread(try_set_dns, ["223.5.5.5", "223.6.6.6"])
            #   self.diagnostic_output += f"{msg}"
            pass


# --- Main Execution Logic ---
def main_cli(args):
    print(f"{BLUE}网络诊断工具 (命令行模式){RESET}")
    interfaces = get_network_interfaces_details()

    if not interfaces:
        print(f"{RED}未找到网络接口或获取接口信息时出错。{RESET}")
        return

    target_interface_name = args.interface
    if not target_interface_name:
        active_ips_interfaces = {name: details for name, details in interfaces.items() if details.get('ips')}
        if len(active_ips_interfaces) == 1:
            target_interface_name = list(active_ips_interfaces.keys())[0]
            print(f"{YELLOW}找到一个活动接口: {BOLD}{target_interface_name}{YELLOW}。正在对其进行诊断。{RESET}")
        elif active_ips_interfaces:
            print(f"{YELLOW}找到多个具有 IP 地址的接口。请使用 {BOLD}--interface <接口名称>{YELLOW} 指定一个，或从下方选择:{RESET}")
            for i, (name, details) in enumerate(active_ips_interfaces.items()):
                print(f"  {BOLD}{i+1}{RESET}. {name} ({details['ips'][0]})")
            try:
                choice = input(f"输入要诊断的接口编号 (或输入 'q' 退出): ")
                if choice.lower() == 'q': return
                target_interface_name = list(active_ips_interfaces.keys())[int(choice)-1]
            except (ValueError, IndexError):
                print(f"{RED}无效的选择。{RESET}")
                return
        else: # 没有带 IP 的接口
            print(f"{YELLOW}当前没有接口分配有 IP 地址。请选择一个接口以检查其状态:{RESET}")
            all_interfaces_list = list(interfaces.keys())
            for i, name in enumerate(all_interfaces_list):
                 print(f"  {BOLD}{i+1}{RESET}. {name} (状态: {interfaces[name].get('state', 'N/A')})")
            try:
                choice = input(f"输入要诊断的接口编号 (或输入 'q' 退出): ")
                if choice.lower() == 'q': return
                target_interface_name = all_interfaces_list[int(choice)-1]
            except (ValueError, IndexError):
                print(f"{RED}无效的选择。{RESET}")
                return


    if target_interface_name not in interfaces:
        print(f"{RED}未找到接口 '{BOLD}{target_interface_name}{RED}'。可用接口: {', '.join(interfaces.keys())}{RESET}")
        return

    print(f"{BLUE}开始诊断接口: {BOLD}{target_interface_name}{RESET}")
    results, suggestions, overall_ok = cli_diagnose_interface(target_interface_name, interfaces[target_interface_name])
    print_cli_results(results, suggestions)

    # CLI 中交互式修复的占位符
    if not overall_ok and suggestions:
        # 检查建议中是否包含 DNS 问题 (需要确保 cli_diagnose_interface 中的文本也已相应更新或通过特定标志判断)
        dns_issue_detected = any(
            "未配置 DNS 服务器" in sug or 
            "一个或多个 DNS 服务器无法访问" in sug or
            "No DNS servers configured" in sug or # 保留英文以防万一
            "One or more DNS servers are unreachable" in sug # 保留英文以防万一
            for sug in suggestions
        )
        if dns_issue_detected:
            if input(f"{CYAN}您想尝试自动修复 DNS (设置为 {PRIMARY_DNS} 和 {SECONDARY_DNS}) 吗? (可能需要 sudo权限) [y/N]: {RESET}").lower() == 'y':
                print(f"{YELLOW}正在尝试生成并执行 DNS 修复命令...{RESET}")
                gen_success, commands_or_msg = try_set_dns(target_interface_name, [PRIMARY_DNS, SECONDARY_DNS])
                
                if gen_success:
                    assert isinstance(commands_or_msg, list)
                    print(f"{CYAN}已生成以下命令，将尝试执行:{RESET}")
                    for cmd_args in commands_or_msg:
                        print(f"  {WHITE}{' '.join(cmd_args)}{RESET}")
                    
                    print(f"\n{YELLOW}开始执行修复命令...{RESET}")
                    overall_exec_success = True
                    cli_report_parts = []

                    for i, command_args in enumerate(commands_or_msg):
                        cmd_str_display = " ".join(command_args)
                        print(f"\n{BOLD}执行命令 {i+1}/{len(commands_or_msg)}:{RESET} {CYAN}{cmd_str_display}{RESET}")
                        stdout, stderr, code = run_command(command_args)
                        if code == 0:
                            print(f"  {GREEN}成功。{RESET}")
                            if stdout: print(f"  {WHITE}输出:{RESET}\n{stdout}")
                            if stderr: print(f"  {YELLOW}警告/标准错误输出:{RESET}\n{stderr}")
                        else:
                            overall_exec_success = False
                            print(f"  {RED}失败 (返回码: {code})。{RESET}")
                            if stdout: print(f"  {WHITE}标准输出:{RESET}\n{stdout}")
                            if stderr: print(f"  {RED}错误输出:{RESET}\n{stderr}")
                    
                    if overall_exec_success:
                        print(f"\n{GREEN}所有修复命令均已成功执行或未报告严重错误。{RESET}")
                        print(f"{YELLOW}请重新进行网络诊断以确认问题是否已解决。{RESET}")
                    else:
                        print(f"\n{RED}部分或全部修复命令执行失败。{RESET}")
                        print(f"{YELLOW}请检查上面的输出以了解详细信息。您可能需要手动执行相关命令或检查权限。{RESET}")
                else:
                    assert isinstance(commands_or_msg, str)
                    print(f"{RED}无法自动修复 DNS:{RESET}")
                    print(commands_or_msg)

    # --- 新增：CLI DHCP 切换 --- 
    if target_interface_name: # 确保有目标接口
        if input(f"{CYAN}\n是否尝试将接口 {target_interface_name} 切换到 DHCP 模式? (可能需要 sudo权限) [y/N]: {RESET}").lower() == 'y':
            print(f"{YELLOW}正在尝试生成并执行切换到 DHCP 模式的命令...{RESET}")
            gen_success_dhcp, commands_or_msg_dhcp = try_set_dhcp(target_interface_name)

            if gen_success_dhcp:
                assert isinstance(commands_or_msg_dhcp, list)
                print(f"{CYAN}已生成以下命令，将尝试执行:{RESET}")
                for cmd_args in commands_or_msg_dhcp:
                    print(f"  {WHITE}{' '.join(cmd_args)}{RESET}")
                
                print(f"\n{YELLOW}开始执行切换到 DHCP 的命令...{RESET}")
                overall_exec_success_dhcp = True
                for i, command_args in enumerate(commands_or_msg_dhcp):
                    cmd_str_display = " ".join(command_args)
                    print(f"\n{BOLD}执行命令 {i+1}/{len(commands_or_msg_dhcp)}:{RESET} {CYAN}{cmd_str_display}{RESET}")
                    stdout, stderr, code = run_command(command_args)
                    if code == 0:
                        print(f"  {GREEN}成功。{RESET}")
                        if stdout: print(f"  {WHITE}输出:{RESET}\n{stdout}")
                        if stderr: print(f"  {YELLOW}警告/标准错误输出:{RESET}\n{stderr}")
                    else:
                        overall_exec_success_dhcp = False
                        print(f"  {RED}失败 (返回码: {code})。{RESET}")
                        if stdout: print(f"  {WHITE}标准输出:{RESET}\n{stdout}")
                        if stderr: print(f"  {RED}错误输出:{RESET}\n{stderr}")
                
                if overall_exec_success_dhcp:
                    print(f"\n{GREEN}所有切换到 DHCP 的命令均已成功执行或未报告严重错误。{RESET}")
                    print(f"{YELLOW}建议重新进行网络诊断以确认接口是否已获取 IP 地址并工作正常。{RESET}")
                else:
                    print(f"\n{RED}部分或全部切换到 DHCP 的命令执行失败。{RESET}")
                    print(f"{YELLOW}请检查上面的输出以了解详细信息。{RESET}")
            else:
                assert isinstance(commands_or_msg_dhcp, str)
                print(f"{RED}无法自动切换到 DHCP:{RESET}")
                print(commands_or_msg_dhcp)

if __name__ == "__main__":
    # 获取脚本名称，用于帮助信息和错误提示
    script_name = os.path.basename(sys.argv[0])

    parser = argparse.ArgumentParser(
        description="网络诊断工具：检测网络配置、连接性和常见问题。",
        formatter_class=argparse.RawTextHelpFormatter, 
        epilog=f"""示例:
  {script_name}                      # 默认启动图形用户界面 (如果 Textual 可用)
  {script_name} --gui                # 显式启动图形用户界面
  {script_name} --cli                # 启动命令行界面 (如果未指定接口，会提示选择)
  {script_name} --interface <接口名称> # 在命令行界面诊断指定接口

要查看详细的调试日志，请检查脚本同目录下的 {LOG_FILENAME} 文件。
"""
    )
    parser.add_argument(
        "-i", "--interface",
        metavar="<接口名称>",
        help="指定要诊断的网络接口 (例如: eth0, wlan0)。\n如果提供此参数，将以命令行模式运行。"
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="尝试启动 Textual 图形用户界面。\n(这是默认行为，除非指定了 --interface 或 --cli)"
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="强制以命令行界面模式运行诊断。"
    )
    # 根据需要添加更多 CLI 参数，例如 --auto-fix (请谨慎使用)

    args = parser.parse_args()

    # 如果指定了 --interface 或 --cli，则运行 CLI 模式。
    # 否则，默认尝试运行 TUI 模式 (或者用户明确指定了 --gui)。
    if args.interface or args.cli:
        # 即使同时传递了 --gui，--interface 或 --cli 也会优先进入 CLI 模式
        main_cli(args)
    else:
        if TEXTUAL_AVAILABLE:
            app = NetworkDiagnosticsApp()
            app.run()
        else:
            print(f"{RED}错误：Textual 图形库未安装。{RESET}")
            print(f"{YELLOW}图形用户界面 (TUI) 模式无法启动。{RESET}")
            print(f"要使用图形界面，请先安装 Textual： {BOLD}pip install textual{RESET}")
            print("\n您也可以使用命令行模式运行此工具：")
            print(f"  {script_name} --cli             (启动命令行模式，将提示选择接口)")
            print(f"  {script_name} --interface <接口名称>")
            print(f"  {script_name} -h 或者 --help    (查看帮助信息)")
            print(f"详细错误信息已记录到当前目录的 {LOG_FILENAME} 文件中。")
            sys.exit(1) # 表示由于缺少依赖导致默认模式失败 