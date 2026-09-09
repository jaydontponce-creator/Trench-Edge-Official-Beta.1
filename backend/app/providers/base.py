from __future__ import annotations
import os
import httpx
from typing import Any, Dict, Optional

class ProviderError(RuntimeError):
    pass

class HTTPProvider:
    timeout = 20.0
    def get_json(self, url: str, *, params: Optional[Dict[str, Any]]=None, headers: Optional[Dict[str,str]]=None):
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                r = client.get(url, params=params, headers=headers)
                r.raise_for_status()
                return r.json()
        except Exception as exc:
            raise ProviderError(f"{self.__class__.__name__}: {exc}") from exc
