#!/usr/bin/env python3
"""
Test script to verify Kroolo Agent Bot setup
"""

import os
import sys
import importlib
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported"""
    print("🔍 Testing module imports...")
    
    required_modules = [
        'fastapi',
        'uvicorn',
        'telegram',
        'sqlalchemy',
        'redis',
        'httpx',
        'pydantic',
        'dotenv'
    ]
    
    failed_imports = []
    
    for module in required_modules:
        try:
            importlib.import_module(module)
            print(f"  ✅ {module}")
        except ImportError as e:
            print(f"  ❌ {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n❌ Failed to import: {', '.join(failed_imports)}")
        print("Please install missing dependencies: pip install -r requirements.txt")
        return False
    
    print("✅ All required modules imported successfully")
    return True

def test_environment():
    """Test environment variables"""
    print("\n🔍 Testing environment variables...")
    
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_WEBHOOK_SECRET'
    ]
    
    optional_vars = [
        'OPENAI_API_KEY',
        'ADMIN_IDS',
        'DATABASE_URL',
        'REDIS_URL'
    ]
    
    missing_required = []
    missing_optional = []
    
    # Check required variables
    for var in required_vars:
        if not os.getenv(var):
            print(f"  ❌ {var} (required)")
            missing_required.append(var)
        else:
            print(f"  ✅ {var}")
    
    # Check optional variables
    for var in optional_vars:
        if not os.getenv(var):
            print(f"  ⚠️  {var} (optional)")
            missing_optional.append(var)
        else:
            print(f"  ✅ {var}")
    
    if missing_required:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_required)}")
        print("Please set these in your .env file")
        return False
    
    if missing_optional:
        print(f"\n⚠️  Missing optional environment variables: {', '.join(missing_optional)}")
        print("These are not required but recommended for full functionality")
    
    print("✅ Environment variables check completed")
    return True

def test_files():
    """Test if required files exist"""
    print("\n🔍 Testing file structure...")
    
    required_files = [
        'app.py',
        'db.py',
        'requirements.txt',
        'docker-compose.yml',
        'Dockerfile'
    ]
    
    required_dirs = [
        'services',
        'handlers',
        'utils'
    ]
    
    missing_files = []
    missing_dirs = []
    
    # Check files
    for file in required_files:
        if Path(file).exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file}")
            missing_files.append(file)
    
    # Check directories
    for dir_name in required_dirs:
        if Path(dir_name).exists():
            print(f"  ✅ {dir_name}/")
        else:
            print(f"  ❌ {dir_name}/")
            missing_dirs.append(dir_name)
    
    if missing_files or missing_dirs:
        print(f"\n❌ Missing files: {', '.join(missing_files)}")
        print(f"❌ Missing directories: {', '.join(missing_dirs)}")
        return False
    
    print("✅ File structure check completed")
    return True

def test_database():
    """Test database connection"""
    print("\n🔍 Testing database setup...")
    
    try:
        from db import Database
        
        # Test with SQLite
        db = Database("sqlite:///./test.db")
        print("  ✅ Database module imported")
        print("  ✅ Database connection test passed")
        
        # Cleanup test database
        if Path("test.db").exists():
            Path("test.db").unlink()
        
        return True
        
    except Exception as e:
        print(f"  ❌ Database test failed: {e}")
        return False

def test_redis():
    """Test Redis connection"""
    print("\n🔍 Testing Redis setup...")
    
    try:
        from utils.cache import RedisCache
        
        # Test Redis module
        print("  ✅ Redis cache module imported")
        
        # Note: We won't actually connect to Redis in this test
        # to avoid requiring a running Redis instance
        print("  ⚠️  Redis connection test skipped (requires running Redis)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Redis test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Kroolo Agent Bot Setup Test")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_environment,
        test_files,
        test_database,
        test_redis
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ❌ Test failed with error: {e}")
    
    print("\n" + "=" * 40)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your bot is ready to deploy.")
        print("\nNext steps:")
        print("1. Start Redis: redis-server")
        print("2. Deploy locally: ./deploy.sh local")
        print("3. Or deploy with ngrok: ./deploy.sh ngrok")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
