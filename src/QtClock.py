# -*- coding: UTF-8 -*-
"""
PROJECT_NAME Python_projects
PRODUCT_NAME PyCharm
NAME myclock
AUTHOR Pfolg
TIME 2025/3/30 0:36
"""
import json
import os.path
import socket
import sys

from PySide6 import QtCore
from PySide6.QtCore import Qt, QTimer, QDateTime, QRect
from PySide6.QtGui import QAction, QIcon, QFont
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QSystemTrayIcon, QMenu, QPushButton, QSlider, \
    QCheckBox, QFontDialog, QColorDialog, QHBoxLayout


class RainbowLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignTrailing)
        self.setMinimumSize(200, 200)
        font = QFont()
        font.setFamily("Ubuntu Mono")
        font.setPointSize(28)
        self.setFont(font)
        self.setStyleSheet(
            """
            background-color: transparent;
            color: rgba(255, 255, 255, .7);
            font-weight: bold;
        """)

        # 动画参数
        self.hue = 0.0  # 色相初始值 (0-360)
        self.speed = 1.0  # 颜色变化速度
        self.saturation = 1.0  # 饱和度 (0-1)
        self.lightness = 0.5  # 亮度 (0-1)
        self.alpha = 0.8  # 透明度 (0-1)

        # 彩虹变色线程
        self.timer1 = QTimer(self)
        self.timer1.timeout.connect(self.update_color)
        # self.timer1.start(80)  # 50 FPS

        # 时间线程
        self.timer2 = QTimer(self)
        self.timer2.timeout.connect(self.update_time)
        self.timer2.start(200)  # 5 FPS

    def hsv_to_rgb(self, h):
        """将HSV颜色空间转换为RGB"""
        h = h % 360
        c = self.lightness * self.saturation
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = self.lightness - c

        if 0 <= h < 60:
            r, g, b = c, x, 0
        elif 60 <= h < 120:
            r, g, b = x, c, 0
        elif 120 <= h < 180:
            r, g, b = 0, c, x
        elif 180 <= h < 240:
            r, g, b = 0, x, c
        elif 240 <= h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x

        return (
            int((r + m) * 255),
            int((g + m) * 255),
            int((b + m) * 255),
            int(self.alpha * 255)
        )

    def update_color(self):
        """更新颜色并应用样式"""
        # 色相递增
        self.hue = (self.hue + self.speed) % 360

        # 转换为RGB
        r, g, b, a = self.hsv_to_rgb(self.hue)

        # 应用样式
        self.setStyleSheet(f"""
            QLabel {{
                color: rgba({r}, {g}, {b}, {a});
                background-color: transparent;
                border-radius: 100px;
                
            }}
        """)  # font-size: 24px;

    @staticmethod
    def calculate_time(t1: int, t2: int, mode: str) -> str:
        if (not t2 in [1, 2]) or (t1 > 60 | t1 < 0) or (not mode in ["+", "-"]):
            return ""
        t = t1
        if mode == "+":
            t = t1 + t2
            if t > 60:
                t -= 60
        elif mode == "-":
            t = t1 - t2
            if t < 0:
                t += 60
        if 0 <= t < 10:
            return "0" + str(t)
        else:
            return str(t)

    def update_time(self):
        crt_time = QDateTime.currentDateTime()
        weekday = crt_time.toString("dddd")
        sec = crt_time.time().second()
        minute = crt_time.time().minute()
        mode1, mode2 = "+", "-"

        time_text = (
            f"{self.calculate_time(sec, 2, mode2)}\n"
            f"{self.calculate_time(minute, 1, mode2)}:{self.calculate_time(sec, 1, mode2)}\n"
            f"{crt_time.toString('yyyy-MM-dd hh:mm:ss')}\n"
            f"{weekday}    {self.calculate_time(minute, 1, mode1)}:{self.calculate_time(sec, 1, mode1)}\n"
            f"{self.calculate_time(sec, 2, mode1)}")
        self.setText(time_text)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        # 主布局
        layout = QVBoxLayout(self)
        # 水平布局
        h_layout = QHBoxLayout()
        self.label = RainbowLabel()
        h_layout.addWidget(self.label)
        # 添加弹簧将时钟左推
        h_layout.addStretch()
        # 添加水平布局到主布局
        layout.addLayout(h_layout)

        # 启用透明度
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |  # 去除标题栏
            Qt.WindowType.Tool |  # 去除任务栏图标
            Qt.WindowType.WindowTransparentForInput  # 鼠标穿透
        )


