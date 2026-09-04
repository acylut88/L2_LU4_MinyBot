import customtkinter as ctk
import tkinter as tk
import pyautogui
from typing import Callable, Tuple

class CalibrationOverlay(ctk.CTkToplevel):
    def __init__(self, parent, point_type: str, callback: Callable[[str, int, int, Tuple], None]):
        super().__init__(parent)
        
        self.point_type = point_type
        self.callback = callback

        # Настройки окна: полноэкранный режим, полупрозрачность, поверх всех окон
        self.attributes("-fullscreen", True)
        self.attributes("-alpha", 0.3)
        self.attributes("-topmost", True)
        
        # Убираем стандартные рамки Windows, чтобы оверлей был чистым
        self.overrideredirect(True) 
        
        # Курсор в виде перекрестия
        self.configure(cursor="crosshair")
        self.configure(fg_color="black") # Цвет фона для полупрозрачности

        # Текст-подсказка по центру
        self.label = ctk.CTkLabel(
            self, 
            text=f"Калибровка: {point_type}\nЛКМ - выбрать, ПКМ / Esc - отмена",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="white"
        )
        self.label.place(relx=0.5, rely=0.5, anchor="center")

        # Привязка событий мыши и клавиатуры
        self.bind("<Button-1>", self._on_left_click)   # Левый клик
        self.bind("<Button-3>", self._on_right_click)  # Правый клик
        self.bind("<Escape>", self._on_escape)         # Esc

        # Фокусируем окно, чтобы оно сразу ловило клавиши
        self.focus_force()

    def _on_left_click(self, event):
        """Обработка левого клика: считывание координат и цвета."""
        # Получаем глобальные координаты курсора
        x = self.winfo_pointerx()
        y = self.winfo_pointery()

        # Мгновенно считываем цвет пикселя под курсором
        # Используем pyautogui, так как он отлично подходит для одиночных точек 
        # и не требует возни с BGR/RGB конвертацией как в mss.
        rgb = pyautogui.pixel(x, y)

        # Передаем данные в главное окно
        if self.callback:
            self.callback(self.point_type, x, y, rgb)

        # Закрываем оверлей
        self.destroy()

    def _on_right_click(self, event):
        """Отмена по правому клику."""
        self.destroy()

    def _on_escape(self, event):
        """Отмена по Esc."""
        self.destroy()