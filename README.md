# 2.0版本分支，将会有以下改进
1. 重构代码
2. 计划采用GUI终端图形化交互式菜单，就像是在使用图形化，仅需鼠标点击，全程不需要使用键盘选择

# 如何使用
## TUI交互式运行
所有脚本目前均已实现图形化TUI交互式操作，您可以直接使用一键使用命令后根据菜单提示选择对应功能，默认使用的是TUI。由于脚本TUI采用的是 `textual` 库，这个库无法通过apt进行安装和管理，所以必须强行通过pip来进行安装（曾考虑过进行打包后执行但部分脚本可能存在打包后运行问题）
[点击这里查阅详细冲突风险以及解决方案](https://github.com/yxsj245/fnscript/blob/2.0/pip%E5%BA%93%E5%86%B2%E7%AA%81%E9%A3%8E%E9%99%A9.md)
### 使用运行命令
```bash
git clone https://gitee.com/xiao-zhu245/fnscript.git
cd fnscript/
python3 menu.py
```
## 传统命令行运行
若您担心pip库冲突风险或无法使用交互式终端情况下，我将部分功能单一的脚本增加了传统通过命令行形式运行的功能，在无需安装`textual`库就可以直接运行使用
### 如何使用
您可以通过此命令拉取任意脚本后直接使用
```bash
python3 此处替换脚本名称 -h #获取参数信息
```
# 脚本信息

| 脚本名称 | 作用 | 是否支持TUI | 是否支持命令行 |
| ------- | ------- | ------- | ------- |
|  cdmount.py      |  挂载CD/DVD       |✅|❎|
|  filestorage.py      |  分析目录文件大小       |✅|❎|
|  Powermanagement.py      |  电源管理       |✅|✅|
|  qcowtools.py      |  qcow2转换工具       |✅|✅|
|  self_inspection.py      |  硬件压测       |✅|✅|
|  startIOMMU.py      |  开启IOMMU直通       |✅|✅|
|  swapinfo.py      |  管理swap       |✅|✅|
|  vmtoolses.py      |  安装虚拟机工具       |✅|✅|
|  WOLstart.py      |  开启WOL网络唤醒       |✅|✅|
|  network_diagnostic_tool.py      |  网络诊断与修改       |✅|✅|
|  raid_repair_tui.py      |  阵列状态和修复       |✅|❎|
|  ffmpeg_converter_tui.py      |  影音万能格式转换       |✅|❎|
