"""
HTTP客户端模块

公理溯源：自驱公理 - Agent可通过HTTP获取外部知识

设计意图：
- 零外部依赖（仅使用urllib）
- 支持GET/POST/PUT/DELETE
- 超时控制
- 重试机制
- 响应缓存
- 请求限流
"""

import json
import threading
import time
import urllib.request
import urllib.error
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

from exceptions import EternalAgentError


class HTTPClientError(EternalAgentError):
    """HTTP客户端异常"""
    pass


class HTTPTimeoutError(HTTPClientError):
    """HTTP超时异常"""
    pass


class HTTPConnectionError(HTTPClientError):
    """HTTP连接异常"""
    pass


@dataclass
class HTTPResponse:
    """
    HTTP响应

    Attributes:
        status_code: 状态码
        headers: 响应头
        body: 响应体（字符串）
        json_body: 解析后的JSON（如有）
        elapsed_ms: 耗时（毫秒）
        url: 请求URL
    """
    status_code: int = 0
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    json_body: Any = None
    elapsed_ms: float = 0.0
    url: str = ""

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def text(self) -> str:
        return self.body

    def json(self) -> Any:
        """获取JSON响应"""
        if self.json_body is not None:
            return self.json_body
        try:
            self.json_body = json.loads(self.body)
            return self.json_body
        except (json.JSONDecodeError, TypeError):
            raise HTTPClientError(f"响应不是有效JSON: {self.body[:200]}")


@dataclass
class RequestConfig:
    """请求配置"""
    timeout: float = 10.0
    max_retries: int = 2
    retry_delay: float = 1.0
    headers: Dict[str, str] = field(default_factory=dict)
    follow_redirects: bool = True
    verify_ssl: bool = True


