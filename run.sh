#!/bin/bash

# 定义下载所有脚本的函数
download_all_scripts() {
    # 下载 run.py 到当前目录
    echo "正在下载py主程序"
    curl -k -o run.py "https://pub-46d21cac9c7d44b79d73abfeb727999f.r2.dev/Linux%E8%84%9A%E6%9C%AC/%E9%A3%9E%E7%89%9B/run.py"

    # 创建 ability 文件夹
    mkdir -p ability

    # 下载 cdmount.py 到 ability 文件夹
    echo "正在下载所有py方法程序"
    curl -k -o ability/cdmount.py "https://pub-46d21cac9c7d44b79d73abfeb727999f.r2.dev/Linux%E8%84%9A%E6%9C%AC/%E9%A3%9E%E7%89%9B/ability/cdmount.py"
    curl -k -o ability/processinfo.py "https://pub-46d21cac9c7d44b79d73abfeb727999f.r2.dev/Linux%E8%84%9A%E6%9C%AC/%E9%A3%9E%E7%89%9B/ability/processinfo.py"
    curl -k -o ability/startIOMMU.py "https://pub-46d21cac9c7d44b79d73abfeb727999f.r2.dev/Linux%E8%84%9A%E6%9C%AC/%E9%A3%9E%E7%89%9B/ability/startIOMMU.py"
    curl -k -o ability/swapinfo.py "https://pub-46d21cac9c7d44b79d73abfeb727999f.r2.dev/Linux%E8%84%9A%E6%9C%AC/%E9%A3%9E%E7%89%9B/ability/swapinfo.py"
    curl -k -o ability/qcowtools.py "https://pub-46d21cac9c7d44b79d73abfeb727999f.r2.dev/Linux%E8%84%9A%E6%9C%AC/%E9%A3%9E%E7%89%9B/ability/qcowtools.py"
    echo "所有程序 下载/更新 完毕"
}

# 询问用户操作选项
echo "欢迎使用脚本管理器，这是一个用来下载更新和启动python主程序的脚本"
echo "请选择操作："
echo "1) 执行python程序"
echo "2) 仅下载并更新所有python程序"
echo "3) 更新脚本管理器"

read -p "请输入选项 [1 2 3]: " choice

# 如果 run.py 或 cdmount.py 文件不存在，则下载所有脚本
if [ ! -f "run.py" ]; then
    echo "主脚本缺失，开始下载所有脚本..."
    download_all_scripts
else
    echo "所有脚本已存在。"
fi

# 执行用户选择的操作
if [ "$choice" -eq 1 ]; then
    # 执行 run.py 脚本
    echo "正在执行 run.py 脚本..."
    python3 run.py
elif [ "$choice" -eq 2 ]; then
    echo "已完成脚本下载/更新。"
elif [ "$choice" -eq 3 ]; then
    # 更新当前脚本
    curl -k -o run.sh "https://pub-46d21cac9c7d44b79d73abfeb727999f.r2.dev/Linux%E8%84%9A%E6%9C%AC/%E9%A3%9E%E7%89%9B/run.sh"
    echo "当前脚本更新完毕，请ctrl+c结束重新执行 . run.sh 命令运行"
else
    echo "无效选项，请选择 1、2 或 3。"
fi
