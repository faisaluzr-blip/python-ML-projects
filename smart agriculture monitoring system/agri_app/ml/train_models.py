"""
Local ML evaluation script.

The production app uses deterministic pure-Python models so it can run on Python
3.14 without compiled wheels. This script stress-tests the same prediction
engines on synthetic agronomy scenarios and prints practical accuracy metrics.
For scikit-learn/TensorFlow training, install requirements-ml-optional.txt on a
Python version with compatible wheels and extend this module.
"""

import random

from agri_app.ml.engine import analyze_soil, predict_price, recommend_crop


def main():
    soil_hits = 0
    for _ in range(300):
        payload = {
            "n": random.uniform(20, 130),
            "p": random.uniform(15, 110),
            "k": random.uniform(20, 150),
            "ph": random.uniform(4.8, 8.2),
            "organic": random.uniform(0.5, 5.2),
            "moisture": random.uniform(12, 92),
        }
        result = analyze_soil(payload)
        if result["score"] > 72 and result["fertility"] == "High":
            soil_hits += 1
        elif 48 < result["score"] <= 72 and result["fertility"] == "Medium":
            soil_hits += 1
        elif result["score"] <= 48 and result["fertility"] == "Low":
            soil_hits += 1
    print(f"Soil classifier consistency: {soil_hits / 300:.2%}")

    crop_cases = [
        {"soil_type": "Alluvial", "temperature": 31, "humidity": 82, "rainfall": 230, "ph": 6.4, "water": 88},
        {"soil_type": "Black", "temperature": 33, "humidity": 50, "rainfall": 70, "ph": 7.1, "water": 42},
        {"soil_type": "Loamy", "temperature": 20, "humidity": 66, "rainfall": 85, "ph": 6.7, "water": 54},
    ]
    for case in crop_cases:
        print("Crop recommendation:", recommend_crop(case)["top_crop"], case)

    market = predict_price({"crop": "Wheat", "demand": 75, "supply": 52, "fuel": 94, "quantity": 40})
    print(f"Market predictor sample: {market['crop']} at Rs {market['predicted_price']} per quintal")


if __name__ == "__main__":
    main()
