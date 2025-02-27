# 运行库
import os
import subprocess
import time

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

def display_menu():
    """展示菜单"""
    print(f"{GREEN}欢迎使用Linux菜单脚本{RESET}")
    print("1.机箱 CD/DVD 挂载")
    print("2.一键开启IOMMU")
    print("3.一键开关swap")
    print("4.检测消耗最高的进程")
    print("g.关于脚本项目")
    print("n. 退出")

def main():
    while True:
        clear_screen()
        display_menu()
        choice = input("\n请选择一个选项 (输入n退出): ")
        if choice == '1':
            subprocess.run(['python3', 'ability/cdmount.py'])
        elif choice == '2':
            print(f'{RED}风险告知：由于此脚本中运行的指令涉及在root用户下才能运行，脚本会创建一个root终端执行相应命令并在执行完毕后自动关闭。由于root权限强大，为了保证数据安全，请您务必在执行前经过测试或数据备份再进行！对此出现的意外情况，作者不承担任何责任。按任意键表示继续运行，ctrl+c可终止运行{RESET}')
            print(f'{BLUE}此方法中不存在删除文件操作，您可以放心运行！{RESET}')
            input()
            subprocess.run(['sudo','python3', 'ability/startIOMMU.py'])
        elif choice == '3':
            print(f'{RED}风险告知：由于此脚本中运行的指令涉及在root用户下才能运行，脚本会创建一个root终端执行相应命令并在执行完毕后自动关闭。由于root权限强大，为了保证数据安全，请您务必在执行前经过测试或数据备份再进行！对此出现的意外情况，作者不承担任何责任。按任意键表示继续运行，ctrl+c可终止运行{RESET}')
            print(f'{BLUE}此方法中不存在删除文件操作，您可以放心运行！{RESET}')
            input()
            subprocess.run(['sudo','python3', 'ability/swapinfo.py'])
        elif choice == '4':
            print(f'{RED}风险告知：由于此脚本中运行的指令涉及在root用户下才能运行，脚本会创建一个root终端执行相应命令并在执行完毕后自动关闭。由于root权限强大，为了保证数据安全，请您务必在执行前经过测试或数据备份再进行！对此出现的意外情况，作者不承担任何责任。按任意键表示继续运行，ctrl+c可终止运行{RESET}')
            print(f'{BLUE}此方法中不存在删除文件操作，您可以放心运行！{RESET}')
            input()
            print(f'{BLUE}正在安装pip运行库{RESET}')
            subprocess.run(['sudo', 'apt', 'install', 'python3-psutil'])
            print(f'{GREEN}安装完毕，执行脚本{RESET}')
            subprocess.run(['sudo','python3', 'ability/processinfo.py'])

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