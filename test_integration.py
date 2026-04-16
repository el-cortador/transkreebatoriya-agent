#!/usr/bin/env python3
"""
Интеграционные тесты для проверки работы транскрибатора.
"""

import os
import sys
import time
import requests
from pathlib import Path

# Добавляем путь к backend
sys.path.append(str(Path(__file__).parent / "backend"))

def test_server_running():
    """Проверяет, что сервер запущен и отвечает."""
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def test_file_upload(filepath):
    """Тестирует загрузку файла."""
    if not os.path.exists(filepath):
        print(f"Файл {filepath} не найден")
        return None
        
    with open(filepath, 'rb') as f:
        files = {'file': (os.path.basename(filepath), f, 'audio/wav')}
        try:
            response = requests.post(
                "http://localhost:8000/api/upload",
                files=files,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('task_id')
            else:
                print(f"Ошибка загрузки: {response.status_code} - {response.text}")
                return None
        except requests.RequestException as e:
            print(f"Ошибка запроса: {e}")
            return None

def test_task_status(task_id):
    """Проверяет статус задачи."""
    try:
        response = requests.get(f"http://localhost:8000/api/status/{task_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Ошибка получения статуса: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Ошибка запроса статуса: {e}")
        return None

def test_get_result(task_id):
    """Получает результат транскрибации."""
    try:
        response = requests.get(f"http://localhost:8000/api/result/{task_id}", timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Ошибка получения результата: {response.status_code} - {response.text}")
            return None
    except requests.RequestException as e:
        print(f"Ошибка запроса результата: {e}")
        return None

def main():
    print("Начало интеграционного тестирования...")
    
    # Проверяем, что сервер запущен
    if not test_server_running():
        print("Сервер не запущен. Пожалуйста, запустите backend сервер.")
        return
    
    print("Сервер запущен и отвечает")
    
    # Тестируем различные форматы файлов
    test_formats = ['.mp3', '.mp4', '.wav', '.m4a', '.mkv']
    test_dir = Path("test_files")
    
    for ext in test_formats:
        test_file = test_dir / f"test{ext}"
        print(f"\nТестирование формата {ext}...")
        
        if test_file.exists():
            # Загружаем файл
            task_id = test_file_upload(str(test_file))
            if task_id:
                print(f"Файл загружен, task_id: {task_id}")
                
                # Проверяем статус до завершения
                for i in range(30):  # Проверяем до 5 минут
                    status_data = test_task_status(task_id)
                    if status_data:
                        status = status_data.get('status')
                        print(f"Статус: {status}")
                        
                        if status == 'done':
                            # Получаем результат
                            result = test_get_result(task_id)
                            if result:
                                print(f"Результат получен, длина текста: {len(result.get('processed_text', ''))}")
                            break
                        elif status == 'error':
                            print(f"Ошибка обработки: {status_data.get('error')}")
                            break
                    
                    time.sleep(10)  # Ждем 10 секунд между проверками
            else:
                print(f"Не удалось загрузить файл {test_file}")
        else:
            print(f"Тестовый файл {test_file} не найден")

if __name__ == "__main__":
    main()