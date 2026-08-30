import time
import pyautogui
import configparser
import ctypes

# Фикс масштабирования Windows
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try: ctypes.windll.user32.SetProcessDPIAware()
    except Exception: pass

config = configparser.ConfigParser()
config_file = 'bot_config.ini'
config.read(config_file)

if 'SETTINGS' not in config:
    config['SETTINGS'] = {'port': 'COM4', 'baudrate': '115200'}
if 'PIXELS' not in config:
    config['PIXELS'] = {}

print("=== НАСТРОЙКА ТОЧЕК БОТА ===")
print("Инструкция:")
print("1. Переключитесь на игру.")
print("2. Выделите живого моба с ПОЛНЫМ ХП.")
print("3. Наведите курсор мыши на САМЫЙ ЛЕВЫЙ КРАЙ красной полосы HP.")
print("4. Подождите 5 секунд, скрипт считает точку...")

time.sleep(5)
x_hp, y_hp = pyautogui.position()
color_hp = pyautogui.pixel(x_hp, y_hp)
config['PIXELS']['hp_point'] = f"{x_hp},{y_hp}"
config['PIXELS']['hp_color'] = f"{color_hp[0]},{color_hp[1]},{color_hp[2]}"
print(f"[+] Успешно зафиксирована точка HP: Координаты ({x_hp}, {y_hp}), Цвет RGB {color_hp}")

print("\n--------------------------------------------------")
print("Теперь шаг 2:")
print("1. Убейте этого моба (или найдите мертвого).")
print("2. Наведите мышку прямо на КРАСНУЮ ОКАНТОВКУ ЧЕРЕПА мёртвого моба.")
print("3. Подождите 5 секунд, скрипт считает точку...")

time.sleep(10)
x_sk, y_sk = pyautogui.position()
color_sk = pyautogui.pixel(x_sk, y_sk)
config['PIXELS']['skull_point'] = f"{x_sk},{y_sk}"
config['PIXELS']['skull_color'] = f"{color_sk[0]},{color_sk[1]},{color_sk[2]}"
print(f"[+] Успешно зафиксирована точка Черепа: Координаты ({x_sk}, {y_sk}), Цвет RGB {color_sk}")

with open(config_file, 'w') as f:
    config.write(f)

print("\n[!] Все настройки успешно сохранены в bot_config.ini. Теперь картинки-шаблоны больше НЕ НУЖНЫ!")
