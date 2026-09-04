import os
import shutil
from pathlib import Path

def setup_project():
    base_dir = Path(".")
    print("🚀 Начинаем настройку архитектуры проекта L2 Bot...")

    # 1. Создаем директории
    dirs_to_create = ["core", "ui", "arduino", "screenshots", "legacy"]
    for d in dirs_to_create:
        (base_dir / d).mkdir(parents=True, exist_ok=True)
        print(f"✅ Папка '{d}' создана/проверена.")

    # 2. Создаем файлы новой архитектуры
    files_to_create = [
        "main.py",
        "config.json",
        "requirements.txt",
        "core/__init__.py",
        "core/config_manager.py",
        "core/hardware_manager.py",
        "core/vision_manager.py",
        "core/async_tasks.py",
        "ui/__init__.py",
        "ui/app.py",
        "ui/calibration_overlay.py"
    ]
    
    for f in files_to_create:
        file_path = base_dir / f
        if not file_path.exists():
            file_path.touch()
            print(f"✅ Файл '{f}' создан.")
        else:
            print(f"⚠️ Файл '{f}' уже существует, пропускаем.")

    # 3. Заполняем requirements.txt актуальными зависимостями
    req_content = """# Основные зависимости для L2 Bot
pyserial==3.5
pywin32==306
mss==9.0.1
numpy==1.26.4
customtkinter==5.2.2
pynput==1.7.6
"""
    (base_dir / "requirements.txt").write_text(req_content.strip())
    print("✅ Файл 'requirements.txt' заполнен.")

    # 4. Переносим старые файлы в legacy/
    legacy_files = ["bot.py", "bot_v1.2.py", "get_points.py", "bot_config.ini"]
    for lf in legacy_files:
        src = base_dir / lf
        dst = base_dir / "legacy" / lf
        if src.exists() and not dst.exists():
            shutil.move(str(src), str(dst))
            print(f"📦 Старый файл '{lf}' перенесен в legacy/.")

    # 5. Переносим stats_manager.py в core/
    stats_src = base_dir / "stats_manager.py"
    stats_dst = base_dir / "core" / "stats_manager.py"
    if stats_src.exists() and not stats_dst.exists():
        shutil.move(str(stats_src), str(stats_dst))
        print(f"📦 Файл 'stats_manager.py' перенесен в core/.")

    print("\n" + "="*50)
    print("🎉 АРХИТЕКТУРА УСПЕШНО РАЗВЕРНУТА!")
    print("="*50)
    print("Следующие шаги:")
    print("1. Установи зависимости: pip install -r requirements.txt")
    print("2. Можешь открывать новый чат и давать Промт №1 для Агента (ConfigManager).")
    print("   Код от Агента нужно будет вставить в файл: core/config_manager.py")

if __name__ == "__main__":
    setup_project()