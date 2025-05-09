import os
import sys
import locale
import re
from tabulate import tabulate

# 解决 Windows 终端输入输出编码问题
sys.stdin.reconfigure(encoding=locale.getpreferredencoding())
sys.stdout.reconfigure(encoding=locale.getpreferredencoding())

# ANSI 颜色定义（仅终端使用）
GREEN = "\033[32m"
RESET = "\033[0m"

# 去除 ANSI 颜色的正则
ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def get_folder_size(folder_path):
    """计算目录的总大小，并获取文件列表"""
    total_size = 0
    files_info = []

    for dirpath, _, filenames in os.walk(folder_path, followlinks=True):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                if os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    total_size += file_size
                    files_info.append((filepath, file_size))
            except PermissionError:
                pass  # 忽略权限错误的文件
            except Exception:
                pass  # 其他异常也忽略

    return total_size, files_info

def format_size(size_in_bytes):
    """将字节数转换为可读格式"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024

def remove_ansi(text):
    """移除 ANSI 颜色控制字符"""
    return ANSI_ESCAPE_RE.sub('', text)

def analyze_directory(directory, save_path):
    """分析目录并保存结果，包括隐藏文件夹"""
    if not os.path.isdir(directory):
        print(f"'{directory}' 不是有效目录。")
        return

    # 获取所有子目录（包括隐藏目录）
    sub_dirs = [
        os.path.join(directory, d) for d in os.listdir(directory)
        if os.path.isdir(os.path.join(directory, d))
    ]

    output_lines = []

    for folder in [directory] + sub_dirs:
        total_size, files_info = get_folder_size(folder)

        output_lines.append(f"文件夹: {folder} - 总大小: {format_size(total_size)}")
        output_lines.append("文件列表（按大小排序）：")

        files_info.sort(key=lambda x: x[1], reverse=True)

        plain_table = [[file_path, format_size(file_size)] for file_path, file_size in files_info]
        output_lines.append(tabulate(plain_table, headers=["文件路径", "文件大小"], tablefmt="fancy_grid"))

    os.makedirs(save_path, exist_ok=True)
    save_file = os.path.join(save_path, "device_info_report.txt")

    with open(save_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    print(f"{GREEN}分析完成，由于输出展示文件可能较多会影响终端性能，已将结果保存到: {save_file}{RESET}")

# 获取用户输入
os.system('clear' if os.name == 'posix' else 'cls')
user_directory = input("请输入要分析的目录路径：").strip()
save_directory = input("请输入要保存输出结果的目录路径：").strip()

analyze_directory(user_directory, save_directory)
