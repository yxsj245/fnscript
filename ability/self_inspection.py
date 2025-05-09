import os
import subprocess
import time
import psutil

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
    """显示主菜单"""
    clear_screen()
    print(f"{BOLD}{CYAN}系统健康检测工具{RESET}\n")
    print(f"{GREEN}1.{RESET} 内存检测 (使用 memtester)")
    print(f"{GREEN}2.{RESET} CPU 压测")
    print(f"{GREEN}3.{RESET} 退出\n")

def get_test_memory():
    """计算可用于测试的内存 (剩余内存的 85%)"""
    available_memory = psutil.virtual_memory().available // (1024 * 1024)  # 获取可用内存 (MB)
    return int(available_memory * 0.97)  # 取 95% 进行测试

def check_memory_usage():
    """检查当前内存使用情况，若过高则警告用户"""
    memory_usage = psutil.virtual_memory().percent
    if memory_usage > 80:
        print(f"{RED}警告: 当前系统内存使用率已达 {memory_usage}%!{RESET}")
        choice = input(f"{YELLOW}建议关闭一些软件后再运行，继续运行可能检测效果不够准确 (y/N): {RESET}").strip().lower()
        if choice != 'y':
            return False
    return True

def memory_test():
    """执行内存检测"""
    if not check_memory_usage():
        return
    try:
        mem_size = f"{get_test_memory()}M"
        print(f"{BLUE}正在运行内存测试，请勿进行其它操作，如果运行过程中出现死机重启则大概率为内存问题。整个测试过程预计 30-120 分钟 具体根据内存大小，如果需要终止测试请按ctral+c{RESET}")
        subprocess.run(["sudo", "memtester", mem_size, "1"], check=True)
    except Exception as e:
        print(f"{RED}发生错误: {e}{RESET}")
    input(f"{MAGENTA}按 Enter 返回菜单...{RESET}")

def cpu_stress_test():
    """执行 CPU 压测"""
    try:
        duration = input(f"{YELLOW}请输入 CPU 压测时长 (秒): {RESET}")
        print(f"{BLUE}正在进行 CPU 压测...{RESET}")
        subprocess.run(["stress", "--cpu", "4", "--timeout", duration], check=True)
    except Exception as e:
        print(f"{RED}发生错误: {e}{RESET}")
    input(f"{MAGENTA}按 Enter 返回菜单...{RESET}")

def main():
    while True:
        display_menu()
        choice = input(f"{BOLD}{YELLOW}请选择功能 (1-3): {RESET}")
        if choice == '1':
            print(f"{RED}建议关闭所有docker容器以及停用所有应用程序以保证检测的准确性。按任意键继续...{RESET}")
            input()
            memory_test()
        elif choice == '2':
            cpu_stress_test()
        elif choice == '3':
            print(f"{GREEN}退出程序...{RESET}")
            break
        else:
            print(f"{RED}无效输入，请重新选择！{RESET}")
            time.sleep(1)

if __name__ == "__main__":
    main()
