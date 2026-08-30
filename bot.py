import time
import serial
import pyautogui
import configparser
import os
import ctypes
import sys
from pynput import keyboard  # Используем pynput для фонового отслеживания клавиш

# --- ЗАЩИТА ОТ DPI (МАСШТАБИРОВАНИЯ WINDOWS) ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try: ctypes.windll.user32.SetProcessDPIAware()
    except Exception: pass

# --- ЗАГРУЗКА КОНФИГУРАЦИИ ---
config_file = 'bot_config.ini'
if not os.path.exists(config_file):
    print(f"Ошибка: Файл {config_file} не найден! Сначала запустите get_points.py")
    exit()

config = configparser.ConfigParser()
config.read(config_file)

try:
    SERIAL_PORT = config['SETTINGS']['port']
    BAUD_RATE = int(config['SETTINGS']['baudrate'])
    
    HP_POINT = tuple(map(int, config['PIXELS']['hp_point'].split(',')))
    HP_COLOR = tuple(map(int, config['PIXELS']['hp_color'].split(',')))
    
    SKULL_POINT = tuple(map(int, config['PIXELS']['skull_point'].split(',')))
    SKULL_COLOR = tuple(map(int, config['PIXELS']['skull_color'].split(',')))
except Exception as e:
    print(f"Ошибка чтения файла конфигурации. Запустите get_points.py. Ошибка: {e}")
    exit()

# --- НАСТРОЙКИ ПОДКЛЮЧЕНИЯ ---
try:
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print(f"Успешно подключено к Arduino на порту {SERIAL_PORT}!")
except Exception as e:
    print(f"Ошибка подключения к Arduino: {e}")
    exit()

# --- ЛОГИКА ПАУЗЫ ---
IS_PAUSED = False  # Переменная состояния бота
PAUSE_KEY = keyboard.Key.f9  # Горячая клавиша паузы. Можно заменить, например, на keyboard.Key.pause

def on_press(key):
    global IS_PAUSED
    if key == PAUSE_KEY:
        IS_PAUSED = not IS_PAUSED
        if IS_PAUSED:
            print("\n" + "="*40)
            print("!!! БОТ ПОСТАВЛЕН НА ПАУЗУ !!!")
            print("="*40)
        else:
            print("\n" + "="*40)
            print(">>> БОТ СНЯТ С ПАУЗЫ. РАБОТАЕМ...")
            print("="*40)

# Запускаем фоновый поток прослушивания клавиатуры ПК
listener = keyboard.Listener(on_press=on_press)
listener.start()

def send_cmd(cmd: str):
    try:
        arduino.write(cmd.encode())
        arduino.flush()
    except Exception as e:
        print(f"Ошибка отправки команды {cmd}: {e}")

def color_match(current_color, target_color, tolerance=30):
    return all(abs(c - t) <= tolerance for c, t in zip(current_color, target_color))

def is_mob_alive():
    try:
        # Исправлен баг чтения точки (передаем координаты X и Y корректно)
        current_color = pyautogui.pixel(HP_POINT[0], HP_POINT[1])
        return color_match(current_color, HP_COLOR, tolerance=35)
    except Exception:
        return False

def is_mob_dead():
    try:
        current_color = pyautogui.pixel(SKULL_POINT[0], SKULL_POINT[1])
        return color_match(current_color, SKULL_COLOR, tolerance=35)
    except Exception:
        return False

# --- ОСНОВНОЙ ЦИКЛ БОТА ---
print("\nБот запущен [Режим: Пиксельный анализ].")
print(f"ГОРЯЧАЯ КЛАВИША ПАУЗЫ: [ F9 ] (работает из любого окна)")
print("Для полного закрытия нажмите Ctrl+C в этом окне.")
print("Переключитесь на окно игры. Старт через 3 секунды...")
time.sleep(3)

try:
    while True:
        # Если бот на паузе, просто циклично спим и ничего не делаем
        if IS_PAUSED:
            time.sleep(0.5)
            continue
            
        print("\n--- Шаг 1: Поиск моба ---")
        print("Отправка команды F2 (Поиск моба)...")
        send_cmd('2') 
        time.sleep(0.7)  
        
        # Проверяем паузу еще раз после задержки, чтобы мгновенно среагировать
        if IS_PAUSED: continue

        if is_mob_alive():
            print("[+] Моб найден (Цвет в точке HP совпал)! Начинаем атаку.")
            start_fight_time = time.time()
            missed_hp_count = 0
            
            while True:
                if IS_PAUSED:
                    break # Если нажали паузу во время боя, выходим из цикла атаки моба
                    
                elapsed_time = time.time() - start_fight_time
                if elapsed_time > 30.0:
                    print(f"[!] Тайм-аут! Моб не умер за {int(elapsed_time)} сек. Смена цели.")
                    break 
                
                print(f" -> Атака (F4)... Оставшееся время: {int(30 - elapsed_time)} сек.")
                send_cmd('4')
                time.sleep(1.2)  
                
                if IS_PAUSED: break
                
                # 1. Проверяем смерть по пикселю черепа
                if is_mob_dead():
                    print("[X] Моб мертв (Пиксель черепа зафиксирован). Следующая цель.")
                    break
                    
                # 2. Проверяем, на месте ли таргет
                if not is_mob_alive():
                    missed_hp_count += 1
                    if missed_hp_count >= 2:
                        print("[-] Полоса HP действительно пропала. Смена цели.")
                        break
                else:
                    missed_hp_count = 0
        else:
            print("[-] В точке HP пусто. Пробуем снова...")
            time.sleep(0.3)

except KeyboardInterrupt:
    print("\nБот успешно остановлен.")
    listener.stop() # Намного чище закрываем поток клавиатуры
    arduino.close()
    sys.exit()
