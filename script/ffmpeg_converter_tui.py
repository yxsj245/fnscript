#!/usr/bin/env python
import os
import sys
import subprocess
import asyncio

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
    Log,
    Select,
    Static,
)
from textual.validation import Function, Regex
from textual import events


# --- FFmpeg 相关配置 ---
# 尝试找到 ffmpeg
FFMPEG_PATH = "ffmpeg"  # 默认认为 ffmpeg 在 PATH 中
FFMPEG_AVAILABLE = True  # 默认认为可用，避免界面问题

# 创建一个简单的是/否选项列表
YESNO_OPTIONS = [
    ("否", "no"),
    ("是", "yes"),
]

# 常见的音视频输出格式
COMMON_FORMATS = [
    ("MP4 (视频)", "mp4"),
    ("MKV (视频)", "mkv"),
    ("AVI (视频)", "avi"),
    ("MOV (视频)", "mov"),
    ("WEBM (视频)", "webm"),
    ("GIF (动画)", "gif"),
    ("MP3 (音频)", "mp3"),
    ("AAC (音频)", "aac"),
    ("FLAC (音频)", "flac"),
    ("WAV (音频)", "wav"),
    ("OGG (音频)", "ogg"),
]

# 常见的视频编码器选项
VIDEO_ENCODERS = [
    ("H.264 (libx264) - 兼容性最佳", "libx264"),
    ("H.265/HEVC (libx265) - 高压缩率", "libx265"),
    ("VP9 - 开源格式", "libvpx-vp9"),
    ("AV1 - 新一代开源格式", "libaom-av1"),
    # 硬件加速编码器
    ("NVIDIA GPU (H.264) - nvenc", "h264_nvenc"),
    ("NVIDIA GPU (H.265) - nvenc", "hevc_nvenc"),
    ("Intel QSV (H.264)", "h264_qsv"),
    ("Intel QSV (H.265)", "hevc_qsv"),
    ("AMD GPU (H.264)", "h264_amf"),
    ("AMD GPU (H.265)", "hevc_amf"),
    ("复制源编码（不重新编码）", "copy"),
]

# 硬件加速解码选项
HW_DECODERS = [
    ("不使用硬件加速", ""),
    ("NVIDIA CUDA/CUVID", "cuda"),
    ("NVIDIA NVDEC", "cuda -hwaccel_output_format cuda"),
    ("Intel QSV", "qsv"),
    ("DirectX VA2 (Windows)", "dxva2"),
    ("D3D11VA (Windows 8+)", "d3d11va"),
]

# 编码器预设
ENCODER_PRESETS = [
    ("超快 (ultrafast)", "ultrafast"),
    ("非常快 (veryfast)", "veryfast"),
    ("快速 (faster)", "faster"),
    ("快 (fast)", "fast"),
    ("中等 (medium) - 默认", "medium"),
    ("慢 (slow)", "slow"),
    ("较慢 (slower)", "slower"),
    ("非常慢 (veryslow)", "veryslow"),
]

# 横纵比选项
ASPECT_RATIOS = [
    ("不修改", ""),
    ("4:3", "4:3"),
    ("16:9", "16:9"),
    ("1:1", "1:1"),
    ("21:9", "21:9"),
    ("2.35:1", "2.35:1"),
]

