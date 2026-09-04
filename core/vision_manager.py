import numpy as np
import mss

class VisionManager:
    """
    Класс для ультра-быстрого захвата и анализа пикселей экрана.
    Использует mss для захвата микро-областей и numpy для мгновенного векторного анализа.
    """

    def __init__(self):
        # Инициализируем экземпляр mss один раз при старте
        self.sct = mss.mss()

    def _get_match_mask(self, img: np.ndarray, target_rgb: tuple, tolerance: int) -> np.ndarray:
        """
        Внутренний хелпер для вычисления маски совпадения цветов.
        Инвертирует каналы BGRA -> RGB и применяет допуск (tolerance).
        """
        # mss возвращает BGRA. Срез [2::-1] берет каналы в порядке R, G, B (индексы 2, 1, 0)
        img_rgb = img[..., 2::-1]
        
        # Считаем абсолютную разницу по каждому каналу
        diff = np.abs(img_rgb - target_rgb)
        
        # Возвращаем булевую маску: True, если все 3 канала уложились в tolerance
        return np.all(diff <= tolerance, axis=-1)

    def check_pixel(self, x: int, y: int, target_rgb: tuple, tolerance: int = 30) -> bool:
        """
        Проверяет микро-область 3x3 пикселя вокруг заданных координат.
        Возвращает True, если хотя бы один пиксель совпадает с target_rgb.
        """
        # Формируем микро-область 3x3, центрированную на (x, y)
        left = max(0, x - 1)
        top = max(0, y - 1)
        
        monitor = {"top": top, "left": left, "width": 3, "height": 3}
        img = np.array(self.sct.grab(monitor))
        
        match_mask = self._get_match_mask(img, target_rgb, tolerance)
        
        # Возвращаем True, если есть хотя бы одно совпадение
        return np.any(match_mask)

    def check_region(self, x: int, y: int, w: int, h: int, target_rgb: tuple, tolerance: int = 30) -> float:
        """
        Захватывает область w x h и считает процент пикселей, совпадающих с target_rgb.
        Возвращает float от 0.0 до 1.0.
        """
        if w <= 0 or h <= 0:
            return 0.0

        monitor = {"top": y, "left": x, "width": w, "height": h}
        img = np.array(self.sct.grab(monitor))
        
        match_mask = self._get_match_mask(img, target_rgb, tolerance)
        
        total_pixels = w * h
        matched_pixels = np.count_nonzero(match_mask)
        
        return matched_pixels / total_pixels