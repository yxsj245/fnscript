import psutil
import os

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


def get_highest_usage_process(resource_type="CPU"):
    """根据选择的资源类型获取占用最多资源的进程"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'exe']):
        try:
            processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # 根据选择的资源类型排序，找出占用最多的进程
    if resource_type == "CPU":
        highest_process = max(processes, key=lambda p: p['cpu_percent'], default=None)
    elif resource_type == "内存":
        highest_process = max(processes, key=lambda p: p['memory_percent'], default=None)

    return highest_process


def print_process_info(process, resource_type="CPU"):
    """打印进程信息并添加颜色"""
    if process:
        print(f"{MAGENTA}进程ID:{RESET} {process['pid']}")
        print(f"{CYAN}进程名称:{RESET} {process['name']}")
        print(
            f"{YELLOW}{resource_type}占用:{RESET} {process['cpu_percent'] if resource_type == 'CPU' else process['memory_percent']}%")
        print(f"{BLUE}进程路径:{RESET} {process['exe']}")
    else:
        print("未找到相关进程信息")


def user_choice(pid, process_name):
    """用户选择是否结束进程"""
    print(f"\n{RED}警告：结束进程可能会影响系统稳定性，确保您了解该进程的作用。{RESET}")
    choice = input(f"\n是否结束进程 {process_name} (PID: {pid})？(y/n): ").strip().lower()

    if choice == "y":
        print(f"{GREEN}正在结束进程 {process_name} (PID: {pid})...{RESET}")
        try:
            process = psutil.Process(pid)
            process.terminate()  # 终止进程
            process.wait()  # 等待进程终止
            print(f"{GREEN}进程 {process_name} 已成功终止。{RESET}")
        except psutil.NoSuchProcess:
            print(f"{RED}进程 {process_name} 不存在或已经终止。{RESET}")
        except psutil.AccessDenied:
            print(f"{RED}没有权限结束进程 {process_name}。{RESET}")
    else:
        print(f"{YELLOW}未结束进程。{RESET}")


def main():
    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        print("请选择要检测的资源：")
        print("1. 检测 CPU 占用")
        print("2. 检测内存占用")
        print("n. 返回主菜单")

        choice = input("请输入 1 或 2: ").strip()

        if choice == "1":
            resource_type = "CPU"
        elif choice == "2":
            resource_type = "内存"
        else:
            break

        print(f"\n正在获取占用最多 {resource_type} 资源的进程信息...\n")

        # 获取占用最多资源的进程
        highest_process = get_highest_usage_process(resource_type)

        if highest_process:
            # 输出占用最多资源的进程信息
            print(f"{BOLD}最占用 {resource_type} 的进程:{RESET}")
            print_process_info(highest_process, resource_type)

            # 用户选择是否结束进程
            user_choice(highest_process['pid'], highest_process['name'])
        else:
            print(f"{RED}未能获取到占用 {resource_type} 资源最多的进程。{RESET}")
    return

if __name__ == "__main__":
    main()
