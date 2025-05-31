import streamlit as st
import requests

# Function to get the public IP address
def get_public_ip():
    response = requests.get('https://api64.ipify.org?format=json')
    return response.json().get('ip')

# Streamlit app layout
st.title("Get My Public IP")
ip_address = get_public_ip()
st.write(f"Your public IP address is: **{ip_address}**")
