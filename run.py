# 运行库
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

def clear_screen():
    """清空终端屏幕"""
    os.system('clear' if os.name == 'posix' else 'cls')

# 检测脚本安装
def download_file(url, save_path):
    """
    下载文件，如果文件已经存在，则跳过下载。

    :param url: 文件的下载链接
    :param save_path: 文件保存路径
    """
    # 检查文件是否已经存在
    if os.path.exists(save_path):
        print(f"{YELLOW}脚本已经存在，如果需要更新，请删除{save_path}此目录的文件。按下任意键继续运行{RESET}")
        input()
        return

    # 使用 curl 命令下载文件
    print("脚本文件不存在，正在下载...")
    command = ["curl", "-k", "-o", save_path, url]
    try:
        subprocess.run(command, check=True)
        print("脚本下载完成，执行启动。")
    except subprocess.CalledProcessError as e:
        print(f"文件下载失败: {e}")

# 检测库文件
def check_and_install_package(package_name):
    try:
        # 尝试导入库
        __import__(package_name)
        print(f"运行环境已经安装。")
    except ImportError:
        # 如果导入失败，尝试安装库
        print(f"缺少运行环境，正在安装... 需要使用root账户请输入当前账户密码")
        try:
            # 使用 subprocess 执行安装命令
            result = subprocess.run(['sudo', 'apt', 'install', '-y', f'python3-{package_name}'], check=True)
            if result.returncode == 0:
                print(f"安装成功。")
            else:
                print(f"{package_name} 安装失败。")
        except subprocess.CalledProcessError as e:
            print(f"安装 {package_name} 时发生错误: {e}")


