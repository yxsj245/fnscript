# 运行库
import os
import subprocess
import glob

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

# 常驻函数
def clear_screen():
    """清空终端屏幕"""
    os.system('clear' if os.name == 'posix' else 'cls')

def run_as_root(command):
    """以 root 权限执行命令，并返回执行结果，包括状态码和标准输出/错误"""
    result = {
        'status_code': 0,  # 默认状态码为 0 (正常执行)
        'stdout': '', # 正常执行信息输出
        'stderr': '' # 错误执行信息输出
    }

    try:
        # 使用 sudo 执行命令并等待执行完成
        process_result = subprocess.run(['sudo', 'bash', '-c', command], check=True, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)

        # 获取标准输出内容
        result['stdout'] = process_result.stdout.decode()
        return result
    except subprocess.CalledProcessError as e:
        # 捕获异常，获取错误信息
        result['status_code'] = 1  # 设置状态码为 1，表示执行失败
        result['stderr'] = e.stderr.decode()
        return result

# 脚本函数

def detect_cd_drives():
    """动态检测系统中的所有 CD 驱动器（/dev/sr*）"""
    cd_drives = glob.glob('/dev/sr*')  # 查找所有 /dev/srX 的设备
    return cd_drives

def create_mount_path(cd_drive):
    """根据 CD 驱动器创建唯一的挂载路径"""
    # 提取驱动器名（如 sr0, sr1）
    drive_name = os.path.basename(cd_drive)
    # 创建挂载路径：/vol1/1000/CD_DVD/sr0
    mount_path = f"/vol1/1000/CD_DVD/{drive_name}"
    # 如果挂载目录不存在，则创建
    if not os.path.exists(mount_path):
        os.makedirs(mount_path)
    return mount_path

def mount_cd(cd_drive, mount_path):
    """挂载 CD 驱动器"""
    command = f"mount {cd_drive} {mount_path}"
    return run_as_root(command)

def eject_cd(selected_drive):
    """弹出 CD 驱动器"""
    command = f"eject {selected_drive}"
    return run_as_root(command)

# 常驻代码
clear_screen()
print(f"{YELLOW}挂载CD/DVD程序 版本1.0{RED}")
print(f'{RED}风险告知：由于此脚本中运行的指令涉及在root用户下才能运行，脚本会创建一个root终端执行相应命令并在执行完毕后自动关闭。由于root权限强大，为了保证数据安全，请您务必在执行前经过测试或数据备份再进行！对此出现的意外情况，作者不承担任何责任。按任意键表示继续运行，ctrl+c可终止运行{RESET}')
print(f'{BLUE}此方法中不存在删除文件操作，您可以放心运行！{RESET}')
input()
clear_screen()

# 脚本代码
# 检测 CD 驱动器
cd_drives = detect_cd_drives()

if cd_drives:
    print(f"{GREEN}检测到以下 CD/DVD 驱动器：{RESET}")
    for idx, drive in enumerate(cd_drives, start=1):
        print(f"{CYAN}{idx}. {drive}{RESET}")

    print("请选择操作：")
    print("1. 挂载 CD/DVD")
    print("2. 弹出 CD/DVD")
    print("3. 退出")

    choice = input(f"{CYAN}请输入选项 (1/2/3): {RESET}")

    if choice == '1':
        # 选择要挂载的驱动器
        drive_choice = int(input(f"{CYAN}请输入要挂载的驱动器编号: {RESET}"))
        if 1 <= drive_choice <= len(cd_drives):
            selected_drive = cd_drives[drive_choice - 1]
            mount_path = create_mount_path(selected_drive)
            print(f"{MAGENTA}正在挂载 {selected_drive} 到 {mount_path}...{RESET}")
            result = mount_cd(selected_drive, mount_path)
            if result['status_code'] != 0:
                if "no medium found on" in result['stderr']:
                    print(f"{YELLOW}挂载失败\n 错误原因：找不到介质 \n 建议操作：请确认CD已正确放入DVD中后再次尝试{RESET}")
                elif "already mounted on" in result['stderr']:
                    print(f"{YELLOW}挂载失败\n 错误原因：已安装 \n 建议操作：请先弹出CD{RESET}")
                else:
                    print(f"{RED}挂载失败，错误输出\n{result['stderr']}\n请截图在github提交issue或联系作者排查{RESET}")
            else:
                print(f"{YELLOW}挂载成功，如需删除挂载的文件夹，请先弹出{RED}")
        else:
            print(f"{RED}无效的驱动器编号！{RESET}")

    elif choice == '2':
        # 选择要弹出的驱动器
        drive_choice = int(input(f"{CYAN}请输入要弹出的驱动器编号: {RESET}"))
        if 1 <= drive_choice <= len(cd_drives):
            selected_drive = cd_drives[drive_choice - 1]
            print(f"{MAGENTA}正在弹出 {selected_drive}...{RESET}")
            result = eject_cd(selected_drive)
            if result['status_code'] != 0:
                print(f"{RED}弹出失败，错误输出\n{result['stderr']}\n请截图在github提交issue或联系作者排查{RESET}")
            else:
                print(f"{YELLOW}弹出成功，您可以删除挂载的文件夹{RED}")
        else:
            print(f"{RED}无效的驱动器编号！{RESET}")

    elif choice == '3':
        print("退出程序。")
    else:
        print(f"{RED}无效的选项！{RESET}")
else:
    print(f"{RED}未检测到 CD/DVD 驱动器。\n 温馨提示：如果您是USB的驱动器，走的是USB外置存储，无需使用此脚本进行额外挂载。{RESET}")