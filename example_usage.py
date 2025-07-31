#!/usr/bin/env python3
"""
Пример использования GeoZoneChecker для проверки геозон доставки ресторанов
"""

from geo_zones_checker import GeoZoneChecker

def check_single_point():
    """Проверка одной точки"""
    print("=== Проверка одной точки ===")
    
    # Инициализируем checker
    checker = GeoZoneChecker('polygons.xlsx')
    
    # Координаты для проверки (замените на ваши)
    lat = 55.7558  # широта
    lon = 37.6176  # долгота
    
    print(f"Проверяем координаты: {lat}, {lon}")
    
    # Проверяем попадание в геозоны
    results = checker.point_in_zones(lat, lon)
    
    if results:
        print(f"✅ Точка попадает в {len(results)} геозон(ы)")
        for i, result in enumerate(results, 1):
            print(f"\nГеозона {i}:")
            print(f"  Индекс: {result['index']}")
            # Выводим все доступные поля
            for key, value in result.items():
                if key not in ['index', 'geometry']:
                    print(f"  {key}: {value}")
    else:
        print("❌ Точка не попадает ни в одну геозону доставки")

def check_multiple_points():
    """Проверка нескольких точек"""
    print("\n=== Проверка нескольких точек ===")
    
    checker = GeoZoneChecker('polygons.xlsx')
    
    # Список точек для проверки
    test_points = [
        (55.7558, 37.6176, "Центр Москвы"),
        (59.9311, 30.3609, "Центр СПб"),
        (56.8431, 60.6454, "Центр Екатеринбурга"),
        # Добавьте свои координаты
    ]
    
    for lat, lon, description in test_points:
        print(f"\n📍 {description} ({lat}, {lon}):")
        results = checker.point_in_zones(lat, lon)
        
        if results:
            print(f"  ✅ Попадает в {len(results)} геозон(ы)")
            # Показываем только первую геозону для краткости
            if results:
                first_result = results[0]
                print(f"  Первая геозона (индекс {first_result['index']}):")
                for key, value in first_result.items():
                    if key not in ['index', 'geometry', 'WKT'] and value is not None:
                        print(f"    {key}: {value}")
        else:
            print("  ❌ Не попадает в геозоны доставки")

def add_cities_to_file():
    """Добавление информации о городах в файл"""
    print("\n=== Добавление городов в файл ===")
    
    checker = GeoZoneChecker('polygons.xlsx')
    
    # ВНИМАНИЕ: это может занять много времени!
    # Для каждой геозоны будет сделан запрос к API
    
    response = input("Добавить информацию о городах? Это может занять много времени (y/N): ")
    
    if response.lower() in ['y', 'yes', 'да']:
        print("Начинаю добавление информации о городах...")
        print("Это может занять несколько минут в зависимости от количества геозон")
        
        # Добавляем города с сохранением каждые 5 записей
        checker.add_city_column('polygons_with_cities.xlsx', batch_size=5)
        
        print("✅ Информация о городах добавлена в файл polygons_with_cities.xlsx")
    else:
        print("Пропускаем добавление городов")

def main():
    """Главная функция"""
    print("🗺️  Проверка геозон доставки ресторанов")
    print("=" * 50)
    
    try:
        # Проверяем одну точку
        check_single_point()
        
        # Проверяем несколько точек
        check_multiple_points()
        
        # Опционально добавляем города
        add_cities_to_file()
        
    except FileNotFoundError:
        print("❌ Файл polygons.xlsx не найден!")
        print("Убедитесь, что файл находится в той же папке что и скрипт")
    except Exception as e:
        print(f"❌ Произошла ошибка: {e}")

if __name__ == "__main__":
    main()