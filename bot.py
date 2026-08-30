import time
import serial
import pyautogui
import configparser
import os
import ctypes
import sys
from datetime import datetime
from pynput import keyboard

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ И НАСТРОЙКИ ---
SCREENSHOTS_DIR = 'screenshots'
IS_PAUSED = False
PAUSE_KEY = keyboard.Key.f9

# Включаем принудительный фикс масштабирования Windows (DPI)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

def take_screenshot(filename: str):
    """Делает скриншот экрана и сохраняет его в изолированную папку"""
    try:
        if not os.path.exists(SCREENSHOTS_DIR):
            os.makedirs(SCREENSHOTS_DIR)
        path = os.path.join(SCREENSHOTS_DIR, filename)
        pyautogui.screenshot(path)
    except Exception as e:
        print(f"\n[!] Не удалось сделать скриншот {filename}: {e}")

def color_match(current_color, target_color, tolerance=30):
    """Проверяет совпадение RGB цветов с учетом допустимой погрешности"""
    return all(abs(c - t) <= tolerance for c, t in zip(current_color, target_color))

def on_press(key):
    """Глобальный обработчик нажатия горячей клавиши паузы"""
    global IS_PAUSED
    if key == PAUSE_KEY:
        IS_PAUSED = not IS_PAUSED
        if IS_PAUSED:
            print("\n" + "=" * 40)
            print("!!! БОТ ПОСТАВЛЕН НА ПАУЗУ !!!")
            print("=" * 40)
        else:
            print("\n" + "=" * 40)
            print(">>> БОТ СНЯТ С ПАУЗЫ. РАБОТАЕМ...")
            print("=" * 40)

