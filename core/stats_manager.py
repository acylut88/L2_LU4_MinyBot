import time

class BotStatistics:
    def __init__(self):
        self.start_time = time.time()
        self.total_mobs = 0
        
        # Временные метрики
        self.total_fight_time = 0.0  # Суммарное время чистого боя с мобами
        self.total_rest_time = 0.0   # Суммарное время сидения на попе (реген MP)
        
        # Метрики осечек
        self.timeouts_count = 0
        self.escaped_mobs = 0
        self.mp_rest_count = 0       # Количество пауз на регенерацию маны
        
        # Таймстампы для скользящих интервалов (5, 15, 30, 60 минут)
        self.mobs_timestamps = []

    def add_mob(self, fight_duration):
        """Регистрация убитого моба"""
        self.total_mobs += 1
        self.total_fight_time += fight_duration
        self.mobs_timestamps.append(time.time())

    def add_timeout(self, fight_duration):
        """Регистрация таймаута (30 секунд без смерти)"""
        self.timeouts_count += 1
        self.total_fight_time += fight_duration

    def add_escape(self, fight_duration):
        """Регистрация сорвавшегося таргета"""
        self.escaped_mobs += 1
        self.total_fight_time += fight_duration

    def add_rest(self, rest_duration):
        """Регистрация времени отдыха/регенерации маны"""
        self.mp_rest_count += 1
        self.total_rest_time += rest_duration

    def _get_mobs_in_last_minutes(self, minutes):
        """Считает количество убитых мобов за последние N минут"""
        now = time.time()
        threshold = now - (minutes * 60)
        return sum(1 for t in self.mobs_timestamps if t >= threshold)

    def print_report(self, current_profile: int):
        """Формирует и выводит красивый расширенный аналитический отчет"""
        uptime_sec = time.time() - self.start_time
        
        # Форматируем общее время работы бота
        hours, remainder = divmod(int(uptime_sec), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # Расчет среднего времени на одного моба
        avg_time = (self.total_fight_time / self.total_mobs) if self.total_mobs > 0 else 0.0
        
        # Экстраполяция эффективности (мобов в час)
        mobs_per_hour = (self.total_mobs / (uptime_sec / 3600.0)) if uptime_sec > 0 else 0.0

        # Расчет КПД работы бота (% времени в бою от общего аптайма)
        fight_percentage = (self.total_fight_time / uptime_sec) * 100 if uptime_sec > 0 else 0.0
        rest_percentage = (self.total_rest_time / uptime_sec) * 100 if uptime_sec > 0 else 0.0

        print("\n" + "═"*60)
        print(f"📊 МИКРОСЕРВИС СТАТИСТИКИ (Аптайм бота: {uptime_str})")
        print("─"*60)
        print(f" • Убито мобов всего      : {self.total_mobs} шт.")
        print(f" • Скорость фарма         : {mobs_per_hour:.1f} моб/час")
        print(f" • Среднее время на моба  : {avg_time:.1f} сек.")
        print("─"*60)
        print(f" ⏱ Распределение времени:")
        print(f"   - В состоянии боя      : {self.total_fight_time:.1f} сек. ({fight_percentage:.1f}%)")
        if current_profile == 2:
            print(f"   - На регенерации маны  : {self.total_rest_time:.1f} sec. ({rest_percentage:.1f}%)")
            print(f"   - Количество пауз на MP: {self.mp_rest_count} раз")
        print("─"*60)
        print(f" ⚠️ Осечки и проблемы:")
        print(f"   - Таймауты (30 сек)    : {self.timeouts_count} раз")
        print(f"   - Сорвался таргет/Угнали: {self.escaped_mobs} раз")
        print("─"*60)
        print(f" 📈 Интервалы уничтожения мобов:")
        print(f"   - За последние  5 минут: [{self._get_mobs_in_last_minutes(5)}]")
        print(f"   - За последние 15 минут: [{self._get_mobs_in_last_minutes(15)}]")
        print(f"   - За последние 30 минут: [{self._get_mobs_in_last_minutes(30)}]")
        print(f"   - За последние 60 минут: [{self._get_mobs_in_last_minutes(60)}]")
        print("═"*60)
