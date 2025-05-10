#!/usr/bin/env python
from textual.app import App, ComposeResult
from textual.widgets import (
    Header, Footer, Static, Button, 
    Label, Input, DataTable, DirectoryTree
)
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer, VerticalScroll
from textual.screen import Screen, ModalScreen
import os
import asyncio
from operator import itemgetter
import pathlib
from collections import defaultdict
from typing import Dict, List, Tuple
from textual.binding import Binding

def get_current_level_analysis(base_path: str) -> Tuple[int, List[Tuple[str, int]], List[Tuple[str, int]]]:
    direct_files: List[Tuple[str, int]] = []
    direct_subdirs_info: List[Tuple[str, int]] = []
    grand_total_size: int = 0

    try:
        for entry in os.scandir(base_path):
            entry_path = entry.path # Define here for broader scope in except block
            try:
                if entry.is_file(follow_symlinks=False):
                    try:
                        size = entry.stat(follow_symlinks=False).st_size
                        direct_files.append((entry.name, size))
                        grand_total_size += size
                    except (PermissionError, OSError) as e_stat_file:
                        direct_files.append((entry.name, -1))
                elif entry.is_dir(follow_symlinks=False):
                    subdir_total_size = 0
                    try:
                        # onerror to handle errors during os.walk, e.g. permission denied on a sub-directory
                        # Corrected the lambda for onerror f-string compatibility
                        for dirpath_walk, _, filenames_walk in os.walk(entry_path, followlinks=True, onerror=lambda e: None):
                            for f_name_walk in filenames_walk:
                                f_path_walk = os.path.join(dirpath_walk, f_name_walk)
                                try:
                                    file_size_walk = os.path.getsize(f_path_walk)
                                    subdir_total_size += file_size_walk
                                except (PermissionError, FileNotFoundError, OSError):
                                    pass # Skip files in subdir that can't be accessed
                        direct_subdirs_info.append((entry.name, subdir_total_size))
                        grand_total_size += subdir_total_size
                    except (PermissionError, OSError) as e_walk_top:
                        direct_subdirs_info.append((entry.name, -1))
            except (PermissionError, OSError) as e_type_check:
                # Fallback for entries that error on is_file/is_dir or initial stat
                try:
                    if os.path.exists(entry_path): # Check existence before trying to determine type
                        if os.path.isfile(entry_path):
                            direct_files.append((entry.name, -2))
                        elif os.path.isdir(entry_path):
                            direct_subdirs_info.append((entry.name, -2))
                        else:
                            direct_files.append((entry.name, -2)) # Default if type is still unknown
                    else:
                        pass # Skip this entry entirely if its basic properties can't be read even in fallback
                except OSError:
                    pass # Skip this entry entirely if its basic properties can't be read even in fallback

    except (PermissionError, OSError) as e_scan_base:
        raise e_scan_base # Re-raise to be handled by the calling screen

    direct_files.sort(key=itemgetter(1), reverse=True)
    direct_subdirs_info.sort(key=itemgetter(1), reverse=True)
    return grand_total_size, direct_files, direct_subdirs_info

def format_size(size_in_bytes):
    """将字节数转换为可读格式"""
    if size_in_bytes == -1:
        return "[red]无权限[/red]"
    if size_in_bytes == -2:
        return "[yellow]错误/未知[/yellow]" # Added for entries that errored during stat/type check
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.2f} TB" # 处理非常大的情况

def get_root_directory():
    """获取系统根目录"""
    if os.name == 'nt':  # Windows
        return 'C:\\\\' # pathlib.Path('C:/')
    else:  # Linux/Unix/Mac
        return '/' # pathlib.Path('/')

# 错误对话框
class ErrorDialog(ModalScreen):
    """错误提示对话框"""
    
    def __init__(self, message: str):
        super().__init__()
        self.message = message
    
    def compose(self) -> ComposeResult:
        with Container(id="dialog-container"):
            yield Label(f"[red]{self.message}[/red]", id="dialog-title")
            with Horizontal(id="dialog-buttons"):
                yield Button("确定", id="ok", variant="primary")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self.dismiss()

