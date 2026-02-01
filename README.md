# 🏃 The Trail Archive

A premium, automated static website to showcase your trail running activities. Features localized filtering, sorting, pagination, and secure GPX downloads.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Deployment](https://img.shields.io/badge/deploy-GitHub_Pages-green.svg)

## 🎯 Features

- **Automated Daily Updates**: GitHub Actions runs daily to fetch new activities from Strava.
- **Points of Interest (POI) Engine**: Automatically matches routes with custom markers (summit peaks, warungs, waterfalls) via a configurable POI database.
- **Optimized Map Delivery**: Leverages compressed JPEG map icons (~80% smaller than PNG) for lightning-fast page loads while maintaining high resolution.
- **Custom Tooltip System**: A responsive, touch-friendly "glassmorphism" tooltip system for viewing POI names and detailed stats on both desktop and mobile.
- **Smart Effort Metric**: Categorizes routes based on a calculated Effort score (Distance + Elevation Gain), complete with bespoke filtering and sorting.
- **Responsive Navigation**: Intelligent POI layouts that maintain 2 lines on desktop and up to 3 on mobile to maximize information density.
- **Privacy-Centric Obfuscation**: Detailed polyline and stream data are XOR-encrypted to protect private route details from scraping.
- **Custom Domain Ready**: Pre-configured for deployment to subdomains (e.g., `trail.nurandi.id`) with automated `CNAME` management.
- **Multilingual Support**: Comprehensive Indonesian and English documentation for key features.
- **Secure Data**: Incremental fetching ensures only new activities are downloaded, respecting Strava API limits.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11+
- [Strava API Application](https://www.strava.com/settings/api) (Client ID, Secret, and Refresh Token)
- [Mapbox Access Token](https://account.mapbox.com/access-tokens/) (For map generation)

### 2. Local Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/gpx-web.git
cd gpx-web

# Install dependencies
pip install -r scripts/requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### 3. Fetch Data & Run
```bash
# Fetch data and generate maps
python scripts/fetch_strava.py
python scripts/generate_maps.py

# Start local server
python -m http.server 8000
```
Visit `http://localhost:8000` to view your archive.

---

## 🌐 Deployment to GitHub Pages

This project uses a "Clean Repo" deployment strategy. Your GitHub Action will build the site ephemerally and deploy only the final artifacts to GitHub Pages, keeping your `main` branch clean of data files.

### 1. Update .gitignore
The repository is pre-configured to ignore all generated data (`data.json`, `athlete.json`, `assets/maps/*`, etc.).

### 2. Configure GitHub Secrets
Add the following secrets to your repo (**Settings > Secrets and variables > Actions**):
- `STRAVA_CLIENT_ID`
- `STRAVA_CLIENT_SECRET`
- `STRAVA_REFRESH_TOKEN`
- `MAPBOX_ACCESS_TOKEN`
- `GPX_ENCRYPTION_KEY` (Any random string for obfuscation)

### 3. Enable Pages
- Go to **Settings > Pages**.
- Under **Build and deployment > Source**, select **GitHub Actions**.

The workflow in `.github/workflows/update-data.yml` will now handle daily updates and deployment automatically.

---

## 🔑 Strava Token Guide

The system requires `STRAVA_REFRESH_TOKEN` for long-term automation.

1. **Get Authorization Code**:
   Replace `[CLIENT_ID]` and visit:
   `https://www.strava.com/oauth/authorize?client_id=[CLIENT_ID]&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=activity:read_all`
2. **Exchange Code for Refresh Token**:
   ```bash
   curl -X POST https://www.strava.com/oauth/token \
     -d client_id=[CLIENT_ID] \
     -d client_secret=[CLIENT_SECRET] \
     -d code=[AUTHORIZATION_CODE] \
     -d grant_type=authorization_code
   ```
3. Use the `refresh_token` from the response in your `.env` or GitHub Secrets.

---

## 📁 Project Structure

```
gpx-web/
├── assets/
│   ├── maps/               # Optimized JPEG satellite maps
│   └── streams/            # Obfuscated stream data (.dat)
├── data/
│   └── poi.json            # Curated Point of Interest database
├── scripts/
│   ├── fetch_strava.py     # Data fetcher & POI matching engine
│   ├── generate_maps.py    # Map compression & generation script
│   └── requirements.txt    # Python dependencies
├── index.html              # Main Archive UI
├── app.js                  # Frontend UI, Tooltips & GPX Logic
├── styles.css              # Glassmorphism design system
├── analytics.js            # Google Analytics integration
├── legal.json              # Disclaimer & Privacy metadata
└── CNAME                   # Custom domain configuration
```

---

## 🛠️ Technical Details

### Incremental Fetching
The `fetch_strava.py` script maintains a local `all_routes.json` cache. On each run, it checks the latest activity date and only requests newer activities from Strava, minimizing API hits.

### GPX Filename Convention
Generated GPX files follow the naming pattern:
`[stravaID]_[distance]K_[elevation]m.gpx`
Example: `12345678_42K_1500m.gpx`

### Effort Calculation
Routes are assigned an "Effort" score (in km) to help users gauge difficulty beyond simple distance.
`Effort = Distance + (Elevation Gain / 100) * 1.5`
Example: A 20km run with 1000m gain results in a 35km Effort score.

### Map Optimization
To ensure fast load times, the archive converts all satellite map snapshots from the Mapbox API into optimized JPEGs (85% quality). This reduces the average map file size from ~450KB to under ~70KB without perceptible loss in quality.

### Obfuscation
Detailed coordinates and elevation data are XOR-encrypted using your `GPX_ENCRYPTION_KEY`. This ensures that while the site is public, your raw activity data is protected from bulk scrapers.

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
