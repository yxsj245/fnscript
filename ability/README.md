# 功能以及说明
## `cdmount.py`——挂载CD驱动器的脚本
使用命令如下
- `mount`、`eject`
### 运行过程
#### 挂载与弹出
1. 【挂载】默认在管理员用户的第一个存储空间中创建`CD_DVD`的一个文件夹，然后根据cd名称在这个文件夹内创建名为`sr0`文件夹，名字最后一个数字是驱动器的代号，根据数量以此类推。
2. 【弹出】使用`eject`命令进行标准化向驱动器发送弹出命令，物理驱动器会自动弹出光盘，与此同时挂载目录将会自动释放，可以正常删除目录。

## `processinfo.py Continuous_monitoring.py deviceinfo.py`——查看系统资源信息
通过python第三方库`psutil`获取系统资源信息然后根据相关判断代码进行输出向用户展示，结束进程同样。

## `startIOMMU.py`——一键开启IOMMU 
根据B站本视频教程【飞牛安装虚拟机及硬件直通攻略 保姆级教程】 https://www.bilibili.com/video/BV1mJfaYxEYN/?share_source=copy_web&vd_source=6fdda38be5eb9fcf9f074fd04e9bf9ae

## `swapinfo.py`——开关swap
通过编辑系统中`/etc/fstab`文件 注释`swap_line`代码实现关闭，开启swap就是将此代码取消注释

## `qcowtools.py`——转换磁盘映像格式
使用命令如下
- `qemu-img`

## `filestorage.py`——列出指定目录的所有文件夹所占磁盘大小
使用python自带标准库`os`获取文件信息
