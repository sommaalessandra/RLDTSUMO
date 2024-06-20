import os
import pandas as pd
import string
import secrets
from datetime import datetime

def reading_files(folder):
    files = os.listdir(folder)
    data = {}
    for i, file in enumerate(files):
        file_path = os.path.join(folder, file)
        key = os.path.splitext(file)[
            0]  # remove .csv extension to use file name as key value to access the data dictionary
        data[key] = pd.read_csv(file_path)
        files[i] = key
    return data, files

def generate_random_key(length):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))

def load_env_var(file_path):
    env_vars = {}
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()  # remove whitespace
            if line and not line.startswith('#'):  # line is not a comment
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()  # removing leading or trailing spaces
    return env_vars

# function to calculate difference between actual and previous date time of dataset entries to properly simulate devices
def delay_calculation(actual_datetime, last_datetime):
    if last_datetime == -1:
        last_datetime = actual_datetime
    delta = int((actual_datetime - last_datetime).total_seconds()) / 100000
    last_datetime = actual_datetime

    return delta, last_datetime

# TODO: change/create new processing function for properly collect data from traffic loops
# def processing_bus_data(busdata, stopdata, bus):
#     last_datetime = -1
#     for index, row in busdata.iterrows():
#         latitude, longitude = find_lat_long(row, stopdata)
#         coordinates = [latitude, longitude]
#         timestamp = str(datetime.strptime(row["Time stamp"], "%Y-%m-%d %H:%M:%S"))
#         occupancy = row["Occupancy"]
#         # print(coordinates, occupancy)
#         actual_datetime = datetime.strptime(row["Actual arrival time"], "%Y-%m-%d %H:%M:%S")
#         for sensor in bus.sensors:
#             if sensor.name == "GPS":
#                 sensor.send_data(coordinates, timestamp, str(actual_datetime), device_id=sensor.device_id, device_key=sensor.api_key)
#             elif sensor.name == "APC":
#                 sensor.send_data(occupancy, timestamp, str(actual_datetime), device_id=sensor.device_id, device_key=sensor.api_key)
#         delta, last_datetime = delay_calculation(actual_datetime, last_datetime)
#         # print(delta)
#         time.sleep(delta)

# TODO: handle multiple hours time-slots in such a way that the sending of data is proportional
#  to the time of the measurement
def processingTlData(trafficData, trafficLoop):
    # for index, row in trafficData.iterrows():
    #     direction = row["direzione"]
    # iterate through collected data
    for key, values in trafficData.items():
        # iterate through registered devices
        for ind,device in trafficLoop.items():
            # look for sensor belonging to device (only one in the traffic loop case)
            for sensor in device.sensors:
                if sensor.name == "TFO":
                    tl = values.loc[values["ID_loop"] == sensor.device_partial_id]
                    flow = tl["00:00-01:00"].values[0]
                    coordinates = str(tl["geopoint"].values[0])
                    direction = str(tl["direzione"].values[0])
                    sensor.send_data(flow, coordinates, direction,device_id=sensor.device_partial_id, device_key=sensor.api_key)