class HTTPClient:
    """
    HTTP客户端

    职责：
    - 发送HTTP请求
    - 自动重试
    - 响应缓存
    - 请求限流
    - 请求历史
    """

    def __init__(
        self,
        base_url: str = "",
        default_headers: Optional[Dict[str, str]] = None,
        timeout: float = 10.0,
        max_retries: int = 2,
        cache_ttl: float = 300.0,
        rate_limit: float = 0.0,
    ):
        """
        Args:
            base_url: 基础URL
            default_headers: 默认请求头
            timeout: 默认超时（秒）
            max_retries: 默认重试次数
            cache_ttl: 缓存有效期（秒），0=不缓存
            rate_limit: 请求限流间隔（秒），0=不限
        """
        self._base_url = base_url.rstrip("/") if base_url else ""
        self._default_headers = default_headers or {
            "User-Agent": "EternalAgent/1.0",
            "Accept": "application/json",
        }
        self._config = RequestConfig(
            timeout=timeout,
            max_retries=max_retries,
        )
        self._cache_ttl = cache_ttl
        self._rate_limit = rate_limit

        self._cache: Dict[str, Tuple[HTTPResponse, float]] = {}
        self._lock = threading.Lock()
        self._last_request_time: float = 0.0
        self._history: List[Dict[str, Any]] = []
        self._stats = {
            "total_requests": 0,
            "total_errors": 0,
            "cache_hits": 0,
        }

    @property
    def stats(self) -> Dict[str, int]:
        return dict(self._stats)

    @property
    def history(self) -> List[Dict[str, Any]]:
        return list(self._history)

    def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HTTPResponse:
        """发送GET请求"""
        url = self._build_url(path, params)
        return self._request("GET", url, headers=headers, timeout=timeout)

    def post(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HTTPResponse:
        """发送POST请求"""
        url = self._build_url(path)
        body = None
        req_headers = dict(headers or {})

        if json_data is not None:
            body = json.dumps(json_data).encode("utf-8")
            req_headers.setdefault("Content-Type", "application/json")
        elif data is not None:
            body = urlencode(data).encode("utf-8")
            req_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

        return self._request("POST", url, body=body, headers=req_headers, timeout=timeout)

    def put(
        self,
        path: str,
        json_data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HTTPResponse:
        """发送PUT请求"""
        url = self._build_url(path)
        body = None
        req_headers = dict(headers or {})

        if json_data is not None:
            body = json.dumps(json_data).encode("utf-8")
            req_headers.setdefault("Content-Type", "application/json")

        return self._request("PUT", url, body=body, headers=req_headers, timeout=timeout)

    def delete(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HTTPResponse:
        """发送DELETE请求"""
        url = self._build_url(path)
        return self._request("DELETE", url, headers=headers, timeout=timeout)

    def clear_cache(self) -> int:
        """清空缓存"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def clear_history(self) -> int:
        """清空历史"""
        count = len(self._history)
        self._history.clear()
        return count

    def _build_url(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        """构建完整URL"""
        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            url = f"{self._base_url}/{path.lstrip('/')}" if self._base_url else path

        if params:
            query = urlencode({k: v for k, v in params.items() if v is not None})
            if query:
                url = f"{url}?{query}"

        return url

    def _check_cache(self, method: str, url: str) -> Optional[HTTPResponse]:
        """检查缓存（辅助方法）"""
        if method != "GET" or self._cache_ttl <= 0:
            return None
        cache_key = f"{method}:{url}"
        with self._lock:
            if cache_key in self._cache:
                cached_resp, cached_time = self._cache[cache_key]
                if time.time() - cached_time < self._cache_ttl:
                    self._stats["cache_hits"] += 1
                    return cached_resp
        return None

    def _store_cache(self, method: str, url: str, response: HTTPResponse) -> None:
        """存储缓存（辅助方法）"""
        if method == "GET" and self._cache_ttl > 0 and response.ok:
            cache_key = f"{method}:{url}"
            with self._lock:
                self._cache[cache_key] = (response, time.time())

    def _create_ssl_context(self) -> Any:
        """创建SSL上下文（辅助方法）"""
        if not self._config.verify_ssl:
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return ctx
        return None

    def _request(
        self,
        method: str,
        url: str,
        body: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HTTPResponse:
        """发送请求（带重试和缓存）"""
        # 限流
        if self._rate_limit > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self._rate_limit:
                time.sleep(self._rate_limit - elapsed)

        # GET请求缓存检查
        cached = self._check_cache(method, url)
        if cached:
            return cached

        # 合并请求头
        req_headers = dict(self._default_headers)
        req_headers.update(headers or {})

        timeout_val = timeout or self._config.timeout
        last_error = None
        ssl_ctx = self._create_ssl_context()

        for attempt in range(self._config.max_retries + 1):
            start_time = time.time()
            try:
                req = urllib.request.Request(url, data=body, headers=req_headers, method=method)

                if ssl_ctx:
                    resp = urllib.request.urlopen(req, timeout=timeout_val, context=ssl_ctx)
                else:
                    resp = urllib.request.urlopen(req, timeout=timeout_val)

                elapsed_ms = (time.time() - start_time) * 1000
                response_body = resp.read().decode("utf-8", errors="replace")
                resp_headers = {k: v for k, v in resp.headers.items()}

                http_response = HTTPResponse(
                    status_code=resp.status,
                    headers=resp_headers,
                    body=response_body,
                    elapsed_ms=elapsed_ms,
                    url=url,
                )

                # 缓存GET响应
                self._store_cache(method, url, http_response)

                self._record_history(method, url, resp.status, elapsed_ms, None)
                self._stats["total_requests"] += 1
                self._last_request_time = time.time()
                return http_response

            except urllib.error.HTTPError as e:
                elapsed_ms = (time.time() - start_time) * 1000
                response_body = ""
                try:
                    response_body = e.read().decode("utf-8", errors="replace")
                except Exception:
                    pass

                http_response = HTTPResponse(
                    status_code=e.code,
                    body=response_body,
                    elapsed_ms=elapsed_ms,
                    url=url,
                )
                self._record_history(method, url, e.code, elapsed_ms, str(e))
                self._stats["total_requests"] += 1
                self._stats["total_errors"] += 1
                self._last_request_time = time.time()
                return http_response

            except (urllib.error.URLError, Exception) as e:
                last_error = e
                if attempt < self._config.max_retries:
                    time.sleep(self._config.retry_delay * (attempt + 1))
                continue

        # 所有重试失败
        elapsed_ms = (time.time() - start_time) * 1000
        self._record_history(method, url, 0, elapsed_ms, str(last_error))
        self._stats["total_requests"] += 1
        self._stats["total_errors"] += 1
        raise HTTPConnectionError(f"请求失败: {url}", cause=last_error)

    def _record_history(
        self, method: str, url: str, status: int, elapsed_ms: float, error: Optional[str]
    ) -> None:
        """记录请求历史"""
        record = {
            "method": method,
            "url": url,
            "status": status,
            "elapsed_ms": round(elapsed_ms, 2),
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }
        self._history.append(record)
        # 限制历史长度
        if len(self._history) > 500:
            self._history = self._history[-500:]
