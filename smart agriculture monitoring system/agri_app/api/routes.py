from pathlib import Path

from flask import Blueprint, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename

from ..database import User, get_connection
from ..ml.engine import analyze_soil, disease_from_image, predict_price, recommend_crop, sensor_snapshot
from ..services.reports import build_pdf_report, build_sensor_csv
from ..services.weather import get_weather


bp = Blueprint("routes", __name__)
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("routes.dashboard"))
    return redirect(url_for("routes.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = User.authenticate(request.form.get("email", ""), request.form.get("password", ""))
        if user:
            login_user(user)
            return redirect(url_for("routes.dashboard"))
        error = "Invalid email or password"
    return render_template("login.html", error=error)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("routes.login"))


@bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user)


@bp.get("/api/sensors")
@login_required
def api_sensors():
    snapshot = sensor_snapshot()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO sensor_logs(soil_moisture,temperature,humidity,ph,nitrogen,phosphorus,potassium)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                snapshot["soil_moisture"],
                snapshot["temperature"],
                snapshot["humidity"],
                snapshot["ph"],
                snapshot["nitrogen"],
                snapshot["phosphorus"],
                snapshot["potassium"],
            ),
        )
        conn.commit()
    alerts = []
    if snapshot["soil_moisture"] < 35:
        alerts.append({"title": "Low soil moisture", "message": "Zone A requires irrigation within 30 minutes.", "severity": "danger"})
    if snapshot["temperature"] > 33:
        alerts.append({"title": "Heat stress risk", "message": "Increase canopy cooling and inspect crop stress.", "severity": "warning"})
    if snapshot["crop_health"] < 58:
        alerts.append({"title": "Crop health declining", "message": "Run disease scan and soil analysis.", "severity": "danger"})
    return jsonify({"snapshot": snapshot, "alerts": alerts})


@bp.get("/api/history")
@login_required
def api_history():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT soil_moisture, temperature, humidity, ph, created_at FROM sensor_logs ORDER BY id DESC LIMIT 40"
        ).fetchall()
    return jsonify([dict(row) for row in rows][::-1])


@bp.post("/api/disease")
@login_required
def api_disease():
    file = request.files.get("image")
    if not file:
        return jsonify({"error": "Upload an image file."}), 400
    filename = secure_filename(file.filename or "leaf.jpg")
    path = UPLOAD_DIR / filename
    file.save(path)
    try:
        result = disease_from_image(path)
        result["image_url"] = f"/uploads/{filename}"
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.post("/api/soil")
@login_required
def api_soil():
    return jsonify(analyze_soil(request.json or {}))


@bp.post("/api/crop-recommendation")
@login_required
def api_crop_recommendation():
    return jsonify(recommend_crop(request.json or {}))


@bp.get("/api/weather")
@login_required
def api_weather():
    return jsonify(get_weather(request.args.get("city", "Ludhiana")))


@bp.post("/api/irrigation")
@login_required
def api_irrigation():
    data = request.json or {}
    moisture = float(data.get("moisture", 45))
    crop = data.get("crop", "Wheat")
    acreage = float(data.get("acreage", 5))
    target = 64 if crop in ["Rice", "Sugarcane"] else 55
    deficit = max(0, target - moisture)
    liters = round(deficit * acreage * 185, 1)
    saving = round(max(0, (70 - moisture) * 2.4), 1)
    return jsonify(
        {
            "mode": "Auto irrigation recommended" if deficit > 8 else "Hold irrigation",
            "water_required_liters": liters,
            "water_saving_percent": saving,
            "alert": "Open drip valve for Zone B" if deficit > 12 else "Moisture level is acceptable",
        }
    )


@bp.post("/api/market")
@login_required
def api_market():
    return jsonify(predict_price(request.json or {}))


@bp.post("/api/chat")
@login_required
def api_chat():
    message = (request.json or {}).get("message", "").lower()
    language = (request.json or {}).get("language", "English")
    if "disease" in message or "leaf" in message:
        reply = "Upload a clear leaf image in the disease module. Meanwhile isolate affected plants and avoid overhead watering."
    elif "water" in message or "irrigation" in message:
        reply = "Use pulse irrigation when moisture is below 40%. Current smart control can estimate exact liters by crop and acreage."
    elif "fertilizer" in message or "npk" in message:
        reply = "Run soil analysis. If nitrogen is below 55, use compost or a small urea dose; rebalance phosphorus and potassium separately."
    elif "price" in message or "market" in message:
        reply = "Check the market module. Higher demand with falling supply usually signals a better selling window in the next 2-4 weeks."
    else:
        reply = "I can help with crop choice, disease prevention, weather risk, irrigation, NPK balance, and price planning."
    if language != "English":
        reply = f"[{language}] {reply}"
    return jsonify({"reply": reply})


@bp.get("/api/admin")
@login_required
def api_admin():
    with get_connection() as conn:
        farmers = [dict(row) for row in conn.execute("SELECT * FROM farmers").fetchall()]
        records = [dict(row) for row in conn.execute("SELECT * FROM crop_records ORDER BY id DESC LIMIT 10").fetchall()]
        sensor_count = conn.execute("SELECT COUNT(*) count FROM sensor_logs").fetchone()["count"]
    return jsonify({"farmers": farmers, "records": records, "system": {"sensor_events": sensor_count, "model_status": "Online", "api_latency_ms": 42}})


@bp.post("/api/admin/farmers")
@login_required
def api_add_farmer():
    data = request.json or {}
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO farmers(name,location,crop,acreage,status) VALUES(?,?,?,?,?)",
            (data.get("name", "New Farmer"), data.get("location", "Unknown"), data.get("crop", "Wheat"), float(data.get("acreage", 1)), data.get("status", "Active")),
        )
        conn.commit()
    return jsonify({"ok": True})


@bp.get("/api/export/csv")
@login_required
def export_csv():
    with get_connection() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM sensor_logs ORDER BY id DESC LIMIT 100").fetchall()]
    csv_data = build_sensor_csv(rows)
    return send_file(
        __import__("io").BytesIO(csv_data.encode("utf-8")),
        as_attachment=True,
        download_name="sensor_export.csv",
        mimetype="text/csv",
    )


@bp.get("/api/export/pdf")
@login_required
def export_pdf():
    snap = sensor_snapshot()
    soil = analyze_soil({"n": snap["nitrogen"], "p": snap["phosphorus"], "k": snap["potassium"], "ph": snap["ph"], "organic": 2.6, "moisture": snap["soil_moisture"]})
    crop = recommend_crop({"soil_type": "Loamy", "temperature": snap["temperature"], "humidity": snap["humidity"], "rainfall": 120, "ph": snap["ph"], "water": snap["soil_moisture"]})
    pdf = build_pdf_report(snap, soil, crop)
    return send_file(pdf, as_attachment=True, download_name="agriculture_report.pdf", mimetype="application/pdf")


@bp.route("/uploads/<path:filename>")
@login_required
def uploads(filename):
    return send_file(UPLOAD_DIR / filename)
