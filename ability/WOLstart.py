import os
import subprocess

# 颜色定义
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"


def get_network_interfaces():
    """获取设备的所有物理网卡名称（仅限 ens 开头）"""
    result = subprocess.run("ls /sys/class/net", shell=True, capture_output=True, text=True)
    interfaces = [iface for iface in result.stdout.strip().split("\n") if iface.startswith("ens")]
    return interfaces


def check_wol_status(interface):
    """检查指定网卡的 Wake-on-LAN 状态"""
    result = subprocess.run(f"ethtool {interface}", shell=True, capture_output=True, text=True)
    for line in result.stdout.split("\n"):
        if "Wake-on" in line:
            status = line.split(":")[1].strip()
            return status
    return None


def set_wol(interface, enable):
    """设置 Wake-on-LAN 状态，并更新 crontab"""
    mode = "g" if enable else "d"
    print(f"{YELLOW}正在为 {interface} 设置 Wake-on-LAN 为 {mode}...{RESET}")
    subprocess.run(f"ethtool -s {interface} wol {mode}", shell=True)

    cron_job = f"@reboot /sbin/ethtool -s {interface} wol g"
    existing_cron = subprocess.run("crontab -l", shell=True, capture_output=True, text=True)

    if enable:
        if cron_job not in existing_cron.stdout:
            subprocess.run(f'(crontab -l; echo "{cron_job}") | crontab -', shell=True)
            print(f"{GREEN}成功添加开机自动执行 WOL 设置到 crontab！{RESET}")
        else:
            print(f"{CYAN}crontab 已经包含该设置，无需重复添加。{RESET}")
    else:
        new_cron = "\n".join([line for line in existing_cron.stdout.split("\n") if cron_job not in line])
        subprocess.run(f'echo "{new_cron}" | crontab -', shell=True)
        print(f"{GREEN}已从 crontab 移除 Wake-on-LAN 设置。{RESET}")


def main():
    os.system('clear' if os.name == 'posix' else 'cls')
    print(f"{BOLD}{CYAN}=== 网络唤醒（Wake-on-LAN）配置工具 ==={RESET}\n")

    interfaces = get_network_interfaces()
    if not interfaces:
        print(f"{RED}未找到 ens 开头的物理网口！{RESET}")
        return

    print(f"{BOLD}可用的网络接口（ens 开头）：{RESET}")
    for iface in interfaces:
        print(f"- {GREEN}{iface}{RESET}")

    selected_iface = input(f"\n{BOLD}请输入要配置的网卡名称：{RESET}")
    if selected_iface not in interfaces:
        print(f"{RED}错误：输入的网卡名称不存在！{RESET}")
        return

    action = input(f"{BOLD}是否启用 Wake-on-LAN？(y/n)：{RESET}").strip().lower()
    if action not in ["y", "n"]:
        print(f"{RED}无效输入，请输入 'y' 或 'n'！{RESET}")
        return

    enable = action == "y"
    set_wol(selected_iface, enable)
    print(f"{GREEN}操作完成！{RESET}")


if __name__ == "__main__":
    main()