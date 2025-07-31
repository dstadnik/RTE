import pandas as pd
import geopandas as gpd
from shapely.wkt import loads
from shapely.geometry import Point
import requests
import time
from typing import Tuple, Optional, List
import json

class GeoZoneChecker:
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
                'User-Agent': 'GeoZoneChecker/1.0'
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
    
    def check_point_example(self, lat: float, lon: float):
        """
        Пример проверки точки
        
        Args:
            lat: широта
            lon: долгота
        """
        print(f"\nПроверяем точку: {lat}, {lon}")
        
        results = self.point_in_zones(lat, lon)
        
        if results:
            print(f"Точка попадает в {len(results)} геозон(ы):")
            for i, result in enumerate(results, 1):
                print(f"  {i}. Индекс в файле: {result['index']}")
                # Выводим дополнительную информацию если есть
                for key, value in result.items():
                    if key not in ['index', 'geometry', 'WKT']:
                        print(f"     {key}: {value}")
        else:
            print("Точка не попадает ни в одну геозону")


def main():
    """Основная функция для демонстрации работы"""
    
    # Инициализируем checker
    checker = GeoZoneChecker('polygons.xlsx')
    
    # Пример проверки точки (замените на ваши координаты)
    # Например, координаты центра Москвы
    test_lat = 55.7558
    test_lon = 37.6176
    
    checker.check_point_example(test_lat, test_lon)
    
    # Добавляем информацию о городах (раскомментируйте если нужно)
    # ВНИМАНИЕ: это может занять много времени для большого количества геозон
    # checker.add_city_column('polygons_with_cities.xlsx', batch_size=5)
    
    print("\nДля добавления городов раскомментируйте соответствующую строку в main()")
    print("Учтите, что это может занять много времени для большого количества геозон")


if __name__ == "__main__":
    main()