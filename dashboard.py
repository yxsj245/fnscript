#!/usr/bin/env python
from textual.app import App, ComposeResult
from textual.widgets import (
    Header, Footer, Static, Button, 
    DataTable, Input, Label
)
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
import psutil
from time import time
import asyncio

# 自定义ASCII图表组件
class AsciiChart(Static):
    """用字符块绘制的动态图表"""
    data = reactive([])
    
    def watch_data(self, new_data: list) -> None:
        max_val = max(new_data) if new_data else 1
        chart = "\n".join(
            "".join("█" if val >= max_val * (1 - i/10) else " " 
                   for val in new_data[-30:])
            for i in range(10)
        )
        self.update(f"[chart]\n{chart}[/]")

# 主应用
class SystemDashboard(App):
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 2;
        grid-columns: 2fr 1fr;
        padding: 1;
    }
    #cpu-chart {
        height: 10;
        border: round $accent;
        padding: 1;
    }
    #mem-chart {
        height: 6;
        border: round $accent;
    }
    DataTable {
        height: 10;
    }
    Button {
        width: 16;
    }
    .highlight {
        text-style: bold;
        background: $surface;
    }
    Label {
        text-style: bold;
        margin: 1 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "退出"),
        ("r", "refresh", "手动刷新"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()
        
        with Container(id="left-panel"):
            yield Label("📊 实时资源监控 (每2秒自动刷新)")
            yield AsciiChart(id="cpu-chart")
            yield AsciiChart(id="mem-chart")
            with Horizontal():
                yield Button("暂停刷新", id="pause")
                yield Button("导出数据", id="export")
        
        with Vertical(id="right-panel"):
            yield Label("🔥 进程占用TOP5")
            yield DataTable(id="process-table")
            with Horizontal():
                yield Input(placeholder="过滤进程...", id="filter")
                yield Button("搜索", id="search")

    async def on_mount(self) -> None:
        # 初始化表格
        table = self.query_one("#process-table", DataTable)
        table.add_columns("PID", "名称", "CPU%", "内存%")
        
        # 启动数据更新任务
        asyncio.create_task(self.update_data())

    async def update_data(self) -> None:
        """实时更新数据"""
        while True:
            # CPU使用率图表
            cpu_data = [p / 10 for p in psutil.cpu_percent(percpu=True)]
            self.query_one("#cpu-chart").data = cpu_data
            
            # 内存使用图表
            mem = psutil.virtual_memory()
            self.query_one("#mem-chart").data = [mem.percent]
            
            # 进程表格
            table = self.query_one("#process-table")
            table.clear()
            for p in sorted(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']), 
                          key=lambda p: p.info['cpu_percent'] or 0, reverse=True)[:5]:
                table.add_row(
                    str(p.info['pid']),
                    p.info['name'],
                    f"{p.info['cpu_percent']:.1f}%",
                    f"{p.info['memory_percent']:.1f}%"
                )
            
            await asyncio.sleep(2)  # 刷新间隔

    def action_refresh(self) -> None:
        """手动刷新数据"""
        asyncio.create_task(self.update_data())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "pause":
            self.query_one("#pause").label = (
                "继续刷新" if "▶" in self.query_one("#pause").label 
                else "⏸ 暂停刷新"
            )
            # 切换自动刷新状态
            self.set_interval(2, self.update_data, pause=True)

if __name__ == "__main__":
    app = SystemDashboard()
    app.run()