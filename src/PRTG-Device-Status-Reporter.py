import collections
import csv
import io
import os
import re
import urllib.parse

import configparser
import pandas as pd
import requests


# Module information.
__author__ = 'Anthony Farina'
__copyright__ = 'Copyright 2021, PRTG Device Status Reporter'
__credits__ = ['Anthony Farina']
__license__ = 'MIT'
__version__ = '1.0.1'
__maintainer__ = 'Anthony Farina'
__email__ = 'farinaanthony96@gmail.com'
__status__ = 'Released'


# Global variables from the config file for easy referencing.
CONFIG = configparser.ConfigParser()
CONFIG_PATH = '/../configs/PRTG-Device-Status-Reporter-config.ini'
CONFIG.read(os.path.dirname(os.path.realpath(__file__)) + CONFIG_PATH)
SERVER_URL = CONFIG['PRTG Info']['server-url']
USERNAME = urllib.parse.quote_plus(CONFIG['PRTG Info']['username'])
PASSWORD = urllib.parse.quote_plus(CONFIG['PRTG Info']['password'])
PASSHASH = urllib.parse.quote_plus(CONFIG['PRTG Info']['passhash'])
EXCEL_FILE_NAME = CONFIG['Output Info']['excel-file-name']
COL_LABELS = CONFIG['Output Info']['column-names'].replace('\n', '').split(',')


# This method uses the PRTG API to access all devices on the provided PRTG
# instance in order to get their group name, the device name, the device
# IPv4 address, and the ping sensor status for the device. It will output
# this information to an Excel file.
def prtg_device_reporter() -> None:
    # Prepare the URLs to get all devices and ping sensors from PRTG in CSV
    # format. Add filtering into the URLs to get more specific devices /
    # sensors.
    devices_url = SERVER_URL + \
                  '/api/table.xml?content=devices&columns=objid,host' \
                  '&output=csvtable&count=50000&username=' + USERNAME
    devices_url = add_auth(devices_url)
    ping_url = SERVER_URL + '/api/table.xml?content=sensors&filter_type=ping' \
                            '&columns=group,device,status,parentid' \
                            '&output=csvtable&count=50000&username=' + USERNAME
    ping_url = add_auth(ping_url)

    # Get the device information from PRTG and make a dictionary of them where
    # the key is the device's ID and the value is the device's IPv4 address.
    devices_resp = requests.get(url=devices_url)
    devices_csv_strio = io.StringIO(devices_resp.text)
    devices_csv_reader = csv.reader(devices_csv_strio, delimiter=',')
    devices_ip_dict = collections.defaultdict(str)

    # Make the device dictionary.
    # device[0] is the device's object ID
    # device[2] is the device's IPv4 address
    for device in devices_csv_reader:
        devices_ip_dict[device[0]] = device[2]

    # Get the ping sensor information for all devices from PRTG, clean up
    # the response, and read the CSV like a dictionary.
    ping_sens_resp = requests.get(url=ping_url)
    ping_sens_strio = io.StringIO(ping_sens_resp.text)
    ping_sens_df = pd.read_csv(ping_sens_strio)
    ping_sens_df = remove_raw(ping_sens_df)
    ping_sens_csv = ping_sens_df.to_csv(sep=',', index=False, encoding='utf-8')
    ping_sens_strio = io.StringIO(ping_sens_csv)
    ping_sens_dict = csv.DictReader(ping_sens_strio)

    # Prepare the output for the Excel file.
    output_list = list()

    # Go through each row in the ping sensor CSV and access values like a
    # dictionary to build the output list for the Excel file.
    for ping_sens in ping_sens_dict:
        device_info = list()

        # Add the device's information to the device info list.
        device_info.append(ping_sens['Group'])
        device_info.append(ping_sens['Device'])
        device_info.append(devices_ip_dict[ping_sens['Parent ID']])
        device_info.append(ping_sens['Status'])

        # Add the device info list to the output list.
        output_list.append(device_info)

    # Make output list into an Excel file.
    output_df = pd.DataFrame(output_list, columns=COL_LABELS)
    output_df.to_excel('./../' + EXCEL_FILE_NAME + '.xlsx', index=None, header=True)


# Every time table information is called from the PRTG API, the response has
# 'readable' columns and 'raw' columns. Their are subtle differences,
# but the raw columns are not needed. This function removes all the 'raw'
# columns from a dataframe object of the PRTG API response and returns a
# dataframe object with only the non-raw columns.
def remove_raw(raw_df: pd.DataFrame) -> pd.DataFrame:
    # Prepare a list of desired column names.
    col_labels = list()

    # Iterate through the column labels to remove column labels ending with
    # '(RAW)'.
    for col in raw_df.columns:
        # Add only desired column labels to the list.
        if not bool(re.search('\\(RAW\\)$', col)):
            col_labels.append(col)

    # Return the dataframe object that only has desired columns.
    return_df = raw_df[col_labels]
    return return_df


# This function will append the PRTG authentication to the end of the given
# PRTG API call URL. It will append either the password or passhash,
# whichever was provided in the config file. Passhash has priority if both
# fields are filled in.
def add_auth(url: str) -> str:
    # Check if the password or passhash will be used to authenticate the
    # access to the PRTG instance.
    if PASSHASH == '':
        url = url + '&password=' + PASSWORD
    else:
        url = url + '&passhash=' + PASSHASH

    return url


# The main method that runs the script. There are no input arguments.
if __name__ == '__main__':
    # Run the script.
    prtg_device_reporter()
