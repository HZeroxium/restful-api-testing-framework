import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Dict, Any

class HttpClient:
    def __init__(self, default_headers: Optional[Dict[str, str]] = None, token: Optional[str] = None,
                 total_retries: int = 3, backoff: float = 1.0):
        self.session = requests.Session()
        retry_strategy = Retry(
            total=total_retries,
            backoff_factor=backoff,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.session.headers.update({
            'User-Agent': 'API-Test-Runner/1.0',
            'Accept': 'application/json',
            **(default_headers or {})
        })

        if token:
            self.session.headers.update({'Authorization': f'Bearer {token}'})

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        return self.session.request(method.upper(), url, **kwargs)

    def close(self):
        self.session.close()
