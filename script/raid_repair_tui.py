#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button, ListView, ListItem, Label, Checkbox
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual import events
import asyncio
import subprocess
import re
import os
from textual.message import Message
from textual.widgets import Input
from textual.screen import Screen

# 复用原有检测和信息获取逻辑

def run_command(command):
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        return stdout.strip(), stderr.strip()
    except Exception as e:
        return None, str(e)

def get_mdadm_arrays():
    stdout, _ = run_command("ls -1 /dev/md[0-9]* 2>/dev/null")
    md_devices = []
    if stdout:
        for device in stdout.splitlines():
            device = device.strip()
            if device and device.startswith('/dev/md'):
                check_cmd = f"test -b {device} > /dev/null 2>&1 && echo exists || true"
                check_stdout, _ = run_command(check_cmd)
                if check_stdout and "exists" in check_stdout:
                    md_devices.append(device)
    return md_devices

def parse_status(status_raw):
    if not status_raw:
        return "未知", False, False
    status_line = status_raw.splitlines()[0] if isinstance(status_raw, str) else status_raw
    status_list = [s.strip().lower() for s in re.split(r'[ ,]+', status_line) if s.strip()]
    mapping = {
        "active": "活跃",
        "clean": "空闲",
        "degraded": "降级",
        "failed": "失败",
        "not started": "未启用",
    }
    # 只有单一clean或active，视为正常
    if len(status_list) == 1 and status_list[0] in ("clean", "active"):
        return "正常", False, False
    zh_status = []
    abnormal = False
    degraded = False
    for s in status_list:
        zh = mapping.get(s, s)
        zh_status.append(zh)
        if s == "failed":
            abnormal = True
        if s == "degraded":
            degraded = True
    # 只有failed才允许修复
    return ", ".join(zh_status), abnormal, degraded

def get_array_details(array_device):
    stdout, _ = run_command(f"mdadm --detail {array_device}")
    if not stdout:
        return None
    status = "unknown"
    raid_level = "unknown"
    uuid = "unknown"
    device_info_text = ""
    status_match = re.search(r"State\s*:\s*([\w\s,]+)", stdout)
    if status_match:
        status = status_match.group(1).strip()
    raid_level_match = re.search(r"Raid Level\s*:\s*(\w+)", stdout)
    if raid_level_match:
        raid_level = raid_level_match.group(1)
    uuid_match = re.search(r"UUID\s*:\s*([\w:]+)", stdout)
    if uuid_match:
        uuid = uuid_match.group(1).strip()
    device_section_started = False
    for line in stdout.splitlines():
        if "Number   Major   Minor   RaidDevice State" in line:
            device_section_started = True
            device_info_text = line + "\n"
            continue
        if device_section_started:
            if line.strip() == "" or "Events" in line:
                device_section_started = False
                break
            device_info_text += line + "\n"
    # 新增：解析状态
    zh_status, abnormal, degraded = parse_status(status)
    return {
        "status": status,
        "zh_status": zh_status,
        "abnormal": abnormal,
        "degraded": degraded,
        "raid_level": raid_level,
        "uuid": uuid,
        "device_info": device_info_text,
        "raw": stdout
    }

def get_available_block_devices():
    stdout, _ = run_command("lsblk -dpno NAME,TYPE | grep 'part\|disk'")
    devices = []
    if stdout:
        for line in stdout.splitlines():
            parts = line.strip().split()
            if len(parts) == 2 and (parts[1] == "disk" or parts[1] == "part"):
                devices.append(parts[0])
    return devices

def fix_disk_name(disk):
    # /dev/sda -> /dev/sda1
    if re.match(r"^/dev/sd[a-zA-Z]$", disk):
        return disk + "1"
    return disk

class MessageScreen(Screen):
    def __init__(self, msg, title="提示"):
        super().__init__()
        self.msg = msg
        self.title = title
    def compose(self) -> ComposeResult:
        yield Static(f"{self.title}", id="msg-title")
        yield Static(self.msg, id="msg-content")
        yield Button("确定", id="msg-ok")
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "msg-ok":
            self.app.pop_screen()

