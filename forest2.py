import requests

def get_forest_data():
    """
    Fetches a list of forests in India with their respective latitude and longitude.

    Returns:
        list: A list of dictionaries containing forest names and coordinates.
              Example: [{'name': 'Sundarbans', 'latitude': 21.9497, 'longitude': 89.1833}, ...]
    """
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = """
    [out:json];
    area["name"="India"]->.searchArea;
    node["natural"="wood"](area.searchArea);
    out body;
    """
    
    try:
        response = requests.get(overpass_url, params={'data': query}, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        # Process the data
        forests = [
            {
                'name': element.get('tags', {}).get('name', 'Unknown Forest'),
                'latitude': element.get('lat'),
                'longitude': element.get('lon')
            }
            for element in data['elements'] if 'lat' in element and 'lon' in element
        ]

        return forests  # Returning data as a fruitful function result

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return []  # Return empty list on error

# Example Usage
forest_data = get_forest_data()

if forest_data:
    print("Forests in India with Coordinates:")
    for idx, forest in enumerate(forest_data, 1):
        print(f"{idx}. {forest['name']} - Lat: {forest['latitude']}, Lon: {forest['longitude']}")
else:
    print("No forest data found.")
