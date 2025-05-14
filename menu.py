#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import sys
import importlib.metadata
import urllib.request
import urllib.error
import shutil # 新增导入
import argparse # 用于处理命令行参数

# Platform-specific imports for single character input
_IS_WINDOWS = os.name == 'nt'
if _IS_WINDOWS:
    import msvcrt
else:
    import tty
    import termios

# ANSI 转义码定义颜色和样式
class AnsiColors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[93m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    UNDERLINE = "\033[4m"

# --- 用户配置区域 ---
# 请在此定义您的菜单结构
# 格式:
# "一级分类中文名": [
#     ("二级脚本中文显示名1", "实际脚本文件名1.py"),
#     ("二级脚本中文显示名2", "实际脚本文件名2.py"),
# ],
# "另一个一级分类中文名": [
#     ...
# ]
MENU_CONFIG = {
    "系统设置": [
        ("IOMMU 开启", "startIOMMU.py"),
        ("电源管理", "Powermanagement.py"),
        ("开启IOMMU", "startIOMMU.py"),
        ("管理swap", "swapinfo.py"),
    ],
    "网卡/网络 设置": [
        ("开启WOL网络唤醒", "WOLstart.py"),
        ("网络诊断与修改", "network_diagnostic_tool.py"),
    ],
    "磁盘设置": [
        ("阵列状态和修复", "raid_repair_tui.py"),
    ],
    "工具": [
        ("分析目录文件大小", "filestorage.py"),
        ("安装虚拟机工具", "vmtoolses.py"),
        ("挂载物理CD/DVD", "cdmount.py"),
        ("qcow2转换工具", "qcowtools.py"),
        ("硬件压测", "self_inspection.py"),
        ("影音万能格式转换", "ffmpeg_converter_tui.py"),
    ]
    # 您可以根据需要添加更多分类
}
# --- 用户配置区域结束 ---

SCRIPT_DIR_RELATIVE_TO_MENU = 'script'
CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TUISCRIPT_DIR = os.path.join(CURRENT_SCRIPT_DIR, SCRIPT_DIR_RELATIVE_TO_MENU)
GIT_REPO_URL = "https://gitee.com/xiao-zhu245/fnscript.git" # 新增Git仓库地址
DEFAULT_GIT_BRANCH = "main" # 新增默认Git分支

def check_and_install_textual():
    """Checks if textual 0.45.0 is installed and installs it if not."""
    required_version = "0.45.0"
    package_name = "textual"
    try:
        installed_version = importlib.metadata.version(package_name)
        if installed_version == required_version:
            print(f"{AnsiColors.GREEN}{package_name} 版本 {required_version} 已安装。{AnsiColors.RESET}")
            return True
        else:
            print(f"{AnsiColors.YELLOW}检测到 {package_name} 版本 {installed_version}，需要版本 {required_version}。{AnsiColors.RESET}")
    except importlib.metadata.PackageNotFoundError:
        print(f"{AnsiColors.YELLOW}{package_name} 未安装。{AnsiColors.RESET}")

    print(f"{AnsiColors.CYAN}正在尝试安装/更新 {package_name}至版本 {required_version}...{AnsiColors.RESET}")
    install_command = [
        sys.executable, "-m", "pip", "install",
        "--break-system-packages",
        "--timeout", "1000",
        f"{package_name}=={required_version}",
        "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"
    ]
    try:
        process = subprocess.run(install_command, check=True, capture_output=True, text=True)
        print(f"{AnsiColors.GREEN}{package_name} 版本 {required_version} 安装成功。{AnsiColors.RESET}")
        # 验证安装后的版本
        try:
            installed_version_after_install = importlib.metadata.version(package_name)
            if installed_version_after_install == required_version:
                 print(f"{AnsiColors.GREEN}版本验证成功: {installed_version_after_install}{AnsiColors.RESET}")
                 return True
            else:
                print(f"{AnsiColors.RED}版本验证失败: 安装后版本为 {installed_version_after_install}，期望为 {required_version}。请手动检查。{AnsiColors.RESET}")
                return False
        except importlib.metadata.PackageNotFoundError:
            print(f"{AnsiColors.RED}错误: {package_name} 安装后仍未找到。请手动检查。{AnsiColors.RESET}")
            return False
    except subprocess.CalledProcessError as e:
        print(f"{AnsiColors.RED}安装 {package_name} 失败。错误信息:{AnsiColors.RESET}")
        print(e.stdout)
        print(e.stderr)
        return False
    except FileNotFoundError:
        print(f"{AnsiColors.RED}错误: pip 命令未找到。请确保 Python 和 pip 已正确安装并配置在系统路径中。{AnsiColors.RESET}")
        return False

def get_single_char_from_terminal():
    """Gets a single character from standard input without requiring Enter."""
    if _IS_WINDOWS:
        ch_byte = msvcrt.getch()
        if ch_byte == b'\x1b': return '\x1b'  # ESC
        if ch_byte == b'\x03': raise KeyboardInterrupt() # Ctrl+C
        if ch_byte == b'\r': return '\r' 
        try:
            return ch_byte.decode('utf-8', errors='ignore')
        except Exception:
            return '' 
    else:  # POSIX
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            char = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return char

def clear_screen():
    os.system('cls' if _IS_WINDOWS else 'clear')

def display_fnscript_art():
    F_art = ["█████", "█    ", "████ ", "█    ", "█    "]
    n_art = ["███", "█ █", "█ █", "█ █", "█ █"]
    S_art = [" ███", "█   ", " ██ ", "   █", "███ "]
    c_art = [" ██", "█  ", "█  ", "█  ", " ██"]
    r_art = ["██ ", "█ █", "██ ", "█ █", "█  █"]
    i_art = ["█", "█", "█", "█", "█"]
    p_art = ["███", "█ █", "███", "█  ", "█  "]
    t_art = ["███", " █ ", " █ ", " █ ", " █ "]
    space = " "
    
    FNSCRIPT_ART_LINES = []
    for i in range(5):
        line = (F_art[i] + space + n_art[i] + space + space + 
                S_art[i] + space + c_art[i] + space + r_art[i] + space + 
                i_art[i] + space + p_art[i] + space + t_art[i])
        FNSCRIPT_ART_LINES.append(line)

    num_art_lines = len(FNSCRIPT_ART_LINES)
    art_line_len = 0
    if num_art_lines > 0:
        art_line_len = len(FNSCRIPT_ART_LINES[0])

    try:
        terminal_width = os.get_terminal_size().columns
    except OSError:
        terminal_width = 80 

    # Canvas dimensions for shadow effect
    canvas_height = num_art_lines + 1 
    canvas_width = art_line_len + 1
    output_canvas = [[(" ") for _ in range(canvas_width)] for _ in range(canvas_height)]

    shadow_color_start = AnsiColors.BLUE 
    main_color_start = AnsiColors.CYAN + AnsiColors.BOLD # Changed main art color to Cyan
    color_end = AnsiColors.RESET
    char_block = '█'

    # Draw shadow layer (offset down and right)
    for r_idx in range(num_art_lines):
        art_line_str = FNSCRIPT_ART_LINES[r_idx]
        for c_idx in range(len(art_line_str)):
            if art_line_str[c_idx] == char_block:
                if (r_idx + 1 < canvas_height and c_idx + 1 < canvas_width):
                    output_canvas[r_idx + 1][c_idx + 1] = shadow_color_start + char_block + color_end

    # Draw main character layer
    for r_idx in range(num_art_lines):
        art_line_str = FNSCRIPT_ART_LINES[r_idx]
        for c_idx in range(len(art_line_str)):
            if art_line_str[c_idx] == char_block:
                if (r_idx < canvas_height and c_idx < canvas_width): 
                    output_canvas[r_idx][c_idx] = main_color_start + char_block + color_end
    
    print() # Space before art
    for r_canvas in range(canvas_height):
        print(f"{''.join(output_canvas[r_canvas])}") # Removed overall_art_padding

    print(f"{AnsiColors.YELLOW}GitHub: {AnsiColors.UNDERLINE}https://github.com/yxsj245/fnscript{AnsiColors.RESET}")
    print(f"{AnsiColors.YELLOW}Gitee: {AnsiColors.UNDERLINE}https://gitee.com/xiao-zhu245/fnscript{AnsiColors.RESET}")
    print(f"{AnsiColors.YELLOW}开源协议: MIT{AnsiColors.RESET}")
    print() # Add a blank line after this information for better separation from the header

def display_header(title_text, menu_width=70):
    print(AnsiColors.CYAN + AnsiColors.BOLD + "+" + "-" * menu_width + "+")
    try:
        title_display_len = 0
        for char_text_h in title_text:
            if '\u4e00' <= char_text_h <= '\u9fff':
                title_display_len += 2
            else:
                title_display_len += 1       
    except TypeError:
        title_display_len = len(title_text)
    title_padding = (menu_width - title_display_len) // 2
    title_padding = max(0, title_padding)
    remaining_padding = menu_width - title_display_len - title_padding
    remaining_padding = max(0, remaining_padding)
    print(f"{AnsiColors.CYAN}{AnsiColors.BOLD}|{' ' * title_padding}{AnsiColors.YELLOW}{title_text}{AnsiColors.RESET}{AnsiColors.CYAN}{AnsiColors.BOLD}{' ' * remaining_padding}|")
    print(AnsiColors.CYAN + AnsiColors.BOLD + "+" + "-" * menu_width + "+" + AnsiColors.RESET)

def display_menu_items(items, menu_width=70, item_color=AnsiColors.WHITE, index_color=AnsiColors.GREEN):
    for i, item_text in enumerate(items):
        try:
            current_item_display_len = 0
            for char_text_i in item_text:
                if '\u4e00' <= char_text_i <= '\u9fff':
                    current_item_display_len += 2
                else:
                    current_item_display_len += 1 
        except TypeError:
            current_item_display_len = len(item_text)
            
        line_content = f" {AnsiColors.BOLD}{index_color}{i+1}.{AnsiColors.RESET} {item_color}{item_text}{AnsiColors.RESET}"
        num_len = len(str(i+1))
        visible_len = num_len + 2 + current_item_display_len
        padding = menu_width - visible_len -1 
        padding = max(0, padding)
        print(f"{AnsiColors.CYAN}|{line_content}{' ' * padding}{AnsiColors.CYAN}|")

def display_footer(menu_width=70, is_submenu=False):
    print(AnsiColors.CYAN + AnsiColors.BOLD + "+" + "-" * menu_width + "+")
    if is_submenu:
        return_text_val = "返回上级菜单"
        return_prompt = f"{AnsiColors.BOLD}{AnsiColors.YELLOW}Q.{AnsiColors.RESET} {AnsiColors.YELLOW}{return_text_val}{AnsiColors.RESET}"
        try:
            current_text_len_f1 = 0
            for char_text_f1 in return_text_val:
                if '\u4e00' <= char_text_f1 <= '\u9fff':
                    current_text_len_f1 += 2
                else:
                    current_text_len_f1 += 1
            visible_len_f1 = len("Q. ") + current_text_len_f1
        except TypeError:
            visible_len_f1 = len("Q. ") + len(return_text_val)
        padding_f1 = menu_width - visible_len_f1 -1 
        padding_f1 = max(0, padding_f1)
        print(f"{AnsiColors.CYAN}| {return_prompt}{' ' * padding_f1}{AnsiColors.CYAN}|")

    exit_text_val = "退出程序"
    exit_prompt = f"{AnsiColors.BOLD}{AnsiColors.RED}ESC.{AnsiColors.RESET} {AnsiColors.RED}{exit_text_val}{AnsiColors.RESET}"
    try:
        current_text_len_f2 = 0
        for char_text_f2 in exit_text_val:
            if '\u4e00' <= char_text_f2 <= '\u9fff':
                current_text_len_f2 += 2
            else:
                current_text_len_f2 += 1
        visible_len_f2 = len("ESC. ") + current_text_len_f2
    except TypeError:
        visible_len_f2 = len("ESC. ") + len(exit_text_val)
    padding_f2 = menu_width - visible_len_f2 -1 
    padding_f2 = max(0, padding_f2)
    print(f"{AnsiColors.CYAN}| {exit_prompt}{' ' * padding_f2}{AnsiColors.CYAN}|")
    print(AnsiColors.CYAN + AnsiColors.BOLD + "+" + "-" * menu_width + "+" + AnsiColors.RESET)
    # print() # Removed extra blank line from here, will add before prompt if needed

def _run_git_command(command_args, operation_name, cwd):
    """Helper to run a Git command and handle common errors. cwd is now mandatory."""
    try:
        print(f"{AnsiColors.CYAN}正在执行: git {' '.join(command_args)} (在目录: {cwd}){AnsiColors.RESET}")
        process = subprocess.run(["git"] + command_args, check=True, capture_output=True, text=True, cwd=cwd)
        
        if process.stdout:
            print(f"{AnsiColors.GREEN}Git {operation_name} 输出:\n{process.stdout.strip()}{AnsiColors.RESET}")
        if process.stderr:
            stderr_output = process.stderr.strip()
            # Git pull 成功但无更改时，信息可能在 stderr, 或者一些警告
            # "Already up to date." 或法语/德语等其他语言的类似表达
            if any(phrase in stderr_output.lower() for phrase in ["already up to date", "déjà à jour", "bereits aktuell"]):
                print(f"{AnsiColors.GREEN}Git {operation_name}: {stderr_output}{AnsiColors.RESET}")
            elif stderr_output: # 任何其他 stderr 输出都视为警告或注意信息
                print(f"{AnsiColors.YELLOW}Git {operation_name} 注意信息:\n{stderr_output}{AnsiColors.RESET}")
        
        if not process.stdout and not (process.stderr and any(phrase in process.stderr.strip().lower() for phrase in ["already up to date", "déjà à jour", "bereits aktuell"])) and process.stderr.strip() != "":
             # 如果 stdout 为空，stderr 不为空且不是 'already up to date' 等信息，则可能表明某些操作虽未报错但未按预期进行
             pass # 允许继续，但上面已经打印了stderr作为YELLOW信息
        elif not process.stdout and not process.stderr.strip():
            print(f"{AnsiColors.GREEN}Git {operation_name} 执行完成，无输出。{AnsiColors.RESET}")

        return True
    except subprocess.CalledProcessError as e:
        print(f"{AnsiColors.RED}Git {operation_name} 失败。返回码: {e.returncode}{AnsiColors.RESET}")
        if e.stdout: print(f"{AnsiColors.RED}标准输出:\n{e.stdout.strip()}{AnsiColors.RESET}")
        if e.stderr: print(f"{AnsiColors.RED}标准错误:\n{e.stderr.strip()}{AnsiColors.RESET}")
        return False
    except FileNotFoundError:
        print(f"{AnsiColors.RED}错误: Git 命令未找到。请确保 Git 已正确安装并配置在系统路径中。{AnsiColors.RESET}")
        return False
    except Exception as e:
        print(f"{AnsiColors.RED}执行 Git {operation_name} 时发生未知错误: {e}{AnsiColors.RESET}")
        return False

def _prepare_repo_for_sparse_init():
    """Deletes the target script directory (TUISCRIPT_DIR) and any existing .git directory in CURRENT_SCRIPT_DIR."""
    target_script_actual_dir = TUISCRIPT_DIR
    parent_git_dir = os.path.join(CURRENT_SCRIPT_DIR, '.git')
    cleanup_ok = True

    print(f"{AnsiColors.YELLOW}准备清理环境以进行新的稀疏初始化...{AnsiColors.RESET}")

    if os.path.exists(target_script_actual_dir):
        print(f"{AnsiColors.CYAN}正在删除目标脚本目录: {target_script_actual_dir}{AnsiColors.RESET}")
        try:
            shutil.rmtree(target_script_actual_dir)
            print(f"{AnsiColors.GREEN}已删除目录: {target_script_actual_dir}{AnsiColors.RESET}")
        except OSError as e:
            print(f"{AnsiColors.RED}删除目录 '{target_script_actual_dir}' 失败: {e}{AnsiColors.RESET}")
            cleanup_ok = False
    
    if os.path.exists(parent_git_dir):
        print(f"{AnsiColors.CYAN}正在删除父目录中的 .git 目录: {parent_git_dir}{AnsiColors.RESET}")
        try:
            shutil.rmtree(parent_git_dir)
            print(f"{AnsiColors.GREEN}已删除目录: {parent_git_dir}{AnsiColors.RESET}")
        except OSError as e:
            print(f"{AnsiColors.RED}删除目录 '{parent_git_dir}' 失败: {e}{AnsiColors.RESET}")
            cleanup_ok = False
    
    if cleanup_ok:
        print(f"{AnsiColors.GREEN}环境清理完成。{AnsiColors.RESET}")
    else:
        print(f"{AnsiColors.RED}环境清理过程中发生错误。{AnsiColors.RESET}")
    return cleanup_ok

def ensure_scripts_are_present(force_update=False):
    """Ensures TUISCRIPT_DIR is populated by a sparse checkout of the remote 'script/' folder, with .git in CURRENT_SCRIPT_DIR."""
    target_branch = os.environ.get("FNSCRIPT_BRANCH", DEFAULT_GIT_BRANCH)
    print(f"{AnsiColors.CYAN}脚本库目标分支: {target_branch} (环境变量 FNSCRIPT_BRANCH, 默认 {DEFAULT_GIT_BRANCH}){AnsiColors.RESET}")

    # 首先备份menu.py
    menu_py_path = os.path.join(CURRENT_SCRIPT_DIR, "menu.py")
    menu_py_backup_path = os.path.join(CURRENT_SCRIPT_DIR, "menu.py.backup")
    menu_updated = False
    
    if os.path.exists(menu_py_path):
        print(f"{AnsiColors.YELLOW}正在备份当前的menu.py文件...{AnsiColors.RESET}")
        try:
            shutil.copy2(menu_py_path, menu_py_backup_path)
            print(f"{AnsiColors.GREEN}已备份menu.py到 {menu_py_backup_path}{AnsiColors.RESET}")
        except Exception as e:
            print(f"{AnsiColors.RED}备份menu.py失败: {e}{AnsiColors.RESET}")
    
    # 获取远程仓库的最新内容
    print(f"{AnsiColors.CYAN}正在获取远程仓库最新内容...{AnsiColors.RESET}")
    _run_git_command(["fetch", "origin"], "获取远程更新", cwd=CURRENT_SCRIPT_DIR)
    
    parent_git_dir = os.path.join(CURRENT_SCRIPT_DIR, '.git')
    is_git_repo_in_parent = os.path.isdir(parent_git_dir)
    
    needs_fresh_sparse_init = False
    is_correctly_configured_sparse = False

    if is_git_repo_in_parent:
        sparse_checkout_file_path = os.path.join(parent_git_dir, "info", "sparse-checkout")
        expected_config_line = SCRIPT_DIR_RELATIVE_TO_MENU + "/" 
        
        if os.path.isfile(sparse_checkout_file_path):
            try:
                with open(sparse_checkout_file_path, 'r') as f_sparse:
                    found_expected_line = False
                    for line in f_sparse:
                        if line.strip() == expected_config_line:
                            found_expected_line = True
                            break
                    if found_expected_line:
                        is_correctly_configured_sparse = True
                    else:
                        print(f"{AnsiColors.YELLOW}稀疏检出配置文件 '{sparse_checkout_file_path}' 内容 ('{line.strip() if 'line' in locals() else ''}') 与期望 ('{expected_config_line}') 不符。{AnsiColors.RESET}")
            except IOError as e_sparse_io:
                 print(f"{AnsiColors.YELLOW}无法读取稀疏检出配置文件 '{sparse_checkout_file_path}': {e_sparse_io}。假定配置不正确。{AnsiColors.RESET}")
        else:
            print(f"{AnsiColors.YELLOW}未找到稀疏检出配置文件 '{sparse_checkout_file_path}'。{AnsiColors.RESET}")
        
        if not is_correctly_configured_sparse:
            print(f"{AnsiColors.YELLOW}'{CURRENT_SCRIPT_DIR}' 中的 .git 仓库未正确配置为仅拉取远程 '{SCRIPT_DIR_RELATIVE_TO_MENU}/' 子目录。{AnsiColors.RESET}")
            needs_fresh_sparse_init = True
    else:
        print(f"{AnsiColors.YELLOW}在 '{CURRENT_SCRIPT_DIR}' 中未找到 .git 仓库。{AnsiColors.RESET}")
        needs_fresh_sparse_init = True

    # Determine action based on flags and current state
    if needs_fresh_sparse_init:
        print(f"{AnsiColors.CYAN}需要执行全新的稀疏初始化。{AnsiColors.RESET}")
        if not _prepare_repo_for_sparse_init(): 
            print(f"{AnsiColors.RED}环境清理失败，无法继续初始化。{AnsiColors.RESET}")
            return False
        
        print(f"{AnsiColors.CYAN}正在 '{CURRENT_SCRIPT_DIR}' 中初始化新的稀疏Git仓库并配置拉取远程 '{SCRIPT_DIR_RELATIVE_TO_MENU}/' ...{AnsiColors.RESET}")
        if not _run_git_command(["init"], "初始化仓库", cwd=CURRENT_SCRIPT_DIR): return False
        if not _run_git_command(["remote", "add", "origin", GIT_REPO_URL], "添加远程仓库", cwd=CURRENT_SCRIPT_DIR): return False
        if not _run_git_command(["config", "core.sparseCheckout", "true"], "启用稀疏检出", cwd=CURRENT_SCRIPT_DIR): return False
        
        sparse_checkout_config_file_to_write = os.path.join(CURRENT_SCRIPT_DIR, ".git", "info", "sparse-checkout")
        try:
            with open(sparse_checkout_config_file_to_write, 'w') as f_write_sparse:
                f_write_sparse.write(SCRIPT_DIR_RELATIVE_TO_MENU + "/\n") 
            print(f"{AnsiColors.GREEN}已配置稀疏检出以仅拉取远程 '{SCRIPT_DIR_RELATIVE_TO_MENU}/' 目录。{AnsiColors.RESET}")
        except IOError as e_write_sparse_io:
            print(f"{AnsiColors.RED}写入稀疏检出配置文件 '{sparse_checkout_config_file_to_write}' 失败: {e_write_sparse_io}{AnsiColors.RESET}")
            return False

        print(f"{AnsiColors.CYAN}正在从分支 '{target_branch}' 的远程 '{SCRIPT_DIR_RELATIVE_TO_MENU}/' 子目录拉取文件...{AnsiColors.RESET}")
        pull_command = ["pull", "origin", target_branch]
        # pull_command = ["pull", "--depth=1", "origin", target_branch] # Consider shallow clone
        if not _run_git_command(pull_command, f"稀疏拉取分支 {target_branch}", cwd=CURRENT_SCRIPT_DIR):
        #    print(f"{AnsiColors.YELLOW}浅层稀疏拉取失败，尝试完整稀疏拉取分支 '{target_branch}'...{AnsiColors.RESET}")
        #    if not _run_git_command(["pull", "origin", target_branch], f"稀疏拉取分支 {target_branch} (完整)", cwd=CURRENT_SCRIPT_DIR):
            print(f"{AnsiColors.RED}拉取远程分支 '{target_branch}' 的稀疏内容失败。{AnsiColors.RESET}")
            return False
        
        print(f"{AnsiColors.GREEN}已成功从远程仓库的 '{SCRIPT_DIR_RELATIVE_TO_MENU}/' 目录拉取文件到本地 '{TUISCRIPT_DIR}'。{AnsiColors.RESET}")
        return True
    
    elif force_update: # Repo is good (not needs_fresh_sparse_init), and force_update is true
        print(f"{AnsiColors.CYAN}尝试更新 '{CURRENT_SCRIPT_DIR}' 中现有稀疏脚本库到分支 '{target_branch}'...{AnsiColors.RESET}")
        
        # 尝试切换到目标分支
        if not _run_git_command(["checkout", target_branch], f"切换到分支 {target_branch}", cwd=CURRENT_SCRIPT_DIR): return False
        
        # 尝试拉取更新
        pull_result = _run_git_command(["pull", "origin", target_branch], f"拉取分支 {target_branch} 更新", cwd=CURRENT_SCRIPT_DIR)
        
        # 如果拉取失败，尝试使用方法三：强制覆盖本地文件
        if not pull_result:
            print(f"{AnsiColors.YELLOW}检测到本地有冲突文件，正在使用方法三（强制覆盖本地文件）...{AnsiColors.RESET}")
            if _run_git_command(["fetch", "origin"], "重新获取远程更新", cwd=CURRENT_SCRIPT_DIR) and \
               _run_git_command(["reset", "--hard", f"origin/{target_branch}"], "强制重置到远程版本", cwd=CURRENT_SCRIPT_DIR):
                print(f"{AnsiColors.GREEN}已成功强制更新到远程版本。{AnsiColors.RESET}")
                print(f"{AnsiColors.YELLOW}本地修改已被远程版本覆盖。{AnsiColors.RESET}")
                menu_updated = True
            else:
                print(f"{AnsiColors.RED}强制更新失败。{AnsiColors.RESET}")
                return False
        
        print(f"{AnsiColors.GREEN}稀疏脚本库已成功更新到分支 '{target_branch}'。{AnsiColors.RESET}")
        
        # 检查menu.py是否在更新过程中被移除
        if not os.path.exists(menu_py_path) and os.path.exists(menu_py_backup_path):
            print(f"{AnsiColors.YELLOW}检测到menu.py在更新过程中被移除，正在从备份恢复...{AnsiColors.RESET}")
            try:
                shutil.copy2(menu_py_backup_path, menu_py_path)
                print(f"{AnsiColors.GREEN}已从备份恢复menu.py文件{AnsiColors.RESET}")
                
                # 更新稀疏检出配置，显式包含menu.py
                sparse_checkout_file = os.path.join(parent_git_dir, "info", "sparse-checkout")
                if os.path.exists(sparse_checkout_file):
                    try:
                        with open(sparse_checkout_file, 'r') as f:
                            content = f.read()
                        
                        if "menu.py" not in content:
                            with open(sparse_checkout_file, 'a') as f:
                                f.write("\nmenu.py\n")
                            print(f"{AnsiColors.GREEN}已更新稀疏检出配置，显式包含menu.py文件{AnsiColors.RESET}")
                    except Exception as e:
                        print(f"{AnsiColors.YELLOW}更新稀疏检出配置失败: {e}{AnsiColors.RESET}")
            except Exception as e:
                print(f"{AnsiColors.RED}从备份恢复menu.py失败: {e}{AnsiColors.RESET}")
                print(f"{AnsiColors.RED}您可以手动复制 {menu_py_backup_path} 到 {menu_py_path}{AnsiColors.RESET}")
        
        # 更新结束后，删除备份文件
        if os.path.exists(menu_py_backup_path):
            try:
                os.remove(menu_py_backup_path)
                print(f"{AnsiColors.GREEN}已清理menu.py备份文件{AnsiColors.RESET}")
            except Exception as e:
                print(f"{AnsiColors.YELLOW}清理menu.py备份文件失败: {e}{AnsiColors.RESET}")
        
        # 如果menu.py被更新或恢复，提示用户重新运行
        if menu_updated or not os.path.exists(menu_py_path) != os.path.exists(menu_py_backup_path):
            print(f"\n{AnsiColors.GREEN}更新完成，请重新运行本脚本以应用最新版本。{AnsiColors.RESET}")
            input(f"{AnsiColors.CYAN}按 Enter 键退出...{AnsiColors.RESET}")
            sys.exit(0)  # 成功更新后退出程序
        
        return True
    
    else: # Repo is good, not force_update - just check branch status
        print(f"{AnsiColors.GREEN}'{CURRENT_SCRIPT_DIR}' 中的 .git 仓库已正确配置稀疏检出。{AnsiColors.RESET}")
        try:
            process_check_branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, check=True, cwd=CURRENT_SCRIPT_DIR
            )
            current_branch = process_check_branch.stdout.strip()
            if current_branch != target_branch:
                print(f"{AnsiColors.YELLOW}提示: 当前稀疏脚本库位于分支 '{current_branch}'，但配置的目标分支为 '{target_branch}'。{AnsiColors.RESET}")
                print(f"{AnsiColors.YELLOW}如需切换到分支 '{target_branch}' 并获取更新，请在主菜单选择 'U' 更新选项。{AnsiColors.RESET}")
            else:
                print(f"{AnsiColors.GREEN}稀疏脚本库当前位于分支 '{current_branch}' (与目标一致)。{AnsiColors.RESET}")
        except subprocess.CalledProcessError as e_branch_check:
            print(f"{AnsiColors.YELLOW}警告: 无法检查稀疏脚本库的当前分支: {e_branch_check.stderr.strip() if e_branch_check.stderr else 'Unknown error'}{AnsiColors.RESET}")
        except FileNotFoundError:
            print(f"{AnsiColors.RED}错误: Git 命令未找到，无法检查当前分支。{AnsiColors.RESET}")
        return True

