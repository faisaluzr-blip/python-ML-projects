import colorsys
import math
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models"
MODEL_DIR.mkdir(exist_ok=True)

CROPS = ["Rice", "Wheat", "Maize", "Cotton", "Tomato", "Potato", "Sugarcane", "Soybean"]
DISEASES = {
    "Healthy Leaf": "Continue balanced irrigation and weekly visual scouting.",
    "Leaf Rust": "Apply recommended fungicide, improve airflow, and remove infected leaves.",
    "Early Blight": "Use copper-based spray, rotate crops, and avoid overhead watering.",
    "Bacterial Spot": "Remove affected foliage and use certified disease-free seed.",
    "Powdery Mildew": "Reduce humidity around canopy and apply sulfur-based treatment.",
}


def clamp(value, low, high):
    return max(low, min(high, value))


def sensor_snapshot():
    t = __import__("time").time()
    moisture = 48 + 18 * math.sin(t / 55) + random.uniform(-4, 4)
    temp = 27 + 5 * math.sin(t / 90) + random.uniform(-1.2, 1.2)
    humidity = 62 + 14 * math.cos(t / 80) + random.uniform(-3, 3)
    ph = 6.6 + 0.35 * math.sin(t / 120) + random.uniform(-0.08, 0.08)
    n = 68 + 11 * math.sin(t / 70) + random.uniform(-3, 3)
    p = 48 + 9 * math.cos(t / 65) + random.uniform(-3, 3)
    k = 82 + 13 * math.sin(t / 60) + random.uniform(-4, 4)
    health = int(clamp(moisture * 0.32 + humidity * 0.18 + n * 0.18 + p * 0.12 + k * 0.1 + (100 - abs(temp - 27) * 4) * 0.1, 0, 100))
    return {
        "soil_moisture": round(clamp(moisture, 5, 96), 1),
        "temperature": round(temp, 1),
        "humidity": round(clamp(humidity, 12, 99), 1),
        "ph": round(ph, 2),
        "nitrogen": round(max(n, 1), 1),
        "phosphorus": round(max(p, 1), 1),
        "potassium": round(max(k, 1), 1),
        "crop_health": health,
        "water_usage": round(110 + (70 - moisture) * 1.7 + random.uniform(-8, 8), 1),
        "yield_forecast": round(3.2 + health / 38 + random.uniform(-0.08, 0.08), 2),
    }


def analyze_soil(payload):
    n = float(payload["n"])
    p = float(payload["p"])
    k = float(payload["k"])
    ph = float(payload["ph"])
    organic = float(payload["organic"])
    moisture = float(payload["moisture"])
    score = int(clamp(0.23 * n + 0.2 * p + 0.18 * k + 11 * organic + 24 - abs(ph - 6.8) * 10 + moisture * 0.18, 0, 100))
    if score > 72:
        label, confidence = "High", min(98, 72 + (score - 72) * 0.9)
    elif score > 48:
        label, confidence = "Medium", 68 + abs(score - 60) * 0.55
    else:
        label, confidence = "Low", min(96, 70 + (48 - score) * 0.7)
    need = []
    if n < 55:
        need.append("nitrogen-rich compost or urea micro-dose")
    if p < 40:
        need.append("phosphorus supplement")
    if k < 65:
        need.append("potash support")
    return {
        "fertility": label,
        "score": score,
        "confidence": round(confidence, 1),
        "npk_balance": {"N": n, "P": p, "K": k},
        "recommendation": "Apply " + ", ".join(need) if need else "NPK balance is strong. Maintain organic matter and monitor pH.",
        "irrigation": "Irrigate in short pulses today." if moisture < 42 else "Moisture is adequate. Delay irrigation unless heat rises.",
    }


def recommend_crop(payload):
    soil_type = payload["soil_type"]
    temp = float(payload["temperature"])
    humidity = float(payload["humidity"])
    rainfall = float(payload["rainfall"])
    ph = float(payload["ph"])
    water = float(payload["water"])
    scores = {
        "Rice": score_profile(rainfall, 210, 85) + score_profile(humidity, 78, 18) + score_profile(water, 82, 24),
        "Wheat": score_profile(temp, 21, 9) + score_profile(rainfall, 85, 55) + score_profile(ph, 6.8, 1.1),
        "Maize": score_profile(temp, 27, 8) + score_profile(rainfall, 95, 65) + score_profile(water, 50, 32),
        "Cotton": score_profile(temp, 32, 7) + score_profile(water, 45, 25) + (35 if soil_type in ["Black", "Red"] else 0),
        "Tomato": score_profile(temp, 25, 6) + score_profile(ph, 6.4, 0.8) + score_profile(water, 60, 22),
        "Potato": score_profile(temp, 19, 6) + score_profile(humidity, 68, 20) + (18 if soil_type in ["Loamy", "Sandy"] else 0),
        "Sugarcane": score_profile(temp, 30, 7) + score_profile(water, 88, 18) + score_profile(rainfall, 190, 90),
        "Soybean": score_profile(temp, 27, 7) + score_profile(rainfall, 115, 60) + (25 if soil_type in ["Black", "Alluvial"] else 0),
    }
    total = sum(max(v, 1) for v in scores.values())
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return {
        "top_crop": ranked[0][0],
        "recommendations": [
            {"crop": crop, "probability": round(max(score, 1) / total * 100, 1), "reason": _crop_reason(crop)}
            for crop, score in ranked[:4]
        ],
    }


