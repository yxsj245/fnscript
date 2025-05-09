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


# 常驻函数
def clear_screen():
    """清空终端屏幕"""
    os.system('clear' if os.name == 'posix' else 'cls')


def run_command(command):
    """直接执行命令并返回执行结果，包括状态码和标准输出/错误"""
    result = {
        'status_code': 0,  # 默认状态码为 0 (正常执行)
        'stdout': '',  # 正常执行信息输出
        'stderr': ''  # 错误执行信息输出
    }

    try:
        # 执行命令并等待执行完成
        process_result = subprocess.run(command, check=True, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)

        # 获取标准输出内容
        result['stdout'] = process_result.stdout.decode()
        return result
    except subprocess.CalledProcessError as e:
        # 捕获异常，获取错误信息
        result['status_code'] = 1  # 设置状态码为 1，表示执行失败
        result['stderr'] = e.stderr.decode()
        return result


# qemu-img 转换函数
def convert_image(source_path, target_name=None, target_format='qcow2'):
    """使用 qemu-img 工具转换磁盘映像格式"""
    # 如果目标名称为空，使用默认目标文件名
    if not target_name:
        target_name = os.path.splitext(os.path.basename(source_path))[0] + '.' + target_format

    # 获取文件所在路径
    target_path = os.path.join(os.path.dirname(source_path), target_name)

    # 构造 qemu-img 命令
    command = ['qemu-img', 'convert', '-O', target_format, source_path, target_path]

    # 执行命令并返回结果
    result = run_command(command)

    if result['status_code'] == 0:
        print(f"{GREEN}{BOLD}转换成功！目标文件路径：{target_path}{RESET}")
    else:
        if 'Unknown file format' in result['stderr']:
            print(f"{RED}转换失败\n错误输出:未知文件格式\n建议操作：请确认输入的转换类型{RESET}")
        else:
            print(f"{RED}{BOLD}转换失败！错误信息：{result['stderr']}{RESET}")


# 常驻代码
clear_screen()


# 示例：获取用户输入并执行转换
def main():
    print(f"{CYAN}请输入源文件路径(右键需要转换文件的详细信息复制原始路径)：{RESET}")
    source_path = input().strip()

    # 确保文件路径存在
    if not os.path.isfile(source_path):
        print(f"{RED}错误：源文件不存在！{RESET}")
        return

    print(f"{CYAN}请输入转换后的文件名称（例如:is.qcow2。您可以不写后缀，因为Linux不通过后缀名判断文件类型，但为了直观，我们推荐您写个后缀。）：{RESET}")
    target_name = input().strip() or None

    print(f"{CYAN}请输入转的的格式（默认使用qcow2）：{RESET}")
    target_format = input().strip() or 'qcow2'

    # 调用转换函数
    print(f"{BLUE}正在转换中,请稍后...(预计1分钟内完成){RESET}")
    convert_image(source_path, target_name, target_format)


if __name__ == '__main__':
    main()
