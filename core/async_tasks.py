# core/async_tasks.py

import asyncio
import logging
import time
from typing import Optional

from core.config_manager import ConfigManager
from core.hardware_manager import HardwareManager
from core.vision_manager import VisionManager

logger = logging.getLogger(__name__)


class BotCore:
    """
    Центральный оркестратор бота.
    Связывает ConfigManager, HardwareManager и VisionManager
    в единую асинхронную логику.
    """

    # Маппинг названий клавиш из конфига → символы для Arduino
    KEY_TO_ARDUINO_CMD = {
        "F1": "1",
        "F2": "2",
        "F3": "3",
        "F4": "4",
        "F5": "5",
        "F6": "6",
        "F7": "7",
        "F8": "8",
        "F9": "9",
        "F10": "0",
        "F11": "a",
        "F12": "b",
    }

    def __init__(
        self,
        config: ConfigManager,
        hardware: HardwareManager,
        vision: VisionManager,
    ):
        self.config = config
        self.hardware = hardware
        self.vision = vision

        # ── События синхронизации ──────────────────────────────────
        self.combat_allowed = asyncio.Event()
        self.combat_allowed.set()          # бой разрешён по умолчанию

        self.is_paused = asyncio.Event()
        self.is_paused.set()               # не на паузе по умолчанию

        # ── Внутреннее состояние ───────────────────────────────────
        self._tasks: list[asyncio.Task] = []
        self._settings = self.config.get_logic_settings()
        self._main_window: str = self._settings.get(
            "main_window_title", "Lineage II"
        )
        self._buffer_window: str = self._settings.get(
            "buffer_window_title", "Buffer"
        )

    # ================================================================== #
    #  Вспомогательные методы
    # ================================================================== #

    def _key_to_cmd(self, action_name: str) -> str:
        """
        Берёт название хоткея из конфига (например 'F4')
        и переводит в символ для Arduino (например '4').
        """
        hotkey = self.config.get_hotkey(action_name)
        cmd = self.KEY_TO_ARDUINO_CMD.get(hotkey)
        if cmd is None:
            logger.warning(
                "Неизвестный хоткей '%s' для действия '%s'",
                hotkey, action_name,
            )
            return ""
        return cmd

    async def _send(
        self,
        action_name: str,
        window: Optional[str] = None,
    ) -> None:
        """
        Отправляет команду через HardwareManager.
        Автоматически маппит клавишу из конфига в символ Arduino.
        """
        cmd = self._key_to_cmd(action_name)
        if not cmd:
            return
        target = window or self._main_window
        # Если send_command синхронный — оберните в asyncio.to_thread
        await self.hardware.send_command(cmd, target)

    async def _wait_unpaused(self) -> None:
        """Блокирует выполнение, пока бот на глобальной паузе."""
        if not self.is_paused.is_set():
            logger.info("⏸  Бот на паузе, ожидание…")
            await self.is_paused.wait()
            logger.info("▶  Пауза снята, продолжаем.")

    def _get_pixel(self, name: str) -> tuple[int, int, tuple]:
        """Возвращает (x, y, rgb) из конфига по имени точки."""
        data = self.config.get_pixel_coords(name)
        return data["x"], data["y"], data["color"]

    def _check_bar(self, bar_name: str) -> Optional[float]:
        """
        Проверяет полоску HP/MP через VisionManager.check_region.
        Возвращает float 0.0–1.0 (процент заполнения) или None.
        """
        try:
            data = self.config.get_pixel_coords(bar_name)
            x, y = data["x"], data["y"]
            w = data.get("w", 100)
            h = data.get("h", 5)
            rgb = data["color"]
            tolerance = self._settings.get("color_tolerance", 15)
            return self.vision.check_region(x, y, w, h, rgb, tolerance)
        except KeyError:
            logger.debug("Координаты для '%s' не найдены в конфиге", bar_name)
            return None

    # ================================================================== #
    #  Combat Loop
    # ================================================================== #

    async def combat_loop(self) -> None:
        """
        Цикл боя:
          1. Ждём combat_allowed + снятие паузы.
          2. Таргет моба (F2).
          3. Проверка HP моба через check_pixel.
          4. Атака петом → опциональная атака героем.
          5. Добивание: крутим проверку HP до смерти (череп) или таймаута 30 с.
          6. Опциональный лут.
        """
        logger.info("[Combat] 🗡  Запуск цикла боя.")
        tolerance = self._settings.get("color_tolerance", 15)

        while True:
            await self._wait_unpaused()
            await self.combat_allowed.wait()

            # ── Таргет моба ────────────────────────────────────────
            await self._send("target_mob")
            await asyncio.sleep(0.5)

            # ── Есть ли моб в таргете? ─────────────────────────────
            mx, my, mrgb = self._get_pixel("mob_hp_indicator")
            if not self.vision.check_pixel(mx, my, mrgb, tolerance):
                logger.debug("[Combat] Моб не найден, повтор через 1 с.")
                await asyncio.sleep(1.0)
                continue

            # ── Атака петом ────────────────────────────────────────
            await self._send("pet_attack")
            await asyncio.sleep(0.3)

            # ── Опциональная атака героем ──────────────────────────
            if self._settings.get("hero_attack_enabled", False):
                await self._send("main_attack")
                await asyncio.sleep(0.3)

            # ── Добивание моба (таймаут 30 с) ──────────────────────
            timeout = 30.0
            start = time.monotonic()
            mob_alive = True

            while mob_alive:
                await self._wait_unpaused()
                await self.combat_allowed.wait()

                if time.monotonic() - start > timeout:
                    logger.warning("[Combat] ⏱  Таймаут 30 с, сброс таргета.")
                    break

                # Проверка иконки черепа (моб мёртв)
                sx, sy, srgb = self._get_pixel("mob_dead_skull")
                if self.vision.check_pixel(sx, sy, srgb, tolerance):
                    mob_alive = False
                    logger.info("[Combat] 💀 Моб убит.")
                    break

                # Повторная атака героем, если включена
                if self._settings.get("hero_attack_repeat", False):
                    await self._send("main_attack")

                await asyncio.sleep(0.5)

            # ── Опциональный лут ───────────────────────────────────
            if self._settings.get("auto_loot_enabled", False) and not mob_alive:
                await self._send("pick_up")
                await asyncio.sleep(0.5)

            await asyncio.sleep(0.3)

    # ================================================================== #
    #  Survival Loop
    # ================================================================== #

    async def survival_loop(self) -> None:
        """
        Цикл выживания (каждые 0.5 с):
          • HP героя < 30 % → хил.
          • MP героя < 20 % → сесть, ждать > 80 %, встать.
          • Пет мёртв (HP ≈ 0) → перевызов.
        """
        logger.info("[Survival] 💚 Запуск цикла выживания.")

        while True:
            await self._wait_unpaused()
            await asyncio.sleep(0.5)

            # ── HP героя ───────────────────────────────────────────
            hero_hp = self._check_bar("hero_hp")
            if hero_hp is not None and hero_hp < 0.30:
                logger.warning(
                    "[Survival] HP героя < 30%% (%.0f%%), хил!",
                    hero_hp * 100,
                )
                await self._send("heal_self")
                await asyncio.sleep(1.0)

            # ── MP героя ───────────────────────────────────────────
            hero_mp = self._check_bar("hero_mp")
            if hero_mp is not None and hero_mp < 0.20:
                logger.warning(
                    "[Survival] MP героя < 20%% (%.0f%%), садимся.",
                    hero_mp * 100,
                )
                await self._send("sit_stand")

                # Ждём восстановления MP > 80 %
                while True:
                    await self._wait_unpaused()
                    await asyncio.sleep(1.0)
                    cur_mp = self._check_bar("hero_mp")
                    if cur_mp is not None and cur_mp > 0.80:
                        logger.info(
                            "[Survival] MP восстановлен > 80%%, встаём."
                        )
                        await self._send("sit_stand")
                        break

            # ── HP пета ────────────────────────────────────────────
            pet_hp = self._check_bar("pet_hp")
            if pet_hp is not None and pet_hp < 0.05:
                logger.warning("[Survival] 🐾 Пет мёртв, перевызов!")
                await self._send("pet_summon")
                await asyncio.sleep(3.0)

    # ================================================================== #
    #  Buffer Loop
    # ================================================================== #

    async def buffer_loop(self) -> None:
        """
        Цикл баффа (каждые 19 минут):
          1. combat_allowed.clear()  — блокируем бой.
          2. Фокус на окно баффера.
          3. Макрос таргета → инвайт → цикл бафов.
          4. Выход из пати → привязка.
          5. Возврат в окно героя → combat_allowed.set().
        """
        logger.info("[Buffer] 🛡  Запуск цикла баффа (интервал 19 мин).")
        interval = self._settings.get("buffer_interval_sec", 19 * 60)

        while True:
            await self._wait_unpaused()
            await asyncio.sleep(interval)
            await self._wait_unpaused()

            logger.info("[Buffer] Начинаем процедуру баффа…")
            self.combat_allowed.clear()

            try:
                # ── Таргет героя из окна баффера ───────────────────
                await self._send("target_hero", window=self._buffer_window)
                await asyncio.sleep(0.5)

                # ── Инвайт в пати ──────────────────────────────────
                await self._send("invite_party", window=self._buffer_window)
                await asyncio.sleep(1.5)

                # ── Цикл бафов ─────────────────────────────────────
                buff_count = self._settings.get("buff_macro_count", 3)
                for i in range(1, buff_count + 1):
                    await self._send(
                        f"buff_macro_{i}", window=self._buffer_window
                    )
                    await asyncio.sleep(2.0)

                # ── Выход из пати ──────────────────────────────────
                await self._send("leave_party", window=self._buffer_window)
                await asyncio.sleep(1.0)

                # ── Привязка пета (опционально) ────────────────────
                if self._settings.get("rebind_enabled", False):
                    await self._send("rebind_pet", window=self._main_window)
                    await asyncio.sleep(0.5)

            except Exception as exc:
                logger.error(
                    "[Buffer] Ошибка во время баффа: %s", exc, exc_info=True
                )

            finally:
                # Гарантированно разблокируем бой даже при ошибке
                logger.info("[Buffer] ✅ Бафф завершён, возвращаемся в бой.")
                self.combat_allowed.set()

    # ================================================================== #
    #  Buffer Loop
    # ================================================================== #
    
    async def self_buff_loop(self) -> None:
        """
        Цикл самобаффа.
        Читает список хоткеев из конфига и нажимает их по очереди
        с соблюдением GCD (1.5 сек).
        """
        logger.info("[SelfBuff] 🛡 Запуск цикла самобаффа.")
        
        # Интервал срабатывания самобаффа (по умолчанию 15 минут)
        interval = self._settings.get("self_buff_interval_sec", 15 * 60)

        while True:
            await self._wait_unpaused()
            await asyncio.sleep(interval)
            await self._wait_unpaused()

            # Получаем настройки самобаффа из конфига
            buff_settings = self.config.get_self_buff_settings()
            
            if not buff_settings.get("enabled", False):
                logger.debug("[SelfBuff] Самобафф отключен в конфиге.")
                continue

            hotkeys = buff_settings.get("hotkeys", [])
            if not hotkeys:
                logger.debug("[SelfBuff] Список хоткеев для самобаффа пуст.")
                continue

            logger.info("[SelfBuff] Начинаем самобафф. Кнопок: %d", len(hotkeys))

            # Итерируемся по всему списку без ограничений на длину (от 1 до 36+)
            for hotkey in hotkeys:
                await self._wait_unpaused()
                
                # Конвертируем название клавиши (например, "F1") в символ для Arduino ("1")
                # Используем статический маппер напрямую
                cmd = self.KEY_TO_ARDUINO_CMD.get(hotkey)
                if not cmd:
                    logger.warning("[SelfBuff] Неизвестный хоткей '%s', пропускаем.", hotkey)
                    continue

                # Отправляем команду в Arduino
                await self.hardware.send_command(cmd, self._main_window)
                
                # Ждем GCD (1.5 сек) перед следующей кнопкой
                await asyncio.sleep(1.5)

            logger.info("[SelfBuff] ✅ Самобафф завершен.")


    # ================================================================== #
    #  Start / Stop
    # ================================================================== #

    async def start(self) -> None:
        """Запускает все асинхронные таски параллельно."""
        logger.info("═══ BotCore: Запуск всех тасков ═══")
        self._tasks = [
            asyncio.create_task(self.combat_loop(), name="combat_loop"),
            asyncio.create_task(self.survival_loop(), name="survival_loop"),
            asyncio.create_task(self.buffer_loop(), name="buffer_loop"),
        ]
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def stop(self) -> None:
        """Отменяет все таски и корректно завершает работу."""
        logger.info("═══ BotCore: Остановка всех тасков ═══")
        for task in self._tasks:
            if not task.done():
                task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("═══ BotCore: Остановка завершена ═══")