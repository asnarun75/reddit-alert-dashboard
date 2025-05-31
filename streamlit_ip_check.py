import streamlit as st
import requests
import mysql.connector
from mysql.connector import Error

# Replace the variables below with your actual database details
mysql_host = '52.26.110.155'  # Your MySQL server IP
mysql_database = 'BHJCApp'
mysql_user = 'gmanadmin'  # Replace with your MySQL username
mysql_password = 'Jdf^hje*34'  # Replace with your MySQL password

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
            message = "Successfully connected to MySQL Database"
            # Optionally print server info
            db_info = connection.get_server_info()
            message += f"\nServer version: {db_info}"
            connection.close()
            return message
    except Error as e:
        return f"Error while connecting to MySQL: {e}"

# Function to get the public IP address
def get_public_ip():
    response = requests.get('https://api64.ipify.org?format=json')
    return response.json().get('ip')

# Streamlit app layout
st.title("Database Connection Tester")
ip_address = get_public_ip()
st.write(f"Your public IP address is: **{ip_address}**")

# Test MySQL connection and display results
connection_result = test_mysql_connection(mysql_host, mysql_database, mysql_user, mysql_password)
st.write(connection_result)
