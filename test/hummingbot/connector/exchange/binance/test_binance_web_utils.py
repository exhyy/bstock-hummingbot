import unittest

import hummingbot.connector.exchange.binance.binance_constants as CONSTANTS
from hummingbot.connector.exchange.binance import binance_web_utils as web_utils


class BinanceUtilTestCases(unittest.TestCase):

    def test_public_rest_url(self):
        path_url = "/TEST_PATH"
        domain = "com"
        expected_url = CONSTANTS.REST_URL.format(domain) + CONSTANTS.PUBLIC_API_VERSION + path_url
        self.assertEqual(expected_url, web_utils.public_rest_url(path_url, domain))

    def test_private_rest_url(self):
        path_url = "/TEST_PATH"
        domain = "com"
        expected_url = CONSTANTS.REST_URL.format(domain) + CONSTANTS.PRIVATE_API_VERSION + path_url
        self.assertEqual(expected_url, web_utils.private_rest_url(path_url, domain))

    def test_demo_public_rest_url(self):
        path_url = "/TEST_PATH"
        expected_url = CONSTANTS.DEMO_REST_URL + CONSTANTS.PUBLIC_API_VERSION + path_url
        self.assertEqual(expected_url, web_utils.public_rest_url(path_url, CONSTANTS.DEMO_DOMAIN))

    def test_demo_private_rest_url(self):
        path_url = "/TEST_PATH"
        expected_url = CONSTANTS.DEMO_REST_URL + CONSTANTS.PRIVATE_API_VERSION + path_url
        self.assertEqual(expected_url, web_utils.private_rest_url(path_url, CONSTANTS.DEMO_DOMAIN))

    def test_demo_public_ws_url(self):
        self.assertEqual(CONSTANTS.DEMO_WSS_URL, web_utils.public_ws_url(CONSTANTS.DEMO_DOMAIN))

    def test_demo_private_ws_url(self):
        self.assertEqual(CONSTANTS.DEMO_WSS_API_URL, web_utils.private_ws_url(CONSTANTS.DEMO_DOMAIN))

    def test_production_ws_urls_are_unchanged(self):
        domain = "com"
        self.assertEqual(CONSTANTS.WSS_URL.format(domain), web_utils.public_ws_url(domain))
        self.assertEqual(CONSTANTS.WSS_API_URL.format(domain), web_utils.private_ws_url(domain))