def main():
    global IS_PAUSED
    
    # --- ЗАГРУЗКА КОНФИГУРАЦИИ ---
    config_file = 'bot_config.ini'
    if not os.path.exists(config_file):
        print(f"Ошибка: Файл {config_file} не найден! Сначала запустите get_points.py")
        sys.exit()

    config = configparser.ConfigParser()
    config.read(config_file)

    try:
        SERIAL_PORT = config['SETTINGS']['port']
        BAUD_RATE = int(config['SETTINGS']['baudrate'])
        PROFILE = int(config['SETTINGS']['profile'])  # 1 - Милик, 2 - Маг
        
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

    # --- НАСТРОЙКИ ПОДКЛЮЧЕНИЯ К ARDUINO ---
    try:
        arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # Ожидание инициализации COM-дескрипторов
        print(f"Успешно подключено к Arduino на порту {SERIAL_PORT}!")
    except Exception as e:
        print(f"Ошибка подключения к Arduino на {SERIAL_PORT}: {e}")
        sys.exit()

    # Вспомогательные функции внутри main для быстрого доступа к переменным конфигурации
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
        except Exception: return False

    def is_mob_dead():
        try:
            current_color = pyautogui.pixel(SKULL_POINT[0], SKULL_POINT[1])
            return color_match(current_color, SKULL_COLOR, tolerance=35)
        except Exception: return False

    def is_mp_low():
        if PROFILE == 1: return False
        try:
            current_color = pyautogui.pixel(MP_LOW_POINT[0], MP_LOW_POINT[1])
            return not color_match(current_color, MP_LOW_COLOR, tolerance=35)
        except Exception: return False

    def is_mp_full():
        if PROFILE == 1: return True
        try:
            current_color = pyautogui.pixel(MP_FULL_POINT[0], MP_FULL_POINT[1])
            return color_match(current_color, MP_FULL_COLOR, tolerance=35)
        except Exception: return False

    # Запускаем фоновый поток прослушивания клавиатуры ПК для паузы
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    print(f"\nБот успешно запущен. Профиль: [{'Милик' if PROFILE == 1 else 'Маг'}].")
    print("Для переключения паузы нажмите [ F9 ]. Для полного выхода: Ctrl+C")
    print("Сохраняю стартовый скриншот...")
    take_screenshot("start.png")

    time.sleep(2)
    
    # Переменные таймеров для таймлапса скриншотов
    last_minute_time = time.time()
    last_hour_time = time.time()

    try:
        while True:
            if IS_PAUSED:
                time.sleep(0.5)
                continue
                
            # --- ЛОГИКА ТАЙМЛАПСА СКРИНШОТОВ ---
            current_time = time.time()
            
            # Раз в минуту (перезаписывается)
            if current_time - last_minute_time >= 60.0:
                take_screenshot("current_minute.png")
                last_minute_time = current_time
                print("\n[Таймлапс] Минутный скриншот обновлен.")
                
            # Раз в час (уникальные архивные файлы)
            if current_time - last_hour_time >= 3600.0:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                take_screenshot(f"hourly_{timestamp}.png")
                last_hour_time = current_time
                print(f"\n[Таймлапс] Создан часовой архивный скриншот: hourly_{timestamp}.png")
            
            # --- ЛОГИКА КОНТРОЛЯ МАНЫ ---
            if PROFILE == 2 and is_mp_low():
                print("\n[!] Мана упала ниже критического порога. Садимся отдыхать (Жмем F1)...")
                send_cmd('1')  # Посадка
                
                while not is_mp_full():
                    if IS_PAUSED:
                        time.sleep(0.5)
                        continue
                    print("\r[~] Регенерируем ману... Проверка состояния пикселя...", end="")
                    sys.stdout.flush()
                    time.sleep(1.0)
                    
                print("\n[+] Мана полностью восстановилась! Встаем (Жмем F1) и продолжаем охоту.")
                send_cmd('1')  # Подъем
                time.sleep(1.2)  # Пауза на анимацию подъема

            # --- ОСНОВНОЙ БОЕВОЙ ЦИКЛ ---
            print("\n--- Шаг 1: Поиск моба ---")
            send_cmd('2')  # Поиск (F2) через Ардуино (удержание 500мс)
            time.sleep(0.7)  
            
            if IS_PAUSED: continue

            if is_mob_alive():
                print("[+] Моб найден! Красная полоса зафиксирована. Начинаем атаку.")
                start_fight_time = time.time()
                missed_hp_count = 0
                
                while True:
                    if IS_PAUSED: 
                        print()  # Корректный перенос строки при активации паузы
                        break
                        
                    elapsed_time = time.time() - start_fight_time
                    if elapsed_time > 30.0:
                        print(f"\n[!] Тайм-аут! Моб не умер за {int(elapsed_time)} сек. Смена цели.")
                        break 
                    
                    # Динамический вывод в одну строку без спама
                    time_left = int(30 - elapsed_time)
                    print(f"\r -> Атака (F4)... Оставшееся время таймаута: {time_left} сек.   ", end="")
                    sys.stdout.flush()
                    
                    send_cmd('4')  # Атака (F4)
                    time.sleep(1.2)  
                    
                    if IS_PAUSED: 
                        print()
                        break
                    
                    # 1. Проверяем смерть моба по пикселю Черепа
                    if is_mob_dead():
                        print()  # Сдвигаем каретку на новую строку перед основным логом
                        print("[X] Моб мертв (череп найден). Переходим к следующему.")
                        break
                        
                    # 2. Проверяем, на месте ли таргет (двойная проверка от мигания интерфейса)
                    if not is_mob_alive():
                        missed_hp_count += 1
                        if missed_hp_count >= 2:
                            print()  # Сдвигаем каретку на новую строку перед основным логом
                            print("[-] Полоса HP действительно пропала. Смена цели.")
                            break
                    else:
                        missed_hp_count = 0
            else:
                print("[-] В точке HP пусто. Пробуем снова...")
                time.sleep(0.3)

    except KeyboardInterrupt:
        print("\n\nБот остановлен пользователем. Сохраняю финальный скриншот...")
        take_screenshot("stop.png")
        listener.stop()
        arduino.close()
        sys.exit()

if __name__ == "__main__":
    main()
