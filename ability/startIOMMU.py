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

def modify_grub_file():
    """修改 grub 配置文件中的 GRUB_CMDLINE_LINUX_DEFAULT"""
    grub_file_path = "/etc/default/grub"
    # 新的 GRUB_CMDLINE_LINUX_DEFAULT 内容
    new_grub_line = 'GRUB_CMDLINE_LINUX_DEFAULT="quiet i915.force_probe=7d55 intel_iommu=on iommu=pt"'

    # 以 root 权限打开并修改 grub 文件
    with open(grub_file_path, 'r') as grub_file:
        grub_lines = grub_file.readlines()

    # 查找并替换 GRUB_CMDLINE_LINUX_DEFAULT
    for i, line in enumerate(grub_lines):
        if line.startswith("GRUB_CMDLINE_LINUX_DEFAULT"):
            grub_lines[i] = new_grub_line + "\n"
            break

    # 将修改后的内容写回 grub 文件
    with open(grub_file_path, 'w') as grub_file:
        grub_file.writelines(grub_lines)

    print(f"{GREEN}grub 配置文件已成功修改！{RESET}")

# 常驻代码
clear_screen()

# 执行操作
print(f"{CYAN}正在修改 grub 配置文件...{RESET}")
modify_grub_file()

# 执行 grub 更新和 initramfs 更新
print(f"{CYAN}正在重载 grub...{RESET}")
result = run_command(['update-grub'])
if result['status_code'] == 0:
    print(f"{GREEN}执行成功！{RESET}")
else:
    print(f"{RED}update-grub 执行失败！{RESET}")
    print(f"错误信息: {result['stderr']}")

print(f"{CYAN}正在更新 RAM磁盘 预计需要1-3分钟 ...{RESET}")
result = run_command(['update-initramfs', '-u', '-k', 'all'])
if result['status_code'] == 0:
    print(f"{GREEN}执行成功！脚本运行完毕。{RESET}")
else:
    print(f"{RED}update-initramfs -u -k all 执行失败！{RESET}")
    print(f"错误信息: {result['stderr']}")
