import random
import json
import time
from datetime import datetime
from flask_cors import CORS
import paho.mqtt.client as mqtt
from flask import Flask, jsonify

# MQTT Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "telematics/data"
MESSAGE_EXPIRY = 60  # Expire after 60 seconds (1 minute)

# Flask Application
app = Flask(__name__)
CORS(app)

# Static data for vehicles and drivers with configurable vehicle types (electric or fuel-powered)
VEHICLES = [
    {"vehicle_id": f"vehicle-{str(i).zfill(2)}", 
     "vin": f"VIN-{10000 + i}", 
     "driver_id": f"driver-{str(i).zfill(2)}", 
     "type": random.choice(["electric", "fuel-powered"])}  # Randomly assign type
    for i in range(1, 11)
]

# Define Paris and nearby coordinates
PARIS_CENTER = {"latitude": 48.8566, "longitude": 2.3522}
PARIS_RADIUS = 0.1  # Approx. ~11km radius for near-Paris locations

# State initialization
STATE = {
    vehicle["vehicle_id"]: {
        "latitude": round(PARIS_CENTER["latitude"] + random.uniform(-PARIS_RADIUS, PARIS_RADIUS), 6),
        "longitude": round(PARIS_CENTER["longitude"] + random.uniform(-PARIS_RADIUS, PARIS_RADIUS), 6),
        "speed": round(random.uniform(0, 120), 2),
        "rpm": random.randint(800, 3000) if vehicle["type"] == "fuel-powered" else None,
        "load": round(random.uniform(10, 100), 1),
        "fuel_level": round(random.uniform(5, 100), 1) if vehicle["type"] == "fuel-powered" else None,
        "battery_level": round(random.uniform(10, 100), 1) if vehicle["type"] == "electric" else None,
        "coolant_temperature": round(random.uniform(70, 110), 1),
        "battery_voltage": round(random.uniform(12, 14), 2),
        "tire_pressure": {
            "front_left": round(random.uniform(30, 36), 1),
            "front_right": round(random.uniform(30, 36), 1),
            "rear_left": round(random.uniform(30, 36), 1),
            "rear_right": round(random.uniform(30, 36), 1)
        },
        "total_km": round(random.uniform(10000, 200000), 1),
        "trip_km": round(random.uniform(0, 500), 1)
    }
    for vehicle in VEHICLES
}

# To store the latest data for each vehicle
LATEST_DATA = {}

def generate_dynamic_data(vehicle):
    state = STATE[vehicle["vehicle_id"]]

    # Update geolocation to stay near Paris
    state["latitude"] = round(PARIS_CENTER["latitude"] + random.uniform(-PARIS_RADIUS, PARIS_RADIUS), 6)
    state["longitude"] = round(PARIS_CENTER["longitude"] + random.uniform(-PARIS_RADIUS, PARIS_RADIUS), 6)

    # Update speed realistically
    state["speed"] = max(0, min(120, state["speed"] + round(random.uniform(-5, 5), 2)))

    # Update engine or battery metrics realistically
    if vehicle["type"] == "fuel-powered":
        state["rpm"] = max(800, min(3000, state["rpm"] + random.randint(-200, 200)))
        state["fuel_level"] = max(0, min(100, state["fuel_level"] - round(random.uniform(0, 0.5), 1)))
    elif vehicle["type"] == "electric":
        state["battery_level"] = max(0, min(100, state["battery_level"] - round(random.uniform(0, 1), 1)))

    state["load"] = max(10, min(100, state["load"] + round(random.uniform(-5, 5), 1)))
    state["coolant_temperature"] = max(70, min(110, state["coolant_temperature"] + round(random.uniform(-1, 1), 1)))
    state["battery_voltage"] = round(random.uniform(12, 14), 2)

    # Update tire pressures realistically
    for tire in state["tire_pressure"]:
        state["tire_pressure"][tire] = max(25, min(36, state["tire_pressure"][tire] + round(random.uniform(-0.5, 0.5), 1)))

    # Update odometer
    distance_traveled = state["speed"] * (1 / 3600)  # Distance in km based on speed
    state["total_km"] += distance_traveled
    state["trip_km"] += distance_traveled

    # Generate dynamic alerts
    alerts = []
    if vehicle["type"] == "fuel-powered" and state["fuel_level"] < 10:
        alerts.append({
            "type": "low_fuel",
            "fuel_level": state["fuel_level"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
    if vehicle["type"] == "electric" and state["battery_level"] < 15:
        alerts.append({
            "type": "low_battery",
            "battery_level": state["battery_level"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
    for tire, pressure in state["tire_pressure"].items():
        if pressure < 30:
            alerts.append({
                "type": "low_tire_pressure",
                "tire": tire,
                "pressure": pressure,
                "recommended_pressure": 35.0,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
    if state["coolant_temperature"] > 100:
        alerts.append({
            "type": "high_coolant_temperature",
            "temperature": state["coolant_temperature"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

    # Generate the dynamic data
    data = {
        "vehicle_id": vehicle["vehicle_id"],
        "vin": vehicle["vin"],
        "type": vehicle["type"],
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "location": {
            "latitude": state["latitude"],
            "longitude": state["longitude"],
            "altitude": random.randint(0, 500),
            "heading": random.randint(0, 360),
            "speed": state["speed"]
        },
        "driver": {
            "driver_id": vehicle["driver_id"],
            "name": f"Driver {vehicle['driver_id'][-2:]}",
            "hours_of_service": round(random.uniform(0, 10), 1),
            "violations": []
        },
        "engine": {
            "rpm": state["rpm"] if vehicle["type"] == "fuel-powered" else None,
            "load": state["load"],
            "fuel_level": state["fuel_level"] if vehicle["type"] == "fuel-powered" else None,
            "battery_level": state["battery_level"] if vehicle["type"] == "electric" else None,
            "coolant_temperature": state["coolant_temperature"],
            "battery_voltage": state["battery_voltage"]
        },
        "odometer": {
            "total_km": round(state["total_km"], 1),
            "trip_km": round(state["trip_km"], 1)
        },
        "tire_pressure": state["tire_pressure"],
        "alerts": alerts,
        "status": {
            "ignition": random.choice([True, False]),
            "engine_on": random.choice([True, False]),
            "moving": state["speed"] > 0
        }
    }

    # Update the latest data for this vehicle
    LATEST_DATA[vehicle["vehicle_id"]] = data

    return data

@app.route("/vehicle/<vehicle_id>")
def get_vehicle(vehicle_id):
    """REST endpoint to fetch the latest information about a vehicle."""
    data = LATEST_DATA.get(vehicle_id)
    if not data:
        return jsonify({"error": "Vehicle not found"}), 404
    return jsonify(data)

def main():
    client = mqtt.Client(protocol=mqtt.MQTTv5)  # Ensure MQTT v5 protocol
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    while True:
        selected_vehicles = random.sample(VEHICLES, random.randint(3, len(VEHICLES)))
        for vehicle in VEHICLES:
            data = generate_dynamic_data(vehicle)
            properties = mqtt.Properties(mqtt.PacketTypes.PUBLISH)
            properties.MessageExpiryInterval = MESSAGE_EXPIRY
            client.publish(MQTT_TOPIC, json.dumps(data), properties=properties)
            print(f"Published to {MQTT_TOPIC}: {data}")  # For debugging
        time.sleep(1)

if __name__ == "__main__":
    import threading
    threading.Thread(target=main).start()  # Run the MQTT simulator in a separate thread
    app.run(host="0.0.0.0", port=5008)  # Start the Flask server
