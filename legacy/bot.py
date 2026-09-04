import time
import serial
import pyautogui
import configparser
import os
import ctypes
import sys
from datetime import datetime
from pynput import keyboard

# Импортируем микросервис статистики
from stats_manager import BotStatistics

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ И НАСТРОЙКИ ---
SCREENSHOTS_DIR = 'screenshots'
IS_PAUSED = False
PAUSE_KEY = keyboard.Key.f9
stats = BotStatistics()  # Инициализируем внешний сервис статистики

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try: ctypes.windll.user32.SetProcessDPIAware()
    except Exception: pass

def take_screenshot(filename: str):
    try:
        if not os.path.exists(SCREENSHOTS_DIR):
            os.makedirs(SCREENSHOTS_DIR)
        path = os.path.join(SCREENSHOTS_DIR, filename)
        pyautogui.screenshot(path)
    except Exception as e:
        print(f"\n[!] Не удалось сделать скриншот {filename}: {e}")

def color_match(current_color, target_color, tolerance=30):
    return all(abs(c - t) <= tolerance for c, t in zip(current_color, target_color))

def on_press(key):
    global IS_PAUSED
    if key == PAUSE_KEY:
        IS_PAUSED = not IS_PAUSED
        if IS_PAUSED:
            print("\n========================================\n!!! БОТ ПОСТАВЛЕН НА ПАУЗУ !!!\n========================================")
        else:
            print("\n========================================\n>>> БОТ СНЯТ С ПАУЗЫ. РАБОТАЕМ...\n========================================")