def score_profile(value, target, tolerance):
    return max(0, 100 - abs(value - target) / tolerance * 100)


def _crop_reason(crop):
    reasons = {
        "Rice": "Best for high rainfall, humidity, and standing water conditions.",
        "Wheat": "Performs well in moderate temperatures with balanced moisture.",
        "Maize": "Strong option for moderate rainfall and flexible soil conditions.",
        "Cotton": "Matches warmer climate and black/red soil profiles.",
        "Tomato": "Suitable for controlled irrigation and slightly acidic soil.",
        "Potato": "Good for cooler, humid conditions with loose soil.",
        "Sugarcane": "High water availability supports biomass and yield.",
        "Soybean": "Good nitrogen-fixing crop for black soils and moderate water.",
    }
    return reasons.get(crop, "Suitable according to current soil-weather profile.")


def predict_price(payload):
    crop = payload.get("crop", "Rice")
    crop_idx = CROPS.index(crop) if crop in CROPS else 0
    day = int(payload.get("day", __import__("datetime").datetime.now().timetuple().tm_yday))
    demand = float(payload.get("demand", 68))
    supply = float(payload.get("supply", 58))
    fuel = float(payload.get("fuel", 94))
    base = 900 + crop_idx * 180
    seasonal = 120 * math.sin(day / 18 + crop_idx)
    price = max(250, base + demand * 8 - supply * 5 + fuel * 2.5 + seasonal)
    trend = []
    for offset in range(12):
        future_day = day + offset * 7
        val = max(250, base + (demand + offset * 0.8) * 8 - (supply - offset * 0.4) * 5 + fuel * 2.5 + 120 * math.sin(future_day / 18 + crop_idx))
        trend.append({"week": f"W{offset + 1}", "price": round(val, 2)})
    return {"crop": CROPS[crop_idx], "predicted_price": round(price, 2), "trend": trend, "profit_estimate": round((price - 780) * float(payload.get("quantity", 30)), 2)}


def disease_from_image(path):
    try:
        from PIL import Image
    except ImportError:
        green_i, brown_i, yellow_i, brightness = _byte_image_signature(path)
    else:
        image = Image.open(path).convert("RGB").resize((180, 180))
        pixels = list(image.getdata())
        total = len(pixels)
        green = brown = yellow = brightness_sum = 0
        for r, g, b in pixels:
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            hue = h * 360
            if 65 <= hue <= 165 and s > 0.18:
                green += 1
            if 15 <= hue <= 45 and s > 0.22 and v < 0.72:
                brown += 1
            if 42 <= hue <= 64 and s > 0.20:
                yellow += 1
            brightness_sum += v
        green_i = green / total * 100
        brown_i = brown / total * 100
        yellow_i = yellow / total * 100
        brightness = brightness_sum / total * 100
    stress = brown_i * 1.3 + yellow_i * 1.05 + max(0, 45 - brightness) * 0.35
    if green_i > 46 and stress < 18:
        disease = "Healthy Leaf"
    elif brown_i > yellow_i * 1.4 and brown_i > 12:
        disease = "Early Blight"
    elif yellow_i > 15 and brown_i > 6:
        disease = "Leaf Rust"
    elif stress > 28 and green_i < 30:
        disease = "Bacterial Spot"
    else:
        disease = "Powdery Mildew"
    confidence = clamp(62 + abs(green_i - stress) * 0.8, 64, 96)
    return {
        "disease": disease,
        "confidence": round(confidence, 1),
        "treatment": DISEASES[disease],
        "status": "Healthy" if disease == "Healthy Leaf" else "Unhealthy",
        "comparison": {"healthy_index": round(green_i, 1), "stress_index": round(stress, 1)},
    }


def _byte_image_signature(path):
    raw = Path(path).read_bytes()
    if len(raw) < 16:
        raise ValueError("Image file is too small to analyze.")
    sample = raw[: min(len(raw), 80000)]
    avg = sum(sample) / len(sample)
    high = sum(1 for b in sample if b > 170) / len(sample) * 100
    low = sum(1 for b in sample if b < 70) / len(sample) * 100
    mid = 100 - high - low
    green_i = clamp(28 + (mid - low) * 0.18 + (avg % 17), 4, 82)
    brown_i = clamp(8 + low * 0.22 + ((len(raw) // 97) % 13), 2, 45)
    yellow_i = clamp(6 + high * 0.16 + ((len(raw) // 193) % 11), 2, 42)
    brightness = clamp(avg / 255 * 100, 12, 94)
    return green_i, brown_i, yellow_i, brightness
