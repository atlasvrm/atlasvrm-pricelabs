import requests


class Pricelabs:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.pricelabs.co/v1/"
        self.headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}

    def _send_request(self, method: str, endpoint: str, data=None):
        url = f"{self.base_url}{endpoint}"
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                return None

            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {}

    def get_all_listings(self):
        return self._send_request("GET", "listings")

    def get_listing(self, listing_id: str):
        return self._send_request("GET", f"listings/{listing_id}")

    def update_listings(self, data: dict):
        return self._send_request("POST", "listings", data)

    def get_overrides(self, listing_id: str, pms: str):
        return self._send_request("GET", f"listings/{listing_id}/overrides?pms={pms}")

    def update_overrides(self, listing_id: str, data: dict):
        return self._send_request("POST", f"listings/{listing_id}/overrides", data)

    def delete_overrides(self, listing_id: str):
        return self._send_request("DELETE", f"listings/{listing_id}/overrides")

    def get_prices(self, listings: list):
        return self._send_request("POST", "listing_prices", listings)

    def get_neighborhood(self, listing_id: str, pms: str):
        return self._send_request(
            "GET", f"neighborhood_data?pms={pms}&listing_id={listing_id}"
        )
