#!/usr/bin/env python3
"""
Быстрый тест функций RTE Zones
"""

from rte_zones import RTEZoneChecker, check_point_simple, get_delivery_restaurants

def test_basic_functionality():
    """Тестирование основного функционала"""
    print("🧪 Тестирование RTE Zones")
    print("=" * 40)
    
    # Тестовые координаты
    moscow_center = (55.7558, 37.6176)
    spb_center = (59.9311, 30.3609)
    random_point = (55.0000, 50.0000)  # Где-то в поле
    
    print("\n1. Простая проверка точек:")
    for lat, lon, name in [moscow_center + ("Центр Москвы",), 
                          spb_center + ("Центр СПб",), 
                          random_point + ("Случайная точка",)]:
        result = check_point_simple(lat, lon)
        print(f"   {name}: {'✅ В зоне' if result else '❌ Не в зоне'}")
    
    print("\n2. Получение ресторанов для центра Москвы:")
    restaurants = get_delivery_restaurants(*moscow_center)
    for i, rest in enumerate(restaurants, 1):
        zones_info = f"{len(rest['zones'])} зон" if len(rest['zones']) > 1 else "1 зона"
        print(f"   {i}. {rest['partner']} (ID: {rest['restaurant_id']}) - {zones_info}")
    
    print("\n3. Детальная информация с RTEZoneChecker:")
    checker = RTEZoneChecker('polygons.xlsx')
    
    # Получаем детальную информацию о зонах
    zones = checker.point_in_zones(*moscow_center)
    print(f"   Точка попадает в {len(zones)} геозон:")
    for zone in zones:
        print(f"     - {zone['name']} ({zone['Партнер']})")
    
    print("\n✅ Тестирование завершено!")

if __name__ == "__main__":
    test_basic_functionality()