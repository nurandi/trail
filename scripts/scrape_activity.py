import requests
import re
import json
import sys

def scrape_strava_activity(activity_id):
    url = f"https://www.strava.com/activities/{activity_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    print(f"📡 Fetching activity {activity_id}...")
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to fetch activity. Status code: {response.status_code}")
        return None

    html = response.text
    
    # Try to find the JSON data in the script tags
    # Strava public pages use a Next.js JSON blob (__NEXT_DATA__)
    next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if not next_data_match:
        print("❌ Could not find __NEXT_DATA__ script tag.")
        return None

    try:
        full_json = json.loads(next_data_match.group(1))
        
        # Deep search for key activity data
        def find_key_recursive(obj, key_to_find):
            if isinstance(obj, dict):
                if key_to_find in obj:
                    return obj[key_to_find]
                for k, v in obj.items():
                    res = find_key_recursive(v, key_to_find)
                    if res is not None:
                        return res
            elif isinstance(obj, list):
                for item in obj:
                    res = find_key_recursive(item, key_to_find)
                    if res is not None:
                        return res
            return None

        # Look for a common structure: Apollo state or specific props
        # Sometimes Strava hides it deep in "initialState" or "apollo"
        
        # Try to find the actual activity object by its ID
        def find_activity_by_id(obj, target_id):
            if isinstance(obj, dict):
                # Check for ID
                if str(obj.get('id')) == str(target_id):
                    # Prefer the one with 'stats' or 'streams'
                    if 'stats' in obj or 'streams' in obj:
                        return obj
                for v in obj.values():
                    res = find_activity_by_id(v, target_id)
                    if res: return res
            elif isinstance(obj, list):
                for item in obj:
                    res = find_activity_by_id(item, target_id)
                    if res: return res
            return None

        activity = find_activity_by_id(full_json, activity_id)
        
        if not activity:
            print(f"❌ Could not find data for ID {activity_id} in JSON.")
            return None

        # Extract name
        name = activity.get('name')
        
        # Extract stats from 'stats' sub-object
        stats = activity.get('stats', []) # Sometimes it's a list of dicts
        dist = 0
        elev = 0
        if isinstance(stats, list):
            for s in stats:
                if s.get('key') == 'distance': dist = s.get('value')
                if s.get('key') == 'elevation_gain': elev = s.get('value')
        elif isinstance(stats, dict):
            dist = stats.get('distance') or stats.get('distanceValue')
            elev = stats.get('elevation_gain') or stats.get('totalElevationGain')

        # Extract streams
        streams = activity.get('streams', {})
        latlng = []
        polyline = ""
        
        if isinstance(streams, dict):
            raw_latlng = streams.get('location', []) 
            if raw_latlng:
                # Convert list of dicts to list of lists
                if isinstance(raw_latlng[0], dict):
                    latlng = [[p.get('lat'), p.get('lng')] for p in raw_latlng]
                else:
                    latlng = raw_latlng
            
        # 1. Calculate Distance from stream if not in stats
        if dist == 0 and isinstance(streams, dict) and 'distance' in streams:
            dist_stream = streams.get('distance', [])
            if dist_stream:
                dist = dist_stream[-1] # Total distance is the last point

        # 2. Calculate Elevation from stream if not in stats
        alt_stream = []
        if isinstance(streams, dict) and ('elevation' in streams or 'altitude' in streams):
            alt_stream = streams.get('elevation') or streams.get('altitude')
            if alt_stream and elev == 0:
                # Calculate cumulative gain
                gain = 0
                for i in range(1, len(alt_stream)):
                    diff = alt_stream[i] - alt_stream[i-1]
                    if diff > 0:
                        gain += diff
                elev = gain

        # 3. Generate Polyline from latlng stream
        def encode_polyline(points):
            def encode_value(value):
                value = value << 1
                if value < 0:
                    value = ~value
                res = ""
                while value >= 0x20:
                    res += chr((0x20 | (value & 0x1f)) + 63)
                    value >>= 5
                res += chr(value + 63)
                return res

            res = ""
            old_lat = 0
            old_lng = 0
            for p in points:
                lat = int(round(p[0] * 1e5))
                lng = int(round(p[1] * 1e5))
                res += encode_value(lat - old_lat)
                res += encode_value(lng - old_lng)
                old_lat = lat
                old_lng = lng
            return res

        if not polyline and latlng:
            # Simplify latlng for Mapbox URI limit (take every Nth point)
            # A typical long route might have thousands of points, but Mapbox only needs a few hundred.
            step = max(1, len(latlng) // 250) 
            simplified_latlng = latlng[::step]
            polyline = encode_polyline(simplified_latlng)

        # Extract Athlete Info
        athlete = activity.get('athlete')
        if not athlete:
            athlete = find_key_recursive(full_json, 'athlete')
        
        athlete_id = None
        athlete_name = "Unknown"
        if isinstance(athlete, dict):
            athlete_id = str(athlete.get('id', ''))
            first = athlete.get('firstName', '')
            last = athlete.get('lastName', '')
            athlete_name = f"{first} {last}".strip() or "Unknown"

        activity_data = {
            'name': name,
            'distance': dist,
            'elevation': elev,
            'ePolyline': polyline,
            'altitudeStream': alt_stream,
            'athleteId': athlete_id,
            'athleteName': athlete_name,
            'dateDisplay': activity.get('startDateLocal') or activity.get('startLocal'),
            'startLatLng': latlng[0] if latlng else [activity.get('startLat'), activity.get('startLng')]
        }
        
        # Sometimes lat/lng are separate fields not in a list
        if not any(activity_data['startLatLng']):
             lat = activity.get('start_latitude') or activity.get('latitude')
             lng = activity.get('start_longitude') or activity.get('longitude')
             if lat and lng:
                 activity_data['startLatLng'] = [lat, lng]

        # Construct result
        result = {
            "name": activity_data.get('name', 'Unknown Activity'),
            "stravaId": str(activity_id),
            "athleteId": activity_data.get('athleteId'),
            "athleteName": activity_data.get('athleteName'),
            "distance": activity_data.get('distance', 0),
            "elevation": activity_data.get('elevation', 0),
            "dateDisplay": activity_data.get('dateDisplay', ''),
            "ePolyline": activity_data.get('ePolyline', ''),
            "altitudeStream": activity_data.get('altitudeStream', []),
            "latlng": latlng,
            "startLatLng": activity_data.get('startLatLng', []),
            "type": "training",
            "location": "Unknown",
            "tags": []
        }
        
        return result

    except Exception as e:
        print(f"❌ Error parsing JSON: {e}")
        return None
    
    return result

def print_summary(data):
    if not data: return
    
    print("\n" + "="*50)
    print(f"🏃 ACTIVITY : {data['name']}")
    print(f"👤 ATHLETE  : {data.get('athleteName')} (ID: {data.get('athleteId')})")
    print("="*50)
    
    dist_km = data['distance'] / 1000
    elev_m = data['elevation']
    
    # Format date (expecting YYYY-MM-DD or similar)
    date_str = data['dateDisplay']
    if 'T' in date_str:
        date_str = date_str.split('T')[0]

    print(f"📅 Date      : {date_str}")
    print(f"📏 Distance  : {dist_km:.2f} km")
    print(f"⛰️  Elevation : {elev_m:.1f} m")
    
    alt_pts = len(data.get('altitudeStream', []))
    if alt_pts:
        print(f"📈 Alt Stream: {alt_pts} data points")
        
    print(f"🆔 Strava ID : {data['stravaId']}")
    
    if data['startLatLng']:
        print(f"📍 Start     : {data['startLatLng'][0]:.6f}, {data['startLatLng'][1]:.6f}")
    
    poly = data.get('ePolyline', '')
    if poly:
        poly_display = poly[:60] + "..." if len(poly) > 60 else poly
        print(f"🗺️  Polyline  : {poly_display}")
    
    print("="*50)

if __name__ == "__main__":
    activity_id = "16834108224"
    if len(sys.argv) > 1:
        activity_id = sys.argv[1]
        
    data = scrape_strava_activity(activity_id)
    if data:
        print_summary(data)
        
        # Save to a temporary file as requested
        filename = f"scraped_{activity_id}.json"
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        print(f"💾 Data saved to {filename}\n")
    else:
        print("❌ Could not extract data.")
