#!/usr/bin/env python3
"""
Generate static map images with elevation profiles
Reads from data.json and assets/streams/
"""

import os
import json
import requests
import matplotlib
matplotlib.use('Agg') # Headless mode for CI/CD
import matplotlib.pyplot as plt
import io
import base64
from PIL import Image, ImageDraw
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MAPBOX_ACCESS_TOKEN = os.getenv('MAPBOX_ACCESS_TOKEN')
GPX_ENCRYPTION_KEY = os.getenv('GPX_ENCRYPTION_KEY', 'Run2026')
MAPS_DIR = 'assets/maps'
STREAMS_DIR = 'assets/streams'


def deobfuscate_data(encrypted_str):
    """Decrypt the stream data"""
    if not encrypted_str:
        return None
    try:
        # Base64 decode to bytes -> decode utf-8 to string
        obfuscated_str = base64.b64decode(encrypted_str).decode('utf-8')
        
        # XOR string chars
        key = GPX_ENCRYPTION_KEY
        decrypted_chars = []
        for i, c in enumerate(obfuscated_str):
            key_char = key[i % len(key)]
            decrypted_chars.append(chr(ord(c) ^ ord(key_char)))
            
        return "".join(decrypted_chars)
    except Exception as e:
        print(f"Decryption error: {e}")
        return None


def generate_map(activity):
    activity_id = activity['id']
    polyline = activity['polyline']
    
    map_filepath = os.path.join(MAPS_DIR, f"{activity_id}.jpg")
    
    if os.path.exists(map_filepath):
        # print(f"  ⏭️ Map already exists for {activity_id}, skipping.")
        return

    print(f"  🎨 Generating map for {activity_id}...")

    # 1. Get Elevation Data (from encrypted stream file)
    alts = []
    stream_filepath = os.path.join(STREAMS_DIR, f"{activity_id}.dat")
    
    if os.path.exists(stream_filepath):
        with open(stream_filepath, 'r') as f:
            encrypted_content = f.read()
            json_str = deobfuscate_data(encrypted_content)
            if json_str:
                data = json.loads(json_str)
                # Format is [lat, lng, ele]
                alts = [point[2] for point in data]
    
    # Fallback if no elevation data
    if not alts:
        alts = [0, 5, 2, 8] # Dummy

    try:
        # 2. Download Mapbox Image
        if not MAPBOX_ACCESS_TOKEN or not polyline:
            print("    ⚠️ Missing token or polyline")
            return
            
        from urllib.parse import quote
        encoded_polyline = quote(polyline)
        
        # Strategy: Request even taller image (500px) with huge padding (120px).
        # Crop top 100px.
        # This makes the route smaller and pushes it way up.
        
        url = (
            f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/"
            f"path-3+fc4c02-1({encoded_polyline})/"
            f"auto/600x500?padding=120&access_token={MAPBOX_ACCESS_TOKEN}"
        )
        
        map_response = requests.get(url)
        if map_response.status_code != 200:
            print(f"    ❌ Mapbox Error: {map_response.status_code}")
            return

        # 3. Draw Elevation Profile (Overlay Style)
        # Transparent background, white line + fill
        
        # 3. Draw Elevation Profile (Overlay Style)
        # Transparent background, white line + fill
        
        plt.figure(figsize=(6, 0.8), dpi=100) # 600x80 px (Slightly shorter)
        plt.gcf().patch.set_alpha(0)
        plt.gca().patch.set_alpha(0)
        
        # Plot area - Line Only (No Fill)
        # plt.fill_between(range(len(alts)), alts, color='white', alpha=0.3)
        plt.plot(alts, color='white', linewidth=1.5, alpha=1.0) 
        plt.axis('off')
        plt.margins(0)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', transparent=True, bbox_inches='tight', pad_inches=0)
        buf.seek(0)
        plt.close()
        
        # 4. Composite
        map_img = Image.open(io.BytesIO(map_response.content)).convert("RGBA")
        profile_img = Image.open(buf).convert("RGBA")
        
        # Crop Map: Take (0, 100, 600, 500) -> Result 600x400
        # This shifts everything "up" significantly
        map_img = map_img.crop((0, 100, 600, 500))
        
        # Resize profile to 600 width, max 80 height
        profile_w = map_img.width
        profile_h = 80
        profile_img = profile_img.resize((profile_w, profile_h), Image.Resampling.LANCZOS)
        
        # Overlay Profile
        # Shift it UP by 30px to leave room for Mapbox Logo at bottom
        margin_bottom = 30 
        position_y = map_img.height - profile_h - margin_bottom
        
        map_img.paste(profile_img, (0, position_y), profile_img)
        
        # Convert to RGB before saving as JPEG
        map_img = map_img.convert("RGB")
        map_img.save(map_filepath, "JPEG", quality=85, optimize=True)
        
    except Exception as e:
        print(f"    ❌ Error: {e}")


def deobfuscate_polyline(encrypted_str):
    """Decrypt polyline string"""
    if not encrypted_str:
        return None
    try:
        data = base64.b64decode(encrypted_str)
        key = GPX_ENCRYPTION_KEY.encode('utf-8')
        xored = bytearray(b ^ key[i % len(key)] for i, b in enumerate(data))
        return xored.decode('utf-8')
    except Exception as e:
        print(f"Polyline decryption error: {e}")
        return None


def main():
    if not os.path.exists('data.json'):
        print("data.json not found. Run fetch_strava.py first.")
        return

    with open('data.json', 'r') as f:
        data = json.load(f)
        queue = data.get('routes', [])
        
    print(f"Found {len(queue)} routes to process...")
    
    # Ensure maps dir exists
    os.makedirs(MAPS_DIR, exist_ok=True)
    
    for item in queue:
        # Decrypt polyline for Mapbox
        raw_polyline = deobfuscate_polyline(item.get('ePolyline'))
        
        if not raw_polyline:
            print(f"  ⚠️ Skipping {item['stravaId']} - No polyline available")
            continue

        activity = {
            'id': item['stravaId'],
            'polyline': raw_polyline
        }
        generate_map(activity)
        
    print("✓ Map generation complete!")
    
    # Optional: cleanup intermediate file
    # if os.path.exists('data.json'):
    #     os.remove('data.json')


if __name__ == '__main__':
    main()
