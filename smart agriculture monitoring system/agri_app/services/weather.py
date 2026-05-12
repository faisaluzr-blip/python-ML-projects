import os
import random

import requests


def get_weather(city="Ludhiana"):
    key = os.getenv("OPENWEATHER_API_KEY")
    if key:
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            res = requests.get(url, params={"q": city, "appid": key, "units": "metric"}, timeout=6)
            res.raise_for_status()
            data = res.json()
            temp = data["main"]["temp"]
            humidity = data["main"]["humidity"]
            wind = data["wind"]["speed"]
            rain = data.get("rain", {}).get("1h", 0)
            return _shape(city, temp, humidity, wind, rain, live=True)
        except requests.RequestException:
            pass
    temp = random.uniform(24, 34)
    humidity = random.uniform(45, 82)
    wind = random.uniform(2, 9)
    rain = max(0, humidity - 62) * random.uniform(0.1, 0.7)
    return _shape(city, temp, humidity, wind, rain, live=False)


def _shape(city, temp, humidity, wind, rain, live):
    rain_probability = min(92, max(5, humidity * 0.7 + rain * 9))
    forecast = []
    for i in range(7):
        forecast.append(
            {
                "day": f"Day {i + 1}",
                "temperature": round(temp + random.uniform(-3, 3), 1),
                "humidity": round(min(99, max(20, humidity + random.uniform(-12, 12))), 1),
                "rain_probability": round(min(95, max(4, rain_probability + random.uniform(-18, 18))), 1),
            }
        )
    recommendation = "Rain risk is high. Pause irrigation and check drainage." if rain_probability > 60 else "Weather is stable. Irrigate based on soil moisture only."
    return {
        "city": city,
        "live": live,
        "temperature": round(temp, 1),
        "humidity": round(humidity, 1),
        "wind_speed": round(wind, 1),
        "rain_probability": round(rain_probability, 1),
        "recommendation": recommendation,
        "forecast": forecast,
    }
