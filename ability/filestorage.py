import os
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


def get_folder_size(folder_path):
    """递归计算文件夹的总大小"""
    total_size = 0
    files_info = []  # 存储文件的大小和路径
    for dirpath, dirnames, filenames in os.walk(folder_path, followlinks=True):  # 增加followlinks，确保遍历符号链接
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                if os.path.exists(filepath):  # 可能有链接失效的情况
                    file_size = os.path.getsize(filepath)
                    total_size += file_size
                    files_info.append((filepath, file_size))  # 添加文件大小和路径
            except PermissionError:
                print(f"权限不足，无法访问文件: {filepath}")
            except Exception as e:
                print(f"无法处理文件 {filepath}: {e}")
    return total_size, files_info


def format_size(size_in_bytes):
    """将字节大小转换为合适的单位"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024


def list_folders_by_size(directory):
    """列出指定目录下所有文件夹的存储占用，按大小从大到小排序"""
    folder_sizes = []

    # 确保输入的是一个有效目录
    if not os.path.isdir(directory):
        print(f"'{directory}' 不是一个有效的目录。")
        return

    # 遍历目录，获取所有子文件夹的大小
    for item in os.listdir(directory):
        folder_path = os.path.join(directory, item)
        if os.path.isdir(folder_path):
            size, files_info = get_folder_size(folder_path)
            # 只将大小大于0的文件夹添加到结果中
            if size > 0:
                folder_sizes.append((folder_path, size, files_info))

    # 按照大小从大到小排序
    folder_sizes.sort(key=lambda x: x[1], reverse=True)

    # 打印表格的表头
    print(f"目录 '{directory}' 下的文件夹按大小排序：")
    print("\n" + "-" * 60)
    print(f"{'文件夹路径':<45} {'文件夹大小':<15}")
    print("-" * 60)

    # 输出文件夹表格
    folder_table = []
    for folder, size, _ in folder_sizes:
        folder_table.append([f"{BLUE}{folder}{RESET}", f"{format_size(size)}"])

    print(tabulate(folder_table, headers=["文件夹路径", "文件夹大小"], tablefmt="fancy_grid"))

    # 输出每个文件夹中的文件信息表格
    for folder, size, files_info in folder_sizes:
        print(f"\n{CYAN}文件夹: {folder}{RESET} - 总大小: {format_size(size)}")
        print(f"{CYAN}文件列表（按大小排序）:{RESET}")

        files_info.sort(key=lambda x: x[1], reverse=True)

        file_table = []
        for file_path, file_size in files_info:
            file_table.append([f"{GREEN}{file_path}{RESET}", f"{format_size(file_size)}"])

        print(tabulate(file_table, headers=["文件路径", "文件大小"], tablefmt="fancy_grid"))


# 用户输入目录
os.system('clear' if os.name == 'posix' else 'cls')
user_directory = input("请输入要查看的目录路径：")
list_folders_by_size(user_directory)