def run_script(script_name, script_actual_filename, script_dir):
    print(f"{AnsiColors.CYAN}执行脚本 '{script_name}' 前检查脚本库状态...{AnsiColors.RESET}")
    if not ensure_scripts_are_present(force_update=False):
        print(f"{AnsiColors.RED}脚本库准备失败。无法执行脚本 '{script_name}'。{AnsiColors.RESET}")
        input(f"\n{AnsiColors.CYAN}按 Enter 键返回菜单...{AnsiColors.RESET}")
        return

    script_path = os.path.join(script_dir, script_actual_filename)
    
    if not os.path.isfile(script_path):
        print(f"{AnsiColors.RED}错误: 脚本文件 '{script_actual_filename}' 在 '{script_dir}' 中未找到。{AnsiColors.RESET}")
        print(f"{AnsiColors.YELLOW}这可能意味着该脚本不存在于远程仓库中，或者MENU_CONFIG配置有误。{AnsiColors.RESET}")
        print(f"{AnsiColors.YELLOW}请尝试从主菜单更新脚本库，如果问题依旧，请检查脚本名和配置。{AnsiColors.RESET}")
        input(f"\n{AnsiColors.CYAN}按 Enter 键返回菜单...{AnsiColors.RESET}")
        return
    
    # 执行脚本
    clear_screen()
    print(f"{AnsiColors.YELLOW}正在启动脚本: {AnsiColors.BOLD}{script_name}{AnsiColors.RESET}{AnsiColors.YELLOW} (文件: {script_actual_filename})...{AnsiColors.RESET}\n")
    original_stdin_settings = None
    if not _IS_WINDOWS:
        fd = sys.stdin.fileno()
        original_stdin_settings = termios.tcgetattr(fd)
    try:
        process = subprocess.run([sys.executable, script_path], cwd=script_dir)
        if process.returncode != 0:
            print(f"\n{AnsiColors.RED}脚本 '{script_name}' 执行完毕，返回码: {process.returncode}{AnsiColors.RESET}")
        else:
            print(f"\n{AnsiColors.GREEN}脚本 '{script_name}' 执行完毕。{AnsiColors.RESET}")
    except FileNotFoundError: # 主要捕获 sys.executable 未找到的情况
        print(f"\n{AnsiColors.RED}错误：无法执行脚本。可能是Python解释器 '{sys.executable}' 未找到或脚本 '{script_path}' 下载后仍有问题。{AnsiColors.RESET}")
    except Exception as e:
        print(f"\n{AnsiColors.RED}运行脚本 '{script_name}' 时发生错误: {e}{AnsiColors.RESET}")
    finally:
        if not _IS_WINDOWS and original_stdin_settings:
             termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, original_stdin_settings)
    input(f"\n{AnsiColors.CYAN}按 Enter 键返回菜单...{AnsiColors.RESET}")

