#!/usr/bin/env python3
"""
Fetch trail running activities from Strava API and generate data.json
This script does NOT store GPX files - only metadata and encrypted streams
"""

import os
import json
import requests
import base64
import math
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Credentials
STRAVA_CLIENT_ID = os.getenv('STRAVA_CLIENT_ID')
STRAVA_CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')
STRAVA_REFRESH_TOKEN = os.getenv('STRAVA_REFRESH_TOKEN')
MAPBOX_ACCESS_TOKEN = os.getenv('MAPBOX_ACCESS_TOKEN')
GPX_ENCRYPTION_KEY = os.getenv('GPX_ENCRYPTION_KEY', 'Run2026')

# Constants
STRAVA_AUTH_URL = 'https://www.strava.com/oauth/token'
STRAVA_API_URL = 'https://www.strava.com/api/v3'
OUTPUT_FILE = 'data.json'
MAPS_DIR = 'assets/maps'
STREAMS_DIR = 'assets/streams'
DB_FILE = 'all_routes.json'
LOCATIONS_FILE = 'locations.json'


def get_access_token():
    """Get a fresh access token using the refresh token"""
    if not all([STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN]):
        print(f"  ❌ Missing credentials: ID={bool(STRAVA_CLIENT_ID)}, Secret={bool(STRAVA_CLIENT_SECRET)}, Refresh={bool(STRAVA_REFRESH_TOKEN)}")
        # Fallback
        token = os.getenv('STRAVA_ACCESS_TOKEN')
        if token:
            print("⚠️ Using static STRAVA_ACCESS_TOKEN (might expire)")
            return token
        raise ValueError("Missing Strava credentials (need Client ID, Secret, and Refresh Token)")

    payload = {
        'client_id': STRAVA_CLIENT_ID,
        'client_secret': STRAVA_CLIENT_SECRET,
        'refresh_token': STRAVA_REFRESH_TOKEN,
        'grant_type': 'refresh_token'
    }

    try:
        response = requests.post(STRAVA_AUTH_URL, data=payload)
        if response.status_code != 200:
            print(f"  ❌ Strava Auth Error: {response.status_code}")
            print(f"  ❌ Response JSON: {response.text}")
        response.raise_for_status()
        return response.json()['access_token']
    except Exception as e:
        print(f"Error refreshing token: {e}")
        raise


def load_stored_routes():
    """Load existing routes from local JSON file"""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []


def save_routes_db(routes):
    """Save routes to local JSON file"""
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(routes, f, indent=4)


def fetch_activities(after_timestamp=None):
    """Fetch activities from Strava API, optionally after a specific time"""
    access_token = get_access_token()
    headers = {'Authorization': f'Bearer {access_token}'}
    
    all_runs = []
    page = 1
    
    print(f"  ⬇️ Fetching activities{' after ' + str(datetime.fromtimestamp(after_timestamp)) if after_timestamp else ' (All)'}...")
    
    while True:
        params = {
            'per_page': 200, 
            'page': page
        }
        if after_timestamp:
            params['after'] = after_timestamp
        
        try:
            response = requests.get(
                f'{STRAVA_API_URL}/athlete/activities',
                headers=headers,
                params=params
            )
            response.raise_for_status()
            
            activities = response.json()
            
            if not activities:
                break 
                
            filtered_activities = [a for a in activities if a.get('sport_type') == 'TrailRun']
            
            print(f"    Page {page}: Found {len(activities)} activities ({len(filtered_activities)} Trail Runs)")
            
            all_runs.extend(filtered_activities)
            page += 1
            
        except Exception as e:
            print(f"  ❌ Error fetching page {page}: {e}")
            break
            
    return all_runs


def obfuscate_polyline(polyline):
    """XOR Cipher + Base64"""
    if not polyline:
        return None
    
    key_bytes = GPX_ENCRYPTION_KEY.encode('utf-8')
    data = polyline.encode('utf-8')
    xored = bytearray(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data))
    return base64.b64encode(xored).decode('ascii')


