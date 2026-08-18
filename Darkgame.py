import ctypes
from ctypes import windll
import platform
import cv2
import mediapipe as mp
import tkinter as tk

# WinAPI Константы
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
LWA_ALPHA = 0x2

# --- ФИКС ДЛЯ 64-БИТНЫХ СИСТЕМ ---
# Используем SetWindowLongPtrW на 64-битных ОС, чтобы избежать вылета (Access Violation)
if platform.architecture()[0] == "64bit":
    GetWindowLong = windll.user32.GetWindowLongPtrW
    SetWindowLong = windll.user32.SetWindowLongPtrW
else:
    GetWindowLong = windll.user32.GetWindowLongW
    SetWindowLong = windll.user32.SetWindowLongW


def set_ghost_style(hwnd):
    if not hwnd:
        return
    # Получаем текущие стили через правильную функцию
    style = GetWindowLong(hwnd, GWL_EXSTYLE)

    # Комбинируем флаги: Сквозной клик + Слой + Без активации + Скрытие из панели задач
    new_style = (
        style
        | WS_EX_TRANSPARENT
        | WS_EX_LAYERED
        | WS_EX_NOACTIVATE
        | WS_EX_TOOLWINDOW
    )

    SetWindowLong(hwnd, GWL_EXSTYLE, new_style)
    # Устанавливаем прозрачность
    windll.user32.SetLayeredWindowAttributes(hwnd, 0, 255, LWA_ALPHA)


L_THRESHOLD = 0.18
R_THRESHOLD = 0.22
APPEAR_DELAY = 1
RETAIN_DELAY = 25

# --- ИНИЦИАЛИЗАЦИЯ MEDIAPIPE ---
mp_face = mp.solutions.face_mesh
face_mesh = mp_face.FaceMesh(refine_landmarks=True, max_num_faces=1)


def setup_win(win, geom):
    win.configure(bg="black")
    win.geometry(geom)
    win.overrideredirect(True)
    win.attributes("-topmost", True)

    win.update()  # Принудительно создаем окно в системе
    hwnd = windll.user32.GetParent(win.winfo_id())
    if not hwnd:
        hwnd = win.winfo_id()

    set_ghost_style(hwnd)
    win.withdraw()


# Инициализация Tkinter
root_r = tk.Tk()
screen_w = root_r.winfo_screenwidth()
screen_h = root_r.winfo_screenheight()
half = screen_w // 2

root_l = tk.Toplevel(root_r)
setup_win(root_r, f"{half}x{screen_h}+{half}+0")
setup_win(root_l, f"{half}x{screen_h}+0+0")

EYE_L = [159, 145, 33, 133]
EYE_R = [386, 374, 362, 263]

l_counter = 0
r_counter = 0

# Проверка подключения камеры
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Ошибка: Не удалось открыть веб-камеру!")
    exit()

while True:
    success, img = cap.read()
    if not success:
        print("Не удалось получить кадр с камеры")
        break

    img = cv2.flip(img, 1)
    results = face_mesh.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    l_is_closed = False
    r_is_closed = False

    if results.multi_face_landmarks:
        face = results.multi_face_landmarks[0]

        # Защита от деления на 0
        def get_ratio(idx):
            t, b, l, r = [face.landmark[i] for i in idx]
            width = abs(l.x - r.x)
            if width == 0:
                return 0.0
            return abs(t.y - b.y) / width

        if get_ratio(EYE_L) < L_THRESHOLD:
            l_is_closed = True
        if get_ratio(EYE_R) < R_THRESHOLD:
            r_is_closed = True

    # Логика счетчиков
    l_counter = (
        (RETAIN_DELAY + APPEAR_DELAY) if l_is_closed else max(0, l_counter - 1)
    )
    r_counter = (
        (RETAIN_DELAY + APPEAR_DELAY) if r_is_closed else max(0, r_counter - 1)
    )

    # Управление левым окном
    if l_counter > RETAIN_DELAY:
        if not root_l.winfo_viewable():
            root_l.deiconify()
    elif l_counter == 0:
        if root_l.winfo_viewable():
            root_l.withdraw()

    # Управление правым окном
    if r_counter > RETAIN_DELAY:
        if not root_r.winfo_viewable():
            root_r.deiconify()
    elif r_counter == 0:
        if root_r.winfo_viewable():
            root_r.withdraw()

    # Безопасное обновление Tkinter
    try:
        root_r.update()
    except tk.TclError:
        break  # Выход, если окно была уничтожено

    # Дебаг-окно
    cv2.putText(
        img, f"L: {l_counter} | R: {r_counter}", (30, 50), 1, 1, (0, 255, 0), 2
    )
    cv2.imshow("CONTROL PANEL (Press ']' to exit)", img)

    if cv2.waitKey(1) & 0xFF == ord("]"):
        break

# Очистка ресурсов при выходе
cap.release()
cv2.destroyAllWindows()
try:
    root_r.destroy()
except Exception:
    pass