def bind_to_root_login():
    """将脚本绑定到root登录时自动运行（执行sudo -i时自动启动）"""
    if _IS_WINDOWS:
        print(f"{AnsiColors.RED}此功能仅支持Linux系统。{AnsiColors.RESET}")
        return False
    
    # 以下代码仅在Linux/Unix系统执行
    # 获取当前脚本的绝对路径
    current_script_path = os.path.abspath(__file__)
    
    # 检查是否已经是root用户
    try:
        is_root = os.geteuid() == 0
    except AttributeError:
        # 如果在某些Unix系统上没有geteuid函数
        print(f"{AnsiColors.RED}无法确定当前用户权限，可能不支持此功能。{AnsiColors.RESET}")
        return False
    
    if not is_root:
        print(f"{AnsiColors.YELLOW}您需要具有root权限才能设置登录绑定。{AnsiColors.RESET}")
        print(f"{AnsiColors.YELLOW}正在尝试通过sudo请求权限...{AnsiColors.RESET}")
        try:
            cmd = ["sudo", sys.executable, current_script_path, "--bind"]
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"{AnsiColors.RED}sudo请求失败: {e}{AnsiColors.RESET}")
            return False
    
    # 现在我们以root身份运行，执行绑定操作
    try:
        # 确定bashrc文件位置
        bashrc_path = "/root/.bashrc"
        
        # 要添加的内容
        menu_command = f"python3 {current_script_path}"
        marker_start = "# FNSCRIPT-AUTO-START BEGIN"
        marker_end = "# FNSCRIPT-AUTO-START END"
        
        # 检查是否已经存在
        if os.path.exists(bashrc_path):
            with open(bashrc_path, 'r') as f:
                content = f.read()
                if marker_start in content:
                    print(f"{AnsiColors.YELLOW}脚本已经绑定到root登录。{AnsiColors.RESET}")
                    return True
        
        # 添加到.bashrc
        with open(bashrc_path, 'a') as f:
            f.write(f"\n{marker_start}\n")
            f.write(f"# 以下命令将在root登录时自动运行飞牛脚本\n")
            f.write(f"{menu_command}\n")
            f.write(f"{marker_end}\n")
        
        print(f"{AnsiColors.GREEN}成功将脚本绑定到root登录！{AnsiColors.RESET}")
        print(f"{AnsiColors.GREEN}当您执行 sudo -i 进入root模式时，本脚本将自动启动。{AnsiColors.RESET}")
        return True
    except Exception as e:
        print(f"{AnsiColors.RED}绑定脚本到root登录时出错: {e}{AnsiColors.RESET}")
        return False

