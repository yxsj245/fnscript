#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import sys
import importlib.metadata
import urllib.request
import urllib.error

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
    "网卡设置": [
        ("开启WOL网络唤醒", "WOLstart.py"),
    ],
    "工具": [
        ("分析目录文件大小", "filestorage.py"),
        ("安装虚拟机工具", "vmtoolses.py"),
        ("挂载物理CD/DVD", "cdmount.py"),
    ]
    # 您可以根据需要添加更多分类
}
# --- 用户配置区域结束 ---

SCRIPT_DIR_RELATIVE_TO_MENU = 'script'
CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TUISCRIPT_DIR = os.path.join(CURRENT_SCRIPT_DIR, SCRIPT_DIR_RELATIVE_TO_MENU)

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

def run_script(script_name, script_actual_filename, script_dir):
    script_path = os.path.join(script_dir, script_actual_filename)
    
    if not os.path.isfile(script_path):
        print(f"{AnsiColors.YELLOW}脚本 '{script_actual_filename}' 在本地目录 '{script_dir}' 未找到。{AnsiColors.RESET}")
        base_url = "http://blogpage.xiaozhuhouses.asia/api/fnscript_tui/"
        download_url = base_url + script_actual_filename
        print(f"{AnsiColors.CYAN}正在尝试从 {download_url} 下载...{AnsiColors.RESET}")
        
        # 确保 script_dir 存在
        if not os.path.exists(script_dir):
            try:
                os.makedirs(script_dir, exist_ok=True) # exist_ok=True 避免并发问题
                print(f"{AnsiColors.GREEN}已创建脚本目录: {script_dir}{AnsiColors.RESET}")
            except OSError as e:
                print(f"{AnsiColors.RED}创建脚本目录 {script_dir} 失败: {e}{AnsiColors.RESET}")
                input(f"\n{AnsiColors.CYAN}按 Enter 键返回菜单...{AnsiColors.RESET}")
                return

        try:
            urllib.request.urlretrieve(download_url, script_path)
            print(f"{AnsiColors.GREEN}脚本 '{script_actual_filename}' 下载成功。{AnsiColors.RESET}")
        except urllib.error.HTTPError as e:
            print(f"{AnsiColors.RED}下载脚本 '{script_actual_filename}' 失败 (HTTP Error {e.code}): {e.reason}{AnsiColors.RESET}")
            print(f"{AnsiColors.YELLOW}请检查文件名是否正确或服务器上是否存在该文件。{AnsiColors.RESET}")
            input(f"\n{AnsiColors.CYAN}按 Enter 键返回菜单...{AnsiColors.RESET}")
            return 
        except urllib.error.URLError as e:
            print(f"{AnsiColors.RED}下载脚本 '{script_actual_filename}' 失败 (URL Error): {e.reason}{AnsiColors.RESET}")
            print(f"{AnsiColors.YELLOW}请检查网络连接或URL。{AnsiColors.RESET}")
            input(f"\n{AnsiColors.CYAN}按 Enter 键返回菜单...{AnsiColors.RESET}")
            return
        except Exception as e:
            print(f"{AnsiColors.RED}下载脚本 '{script_actual_filename}' 时发生未知错误: {e}{AnsiColors.RESET}")
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

def main():
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
            display_footer(is_submenu=False)
            
            # Display "power by" message
            power_by_text = "power by 又菜又爱玩的小朱"
            # chinese_chars_count = sum(1 for char_pb in power_by_text if '\u4e00' <= char_pb <= '\u9fff')
            # english_chars_count = len(power_by_text) - chinese_chars_count
            # credit_display_width = english_chars_count + (chinese_chars_count * 2)
            # credit_padding = (terminal_width - credit_display_width) // 2
            # credit_padding = max(0, credit_padding)
            # print(f"\n{' ' * credit_padding}{AnsiColors.CYAN}{power_by_text}{AnsiColors.RESET}")
            print(f"\n{AnsiColors.CYAN}{power_by_text}{AnsiColors.RESET}") # 主菜单Power by靠左显示
            print() # Blank line before prompt

            print(f"{AnsiColors.MAGENTA}{AnsiColors.BOLD}请按键选择分类 (数字) 或 ESC 退出： {AnsiColors.RESET}", end='', flush=True)
            choice_char = get_single_char_from_terminal()

            if choice_char == '\x1b': # ESC
                clear_screen()
                print(f"{AnsiColors.GREEN}感谢使用，再见！{AnsiColors.RESET}")
                break
            
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
    # 首先检查并安装 Textual
    if not check_and_install_textual():
        input(f"{AnsiColors.RED}Textual 依赖项处理失败，按 Enter 键退出...{AnsiColors.RESET}")
        sys.exit(1) # 如果安装失败，退出程序

    if not os.path.isdir(TUISCRIPT_DIR):
        clear_screen()
        # display_fnscript_art() # Optionally show art on dir error too
        display_header("飞牛脚本启动器 - 错误")
        print(f"{AnsiColors.RED}{AnsiColors.BOLD}错误：脚本目录 '{TUISCRIPT_DIR}' 未找到。{AnsiColors.RESET}")
        print(f"{AnsiColors.YELLOW}请确保在 'menu.py' 文件同级目录下存在名为 'TUIscript' 的文件夹，并且其中包含您的脚本。{AnsiColors.RESET}")
        input(f"{AnsiColors.CYAN}按 Enter 键退出...{AnsiColors.RESET}")
    else:
        main()
