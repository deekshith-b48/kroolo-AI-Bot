import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException

from src.core.webhook import TelegramUpdate, verify_telegram_signature
from src.core.security import security_manager

class TestTelegramUpdate:
    """Test Telegram update validation."""
    
    def test_valid_update(self):
        """Test valid update data."""
        update_data = {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {"id": 123, "first_name": "Test"},
                "chat": {"id": 456, "type": "private"},
                "text": "Hello"
            }
        }
        
        update = TelegramUpdate(**update_data)
        assert update.update_id == 123456789
        assert update.message is not None
        assert update.message.text == "Hello"
    
    def test_invalid_update(self):
        """Test invalid update data."""
        with pytest.raises(ValueError):
            TelegramUpdate(update_id="invalid")

class TestWebhookEndpoints:
    """Test webhook endpoints."""
    
    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_webhook_info(self, client: TestClient):
        """Test webhook info endpoint."""
        response = client.get("/webhook")
        assert response.status_code == 200
        data = response.json()
        assert "webhook_url" in data
    
    def test_webhook_validation(self, client: TestClient, mock_telegram_update):
        """Test webhook validation."""
        with patch('src.core.webhook.verify_telegram_signature') as mock_verify:
            mock_verify.return_value = "valid_token"
            
            response = client.post(
                "/webhook",
                json=mock_telegram_update,
                headers={"X-Telegram-Bot-Api-Secret-Token": "valid_token"}
            )
            
            assert response.status_code == 200
    
    def test_webhook_invalid_signature(self, client: TestClient, mock_telegram_update):
        """Test webhook with invalid signature."""
        with patch('src.core.webhook.verify_telegram_signature') as mock_verify:
            mock_verify.side_effect = HTTPException(status_code=401, detail="Invalid signature")
            
            response = client.post(
                "/webhook",
                json=mock_telegram_update,
                headers={"X-Telegram-Bot-Api-Secret-Token": "invalid_token"}
            )
            
            assert response.status_code == 401
    
    def test_webhook_rate_limited(self, client: TestClient, mock_telegram_update):
        """Test webhook rate limiting."""
        with patch('src.core.webhook.verify_telegram_signature') as mock_verify, \
             patch('src.core.webhook.rate_limiter.check_rate_limit') as mock_rate_limit:
            
            mock_verify.return_value = "valid_token"
            mock_rate_limit.return_value = False  # Rate limited
            
            response = client.post(
                "/webhook",
                json=mock_telegram_update,
                headers={"X-Telegram-Bot-Api-Secret-Token": "valid_token"}
            )
            
            assert response.status_code == 429
    
    def test_webhook_delete(self, client: TestClient):
        """Test webhook deletion endpoint."""
        response = client.delete("/webhook")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "webhook_deleted"

class TestSecurityFeatures:
    """Test security features."""
    
    def test_telegram_signature_verification(self):
        """Test Telegram signature verification."""
        # This would test the actual signature verification logic
        # For now, we'll test the function exists
        assert callable(verify_telegram_signature)
    
    def test_security_manager(self):
        """Test security manager functionality."""
        # Test IP blocking
        security_manager.block_ip("192.168.1.1", "Test blocking")
        assert "192.168.1.1" in security_manager.blocked_ips
        
        # Test suspicious activity tracking
        security_manager.record_suspicious_activity("192.168.1.2", "Test activity")
        assert len(security_manager.suspicious_activities) > 0

class TestErrorHandling:
    """Test error handling in webhook."""
    
    def test_malformed_json(self, client: TestClient):
        """Test handling of malformed JSON."""
        response = client.post(
            "/webhook",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_missing_required_fields(self, client: TestClient):
        """Test handling of missing required fields."""
        response = client.post(
            "/webhook",
            json={"update_id": 123},  # Missing message
            headers={"X-Telegram-Bot-Api-Secret-Token": "valid_token"}
        )
        assert response.status_code == 422
    
    def test_large_message_handling(self, client: TestClient):
        """Test handling of very large messages."""
        large_message = "x" * 10000  # Very long message
        
        update_data = {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {"id": 123, "first_name": "Test"},
                "chat": {"id": 456, "type": "private"},
                "text": large_message
            }
        }
        
        with patch('src.core.webhook.verify_telegram_signature') as mock_verify:
            mock_verify.return_value = "valid_token"
            
            response = client.post(
                "/webhook",
                json=update_data,
                headers={"X-Telegram-Bot-Api-Secret-Token": "valid_token"}
            )
            
            # Should handle large messages gracefully
            assert response.status_code in [200, 413]

class TestWebhookPerformance:
    """Test webhook performance characteristics."""
    
    def test_concurrent_requests(self, client: TestClient, mock_telegram_update):
        """Test handling of concurrent webhook requests."""
        import asyncio
        import time
        
        async def send_concurrent_requests():
            with patch('src.core.webhook.verify_telegram_signature') as mock_verify:
                mock_verify.return_value = "valid_token"
                
                start_time = time.time()
                
                # Send multiple concurrent requests
                tasks = []
                for i in range(10):
                    task = asyncio.create_task(
                        client.post(
                            "/webhook",
                            json=mock_telegram_update,
                            headers={"X-Telegram-Bot-Api-Secret-Token": "valid_token"}
                        )
                    )
                    tasks.append(task)
                
                responses = await asyncio.gather(*tasks)
                end_time = time.time()
                
                # All requests should succeed
                assert all(r.status_code == 200 for r in responses)
                
                # Should handle concurrent requests efficiently
                assert end_time - start_time < 5.0  # Should complete within 5 seconds
        
        asyncio.run(send_concurrent_requests())
    
    def test_large_batch_processing(self, client: TestClient):
        """Test processing of large batches of updates."""
        # Create a batch of updates
        batch_updates = []
        for i in range(100):
            update = {
                "update_id": 123456789 + i,
                "message": {
                    "message_id": i + 1,
                    "from": {"id": 123 + i, "first_name": f"User{i}"},
                    "chat": {"id": 456 + i, "type": "private"},
                    "text": f"Message {i}"
                }
            }
            batch_updates.append(update)
        
        with patch('src.core.webhook.verify_telegram_signature') as mock_verify:
            mock_verify.return_value = "valid_token"
            
            # Process batch
            start_time = time.time()
            for update in batch_updates:
                response = client.post(
                    "/webhook",
                    json=update,
                    headers={"X-Telegram-Bot-Api-Secret-Token": "valid_token"}
                )
                assert response.status_code == 200
            
            end_time = time.time()
            
            # Should process batch efficiently
            assert end_time - start_time < 30.0  # Should complete within 30 seconds