def unbind_from_root_login():
    """解除脚本与root登录的绑定"""
    if _IS_WINDOWS:
        print(f"{AnsiColors.RED}此功能仅支持Linux系统。{AnsiColors.RESET}")
        return False
    
    # 以下代码仅在Linux/Unix系统执行
    # 检查是否已经是root用户
    try:
        is_root = os.geteuid() == 0
    except AttributeError:
        # 如果在某些Unix系统上没有geteuid函数
        print(f"{AnsiColors.RED}无法确定当前用户权限，可能不支持此功能。{AnsiColors.RESET}")
        return False
    
    if not is_root:
        print(f"{AnsiColors.YELLOW}您需要具有root权限才能解除登录绑定。{AnsiColors.RESET}")
        print(f"{AnsiColors.YELLOW}正在尝试通过sudo请求权限...{AnsiColors.RESET}")
        try:
            current_script_path = os.path.abspath(__file__)
            cmd = ["sudo", sys.executable, current_script_path, "--unbind"]
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"{AnsiColors.RED}sudo请求失败: {e}{AnsiColors.RESET}")
            return False
    
    # 现在我们以root身份运行，执行解绑操作
    try:
        # 确定bashrc文件位置
        bashrc_path = "/root/.bashrc"
        
        # 要查找和删除的标记
        marker_start = "# FNSCRIPT-AUTO-START BEGIN"
        marker_end = "# FNSCRIPT-AUTO-START END"
        
        # 检查文件是否存在
        if not os.path.exists(bashrc_path):
            print(f"{AnsiColors.YELLOW}.bashrc文件不存在，无需解绑。{AnsiColors.RESET}")
            return True
        
        # 读取原始内容
        with open(bashrc_path, 'r') as f:
            lines = f.readlines()
        
        # 寻找标记并删除标记内的内容
        new_lines = []
        skip_mode = False
        found = False
        
        for line in lines:
            if marker_start in line:
                skip_mode = True
                found = True
                continue
            if marker_end in line:
                skip_mode = False
                continue
            if not skip_mode:
                new_lines.append(line)
        
        # 如果找到标记，则重写文件
        if found:
            with open(bashrc_path, 'w') as f:
                f.writelines(new_lines)
            print(f"{AnsiColors.GREEN}成功解除脚本与root登录的绑定！{AnsiColors.RESET}")
        else:
            print(f"{AnsiColors.YELLOW}未找到绑定标记，无需解绑。{AnsiColors.RESET}")
        
        return True
    except Exception as e:
        print(f"{AnsiColors.RED}解除绑定时出错: {e}{AnsiColors.RESET}")
        return False

