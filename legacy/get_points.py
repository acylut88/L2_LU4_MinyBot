import tkinter as tk
from tkinter import messagebox
import configparser
import os
import ctypes
import pyautogui

# Принудительный фикс масштабирования Windows (DPI)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

class TkinterCalibrator:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_file = 'bot_config.ini'
        
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            self.config['SETTINGS'] = {'port': 'COM4', 'baudrate': '115200', 'profile': '1'}
            self.config['PIXELS'] = {}

        # Главное окно
        self.root = tk.Tk()
        self.root.title("Калибровка точек v1.3")
        self.root.geometry("400x430")  # Увеличили высоту с 380 до 430
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)

        # Секция выбора профиля
        tk.Label(self.root, text="Шаг 1: Выберите профиль класса", font=("Arial", 10, "bold")).pack(pady=8)
        self.profile_var = tk.StringVar(value=self.config['SETTINGS'].get('profile', '1'))
        
        frame_prof = tk.Frame(self.root)
        frame_prof.pack(pady=2)
        tk.Radiobutton(frame_prof, text="Милик (без MP)", variable=self.profile_var, value="1", command=self.toggle_mp_buttons, font=("Arial", 10)).pack(side=tk.LEFT, padx=15)
        tk.Radiobutton(frame_prof, text="Маг (с учетом MP)", variable=self.profile_var, value="2", command=self.toggle_mp_buttons, font=("Arial", 10)).pack(side=tk.LEFT, padx=15)

        # Секция калибровки точек
        tk.Label(self.root, text="Шаг 2: Отметьте точки на экране", font=("Arial", 10, "bold")).pack(pady=10)
        
        # Уменьшили отступы pady с 4 до 3 для более плотной и аккуратной посадки
        self.btn_hp = tk.Button(self.root, text="Указать точку HP (Левый край бара)", height=2, command=lambda: self.start_capture("hp_point", "hp_color"))
        self.btn_hp.pack(fill=tk.X, padx=40, pady=3)

        self.btn_sk = tk.Button(self.root, text="Указать точку Черепа (Окантовка смерти)", height=2, command=lambda: self.start_capture("skull_point", "skull_color"))
        self.btn_sk.pack(fill=tk.X, padx=40, pady=3)

        self.btn_mp1 = tk.Button(self.root, text="Указать точку МИНИМУМ MP (Посадка)", height=2, command=lambda: self.start_capture("mp_low_point", "mp_low_color"))
        self.btn_mp1.pack(fill=tk.X, padx=40, pady=3)

        self.btn_mp2 = tk.Button(self.root, text="Указать точку МАКСИМУМ MP (Подъем)", height=2, command=lambda: self.start_capture("mp_full_point", "mp_full_color"))
        self.btn_mp2.pack(fill=tk.X, padx=40, pady=3)

        # Финальное сохранение (теперь кнопка встанет идеально)
        self.btn_save = tk.Button(self.root, text="СОХРАНИТЬ НАСТРОЙКИ", bg="#2ecc71", fg="white", font=("Arial", 10, "bold"), height=2, command=self.save_config)
        self.btn_save.pack(fill=tk.X, padx=40, pady=15)

        self.toggle_mp_buttons()
        self.root.mainloop()

    def toggle_mp_buttons(self):
        state = tk.NORMAL if self.profile_var.get() == "2" else tk.DISABLED
        self.btn_mp1.config(state=state)
        self.btn_mp2.config(state=state)

    def start_capture(self, point_key, color_key):
        self.root.withdraw()
        self.root.update()
        self.root.after(200)

        self.overlay = tk.Toplevel()
        self.overlay.attributes("-fullscreen", True)
        self.overlay.attributes("-alpha", 0.3)
        self.overlay.attributes("-topmost", True)
        self.overlay.configure(cursor="cross")

        canvas = tk.Canvas(self.overlay, bg="grey", highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.bind("<ButtonRelease-1>", lambda event: self.get_absolute_pixel(point_key, color_key))

    def get_absolute_pixel(self, point_key, color_key):
        x, y = pyautogui.position()
        try:
            color = pyautogui.pixel(x, y)
            self.config['PIXELS'][point_key] = f"{x},{y}"
            self.config['PIXELS'][color_key] = f"{color[0]},{color[1]},{color[2]}"
            print(f"[📊 Конфиг] Запись {point_key} -> Координаты: ({x}, {y}), Цвет RGB: {color}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось считать пиксель: {e}")

        self.overlay.destroy()
        self.root.deiconify()

    def save_config(self):
        self.config['SETTINGS']['profile'] = self.profile_var.get()
        with open(self.config_file, 'w') as f:
            self.config.write(f)
        messagebox.showinfo("Успех", "Конфигурация версии 1.3 успешно обновлена!")

if __name__ == "__main__":
    TkinterCalibrator()