class LoadedUI(QWidget):
    def __init__(self, data: {}):
        super().__init__()
        ui = QUiLoader().load("setting.ui", self)
        self.font: str = data.get("font")
        self.color: str = data.get("color")
        self.winLocation: list = data.get("location")
        self.isRainbow: bool = data.get("isRainbow")
        self.pushButton_font: QPushButton = ui.findChild(QPushButton, "pushButton")
        self.pushButton_color: QPushButton = ui.findChild(QPushButton, "pushButton_2")
        self.label: QLabel = ui.findChild(QLabel, "label")
        self.horizontalSlider_x: QSlider = ui.findChild(QSlider, "horizontalSlider")
        self.horizontalSlider_y: QSlider = ui.findChild(QSlider, "horizontalSlider_2")
        self.checkBox: QCheckBox = ui.findChild(QCheckBox, "checkBox")
        self.screen_w, self.screen_h = get_screen_info()
        # self.screen_geometry = primary_screen.availableGeometry()  # 可用区域（排除任务栏）
        print("screen w&h :", self.screen_w, self.screen_h)
        self.setup()
        self.set_function()

    def save_data(self):
        mydata = {
            "font": self.font,
            "color": self.color,
            "location": self.winLocation,
            "isRainbow": self.isRainbow,
            "port": setting_data.get("port")

        }
        print(mydata)
        font = QFont()
        font.fromString(self.font)
        self.label.setStyleSheet(f"color:{self.color}")
        self.label.setFont(font)
        root.label.setStyleSheet(f"color:{self.color}")
        root.label.setFont(font)
        with open("setting.json", "w", encoding="utf-8") as file:
            json.dump(mydata, file, ensure_ascii=False, indent=4)

    def change_location(self):
        self.winLocation = (self.horizontalSlider_x.value(), self.horizontalSlider_y.value())
        print(self.winLocation)
        root.setGeometry(*self.winLocation, self.screen_w, self.screen_h)
        self.save_data()

    def select_font(self):
        ok, font = QFontDialog.getFont()
        if ok:
            # print(font, font.toString())
            self.font = font.toString()
        self.save_data()

    def select_color(self):  # 只会返回颜色
        # 弹出颜色对话框并获取颜色
        color = QColorDialog.getColor()

        if color.isValid():
            # 获取颜色信息
            hex_color = color.name()  # 十六进制字符串，如 "#ff0000"
            # rgb = color.getRgb()  # 元组 (R, G, B, A)
            # rgba_normalized = color.getRgbF()  # 浮点数元组 (0-1范围)

            # print(f"十六进制: {hex_color}")
            # print(f"RGB(A) 值: {rgb}")
            # print(f"标准化 RGBA: {rgba_normalized}")
            self.color = hex_color
        self.save_data()

    def use_rainbow(self):
        state = self.checkBox.isChecked()
        self.isRainbow = state
        # print(state)
        if state:
            root.label.timer1.start(80)
        else:
            root.label.timer1.stop()
            root.label.setStyleSheet(f"color:{self.color}")

        self.save_data()

    def setup(self):
        self.horizontalSlider_x.setValue(self.winLocation[0])
        self.horizontalSlider_y.setValue(self.winLocation[1])
        self.checkBox.setChecked(self.isRainbow)
        font = QFont()
        font.fromString(self.font)
        self.label.setStyleSheet(f"color:{self.color}")
        self.label.setFont(font)

    def set_function(self):
        self.pushButton_font.clicked.connect(self.select_font)
        self.pushButton_color.clicked.connect(self.select_color)
        self.horizontalSlider_x.setMaximum(self.screen_w)
        self.horizontalSlider_y.setMaximum(self.screen_h)
        self.horizontalSlider_x.valueChanged.connect(self.change_location)
        self.horizontalSlider_y.valueChanged.connect(self.change_location)
        self.checkBox.stateChanged.connect(self.use_rainbow)

    # 忽略关闭事件
    def closeEvent(self, event):
        self.hide()
        event.ignore()


def SettingUI(data: {}):
    global setting_ui
    if not setting_ui:
        setting_ui = LoadedUI(data)
    setting_ui.show()


# 读取屏幕长宽
def get_screen_info() -> tuple:
    # 获取现有的 QApplication 实例
    _app = QApplication.instance()

    if _app is not None:
        screen = _app.primaryScreen().geometry()

        return screen.width(), screen.height()
    else:
        return 800, 600


def set_tray(icon: QSystemTrayIcon):
    icon.setToolTip("QtClock is running")
    menu = QMenu()
    action_quit = QAction(menu)
    action_quit.setText("Quit")
    action_quit.triggered.connect(sys.exit)
    action_set = QAction(menu)
    action_set.setText("Set")
    action_set.triggered.connect(lambda: SettingUI(setting_data))
    menu.addActions([action_set, action_quit])
    icon.setContextMenu(menu)
    icon.setIcon(QIcon("QC.png"))


def setup_setting() -> dict:
    if not os.path.exists("setting.json"):
        _data = {
            "font": "Ubuntu Mono,24,-1,5,500,0,0,0,0,0,0,0,0,0,0,1,Medium",
            "color": "#ffffff",
            "location": [0, 0],
            "isRainbow": False,
            "port": 20323
        }
        with open("setting.json", "w", encoding="utf-8") as file:
            json.dump(_data, file, indent=4, ensure_ascii=False)
    else:
        with open("setting.json", "r", encoding="utf-8") as file:
            _data: dict = json.load(file)

    return _data


def setup_clock(data: dict):
    geometry = [*data.get("location"), *get_screen_info()]
    root.setGeometry(*geometry)  # 位置
    # root.setGeometry(0, 0, *get_screen_info())  # 位置
    font_str = data.get("font")
    f = QFont()
    f.fromString(font_str)
    root.label.setFont(f)
    root.label.setStyleSheet(f"color:{data.get('color')}")
    if data.get("isRainbow"):
        root.label.timer1.start(80)


def single_instance(port: int):
    try:
        # 选择一个不常用的端口
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", port))
    except socket.error:
        print("另一个实例正在运行，退出。")
        sys.exit(1)
    return sock


if __name__ == '__main__':
    # 格式 "00\n00:00\n0000-00-00 00:00:00\n    Saturday    00:00\n00"
    setting_data = setup_setting()
    print(setting_data)
    # 单实例限制
    lock_socket = single_instance(setting_data.get("port"))
    # 定义应用
    app = QApplication(sys.argv)
    # 主窗口
    root = MainWindow()
    root.show()
    # 系统托盘
    tray = QSystemTrayIcon()
    set_tray(tray)
    tray.show()
    # 初始设定
    setup_clock(setting_data)
    # 设置窗口 全局变量
    setting_ui = None
    sys.exit(app.exec())
