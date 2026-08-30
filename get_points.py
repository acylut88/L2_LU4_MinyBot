import time
import pyautogui
import configparser
import ctypes

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try: ctypes.windll.user32.SetProcessDPIAware()
    except Exception: pass

config = configparser.ConfigParser()
config.read('bot_config.ini')

if 'SETTINGS' not in config:
    config['SETTINGS'] = {'port': 'COM4', 'baudrate': '115200', 'profile': '1'}
if 'PIXELS' not in config:
    config['PIXELS'] = {}

print("=== КАЛИБРОВКА БОТА ВЕРСИЯ 1.1 ===")
print("Выберите профиль работы бота:")
print("1 - Милик (без учета маны)")
print("2 - Маг (с контролем MP и регенерацией)")
choice = input("Введите цифру 1 или 2: ").strip()

if choice not in ['1', '2']:
    print("Неверный ввод, по умолчанию выбран Милик (1).")
    choice = '1'

config['SETTINGS']['profile'] = choice

print("\n--- Шаг 1: Точка HP моба ---")
print("1. Переключитесь на игру. Выделите живого моба с ПОЛНЫМ ХП.")
print("2. Наведите мышку на САМЫЙ ЛЕВЫЙ КРАЙ красной полосы HP.")
print("3. Держите мышку, через 5 секунд скрипт считает точку...")
time.sleep(5)
x_hp, y_hp = pyautogui.position()
color_hp = pyautogui.pixel(x_hp, y_hp)
config['PIXELS']['hp_point'] = f"{x_hp},{y_hp}"
config['PIXELS']['hp_color'] = f"{color_hp[0]},{color_hp[1]},{color_hp[2]}"
print(f"[+] Зафиксировано HP: Координаты ({x_hp}, {y_hp}), Цвет RGB {color_hp}")

print("\n--- Шаг 2: Точка Черепа ---")
print("1. Наведите мышку на КРАСНУЮ ОКАНТОВКУ ЧЕРЕПА мёртвого моба.")
print("2. Держите мышку 10 секунд...")
time.sleep(10)
x_sk, y_sk = pyautogui.position()
color_sk = pyautogui.pixel(x_sk, y_sk)
config['PIXELS']['skull_point'] = f"{x_sk},{y_sk}"
config['PIXELS']['skull_color'] = f"{color_sk[0]},{color_sk[1]},{color_sk[2]}"
print(f"[+] Зафиксирован Череп: Координаты ({x_sk}, {y_sk}), Цвет RGB {color_sk}")

# Если выбран профиль Мага — калибруем MP
if choice == '2':
    print("\n--- Шаг 3: Минимальное MP (Порог посадки) ---")
    print("1. Посмотрите на свою синюю полоску MP.")
    print("2. Наведите мышку на точку (например, на 20-30% маны), ниже которой персонаж должен сесть отдыхать.")
    print("3. Держите мышку 5 секунд...")
    time.sleep(5)
    x_mp1, y_mp1 = pyautogui.position()
    color_mp1 = pyautogui.pixel(x_mp1, y_mp1)
    config['PIXELS']['mp_low_point'] = f"{x_mp1},{y_mp1}"
    config['PIXELS']['mp_low_color'] = f"{color_mp1[0]},{color_mp1[1]},{color_mp1[2]}"
    print(f"[+] Зафиксировано минимальное MP: ({x_mp1}, {y_mp1}), Цвет RGB {color_mp1}")

    print("\n--- Шаг 4: Максимальное MP (Порог подъема) ---")
    print("1. Наведите мышку на точку ближе к концу полоски MP (например, 90-95%), при заполнении которой бот встанет.")
    print("2. Держите мышку 5 секунд...")
    time.sleep(5)
    x_mp2, y_mp2 = pyautogui.position()
    color_mp2 = pyautogui.pixel(x_mp2, y_mp2)
    config['PIXELS']['mp_full_point'] = f"{x_mp2},{y_mp2}"
    config['PIXELS']['mp_full_color'] = f"{color_mp2[0]},{color_mp2[1]},{color_mp2[2]}"
    print(f"[+] Зафиксировано максимальное MP: ({x_mp2}, {y_mp2}), Цвет RGB {color_mp2}")

with open('bot_config.ini', 'w') as f:
    config.write(f)

print("\n[!] Все настройки версии 1.1 успешно сохранены в bot_config.ini!")
