import os
import re
import google.generativeai as genai
import requests

# === API Keys ===
GOOGLE_API_KEY = "AIzaSyBTSqnDhr7assffH0B5Qn5NEcyg0YUSNMM"
WEATHER_API_KEY = "a8d346daaedf6c4ad14781551c813db2"
GEMINI_API_KEY = "AIzaSyBRdwktUscXyQ3WxSSRdqTVuEqEHoeVU8Q"

# Configure Gemini (only needs to be done once)
genai.configure(api_key=GEMINI_API_KEY)

# === Utils ===
def get_places(latlon, interest):
    latlon_str = f"{latlon['lat']},{latlon['lon']}"
    endpoint = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": latlon_str,
        "radius": 1000,
        "keyword": interest,
        "key": GOOGLE_API_KEY
    }
    response = requests.get(endpoint, params=params)
    places = response.json().get("results", [])[:5]
    return [{
        "name": p["name"],
        "lat": p["geometry"]["location"]["lat"],
        "lng": p["geometry"]["location"]["lng"]
    } for p in places]

def get_weather_forecast(lat, lon):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": WEATHER_API_KEY,
        "units": "metric"
    }
    res = requests.get(url, params=params)
    data = res.json()
    if "weather" in data and data["weather"]:
        return {
            "description": data["weather"][0]["description"],
            "temp": data["main"]["temp"],
            "humidity": data["main"]["humidity"]
        }
    return {}

def get_distance_matrix(origins, destinations):
    origin_str = "|".join(origins)
    dest_str = "|".join(destinations)
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": origin_str,
        "destinations": dest_str,
        "key": GOOGLE_API_KEY,
        "mode": "driving"
    }
    res = requests.get(url, params=params)
    return res.json()

def get_coordinates_for_places(place_names):
    coords = []
    for name in place_names:
        url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        params = {
            "input": name,
            "inputtype": "textquery",
            "fields": "geometry",
            "key": GOOGLE_API_KEY
        }
        res = requests.get(url, params=params).json()
        try:
            location = res["candidates"][0]["geometry"]["location"]
            coords.append({
                "name": name,
                "lat": location["lat"],
                "lng": location["lng"]
            })
        except:
            continue
    return coords

def extract_locations_by_day_and_slot(text):
    itinerary = {}
    current_day = None
    current_slot = None

    lines = text.splitlines()

    for line in lines:
        line = line.strip()

        if re.match(r'^Day\s*\d+', line, re.IGNORECASE):
            current_day = line.strip()
            itinerary[current_day] = {}
            current_slot = None
            continue

        if re.match(r'^(Morning|Afternoon|Evening)', line, re.IGNORECASE):
            current_slot = line.strip().capitalize()
            if current_day:
                itinerary[current_day][current_slot] = []
            continue

        if current_day and current_slot and line:
            clean_line = re.sub(r'^[\u2022\-\*\d\.\s]+', '', line)
            match = re.search(
                r'(Visit|Explore|Head to|Then|Start at|Stop at|End at|Enjoy|See|Walk around|Check out)?\s*(.*)',
                clean_line,
                re.IGNORECASE
            )
            if match:
                place = match.group(2).strip()
                if place and len(place.split()) <= 8 and not place.lower().startswith(
                    ("return", "relax", "rest", "lunch", "dinner", "free time")
                ):
                    itinerary[current_day][current_slot].append(place)

    return itinerary

# === Itinerary Generation Logic ===
def generate_itinerary_data(lat, lon, days, interests):
    # Step 1: Get suggested places & weather
    suggested_places = get_places({'lat': lat, 'lon': lon}, interests)
    weather = get_weather_forecast(lat, lon)

    # Step 2: Create prompt for AI
    prompt = f"""
    Create a {days}-day travel itinerary near {lat},{lon} for a traveler interested in {interests}.
    Current weather is {weather.get('description', 'clear')} with temperature around {weather.get('temp', '25')}°C and humidity {weather.get('humidity', '60')}%.
    Suggested places to consider: {[p['name'] for p in suggested_places]}.
    Group nearby places together by morning, afternoon, and evening slots.
    Use bullet points for places.
    """

    
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)
    itinerary_text = response.text if hasattr(response, "text") else "No itinerary generated."

    # Step 3: Extract structured itinerary
    day_wise_places = extract_locations_by_day_and_slot(itinerary_text)

    # Step 4: Get travel segments
    travel_segments = []

    for day, slots in day_wise_places.items():
        for slot, places in slots.items():
            coords = get_coordinates_for_places(places)
            if len(coords) < 2:
                continue
            names = [p['name'] for p in coords]
            latlngs = [f"{p['lat']},{p['lng']}" for p in coords]

            for i in range(len(latlngs) - 1):
                result = get_distance_matrix([latlngs[i]], [latlngs[i + 1]])
                if "rows" in result and "elements" in result["rows"][0]:
                    element = result["rows"][0]["elements"][0]
                    duration = element.get("duration", {}).get("text", "N/A")
                    distance = element.get("distance", {}).get("text", "N/A")
                    travel_segments.append(f"{day} - {slot}: {names[i]} → {names[i+1]} = {duration}, {distance}")
                else:
                    travel_segments.append(f"{day} - {slot}: {names[i]} → {names[i+1]} = N/A")

    return itinerary_text, travel_segments