class RepairScreen(Screen):
    def __init__(self, array_device, array_details, on_confirm):
        super().__init__()
        self.array_device = array_device
        self.array_details = array_details
        self.on_confirm = on_confirm
        self.checkboxes = []
    def compose(self) -> ComposeResult:
        yield Static("请您根据您的阵列等级，raid1至少需要一个硬盘 raid5至少需要原磁盘数量总数-1个 raid6至少需要原磁盘数量总数-2个", id="raid-level-tip")
        yield Static(f"修复阵列 {self.array_device}", id="repair-title")
        yield Static(f"原阵列硬盘信息:\n{self.array_details['device_info']}", id="repair-old-info")
        yield Static("请选择用于修复的磁盘：", id="repair-disk-title")
        self.checkboxes = []
        available = get_available_block_devices()
        for dev in available:
            cb = Checkbox(dev)
            self.checkboxes.append(cb)
            yield cb
        yield Button("确认修复", id="repair-confirm")
        yield Button("取消", id="repair-cancel")
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "repair-cancel":
            self.app.pop_screen()
        elif event.button.id == "repair-confirm":
            selected = [cb.label.plain if hasattr(cb.label, 'plain') else str(cb.label) for cb in self.checkboxes if cb.value]
            # 自动将sda等整盘转为sda1
            selected = [fix_disk_name(d) for d in selected]
            # 检查所有选中硬盘的Array UUID是否一致
            if not selected:
                self.app.push_screen(MessageScreen("未选择任何磁盘，修复已取消。"))
                self.app.pop_screen()
                return
            uuids = []
            uuid_disk_map = {}
            for disk in selected:
                stdout, _ = run_command(f"mdadm --examine {disk}")
                uuid_match = re.search(r'Array UUID\s*:\s*([\w:-]+)', stdout or "")
                uuid = uuid_match.group(1) if uuid_match else None
                uuids.append(uuid)
                uuid_disk_map[disk] = uuid
            if len(set(uuids)) > 1:
                # 找出不同的uuid及其对应磁盘
                uuid_info = "\n".join([f"{d}: {u}" for d, u in uuid_disk_map.items()])
                self.app.push_screen(MessageScreen(f"你选中的硬盘阵列UUID不一致，请确认选中的硬盘为同一阵列下：\n{uuid_info}"))
                return
            disks_str = " ".join(selected)
            # 先停止阵列
            stop_cmd = f"mdadm --stop {self.array_device}"
            stop_out, stop_err = run_command(stop_cmd)
            # 再组装阵列
            assemble_cmd = f"mdadm --assemble --force --run {self.array_device} {disks_str}"
            assemble_out, assemble_err = run_command(assemble_cmd)
            msg = f"执行停止命令：\n{stop_cmd}\n"
            if stop_out:
                msg += f"\n停止输出：\n{stop_out}"
            if stop_err:
                msg += f"\n停止警告/错误：\n{stop_err}"
            msg += f"\n\n执行修复命令：\n{assemble_cmd}\n"
            if assemble_out:
                msg += f"\n修复输出：\n{assemble_out}"
            if assemble_err:
                msg += f"\n修复警告/错误：\n{assemble_err}"
            msg += "\n\n阵列已尝试重组完毕，您可以重新回到飞牛磁盘界面刷新网页点击挂载即可"
            self.app.push_screen(MessageScreen(msg))

class RaidList(ListView):
    pass

