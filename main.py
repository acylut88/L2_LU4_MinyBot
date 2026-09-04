import argparse
import asyncio
import logging
import sys
from pathlib import Path
from pynput import keyboard

# ==============================================================================
# Настройка логирования
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ==============================================================================
# Внутренние импорты проекта
# ==============================================================================
from core.config_manager import ConfigManager
from core.hardware_manager import HardwareManager
from core.vision_manager import VisionManager
from core.async_tasks import BotCore

# Глобальная ссылка на экземпляр BotCore для обработчика хоткеев
_bot_core_instance = None

# ==============================================================================
# Глобальный хоткей (F9)
# ==============================================================================
def on_press(key):
    global _bot_core_instance
    try:
        if key == keyboard.Key.f9:
            logger.info("🔥 Глобальный хоткей F9 нажат! Переключение паузы...")
            if _bot_core_instance is not None:
                # Вызов toggle_pause() безопасен из другого потока, 
                # так как внутри он просто меняет состояние asyncio.Event (event.set()/clear())
                _bot_core_instance.toggle_pause()
    except AttributeError:
        pass

# ==============================================================================
# Headless режим
# ==============================================================================
async def run_headless(config_path: Path):
    global _bot_core_instance
    
    logger.info("🚀 Инициализация компонентов в headless-режиме...")
    
    # 1. Инициализация в правильном порядке
    config_manager = ConfigManager(config_path)
    config_manager.load()
    
    logger.info("⚙️ Подключение к Arduino (HardwareManager)...")
    hardware_manager = HardwareManager(config_manager)
    await hardware_manager.start()
    
    vision_manager = VisionManager()
    
    _bot_core_instance = BotCore(config_manager, hardware_manager, vision_manager)
    
    # 2. Запуск слушателя клавиатуры в отдельном потоке
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    logger.info("⌨️ Слушатель глобальных хоткеев запущен (F9 - пауза/старт).")
    
    try:
        # 3. Запуск основной логики бота
        logger.info("▶️ Запуск BotCore...")
        await _bot_core_instance.start()
        
        # Поддерживаем работу event loop, если start() не является бесконечным циклом сам по себе
        while True:
            await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        logger.info("⚠️ Задача BotCore была отменена.")
    except KeyboardInterrupt:
        logger.info("🛑 Получен сигнал KeyboardInterrupt (Ctrl+C).")
    finally:
        # 4. Корректное завершение (Graceful Shutdown)
        logger.info("🔄 Инициализация корректного завершения (Graceful Shutdown)...")
        
        listener.stop()
        logger.info("✅ Слушатель клавиатуры остановлен.")
        
        if _bot_core_instance is not None:
            await _bot_core_instance.stop()
            logger.info("✅ BotCore остановлен, задачи отменены.")
            
        await hardware_manager.stop()
        logger.info("✅ COM-порт Arduino закрыт, ресурсы освобождены.")
        
        logger.info("🏁 Работа бота успешно завершена.")

# ==============================================================================
# UI режим (по умолчанию)
# ==============================================================================
def run_ui(config_path: Path):
    global _bot_core_instance
    from ui.app import App
    
    logger.info("🚀 Инициализация компонентов для UI-режима...")
    
    # 1. Инициализация в правильном порядке
    config_manager = ConfigManager(config_path)
    config_manager.load()
    
    hardware_manager = HardwareManager(config_manager)
    # Примечание: UI может сам вызывать hardware_manager.start() при подключении, 
    # но мы передаем проинициализированный экземпляр для согласованности
    
    vision_manager = VisionManager()
    _bot_core_instance = BotCore(config_manager, hardware_manager, vision_manager)
    
    # 2. Запуск слушателя клавиатуры (работает параллельно с mainloop Tkinter)
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    logger.info("⌨️ Слушатель глобальных хоткеев запущен (F9 - пауза/старт).")
    
    try:
        # 3. Запуск графического интерфейса
        # App сам запустит BotCore в фоновом потоке и будет управлять его жизненным циклом
        app = App()
        app.run()
    except KeyboardInterrupt:
        logger.info("🛑 Получен сигнал KeyboardInterrupt в UI-режиме.")
    finally:
        # 4. Корректное завершение
        listener.stop()
        logger.info("✅ Слушатель клавиатуры остановлен. Завершение UI-режима.")
        # Примечание: App/BotCore должны сами вызывать hardware_manager.stop() при закрытии окна,
        # но если нет, это можно продублировать здесь через asyncio.run(hardware_manager.stop())

# ==============================================================================
# Точка входа
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Lineage 2 LU4 Async Bot")
    parser.add_argument(
        '--headless', 
        action='store_true', 
        help='Запуск без графического интерфейса (только консоль и логика)'
    )
    parser.add_argument(
        '--config', 
        type=str, 
        default='config.json', 
        help='Путь к файлу конфигурации (по умолчанию: config.json)'
    )
    
    args = parser.parse_args()
    config_path = Path(args.config)
    
    if not config_path.exists():
        logger.warning(f"⚠️ Файл конфигурации не найден по пути: {config_path}. Убедитесь, что он существует.")
    
    if args.headless:
        try:
            asyncio.run(run_headless(config_path))
        except KeyboardInterrupt:
            logger.info("🛑 Завершение работы по инициативе пользователя.")
    else:
        run_ui(config_path)

if __name__ == "__main__":
    main()