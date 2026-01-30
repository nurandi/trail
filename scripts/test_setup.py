#!/usr/bin/env python3
"""
Test script to verify the fetch_strava.py works correctly
Run this before deploying to GitHub Actions
"""

import os
import sys
from pathlib import Path

def check_env_file():
    """Check if .env file exists and has required variables"""
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("   Copy .env.example to .env and add your tokens")
        return False
    
    print("✓ .env file exists")
    
    # Check for required variables
    from dotenv import load_dotenv
    load_dotenv()
    
    strava_token = os.getenv('STRAVA_ACCESS_TOKEN')
    if not strava_token or strava_token == 'your_strava_access_token_here':
        print("❌ STRAVA_ACCESS_TOKEN not configured in .env")
        return False
    
    print("✓ STRAVA_ACCESS_TOKEN is set")
    return True


def check_dependencies():
    """Check if required Python packages are installed"""
    try:
        import requests
        import dotenv
        print("✓ Python dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("   Run: pip install -r scripts/requirements.txt")
        return False


def run_fetch_script():
    """Run the fetch script and check output"""
    print("\nRunning fetch_strava.py...")
    print("-" * 50)
    
    import subprocess
    result = subprocess.run(
        [sys.executable, 'scripts/fetch_strava.py'],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)
    
    if result.returncode != 0:
        print("❌ Fetch script failed")
        return False
    
    print("-" * 50)
    print("✓ Fetch script completed successfully")
    return True


def check_output():
    """Verify that data.json was created"""
    if not os.path.exists('data.json'):
        print("❌ data.json not created")
        return False
    
    # Read and check data.json
    with open('data.json', 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '"routes"' not in content:
        print("❌ data.json has invalid format")
        return False
    
    if 'Sample Trail Run' in content:
        print("⚠️  data.json still contains placeholder data")
        print("   This is OK for initial testing, but make sure Strava fetch works")
    else:
        print("✓ data.json contains real route data")
    
    return True


def main():
    print("=" * 50)
    print("GPX Web - Pre-deployment Test")
    print("=" * 50)
    print()
    
    checks = [
        ("Environment Configuration", check_env_file),
        ("Python Dependencies", check_dependencies),
        ("Fetch Script Execution", run_fetch_script),
        ("Output Validation", check_output),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    for (name, _), result in zip(checks, results):
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print()
    
    if all(results):
        print("🎉 All tests passed! You're ready to deploy to GitHub.")
        print("\nNext steps:")
        print("  1. git add .")
        print("  2. git commit -m 'Initial commit'")
        print("  3. git push")
        print("  4. Set up GitHub Secrets (see QUICKSTART.md)")
        return 0
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
