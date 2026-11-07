import requests
from datetime import datetime


class WeatherAgent:

    def __init__(self):
        self.geocoding_url = (
            "https://geocoding-api.open-meteo.com/v1/search"
        )
        self.forecast_url = (
            "https://api.open-meteo.com/v1/forecast"
        )
        self.session = requests.Session()
        self.timeout = 20

        self.weather_codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
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
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail"
        }

    def _get_weather_description(self, code):
        return self.weather_codes.get(
            code, "Unknown weather condition"
        )

    # --------------------------------------------------
    # 1. CITY GEOCODING
    # --------------------------------------------------

    def get_coordinates(self, city):

        if not isinstance(city, str) or not city.strip():
            raise ValueError("Please provide a valid city name.")

        params = {
            "name": city.strip(),
            "count": 1,
            "language": "en",
            "format": "json"
        }

        response = self.session.get(
            self.geocoding_url,
            params=params,
            timeout=self.timeout
        )

        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])

        if not results:
            raise ValueError(
                f"Location '{city}' could not be found."
            )

        location = results[0]

        return {
            "name": location["name"],
            "country": location.get("country"),
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "timezone": location.get("timezone")
        }

    # --------------------------------------------------
    # 2. CURRENT WEATHER + FORECAST
    # --------------------------------------------------

    def get_weather_report(self, city, forecast_days=7):

        if not isinstance(forecast_days, int) or not 1 <= forecast_days <= 16:
            raise ValueError(
                "Forecast days must be an integer between 1 and 16."
            )

        location = self.get_coordinates(city)

        params = {
            "latitude": location["latitude"],
            "longitude": location["longitude"],

            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "precipitation",
                "weather_code",
                "wind_speed_10m"
            ],

            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
                "weather_code"
            ],

            "hourly": [
                "temperature_2m",
                "precipitation_probability",
                "precipitation",
                "weather_code",
                "wind_speed_10m"
            ],

            "forecast_days": forecast_days,
            "timezone": "auto",
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm"
        }

        response = self.session.get(
            self.forecast_url,
            params=params,
            timeout=self.timeout
        )

        response.raise_for_status()
        data = response.json()

        if "error" in data:
            raise RuntimeError(
                data.get("reason", "Weather API request failed.")
            )

        if "current" not in data or "daily" not in data:
            raise RuntimeError(
                "Weather API returned incomplete data."
            )

        current = data["current"]

        # Normalize current weather
        current_weather = {
            "temperature_c": current.get("temperature_2m"),
            "feels_like_c": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "precipitation_mm": current.get("precipitation"),
            "condition": self._get_weather_description(
                current.get("weather_code")
            ),
            "weather_code": current.get("weather_code"),
            "time": current.get("time")
        }

        # Normalize daily forecast
        daily = data["daily"]
        daily_forecast = []

        for i, date in enumerate(daily["time"]):

            daily_forecast.append({
                "date": date,
                "max_temperature_c": daily["temperature_2m_max"][i],
                "min_temperature_c": daily["temperature_2m_min"][i],
                "precipitation_probability": (
                    daily["precipitation_probability_max"][i]
                ),
                "condition": self._get_weather_description(
                    daily["weather_code"][i]
                ),
                "weather_code": daily["weather_code"][i]
            })

        # Normalize next 24 hours
        hourly = data.get("hourly", {})
        hourly_forecast = []

        if hourly.get("time"):

            current_time = current.get("time", "")

            future_indices = [
                i for i, time in enumerate(hourly["time"])
                if time >= current_time
            ][:24]

            for i in future_indices:

                hourly_forecast.append({
                    "time": hourly["time"][i],
                    "temperature_c": hourly["temperature_2m"][i],
                    "precipitation_probability": (
                        hourly["precipitation_probability"][i]
                    ),
                    "precipitation_mm": hourly["precipitation"][i],
                    "wind_speed_kmh": hourly["wind_speed_10m"][i],
                    "condition": self._get_weather_description(
                        hourly["weather_code"][i]
                    )
                })

        return {
            "location": location,
            "timezone": data.get("timezone"),
            "current_weather": current_weather,
            "daily_forecast": daily_forecast,
            "hourly_forecast": hourly_forecast
        }
