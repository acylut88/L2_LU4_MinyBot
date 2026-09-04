import asyncio
import logging
from typing import Optional

import serial
import win32gui
import win32con

from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class HardwareManager:
    """
    Асинхронный менеджер для взаимодействия с Arduino (через Serial) 
    и окнами Windows (через pywin32).
    """

    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        
        # Читаем настройки из global_settings
        # Предполагаем, что ConfigManager имеет метод get_global_settings() или аналогичный доступ
        global_settings = self.config.get_global_settings() if hasattr(self.config, 'get_global_settings') else self.config.config_data.get('global_settings', {})
        
        self.port_name: str = global_settings.get("arduino_port", "COM3")
        self.baudrate: int = global_settings.get("baudrate", 115200)
        
        self.serial_conn: Optional[serial.Serial] = None
        self._init_serial()
        
        # Очередь команд и блокировка для эксклюзивного доступа
        self.command_queue: asyncio.Queue = asyncio.Queue()
        self.lock: asyncio.Lock = asyncio.Lock()
        
        self._worker_task: Optional[asyncio.Task] = None
        self._is_running: bool = False

    def _init_serial(self):
        """Инициализация COM-порта."""
        try:
            self.serial_conn = serial.Serial(
                port=self.port_name,
                baudrate=self.baudrate,
                timeout=1
            )
            logger.info(f"Serial port {self.port_name} успешно открыт.")
        except serial.SerialException as e:
            logger.error(f"Не удалось открыть COM-порт {self.port_name}: {e}")
            self.serial_conn = None

    async def _reconnect_serial(self):
        """Логика переподключения Arduino с экспоненциальной задержкой."""
        delay = 1
        max_delay = 30
        
        while self._is_running and (self.serial_conn is None or not self.serial_conn.is_open):
            logger.info(f"Попытка переподключения к {self.port_name} через {delay} сек...")
            await asyncio.sleep(delay)
            try:
                self.serial_conn = serial.Serial(
                    port=self.port_name,
                    baudrate=self.baudrate,
                    timeout=1
                )
                logger.info(f"Arduino успешно переподключена к {self.port_name}.")
                return
            except serial.SerialException:
                delay = min(delay * 2, max_delay)

    def _focus_window(self, window_title: str) -> bool:
        """
        Синхронный метод для поиска и вывода окна на передний план.
        """
        try:
            hwnd = win32gui.FindWindow(None, window_title)
            if not hwnd:
                logger.warning(f"Окно с заголовком '{window_title}' не найдено.")
                return False
            
            # Если окно свернуто, разворачиваем его
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            # Выводим на передний план
            win32gui.SetForegroundWindow(hwnd)
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при фокусировке окна '{window_title}': {e}")
            return False

    async def start(self):
        """Запуск фонового воркера."""
        if not self._is_running:
            self._is_running = True
            self._worker_task = asyncio.create_task(self._command_worker())
            logger.info("HardwareManager: фоновый воркер запущен.")

    async def stop(self):
        """Остановка воркера и закрытие порта."""
        self._is_running = False
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
                
        if self.serial_conn and self.serial_conn.is_open:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.serial_conn.close)
            
        logger.info("HardwareManager: остановлен, COM-порт закрыт.")

    async def send_command(self, cmd: str, target_window_title: str):
        """
        Публичный метод. Кладет команду в очередь для обработки воркером.
        """
        await self.command_queue.put((cmd, target_window_title))

    async def _command_worker(self):
        """
        Фоновый воркер. Забирает команды из очереди, фокусирует окно 
        и отправляет байты в Serial, не блокируя event loop.
        """
        loop = asyncio.get_running_loop()
        
        while self._is_running:
            try:
                # Ждем новую команду из очереди
                cmd, target_window_title = await self.command_queue.get()
            except asyncio.CancelledError:
                break
            
            try:
                # Эксклюзивный доступ к порту и окнам
                async with self.lock:
                    # 1. Фокусируем нужное окно
                    if not self._focus_window(target_window_title):
                        logger.warning(f"Команда '{cmd}' пропущена: окно '{target_window_title}' не найдено.")
                        continue
                    
                    # 2. Ждем 50мс, чтобы Windows физически переключила фокус
                    await asyncio.sleep(0.05)
                    
                    # 3. Проверяем, что Serial подключен (переподключаемся, если нет)
                    if not self.serial_conn or not self.serial_conn.is_open:
                        await self._reconnect_serial()
                        if not self.serial_conn:
                            logger.error("Serial все еще не подключен, команда пропущена.")
                            continue

                    # 4. Пишем в Serial (неблокирующе через executor)
                    try:
                        await loop.run_in_executor(
                            None, 
                            self.serial_conn.write, 
                            cmd.encode('utf-8')
                        )
                    except serial.SerialException as e:
                        logger.error(f"Ошибка записи в Serial: {e}. Помечаем порт как отключенный.")
                        try:
                            await loop.run_in_executor(None, self.serial_conn.close)
                        except:
                            pass
                        self.serial_conn = None
                        continue
                    
                    # 5. Ждем 100мс, давая Arduino время на эмуляцию нажатия
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.exception(f"Непредвиденная ошибка в воркере при обработке команды: {e}")
            finally:
                # Сообщаем очереди, что задача обработана
                self.command_queue.task_done()