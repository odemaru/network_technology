import aiohttp
import asyncio
from colorama import init, Fore, Style
from datetime import datetime, timedelta, timezone
import pytz

init(autoreset=True)

weather = "c0f895eeaa289a4f9416ae9f4f52cdb3"
geoapify = "8de08bfe72e14c4b8ab98d4ec2f0b882"


async def fetch_json(session, url, params=None):
    async with session.get(url, params=params) as response:
        return await response.json()


async def get_locations(query):
    url = "https://api.geoapify.com/v1/geocode/search"
    params = {
        'text': query,
        'apiKey': geoapify
    }
    async with aiohttp.ClientSession() as session:
        return await fetch_json(session, url, params)


async def get_weather(lat, lon):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        'lat': lat,
        'lon': lon,
        'appid': weather,
        'units': 'metric'
    }
    async with aiohttp.ClientSession() as session:
        return await fetch_json(session, url, params)


async def get_interesting_places(lat, lon):
    url = "https://api.geoapify.com/v2/places"
    params = {
        'categories': 'tourism.sights',
        'filter': f'circle:{lon},{lat},1500',
        'limit': 10,
        'apiKey': geoapify
    }
    async with aiohttp.ClientSession() as session:
        return await fetch_json(session, url, params)


async def get_place_description(place_id):
    url = f"https://api.geoapify.com/v2/place-details"
    params = {
        'id': place_id,
        'apiKey': geoapify
    }
    async with aiohttp.ClientSession() as session:
        response = await fetch_json(session, url, params)
        return response


def get_local_time(timezone_offset):
    utc_now = datetime.now(timezone.utc)
    return utc_now + timedelta(seconds=timezone_offset)


async def main(query):
    locations = await get_locations(query)

    if not locations.get('features'):
        print(Fore.RED + "No locations found.")
        return

    for idx, loc in enumerate(locations['features']):
        name = loc['properties'].get('formatted', 'Unnamed location')
        print(Fore.CYAN + f"{idx + 1}. {name}")

    choice = int(input(Fore.YELLOW + "Choose a location number: ")) - 1
    selected_location = locations['features'][choice]
    lat = selected_location['properties']['lat']
    lon = selected_location['properties']['lon']
    print(Fore.GREEN + f"Selected location: {selected_location['properties'].get('formatted', 'Unnamed location')}")


    places_data = await get_interesting_places(lat, lon)

    description_tasks = [
        asyncio.create_task(get_place_description(place['properties']['place_id']))
        for place in places_data['features']
    ]

    weather_data = await get_weather(lat, lon)
    descriptions = await asyncio.gather(*description_tasks)

    local_time = get_local_time(weather_data['timezone'])

    print(Fore.BLUE + f"Weather: {weather_data['main']['temp']}°C")
    print(Fore.BLUE + f"Local Time: {local_time.strftime('%Y-%m-%d %H:%M:%S')}")

    for place, desc in zip(places_data['features'], descriptions):
        place_name = place['properties'].get('name', 'Unnamed place')
        description = desc.get('properties', {}).get('details', {}).get('long_description', desc.get('properties', {}).get('details',{}).get('short_description', 'No description available'))

        print(Style.BRIGHT + Fore.MAGENTA + f"Place: {place_name}")
        print(Style.DIM + Fore.WHITE + f"Description: {description}")


if __name__ == "__main__":
    place = input(Fore.YELLOW + "Enter the place name: ")
    asyncio.run(main(place))