def check_ffmpeg():
    """检查 ffmpeg 是否可用"""
    global FFMPEG_AVAILABLE, FFMPEG_PATH
    
    # 可能的 ffmpeg 路径列表
    possible_paths = [
        "ffmpeg",                   # 默认 PATH 中
        "/usr/bin/ffmpeg",         # 常见 Linux 路径
        "/usr/local/bin/ffmpeg",   # 常见 macOS, BSD 路径
        "/opt/bin/ffmpeg",         # 某些 NAS 系统
        "/opt/local/bin/ffmpeg",   # 某些 NAS 系统
    ]
    
    # 尝试从环境变量 FFMPEG_PATH 获取路径
    env_path = os.environ.get('FFMPEG_PATH')
    if env_path:
        possible_paths.insert(0, env_path)  # 添加到列表首位
    
    # 尝试从命令行参数 --ffmpeg-path 获取路径
    for i, arg in enumerate(sys.argv):
        if arg == "--ffmpeg-path" and i + 1 < len(sys.argv):
            possible_paths.insert(0, sys.argv[i + 1])
            break
            
    # 尝试所有可能的路径
    for path in possible_paths:
        try:
            print(f"尝试检测 ffmpeg 路径: {path}")
            process = subprocess.Popen([path, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if process.returncode == 0 and b"ffmpeg version" in stdout.lower():
                FFMPEG_PATH = path
                FFMPEG_AVAILABLE = True
                print(f"已找到可用的 ffmpeg: {path}")
                return True
        except FileNotFoundError:
            continue
    
    print("未能找到可用的 ffmpeg")
    return False

class SimplifiedFFmpegApp(App):
    """简化版的 FFmpeg 文件转换器"""

    TITLE = "FFmpeg 文件转换器"
    
    # 添加键盘绑定
    BINDINGS = [
        ("c", "start_conversion", "开始转换"),
    ]
    
    # 简化的 CSS
    CSS = """
    #main-container {
        width: 100%;
        height: 100%;
        overflow: hidden;
    }
    
    #dir-tree {
        width: 40%;
        height: 60%;
        dock: left;
        border: solid green;
    }
    
    #form-container {
        width: 60%;
        height: 60%;
        dock: right;
        border: solid blue;
        overflow: auto;
    }
    
    #log-container {
        width: 100%;
        height: 40%;
        dock: bottom;
        border: solid red;
    }
    
    Label {
        width: 100%;
        height: 1;
    }
    
    Input, Select {
        width: 100%;
        margin-bottom: 1;
    }
    
    Button {
        margin: 1;
    }
    
    #convert-button {
        background: green;
    }
    """
    
    # 保存当前选择的源文件路径
    source_file_path = reactive("")
    
    def compose(self) -> ComposeResult:
        """简化界面布局，减少嵌套层次"""
        yield Header()
        
        with Container(id="main-container"):
            # 左侧文件浏览器
            yield DirectoryTree(os.path.expanduser("~"), id="dir-tree")
            
            # 右侧参数表单 - 使用垂直布局
            with Vertical(id="form-container"):
                # 基本文件参数
                yield Label("源文件:")
                yield Input(placeholder="点击左侧文件或直接输入路径", id="source-path")
                
                yield Label("输出文件名:")
                yield Input(placeholder="例如: converted_video", id="output-name")
                
                # 输出格式
                yield Label("输出格式:")
                yield Select(COMMON_FORMATS, value="mp4", id="output-format")
                
                yield Label("自定义输出格式:")
                yield Input(value="mp4", placeholder="例如: mkv, mp4, avi...", id="custom-format")
                
                # 编码选项
                yield Label("跳过重新编码:")
                yield Select(YESNO_OPTIONS, value="no", id="no-reencoding")
                
                # 视频编码器选项
                yield Label("视频编码器:")
                yield Select(VIDEO_ENCODERS, value="libx264", id="video-encoder")
                
                # 添加硬件加速解码选项
                yield Label("硬件加速解码:")
                yield Select(HW_DECODERS, value="", id="hw-decoder")
                
                yield Label("编码预设:")
                yield Select(ENCODER_PRESETS, value="medium", id="encoder-preset")
                
                # 添加高级选项
                yield Label("去除音频:")
                yield Select(YESNO_OPTIONS, value="no", id="remove-audio")
                
                yield Label("去除视频:")
                yield Select(YESNO_OPTIONS, value="no", id="remove-video")
                
                yield Label("起始时间 (秒):")
                yield Input(placeholder="例如: 10.5", id="start-time")
                
                yield Label("持续时长 (秒):")
                yield Input(placeholder="例如: 60", id="duration")
                
                yield Label("帧率:")
                yield Input(placeholder="例如: 30", id="frame-rate")
                
                yield Label("帧大小 (宽x高):")
                yield Input(placeholder="例如: 1280x720", id="frame-size")
                
                yield Label("横纵比:")
                yield Select(ASPECT_RATIOS, value="", id="aspect-ratio")
                
                # 按钮
                with Horizontal():
                    yield Button("开始转换", id="convert-button")
                    yield Button("退出", id="quit-button")
            
            # 底部日志区
            with Container(id="log-container"):
                yield Label("日志输出:")
                yield Log(id="log", highlight=True, max_lines=100)
        
        yield Footer()
    
    def on_mount(self) -> None:
        """组件挂载后执行"""
        log = self.query_one("#log", Log)
        log.write_line("欢迎使用 FFmpeg 文件转换器")
        
        # 获取并显示 FFmpeg 版本
        if FFMPEG_AVAILABLE:
            try:
                process = subprocess.run([FFMPEG_PATH, "-version"], capture_output=True, text=True, check=True)
                version_line = process.stdout.splitlines()[0] if process.stdout else "未知版本"
                log.write_line(f"检测到 FFmpeg: {version_line}")
            except Exception as e:
                log.write_line(f"FFmpeg 版本获取失败: {e}")
        else:
            log.write_line("警告: 未检测到 FFmpeg，转换功能将无法使用")

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """当在目录树中选择文件时触发"""
        # 获取选中文件的完整路径
        file_path = event.path.resolve().as_posix()
        self.source_file_path = file_path
        
        # 更新源文件路径输入框
        self.query_one("#source-path", Input).value = file_path
        
        # 解析文件名作为默认的输出文件名
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        suggested_name = f"{base_name}_converted"
        self.query_one("#output-name", Input).value = suggested_name
        
        # 记录日志
        self.query_one("#log", Log).write_line(f"已选择文件: {file_path}")

    def on_select_changed(self, event: Select.Changed) -> None:
        """当选择框内容改变时触发"""
        # 如果是输出格式选择框发生变化
        if event.select.id == "output-format":
            # 更新自定义格式输入框
            self.query_one("#custom-format", Input).value = event.select.value

    async def action_start_conversion(self) -> None:
        """响应C键按下，开始转换操作"""
        log = self.query_one("#log", Log)
        convert_button = self.query_one("#convert-button", Button)
        
        # 检查按钮是否可用（不在转换过程中）
        if not convert_button.disabled:
            # 获取参数
            source_path = self.query_one("#source-path", Input).value
            output_name = self.query_one("#output-name", Input).value
            custom_format = self.query_one("#custom-format", Input).value
            no_reencoding = self.query_one("#no-reencoding", Select).value == "yes"
            video_encoder = self.query_one("#video-encoder", Select).value
            encoder_preset = self.query_one("#encoder-preset", Select).value
            hw_decoder = self.query_one("#hw-decoder", Select).value
            
            # 获取高级参数
            remove_audio = self.query_one("#remove-audio", Select).value == "yes"
            remove_video = self.query_one("#remove-video", Select).value == "yes"
            start_time = self.query_one("#start-time", Input).value
            duration = self.query_one("#duration", Input).value
            frame_rate = self.query_one("#frame-rate", Input).value
            frame_size = self.query_one("#frame-size", Input).value
            aspect_ratio = self.query_one("#aspect-ratio", Select).value
            
            # 验证输入
            if not source_path:
                log.write_line("错误: 请输入源文件路径")
                return
            
            if not output_name:
                log.write_line("错误: 请输入输出文件名")
                return
            
            # 检查源文件是否存在
            if not os.path.isfile(source_path):
                log.write_line(f"错误: 源文件 '{source_path}' 不存在")
                return
            
            # 构建输出路径（与源文件同目录）
            source_dir = os.path.dirname(source_path)
            output_path = os.path.join(source_dir, f"{output_name}.{custom_format}")
            
            # 显示转换信息
            log.write_line("准备转换:")
            log.write_line(f"  源文件: {source_path}")
            log.write_line(f"  输出到: {output_path}")
            log.write_line(f"  输出格式: {custom_format}")
            log.write_line(f"  跳过重新编码: {no_reencoding}")
            if not no_reencoding:
                log.write_line(f"  编码器: {video_encoder}")
                log.write_line(f"  预设: {encoder_preset}")
                if hw_decoder:
                    log.write_line(f"  硬件加速解码: {hw_decoder}")
            
            # 显示高级参数信息
            if remove_audio:
                log.write_line("  去除音频: 是")
            if remove_video:
                log.write_line("  去除视频: 是")
            if start_time:
                log.write_line(f"  起始时间: {start_time}秒")
            if duration:
                log.write_line(f"  持续时长: {duration}秒")
            if frame_rate:
                log.write_line(f"  帧率: {frame_rate}")
            if frame_size:
                log.write_line(f"  帧大小: {frame_size}")
            if aspect_ratio:
                log.write_line(f"  横纵比: {aspect_ratio}")
            
            # 禁用按钮，表示正在进行转换
            convert_button.disabled = True
            convert_button.label = "转换中..."
            
            # 启动转换任务
            async def run_and_reset():
                try:
                    await self.convert_file(source_path, output_path, log, no_reencoding, video_encoder, encoder_preset)
                finally:
                    # 无论成功或失败都重置按钮状态
                    convert_button.disabled = False
                    convert_button.label = "开始转换"
            
            # 使用单独的任务运行转换
            asyncio.create_task(run_and_reset())
            log.write_line("通过快捷键[C]开始转换操作")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击事件"""
        log = self.query_one("#log", Log)
        
        if event.button.id == "convert-button":
            # 调用与快捷键相同的转换函数
            self.action_start_conversion()
            
        elif event.button.id == "quit-button":
            # 退出程序
            self.exit()

    async def convert_file(self, source, target, log, no_reencoding, video_encoder, encoder_preset):
        """执行文件转换"""
        # 获取硬件加速解码器选项
        hw_decoder = self.query_one("#hw-decoder", Select).value
        
        # 获取高级参数
        remove_audio = self.query_one("#remove-audio", Select).value == "yes"
        remove_video = self.query_one("#remove-video", Select).value == "yes"
        start_time = self.query_one("#start-time", Input).value
        duration = self.query_one("#duration", Input).value
        frame_rate = self.query_one("#frame-rate", Input).value
        frame_size = self.query_one("#frame-size", Input).value
        aspect_ratio = self.query_one("#aspect-ratio", Select).value
        
        # 构建ffmpeg命令
        command = [FFMPEG_PATH]
        
        # 添加硬件加速解码参数
        if hw_decoder:
            command.extend(["-hwaccel", hw_decoder])
            # 对于特定的解码器添加额外参数
            if hw_decoder == "cuda -hwaccel_output_format cuda":
                # 处理特殊情况，拆分参数
                command = [FFMPEG_PATH, "-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]
        
        # 添加起始时间参数（放在输入文件之前）
        if start_time:
            command.extend(["-ss", start_time])
        
        command.extend(["-i", source])
        
        # 添加持续时长参数
        if duration:
            command.extend(["-t", duration])
        
        # 添加去除音频/视频参数
        if remove_audio:
            command.append("-an")
        if remove_video:
            command.append("-vn")
        
        # 添加帧率参数
        if frame_rate:
            command.extend(["-r", frame_rate])
        
        # 添加帧大小参数
        if frame_size:
            command.extend(["-s", frame_size])
        
        # 添加横纵比参数
        if aspect_ratio:
            command.extend(["-aspect", aspect_ratio])
        
        # 根据选项决定是否重新编码
        if no_reencoding:
            # 不重新编码，直接复制视频和音频流
            command.extend(["-c:v", "copy", "-c:a", "copy"])
            log.write_line("使用直接复制模式，不重新编码")
        else:
            # 使用选定的编码器和预设
            command.extend(["-c:v", video_encoder])
            
            # 对于copy编码器，不使用预设参数
            if video_encoder != "copy":
                command.extend(["-preset", encoder_preset])
                
                # 为H.265添加特定参数
                if video_encoder == "libx265":
                    command.extend(["-crf", "28"]) # H.265的CRF值通常比H.264高一些
                elif video_encoder == "libx264":
                    command.extend(["-crf", "23"]) # H.264的默认CRF值
                
            # 设置音频编码（可以根据需要调整）
            command.extend(["-c:a", "aac", "-b:a", "128k"])
            
            log.write_line(f"使用编码器: {video_encoder}, 预设: {encoder_preset}")
        
        # 输出文件
        command.extend(["-y", target])
        
        log.write_line(f"执行命令: {' '.join(command)}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 读取输出流
            async def read_stream(stream, prefix=""):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    text = line.decode('utf-8', errors='replace').rstrip()
                    # 在异步上下文中直接调用
                    log.write_line(f"{prefix}{text}")
            
            await asyncio.gather(
                read_stream(process.stdout, "[OUT] "),
                read_stream(process.stderr, "[LOG] ")
            )
            
            return_code = await process.wait()
            
            if return_code == 0:
                log.write_line("转换成功!")
                log.write_line(f"输出文件: {target}")
            else:
                log.write_line(f"转换失败! 返回代码: {return_code}")
                
        except Exception as e:
            log.write_line(f"错误: {e}")


if __name__ == "__main__":
    # 检查命令行参数
    for i, arg in enumerate(sys.argv):
        if arg == "--help" or arg == "-h":
            print("FFmpeg 转换器 TUI")
            print("用法:")
            print(f"  {sys.argv[0]} [选项]")
            print("选项:")
            print("  --ffmpeg-path PATH    指定 ffmpeg 可执行文件的路径")
            print("  --help, -h            显示帮助信息")
            sys.exit(0)
    
    # 检查 ffmpeg
    check_ffmpeg()
    
    app = SimplifiedFFmpegApp()
    app.run() 