import unittest
import pinecone_analytics
from dotenv import load_dotenv
import os

load_dotenv()
conn_string = os.getenv('db_connect_string')

class TestStringMethods(unittest.TestCase):

    def test_pinecone_universe_xls_import(self):
        pinecone_analytics.stock_universe_pinecone_import()
        self.assertEqual(1, 1)

    def test_pinecone_query(self):
        pinecone_analytics.pinecone_query(prompt="Digital pathology, Agilent",
                                          max_sma_rating=1,
                                          max_macd_rating=3,
                                          max_rsi_rating=40)
        self.assertEqual(1, 1)