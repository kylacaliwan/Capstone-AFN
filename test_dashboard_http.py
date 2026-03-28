#!/usr/bin/env python
import requests
import json
import time

# Give server time to start
time.sleep(2)

BASE_URL = "http://127.0.0.1:8000"

# Step 1: Login
login_response = requests.post(f"{BASE_URL}/users/login/", json={
    "username": "admin",
    "password": "admin123"
})

if login_response.status_code == 200:
    token = login_response.json().get('token')
    print(f"[OK] Login successful, token: {token[:20]}...")
    
    # Step 2: Access dashboard
    headers = {"Authorization": f"Token {token}"}
    dashboard_response = requests.get(f"{BASE_URL}/services/dashboard/", headers=headers)
    
    print(f"[OK] Dashboard response status: {dashboard_response.status_code}")
    if dashboard_response.status_code == 200:
        data = dashboard_response.json()
        print(f"[OK] Dashboard loaded successfully!")
        print(f"  - Role: {data.get('role')}")
        print(f"  - Overview keys: {list(data.get('overview', {}).keys())}")
        print(f"  - Has client_schedule: {'client_schedule' in data}")
        print(f"  - Has recent_activity: {'recent_activity' in data}")
        print(f"  - Has pending_requests: {'pending_requests' in data}")
    else:
        print(f"[ERROR] Dashboard error: {dashboard_response.status_code}")
        print(dashboard_response.text[:500])
else:
    print(f"[ERROR] Login failed: {login_response.status_code}")
    print(login_response.text)
