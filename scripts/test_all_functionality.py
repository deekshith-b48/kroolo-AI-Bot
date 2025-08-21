#!/usr/bin/env python3
"""
Comprehensive functionality test for Kroolo AI Bot.
Tests all major components and APIs.
"""

import asyncio
import json
import logging
import requests
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test health check endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Health Check: {data['status']} - {data['message']}")
            return True
        else:
            logger.error(f"❌ Health Check Failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Health Check Error: {e}")
        return False

def test_root_endpoint():
    """Test root endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Root Endpoint: {data['service']} v{data['version']}")
            return True
        else:
            logger.error(f"❌ Root Endpoint Failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Root Endpoint Error: {e}")
        return False

def test_telegram_webhook():
    """Test Telegram webhook endpoint."""
    try:
        # Sample Telegram update
        telegram_update = {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {
                    "id": 987654321,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "testuser"
                },
                "chat": {
                    "id": -100123456789,
                    "type": "group",
                    "title": "Test Group"
                },
                "date": int(time.time()),
                "text": "Hello @AlanTuring! How are you?"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/telegram/webhook/krooloAgentBot",
            json=telegram_update,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Telegram Webhook: Update {data['update_id']} processed")
            logger.info(f"   Simulated Response: {data['simulated_response']}")
            return True
        else:
            logger.error(f"❌ Telegram Webhook Failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Telegram Webhook Error: {e}")
        return False

def test_api_documentation():
    """Test API documentation availability."""
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            logger.info("✅ API Documentation: Available at /docs")
            return True
        else:
            logger.error(f"❌ API Documentation Failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ API Documentation Error: {e}")
        return False

def test_openapi_schema():
    """Test OpenAPI schema endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ OpenAPI Schema: {data['info']['title']} v{data['info']['version']}")
            logger.info(f"   Available paths: {len(data.get('paths', {}))} endpoints")
            return True
        else:
            logger.error(f"❌ OpenAPI Schema Failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ OpenAPI Schema Error: {e}")
        return False

def test_services_status():
    """Test external services status."""
    services_status = {}
    
    # Test PostgreSQL
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="kroolo",
            user="kroolo", 
            password="password"
        )
        conn.close()
        services_status["postgresql"] = "✅ Available"
    except Exception as e:
        services_status["postgresql"] = f"❌ Unavailable: {str(e)[:50]}"
    
    # Test Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        services_status["redis"] = "✅ Available"
    except Exception as e:
        services_status["redis"] = f"❌ Unavailable: {str(e)[:50]}"
    
    # Test Qdrant
    try:
        response = requests.get("http://localhost:6333/health", timeout=2)
        if response.status_code == 200:
            services_status["qdrant"] = "✅ Available"
        else:
            services_status["qdrant"] = f"❌ HTTP {response.status_code}"
    except Exception as e:
        services_status["qdrant"] = f"❌ Unavailable: {str(e)[:50]}"
    
    logger.info("🔍 External Services Status:")
    for service, status in services_status.items():
        logger.info(f"   {service}: {status}")
    
    return services_status

def run_comprehensive_test():
    """Run all tests and generate report."""
    logger.info("🧪 Starting Comprehensive Kroolo AI Bot Test...")
    logger.info("=" * 60)
    
    test_results = {}
    
    # Test all components
    test_results["health_check"] = test_health_check()
    test_results["root_endpoint"] = test_root_endpoint()
    test_results["telegram_webhook"] = test_telegram_webhook()
    test_results["api_documentation"] = test_api_documentation()
    test_results["openapi_schema"] = test_openapi_schema()
    
    # Test services
    services_status = test_services_status()
    
    # Generate report
    logger.info("=" * 60)
    logger.info("📊 TEST RESULTS SUMMARY")
    logger.info("=" * 60)
    
    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    
    logger.info(f"🎯 Overall: {passed_tests}/{total_tests} tests passed")
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"   {test_name}: {status}")
    
    # Service status summary
    logger.info("\n🔧 External Services:")
    for service, status in services_status.items():
        logger.info(f"   {service}: {status}")
    
    # Final status
    if passed_tests == total_tests:
        logger.info("\n🎉 ALL TESTS PASSED! Kroolo AI Bot is fully functional!")
        logger.info("🚀 Ready for production deployment with real credentials")
    else:
        logger.info(f"\n⚠️  {total_tests - passed_tests} tests failed. Check logs above.")
    
    logger.info("=" * 60)
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = run_comprehensive_test()
    exit(0 if success else 1)
