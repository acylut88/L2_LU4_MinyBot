import json
from pathlib import Path
from typing import Any, Dict

# --- КОНСТАНТЫ МОДУЛЯ ---

# Все 36 валидных хоткеев L2 (3 линии по 12 кнопок).
# Используется set внутри методов для O(1) проверки, но хранится как list для сохранения порядка.
ALL_VALID_HOTKEYS: list[str] = [
    "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=",
    "Num1", "Num2", "Num3", "Num4", "Num5", "Num6", "Num7", "Num8", "Num9", "Num0", "Num/", "Num*"
]


class ConfigManager:
    """Менеджер конфигурации для бота Lineage 2 с поддержкой профилей и разрешений."""
    
    DEFAULT_CONFIG: Dict[str, Any] = {
        "global_settings": {
            "arduino_port": "COM3",
            "mss_tick_rate_ms": 50
        },
        "active_user": "Default_User",
        "users": {
            "Default_User": {
                "active_resolution": "1920x1080",
                "hotkeys": {
                    "attack": "F1",
                    "heal": "F2",
                    "buff": "F3"
                },
                "logic": {
                    "has_pet": False,
                    "auto_loot": True,
                    "use_potions": True
                },
                "self_buff": {
                    "enabled": False,
                    "interval_minutes": 15,
                    "hotkeys": []
                },
                "resolutions": {
                    "1920x1080": {
                        "pixels": {
                            "hp_bar": {"x": 150, "y": 45, "color": "#FF0000"},
                            "mp_bar": {"x": 150, "y": 65, "color": "#0000FF"}
                        }
                    }
                }
            }
        }
    }

    def __init__(self, config_path: str | Path = "config.json"):
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Загружает конфиг. Если файл отсутствует или поврежден, создает дефолтный."""
        if not self.config_path.exists():
            self._config = self.DEFAULT_CONFIG.copy()
            self.save()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
            self._validate_structure()
        except (json.JSONDecodeError, KeyError, TypeError):
            # Резервное копирование битого конфига и сброс к дефолтному
            backup_path = self.config_path.with_suffix(".json.bak")
            self.config_path.rename(backup_path)
            self._config = self.DEFAULT_CONFIG.copy()
            self.save()

    def _validate_structure(self) -> None:
        """Базовая проверка наличия ключевых разделов."""
        required_keys = ["global_settings", "active_user", "users"]
        if not all(key in self._config for key in required_keys):
            raise ValueError("Invalid config structure")
        
        active = self._config["active_user"]
        if active not in self._config["users"]:
            self._config["active_user"] = list(self._config["users"].keys())[0]

    def save(self) -> None:
        """Сохраняет текущее состояние конфигурации в файл."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=4, ensure_ascii=False)

    def get_active_user(self) -> str:
        """Возвращает имя текущего активного пользователя."""
        return self._config["active_user"]

    def switch_user(self, username: str) -> None:
        """Переключает активный профиль пользователя."""
        if username not in self._config["users"]:
            raise ValueError(f"Пользователь '{username}' не найден в конфигурации.")
        self._config["active_user"] = username
        self.save()

    def _get_current_user_data(self) -> Dict[str, Any]:
        """Вспомогательный метод: возвращает данные активного пользователя."""
        return self._config["users"][self._config["active_user"]]

    def _hex_to_rgb(self, hex_color: str) -> tuple[int, int, int]:
        """Конвертирует HEX-строку (#RRGGBB) в RGB-кортеж."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def get_pixel_coords(self, pixel_name: str) -> dict[str, int | tuple[int, int, int]]:
        """
        Возвращает координаты и цвет (в виде RGB-кортежа) пикселя 
        для текущего юзера и его активного разрешения.
        """
        user_data = self._get_current_user_data()
        resolution = user_data["active_resolution"]
        pixels = user_data["resolutions"][resolution]["pixels"]
        
        if pixel_name not in pixels:
            raise KeyError(f"Пиксель '{pixel_name}' не найден для разрешения {resolution}.")
        
        # Копируем словарь, чтобы не мутировать исходные данные конфига
        pixel_data = pixels[pixel_name].copy()
        pixel_data["color"] = self._hex_to_rgb(pixel_data["color"])
        return pixel_data

    def get_hotkey(self, action_name: str) -> str:
        """Возвращает название клавиши для указанного действия текущего пользователя."""
        hotkeys = self._get_current_user_data()["hotkeys"]
        if action_name not in hotkeys:
            raise KeyError(f"Хоткей для действия '{action_name}' не найден.")
        return hotkeys[action_name]

    def get_logic_settings(self) -> Dict[str, bool]:
        """Возвращает словарь булевых флагов логики текущего пользователя."""
        return self._get_current_user_data()["logic"]

    def set_active_resolution(self, resolution: str) -> None:
        """Устанавливает активное разрешение для текущего пользователя."""
        user_data = self._get_current_user_data()
        if resolution not in user_data["resolutions"]:
            raise ValueError(f"Разрешение '{resolution}' не настроено для этого пользователя.")
        user_data["active_resolution"] = resolution
        self.save()

    def get_global_settings(self) -> Dict[str, Any]:
        """Возвращает словарь глобальных настроек."""
        return self._config.get("global_settings", {})

    def get_users(self) -> Dict[str, Any]:
        """Возвращает словарь всех пользователей."""
        return self._config.get("users", {})

    def get_self_buff_settings(self) -> dict[str, bool | int | list[str]]:
        """
        Возвращает настройки самобаффа для текущего пользователя.
        При чтении автоматически валидирует список хоткеев, удаляя невалидные.
        """
        user_data = self._get_current_user_data()
        
        # Инициализация секции, если её еще нет в конфиге (защита от KeyError)
        if "self_buff" not in user_data:
            user_data["self_buff"] = {
                "enabled": False,
                "interval_minutes": 15,
                "hotkeys": []
            }
            self.save()
            
        settings = user_data["self_buff"]
        raw_hotkeys = settings.get("hotkeys", [])
        
        if not isinstance(raw_hotkeys, list):
            raw_hotkeys = []

        # Валидация списка хоткеев. Оставляем только те, что есть в ALL_VALID_HOTKEYS.
        valid_keys_set = set(ALL_VALID_HOTKEYS)
        valid_hotkeys = []
        for key in raw_hotkeys:
            # Проверяем валидность и отсутствие дублей
            if key in valid_keys_set and key not in valid_hotkeys:
                valid_hotkeys.append(key)

        # Если после валидации список изменился, обновляем данные и сохраняем конфиг
        if valid_hotkeys != raw_hotkeys:
            settings["hotkeys"] = valid_hotkeys
            self.save()

        return {
            "enabled": bool(settings.get("enabled", False)),
            "interval_minutes": int(settings.get("interval_minutes", 15)),
            "hotkeys": valid_hotkeys
        }

    def set_self_buff_settings(self, enabled: bool, interval_minutes: int, hotkeys: list[str]) -> None:
        """
        Обновляет и сохраняет настройки самобаффа для текущего пользователя.
        Валидирует список хоткеев перед сохранением.
        """
        user_data = self._get_current_user_data()
        
        # Валидация хоткеев перед сохранением
        valid_keys_set = set(ALL_VALID_HOTKEYS)
        valid_hotkeys = []
        for key in hotkeys:
            if key in valid_keys_set and key not in valid_hotkeys:
                valid_hotkeys.append(key)

        user_data["self_buff"] = {
            "enabled": bool(enabled),
            "interval_minutes": int(interval_minutes),
            "hotkeys": valid_hotkeys
        }
        self.save()