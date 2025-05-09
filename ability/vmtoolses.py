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

def check_package_installed(package_name):
    try:
        result = subprocess.run(
            ["dpkg-query", "-W", "-f='${Status}'", package_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return "install ok installed" in result.stdout
    except subprocess.CalledProcessError:
        return False



def run_apt_command(command):
    """执行 APT 相关命令，并返回输出"""
    try:
        subprocess.run(command, check=True)
        print(f"\033[32m操作成功\033[0m")
    except subprocess.CalledProcessError:
        print(f"\033[31m操作失败: {' '.join(command)}\033[0m")


def menu():
    open_vm_tools_installed = check_package_installed("open-vm-tools")
    qemu_guest_agent_installed = check_package_installed("qemu-guest-agent")

    if open_vm_tools_installed and qemu_guest_agent_installed:
        print("\033[33m检测到两个工具均已安装，仅操作其中之一。\033[0m")
        print("默认选择 open-vm-tools 进行操作。\n")
        qemu_guest_agent_installed = False  # 只对 open-vm-tools 进行操作

    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        print("\033[36m=== 虚拟机工具管理 ===\033[0m")

        if open_vm_tools_installed:
            print("\033[32m[已安装] open-vm-tools\033[0m")
        elif qemu_guest_agent_installed:
            print("\033[32m[已安装] qemu-guest-agent\033[0m")
        else:
            print("[未安装] open-vm-tools 和 qemu-guest-agent")

        print("\n请选择操作:")
        if open_vm_tools_installed or qemu_guest_agent_installed:
            print("1. 更新已安装的软件")
            print("2. 卸载软件")
        else:
            print("3. 安装 适用于VMware虚拟机平台工具")
            print("4. 安装 适用于qemu虚拟机的平台工具(例如PVE)")
        print("5. 退出")

        choice = input("请输入选项: ")
        package = "open-vm-tools" if open_vm_tools_installed else "qemu-guest-agent"

        if choice == "1" and (open_vm_tools_installed or qemu_guest_agent_installed):
            run_apt_command(["sudo", "apt", "install", "--only-upgrade", "-y", package])
        elif choice == "2" and (open_vm_tools_installed or qemu_guest_agent_installed):
            run_apt_command(["sudo", "apt", "remove", "-y", package])
            run_apt_command(["sudo", "dpkg", "--purge", package])
        elif choice == "3" and not open_vm_tools_installed:
            run_apt_command(["sudo", "apt", "install", "-y", "open-vm-tools"])
        elif choice == "4" and not qemu_guest_agent_installed:
            run_apt_command(["sudo", "apt", "install", "-y", "qemu-guest-agent"])
        elif choice == "5":
            break
        else:
            print("\033[31m无效选项，请重新输入!\033[0m")
        input("\n按回车键继续...")


if __name__ == "__main__":
    menu()