# 目录选择屏幕
class DirectoryBrowserScreen(Screen):
    """目录浏览选择屏幕"""
    
    BINDINGS = [
        Binding("escape", "app.pop_screen", "返回", show=True),
        Binding("backspace", "go_parent", "上级目录", show=True),
        Binding("/", "go_root", "根目录", show=True)
    ]
    
    def __init__(self, callback, current_path="."):
        super().__init__()
        self.current_path = os.path.abspath(current_path)
        self.callback = callback
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()
        
        with Container(id="browser-container"):
            yield Label("[b]请选择目录[/b]", id="browser-title")
            yield Label(f"当前路径: [blue]{self.current_path}[/blue]", id="current-path-display") # Renamed ID
            
            with Horizontal(id="nav-buttons"):
                yield Button("根目录", id="root-dir", variant="primary")
                yield Button("上级目录", id="parent-dir", variant="warning")
            
            yield Label("操作指南: Backspace=上级目录, /=根目录, Escape=返回", id="browser-help")
            
            with ScrollableContainer(id="tree-container"):
                yield DirectoryTree(self.current_path, id="directory-browser")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "parent-dir":
            self.action_go_parent()
        elif event.button.id == "root-dir":
            self.action_go_root()
    
    def action_go_parent(self) -> None:
        parent_dir = os.path.dirname(self.current_path)
        if parent_dir and parent_dir != self.current_path:
            self.refresh_directory_tree(parent_dir)
    
    def action_go_root(self) -> None:
        root_dir = get_root_directory()
        self.refresh_directory_tree(root_dir)
    
    def refresh_directory_tree(self, new_path):
        if not os.path.isdir(new_path):
            self.app.push_screen(ErrorDialog(f"无效路径: {new_path}"))
            return
        
        try:
            self.current_path = new_path
            self.query_one("#current-path-display").update(f"当前路径: [blue]{self.current_path}[/blue]") # Updated ID
            
            tree_container = self.query_one("#tree-container")
            tree_container.remove_children()
            tree_container.mount(DirectoryTree(new_path, id="directory-browser"))
        except Exception as e:
            self.app.push_screen(ErrorDialog(f"无法导航到目录: {str(e)}"))
    
    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected): # Corrected event type
        selected_path = str(event.path)
        self.callback(selected_path)
        self.app.pop_screen()