def install_package(package_name):
    """检测APT包是否已安装，若未安装则进行安装"""
    try:
        # 检查包是否已安装
        result = subprocess.run(
            ["dpkg", "-l", package_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if package_name in result.stdout:
            print(f"软件包 '{package_name}' 已安装，跳过安装。")
            return

        # 安装包
        print(f"安装软件包 '{package_name}'...")
        subprocess.run(["sudo", "apt-get", "install", "-y", package_name], check=True)
        print(f"软件包 '{package_name}' 安装完成。")

    except Exception as e:
        print(f"处理软件包 '{package_name}' 时出错: {e}")

def display_menu():
    """展示菜单"""
    print(f"{GREEN}欢迎使用Linux(FnOS)菜单脚本{RESET}")
    print("1.机箱 CD/DVD 挂载")
    print("2.一键开启IOMMU")
    print("3.一键开关swap")
    print("4.检测消耗最高的进程")
    print("5.qemu-img转换磁盘映像格式（例如qcow2）")
    print("6.列出指定目录的所有文件夹所占磁盘大小")
    print("7.查看设备硬件详细信息")
    print("8.持续监控CPU状态信息")
    print("9.安装虚拟机运行优化工具")
    print("10.设备电源管理")
    print("11.硬件自检及压测")
    print("12.开关WOL网络唤醒")
    print("g.关于脚本项目")
    print("n. 退出")

def main():
    while True:
        clear_screen()
        display_menu()
        choice = input("\n请选择一个选项 (输入n退出): ")
        if choice == '1':
            url = "https://pub-46d21cac9c7d44b79d73abfeb727999f.r2.dev/Linux%E8%84%9A%E6%9C%AC/%E9%A3%9E%E7%89%9B/ability/cdmount.py"
            save_path = "ability/cdmount.py"
            download_file(url, save_path)

            subprocess.run(['python3', 'ability/cdmount.py'])
        elif choice == '2':
            print(f'{RED}风险告知：由于此脚本中运行的指令涉及在root用户下才能运行，脚本会创建一个root终端执行相应命令并在执行完毕后自动关闭。由于root权限强大，为了保证数据安全，请您务必在执行前经过测试或数据备份再进行！对此出现的意外情况，作者不承担任何责任。按任意键表示继续运行，ctrl+c可终止运行{RESET}')
            print(f'{BLUE}此方法中不存在删除文件等其它敏感操作，您可以放心运行！{RESET}')
            input()
            url = "https://pub-46d21cac9c7d44b79d73abfeb727999f.r2.dev/Linux%E8%84%9A%E6%9C%AC/%E9%A3%9E%E7%89%9B/ability/startIOMMU.py"
            save_path = "ability/startIOMMU.py"
            download_file(url, save_path)

            subprocess.run(['sudo','python3', 'ability/startIOMMU.py'])
        elif choice == '3':
            print(f'{RED}风险告知：由于此脚本中运行的指令涉及在root用户下才能运行，脚本会创建一个root终端执行相应命令并在执行完毕后自动关闭。由于root权限强大，为了保证数据安全，请您务必在执行前经过测试或数据备份再进行！对此出现的意外情况，作者不承担任何责任。按任意键表示继续运行，ctrl+c可终止运行{RESET}')
            print(f'{BLUE}此方法中不存在删除文件等其它敏感操作，您可以放心运行！{RESET}')
            input()
            url = "https://pub-46d21cac9c7d44b79d73abfeb727999f.r2.dev/Linux%E8%84%9A%E6%9C%AC/%E9%A3%9E%E7%89%9B/ability/swapinfo.py"
            save_path = "ability/swapinfo.py"
            download_file(url, save_path)

            subprocess.run(['sudo','python3', 'ability/swapinfo.py'])
        elif choice == '4':
            print(f'{RED}风险告知：由于此脚本中运行的指令涉及在root用户下才能运行，脚本会创建一个root终端执行相应命令并在执行完毕后自动关闭。由于root权限强大，为了保证数据安全，请您务必在执行前经过测试或数据备份再进行！对此出现的意外情况，作者不承担任何责任。按任意键表示继续运行，ctrl+c可终止运行{RESET}')
            print(f'{BLUE}此方法中不存在删除文件等其它敏感操作，您可以放心运行！{RESET}')
            input()
            url = "https://pub-46d21cac9c7d44b79d73abfeb727999f.r2.dev/Linux%E8%84%9A%E6%9C%AC/%E9%A3%9E%E7%89%9B/ability/processinfo.py"
            save_path = "ability/processinfo.py"
            download_file(url, save_path)

            print(f'{BLUE}正在安装pip运行库{RESET}')
            check_and_install_package('psutil')
            print(f'{GREEN}安装完毕，执行脚本{RESET}')
            subprocess.run(['sudo','python3', 'ability/processinfo.py'])
        elif choice == '5':
            # print(f'{RED}风险告知：由于此脚本中运行的指令涉及在root用户下才能运行，脚本会创建一个root终端执行相应命令并在执行完毕后自动关闭。由于root权限强大，为了保证数据安全，请您务必在执行前经过测试或数据备份再进行！对此出现的意外情况，作者不承担任何责任。按任意键表示继续运行，ctrl+c可终止运行{RESET}')
            # print(f'{BLUE}此方法中不存在删除文件等其它敏感操作，您可以放心运行！{RESET}')
            # input()
            url = "https://pub-46d21cac9c7d44b79d73abfeb727999f.r2.dev/Linux%E8%84%9A%E6%9C%AC/%E9%A3%9E%E7%89%9B/ability/qcowtools.py"
            save_path = "ability/qcowtools.py"
            download_file(url, save_path)

            subprocess.run(['python3', 'ability/qcowtools.py'])
        elif choice == '6':
            # print(f'{RED}风险告知：由于此脚本中运行的指令涉及在root用户下才能运行，脚本会创建一个root终端执行相应命令并在执行完毕后自动关闭。由于root权限强大，为了保证数据安全，请您务必在执行前经过测试或数据备份再进行！对此出现的意外情况，作者不承担任何责任。按任意键表示继续运行，ctrl+c可终止运行{RESET}')
            # print(f'{BLUE}此方法中不存在删除文件等其它敏感操作，您可以放心运行！{RESET}')
            # input()

            url = "https://pub-46d21cac9c7d44b79d73abfeb727999f.r2.dev/Linux%E8%84%9A%E6%9C%AC/%E9%A3%9E%E7%89%9B/ability/filestorage.py"
            save_path = "ability/filestorage.py"
            download_file(url, save_path)

            print(f'{BLUE}正在安装pip运行库{RESET}')
            check_and_install_package('tabulate')
            print(f'{GREEN}安装完毕，执行脚本{RESET}')
            subprocess.run(['python3', 'ability/filestorage.py'])
        elif choice == '7':
            # print(f'{RED}风险告知：由于此脚本中运行的指令涉及在root用户下才能运行，脚本会创建一个root终端执行相应命令并在执行完毕后自动关闭。由于root权限强大，为了保证数据安全，请您务必在执行前经过测试或数据备份再进行！对此出现的意外情况，作者不承担任何责任。按任意键表示继续运行，ctrl+c可终止运行{RESET}')
            # print(f'{BLUE}此方法中不存在删除文件等其它敏感操作，您可以放心运行！{RESET}')
            # input()

            url = "https://pub-46d21cac9c7d44b79d73abfeb727999f.r2.dev/Linux%E8%84%9A%E6%9C%AC/%E9%A3%9E%E7%89%9B/ability/deviceinfo.py"
            save_path = "ability/deviceinfo.py"
            download_file(url, save_path)

            print(f'{BLUE}正在安装pip运行库{RESET}')
            check_and_install_package('psutil')
            print(f'{GREEN}安装完毕，执行脚本{RESET}')
            subprocess.run(['python3', 'ability/deviceinfo.py'])

        elif choice == '8':
            # print(f'{RED}风险告知：由于此脚本中运行的指令涉及在root用户下才能运行，脚本会创建一个root终端执行相应命令并在执行完毕后自动关闭。由于root权限强大，为了保证数据安全，请您务必在执行前经过测试或数据备份再进行！对此出现的意外情况，作者不承担任何责任。按任意键表示继续运行，ctrl+c可终止运行{RESET}')
            # print(f'{BLUE}此方法中不存在删除文件等其它敏感操作，您可以放心运行！{RESET}')
            # input()

            url = "https://pub-46d21cac9c7d44b79d73abfeb727999f.r2.dev/Linux%E8%84%9A%E6%9C%AC/%E9%A3%9E%E7%89%9B/ability/Continuous_monitoring.py"
            save_path = "ability/Continuous_monitoring.py"
            download_file(url, save_path)

            print(f'{BLUE}正在安装pip运行库{RESET}')
            check_and_install_package('psutil')
            check_and_install_package('tabulate')
            print(f'{GREEN}安装完毕，执行脚本{RESET}')
            subprocess.run(['python3', 'ability/Continuous_monitoring.py'])

        elif choice == '9':
            print(f'{RED}风险告知：由于此脚本中运行的指令涉及在root用户下才能运行，脚本会创建一个root终端执行相应命令并在执行完毕后自动关闭。由于root权限强大，为了保证数据安全，请您务必在执行前经过测试或数据备份再进行！对此出现的意外情况，作者不承担任何责任。按任意键表示继续运行，ctrl+c可终止运行{RESET}')
            print(f'{BLUE}此方法中不存在删除文件等其它敏感操作，您可以放心运行！{RESET}')
            input()

            url = "https://pub-46d21cac9c7d44b79d73abfeb727999f.r2.dev/Linux%E8%84%9A%E6%9C%AC/%E9%A3%9E%E7%89%9B/ability/vmtoolses.py"
            save_path = "ability/vmtoolses.py"
            download_file(url, save_path)

            print(f'{GREEN}安装完毕，执行脚本{RESET}')
            subprocess.run(['sudo','python3', 'ability/vmtoolses.py'])

        elif choice == '10':
            print(f'{RED}风险告知：由于此脚本中运行的指令涉及在root用户下才能运行，脚本会创建一个root终端执行相应命令并在执行完毕后自动关闭。由于root权限强大，为了保证数据安全，请您务必在执行前经过测试或数据备份再进行！对此出现的意外情况，作者不承担任何责任。按任意键表示继续运行，ctrl+c可终止运行{RESET}')
            print(f'{BLUE}此方法中不存在删除文件等其它敏感操作，您可以放心运行！{RESET}')
            input()

            # url = "https://pub-46d21cac9c7d44b79d73abfeb727999f.r2.dev/Linux%E8%84%9A%E6%9C%AC/%E9%A3%9E%E7%89%9B/ability/Powermanagement.py"
            save_path = "ability/Powermanagement.py"
            download_file(url, save_path)

            print(f'{GREEN}安装完毕，执行脚本{RESET}')
            subprocess.run(['sudo','python3', 'ability/Powermanagement.py'])

        elif choice == '11':
            print(f'{RED}风险告知：由于此脚本中运行的指令涉及在root用户下才能运行，脚本会创建一个root终端执行相应命令并在执行完毕后自动关闭。由于root权限强大，为了保证数据安全，请您务必在执行前经过测试或数据备份再进行！对此出现的意外情况，作者不承担任何责任。按任意键表示继续运行，ctrl+c可终止运行{RESET}')
            print(f'{BLUE}此方法中不存在删除文件等其它敏感操作，您可以放心运行！{RESET}')
            input()

            url = "https://pub-46d21cac9c7d44b79d73abfeb727999f.r2.dev/Linux%E8%84%9A%E6%9C%AC/%E9%A3%9E%E7%89%9B/ability/self_inspection.py"
            save_path = "ability/self_inspection.py"
            download_file(url, save_path)

            print(f'{GREEN}安装apt包{RESET}')
            install_package('memtester')
            install_package('stress')
            print(f'{BLUE}正在安装pip运行库{RESET}')
            check_and_install_package('psutil')
            print(f'{GREEN}安装完毕，执行脚本{RESET}')
            subprocess.run(['sudo','python3', 'ability/self_inspection.py'])

        elif choice == '12':
            print(f'{RED}风险告知：由于此脚本中运行的指令涉及在root用户下才能运行，脚本会创建一个root终端执行相应命令并在执行完毕后自动关闭。由于root权限强大，为了保证数据安全，请您务必在执行前经过测试或数据备份再进行！对此出现的意外情况，作者不承担任何责任。按任意键表示继续运行，ctrl+c可终止运行{RESET}')
            print(f'{BLUE}此方法中不存在删除文件等其它敏感操作，您可以放心运行！{RESET}')
            input()

            url = "https://pub-46d21cac9c7d44b79d73abfeb727999f.r2.dev/Linux%E8%84%9A%E6%9C%AC/%E9%A3%9E%E7%89%9B/ability/WOLstart.py"
            save_path = "ability/WOLstart.py"
            download_file(url, save_path)

            print(f'{GREEN}安装完毕，执行脚本{RESET}')
            subprocess.run(['sudo','python3', 'ability/WOLstart.py'])

        elif choice == 'g':
            None
        elif choice == 'n':
            print("\n感谢您的使用")
            break
        else:
            print("\n无效的选项，请重新选择。")

        input("\n按回车键继续...")

if __name__ == "__main__":
    main()