def main():
    # 处理命令行参数
    parser = argparse.ArgumentParser(description='飞牛脚本启动器')
    parser.add_argument('--bind', action='store_true', help='将脚本绑定到root登录时自动运行')
    parser.add_argument('--unbind', action='store_true', help='解除脚本与root登录的绑定')
    args = parser.parse_args()
    
    # 处理绑定参数
    if args.bind:
        if _IS_WINDOWS:
            print(f"{AnsiColors.RED}绑定功能仅支持Linux系统。{AnsiColors.RESET}")
            sys.exit(1)
        if bind_to_root_login():
            return
        else:
            sys.exit(1)
    
    # 处理解绑参数
    if args.unbind:
        if _IS_WINDOWS:
            print(f"{AnsiColors.RED}解绑功能仅支持Linux系统。{AnsiColors.RESET}")
            sys.exit(1)
        if unbind_from_root_login():
            return
        else:
            sys.exit(1)
    
    global MENU_CONFIG
    
    # Initial validation removed. Script existence will be checked at runtime by run_script.
    # validated_menu_config = validate_menu_config(MENU_CONFIG, TUISCRIPT_DIR)

    if not MENU_CONFIG: # Check if MENU_CONFIG itself is empty
        clear_screen() 
        display_fnscript_art() 
        display_header("飞牛脚本启动器 - 配置错误")
        print(f"{AnsiColors.RED}{AnsiColors.BOLD}错误：MENU_CONFIG 为空。{AnsiColors.RESET}")
        print(f"{AnsiColors.YELLOW}请在脚本中定义 'MENU_CONFIG'。{AnsiColors.RESET}")
        input(f"{AnsiColors.CYAN}按 Enter 键退出...{AnsiColors.RESET}")
        return

    categories = list(MENU_CONFIG.keys())
    terminal_width = 80 
    try:
        terminal_width = os.get_terminal_size().columns
    except OSError:
        pass # Use default if fails

    original_stdin_settings_main = None
    if not _IS_WINDOWS:
        fd_main = sys.stdin.fileno()
        try:
            original_stdin_settings_main = termios.tcgetattr(fd_main)
        except termios.error as e:
            pass 

    try:
        while True: # Main menu loop
            clear_screen()
            display_fnscript_art() # Display art at the top of the main menu
            display_header("飞牛脚本启动器 - 主菜单")
            display_menu_items(categories, item_color=AnsiColors.MAGENTA)
            
            # 在菜单底部添加系统管理选项
            print(AnsiColors.CYAN + AnsiColors.BOLD + "+" + "-" * 70 + "+")
            
            # 根据系统是否为Windows显示不同的绑定/解绑选项
            if _IS_WINDOWS:
                admin_options = [
                    f"{AnsiColors.BOLD}{AnsiColors.RED}B.{AnsiColors.RESET} {AnsiColors.RED}绑定到root登录 (仅支持Linux系统){AnsiColors.RESET}",
                    f"{AnsiColors.BOLD}{AnsiColors.RED}D.{AnsiColors.RESET} {AnsiColors.RED}取消root登录绑定 (仅支持Linux系统){AnsiColors.RESET}",
                    f"{AnsiColors.BOLD}{AnsiColors.YELLOW}U.{AnsiColors.RESET} {AnsiColors.YELLOW}更新脚本{AnsiColors.RESET}"
                ]
            else:
                admin_options = [
                    f"{AnsiColors.BOLD}{AnsiColors.YELLOW}B.{AnsiColors.RESET} {AnsiColors.YELLOW}绑定到root登录{AnsiColors.RESET}",
                    f"{AnsiColors.BOLD}{AnsiColors.YELLOW}D.{AnsiColors.RESET} {AnsiColors.YELLOW}取消root登录绑定{AnsiColors.RESET}",
                    f"{AnsiColors.BOLD}{AnsiColors.YELLOW}U.{AnsiColors.RESET} {AnsiColors.YELLOW}更新脚本{AnsiColors.RESET}"
                ]
            
            for option in admin_options:
                # 去除颜色代码后计算实际长度
                cleaned_option = option.replace(AnsiColors.BOLD, '').replace(AnsiColors.RESET, '')
                cleaned_option = cleaned_option.replace(AnsiColors.YELLOW, '').replace(AnsiColors.RED, '')
                padding = 70 - len(cleaned_option) - 1
                padding = max(0, padding)
                print(f"{AnsiColors.CYAN}| {option}{' ' * padding}{AnsiColors.CYAN}|")
            
            display_footer(is_submenu=False)
            
            # Display "power by" message
            power_by_text = "power by 又菜又爱玩的小朱"
            print(f"\n{AnsiColors.CYAN}{power_by_text}{AnsiColors.RESET}") # 主菜单Power by靠左显示
            print() # Blank line before prompt

            # 提示信息也根据系统类型显示不同内容
            if _IS_WINDOWS:
                prompt = f"{AnsiColors.MAGENTA}{AnsiColors.BOLD}请按键选择分类 (数字), U 更新脚本, 或 ESC 退出： {AnsiColors.RESET}"
            else:
                prompt = f"{AnsiColors.MAGENTA}{AnsiColors.BOLD}请按键选择分类 (数字), U 更新脚本, B 绑定root, D 解绑, 或 ESC 退出： {AnsiColors.RESET}"
            
            print(prompt, end='', flush=True)
            choice_char = get_single_char_from_terminal()

            if choice_char == '\x1b': # ESC
                clear_screen()
                print(f"{AnsiColors.GREEN}感谢使用，再见！{AnsiColors.RESET}")
                break
            
            if choice_char.upper() == 'U':
                clear_screen()
                display_fnscript_art()
                display_header("飞牛脚本启动器 - 更新脚本库")
                print(f"{AnsiColors.CYAN}正在检查并更新脚本库...{AnsiColors.RESET}")
                if ensure_scripts_are_present(force_update=True):
                    print(f"\n{AnsiColors.GREEN}脚本库更新处理完成。{AnsiColors.RESET}")
                else:
                    print(f"\n{AnsiColors.RED}脚本库更新失败。请检查网络连接和Git是否正确安装及配置。{AnsiColors.RESET}")
                input(f"{AnsiColors.CYAN}按 Enter 键返回主菜单...{AnsiColors.RESET}")
                continue
            
            if choice_char.upper() == 'B':
                if _IS_WINDOWS:
                    print(f"\n{AnsiColors.RED}绑定功能仅支持Linux系统。{AnsiColors.RESET}")
                    input(f"{AnsiColors.CYAN}按 Enter 键返回主菜单...{AnsiColors.RESET}")
                    continue
                
                clear_screen()
                display_fnscript_art()
                display_header("飞牛脚本启动器 - 绑定到root登录")
                print(f"{AnsiColors.CYAN}正在尝试绑定脚本到root登录...{AnsiColors.RESET}")
                bind_to_root_login()
                input(f"\n{AnsiColors.CYAN}按 Enter 键返回主菜单...{AnsiColors.RESET}")
                continue
            
            if choice_char.upper() == 'D':
                if _IS_WINDOWS:
                    print(f"\n{AnsiColors.RED}解绑功能仅支持Linux系统。{AnsiColors.RESET}")
                    input(f"{AnsiColors.CYAN}按 Enter 键返回主菜单...{AnsiColors.RESET}")
                    continue
                
                clear_screen()
                display_fnscript_art()
                display_header("飞牛脚本启动器 - 取消root登录绑定")
                print(f"{AnsiColors.CYAN}正在尝试取消脚本与root登录的绑定...{AnsiColors.RESET}")
                unbind_from_root_login()
                input(f"\n{AnsiColors.CYAN}按 Enter 键返回主菜单...{AnsiColors.RESET}")
                continue
            
            try:
                choice_num = int(choice_char)
                if 1 <= choice_num <= len(categories):
                    selected_category_name = categories[choice_num-1]
                    scripts_in_category = MENU_CONFIG[selected_category_name] # Use MENU_CONFIG directly
                    
                    while True: # Submenu loop
                        clear_screen()
                        display_fnscript_art() # 在子菜单也显示艺术字
                        display_header(f"分类：{selected_category_name}")
                        script_display_names = [s[0] for s in scripts_in_category]
                        display_menu_items(script_display_names)
                        display_footer(is_submenu=True)
                        
                        print(f"\n{AnsiColors.CYAN}{power_by_text}{AnsiColors.RESET}") # 子菜单Power by靠左显示
                        print()

                        print(f"{AnsiColors.MAGENTA}{AnsiColors.BOLD}请按键选择脚本 (数字), Q 返回, 或 ESC 退出： {AnsiColors.RESET}", end='', flush=True)
                        sub_choice_char = get_single_char_from_terminal()

                        if sub_choice_char == '\x1b': # ESC
                            clear_screen()
                            print(f"{AnsiColors.GREEN}感谢使用，再见！{AnsiColors.RESET}")
                            if not _IS_WINDOWS and original_stdin_settings_main:
                                try: termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, original_stdin_settings_main)
                                except termios.error: pass 
                            return 

                        if sub_choice_char.upper() == 'Q':
                            break 
                        
                        try:
                            sub_choice_num = int(sub_choice_char)
                            if 1 <= sub_choice_num <= len(scripts_in_category):
                                script_to_run_display_name, script_to_run_filename = scripts_in_category[sub_choice_num-1]
                                
                                if not _IS_WINDOWS and original_stdin_settings_main:
                                    try: termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, original_stdin_settings_main)
                                    except termios.error: pass 
                                
                                run_script(script_to_run_display_name, script_to_run_filename, TUISCRIPT_DIR)
                                
                            else:
                                print(f"\n{AnsiColors.RED}无效选项: '{sub_choice_char}'{AnsiColors.RESET}")
                                input(f"{AnsiColors.CYAN}按 Enter 键继续...{AnsiColors.RESET}")
                        except ValueError:
                            if sub_choice_char: 
                                print(f"\n{AnsiColors.RED}无效输入: '{sub_choice_char}'. 请输入数字, Q, 或 ESC。{AnsiColors.RESET}")
                                input(f"{AnsiColors.CYAN}按 Enter 键继续...{AnsiColors.RESET}")
                else:
                    print(f"\n{AnsiColors.RED}无效的分类选项: '{choice_char}'{AnsiColors.RESET}")
                    input(f"{AnsiColors.CYAN}按 Enter 键继续...{AnsiColors.RESET}")
            except ValueError:
                if choice_char and choice_char != '\x1b': 
                    print(f"\n{AnsiColors.RED}无效输入: '{choice_char}'. 请输入数字选择分类或按 ESC 退出。{AnsiColors.RESET}")
                    input(f"{AnsiColors.CYAN}按 Enter 键继续...{AnsiColors.RESET}")
            except KeyboardInterrupt:
                clear_screen()
                print(f"\n{AnsiColors.YELLOW}捕获到中断信号，正在退出...{AnsiColors.RESET}")
                break
    finally:
        if not _IS_WINDOWS and original_stdin_settings_main:
             try: termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, original_stdin_settings_main)
             except termios.error: pass 

