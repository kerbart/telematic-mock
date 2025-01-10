from flask import Flask, render_template
from flask_socketio import SocketIO
from flask_cors import CORS
import paho.mqtt.client as mqtt
import json

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# MQTT Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "telematics/data"

# MQTT Callback Functions
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        print(f"Received MQTT message...")  # Debugging
        socketio.emit('vehicle_data', data)
        print(f"Emitted data to frontend")  # Confirm the data is sent
    except Exception as e:
        print(f"Error processing message: {e}")



# MQTT Client Setup
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

@app.route("/")
def index():
    return render_template("index.html")

# Start MQTT Loop in a separate thread
@socketio.on('connect')
def start_mqtt():
    print("Frontend connected")
    mqtt_client.loop_start()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5005)
