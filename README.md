# Telematic Box Simulator

`telematic-generator-mqtt.py` will create fake telematic box data and put them in an mqtt.

data can be retrieve in mqtt or with a Rest API

## setup
Activate python virutal env

```
source simulation/bin/activate
```

pip install all deps

```
pip install flask flask-socketio flask-cors paho-mqtt
```

## run mqtt docker container

```
docker-compose up -d
```

## run event generator

```
python telematic-generator-mqtt.py
```

## display mqtt messages
(need mosquitto binaries installed and jq for pretty printing)

```
mosquitto_sub -h localhost -t telematics/data | jq
```

## mini app to display vehicles

```
python app.py 
```

then go to http://localhost:5005/