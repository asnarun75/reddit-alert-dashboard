import streamlit as st
import requests

import mysql.connector
from mysql.connector import Error
# Replace the variables below with your actual database details
mysql_host = '52.26.110.155'  # e.g., '52.26.110.155'
mysql_database = 'BHJCApp'
mysql_user = 'gmanadmin'
mysql_password = 'Jdf^hje*34'

# Function to get the public IP address
def get_public_ip():
    response = requests.get('https://api64.ipify.org?format=json')
    return response.json().get('ip')

# Streamlit app layout
st.title("Get My Public IP")
ip_address = get_public_ip()
st.write(f"Your public IP address is: **{ip_address}**")


def test_mysql_connection(host, database, user, password):
    try:
        # Establish the connection
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )

        if connection.is_connected():
            print("Successfully connected to MySQL Database")
            # Optionally print server info
            db_info = connection.get_server_info()
            print("Server version:", db_info)
            connection.close()
    except Error as e:
        print("Error while connecting to MySQL", e)



test_mysql_connection(mysql_host, mysql_database, mysql_user, mysql_password)
