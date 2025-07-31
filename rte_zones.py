#!/usr/bin/env python3
"""
RTE Zones - Система проверки геозон доставки ресторанов
Позволяет проверить попадание геоточки в зоны доставки и добавить информацию о городах
"""

import pandas as pd
import geopandas as gpd
from shapely.wkt import loads
from shapely.geometry import Point
import requests
import time
from typing import Tuple, Optional, List
import json

class RTEZoneChecker:
    """Класс для работы с геозонами доставки ресторанов"""
    
    def __init__(self, polygons_file: str):
        """
        Инициализация класса для работы с геозонами
        
        Args:
            polygons_file: путь к файлу с полигонами (Excel или CSV)
        """
        self.polygons_file = polygons_file
        self.df = None
        self.gdf = None
        self.load_data()
    
    def load_data(self):
        """Загружает данные из файла и создает GeoDataFrame"""
        try:
            # Загружаем данные
            if self.polygons_file.endswith('.xlsx'):
                self.df = pd.read_excel(self.polygons_file)
            elif self.polygons_file.endswith('.csv'):
                self.df = pd.read_csv(self.polygons_file)
            else:
                raise ValueError("Поддерживаются только файлы .xlsx и .csv")
            
            print(f"Загружено {len(self.df)} записей")
            print("Колонки в файле:", list(self.df.columns))
            
            # Проверяем наличие WKT колонки
            if 'WKT' not in self.df.columns:
                raise ValueError("В файле не найдена колонка 'WKT'")
            
            # Преобразуем WKT в геометрию
            geometries = []
            valid_indices = []
            
            for idx, wkt_string in enumerate(self.df['WKT']):
                try:
                    if pd.notna(wkt_string):
                        geom = loads(wkt_string)
                        geometries.append(geom)
                        valid_indices.append(idx)
                    else:
                        print(f"Пустая WKT строка в индексе {idx}")
                except Exception as e:
                    print(f"Ошибка парсинга WKT в индексе {idx}: {e}")
            
            # Создаем GeoDataFrame только с валидными геометриями
            valid_df = self.df.iloc[valid_indices].copy()
            self.gdf = gpd.GeoDataFrame(valid_df, geometry=geometries, crs='EPSG:4326')
            
            print(f"Успешно обработано {len(self.gdf)} геозон")
            
        except Exception as e:
            print(f"Ошибка при загрузке данных: {e}")
            raise
    
    def point_in_zones(self, lat: float, lon: float) -> List[dict]:
        """
        Проверяет, попадает ли точка в какие-либо геозоны
        
        Args:
            lat: широта точки
            lon: долгота точки
            
        Returns:
            Список словарей с информацией о геозонах, в которые попадает точка
        """
        if self.gdf is None:
            raise ValueError("Данные не загружены")
        
        point = Point(lon, lat)  # Shapely использует (lon, lat)
        
        # Находим все геозоны, в которые попадает точка
        intersecting = self.gdf[self.gdf.geometry.contains(point)]
        
        results = []
        for idx, row in intersecting.iterrows():
            result = {
                'index': idx,
                'geometry': row.geometry,
            }
            # Добавляем все остальные колонки из исходного файла
            for col in self.gdf.columns:
                if col != 'geometry':
                    result[col] = row[col]
            results.append(result)
        
        return results
    
    def is_point_in_any_zone(self, lat: float, lon: float) -> bool:
        """
        Простая проверка - попадает ли точка в любую геозону
        
        Args:
            lat: широта точки
            lon: долгота точки
            
        Returns:
            True если точка попадает хотя бы в одну геозону, False иначе
        """
        results = self.point_in_zones(lat, lon)
        return len(results) > 0
    
    def get_restaurants_for_point(self, lat: float, lon: float) -> List[dict]:
        """
        Получает список ресторанов, которые доставляют в указанную точку
        
        Args:
            lat: широта точки
            lon: долгота точки
            
        Returns:
            Список уникальных ресторанов с их зонами доставки
        """
        zones = self.point_in_zones(lat, lon)
        
        # Группируем по ресторанам
        restaurants = {}
        for zone in zones:
            restaurant_id = zone.get('ID реста', 'unknown')
            partner = zone.get('Партнер', 'Неизвестно')
            zone_name = zone.get('name', 'Неизвестная зона')
            
            if restaurant_id not in restaurants:
                restaurants[restaurant_id] = {
                    'restaurant_id': restaurant_id,
                    'partner': partner,
                    'zones': []
                }
            
            restaurants[restaurant_id]['zones'].append({
                'name': zone_name,
                'internal_id': zone.get('ID внутренний', ''),
                'index': zone['index']
            })
        
        return list(restaurants.values())
    
    def get_city_from_coordinates(self, lat: float, lon: float, delay: float = 1.0) -> Optional[str]:
        """
        Получает название города по координатам через Nominatim API
        
        Args:
            lat: широта
            lon: долгота
            delay: задержка между запросами в секундах
            
        Returns:
            Название города или None
        """
        try:
            # Используем бесплатный Nominatim API
            url = f"https://nominatim.openstreetmap.org/reverse"
            params = {
                'format': 'json',
                'lat': lat,
                'lon': lon,
                'zoom': 10,
                'addressdetails': 1
            }
            headers = {
                'User-Agent': 'RTEZoneChecker/1.0'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Пытаемся извлечь город из разных полей
                address = data.get('address', {})
                city = (address.get('city') or 
                       address.get('town') or 
                       address.get('village') or 
                       address.get('municipality') or
                       address.get('county'))
                
                if delay > 0:
                    time.sleep(delay)  # Соблюдаем лимиты API
                
                return city
            else:
                print(f"Ошибка API: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Ошибка при получении города для координат ({lat}, {lon}): {e}")
            return None
    
    def get_city_from_geometry(self, geometry) -> Optional[str]:
        """
        Получает город для геометрии (использует центроид)
        
        Args:
            geometry: геометрия Shapely
            
        Returns:
            Название города или None
        """
        try:
            centroid = geometry.centroid
            return self.get_city_from_coordinates(centroid.y, centroid.x)
        except Exception as e:
            print(f"Ошибка при получении города для геометрии: {e}")
            return None
    
    def add_city_column(self, save_file: Optional[str] = None, batch_size: int = 10):
        """
        Добавляет колонку с городом для каждой геозоны
        
        Args:
            save_file: путь для сохранения обновленного файла
            batch_size: количество запросов перед сохранением промежуточного результата
        """
        if self.gdf is None:
            raise ValueError("Данные не загружены")
        
        print("Начинаю добавление информации о городах...")
        
        # Проверяем, есть ли уже колонка city
        if 'city' not in self.gdf.columns:
            self.gdf['city'] = None
        
        total_zones = len(self.gdf)
        processed = 0
        
        for idx, row in self.gdf.iterrows():
            if pd.isna(row['city']) or row['city'] == '':
                city = self.get_city_from_geometry(row.geometry)
                self.gdf.at[idx, 'city'] = city
                processed += 1
                
                print(f"Обработано {processed}/{total_zones}: {city}")
                
                # Сохраняем промежуточный результат каждые batch_size записей
                if processed % batch_size == 0 and save_file:
                    self.save_data(save_file)
                    print(f"Промежуточное сохранение выполнено")
        
        print("Завершено добавление информации о городах")
        
        if save_file:
            self.save_data(save_file)
    
    def save_data(self, filename: str):
        """
        Сохраняет данные в файл
        
        Args:
            filename: имя файла для сохранения
        """
        if self.gdf is None:
            raise ValueError("Нет данных для сохранения")
        
        # Создаем DataFrame для сохранения (без геометрии Shapely)
        save_df = self.df.copy()
        
        # Добавляем новые колонки если они есть
        for col in self.gdf.columns:
            if col not in save_df.columns and col != 'geometry':
                # Сопоставляем по индексам
                for idx in save_df.index:
                    if idx in self.gdf.index:
                        save_df.at[idx, col] = self.gdf.at[idx, col]
        
        if filename.endswith('.xlsx'):
            save_df.to_excel(filename, index=False)
        elif filename.endswith('.csv'):
            save_df.to_csv(filename, index=False)
        else:
            raise ValueError("Поддерживаются только форматы .xlsx и .csv")
        
        print(f"Данные сохранены в {filename}")
    
    def get_stats(self) -> dict:
        """
        Получает статистику по геозонам
        
        Returns:
            Словарь со статистикой
        """
        if self.gdf is None:
            return {}
        
        stats = {
            'total_zones': len(self.gdf),
            'partners': self.gdf['Партнер'].nunique() if 'Партнер' in self.gdf.columns else 0,
            'restaurants': self.gdf['ID реста'].nunique() if 'ID реста' in self.gdf.columns else 0,
        }
        
        if 'Партнер' in self.gdf.columns:
            stats['partner_distribution'] = self.gdf['Партнер'].value_counts().to_dict()
        
        if 'city' in self.gdf.columns:
            stats['cities'] = self.gdf['city'].nunique()
            stats['city_distribution'] = self.gdf['city'].value_counts().head(10).to_dict()
        
        return stats
    
    def print_stats(self):
        """Выводит статистику в консоль"""
        stats = self.get_stats()
        
        print("\n=== Статистика геозон ===")
        print(f"Всего геозон: {stats.get('total_zones', 0)}")
        print(f"Партнеров: {stats.get('partners', 0)}")
        print(f"Ресторанов: {stats.get('restaurants', 0)}")
        
        if 'partner_distribution' in stats:
            print("\nРаспределение по партнерам:")
            for partner, count in stats['partner_distribution'].items():
                print(f"  {partner}: {count}")
        
        if 'city_distribution' in stats:
            print(f"\nГородов: {stats.get('cities', 0)}")
            print("Топ-10 городов по количеству геозон:")
            for city, count in stats['city_distribution'].items():
                print(f"  {city}: {count}")


def check_point_simple(lat: float, lon: float, polygons_file: str = 'polygons.xlsx') -> bool:
    """
    Простая функция для быстрой проверки точки
    
    Args:
        lat: широта
        lon: долгота
        polygons_file: путь к файлу с полигонами
        
    Returns:
        True если точка в зоне доставки, False иначе
    """
    checker = RTEZoneChecker(polygons_file)
    return checker.is_point_in_any_zone(lat, lon)


def get_delivery_restaurants(lat: float, lon: float, polygons_file: str = 'polygons.xlsx') -> List[dict]:
    """
    Получает список ресторанов для доставки в точку
    
    Args:
        lat: широта
        lon: долгота
        polygons_file: путь к файлу с полигонами
        
    Returns:
        Список ресторанов с зонами доставки
    """
    checker = RTEZoneChecker(polygons_file)
    return checker.get_restaurants_for_point(lat, lon)


def main():
    """Демонстрация работы с RTE Zones"""
    print("🗺️  RTE Zones - Проверка геозон доставки")
    print("=" * 50)
    
    try:
        # Инициализируем checker
        checker = RTEZoneChecker('polygons.xlsx')
        
        # Показываем статистику
        checker.print_stats()
        
        # Тестовые координаты
        test_points = [
            (55.7558, 37.6176, "Центр Москвы"),
            (59.9311, 30.3609, "Центр СПб"),
            (56.8431, 60.6454, "Центр Екатеринбурга"),
        ]
        
        print("\n=== Проверка тестовых точек ===")
        
        for lat, lon, description in test_points:
            print(f"\n📍 {description} ({lat}, {lon}):")
            
            # Простая проверка
            in_zone = checker.is_point_in_any_zone(lat, lon)
            print(f"  В зоне доставки: {'✅ Да' if in_zone else '❌ Нет'}")
            
            if in_zone:
                # Получаем рестораны
                restaurants = checker.get_restaurants_for_point(lat, lon)
                print(f"  Доступно ресторанов: {len(restaurants)}")
                
                for i, restaurant in enumerate(restaurants[:3], 1):  # Показываем первые 3
                    print(f"    {i}. {restaurant['partner']} (ID: {restaurant['restaurant_id']})")
                    print(f"       Зон доставки: {len(restaurant['zones'])}")
                
                if len(restaurants) > 3:
                    print(f"    ... и еще {len(restaurants) - 3} ресторанов")
        
        print("\n=== Примеры использования функций ===")
        
        # Пример простой проверки
        lat, lon = 55.7558, 37.6176
        result = check_point_simple(lat, lon)
        print(f"check_point_simple({lat}, {lon}) = {result}")
        
        # Пример получения ресторанов
        restaurants = get_delivery_restaurants(lat, lon)
        print(f"get_delivery_restaurants({lat}, {lon}) вернул {len(restaurants)} ресторанов")
        
    except FileNotFoundError:
        print("❌ Файл polygons.xlsx не найден!")
        print("Убедитесь, что файл находится в той же папке что и скрипт")
    except Exception as e:
        print(f"❌ Произошла ошибка: {e}")


if __name__ == "__main__":
    main()