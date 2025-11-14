import requests
import streamlit as st
from dotenv import load_dotenv
load_dotenv()


def get_directions(origin: str, destination: str) -> dict:
    """
    Tool to retrieve step-by-step textual driving directions between two 
    addresses.

    This tool sends a request to the Google Maps Directions API to generate
    navigation instructions from the specified origin to destination. The
    response includes each maneuver (e.g., turns, exits, and road names) 
    formatted as human-readable text.

    Args:
        origin (str): Starting address or location of the user.
            - e.g., "Kochi, Kerala"
        destination (str): Destination address or location of the user.
            - e.g., "Thrissur, Kerala"

    Returns:
        dict: A dictionary containing:
            - status (str): Indicates the operation result 
                - "success", "not_found", or "error".

            On success:
            A dictionary containing:
                - directions (str): Step-by-step navigation directions, each on 
                    a new line and numbered sequentially.
                    e.g.,
                        1. Head north on NH544 toward Angamaly
                        2. Continue straight to stay on NH544
                        3. Take the exit toward Thrissur

            On error:
            - message (str): Brief description of the error.
    """
    GMAPS_API_KEY = st.secrets["GOOGLE_MAPS_DISTANCE_MATRIX_API_KEY"]
    GMAPS_DIRECTIONS_BASE_URL = "https://maps.googleapis.com/maps/api/directions/json"

    params = {
        "origin": origin,
        "destination": destination,
        "mode": "driving",
        "key": GMAPS_API_KEY
    }

    response = requests.get(GMAPS_DIRECTIONS_BASE_URL, params=params)
    data = response.json()

    if data["status"] != "OK":
        return {
            "status": "error",
            "error": data.get("status", "API Error"),
            "details": data.get("error_message", "")
        }

    route = data["routes"][0]["legs"][0]
    directions = [
        step["html_instructions"]
        for step in route["steps"]
    ]

    directions = "\n".join(
        f"{idx + 1}. {step}" for idx, step in enumerate(directions)
    )

    return {
        "status": "success",
        "directions": directions
    }


def get_weather(district: str, state: str, zipcode: str) -> dict:
    if district and state and zipcode:
        address = f"{district}, {state}-{zipcode}"

        GEOCODE_URL = f"https://nominatim.openstreetmap.org/search?q={address}&format=json"
        
        geocoding_response = requests.get(
            GEOCODE_URL, 
            headers={"User-Agent": "logiq-engineers-navigation-agent"}
        ).json()

        if not geocoding_response:
            return {
                "status": "error", 
                "message": "Location not found."
            }

        else:
            lat = geocoding_response[0]['lat']
            lon = geocoding_response[0]['lon']

            WEATHER_URL = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            weather_res = requests.get(WEATHER_URL).json()

            if "current_weather" in weather_res:
                weather = weather_res["current_weather"]
                condition_code = weather.get("weathercode", 0)

                weather_conditions = {
                    0:  "Clear sky",
                    1:  "Mainly clear",
                    2:  "Partly cloudy",
                    3:  "Overcast",
                    45: "Fog",
                    48: "Depositing rime fog",
                    51: "Light drizzle",
                    53: "Moderate drizzle",
                    55: "Dense drizzle",
                    56: "Light freezing drizzle",
                    57: "Dense freezing drizzle",
                    61: "Slight rain",
                    63: "Moderate rain",
                    65: "Heavy rain",
                    66: "Light freezing rain",
                    67: "Heavy freezing rain",
                    71: "Slight snow fall",
                    73: "Moderate snow fall",
                    75: "Heavy snow fall",
                    77: "Snow grains",
                    80: "Slight rain showers",
                    81: "Moderate rain showers",
                    82: "Violent rain showers",
                    85: "Slight snow showers",
                    86: "Heavy snow showers",
                    95: "Thunderstorm (slight or moderate)",
                    96: "Thunderstorm with slight hail",
                    99: "Thunderstorm with heavy hail"
                }

                description = weather_conditions.get(
                    condition_code, 
                    f"Unknown. Weather code: {condition_code}"
                )

                return {
                    "status": "success",
                    "weather": {
                        "description": description,
                        "temperature (°C)": weather["temperature"],
                        "windspeed (km/h)": weather["windspeed"],
                        "winddirection (°)": weather["winddirection"],
                    }
                }

            else:
                return {
                    "status": "error", 
                    "message": "Weather data not available."
                }
            


def get_traffic_eta(origin: str, destination: str) -> dict:
    """
    Tool to retrieve real-time traffic information and estimated travel time 
    between two addresses.

    This tool sends a request to the Google Maps Directions API to calculate
    the distance, typical travel duration, and the estimated duration 
    considering current traffic conditions.

    Args:
        origin (str): Starting address or location of the user.
            - e.g., "Kochi, Kerala"
        destination (str): Destination address or location of the user.
            - e.g., "Thrissur, Kerala"

    Returns:
        dict: A dictionary containing:
            - status (str): Indicates the operation result 
                - "success", "not_found", or "error".

            On success:
            A dictionary containing:
                - origin (str): Formatted starting address.
                - destination (str): Formatted destination address.
                - distance (str): Human-readable distance (e.g., "10 km").
                - duration (str): Human-readable duration (e.g., "30 mins").
                - duration_in_traffic (str): Duration in traffic (e.g., "45 
                  mins").

            On error:
            - error (str): Error code from the API.
            - details (str): Additional error details if available.
    """
    GMAPS_API_KEY = st.secrets["GOOGLE_MAPS_DISTANCE_MATRIX_API_KEY"]
    GMAPS_DIRECTIONS_BASE_URL = "https://maps.googleapis.com/maps/api/directions/json"

    params = {
        "origin": origin,
        "destination": destination,
        "departure_time": "now",
        "traffic_model": "best_guess",
        "key": GMAPS_API_KEY
    }

    response = requests.get(GMAPS_DIRECTIONS_BASE_URL, params=params)
    data = response.json()

    if data["status"] != "OK":
        return {
            "status": "error",
            "error": data.get("status", "API Error"),
            "details": data.get("error_message", "No error details available.")
        }

    route = data["routes"][0]["legs"][0]
    result = {
        "origin": route["start_address"],
        "destination": route["end_address"],
        "distance": route["distance"]["text"],
        "duration": route["duration"]["text"],
        "duration_in_traffic": route.get(
            "duration_in_traffic", route["duration"]
        )["text"],
    }

    return {
        "status": "success",
        "traffic_data": result
    }


def get_engineer_address(engineer_id: str) -> dict:
    """
    Tool to retrieve the address details of a field engineer based on their 
    unique ID.

    This tool simulates a lookup in a database or directory to fetch the 
    address information associated with the provided engineer ID.

    Args:
        engineer_id (str): Unique identifier for the field engineer.
            - e.g., "ENG12345"

    Returns:
        dict: A dictionary containing:
            - status (str): Indicates the operation result 
                - "success" or "not_found".

            On success:
            A dictionary containing:
                - district (str): District of the engineer's address.
                - state (str): State of the engineer's address.
                - zipcode (str): Zipcode of the engineer's address.

            On not found:
            - message (str): Brief description indicating no data found.
    """
    pass