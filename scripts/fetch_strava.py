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
WHITELIST_FILE = 'filters/whitelist.txt'
BLACKLIST_FILE = 'filters/blacklist.txt'
ROUTES_WHITELIST_FILE = 'filters/routes_whitelist.txt'


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


def load_filter_list(filepath):
    """Load IDs from a text file, ignoring comments and empty lines"""
    if not os.path.exists(filepath):
        return set()
    ids = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                # Remove comments and whitespace
                clean_line = line.split('#')[0].strip()
                if clean_line:
                    ids.add(clean_line)
    except Exception as e:
        print(f"  ⚠️ Error loading filter list {filepath}: {e}")
    return ids


def should_include_activity(activity_id, activity_date_str, whitelist, blacklist):
    """
    Logic:
    1. If blacklisted -> False
    2. If whitelisted -> True
    3. If year is 2025 or newer -> True
    4. Otherwise -> False
    """
    str_id = str(activity_id)
    if str_id in blacklist:
        return False
    if str_id in whitelist:
        return True
    
    try:
        # Extract year from date string (usually 2025-01-01T...)
        year = int(activity_date_str[:4])
        if year >= 2025:
            return True
    except:
        pass
        
    return False


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
                
            filtered_activities = []
            for a in activities:
                # Check both sport_type and legacy type
                is_trail_run = (a.get('sport_type') == 'TrailRun' or a.get('type') == 'TrailRun')
                if is_trail_run:
                    filtered_activities.append(a)
                    print(f"      ✅ Found Act: {a.get('name')} ({a.get('start_date_local')[:10]})")
            
            print(f"    Page {page}: Found {len(activities)} activities ({len(filtered_activities)} Trail Runs)")
            
            all_runs.extend(filtered_activities)
            page += 1
            
        except Exception as e:
            print(f"  ❌ Error fetching page {page}: {e}")
            break
            
    return all_runs


def fetch_route_details(route_id):
    """Fetch details for a specific Strava route"""
    access_token = get_access_token()
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        response = requests.get(f"{STRAVA_API_URL}/routes/{route_id}", headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"    ⚠️ Failed to fetch route {route_id}: {response.status_code}")
            return None
    except Exception as e:
        print(f"    ❌ Error fetching route {route_id}: {e}")
        return None


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
                if dist <= 300:  # Increased to 300m for better match rate
                    return {
                        'name': loc['name'],
                        'tags': loc.get('tag', [])
                    }
    except Exception as e:
        print(f"    ⚠️ Error reading custom locations: {e}")
    return None


def get_location_name(lat, lng):
    """Get location info: custom list first, then Mapbox reverse geocoding"""
    # 1. Check Custom Data First
    custom_data = get_custom_location(lat, lng)
    if custom_data:
        return custom_data['name'], custom_data['tags']

    # 2. Fallback to Mapbox
    if not MAPBOX_ACCESS_TOKEN:
        return None, []
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
                name = data['features'][0]['place_name'].split(',')[0]
                return name, []
        return None, []
    except Exception as e:
        print(f"    ⚠️ Error reverse geocoding: {e}")
        return None


def create_route_data(items, existing_routes=None, is_activity=True):
    """Convert Strava activities or routes to unified data format"""
    routes = []
    for item in items:
        item_id = str(item['id'])
        
        # Save streams for activities (routes don't have streams in same way)
        if is_activity:
            save_stream_data(item_id)
        
        # Date Parsing
        if is_activity:
            raw_date = item.get('start_date_local', '')
        else:
            # For routes, use updated_at or created_at
            raw_date = item.get('updated_at') or item.get('created_at') or ''
            
        date_display = ''
        try:
            dt = datetime.fromisoformat(raw_date.replace('Z', ''))
            date_display = dt.strftime('%b %Y')
        except:
            date_display = raw_date[:10] 

        # Type logic: race, train, route
        if not is_activity:
            rtype = 'route'
            is_race = False
        else:
            is_race = item.get('workout_type') == 1
            rtype = 'race' if is_race else 'train'
        
        # Location logic
        location_name = None
        tags = []
        
        if is_activity:
            start_latlng = item.get('start_latlng')
        else:
            # Routes have segments or just map? Actually they usually have start_latlng
            start_latlng = item.get('start_latlng')
        
        # 1. ALWAYS check custom location first
        if start_latlng and len(start_latlng) == 2:
            custom_data = get_custom_location(start_latlng[0], start_latlng[1])
            if custom_data:
                location_name = custom_data['name']
                tags = custom_data['tags']
        
        # 2. Fallback to existing routes
        if not location_name and existing_routes:
            match = next((r for r in existing_routes if r['stravaId'] == item_id), None)
            if match and match.get('location'):
                location_name = match['location']
                tags = match.get('tags', [])
        
        # 3. Last resort: Fetch from Mapbox
        if not location_name and start_latlng and len(start_latlng) == 2:
            print(f"    📍 Geocoding start location for {item_id}...")
            location_name, tags = get_location_name(start_latlng[0], start_latlng[1])

        route_entry = {
            'name': item.get('name', 'Unnamed'),
            'stravaId': item_id,
            'distance': item.get('distance', 0),
            'elevation': item.get('total_elevation_gain', 0) if is_activity else item.get('elevation_gain', 0),
            'location': location_name,
            'tags': tags,
            'startLatLng': start_latlng,
            'dateDisplay': date_display,
            'dateFull': raw_date,
            'type': rtype,
            'isRace': is_race,
            'mapImage': f"assets/maps/{item_id}.png",
            'ePolyline': obfuscate_polyline(
                item.get('map', {}).get('summary_polyline') or item.get('map', {}).get('polyline')
            )
        }
        routes.append(route_entry)
    
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


