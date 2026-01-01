"""HTTP client with retries, timeouts, and circuit breaker."""
import httpx
from typing import Optional, Dict, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryCallState
)
import structlog
from datetime import datetime, timedelta

logger = structlog.get_logger(__name__)


class CircuitBreaker:
    """Simple circuit breaker to avoid hammering down services."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half_open
    
    def call_succeeded(self):
        """Reset on success."""
        self.failure_count = 0
        self.state = "closed"
    
    def call_failed(self):
        """Record failure."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                "circuit_breaker_opened",
                failure_count=self.failure_count,
                threshold=self.failure_threshold
            )
    
    def can_attempt(self) -> bool:
        """Check if we can attempt a call."""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout:
                    self.state = "half_open"
                    logger.info("circuit_breaker_half_open")
                    return True
            return False
        
        # half_open: allow one attempt
        return True


class RobustHTTPClient:
    """HTTP client with retries, timeouts, and circuit breaker."""
    
    def __init__(
        self,
        default_timeout: float = 30.0,
        max_retries: int = 3,
        retry_backoff_base: float = 2.0,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60
    ):
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.retry_backoff_base = retry_backoff_base
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
    
    def _get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for a service."""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker(
                failure_threshold=self.circuit_breaker_threshold,
                timeout=self.circuit_breaker_timeout
            )
        return self.circuit_breakers[service_name]
    
    def _log_retry(self, retry_state: RetryCallState):
        """Log retry attempts."""
        logger.warning(
            "http_retry_attempt",
            attempt=retry_state.attempt_number,
            max_attempts=self.max_retries,
            exception=str(retry_state.outcome.exception())
        )
    
    @retry(
        stop=stop_after_attempt(4),  # 1 initial + 3 retries
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException))
    )
    async def get_async(
        self,
        url: str,
        service_name: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> httpx.Response:
        """GET request with retries and circuit breaker."""
        timeout = timeout or self.default_timeout
        cb = self._get_circuit_breaker(service_name)
        
        if not cb.can_attempt():
            raise httpx.HTTPError(f"Circuit breaker open for {service_name}")
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                cb.call_succeeded()
                return response
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            cb.call_failed()
            logger.error(
                "http_request_failed",
                service=service_name,
                url=url,
                error=str(e),
                circuit_breaker_state=cb.state
            )
            raise
    
    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException))
    )
    async def delete_async(
        self,
        url: str,
        service_name: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> httpx.Response:
        """DELETE request with retries and circuit breaker."""
        timeout = timeout or self.default_timeout
        cb = self._get_circuit_breaker(service_name)
        
        if not cb.can_attempt():
            raise httpx.HTTPError(f"Circuit breaker open for {service_name}")
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.delete(url, headers=headers, params=params)
                response.raise_for_status()
                cb.call_succeeded()
                return response
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            cb.call_failed()
            logger.error(
                "http_delete_failed",
                service=service_name,
                url=url,
                error=str(e),
                circuit_breaker_state=cb.state
            )
            raise
    
    def get_sync(
        self,
        url: str,
        service_name: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> httpx.Response:
        """GET request (synchronous) with retries and circuit breaker."""
        timeout = timeout or self.default_timeout
        cb = self._get_circuit_breaker(service_name)
        
        if not cb.can_attempt():
            raise httpx.HTTPError(f"Circuit breaker open for {service_name}")
        
        max_attempts = self.max_retries + 1
        for attempt in range(1, max_attempts + 1):
            try:
                with httpx.Client(timeout=timeout) as client:
                    response = client.get(url, headers=headers, params=params)
                    response.raise_for_status()
                    cb.call_succeeded()
                    return response
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                if attempt < max_attempts:
                    wait_time = min(self.retry_backoff_base ** (attempt - 1), 10)
                    logger.warning(
                        "http_retry_attempt_sync",
                        service=service_name,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        wait_seconds=wait_time,
                        error=str(e)
                    )
                    import time
                    time.sleep(wait_time)
                else:
                    cb.call_failed()
                    logger.error(
                        "http_request_failed_sync",
                        service=service_name,
                        url=url,
                        error=str(e),
                        circuit_breaker_state=cb.state
                    )
                    raise


# Global instance
_http_client: Optional[RobustHTTPClient] = None


def get_http_client() -> RobustHTTPClient:
    """Get global HTTP client instance."""
    global _http_client
    if _http_client is None:
        _http_client = RobustHTTPClient(
            default_timeout=30.0,
            max_retries=3,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=60
        )
    return _http_client

