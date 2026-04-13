import requests
import time


class MotiClient:
    BASE_URL = "https://api.motiphysio.com"

    def __init__(self, program_id: str, security_key: str):
        self.program_id = program_id
        self.security_key = security_key
        self._last_request_time = 0

    def _request(self, endpoint: str, extra_params: dict = None) -> dict:
        """統一請求方法：自動認證 + 錯誤處理 + rate limit + retry"""
        # Rate limit protection
        elapsed = time.time() - self._last_request_time
        if elapsed < 0.15:
            time.sleep(0.15 - elapsed)

        payload = {
            "program_id": self.program_id,
            "security_key": self.security_key,
        }
        if extra_params:
            payload.update(extra_params)

        max_retries = 3
        for attempt in range(max_retries):
            resp = requests.post(f"{self.BASE_URL}{endpoint}", json=payload, timeout=30)
            self._last_request_time = time.time()

            if resp.status_code == 429:
                wait = 2 ** attempt
                time.sleep(wait)
                continue

            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, dict) and "error" in data:
                raise MotiAPIError(data["error"])

            return data

        raise MotiAPIError("Rate limit exceeded after retries")

    # --- 會員 ---

    def get_user_list(self, start_period=None, end_period=None):
        params = {}
        if start_period is not None:
            params["start_period"] = start_period
        if end_period is not None:
            params["end_period"] = end_period
        return self._request("/v1/get_user_list", params)

    def get_user_info(self, user_id: str):
        return self._request("/v1/get_user_info", {"user_id": user_id})

    # --- 分析列表 ---

    def get_static_analysis_list(self, user_id: str):
        return self._request("/v1/get_user_static_analysis_list", {"user_id": user_id})

    def get_ohs_analysis_list(self, user_id: str):
        return self._request("/v1/get_user_ohs_analysis_list", {"user_id": user_id})

    def get_ols_analysis_list(self, user_id: str):
        return self._request("/v1/get_user_ols_analysis_list", {"user_id": user_id})

    # --- 分析報告 ---

    def get_static_report(self, user_id: str, analysis_index: int):
        return self._request("/v1/get_user_static_analysis_report", {
            "user_id": user_id, "analysis_index": analysis_index,
        })

    def get_ohs_report(self, user_id: str, analysis_index: int):
        return self._request("/v1/get_user_ohs_analysis_report", {
            "user_id": user_id, "analysis_index": analysis_index,
        })

    def get_ols_report(self, user_id: str, analysis_index: int):
        return self._request("/v1/get_user_ols_analysis_report", {
            "user_id": user_id, "analysis_index": analysis_index,
        })


class MotiAPIError(Exception):
    pass
