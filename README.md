# 🏃 The Trail Archive

A premium, automated static website to showcase your trail running activities. Features localized filtering, sorting, pagination, and secure GPX downloads.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Deployment](https://img.shields.io/badge/deploy-GitHub_Pages-green.svg)

## 🎯 Features

- **Automated Daily Updates**: GitHub Actions runs daily to fetch new activities from Strava.
- **Incremental Fetching**: Efficient data updates that only fetch what's new, saving API bandwidth.
- **Secure Data**: Route polylines and detailed streams are XOR-obfuscated to prevent scraping.
- **Rich Aesthetics**: Dark-themed cards with satellite maps and embedded elevation profiles.
- **Advanced UI**: Client-side filtering (distance/elevation), sorting, and pagination.
- **Detailed GPX Downloads**: Custom GPX files generated on-the-fly with elevation data.
- **Privacy First**: No Strava data is stored in the git history. The repository remains a clean code template even after deployment.
- **Developer Friendly**: Built with Vanilla JS, CSS, and Python. No heavy frameworks required.

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
│   ├── maps/               # Generated satellite maps
│   └── streams/            # Encrypted stream data (.dat)
├── scripts/
│   ├── fetch_strava.py     # Main data fetcher (incremental)
│   ├── generate_maps.py    # Map & Profile generator
│   └── requirements.txt    # Python dependencies
├── index.html              # Main UI
├── app.js                  # Frontend Logic & GPX Generator
├── styles.css              # Custom styles
└── data.json/athlete.json  # Generated metadata (ignored by git)
```

---

## 🛠️ Technical Details

### Incremental Fetching
The `fetch_strava.py` script maintains a local `all_routes.json` cache. On each run, it checks the latest activity date and only requests newer activities from Strava, minimizing API hits.

### GPX Filename Convention
Generated GPX files follow the naming pattern:
`[stravaID]_[distance]K_[elevation]m.gpx`
Example: `12345678_42K_1500m.gpx`

### Obfuscation
Detailed coordinates and elevation data are XOR-encrypted using your `GPX_ENCRYPTION_KEY`. This ensures that while the site is public, your raw activity data is protected from bulk scrapers.

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
