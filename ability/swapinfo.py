import os
import subprocess

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

# 常驻函数
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

def toggle_swap(enable=True):
    """启用或禁用 swap"""
    fstab_path = '/etc/fstab'
    swap_line = None

    # 读取 /etc/fstab 文件内容
    with open(fstab_path, 'r') as f:
        lines = f.readlines()

    # 查找 swap 配置行
    for line in lines:
        if 'swap' in line:
            swap_line = line
            break

    # 如果 swap 配置不存在，返回错误
    if swap_line is None:
        print(f"{RED}未找到 swap 配置!{RESET}")
        return

    # 修改 fstab 文件来启用或禁用 swap
    if enable:
        # 启用 swap：确保 swap 行没有注释掉
        if swap_line.startswith('#'):
            lines[lines.index(swap_line)] = swap_line[1:]  # 移除注释
            print(f"{GREEN}已启用 swap。{RESET}")
    else:
        # 禁用 swap：注释掉 swap 行
        if not swap_line.startswith('#'):
            lines[lines.index(swap_line)] = '#' + swap_line
            print(f"{YELLOW}已禁用 swap。{RESET}")

    # 写回修改后的 fstab 文件
    with open(fstab_path, 'w') as f:
        f.writelines(lines)

    # 提示用户重启
    print(f"{CYAN}修改已保存，请确认是否重启系统以生效。{RESET}")
    confirmation = input(f"{MAGENTA}是否现在重启系统？(y/n): {RESET}")

    if confirmation.lower() == 'y':
        print(f"{BLUE}正在重启系统...{RESET}")
        run_command('reboot')  # 执行重启命令
    else:
        print(f"{BLUE}请记得在稍后重启系统以使更改生效。{RESET}")

# 常驻代码
clear_screen()

# 用户输入决定启用或禁用 swap
user_input = input(f"{BOLD}请输入你要执行的操作：启用(1)或禁用(2) swap: {RESET}")
if user_input == '1':
    toggle_swap(enable=True)
elif user_input == '2':
    toggle_swap(enable=False)
else:
    print(f"{RED}无效的输入，请输入 1 或 2。{RESET}")