if __name__ == "__main__":
    # 首先检查在Windows系统上尝试使用bind/unbind选项的情况
    if _IS_WINDOWS and ("--bind" in sys.argv or "--unbind" in sys.argv):
        if "--bind" in sys.argv:
            print(f"{AnsiColors.RED}错误: 绑定功能仅支持Linux系统。{AnsiColors.RESET}")
        elif "--unbind" in sys.argv:
            print(f"{AnsiColors.RED}错误: 解绑功能仅支持Linux系统。{AnsiColors.RESET}")
        sys.exit(1)
    
    # 首先检查并安装 Textual
    if not check_and_install_textual():
        input(f"{AnsiColors.RED}Textual 依赖项处理失败，按 Enter 键退出...{AnsiColors.RESET}")
        sys.exit(1) # 如果安装失败，退出程序

    # 如果是通过命令行参数直接处理绑定或解绑，则不需要初始化脚本库
    if "--bind" in sys.argv or "--unbind" in sys.argv:
        main()
        sys.exit(0)

    print(f"{AnsiColors.CYAN}正在初始化并检查脚本库...{AnsiColors.RESET}")
    if not ensure_scripts_are_present(force_update=False): # Initial check/clone
        clear_screen()
        # display_fnscript_art() # 可以在错误时显示
        display_header("飞牛脚本启动器 - 初始化错误")
        print(f"{AnsiColors.RED}{AnsiColors.BOLD}错误：无法初始化脚本库。{AnsiColors.RESET}")
        print(f"{AnsiColors.YELLOW}尝试从 '{GIT_REPO_URL}' 克隆脚本。{AnsiColors.RESET}")
        print(f"{AnsiColors.YELLOW}请检查您的网络连接以及Git是否已正确安装并配置在系统路径中。{AnsiColors.RESET}")
        input(f"{AnsiColors.CYAN}按 Enter 键退出...{AnsiColors.RESET}")
        sys.exit(1)
    else:
        print(f"{AnsiColors.GREEN}脚本库准备就绪。{AnsiColors.RESET}")
        # time.sleep(1) # 可选的短暂暂停
        main()