def save_stream_data(activity_id):
    """Fetch activity streams and save as encrypted .dat file"""
    try:
        filename = f"{activity_id}.dat"
        filepath = os.path.join(STREAMS_DIR, filename)
        os.makedirs(STREAMS_DIR, exist_ok=True)
        
        # Check if exists
        if os.path.exists(filepath):
            return

        print(f"    ⬇️ Fetching streams for {activity_id}...")
        access_token = get_access_token()
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {'keys': 'latlng,altitude', 'key_by_type': 'true'}
        
        response = requests.get(
            f"{STRAVA_API_URL}/activities/{activity_id}/streams",
            headers=headers,
            params=params
        )
        
        if response.status_code == 200:
            streams = response.json()
            # Streams is a dict when key_by_type=true
            latlngs = streams.get('latlng', {}).get('data', [])
            alts = streams.get('altitude', {}).get('data', [])
            
            if latlngs:
                # Combine [lat, lng, ele]
                combined_data = []
                for i in range(len(latlngs)):
                    ele = alts[i] if i < len(alts) else 0
                    combined_data.append([latlngs[i][0], latlngs[i][1], round(ele, 1)])
                
                json_str = json.dumps(combined_data)
                
                # XOR Obfuscation
                key = GPX_ENCRYPTION_KEY
                obfuscated = []
                for i in range(len(json_str)):
                    char_code = ord(json_str[i])
                    key_code = ord(key[i % len(key)])
                    obfuscated.append(chr(char_code ^ key_code))
                
                encrypted_data = base64.b64encode("".join(obfuscated).encode('utf-8')).decode('utf-8')

                with open(filepath, 'w') as f:
                    f.write(encrypted_data)
        elif response.status_code == 404:
             print(f"    ⚠️ Stream not found (404)")
        else:
             print(f"    ⚠️ Failed to fetch streams: {response.status_code}")

    except Exception as e:
        print(f"    ❌ Error fetching streams: {e}")


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS points in meters"""
    R = 6371000  # Radius of Earth in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_custom_location(lat, lng):
    """Check if coordinates are near a custom location defined in locations.json"""
    if not os.path.exists(LOCATIONS_FILE):
        return None
    try:
        with open(LOCATIONS_FILE, 'r', encoding='utf-8') as f:
            custom_locs = json.load(f)
            for loc in custom_locs:
                dist = calculate_distance(lat, lng, loc['lat'], loc['lng'])
                if dist <= 50:  # 50m radius as requested
                    return loc['name']
    except Exception as e:
        print(f"    ⚠️ Error reading custom locations: {e}")
    return None


def get_location_name(lat, lng):
    """Get location name: custom list first, then Mapbox reverse geocoding"""
    # 1. Check Custom Data First
    custom_name = get_custom_location(lat, lng)
    if custom_name:
        return custom_name

    # 2. Fallback to Mapbox
    if not MAPBOX_ACCESS_TOKEN:
        return None
    try:
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lng},{lat}.json"
        params = {
            'access_token': MAPBOX_ACCESS_TOKEN,
            'types': 'place,locality',
            'limit': 1
        }
        res = requests.get(url, params=params)
        if res.status_code == 200:
            data = res.json()
            if data['features']:
                return data['features'][0]['place_name'].split(',')[0]
        return None
    except Exception as e:
        print(f"    ⚠️ Error reverse geocoding: {e}")
        return None


def create_route_data(activities, existing_routes=None):
    """Convert Strava activities to route data format"""
    routes = []
    for activity in activities:
        # Save streams 
        save_stream_data(activity['id'])
        
        # Date Parsing
        start_date = activity.get('start_date_local', '')
        date_display = ''
        try:
            dt = datetime.fromisoformat(start_date.replace('Z', ''))
            date_display = dt.strftime('%b %Y')
        except:
            date_display = start_date[:10] 

        is_race = activity.get('workout_type') == 1
        
        # Location logic
        location = None
        # Try to find in existing routes first
        if existing_routes:
            match = next((r for r in existing_routes if r['stravaId'] == str(activity['id'])), None)
            if match and match.get('location'):
                location = match['location']
        
        # If not found, fetch from Mapbox
        if not location:
            start_latlng = activity.get('start_latlng')
            if start_latlng and len(start_latlng) == 2:
                print(f"    📍 Geocoding start location for {activity['id']}...")
                location = get_location_name(start_latlng[0], start_latlng[1])

        route = {
            'name': activity.get('name', 'Unnamed Run'),
            'stravaId': str(activity['id']),
            'distance': activity.get('distance', 0),
            'elevation': activity.get('total_elevation_gain', 0),
            'location': location,
            'dateDisplay': date_display,
            'dateFull': start_date,
            'isRace': is_race,
            'mapImage': f"assets/maps/{activity['id']}.png",
            'ePolyline': obfuscate_polyline(
                activity.get('map', {}).get('summary_polyline')
            )
        }
        routes.append(route)
    
    return routes


def get_athlete_info():
    """Fetch authenticated athlete profile"""
    print("  👤 Fetching athlete profile...")
    access_token = get_access_token()
    headers = {'Authorization': f'Bearer {access_token}'}
    
    response = requests.get(f"{STRAVA_API_URL}/athlete", headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"  ⚠️ Failed to fetch athlete: {response.status_code}")
        return None


def write_athlete_json(athlete):
    """Write athlete data to athlete.json"""
    output_file = 'athlete.json'
    athlete_data = {}
    if athlete:
        athlete_data = {
            "id": athlete.get('id'),
            "name": f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip(),
            "username": athlete.get('username'),
            "profile": athlete.get('profile') 
        }
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(athlete_data, f, indent=4)
    print(f"✓ Successfully wrote athlete data to {output_file}")


def write_data_json(routes):
    """Write routes data to data.json"""
    timestamp = datetime.utcnow().isoformat() + 'Z'
    data = {
        "routes": routes,
        "lastUpdated": timestamp,
        "encryptionKey": GPX_ENCRYPTION_KEY
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print(f"✓ Successfully wrote {len(routes)} routes to {OUTPUT_FILE}")


def main():
    """Main execution function"""
    print("Fetching activities from Strava...")
    
    try:
        os.makedirs(MAPS_DIR, exist_ok=True)
        os.makedirs(STREAMS_DIR, exist_ok=True)
        
        # 1. Fetch Athlete Info
        athlete = get_athlete_info()
        write_athlete_json(athlete)
        
        # 2. Load Existing Routes
        existing_routes = load_stored_routes()
        print(f"  📂 Loaded {len(existing_routes)} existing routes.")
        
        # 3. Determine Latest Date
        latest_timestamp = None
        if existing_routes:
            timestamps = []
            for r in existing_routes:
                if 'dateFull' in r:
                    try:
                        dt_str = r['dateFull'].replace('Z', '+00:00')
                        dt = datetime.fromisoformat(dt_str)
                        timestamps.append(dt.timestamp())
                    except:
                        pass
            if timestamps:
                latest_timestamp = int(max(timestamps))
        
        # 4. Fetch NEW activities from Strava
        activities = fetch_activities(after_timestamp=latest_timestamp)
        print(f"  ✓ Found {len(activities)} new running activities")
        
        # 5. Convert & Merge
        if activities:
            new_routes = create_route_data(activities, existing_routes)
            
            # Deduplicate by ID
            routes_map = {r['stravaId']: r for r in existing_routes}
            for r in new_routes:
                routes_map[r['stravaId']] = r
                
            final_routes = list(routes_map.values())
            # Sort newest first
            final_routes.sort(key=lambda x: x.get('dateFull', ''), reverse=True)
            
            save_routes_db(final_routes)
            routes_to_write = final_routes
        else:
            print("  ✓ No new activities found.")
            routes_to_write = existing_routes

        # 6. Write to data.json
        write_data_json(routes_to_write)
        
        print("✓ Data fetch complete!")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        raise


if __name__ == '__main__':
    main()
