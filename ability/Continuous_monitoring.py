import os
import time
import psutil
from tabulate import tabulate

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

# 定义清空屏幕的函数
def clear_screen():
    """清空终端屏幕"""
    os.system('clear' if os.name == 'posix' else 'cls')


# 获取CPU温度
def get_cpu_temperature():
    """获取CPU温度（Linux）"""
    if os.name == 'posix':  # 针对Linux
        # 读取温度文件，获取温度数据
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = f.read()
                return float(temp) / 1000  # 温度单位转换为摄氏度
        except Exception as e:
            return f"无法获取温度: {e}"
    else:
        return "不支持此平台获取温度"


# 获取每个核心的负载
def get_cpu_load():
    """获取每个核心的负载"""
    return psutil.cpu_percent(percpu=True)


# 获取当前CPU频率
def get_cpu_frequency():
    """获取当前CPU频率"""
    return psutil.cpu_freq()


# 获取占用CPU最多的前五个进程
def get_top_processes():
    """获取占用CPU最多的前五个进程"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        try:
            processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    # 按照cpu_percent排序，取前五个
    top_processes = sorted(processes, key=lambda p: p['cpu_percent'], reverse=True)[:5]
    return top_processes


# 每秒刷新并展示信息
def display_table():
    """每秒刷新并展示信息"""
    while True:
        # 获取数据
        temperature = get_cpu_temperature()
        cpu_load = get_cpu_load()
        cpu_freq = get_cpu_frequency().current
        top_processes = get_top_processes()

        # 表格内容
        table_data = []

        # CPU信息
        table_data.append([f"{GREEN}CPU温度", f"{temperature}°C{RESET}"])
        table_data.append([f"{GREEN}CPU频率", f"{cpu_freq} MHz{RESET}"])

        # 将每个核心负载显示在一行上，用空格分隔
        core_loads = " ".join([f"{GREEN}核心{i + 1}: {load}%{RESET}" for i, load in enumerate(cpu_load)])
        table_data.append([f"{GREEN}核心负载{RESET}", core_loads])

        # 获取Top 5进程
        table_data.append([f"{GREEN}占用最高的进程:{RESET}", ""])
        for idx, process in enumerate(top_processes):
            table_data.append(
                [f"进程{idx + 1}: {process['name']}", f"PID: {process['pid']} | CPU: {process['cpu_percent']}%"])

        # 清空屏幕
        clear_screen()

        # 打印表格
        print(tabulate(table_data, headers=["项", "值"], tablefmt="grid"))

        # 每隔1秒刷新
        time.sleep(1)


# 常驻代码
clear_screen()
display_table()