# 文件分析结果屏幕
class FileAnalysisResultScreen(Screen):
    BINDINGS = [
        Binding("escape", "custom_pop_screen", "返回上层/主界面", show=True, priority=True),
        Binding("u", "go_up", "上级目录 (分析内)", show=True),
    ]

    NUM_BUTTONS_PER_ROW = 2 # Define how many buttons per horizontal row

    def __init__(self, initial_folder_path: str, app_status_callback):
        super().__init__()
        self.initial_folder_path = os.path.abspath(initial_folder_path)
        self.current_analyzed_path = self.initial_folder_path
        self.path_history: List[str] = [self.initial_folder_path]
        self.app_status_callback = app_status_callback

        self.current_path_label: Label | None = None
        self.total_size_label: Label | None = None
        self.files_table: DataTable | None = None
        self.subdirs_container: ScrollableContainer | None = None # This will hold Horizontal rows
        self.go_up_button: Button | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Vertical(id="result-top-bar"):
            self.current_path_label = Label(f"当前分析路径: {self.current_analyzed_path}", id="current-analyzed-path-label")
            yield self.current_path_label
            self.total_size_label = Label("总大小: N/A", id="current-total-size-label")
            yield self.total_size_label
            self.go_up_button = Button("返回上级 (U)", id="go-up-button", variant="default")
            yield self.go_up_button
        
        yield Label("[b]当前目录文件:[/b]", classes="section-title")
        with ScrollableContainer(id="files-in-current-dir-container", classes="data-container"):
            self.files_table = DataTable(id="files-in-current-dir-table")
            self.files_table.add_columns("文件名", "大小")
            yield self.files_table
            
        yield Label("[b]子目录:[/b]", classes="section-title")
        # ScrollableContainer will now contain multiple Horizontal widgets, each acting as a row.
        self.subdirs_container = ScrollableContainer(id="subdirs-list-container", classes="data-container")
        yield self.subdirs_container # Children (Horizontal rows) will be added in _load_and_display_path_data
        
        yield Footer()

    async def on_mount(self) -> None:
        """加载初始路径的数据。"""
        await self._load_and_display_path_data(self.initial_folder_path)
        self._update_go_up_button_state()

    def _update_go_up_button_state(self):
        """根据历史记录启用/禁用"返回上级"按钮。"""
        if self.go_up_button:
            self.go_up_button.disabled = len(self.path_history) <= 1

    async def _load_and_display_path_data(self, path_to_analyze: str):
        self.current_analyzed_path = os.path.abspath(path_to_analyze)
        
        # Update the path label here
        if self.current_path_label:
            self.current_path_label.update(f"当前分析路径: {self.current_analyzed_path}")
            self.current_path_label.refresh()

        self.app_status_callback(f"分析中: {self.current_analyzed_path}...")
        self.query(".subdir-button").remove() # Clear previous buttons
        
        if self.total_size_label:
            self.total_size_label.update("总大小: 计算中...")

        if self.files_table:
            self.files_table.clear()
        
        # Clear previous Horizontal rows from the subdirs_container
        if self.subdirs_container:
            await self.subdirs_container.remove_children()

        try:
            grand_total_size, direct_files, direct_subdirs = await asyncio.to_thread(
                get_current_level_analysis, self.current_analyzed_path
            )

            if self.total_size_label:
                self.total_size_label.update(f"总大小: {format_size(grand_total_size)}")

            if self.files_table:
                if not direct_files:
                    self.files_table.add_row(Static("此目录中没有文件。"))
                else:
                    for file_name, file_size in direct_files:
                        self.files_table.add_row(file_name, format_size(file_size))
            
            if self.subdirs_container: # Check if container exists
                if not direct_subdirs:
                    # If no subdirs, we might want to mount a message directly to subdirs_container
                    await self.subdirs_container.mount(Static("  没有子目录或无法访问。"))
                else:
                    current_row_horizontal: Horizontal | None = None
                    buttons_in_current_row = 0

                    for i, (subdir_name, subdir_size) in enumerate(direct_subdirs):
                        # Create a new Horizontal row if needed
                        if buttons_in_current_row == 0 or not current_row_horizontal:
                            current_row_horizontal = Horizontal(classes="subdir-row")
                            await self.subdirs_container.mount(current_row_horizontal)
                            buttons_in_current_row = 0 # Reset for the new row
                        
                        button_label = f"{subdir_name} ({format_size(subdir_size)})"
                        safe_id_name = "".join(c if c.isalnum() else "_" for c in subdir_name)
                        subdir_button = Button(
                            button_label,
                            id=f"subdir_{safe_id_name}_{abs(hash(subdir_name))}", 
                            variant="primary", 
                            classes="subdir-button"
                        )
                        subdir_button.full_path = os.path.join(self.current_analyzed_path, subdir_name)
                        
                        try:
                            if current_row_horizontal:
                                await current_row_horizontal.mount(subdir_button)
                                buttons_in_current_row += 1
                        except Exception as e_mount:
                            # Optionally, inform the user about this specific button mount error
                            self.app_status_callback(f"[yellow]挂载按钮 '{subdir_name}' 出错[/yellow]")

                        # If row is full, reset for next iteration to create a new row
                        if buttons_in_current_row >= self.NUM_BUTTONS_PER_ROW:
                            buttons_in_current_row = 0
                            current_row_horizontal = None # Signal to create a new row next time
            
            self.app_status_callback(f"[green]分析完成: {self.current_analyzed_path}[/green]")

        except Exception as e:
            error_message = f"分析 {self.current_analyzed_path} 出错: {str(e)}"
            self.app_status_callback(f"[red]{error_message}[/red]")
            if self.total_size_label:
                self.total_size_label.update("总大小: [red]错误[/red]")
            # If error, we might still want to mount the error to subdirs_container
            if self.subdirs_container:
                 await self.subdirs_container.mount(Static(f"[red]分析时发生错误: {str(e)}[/red]"))

        self._update_go_up_button_state()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "go-up-button":
            await self.action_go_up()
        elif hasattr(event.button, 'full_path'): 
            clicked_subdir_path = event.button.full_path
            if not os.path.isdir(clicked_subdir_path):
                self.app.push_screen(ErrorDialog(f"无法访问目录: {clicked_subdir_path}"))
                return

            if self.path_history[-1] != clicked_subdir_path:
                 self.path_history.append(clicked_subdir_path)
            await self._load_and_display_path_data(clicked_subdir_path)

    async def action_go_up(self) -> None:
        """在分析历史记录中导航到父目录。"""
        if len(self.path_history) > 1:
            self.path_history.pop() 
            parent_path = self.path_history[-1] 
            await self._load_and_display_path_data(parent_path)
        self._update_go_up_button_state()

    async def action_custom_pop_screen(self) -> None: 
        """自定义弹出屏幕以处理历史记录或退出。"""
        if len(self.path_history) > 1:
            await self.action_go_up()
        else:
            self.app.pop_screen()

