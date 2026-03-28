import requests
import json

# No auth token - like original problem before we fixed it
print("Test 1: Without authentication token")
try:
    resp = requests.get(
        'http://localhost:8000/api/services/ors/route/',
        params={'start': '120.9842,14.5995', 'end': '121.0337,14.5547'},
        timeout=10
    )
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:200]}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*60 + "\n")

# Get a token first by logging in
print("Test 2: With authentication token")
try:
    # First login to get token
    login_resp = requests.post(
        'http://localhost:8000/api/users/login/',
        json={'username': 'admin', 'password': 'admin123'},
        timeout=10
    )
    print(f"Login status: {login_resp.status_code}")
    if login_resp.status_code == 200:
        token = login_resp.json().get('token')
        print(f"Got token: {token[:20]}...")
        
        # Now make the ORS request with token
        resp = requests.get(
            'http://localhost:8000/api/services/ors/route/',
            params={'start': '120.9842,14.5995', 'end': '121.0337,14.5547'},
            headers={'Authorization': f'Token {token}'},
            timeout=10
        )
        print(f"ORS Status: {resp.status_code}")
        if resp.status_code == 200:
            print("✓ SUCCESS - Got routing data")
            data = resp.json()
            distance = data['features'][0]['properties']['segments'][0]['distance']
            duration = data['features'][0]['properties']['segments'][0]['duration']
            print(f"  Distance: {distance/1000:.2f} km, Duration: {duration:.0f} seconds")
        else:
            print(f"Error response: {resp.text[:500]}")
    else:
        print(f"Login failed: {login_resp.text}")
except Exception as e:
    print(f"Error: {e}")
