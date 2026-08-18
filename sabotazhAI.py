import sys
import os
import json
import random
import ctypes
from ctypes import windll, wintypes
import pydirectinput
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor, QTransform, QPen, QIcon

try:
    myappid = 'mycompany.deadlock.roulette.1.0'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

pydirectinput.PAUSE = 0.05

DEFAULT_CONFIG = {
    "COUNTDOWN_TIME": 40,
    "ULT_KEYS": ["e", "f", "l", "i"],
    "PUNISHMENTS": [
        {"id": "disco", "text": "ДИСКОТЕКА", "weight": 20},
        {"id": "moonwalk", "text": "ЛУННАЯ ПОХОДКА", "weight": 15},
        {"id": "reload", "text": "ВНЕЗАПНАЯ ПЕРЕЗАРЯДКА", "weight": 10},
        {"id": "drunk", "text": "ПЬЯНЫЙ ПРИЦЕЛ", "weight": 15},
        {"id": "hyper_mouse", "text": "ГИПЕР-ЧУВСТВИТЕЛЬНОСТЬ", "weight": 15},
        {"id": "flashbang", "text": "ФЛЕШКА", "weight": 10},
        {"id": "half_blind", "text": "Минус один глаз", "weight": 10},
        {"id": "rand_ult", "text": "СЛУЧАЙНАЯ СПОСОБНОСТЬ!", "weight": 5}
    ]
}


def load_config():
    exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(
        os.path.abspath(__file__))
    config_path = os.path.join(exe_dir, 'config.json')

    if not os.path.exists(config_path):
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка создания конфига: {e}")
        return DEFAULT_CONFIG

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка чтения config.json: {e}")
        return DEFAULT_CONFIG


CONFIG = load_config()

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_APPWINDOW = 0x00040000


def make_window_ghost(hwnd):
    style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    new_style = style | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE | WS_EX_APPWINDOW
    windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)


