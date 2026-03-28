from dotenv import load_dotenv
import os
load_dotenv('.env')
ORS_API_KEY = os.environ.get('ORS_API_KEY')

import openrouteservice
client = openrouteservice.Client(key=ORS_API_KEY)

tests = [
    ("Makati to Manila", [[121.0337, 14.5547], [120.9842, 14.5995]]),
    ("Manila to Quezon City", [[120.9842, 14.5995], [121.0353, 14.6349]]),
    ("Manila to Pasig", [[120.9842, 14.5995], [121.1641, 14.5769]]),
]

for name, coords in tests:
    try:
        result = client.directions(coordinates=coords, format='geojson')
        print(f"✓ {name}: SUCCESS")
    except Exception as e:
        print(f"✗ {name}: FAILED - {e}")
