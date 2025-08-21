import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json

try:
    from prometheus_client import Counter, Histogram, Gauge, Summary, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("Prometheus client not available. Metrics will be limited.")

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collects and manages application metrics for monitoring and observability."""
    
    def __init__(self):
        self.is_initialized = False
        
        # In-memory metrics storage
        self.message_metrics = {
            "total_messages": 0,
            "messages_by_type": defaultdict(int),
            "messages_by_agent": defaultdict(int),
            "messages_by_chat": defaultdict(int),
            "messages_by_user": defaultdict(int)
        }
        
        self.response_metrics = {
            "total_responses": 0,
            "response_times": deque(maxlen=1000),
            "response_sizes": deque(maxlen=1000),
            "responses_by_agent": defaultdict(int),
            "successful_responses": 0,
            "failed_responses": 0
        }
        
        self.error_metrics = {
            "total_errors": 0,
            "errors_by_type": defaultdict(int),
            "errors_by_agent": defaultdict(int),
            "errors_by_chat": defaultdict(int),
            "error_timestamps": deque(maxlen=1000)
        }
        
        self.performance_metrics = {
            "active_connections": 0,
            "memory_usage": 0,
            "cpu_usage": 0,
            "database_connections": 0,
            "cache_hit_rate": 0.0
        }
        
        self.agent_metrics = {
            "active_agents": 0,
            "agent_response_times": defaultdict(list),
            "agent_usage_counts": defaultdict(int),
            "agent_error_counts": defaultdict(int)
        }
        
        self.rate_limit_metrics = {
            "total_rate_limited": 0,
            "rate_limited_by_user": defaultdict(int),
            "rate_limited_by_chat": defaultdict(int),
            "rate_limit_violations": defaultdict(int)
        }
        
        # Prometheus metrics (if available)
        if PROMETHEUS_AVAILABLE:
            self._setup_prometheus_metrics()
        
        # Metrics history for trending
        self.metrics_history = deque(maxlen=1000)
        self.last_cleanup = time.time()
        self.cleanup_interval = 3600  # 1 hour
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics."""
        try:
            # Message metrics
            self.prometheus_metrics = {
                "messages_total": Counter(
                    "kroolo_messages_total",
                    "Total number of messages processed",
                    ["message_type", "chat_type"]
                ),
                "messages_by_agent": Counter(
                    "kroolo_messages_by_agent_total",
                    "Total number of messages by agent",
                    ["agent_type", "agent_handle"]
                ),
                "response_time": Histogram(
                    "kroolo_response_time_seconds",
                    "Response time in seconds",
                    ["agent_type", "response_status"]
                ),
                "response_size": Histogram(
                    "kroolo_response_size_bytes",
                    "Response size in bytes",
                    ["agent_type"]
                ),
                "errors_total": Counter(
                    "kroolo_errors_total",
                    "Total number of errors",
                    ["error_type", "agent_type"]
                ),
                "rate_limited_total": Counter(
                    "kroolo_rate_limited_total",
                    "Total number of rate limited requests",
                    ["limit_type", "user_id"]
                ),
                "active_connections": Gauge(
                    "kroolo_active_connections",
                    "Number of active connections"
                ),
                "memory_usage_bytes": Gauge(
                    "kroolo_memory_usage_bytes",
                    "Memory usage in bytes"
                ),
                "cpu_usage_percent": Gauge(
                    "kroolo_cpu_usage_percent",
                    "CPU usage percentage"
                ),
                "database_connections": Gauge(
                    "kroolo_database_connections",
                    "Number of database connections"
                ),
                "cache_hit_rate": Gauge(
                    "kroolo_cache_hit_rate",
                    "Cache hit rate percentage"
                )
            }
        except Exception as e:
            logger.error(f"Failed to setup Prometheus metrics: {e}")
            self.prometheus_metrics = {}
    
    async def initialize(self):
        """Initialize the metrics collector."""
        try:
            # Start background tasks
            asyncio.create_task(self._cleanup_loop())
            asyncio.create_task(self._metrics_collection_loop())
            
            self.is_initialized = True
            logger.info("Metrics collector initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize metrics collector: {e}")
            raise
    
    async def record_message(self, message_info: Dict[str, Any]):
        """Record message metrics."""
        try:
            # Update in-memory metrics
            self.message_metrics["total_messages"] += 1
            
            message_type = message_info.get("message_type", "unknown")
            self.message_metrics["messages_by_type"][message_type] += 1
            
            chat_id = message_info.get("chat_id")
            if chat_id:
                self.message_metrics["messages_by_chat"][str(chat_id)] += 1
            
            user_id = message_info.get("user_id")
            if user_id:
                self.message_metrics["messages_by_user"][str(user_id)] += 1
            
            # Update Prometheus metrics
            if PROMETHEUS_AVAILABLE and "messages_total" in self.prometheus_metrics:
                chat_type = message_info.get("chat_type", "unknown")
                self.prometheus_metrics["messages_total"].labels(
                    message_type=message_type,
                    chat_type=chat_type
                ).inc()
        
        except Exception as e:
            logger.error(f"Failed to record message metrics: {e}")
    
    async def record_agent_response(self, agent_info: Dict[str, Any], response_info: Dict[str, Any]):
        """Record agent response metrics."""
        try:
            # Update in-memory metrics
            self.response_metrics["total_responses"] += 1
            
            agent_type = agent_info.get("agent_type", "unknown")
            agent_handle = agent_info.get("handle", "unknown")
            
            self.response_metrics["responses_by_agent"][agent_type] += 1
            
            # Record response time
            response_time = response_info.get("response_time", 0)
            if response_time > 0:
                self.response_metrics["response_times"].append(response_time)
                self.agent_metrics["agent_response_times"][agent_type].append(response_time)
            
            # Record response size
            response_size = response_info.get("response_size", 0)
            if response_size > 0:
                self.response_metrics["response_sizes"].append(response_size)
            
            # Record success/failure
            if response_info.get("success", False):
                self.response_metrics["successful_responses"] += 1
            else:
                self.response_metrics["failed_responses"] += 1
            
            # Update agent usage
            self.agent_metrics["agent_usage_counts"][agent_type] += 1
            
            # Update Prometheus metrics
            if PROMETHEUS_AVAILABLE:
                if "messages_by_agent" in self.prometheus_metrics:
                    self.prometheus_metrics["messages_by_agent"].labels(
                        agent_type=agent_type,
                        agent_handle=agent_handle
                    ).inc()
                
                if "response_time" in self.prometheus_metrics:
                    response_status = "success" if response_info.get("success", False) else "failure"
                    self.prometheus_metrics["response_time"].labels(
                        agent_type=agent_type,
                        response_status=response_status
                    ).observe(response_time)
                
                if "response_size" in self.prometheus_metrics:
                    self.prometheus_metrics["response_size"].labels(
                        agent_type=agent_type
                    ).observe(response_size)
        
        except Exception as e:
            logger.error(f"Failed to record agent response metrics: {e}")
    
    async def record_error(self, error_info: Dict[str, Any]):
        """Record error metrics."""
        try:
            # Update in-memory metrics
            self.error_metrics["total_errors"] += 1
            
            error_type = error_info.get("error_type", "unknown")
            self.error_metrics["errors_by_type"][error_type] += 1
            
            agent_type = error_info.get("agent_type", "unknown")
            self.error_metrics["errors_by_agent"][agent_type] += 1
            
            chat_id = error_info.get("chat_id")
            if chat_id:
                self.error_metrics["errors_by_chat"][str(chat_id)] += 1
            
            # Record error timestamp
            self.error_metrics["error_timestamps"].append(time.time())
            
            # Update agent error count
            self.agent_metrics["agent_error_counts"][agent_type] += 1
            
            # Update Prometheus metrics
            if PROMETHEUS_AVAILABLE and "errors_total" in self.prometheus_metrics:
                self.prometheus_metrics["errors_total"].labels(
                    error_type=error_type,
                    agent_type=agent_type
                ).inc()
        
        except Exception as e:
            logger.error(f"Failed to record error metrics: {e}")
    
    async def record_rate_limit(self, rate_limit_info: Dict[str, Any]):
        """Record rate limit metrics."""
        try:
            # Update in-memory metrics
            self.rate_limit_metrics["total_rate_limited"] += 1
            
            limit_type = rate_limit_info.get("limit_type", "unknown")
            self.rate_limit_metrics["rate_limit_violations"][limit_type] += 1
            
            user_id = rate_limit_info.get("user_id")
            if user_id:
                self.rate_limit_metrics["rate_limited_by_user"][str(user_id)] += 1
            
            chat_id = rate_limit_info.get("chat_id")
            if chat_id:
                self.rate_limit_metrics["rate_limited_by_chat"][str(chat_id)] += 1
            
            # Update Prometheus metrics
            if PROMETHEUS_AVAILABLE and "rate_limited_total" in self.prometheus_metrics:
                self.prometheus_metrics["rate_limited_total"].labels(
                    limit_type=limit_type,
                    user_id=str(user_id) if user_id else "unknown"
                ).inc()
        
        except Exception as e:
            logger.error(f"Failed to record rate limit metrics: {e}")
    
    async def update_performance_metrics(self, performance_info: Dict[str, Any]):
        """Update performance metrics."""
        try:
            # Update in-memory metrics
            for key, value in performance_info.items():
                if key in self.performance_metrics:
                    self.performance_metrics[key] = value
            
            # Update Prometheus metrics
            if PROMETHEUS_AVAILABLE:
                if "active_connections" in self.prometheus_metrics:
                    self.prometheus_metrics["active_connections"].set(
                        performance_info.get("active_connections", 0)
                    )
                
                if "memory_usage_bytes" in self.prometheus_metrics:
                    self.prometheus_metrics["memory_usage_bytes"].set(
                        performance_info.get("memory_usage", 0)
                    )
                
                if "cpu_usage_percent" in self.prometheus_metrics:
                    self.prometheus_metrics["cpu_usage_percent"].set(
                        performance_info.get("cpu_usage", 0)
                    )
                
                if "database_connections" in self.prometheus_metrics:
                    self.prometheus_metrics["database_connections"].set(
                        performance_info.get("database_connections", 0)
                    )
                
                if "cache_hit_rate" in self.prometheus_metrics:
                    self.prometheus_metrics["cache_hit_rate"].set(
                        performance_info.get("cache_hit_rate", 0.0)
                    )
        
        except Exception as e:
            logger.error(f"Failed to update performance metrics: {e}")
    
    async def get_metrics(self, include_history: bool = False) -> Dict[str, Any]:
        """Get current metrics."""
        try:
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "message_metrics": dict(self.message_metrics),
                "response_metrics": dict(self.response_metrics),
                "error_metrics": dict(self.error_metrics),
                "performance_metrics": dict(self.performance_metrics),
                "agent_metrics": dict(self.agent_metrics),
                "rate_limit_metrics": dict(self.rate_limit_metrics)
            }
            
            # Calculate derived metrics
            metrics["derived_metrics"] = self._calculate_derived_metrics()
            
            # Include history if requested
            if include_history:
                metrics["metrics_history"] = list(self.metrics_history)
            
            return metrics
        
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {"error": str(e)}
    
    def _calculate_derived_metrics(self) -> Dict[str, Any]:
        """Calculate derived metrics from raw data."""
        try:
            derived = {}
            
            # Response time statistics
            if self.response_metrics["response_times"]:
                times = list(self.response_metrics["response_times"])
                derived["avg_response_time"] = sum(times) / len(times)
                derived["min_response_time"] = min(times)
                derived["max_response_time"] = max(times)
                derived["p95_response_time"] = sorted(times)[int(len(times) * 0.95)]
                derived["p99_response_time"] = sorted(times)[int(len(times) * 0.99)]
            
            # Response size statistics
            if self.response_metrics["response_sizes"]:
                sizes = list(self.response_metrics["response_sizes"])
                derived["avg_response_size"] = sum(sizes) / len(sizes)
                derived["min_response_size"] = min(sizes)
                derived["max_response_size"] = max(sizes)
            
            # Success rate
            total_responses = self.response_metrics["total_responses"]
            if total_responses > 0:
                derived["success_rate"] = (
                    self.response_metrics["successful_responses"] / total_responses
                ) * 100
            
            # Error rate
            total_messages = self.message_metrics["total_messages"]
            if total_messages > 0:
                derived["error_rate"] = (
                    self.error_metrics["total_errors"] / total_messages
                ) * 100
            
            # Rate limit rate
            if total_messages > 0:
                derived["rate_limit_rate"] = (
                    self.rate_limit_metrics["total_rate_limited"] / total_messages
                ) * 100
            
            # Agent performance
            for agent_type, response_times in self.agent_metrics["agent_response_times"].items():
                if response_times:
                    avg_time = sum(response_times) / len(response_times)
                    derived[f"avg_response_time_{agent_type}"] = avg_time
            
            return derived
        
        except Exception as e:
            logger.error(f"Failed to calculate derived metrics: {e}")
            return {}
    
    async def _cleanup_loop(self):
        """Background cleanup loop for old metrics."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                current_time = time.time()
                
                # Clean up old error timestamps
                cutoff_time = current_time - 86400  # 24 hours
                self.error_metrics["error_timestamps"] = deque(
                    [ts for ts in self.error_metrics["error_timestamps"] if ts > cutoff_time],
                    maxlen=1000
                )
                
                # Clean up old response times (keep last 1000)
                for agent_type in self.agent_metrics["agent_response_times"]:
                    times = self.agent_metrics["agent_response_times"][agent_type]
                    if len(times) > 1000:
                        self.agent_metrics["agent_response_times"][agent_type] = times[-1000:]
                
                self.last_cleanup = current_time
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _metrics_collection_loop(self):
        """Background loop for collecting system metrics."""
        while True:
            try:
                await asyncio.sleep(60)  # Collect every minute
                
                # Collect system metrics
                import psutil
                
                performance_info = {
                    "memory_usage": psutil.virtual_memory().used,
                    "cpu_usage": psutil.cpu_percent(interval=1),
                    "active_connections": len(psutil.net_connections()),
                }
                
                await self.update_performance_metrics(performance_info)
                
                # Store metrics snapshot in history
                current_metrics = await self.get_metrics(include_history=False)
                self.metrics_history.append(current_metrics)
                
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def get_prometheus_metrics(self) -> str:
        """Get Prometheus-formatted metrics."""
        if not PROMETHEUS_AVAILABLE:
            return "# Prometheus client not available"
        
        try:
            return generate_latest()
        except Exception as e:
            logger.error(f"Failed to generate Prometheus metrics: {e}")
            return f"# Error generating metrics: {e}"
    
    async def health_check(self) -> Dict[str, Any]:
        """Check metrics collector health."""
        try:
            return {
                "status": "healthy" if self.is_initialized else "unhealthy",
                "is_initialized": self.is_initialized,
                "prometheus_available": PROMETHEUS_AVAILABLE,
                "metrics_count": {
                    "total_messages": self.message_metrics["total_messages"],
                    "total_responses": self.response_metrics["total_responses"],
                    "total_errors": self.error_metrics["total_errors"],
                    "total_rate_limited": self.rate_limit_metrics["total_rate_limited"]
                },
                "last_cleanup": self.last_cleanup,
                "metrics_history_size": len(self.metrics_history)
            }
        except Exception as e:
            logger.error(f"Failed to check metrics collector health: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        try:
            # Reset all metric counters
            self.message_metrics = {
                "total_messages": 0,
                "messages_by_type": defaultdict(int),
                "messages_by_chat": defaultdict(int),
                "messages_by_user": defaultdict(int)
            }
            
            self.response_metrics = {
                "total_responses": 0,
                "response_times": deque(maxlen=1000),
                "response_sizes": deque(maxlen=1000),
                "responses_by_agent": defaultdict(int),
                "successful_responses": 0,
                "failed_responses": 0
            }
            
            self.error_metrics = {
                "total_errors": 0,
                "errors_by_type": defaultdict(int),
                "errors_by_agent": defaultdict(int),
                "errors_by_chat": defaultdict(int),
                "error_timestamps": deque(maxlen=1000)
            }
            
            self.agent_metrics = {
                "active_agents": 0,
                "agent_response_times": defaultdict(list),
                "agent_usage_counts": defaultdict(int),
                "agent_error_counts": defaultdict(int)
            }
            
            self.rate_limit_metrics = {
                "total_rate_limited": 0,
                "rate_limited_by_user": defaultdict(int),
                "rate_limited_by_chat": defaultdict(int),
                "rate_limit_violations": defaultdict(int)
            }
            
            # Clear history
            self.metrics_history.clear()
            
            logger.info("Metrics reset successfully")
        
        except Exception as e:
            logger.error(f"Failed to reset metrics: {e}")

# Global instance
metrics_collector = MetricsCollector()