class RaidRepairApp(App):
    CSS_PATH = None
    BINDINGS = [
        ("q", "quit", "退出"),
        ("r", "refresh", "刷新"),
    ]

    raid_arrays = reactive([])
    selected_index = reactive(0)
    details = reactive({})
    failed_status = reactive(False)
    degraded_status = reactive(False)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical():
                yield Static("RAID阵列列表", id="raid-list-title")
                self.raid_list = RaidList(id="raid-list")
                yield self.raid_list
            with Vertical():
                yield Static("阵列详细信息", id="raid-detail-title")
                self.detail_label = Label("", id="raid-detail")
                yield self.detail_label
        self.repair_button = Button("修复", id="repair-btn", disabled=True)
        yield self.repair_button
        yield Footer()

    async def on_mount(self) -> None:
        await self.refresh_arrays()

    async def refresh_arrays(self):
        self.raid_arrays = get_mdadm_arrays()
        self.raid_list.clear()
        for dev in self.raid_arrays:
            details = get_array_details(dev)
            status = details["status"] if details else "unknown"
            zh_status = details["zh_status"] if details else "未知"
            abnormal = details["abnormal"] if details else True
            # 高亮规则
            if not abnormal and zh_status == "正常":
                label = f"[green]{dev} (正常)[/green]"
            elif abnormal:
                label = f"[red]{dev} ({zh_status})[/red]"
            elif "降级" in zh_status:
                label = f"[yellow]{dev} ({zh_status})[/yellow]"
            elif "活跃" in zh_status or "空闲" in zh_status:
                label = f"[green]{dev} ({zh_status})[/green]"
            else:
                label = f"{dev} ({zh_status})"
            self.raid_list.append(ListItem(Label(label)))
        if self.raid_arrays:
            self.selected_index = 0
            await self.show_details(0)
        else:
            self.detail_label.update("未检测到RAID阵列。")
        self.repair_button.disabled = True

    async def show_details(self, idx):
        if 0 <= idx < len(self.raid_arrays):
            dev = self.raid_arrays[idx]
            details = get_array_details(dev)
            if details:
                info = f"设备: {dev}\n状态: {details['zh_status']}\nRAID级别: {details['raid_level']}\nUUID: {details['uuid']}\n"
                if details['device_info']:
                    info += f"\n硬盘信息:\n{details['device_info']}"
                if details['abnormal']:
                    info += "\n[red]警告：该阵列状态失败！可尝试修复。[/red]"
                elif details.get("degraded"):
                    info += "\n[yellow]警告：该阵列降级，请前往飞牛磁盘管理修复。[/yellow]"
                self.detail_label.update(info)
                # 只有failed才允许修复
                self.repair_button.disabled = not details['abnormal']
                self.current_abnormal = details['abnormal']
            else:
                self.detail_label.update(f"无法获取 {dev} 的详细信息。")
                self.repair_button.disabled = True
                self.current_abnormal = False
        else:
            self.detail_label.update("")
            self.repair_button.disabled = True
            self.current_abnormal = False

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = self.raid_list.index
        self.selected_index = idx
        await self.show_details(idx)

    async def on_key(self, event: events.Key) -> None:
        if event.key == "up":
            if self.selected_index > 0:
                self.selected_index -= 1
                await self.show_details(self.selected_index)
                self.raid_list.index = self.selected_index
        elif event.key == "down":
            if self.selected_index < len(self.raid_arrays) - 1:
                self.selected_index += 1
                await self.show_details(self.selected_index)
                self.raid_list.index = self.selected_index
        elif event.key == "r":
            await self.refresh_arrays()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "repair-btn" and getattr(self, 'current_abnormal', False):
            idx = self.selected_index
            dev = self.raid_arrays[idx]
            details = get_array_details(dev)
            async def do_repair(selected_disks):
                if not selected_disks:
                    self.show_message("未选择任何磁盘，修复已取消。")
                    return
                disks_str = " ".join(selected_disks)
                cmd = f"mdadm --assemble --force --run {dev} {disks_str}"
                self.show_message(f"执行修复命令：\n{cmd}")
                stdout, stderr = run_command(cmd)
                if stdout:
                    self.show_message(f"修复输出：\n{stdout}")
                if stderr:
                    self.show_message(f"修复警告/错误：\n{stderr}")
            self.push_screen(RepairScreen(dev, details, do_repair))

    def show_message(self, msg):
        self.push_screen(MessageScreen(msg))

if __name__ == "__main__":
    RaidRepairApp().run() 