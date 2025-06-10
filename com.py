import requests
from datetime import datetime, timedelta
import json
import random

def get_deforestation_data(lat, lon):
    """Generate sample historical deforestation data for given coordinates"""
    start_year = 2015
    current_year = datetime.now().year
    
    # Generate synthetic historical data
    historical_data = []
    base_deforestation = random.uniform(10, 30)  # Base deforestation percentage
    
    for year in range(start_year, current_year + 1):
        deforestation_percent = base_deforestation + random.uniform(-5, 5)
        deforestation_percent = max(0, min(100, deforestation_percent))  # Clamp between 0-100
        
        historical_data.append({
            'year': year,
            'deforestation_percent': round(deforestation_percent, 2)
        })
    
    return {
        'latitude': lat,
        'longitude': lon,
        'historical_data': historical_data
    }

def get_user_dates():
    """Get date range from user input"""
    while True:
        try:
            start = input("Enter start date (YYYY-MM-DD): ")
            end = input("Enter end date (YYYY-MM-DD): ")
            # Validate dates
            datetime.strptime(start, '%Y-%m-%d')
            datetime.strptime(end, '%Y-%m-%d')
            return start, end
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD format.")

# Example Usage
if __name__ == "__main__":
    # Example for Bangalore, India
    start_date, end_date = get_user_dates()
    result = get_deforestation_data(12.9716, 77.5946, start_date, end_date)
    if result:
        print("\nDetails:")
        print(f"Deforestation risk score: {result['percentage']}%")
        print(f"Fire points detected: {result['fire_points']}")
        print(f"Time period: {result['period']}")