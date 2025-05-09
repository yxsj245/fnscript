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

# 文件路径
config_file = "/etc/systemd/logind.conf"

def clear_screen():
    """清空终端屏幕"""
    os.system('clear' if os.name == 'posix' else 'cls')

def show_menu():
    clear_screen()  # 清空终端屏幕
    print(f"{CYAN}请选择要配置的选项:{RESET}")
    print(f"{YELLOW}1. 笔记本合盖时操作{RESET}")
    print(f"{YELLOW}2. 电源适配器移除时操作{RESET}")
    print(f"{YELLOW}0. 退出{RESET}")
    choice = input(f"{MAGENTA}请输入选项（0-2）：{RESET}")
    return choice

def modify_lid_switch(option):
    try:
        # 读取配置文件内容
        with open(config_file, 'r') as file:
            lines = file.readlines()

        modified = False

        # 根据用户选择修改合盖时的行为
        if option == "1":
            print(f"{CYAN}请选择笔记本合盖时的操作：{RESET}")
            print(f"{YELLOW}1. 不做任何反应（ignore）{RESET}")
            print(f"{YELLOW}2. 关机（poweroff）{RESET}")
            lid_action = input(f"{MAGENTA}请输入选项（1-2）：{RESET}")

            for i, line in enumerate(lines):
                if "HandleLidSwitch=" in line:
                    if lid_action == "1":
                        lines[i] = "HandleLidSwitch=ignore\n"
                        print(f"{GREEN}设置为合盖时不做任何反应。{RESET}")
                    elif lid_action == "2":
                        lines[i] = "HandleLidSwitch=poweroff\n"
                        print(f"{GREEN}设置为合盖时关机。{RESET}")
                    modified = True
                    break
            if not modified:
                lines.append("HandleLidSwitch=poweroff\n")
                print(f"{GREEN}未找到HandleLidSwitch参数，已添加并设置为合盖时关机。{RESET}")
                modified = True

        elif option == "2":
            print(f"{CYAN}请选择电源适配器移除时的操作：{RESET}")
            print(f"{YELLOW}1. 关机（poweroff）{RESET}")
            print(f"{YELLOW}2. 不做任何操作（ignore）{RESET}")
            power_action = input(f"{MAGENTA}请输入选项（1-2）：{RESET}")

            # 检查是否存在 HandleLidSwitchExternalPower 参数
            found_power_key = False
            for i, line in enumerate(lines):
                if "HandleLidSwitchExternalPower=" in line:
                    found_power_key = True
                    if power_action == "1":
                        lines[i] = "HandleLidSwitchExternalPower=poweroff\n"
                        print(f"{GREEN}设置为电源适配器移除时关机。{RESET}")
                    elif power_action == "2":
                        lines[i] = "HandleLidSwitchExternalPower=ignore\n"
                        print(f"{GREEN}设置为电源适配器移除时不做任何操作。{RESET}")
                    break

            if not found_power_key:
                if power_action == "1":
                    lines.append("HandleLidSwitchExternalPower=poweroff\n")
                    print(f"{GREEN}未找到HandleLidSwitchExternalPower参数，已添加并设置为电源适配器移除时关机。{RESET}")
                elif power_action == "2":
                    lines.append("HandleLidSwitchExternalPower=ignore\n")
                    print(f"{GREEN}未找到HandleLidSwitchExternalPower参数，已添加并设置为电源适配器移除时不做任何操作。{RESET}")

        # 如果有修改，更新文件
        with open(config_file, 'w') as file:
            file.writelines(lines)

        print(f"{GREEN}配置文件已成功修改！{RESET}")

        # 重新启动 systemd-logind 服务
        print(f"{YELLOW}正在重载配置{RESET}")
        subprocess.run(["sudo", "systemctl", "restart", "systemd-logind"], check=True)
        print(f"{GREEN}重载配置完毕！{RESET}")

    except Exception as e:
        print(f"{RED}发生错误: {e}{RESET}")

def main():
    while True:
        choice = show_menu()

        if choice == "1":
            modify_lid_switch("1")
        elif choice == "2":
            modify_lid_switch("2")
        elif choice == "0":
            print(f"{MAGENTA}退出程序...{RESET}")
            break
        else:
            print(f"{RED}无效选项，请重新选择！{RESET}")

# 执行主函数
main()