def create_app_icon():
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(230, 57, 70))
    painter.setPen(QPen(Qt.black, 2))
    painter.drawRoundedRect(4, 4, 56, 56, 12, 12)
    painter.setPen(Qt.white)
    painter.setFont(QFont("Arial", 28, QFont.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "R")
    painter.end()
    return QIcon(pixmap)


def create_dummy_wheel(punishments_list, size=500):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    active_punishments = [p for p in punishments_list if p["weight"] > 0]
    num_sectors = len(active_punishments) if len(active_punishments) > 0 else len(punishments_list)
    display_list = active_punishments if len(active_punishments) > 0 else punishments_list

    base_colors = [
        QColor(230, 57, 70), QColor(241, 250, 238), QColor(69, 123, 157),
        QColor(29, 53, 87), QColor(244, 162, 97), QColor(42, 157, 143),
        QColor(233, 196, 106), QColor(141, 153, 174), QColor(214, 40, 40)
    ]

    rect = QRectF(10, 10, size - 20, size - 20)
    sector_deg = 360.0 / num_sectors
    span_angle = int(sector_deg * 16)
    center = size / 2.0

    font = QFont("Arial", 9, QFont.Bold)
    painter.setFont(font)

    for i, item in enumerate(display_list):
        color = base_colors[i % len(base_colors)]
        painter.setBrush(color)
        text_color = Qt.black if color.lightness() > 128 else Qt.white

        painter.setPen(QPen(Qt.black, 2))
        painter.drawPie(rect, int(i * span_angle), span_angle)

        mid_angle_deg = (i * sector_deg) + (sector_deg / 2.0)

        painter.save()
        painter.translate(center, center)
        painter.rotate(-mid_angle_deg)
        painter.setPen(text_color)

        x_start = size * 0.18
        text_width = size * 0.30
        text_height = 50
        text_rect = QRectF(x_start, -text_height / 2.0, text_width, text_height)

        display_text = item["text"]
        painter.drawText(text_rect, Qt.AlignCenter | Qt.TextWordWrap, display_text)
        painter.restore()

    painter.setBrush(Qt.white)
    painter.setPen(QPen(Qt.black, 2))
    painter.drawEllipse(QPointF(center, center), 25, 25)
    painter.end()
    return pixmap


class Overlay(QMainWindow):
    def __init__(self):
        super().__init__()
        self.time_left = CONFIG.get("COUNTDOWN_TIME", 180)
        self.spin_angle = 0
        self.spin_speed = 0
        self.last_mouse_pos = (0, 0)
        self.is_paused = False

        self.initUI()
        self.setup_tray_icon()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setWindowTitle("Deadlock Рулетка")
        self.setWindowIcon(create_app_icon())

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(0, 0, screen.width(), screen.height())

        self.punishment_layer = QLabel(self)
        self.punishment_layer.setGeometry(0, 0, screen.width(), screen.height())
        self.punishment_layer.setScaledContents(True)
        self.punishment_layer.hide()

        self.timer_label = QLabel(self)
        self.timer_label.setGeometry(screen.width() - 200, 50, 150, 50)
        self.timer_label.setFont(QFont("Arial", 30, QFont.Bold))
        self.timer_label.setStyleSheet("color: white; background-color: rgba(0,0,0,150); border-radius: 10px;")
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.update_timer_text()

        self.wheel_size = 400
        self.wheel_original_pixmap = create_dummy_wheel(CONFIG.get("PUNISHMENTS", []), self.wheel_size)
        self.wheel_label = QLabel(self)
        self.wheel_label.setGeometry(screen.width() - self.wheel_size - 50,
                                     screen.height() // 2 - self.wheel_size // 2,
                                     self.wheel_size, self.wheel_size)
        self.wheel_label.setAlignment(Qt.AlignCenter)
        self.wheel_label.hide()

        self.result_label = QLabel(self)
        self.result_label.setGeometry(0, screen.height() // 2 - 100, screen.width(), 200)
        self.result_label.setFont(QFont("Arial", 60, QFont.Bold))
        self.result_label.setStyleSheet("color: red; background-color: rgba(0,0,0,200);")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.hide()

        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.tick_countdown)
        self.countdown_timer.start(1000)

        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self.rotate_wheel)

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(create_app_icon())
        self.tray_icon.setToolTip("Deadlock Рулетка")

        tray_menu = QMenu()
        self.pause_action = QAction("Пауза", self)
        self.pause_action.triggered.connect(self.toggle_pause)
        tray_menu.addAction(self.pause_action)

        tray_menu.addSeparator()

        exit_action = QAction("Выход из программы", self)
        exit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def toggle_pause(self):
        if not self.is_paused:
            self.countdown_timer.stop()
            self.is_paused = True
            self.timer_label.setText("ПАУЗА")
            self.pause_action.setText("Возобновить")
        else:
            self.is_paused = False
            self.countdown_timer.start(1000)
            self.update_timer_text()
            self.pause_action.setText("Пауза")

    def update_timer_text(self):
        mins = self.time_left // 60
        secs = self.time_left % 60
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")

    def tick_countdown(self):
        self.time_left -= 1
        self.update_timer_text()
        if self.time_left <= 0:
            self.countdown_timer.stop()
            self.start_roulette()

    def start_roulette(self):
        self.result_label.hide()
        self.timer_label.hide()
        self.wheel_label.show()
        self.spin_speed = random.randint(30, 50)
        self.anim_timer.start(16)

    def rotate_wheel(self):
        self.spin_angle = (self.spin_angle + self.spin_speed) % 360
        self.spin_speed *= 0.98

        transform = QTransform().rotate(self.spin_angle)
        rotated_pixmap = self.wheel_original_pixmap.transformed(transform, Qt.SmoothTransformation)
        self.wheel_label.setPixmap(rotated_pixmap)

        if self.spin_speed < 0.3:
            self.anim_timer.stop()
            self.show_result()

    def show_result(self):
        self.wheel_label.hide()

        punishments = CONFIG.get("PUNISHMENTS", [])
        weights = [p["weight"] for p in punishments]
        chosen_punishment = random.choices(punishments, weights=weights, k=1)[0]
        p_id = chosen_punishment["id"]

        self.result_label.setText(f"НАКАЗАНИЕ:\n{chosen_punishment['text']}")
        self.result_label.show()
        QTimer.singleShot(1000, lambda: self.trigger_effect(p_id))

    def trigger_effect(self, p_id):
        self.result_label.hide()
        self.execute_punishment(p_id)

    def execute_punishment(self, p_id):
        print(f"Активировано наказание: {p_id}")
        screen_w = self.width()
        screen_h = self.height()

        self.punishment_layer.setGeometry(0, 0, screen_w, screen_h)
        self.punishment_layer.setPixmap(QPixmap())
        self.punishment_layer.setStyleSheet("")

        #  ПОЛУОСЛЕПЛЕНИЕ
        if p_id == "half_blind":
            self.punishment_layer.setGeometry(0, 0, screen_w // 2, screen_h)
            self.punishment_layer.setStyleSheet("background-color: black;")
            self.punishment_layer.show()
            QTimer.singleShot(10000, self.end_punishment)

        # 2. ФЛЕШКА
        elif p_id == "flashbang":
            self.punishment_layer.setStyleSheet("background-color: white;")
            self.punishment_layer.show()
            QTimer.singleShot(3000, self.end_punishment)

        # 3. ДИСКОТЕКА
        elif p_id == "disco":
            self.punishment_layer.show()
            self.disco_timer = QTimer(self)
            self.disco_timer.timeout.connect(self.disco_blink)
            self.disco_timer.start(200)
            QTimer.singleShot(5000, self.end_punishment)

        # 4. ЛУННАЯ ПОХОДКА
        elif p_id == "moonwalk":
            pydirectinput.keyDown("s")
            QTimer.singleShot(4000, self.stop_moonwalk)

        # 5. СЛУЧАЙНАЯ СПОСОБНОСТЬ
        elif p_id == "rand_ult":
            ult_keys = CONFIG.get("ULT_KEYS", ["e", "f", "l", "i",])
            key = random.choice(ult_keys)
            pydirectinput.press(key)
            print(f"Нажата кнопка из конфига: {key}")
            QTimer.singleShot(1000, self.end_punishment)

        # 6. СПАМ ПЕРЕЗАРЯДКИ
        elif p_id == "reload":
            self.reload_timer = QTimer(self)
            self.reload_timer.timeout.connect(lambda: pydirectinput.press('r'))
            self.reload_timer.start(500)
            QTimer.singleShot(6000, self.stop_reload)

        # 7. ПЬЯНЫЙ ПРИЦЕЛ
        elif p_id == "drunk":
            self.start_drunk_mouse()
            QTimer.singleShot(6000, self.end_punishment)

        # 8. ГИПЕР-ЧУВСТВИТЕЛЬНОСТЬ
        elif p_id == "hyper_mouse":
            self.start_hyper_mouse()
            QTimer.singleShot(6000, self.end_punishment)

    def start_hyper_mouse(self):
        self.hyper_timer = QTimer(self)
        self.hyper_timer.timeout.connect(self.update_hyper_mouse)
        self.hyper_timer.start(20)  # 50 ураганных импульсов в секунду

    def update_hyper_mouse(self):

        dx = random.choice([-4000, -2500, -1500, 1500, 2500, 4000])
        dy = random.choice([-2000, -1200, -800, 800, 1200, 2000])
        windll.user32.mouse_event(0x0001, dx, dy, 0, 0)

    def start_drunk_mouse(self):
        self.drunk_timer = QTimer(self)
        self.drunk_timer.timeout.connect(self.update_drunk_mouse)
        self.drunk_timer.start(25)

    def update_drunk_mouse(self):
        dx = random.randint(-18, 18)
        dy = random.randint(-18, 18)
        windll.user32.mouse_event(0x0001, dx, dy, 0, 0)

    def stop_moonwalk(self):
        pydirectinput.keyUp('s')
        self.end_punishment()

    def stop_reload(self):
        if hasattr(self, 'reload_timer') and self.reload_timer.isActive():
            self.reload_timer.stop()
        self.end_punishment()

    def disco_blink(self):
        colors = ["rgba(255,0,0,100)", "rgba(0,0,255,100)", "rgba(0,255,0,100)","rgba(255, 20, 147,100)","rgba(255, 255, 0,100)"]
        color = random.choice(colors)
        self.punishment_layer.setStyleSheet(f"background-color: {color};")

    def end_punishment(self):
        self.punishment_layer.hide()
        self.punishment_layer.setPixmap(QPixmap())

        # Гарантированно отжимаем ходьбу
        pydirectinput.keyUp('s')

        # Останавливаем таймеры
        if hasattr(self, 'disco_timer') and self.disco_timer.isActive():
            self.disco_timer.stop()
        if hasattr(self, 'reload_timer') and self.reload_timer.isActive():
            self.reload_timer.stop()
        if hasattr(self, 'drunk_timer') and self.drunk_timer.isActive():
            self.drunk_timer.stop()
        if hasattr(self, 'hyper_timer') and self.hyper_timer.isActive():
            self.hyper_timer.stop()

        print("Наказание окончено. Запуск таймера.")
        if not self.is_paused:
            self.reset_cycle()

    # обновление колеса
    def reset_cycle(self):
        self.result_label.hide()
        self.timer_label.show()
        self.time_left = CONFIG.get("COUNTDOWN_TIME", 180)
        self.countdown_timer.start(1000)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    app.setWindowIcon(create_app_icon())

    overlay = Overlay()
    overlay.show()

    hwnd = int(overlay.winId())
    make_window_ghost(hwnd)

    sys.exit(app.exec_())