# 文件分析应用
class FileStorageAnalyzerApp(App):
    """文件分析应用"""
    
    CSS = """
    /* CSS - Main changes will be to .subdir-row and .subdir-button */

    Screen {
        background: $surface;
    }

    #title, #browser-title {
        dock: top;
        width: 100%;
        text-align: center;
        text-style: bold;
        background: $accent;
        color: $text;
        padding: 1;
        margin-bottom: 1;
    }

    #browser-help, #nav-label {
        text-align: center;
        color: $text-muted;
        margin: 1 0;
    }

    #current-path-display {
        text-align: center;
        margin-bottom: 1;
        background: $primary-darken-2;
        padding: 1;
    }

    #nav-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 1 0;
    }

    #nav-buttons Button {
        min-width: 10;
        margin: 0 1;
        padding: 0 1;
    }

    #tree-container {
        width: 100%;
        height: 25;
        border: solid $accent;
        margin: 1 0;
    }

    #main-container, #browser-container, #result-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }

    #input-area {
        width: 100%;
        height: auto;
        margin: 1;
        padding: 1;
        border: round $primary;
    }

    #path-input-label {
        margin-bottom: 1;
    }

    #path-input-field {
        width: 100%;
        margin-bottom: 1;
    }

    #action-buttons {
        width: 100%;
        margin: 1 0;
        align: center middle;
    }

    #action-buttons Button {
        margin: 0 1;
    }

    #status-display {
        height: auto;
        min-height: 3;
        width: 100%;
        margin: 1;
        padding: 1;
        border: solid $accent;
        background: $surface-darken-1;
        text-align: center;
    }

    #directory-browser {
        width: 100%;
        min-height: 20;
    }

    #dialog-container {
        width: 60%;
        height: auto;
        padding: 2;
        background: $surface;
        border: thick $error;
        margin: 1 0;
        align: center middle;
    }

    #dialog-title {
        text-align: center;
        width: 100%;
        margin-bottom: 2;
    }

    #dialog-buttons {
        align: center middle;
        width: 100%;
    }

    /* Styles for FileAnalysisResultScreen */
    #result-top-bar {
        width: 100%;
        padding: 1;
        background: $primary-background;
        border: round $primary;
        margin-bottom:1;
        height: 7; /* 设置一个合适的高度，足够显示所有内容 */
    }

    #current-analyzed-path-label {
        width: 100%;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #current-total-size-label {
        width: 100%;
        text-align: center;
        color: $secondary;
         margin-bottom: 1;
    }

    #go-up-button {
        width: 100%;
        margin-top: 1;
    }

    .section-title {
        width: 100%;
        padding: 1;
        background: $secondary-background;
        text-style: bold;
        text-align: center;
        margin-top: 1;
    }

    .data-container {
        width: 100%;
        border: round $primary;
        margin-top: 1;
    }
    
    #files-in-current-dir-container {
        height: 10;
    }

    #files-in-current-dir-table {
        width: 100%;
    }

    #subdirs-list-container {
        height: 20; /* Height for the scrollable area of rows */
    }

    /* Styles for the new Horizontal rows and buttons within them */
    .subdir-row {
        width: 100%;
        height: auto; /* Row height will be determined by button height + padding/margin */
        align: left middle; /* Corrected: Horizontal align left, Vertical align middle */
        /* Optionally, add some vertical margin between rows if Horizontal doesn't have it */
        margin-bottom: 1;
    }

    .subdir-row .subdir-button {
        width: 1fr; /* Distribute space equally among buttons in a row */
        height: 3;
        margin-right: 1; /* Space between buttons in a row */
        /* To ensure the last button in a row doesn't have extra margin: */
        /* &:last-child { margin-right: 0; } */ /* This is advanced CSS, might not work in Textual basic CSS */
        
        border: round $secondary; 
        background: $secondary-background; 
        text-align: center; 
    }
    """

    BINDINGS = [
        Binding("q", "quit", "退出", show=True),
        Binding("escape", "handle_escape", "退出/返回", show=True)
    ]
    
    def __init__(self):
        super().__init__()
        self.path_input: Input | None = None
        self.status_label: Static | None = None 

    def compose(self) -> ComposeResult:
        """创建应用界面"""
        yield Header(show_clock=True)
        yield Footer()
        
        with Container(id="main-container"):
            yield Label("[b]文件夹分析工具[/b]", id="title")
            
            with Vertical(id="input-area"):
                yield Label("请输入要分析的目录路径:", id="path-input-label") 
                self.path_input = Input(placeholder="例如: /home/user/documents", id="path-input-field") 
                yield self.path_input
                
                with Horizontal(id="action-buttons"):
                    yield Button("分析", id="analyze", variant="primary")
                    yield Button("浏览...", id="browse", variant="default")
            
            self.status_label = Static("请输入目录路径并点击分析按钮。", id="status-display") 
            yield self.status_label
    
    def on_mount(self):
        """应用加载完成后执行"""
        # self.path_input 和 self.status_label 已在 compose 中赋值
        if self.path_input: # 设置初始焦点
             self.path_input.focus()

    def update_status(self, message: str):
        """回调函数，用于从其他屏幕更新状态标签。"""
        if self.status_label:
            self.status_label.update(message)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击事件"""
        if event.button.id == "analyze":
            await self.action_analyze_directory() 
        elif event.button.id == "browse":
            self.action_browse_directory() 
    
    def action_browse_directory(self):
        self.update_status("[blue]正在浏览目录...[/blue]")
        current_path = "."
        if self.path_input and self.path_input.value and os.path.isdir(self.path_input.value):
            current_path = self.path_input.value
        self.push_screen(DirectoryBrowserScreen(self.on_directory_selected, current_path))

    def on_directory_selected(self, selected_path: str):
        """处理目录选择的回调函数"""
        if self.path_input:
            self.path_input.value = selected_path
        self.update_status(f"[green]已选择目录: {selected_path}[/green]")
    
    async def action_analyze_directory(self): 
        if not self.path_input: return

        directory = self.path_input.value.strip()
        
        if not directory:
            self.push_screen(ErrorDialog("请输入有效的目录路径！"))
            return
        
        if not os.path.isdir(directory):
            self.push_screen(ErrorDialog(f"\'{directory}\' 不是有效目录。"))
            return
        
        analyze_button = self.query_one("#analyze", Button)
        analyze_button.disabled = True
        
        try:
            self.push_screen(FileAnalysisResultScreen(directory, self.update_status))
        except Exception as e:
            self.update_status(f"[red]启动分析界面时出错: {str(e)}[/red]")
        finally:
            analyze_button.disabled = False

    def action_handle_escape(self):
        """处理全局Escape键。"""
        # This action is now less likely to conflict with screen-specific Escape
        # because the app's Escape binding no longer has priority=True.
        if len(self.screen_stack) == 1: # 主屏幕
            self.exit() # Corrected from self.app.quit()
        else:
            # If a screen is active, its own Escape binding (if any) should have taken precedence.
            # If it didn't (e.g., no Escape binding on the active screen),
            # Textual's default behavior is to pop the screen. This app-level handler
            # might be called after a screen pop or if the screen didn't handle Escape.
            pass


if __name__ == "__main__":
    app = FileStorageAnalyzerApp()
    app.run() 