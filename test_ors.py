from dotenv import load_dotenv
import os
load_dotenv('.env')
ORS_API_KEY = os.environ.get('ORS_API_KEY')

import openrouteservice
print(f"Creating ORS client with key: {ORS_API_KEY[:30]}...")

try:
    client = openrouteservice.Client(key=ORS_API_KEY)
    print("Client created successfully")
    
    # Try a simple request
    params = {
        'coordinates': [[122.7322, 6.9271], [121.0337, 14.5547]],
        'format': 'geojson',
        'instructions': True,
    }
    print("Attempting request with params:", params)
    result = client.directions(**params)
    print("Success!")
    print("Result:", result)
    
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
