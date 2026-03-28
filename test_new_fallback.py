from dotenv import load_dotenv
import os
load_dotenv('.env')
ORS_API_KEY = os.environ.get('ORS_API_KEY')

import openrouteservice
client = openrouteservice.Client(key=ORS_API_KEY)

# Test the new default fallback (Manila) to job location (Makati)
try:
    result = client.directions(
        coordinates=[[120.9842, 14.5995], [121.0337, 14.5547]], 
        format='geojson'
    )
    print("✓ Manila (fallback) to Makati (job location): SUCCESS")
    print(f"  Distance: {result['features'][0]['properties']['segments'][0]['distance']/1000:.2f} km")
    print(f"  Duration: {result['features'][0]['properties']['segments'][0]['duration']:.0f} seconds")
except Exception as e:
    print(f"✗ Manila (fallback) to Makati (job location): FAILED - {e}")
