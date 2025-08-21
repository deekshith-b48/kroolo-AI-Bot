#!/usr/bin/env python3
"""
Simple test script for Kroolo Agent Bot
"""

import os
import sys
from pathlib import Path

def test_basic_setup():
    """Test basic setup without complex imports"""
    print("🚀 Kroolo Agent Bot Basic Setup Test")
    print("=" * 40)
    
    # Test 1: File structure
    print("🔍 Testing file structure...")
    required_files = [
        'app.py',
        'db.py',
        'requirements.txt',
        'docker-compose.yml',
        'Dockerfile',
        'deploy.sh'
    ]
    
    required_dirs = [
        'services',
        'handlers',
        'utils'
    ]
    
    all_good = True
    
    for file in required_files:
        if Path(file).exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file}")
            all_good = False
    
    for dir_name in required_dirs:
        if Path(dir_name).exists():
            print(f"  ✅ {dir_name}/")
        else:
            print(f"  ❌ {dir_name}/")
            all_good = False
    
    if not all_good:
        print("❌ File structure test failed")
        return False
    
    print("✅ File structure test passed")
    
    # Test 2: Environment file
    print("\n🔍 Testing environment setup...")
    if Path(".env").exists():
        print("  ✅ .env file exists")
    elif Path("env.example").exists():
        print("  ⚠️  .env file not found, but env.example exists")
        print("  💡 Please copy env.example to .env and configure it")
    else:
        print("  ❌ No environment files found")
        all_good = False
    
    # Test 3: Requirements
    print("\n🔍 Testing requirements...")
    if Path("requirements.txt").exists():
        print("  ✅ requirements.txt exists")
        with open("requirements.txt", "r") as f:
            lines = f.readlines()
            print(f"  📦 {len(lines)} dependencies listed")
    else:
        print("  ❌ requirements.txt not found")
        all_good = False
    
    # Test 4: Docker setup
    print("\n🔍 Testing Docker setup...")
    if Path("docker-compose.yml").exists():
        print("  ✅ docker-compose.yml exists")
    if Path("Dockerfile").exists():
        print("  ✅ Dockerfile exists")
    if Path("deploy.sh").exists():
        print("  ✅ deploy.sh exists")
        # Check if executable
        if os.access("deploy.sh", os.X_OK):
            print("  ✅ deploy.sh is executable")
        else:
            print("  ⚠️  deploy.sh is not executable")
    
    # Test 5: Basic Python syntax
    print("\n🔍 Testing Python syntax...")
    try:
        # Try to import basic modules
        import fastapi
        print("  ✅ FastAPI module available")
    except ImportError:
        print("  ❌ FastAPI not installed - run: pip install -r requirements.txt")
        all_good = False
    
    try:
        import telegram
        print("  ✅ python-telegram-bot module available")
    except ImportError:
        print("  ❌ python-telegram-bot not installed - run: pip install -r requirements.txt")
        all_good = False
    
    # Summary
    print("\n" + "=" * 40)
    if all_good:
        print("🎉 Basic setup test passed!")
        print("\nNext steps:")
        print("1. Configure your .env file with bot tokens")
        print("2. Start Redis: redis-server")
        print("3. Deploy locally: ./deploy.sh local")
        print("4. Or deploy with ngrok: ./deploy.sh ngrok")
    else:
        print("❌ Some basic tests failed. Please fix the issues above.")
    
    return all_good

if __name__ == "__main__":
    test_basic_setup()