def main():
    global IS_PAUSED
    
    config_file = 'bot_config.ini'
    if not os.path.exists(config_file):
        print(f"Ошибка: Файл {config_file} не найден! Сначала запустите get_points.py")
        sys.exit()

    config = configparser.ConfigParser()
    config.read(config_file)

    try:
        SERIAL_PORT = config['SETTINGS']['port']
        BAUD_RATE = int(config['SETTINGS']['baudrate'])
        PROFILE = int(config['SETTINGS']['profile'])
        
        HP_POINT = tuple(map(int, config['PIXELS']['hp_point'].split(',')))
        HP_COLOR = tuple(map(int, config['PIXELS']['hp_color'].split(',')))
        
        SKULL_POINT = tuple(map(int, config['PIXELS']['skull_point'].split(',')))
        SKULL_COLOR = tuple(map(int, config['PIXELS']['skull_color'].split(',')))
        
        if PROFILE == 2:
            MP_LOW_POINT = tuple(map(int, config['PIXELS']['mp_low_point'].split(',')))
            MP_LOW_COLOR = tuple(map(int, config['PIXELS']['mp_low_color'].split(',')))
            MP_FULL_POINT = tuple(map(int, config['PIXELS']['mp_full_point'].split(',')))
            MP_FULL_COLOR = tuple(map(int, config['PIXELS']['mp_full_color'].split(',')))
    except Exception as e:
        print(f"Ошибка чтения конфигурации. Запустите get_points.py. Ошибка: {e}")
        sys.exit()

    try:
        arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        print(f"Успешно подключено к Arduino на порту {SERIAL_PORT}!")
    except Exception as e:
        print(f"Ошибка подключения к Arduino на {SERIAL_PORT}: {e}")
        sys.exit()

    def send_cmd(cmd: str):
        try:
            arduino.write(cmd.encode())
            arduino.flush()
        except Exception as err:
            print(f"\nОшибка отправки команды {cmd}: {err}")

    def is_mob_alive():
        try:
            current_color = pyautogui.pixel(HP_POINT[0], HP_POINT[1])
            return color_match(current_color, HP_COLOR, tolerance=35)
        except Exception: 
            return False

    def is_mob_dead():
        try:
            current_color = pyautogui.pixel(SKULL_POINT[0], SKULL_POINT[1])
            # Возвращаем твой оригинальный точный метод сравнения цветов из стабильной версии!
            return color_match(current_color, SKULL_COLOR, tolerance=35)
        except Exception: 
            return False

    def is_mp_low():
        if PROFILE == 1: return False
        try:
            current_color = pyautogui.pixel(MP_LOW_POINT[0], MP_LOW_POINT[1])
            return not color_match(current_color, MP_LOW_COLOR, tolerance=35)
        except Exception: 
            return False

    def is_mp_full():
        if PROFILE == 1: return True
        try:
            current_color = pyautogui.pixel(MP_FULL_POINT[0], MP_FULL_POINT[1])
            return color_match(current_color, MP_FULL_COLOR, tolerance=35)
        except Exception: 
            return False

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    print(f"\nБот запущен. Профиль: [{'Милик' if PROFILE == 1 else 'Маг'}]")
    print("Сохраняю стартовый скриншот...")
    take_screenshot("start.png")

    time.sleep(2)
    
    last_minute_time = time.time()
    last_hour_time = time.time()

    try:
        while True:
            if IS_PAUSED:
                time.sleep(0.5)
                continue
                
            current_time = time.time()
            if current_time - last_minute_time >= 60.0:
                take_screenshot("current_minute.png")
                last_minute_time = current_time
                
            if current_time - last_hour_time >= 3600.0:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                take_screenshot(f"hourly_{timestamp}.png")
                last_hour_time = current_time
            
            # --- ЛОГИКА КОНТРОЛЯ МАНЫ ---
            if PROFILE == 2 and is_mp_low():
                print("\n[!] Мана упала ниже порога. Садимся отдыхать (Жмем F1)...")
                send_cmd('1')
                start_rest_time = time.time()
                
                while not is_mp_full():
                    if IS_PAUSED:
                        time.sleep(0.5)
                        continue
                    print("\r[~] Регенерируем ману...", end="")
                    sys.stdout.flush()
                    time.sleep(1.0)
                
                rest_duration = time.time() - start_rest_time
                print("\n[+] Мана восстановлена! Встаем (Жмем F1).")
                send_cmd('1')
                stats.add_rest(rest_duration)
                time.sleep(.2)

            print("\n--- Шаг 1: Поиск моба ---")
            send_cmd('2')
            time.sleep(0.7)
            
            if IS_PAUSED: continue

            if is_mob_alive():
                print("[+] Моб найден! Начинаем атаку.")
                start_fight_time = time.time()
                missed_hp_count = 0
                
                while True:
                    if IS_PAUSED: break
                        
                    elapsed_time = time.time() - start_fight_time
                    if elapsed_time > 30.0:
                        print(f"\n[!] Тайм-аут! Смена цели.")
                        stats.add_timeout(elapsed_time)
                        stats.print_report(PROFILE)
                        break 
                    
                    print(f"\r -> Атака (F4)... Оставшееся время: {int(30 - elapsed_time)} сек.   ", end="")
                    sys.stdout.flush()
                    
                    send_cmd('4')
                    time.sleep(.2)
                    
                    if IS_PAUSED: break
                    
                    # И ВСЁ! Проверяем только одну точку HP с защитой от мигания
                    if not is_mob_alive():
                        missed_hp_count += 1
                        if missed_hp_count >= 2:  # Достаточно 2 проверок, чтобы мгновенно сорваться к новому мобу
                            fight_duration = time.time() - start_fight_time
                            print()
                            print(f"[X] Цель мертва или пропала! Время боя: {fight_duration:.1f} сек.")
                            stats.add_mob(fight_duration)  # Пишем в общую статистику
                            stats.print_report(PROFILE)
                            break
                    else:
                        missed_hp_count = 0


    except KeyboardInterrupt:
        print("\n\nБот остановлен пользователем. Сохраняю финальный скриншот...")
        take_screenshot("stop.png")
        listener.stop()
        arduino.close()
        sys.exit()

if __name__ == "__main__":
    main()
