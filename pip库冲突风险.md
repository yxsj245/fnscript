### 从 Python 3.11 开始，Debian/Ubuntu 等系统启用了 PEP 668，不允许你直接用 pip install 安装包到系统的 Python 目录中，防止破坏系统依赖
在安装 `textual`的同时会把他所依赖的pip库进行升级，经过查询，此库依赖下面的库运行 \
`importlib-metadata` `markdown-it-py` `rich` `typing-extensions` \
这些库的安装不会影响系统。本人在没有安装textual库的设备进行依次查询每个库的版本发现部分库的版本信息可能在安装textual库后进行了升级。 
| PIP库 | 0.9.2飞牛系统内置库版本 | 安装后的版本 |
| ------- | ------- |------- |
|   markdown-it-py      |   2.1.0      | 3.0.0|
| rich | 13.3.1 | 14.0.0 |

表格中没有的是在没有安装textual库的设备不存在这个库，将不会产生应用级别兼容风险。
升级后的pip库可能会产生应用级别的兼容问题，如果您在使用飞牛相关使用到python，尤其是AI相关，若执行出现错误，可以执行此命令回退到飞牛系统内置库版本来解决安装`textual`造成的问题
```bash
pip install --break-system-packages markdown-it-py==2.1.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install --break-system-packages rich==13.3.1 -i https://pypi.tuna.tsinghua.edu.cn/simple
```
### 请注意：当你回退后，textual库将无法正常使用，如果您想继续使用，请重新运行安装textual库命令即可。
```bash
pip install --break-system-packages textual==0.45.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
```
