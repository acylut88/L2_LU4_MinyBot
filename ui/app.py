"""
ui/app.py — Главное окно управления ботом Lineage 2 LU4.
Архитектура потоков:
  - Главный поток: customtkinter (root.mainloop)
  - Фоновый daemon-поток: asyncio event loop для BotCore
  - Связь UI -> Bot: asyncio.run_coroutine_threadsafe()
  - Связь Bot -> UI: root.after(0, callback)
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import asyncio
import threading
from typing import List, Tuple

# Импорты бэкенд-модулей
from core.config_manager import ConfigManager
from core.hardware_manager import HardwareManager
from core.vision_manager import VisionManager
from core.async_tasks import BotCore
from ui.calibration_overlay import CalibrationOverlay

# Глобальная настройка темы
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Все 36 валидных кнопок Lineage 2 (3 линии по 12 кнопок)
VALID_KEYS = {
    # Линия 1
    "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
    # Линия 2
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=",
    # Линия 3
    "Num1", "Num2", "Num3", "Num4", "Num5", "Num6", "Num7", "Num8", "Num9", "Num0", "Num/", "Num*"
}


class App(ctk.CTk):
    """Главное окно приложения. Владеет всеми менеджерами и UI."""

    def __init__(self):
        super().__init__()

        self.title("Lineage 2 LU4 Bot Control")
        self.geometry("850x650")

        # ── 1. Инициализация бэкенд-менеджеров ──
        self.config = ConfigManager()
        self.hardware = HardwareManager(self.config)
        self.vision = VisionManager()

        # ── 2. Запуск asyncio в отдельном daemon-потоке ──
        self.async_loop = asyncio.new_event_loop()
        self.async_thread = threading.Thread(
            target=self._run_async_loop, daemon=True
        )
        self.async_thread.start()

        # BotCore получает ссылку на event loop и все менеджеры
        self.bot_core = BotCore(
            config=self.config,
            hardware=self.hardware,
            vision=self.vision,
        )

        # ── 3. Построение интерфейса ──
        self._build_ui()

        # Корректное завершение при закрытии окна
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    # ================================================================
    #  АСИНХРОННЫЙ ПОТОК
    # ================================================================

    def _run_async_loop(self):
        """Целевая функция фонового потока — крутит event loop."""
        asyncio.set_event_loop(self.async_loop)
        self.async_loop.run_forever()

    # ================================================================
    #  ПОСТРОЕНИЕ UI
    # ================================================================

    def _build_ui(self):
        """Создание контейнера вкладок и всех четырёх вкладок."""
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)

        self._build_main_tab()
        self._build_calibration_tab()
        self._build_hotkeys_tab()
        self._build_logic_tab()

    # ──────────────── Вкладка 1: Главная ────────────────

    def _build_main_tab(self):
        tab = self.tabview.add("Главная")

        # Выбор профиля пользователя
        ctk.CTkLabel(tab, text="Профиль пользователя:").pack(pady=(10, 0))
        users = self.config.get_users()
        self.user_dropdown = ctk.CTkComboBox(
            tab, values=users, command=self._on_user_change
        )
        self.user_dropdown.set(self.config.current_user)
        self.user_dropdown.pack(pady=5)

        # Выбор разрешения
        ctk.CTkLabel(tab, text="Разрешения:").pack(pady=(10, 0))
        permissions = self.config.get_permissions()
        self.perm_dropdown = ctk.CTkComboBox(
            tab, values=permissions, command=self._on_permission_change
        )
        self.perm_dropdown.set(self.config.current_permission)
        self.perm_dropdown.pack(pady=5)

        # Кнопки управления ботом
        btn_frame = ctk.CTkFrame(tab)
        btn_frame.pack(pady=30)

        self.btn_start = ctk.CTkButton(
            btn_frame, text="СТАРТ", fg_color="green", command=self._start_bot
        )
        self.btn_start.grid(row=0, column=0, padx=10)

        self.btn_stop = ctk.CTkButton(
            btn_frame, text="СТОП", fg_color="red", command=self._stop_bot
        )
        self.btn_stop.grid(row=0, column=1, padx=10)

        self.btn_pause = ctk.CTkButton(
            btn_frame, text="ПАУЗА", fg_color="orange", command=self._pause_bot
        )
        self.btn_pause.grid(row=0, column=2, padx=10)

        # Метка статуса (обновляется потокобезопасно)
        self.status_label = ctk.CTkLabel(
            tab, text="Статус: Ожидание", text_color="gray"
        )
        self.status_label.pack(pady=20)

    # ──────────────── Вкладка 2: Калибровка ────────────────

    def _build_calibration_tab(self):
        tab = self.tabview.add("Калибровка")
        ctk.CTkLabel(
            tab, text="Нажмите кнопку и кликните по нужной точке на экране"
        ).pack(pady=10)

        points = ["HP", "MP", "CP", "Пет", "Моб", "Череп"]
        grid_frame = ctk.CTkFrame(tab)
        grid_frame.pack(pady=20)

        for i, point in enumerate(points):
            btn = ctk.CTkButton(
                grid_frame,
                text=f"Калибровать: {point}",
                command=lambda p=point: self._open_calibration(p),
            )
            btn.grid(row=i // 3, column=i % 3, padx=10, pady=10)

    # ──────────────── Вкладка 3: Хоткеи ────────────────

    def _build_hotkeys_tab(self):
        tab = self.tabview.add("Хоткеи")
        ctk.CTkLabel(
            tab, text="Сетка 3×12 (изменение сохраняется мгновенно)"
        ).pack(pady=10)

        actions = [
            "None", "Атака", "Хил", "Бафф", "Дебафф", "Призыв",
            "Предмет", "Скилл 1", "Скилл 2", "Скилл 3", "Скилл 4", "Скилл 5",
        ]

        grid_frame = ctk.CTkFrame(tab)
        grid_frame.pack(pady=10, padx=10, fill="both", expand=True)

        for row in range(3):
            for col in range(12):
                current_action = self.config.get_hotkey(row, col)
                combo = ctk.CTkComboBox(
                    grid_frame,
                    values=actions,
                    width=100,
                    command=lambda val, r=row, c=col: self._on_hotkey_change(
                        r, c, val
                    ),
                )
                combo.set(current_action if current_action in actions else "None")
                combo.grid(row=row, column=col, padx=3, pady=3)

    # ──────────────── Вкладка 4: Логика (Самобафф) ────────────────

    def _build_logic_tab(self):
        """Блок настроек самобаффа для основного персонажа (Окно 1)."""
        tab = self.tabview.add("Логика")

        # Контейнер для блока самобаффа
        frame = ctk.CTkFrame(tab)
        frame.pack(padx=20, pady=20, fill="x")

        ctk.CTkLabel(
            frame,
            text="Самобафф (Окно 1)",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(10, 15))

        # ── Чекбокс «Включить самобафф» ──
        logic = self.config.get_logic_settings()

        self.self_buff_var = tk.BooleanVar(
            value=logic.get("self_buff_enabled", False)
        )
        self.chk_self_buff = ctk.CTkCheckBox(
            frame,
            text="Включить самобафф",
            variable=self.self_buff_var,
            command=self._on_self_buff_toggle,
        )
        self.chk_self_buff.pack(anchor="w", padx=20, pady=(5, 10))

        # ── Поле «Интервал (минут)» ──
        interval_frame = ctk.CTkFrame(frame, fg_color="transparent")
        interval_frame.pack(anchor="w", padx=20, pady=5, fill="x")

        ctk.CTkLabel(interval_frame, text="Интервал (минут):").pack(
            side="left", padx=(0, 10)
        )

        self.buff_interval_var = tk.StringVar(
            value=str(logic.get("self_buff_interval", 19))
        )
        self.entry_interval = ctk.CTkEntry(
            interval_frame, textvariable=self.buff_interval_var, width=80
        )
        self.entry_interval.pack(side="left")
        self.entry_interval.bind("<FocusOut>", lambda e: self._save_self_buff_settings())
        self.entry_interval.bind("<Return>", lambda e: self._save_self_buff_settings())

        # ── Поле «Кнопки бафов» (Единое поле для всех 36 кнопок) ──
        hotkeys_frame = ctk.CTkFrame(frame, fg_color="transparent")
        hotkeys_frame.pack(anchor="w", padx=20, pady=5, fill="x")

        ctk.CTkLabel(
            hotkeys_frame, text="Кнопки бафов:"
        ).pack(side="left", padx=(0, 10))

        # Загрузка сохраненных кнопок и преобразование в строку
        saved_hotkeys = logic.get("self_buff_hotkeys", [])
        initial_text = ", ".join(saved_hotkeys) if saved_hotkeys else ""

        self.buff_hotkeys_var = tk.StringVar(value=initial_text)
        self.entry_hotkeys = ctk.CTkEntry(
            hotkeys_frame,
            textvariable=self.buff_hotkeys_var,
            width=450,
            placeholder_text="Введите кнопки через запятую, например: F1, F2, Num1"
        )
        self.entry_hotkeys.pack(side="left", fill="x", expand=True)

        self.entry_hotkeys.bind("<FocusOut>", lambda e: self._save_self_buff_settings())
        self.entry_hotkeys.bind("<Return>", lambda e: self._save_self_buff_settings())

        # ── Подсказка под полем ввода ──
        ctk.CTkLabel(
            frame,
            text="Доступно 36 кнопок: F1-F12, 1-9-0-=-, Num1-Num0-Num/-Num*",
            text_color="gray",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=20, pady=(5, 15))

    # ================================================================
    #  ОБРАБОТЧИКИ СОБЫТИЙ — ГЛАВНАЯ ВКЛАДКА
    # ================================================================

    def _on_user_change(self, choice: str):
        """Смена профиля пользователя."""
        self.config.switch_user(choice)

    def _on_permission_change(self, choice: str):
        """Смена разрешения."""
        self.config.set_permission(choice)

    def _start_bot(self):
        """
        Запуск бота.
        ПЕРЕД запуском — валидируем и сохраняем настройки самобаффа.
        Если валидация не прошла, бот НЕ стартует.
        """
        if not self._save_self_buff_settings():
            return  # Валидация провалилась — messagebox уже показан

        asyncio.run_coroutine_threadsafe(self.bot_core.start(), self.async_loop)
        self._update_status("Статус: Работает", "green")

    def _stop_bot(self):
        """Остановка бота."""
        asyncio.run_coroutine_threadsafe(self.bot_core.stop(), self.async_loop)
        self._update_status("Статус: Остановлен", "red")

    def _pause_bot(self):
        """Пауза бота."""
        asyncio.run_coroutine_threadsafe(self.bot_core.pause(), self.async_loop)
        self._update_status("Статус: Пауза", "orange")

    def _on_hotkey_change(self, row: int, col: int, action: str):
        """Мгновенное сохранение хоткея при выборе в комбобоксе."""
        self.config.save_hotkey(row, col, action)

    # ================================================================
    #  ОБРАБОТЧИКИ — КАЛИБРОВКА
    # ================================================================

    def _open_calibration(self, point_type: str):
        """Открытие полноэкранного оверлея для калибровки точки."""
        CalibrationOverlay(self, point_type, self._on_calibration_complete)

    def _on_calibration_complete(
        self, point_type: str, x: int, y: int, rgb: tuple
    ):
        """Callback от оверлея: сохраняем точку в конфиг."""
        self.config.save_calibration_point(point_type, x, y, rgb)
        self._update_status(
            f"Калибровка '{point_type}' сохранена: ({x}, {y}) RGB{rgb}",
            "cyan",
        )

    # ================================================================
    #  ЛОГИКА САМОБАФФА (ВАЛИДАЦИЯ И СОХРАНЕНИЕ)
    # ================================================================

    @staticmethod
    def _normalize_key(key: str) -> str:
        """
        Приводит введенную пользователем кнопку к каноническому виду.
        Например: 'f6' -> 'F6', 'num1' -> 'Num1', 'nUm/' -> 'Num/'.
        """
        k = key.strip()
        if not k:
            return ""
        
        lower_k = k.lower()
        # Обработка F-клавиш
        if lower_k.startswith('f') and k[1:].isdigit():
            return 'F' + k[1:]
        # Обработка Numpad
        if lower_k.startswith('num'):
            suffix = k[3:]
            return 'Num' + suffix
            
        return k

    def _parse_and_validate_hotkeys(self, text: str) -> Tuple[List[str], List[str]]:
        """
        Парсит строку с кнопками и валидирует их against VALID_KEYS.
        Возвращает кортеж: (список валидных кнопок, список невалидных кнопок).
        """
        if not text or not text.strip():
            return [], []

        raw_keys = [k.strip() for k in text.split(',') if k.strip()]
        
        valid_keys = []
        invalid_keys = []

        for key in raw_keys:
            normalized = self._normalize_key(key)
            if normalized in VALID_KEYS:
                valid_keys.append(normalized)
            else:
                invalid_keys.append(key)

        return valid_keys, invalid_keys

    def _save_self_buff_settings(self) -> bool:
        """
        Валидирует и сохраняет все три параметра самобаффа в ConfigManager.
        Возвращает True при успехе, False при ошибке валидации.
        """
        # 1. Валидация интервала
        raw_interval = self.buff_interval_var.get().strip()
        try:
            interval = int(raw_interval)
            if interval <= 0:
                raise ValueError("Интервал должен быть > 0")
        except ValueError:
            messagebox.showwarning(
                "Ошибка валидации",
                f"Поле «Интервал» должно содержать положительное целое число.\n"
                f"Получено: «{raw_interval}»",
            )
            return False

        # 2. Валидация кнопок
        raw_text = self.buff_hotkeys_var.get()
        valid_hotkeys, invalid_hotkeys = self._parse_and_validate_hotkeys(raw_text)

        # 3. Обработка невалидных кнопок (Мягкий откат)
        if invalid_hotkeys:
            messagebox.showwarning(
                "Найдены недопустимые кнопки",
                f"Следующие кнопки не существуют в L2 и были проигнорированы:\n"
                f"{', '.join(invalid_hotkeys)}\n\n"
                f"Доступны только 36 кнопок (см. подсказку ниже)."
            )
            # Переписываем текст в поле ввода, оставляя только валидные кнопки
            self.buff_hotkeys_var.set(", ".join(valid_hotkeys))

        # 4. Сохранение в ConfigManager
        enabled = self.self_buff_var.get()
        self.config.save_self_buff_settings(enabled, interval, valid_hotkeys)
        return True

    def _on_self_buff_toggle(self):
        """Обработчик переключения чекбокса — сразу сохраняем."""
        self._save_self_buff_settings()

    # ================================================================
    #  ПОТОКОБЕЗОПАСНОЕ ОБНОВЛЕНИЕ UI
    # ================================================================

    def _update_status(self, text: str, color: str):
        """
        Обновляет метку статуса.
        Безопасно вызывается из ЛЮБОГО потока: если вызов из фонового
        потока — перенаправляется в главный через root.after().
        """
        if threading.current_thread() is not threading.main_thread():
            self.after(0, self._update_status, text, color)
            return

        self.status_label.configure(text=text, text_color=color)

    # ================================================================
    #  ЖИЗНЕННЫЙ ЦИКЛ
    # ================================================================

    def _on_closing(self):
        """Корректное завершение: останавливаем event loop и закрываем окно."""
        self.async_loop.call_soon_threadsafe(self.async_loop.stop)
        self.async_thread.join(timeout=1.0)
        self.destroy()


# ================================================================
#  ТОЧКА ВХОДА
# ================================================================

if __name__ == "__main__":
    app = App()
    app.mainloop()  