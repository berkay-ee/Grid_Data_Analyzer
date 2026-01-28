from datetime import datetime, time
import json
import os

class EbiasService:
    def __init__(self):
        self.login_url = "https://giris.epias.com.tr/cas/login?service=https://seffaflik.epias.com.tr"

    def fetch_market_prices(self, username=None, password=None, date_obj=None):
        """
        Fetches hourly PTF (MCP) prices for the given date using eptr2.
        Requires valid EPİAŞ credentials.
        Returns a dictionary of hourly prices and computed Tariff averages.
        """
        if date_obj is None:
            date_obj = datetime.now()
        
        if not username or not password:
            return False, "Username and Password required for EPİAŞ API."

        try:
            # Note: eptr2 call specifics depend on the library version.
            # Using standard call 'mcp' (Market Clearing Price) aka PTF
            # We fetch for the whole day
            start_date = date_obj.strftime("%Y-%m-%d")
            end_date = date_obj.strftime("%Y-%m-%d")
            
            # Call EPİAŞ
            print(f"Fetching PTF for {start_date}...")
            # 'mcp' is the code for PTF (Piyasa Takas Fiyatı)
            call_params = {
                "start_date": f"{start_date}T00:00:00+03:00",
                "end_date": f"{end_date}T23:59:59+03:00"
            }
            
            # Initialize eptr2 with credentials
            from eptr2 import EPTR2
            eptr = EPTR2(
                use_test_api=False,
                username=username,
                password=password
            ) 
            res = eptr.call("mcp", **call_params)
            
            # Parse result
            items = res.json() if hasattr(res, 'json') else res
            
            # Debugging response structure
            print(f"[DEBUG] eptr2 response type: {type(items)}")
            if isinstance(items, list) and len(items) > 0:
                print(f"[DEBUG] First item sample: {items[0]}")

            if isinstance(items, dict) and 'items' in items:
                items = items['items']
            elif isinstance(items, list):
                # Check if it's a list of errors or strings
                if items and isinstance(items[0], str):
                     return False, f"API Error: {', '.join(items[:5])}"

            hourly_prices = []
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        price = item.get('price')
                        if price is not None:
                            hourly_prices.append(price)
                    else:
                        print(f"[WARN] Skipping non-dict item: {item}")
            
            if not hourly_prices:
                return False, f"No valid price data found. Response: {str(items)[:100]}"

            if len(hourly_prices) == 24:
                # Night: 22, 23, 00, 01, 02, 03, 04, 05 (Indices: 22, 23, 0, 1, 2, 3, 4, 5)
                night_indices = [22, 23, 0, 1, 2, 3, 4, 5]
                day_indices = list(range(6, 17)) # 6 to 16
                peak_indices = list(range(17, 22)) # 17 to 21
                
                avg_night = sum([hourly_prices[i] for i in night_indices]) / len(night_indices)
                avg_day = sum([hourly_prices[i] for i in day_indices]) / len(day_indices)
                avg_peak = sum([hourly_prices[i] for i in peak_indices]) / len(peak_indices)
                
                rates = {
                    "day": round(avg_day, 2),
                    "peak": round(avg_peak, 2),
                    "night": round(avg_night, 2)
                }
                return True, rates
            else:
                return False, f"Expected 24 hours of data, got {len(hourly_prices)}"

        except Exception as e:
            return False, str(e)

    def automate_login(self, email, password):
        """
        Uses Playwright to log in to the EPİAŞ portal.
        """
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                page = browser.new_page()
                page.goto(self.login_url)
                page.fill("input[id*='username']", email)
                page.fill("input[id*='password']", password)
                page.click("button:has-text('Giriş')")
                page.wait_for_load_state('networkidle')
                
                curr_url = page.url
                if "login" not in curr_url and "seffaflik" in curr_url:
                    browser.close()
                    return True, "Login successful! Redirected to Transparency Platform."
                
                if page.is_visible("text=Hatalı") or page.is_visible("text=Invalid"):
                    browser.close()
                    return False, "Invalid credentials."

                browser.close()
                return True, "Login sequence completed."

        except Exception as e:
            return False, f"Automation Error: {e}"


class TariffManager:
    """
    Manages electricity tariff rates and calculates costs based on time of use.
    """
    SETTINGS_FILE = "tariff_settings.json"

    def __init__(self):
        # Default Turkish Electricity Tariffs (Example values in TL/kWh)
        # Note: These are now also stored in self.params, but kept here for backward compat
        self.rates = {
            "day": 1.50,    # 06:00 - 17:00
            "peak": 2.50,   # 17:00 - 22:00
            "night": 0.80   # 22:00 - 06:00
        }
        
        # New Detailed Parameters (from user request)
        self.params = {
            "yekdem_tahmini": 284.87,
            "ilave_katsayi": 0.019, # 1.90%
            "dengesizlik_orani": 0.0,
            "dagitim_bedeli": 0.895372,
            "btv": 0.01,
            "trt": 0.00,
            "enerji_fonu": 0.00,
            "kdv": 0.20,
            "profil_maliye": 3.35269
        }
        
        # Time ranges
        self.time_ranges = {
            "day": (time(6, 0), time(17, 0)),
            "peak": (time(17, 0), time(22, 0)),
            # Night is the remaining time
        }
        
        self.load_settings()

    def update_rates(self, day=None, peak=None, night=None):
        """Updates the tariff rates manually."""
        if day is not None: self.rates["day"] = float(day)
        if peak is not None: self.rates["peak"] = float(peak)
        if night is not None: self.rates["night"] = float(night)
        self.save_settings()

    def update_params(self, **kwargs):
        """Updates the detailed calculation parameters."""
        for key, value in kwargs.items():
            if key in self.params:
                self.params[key] = float(value)
        self.save_settings()

    def get_price(self, dt: datetime) -> float:
        """Returns the price per kWh for a given datetime."""
        t = dt.time()
        
        if self.time_ranges["peak"][0] <= t < self.time_ranges["peak"][1]:
            return self.rates["peak"]
        
        if self.time_ranges["day"][0] <= t < self.time_ranges["day"][1]:
            return self.rates["day"]
        
        return self.rates["night"]

    def fetch_prices_from_web(self, username=None, password=None):
        """
        Fetches live PTF (Market Clearing Price) from EPİAŞ using eptr2.
        Updates the rates based on the fetched daily averages.
        Requires username/password.
        """
        service = EbiasService()
        success, result = service.fetch_market_prices(username=username, password=password)
        
        if success:
            self.update_rates(
                day=result.get("day"),
                peak=result.get("peak"),
                night=result.get("night")
            )
            return True
        else:
            print(f"Failed to fetch prices: {result}")
            return False

    def save_settings(self):
        """Persists current rates and params to a JSON file."""
        data = {
            "rates": self.rates,
            "params": self.params
        }
        try:
            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def load_settings(self):
        """Loads settings from JSON file if it exists."""
        if not os.path.exists(self.SETTINGS_FILE):
            return

        try:
            with open(self.SETTINGS_FILE, 'r') as f:
                data = json.load(f)
                if "rates" in data:
                    self.rates.update(data["rates"])
                if "params" in data:
                    self.params.update(data["params"])
        except Exception as e:
            print(f"Error loading settings: {e}")
