import os
import subprocess
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

# 获取CPU信息
def get_cpu_info():
    cpu_info = {
        'cpu_count_logical': psutil.cpu_count(logical=True),  # 逻辑核心数
        'cpu_count_physical': psutil.cpu_count(logical=False),  # 物理核心数
        'cpu_freq': psutil.cpu_freq().current,  # 当前CPU频率
        'cpu_model': None,  # 默认型号为空
        'cpu_usage_per_core': [f"{x}%" for x in psutil.cpu_percent(percpu=True, interval=1)],  # 每个核心的CPU使用率
    }

    # 获取CPU型号，Linux和Windows的命令不同
    if os.name == 'posix':  # Linux系统
        command = "lscpu"
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        cpu_info['cpu_model'] = result.stdout.split("\n")[4].split(":")[1].strip()
    elif os.name == 'nt':  # Windows系统
        command = "wmic cpu get Caption"
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        cpu_info['cpu_model'] = result.stdout.split("\n")[1].strip()

    # 获取CPU温度（仅适用于Linux系统，且硬件支持）
    if os.name == 'posix':
        try:
            temp_command = "sensors | grep 'Core 0' | awk '{print $3}'"
            temp_result = subprocess.run(temp_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                         shell=True)
            cpu_info['cpu_temp'] = temp_result.stdout.strip()  # 获取CPU温度
        except Exception as e:
            cpu_info['cpu_temp'] = '无法获取温度'

    return cpu_info


# 获取内存信息
def get_memory_info():
    memory_info = psutil.virtual_memory()
    swap_info = psutil.swap_memory()
    memory = {
        'total_memory': memory_info.total,
        'available_memory': memory_info.available,
        'used_memory': memory_info.used,
        'memory_percent': memory_info.percent,
        'total_swap': swap_info.total,
        'used_swap': swap_info.used,
        'swap_percent': swap_info.percent
    }
    return memory


# 获取磁盘信息
def get_disk_info():
    disk_info = []
    for partition in psutil.disk_partitions():
        usage = psutil.disk_usage(partition.mountpoint)
        disk_info.append({
            'device': partition.device,
            'mountpoint': partition.mountpoint,
            'fstype': partition.fstype,
            'total': usage.total,
            'used': usage.used,
            'free': usage.free,
            'percent': usage.percent
        })
    return disk_info


# 获取PCIe设备信息
def get_pci_devices():
    # 在Linux系统上使用 `lspci` 命令获取PCI设备信息
    if os.name == 'posix':
        command = "lspci"
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        return result.stdout
    elif os.name == 'nt':
        # Windows系统上使用 `wmic` 命令获取PCI设备信息
        command = "wmic path Win32_PnPEntity get Caption"
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        return result.stdout
    else:
        return "Unsupported OS for PCIe device query."


# 保存信息到文件
def save_info_to_file(file_path):
    print(f"{BLUE}正在获取硬件信息...{RESET}")
    try:
        # 获取硬件信息
        cpu_info = get_cpu_info()
        memory_info = get_memory_info()
        disk_info = get_disk_info()
        pci_devices = get_pci_devices()

        print(f"{BLUE}正在保存配置信息...{RESET}")
        # 打开文件进行写入
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("===== CPU Information =====\n")
            f.write(f"CPU 核心数 (逻辑): {cpu_info['cpu_count_logical']}\n")
            f.write(f"CPU 核心数 (物理): {cpu_info['cpu_count_physical']}\n")
            f.write(f"当前 CPU 频率: {cpu_info['cpu_freq']} MHz\n")
            f.write(f"CPU 型号: {cpu_info['cpu_model']}\n")
            f.write(f"每个核心的使用率: {', '.join(cpu_info['cpu_usage_per_core'])}\n")
            f.write(f"CPU 温度: {cpu_info.get('cpu_temp', '无法获取温度')}\n\n")

            f.write("===== Memory Information =====\n")
            f.write(f"总内存: {memory_info['total_memory'] / (1024 ** 3):.2f} GB\n")
            f.write(f"可用内存: {memory_info['available_memory'] / (1024 ** 3):.2f} GB\n")
            f.write(f"已用内存: {memory_info['used_memory'] / (1024 ** 3):.2f} GB\n")
            f.write(f"内存使用率: {memory_info['memory_percent']}%\n")
            f.write(f"总交换区: {memory_info['total_swap'] / (1024 ** 3):.2f} GB\n")
            f.write(f"已用交换区: {memory_info['used_swap'] / (1024 ** 3):.2f} GB\n")
            f.write(f"交换区使用率: {memory_info['swap_percent']}%\n\n")

            f.write("===== Disk Information =====\n")
            for disk in disk_info:
                f.write(f"设备: {disk['device']}\n")
                f.write(f"挂载点: {disk['mountpoint']}\n")
                f.write(f"文件系统类型: {disk['fstype']}\n")
                f.write(f"总空间: {disk['total'] / (1024 ** 3):.2f} GB\n")
                f.write(f"已用空间: {disk['used'] / (1024 ** 3):.2f} GB\n")
                f.write(f"空闲空间: {disk['free'] / (1024 ** 3):.2f} GB\n")
                f.write(f"使用率: {disk['percent']}%\n\n")

            f.write("===== PCIe Devices =====\n")
            f.write(pci_devices)

        print(f"{GREEN}信息已保存到: {file_path}{RESET}")
    except Exception as e:
        print(f"{RED}发生错误: {e}{RESET}")


# 让用户输入保存路径并保存硬件信息
def main():
    save_path = input(f"请输入保存文件的路径 (例如: /path/to/your/file.txt {RED}切记需要在复制的详细路径后面写上需要保存的文件名！{RESET}): ")
    save_info_to_file(save_path)

if __name__ == "__main__":
    main()
