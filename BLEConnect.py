from time import sleep

from bleak import BleakClient, discover
from bleak.exc import BleakDotNetTaskError, BleakError
import asyncio
import pandas as pd
import os
import sys
from os import path
import datetime
import threading
from datetime import datetime, timedelta
from collections import defaultdict
import matplotlib
import warnings
import RPi.GPIO as GPIO
import struct
warnings.simplefilter("ignore", UserWarning)
sys.coinit_flags = 2


from parse_data import plt


adc_data = {}
accel_data = {}
gyro_data = {}
figure_shown=0
lines = []
DEVICE_NAME = 'GUTRUF LAB v1.BAT_MON'
LED_PIN = 27
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
pin_flash_cycle_duration = 0
DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), "data/streamed_data.csv")
DATA_FOLDER_PATH = os.path.join(os.path.dirname(__file__), "data")
characteristic_names = {
     39: 'Temperature:',
     43: 'Strain:',
     54: 'Gyro_X:',
     58: 'Gyro_Y:',
     62: 'Gyro_Z:',
     66: 'Accel_X:',
     70: 'Accel_Y:',
     74: 'Accel_Z:',
}


def check_data():
    global adc_data
    global accel_data
    global gyro_data
    store_data = False
    # Create new dict to populate and convert to data frame
    packaged_data = {"Time:": [datetime.datetime.now()]}

    # Check if the adc data is ready, if so prepend it. Otherwise use empty strings
    if len(adc_data.keys()) > 1:
        packaged_data['Temperature:'] = adc_data.pop('Temperature:')
        packaged_data['Strain:'] = adc_data.pop('Strain:')
        store_data = True
    else:
        packaged_data['Temperature:'] = ""
        packaged_data['Strain:'] = ""

    # Make sure both accelerometer and gyro data dicts are populated
    if (len(accel_data.keys()) > 2) and (len(gyro_data.keys()) > 2):
        store_data = True
        # Insert XYZ accelerometer and gyroscope
        for key in sorted(accel_data.keys()):
            packaged_data[key] = accel_data.pop(key)[0]

        for key in sorted(gyro_data.keys()):
            packaged_data[key] = gyro_data.pop(key)[0]

    else:
        packaged_data['Gyro_X:'] = ""
        packaged_data['Gyro_Y:'] = ""
        packaged_data['Gyro_Z:'] = ""
        packaged_data['Accel_X:'] = ""
        packaged_data['Accel_Y:'] = ""
        packaged_data['Accel_Z:'] = ""

    if store_data:
        print(Datetime.)
        print(packaged_data)
        # Create dataframe from packaged data disc and write to CSV file
        new_df = pd.DataFrame(packaged_data)
        new_df.to_csv(DATA_FILE_PATH,
                      index=False,
                      header=False,
                      mode='a'  # append data to csv file
                      )


def adc_notification_handler(sender, data):
    global adc_data
    global pin_flash_cycle_duration
    char_name = characteristic_names[sender]
    if char_name == 'Temperature:':
        GPIO.output(LED_PIN, 1)
        pin_flash_cycle_duration += 1

    print(sender, int.from_bytes(data, byteorder='little'))
    adc_data[char_name] = [int.from_bytes(data, byteorder='little')]
    adc_data[char_name] = [int.from_bytes(data, byteorder='little')]

    if char_name == 'Temperature:' and pin_flash_cycle_duration >= 5:
        GPIO.output(LED_PIN, 0)
        pin_flash_cycle_duration = 0

    if len(adc_data.keys()) > 1:
        print(adc_data)
        check_data()


def gyro_notification_handler(sender, data):
    global gyro_data
    # Convert characteristic id number to corresponding characteristic name
    char_name = characteristic_names[sender]
    print(char_name, sender, data, struct.unpack('f', data))
    gyro_data[char_name] = [struct.unpack('f', data)]
    check_data()


def accel_notification_handler(sender, data):
    global accel_data
    char_name = characteristic_names[sender]
    print(char_name, sender, struct.unpack('f', data))
    accel_data[char_name] = [struct.unpack('f', data)]
    check_data()


async def run(event_loop):

    while True:
        address = ''
        try:
            while address == '':
                devices = await discover(timeout=1)
                for d in devices:
                    print(d)
                    if d.name == DEVICE_NAME:
                        address = d.address
                        print('Device found.')
                print('----')

            async with BleakClient(address, loop=event_loop) as client:
                x = await client.is_connected()

                disconnected_event = asyncio.Event()

                def disconnect_callback(client, future):
                    print("Disconnected callback called!")
                    loop.call_soon_threadsafe(disconnected_event.set)
                    print("Connection lost. Retrying...")

                client.set_disconnected_callback(disconnect_callback)

                services = await client.get_services()
                for s in services:
                    for char in s.characteristics:
                        print('Characteristic: {0}'.format(await client.get_all_for_characteristic(char)))
                        # print(f'[{char.uuid}] {char.description}:, {char.handle}, {char.properties}')
                        # handle_desc_pairs[char.handle] = (char.description + ':')
                # Temp Read
                await client.start_notify('15005991-b131-3396-014c-664c9867b917', adc_notification_handler)
                # Strain Read
                await client.start_notify('6eb675ab-8bd1-1b9a-7444-621e52ec6823', adc_notification_handler)
                # Gyro X
                await client.start_notify('2c86686a-53dc-25b3-0c4a-f0e10c8dee20', gyro_notification_handler)
                # Gyro Y
                await client.start_notify('2c86686a-53dc-25b3-0c4a-f0e10c8dbe21', gyro_notification_handler)
                # Gyro Z
                await client.start_notify('2c86686a-53dc-25b3-0c4a-f0e10c8d2e22', gyro_notification_handler)
                # Accel X
                await client.start_notify('2c86686a-53dc-25b3-0c4a-f0e10c8d7e23', accel_notification_handler)
                # Accel Y
                await client.start_notify('2c86686a-53dc-25b3-0c4a-f0e10c8d4e24', accel_notification_handler)
                # Accel Z
                await client.start_notify('2c86686a-53dc-25b3-0c4a-f0e10c8d9e25', accel_notification_handler)

                await disconnected_event.wait()
                await client.disconnect()

                print("Connected: {0}".format(await client.is_connected()))

        except BleakError:
            print("Didn't connect in time. Retrying.")
            pass


def create_csv_if_not_exist():
    if not path.exists(DATA_FILE_PATH):
        os.makedirs(DATA_FOLDER_PATH, exist_ok=True)
        new_file_headers = pd.DataFrame(columns=['Time:', 'Temp Value:', 'Strain Value:'])
        new_file_headers.to_csv(DATA_FILE_PATH, encoding='utf-8', index=False)


if __name__ == "__main__":
    global handle_desc_pairs

    handle_desc_pairs = {}
    GPIO.output(LED_PIN, 0)
    create_csv_if_not_exist()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(loop))

