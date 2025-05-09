import os
import subprocess


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


# 定义颜色常量
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"


# 常驻函数
def clear_screen():
    """清空终端屏幕"""
    os.system('clear' if os.name == 'posix' else 'cls')


def run_command(command):
    """直接执行命令并返回执行结果，包括状态码和标准输出/错误"""
    result = {'status_code': 0, 'stdout': '', 'stderr': ''}
    try:
        process_result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
        print(f"{RED}无效的输入，请输入 Intel 或 AMD{RESET}")
        return False

    with open(grub_file_path, 'r') as grub_file:
        grub_lines = grub_file.readlines()

    for i, line in enumerate(grub_lines):
        if line.startswith("GRUB_CMDLINE_LINUX_DEFAULT"):
            grub_lines[i] = new_grub_line + "\n"
            break

    with open(grub_file_path, 'w') as grub_file:
        grub_file.writelines(grub_lines)

    print(f"{GREEN}grub 配置文件已成功修改！{RESET}")
    return True


# 清屏并检测平台
clear_screen()
detected_platform = detect_platform()
if detected_platform == "Unknown":
    print(f"{RED}无法检测主板平台，请手动输入 Intel 或 AMD{RESET}")
    platform = input(f"{CYAN}请输入主板平台 (Intel 或 AMD): {RESET}")
else:
    confirmation = input(f"{CYAN}检测到您的平台为 {detected_platform}，是否正确？(Y/n): {RESET}")
    if confirmation.lower() == 'n':
        platform = "AMD" if detected_platform == "Intel" else "Intel"
    else:
        platform = detected_platform

# 修改 grub 配置文件
if modify_grub_file(platform):
    print(f"{CYAN}正在重载 grub...{RESET}")
    result = run_command(['update-grub'])
    if result['status_code'] == 0:
        print(f"{GREEN}执行成功！{RESET}")
    else:
        print(f"{RED}update-grub 执行失败！{RESET}\n错误信息: {result['stderr']}")

    print(f"{CYAN}正在更新 RAM 磁盘，预计需要 1-3 分钟...{RESET}")
    result = run_command(['update-initramfs', '-u', '-k', 'all'])
    if result['status_code'] == 0:
        print(f"{GREEN}执行成功！脚本运行完毕。请确认虚拟化已开启。{RESET}")
    else:
        print(f"{RED}update-initramfs -u -k all 执行失败！{RESET}\n错误信息: {result['stderr']}")