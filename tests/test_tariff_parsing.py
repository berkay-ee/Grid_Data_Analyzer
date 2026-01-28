import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'src'))

from backend.tariff import EbiasService

class TestEbiasService(unittest.TestCase):
    def setUp(self):
        self.service = EbiasService()
        self.username = "user"
        self.password = "pass"

    @patch('eptr2.EPTR2')
    def test_fetch_market_prices_success(self, mock_eptr2):
        # Mock successful response with 24 hours of data
        mock_instance = mock_eptr2.return_value
        
        # Create 24 hours of data
        items = [{'price': 100.0} for _ in range(24)]
        mock_instance.call.return_value = items
        
        success, result = self.service.fetch_market_prices(self.username, self.password)
        
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("day", result)
        self.assertIn("peak", result)
        self.assertIn("night", result)
        # 100 avg for all
        self.assertEqual(result["day"], 100.0)

    @patch('eptr2.EPTR2')
    def test_fetch_market_prices_list_error(self, mock_eptr2):
        # Mock response where API returns a list of error strings
        mock_instance = mock_eptr2.return_value
        mock_instance.call.return_value = ["Invalid credentials", "Error 401"]
        
        success, result = self.service.fetch_market_prices(self.username, self.password)
        
        self.assertFalse(success)
        self.assertIn("API Error: Invalid credentials", result)

    @patch('eptr2.EPTR2')
    def test_fetch_market_prices_empty_list(self, mock_eptr2):
        # Mock empty list response
        mock_instance = mock_eptr2.return_value
        mock_instance.call.return_value = []
        
        success, result = self.service.fetch_market_prices(self.username, self.password)
        
        self.assertFalse(success)
        self.assertIn("No valid price data found", result)

    @patch('eptr2.EPTR2')
    def test_fetch_market_prices_unexpected_structure(self, mock_eptr2):
        # Mock response with unexpected dictionary structure (no 'items' and no list)
        mock_instance = mock_eptr2.return_value
        mock_instance.call.return_value = {"some_other_key": "some_value"}
        
        success, result = self.service.fetch_market_prices(self.username, self.password)
        
        self.assertFalse(success)
        self.assertIn("No valid price data found", result)

    @patch('eptr2.EPTR2')
    def test_fetch_market_prices_dict_with_items(self, mock_eptr2):
        # Mock response as dict with 'items' key (sometimes happens in wrappers)
        mock_instance = mock_eptr2.return_value
        items = [{'price': 50.0} for _ in range(24)]
        mock_instance.call.return_value = {'items': items}
        
        success, result = self.service.fetch_market_prices(self.username, self.password)
        
        self.assertTrue(success)
        self.assertEqual(result["day"], 50.0)

if __name__ == '__main__':
    unittest.main()