def should_include_item(item_id, date_str, whitelist, routes_whitelist, blacklist):
    """
    Logic:
    1. If blacklisted -> False
    2. If whitelisted (Activity or Route) -> True
    3. If year is 2025 or newer -> True
    4. Otherwise -> False
    """
    str_id = str(item_id)
    if str_id in blacklist:
        return False
    if str_id in whitelist or str_id in routes_whitelist:
        return True
    
    try:
        # Extract year from date string
        year = int(date_str[:4])
        if year >= 2025:
            return True
    except:
        pass
        
    return False


def main():
    """Main execution function"""
    print("Fetching activities and routes from Strava...")
    
    try:
        os.makedirs(MAPS_DIR, exist_ok=True)
        os.makedirs(STREAMS_DIR, exist_ok=True)
        
        # 1. Fetch Athlete Info
        athlete = get_athlete_info()
        write_athlete_json(athlete)
        
        # 2. Load Existing Routes & Filters
        existing_routes = load_stored_routes()
        print(f"  📂 Loaded {len(existing_routes)} existing routes.")
        
        whitelist = load_filter_list(WHITELIST_FILE)
        blacklist = load_filter_list(BLACKLIST_FILE)
        routes_whitelist = load_filter_list(ROUTES_WHITELIST_FILE)
        
        # 3. Determine Latest Activity Date
        latest_timestamp = None
        if existing_routes:
            timestamps = []
            for r in existing_routes:
                # Only use activities for calculating the sync window
                if r.get('type') != 'route' and 'dateFull' in r:
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
        
        # 5. Fetch WHITELISTED routes from Strava
        raw_routes = []
        if routes_whitelist:
            print(f"  ⬇️ Fetching {len(routes_whitelist)} whitelisted routes...")
            for rid in routes_whitelist:
                r_detail = fetch_route_details(rid)
                if r_detail:
                    raw_routes.append(r_detail)
                    print(f"      ✅ Found Route: {r_detail.get('name')}")

        # 6. Convert & Merge
        # Start with all existing
        routes_map = {r['stravaId']: r for r in existing_routes}
        
        # Add new activities
        if activities:
            new_activity_data = create_route_data(activities, existing_routes, is_activity=True)
            for r in new_activity_data:
                routes_map[r['stravaId']] = r
                
        # Add whitelisted routes (always overwrite to get latest info)
        if raw_routes:
            new_route_data = create_route_data(raw_routes, existing_routes, is_activity=False)
            for r in new_route_data:
                routes_map[r['stravaId']] = r
        
        # 7. Apply Filter (2025 + Whitelists - Blacklist)
        all_merged_routes = list(routes_map.values())
        final_filtered_routes = [
            r for r in all_merged_routes 
            if should_include_item(r['stravaId'], r.get('dateFull', ''), whitelist, routes_whitelist, blacklist)
        ]
        
        # Sort newest first
        final_filtered_routes.sort(key=lambda x: x.get('dateFull', ''), reverse=True)
        
        # Log difference
        dropped = len(all_merged_routes) - len(final_filtered_routes)
        if dropped > 0:
            print(f"  🧹 Filtered out {dropped} items not matching 2025 or whitelist criteria.")
        
        # 8. Write to storage
        save_routes_db(final_filtered_routes)
        write_data_json(final_filtered_routes)
        
        print(f"✓ Data fetch complete! Total items: {len(final_filtered_routes)}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        raise


if __name__ == '__main__':
    main()
