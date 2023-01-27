import unittest
import ticker
from sqlalchemy import create_engine, text
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()
conn_string = os.getenv('db_connect_string')

class TestStringMethods(unittest.TestCase):

    def test_stock_universe_xls_import(self):
        ticker.stock_universe_xls_import()
        db = create_engine(conn_string)
        sql = "SELECT * FROM stocks;"

        with db.begin() as conn:
            db_results = pd.read_sql_query(sql,con=conn)
            spy_frame = pd.read_excel('stock_universe.xlsx', sheet_name="SPY")
            qqq_frame = pd.read_excel('stock_universe.xlsx', sheet_name="QQQ")
            dia_frame = pd.read_excel('stock_universe.xlsx', sheet_name="DIA")
            stocks_frame = pd.concat([spy_frame, qqq_frame, dia_frame], axis=0)
            #assert_frame_equal(db_results.reset_index(drop=True), stocks_frame.reset_index(drop=True))

    def test_stock_universe_drop(self):
        ticker.stock_universe_drop()
        db = create_engine(conn_string)
        sql = "SELECT * FROM information_schema.tables where table_name='stocks';"
        with db.begin() as conn:
            db_results = conn.execute(text(sql))
            self.assertEqual(db_results.rowcount, 0)

    def test_get_rsi_rating(self):
        rsi_rating = ticker.get_rsi_rating('AAPL')
        self.assertGreater(rsi_rating, 10)

    def test_get_sma_rating(self):
        sma_rating = ticker.get_sma_rating('AAPL')
        self.assertGreater(sma_rating, 0)

    def test_fix_market_cap(self):
        fixed_market_cap = ticker.fix_market_cap("$50.0B")
        self.assertEqual(50000.0, fixed_market_cap)
        fixed_market_cap = ticker.fix_market_cap("$50.0T")
        self.assertEqual(50000000.0, fixed_market_cap)
        fixed_market_cap = ticker.fix_market_cap("$50.0M")
        self.assertEqual(50.0, fixed_market_cap)

    def test_fix_dividend_yield(self):
        fixed_dividend_yield = ticker.fix_dividend_yield(0.0057)
        self.assertEqual(0.57, fixed_dividend_yield)
        fixed_dividend_yield = ticker.fix_dividend_yield("--")
        self.assertEqual(0.00, fixed_dividend_yield)

    def test_get_pe(self):
        pe = ticker.get_pe("IBM")
        self.assertGreater(pe, 0)

    def test_watchlist_xls_import(self):
        ticker.watchlist_xls_import()
        db = create_engine(conn_string)
        sql = "SELECT count(*) FROM WATCHLIST;"
        with db.begin() as conn:
            result = conn.execute(text(sql))
            rows = 0
            for row in result:
                rows = row["count"]
            self.assertEqual(rows, 19)

    def test_add_ticker_to_watchlist(self):
        ticker.add_ticker_to_watchlist("GS", "stock")
        ticker.add_ticker_to_watchlist("SQQQ", "etf")

if __name__ == '__main__':
    unittest.main()