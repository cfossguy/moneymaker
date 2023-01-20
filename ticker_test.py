import unittest
import ticker
from sqlalchemy import create_engine, text
from pandas.testing import assert_frame_equal
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()
conn_string = os.getenv('db_connect_string')

class TestStringMethods(unittest.TestCase):

    def test_stock_universe_import(self):
        ticker.stock_universe_import()
        db = create_engine(conn_string)
        sql = "SELECT * FROM stocks;"

        with db.begin() as conn:
            db_results = pd.read_sql_query(sql,con=conn)
            spy_frame = pd.read_excel('stock_universe.xlsx', sheet_name="SPY")
            qqq_frame = pd.read_excel('stock_universe.xlsx', sheet_name="QQQ")
            dia_frame = pd.read_excel('stock_universe.xlsx', sheet_name="DIA")
            stocks_frame = pd.concat([spy_frame, qqq_frame, dia_frame], axis=0)
            assert_frame_equal(db_results.reset_index(drop=True), stocks_frame.reset_index(drop=True))

    def test_stock_universe_drop(self):
        ticker.stock_universe_drop()
        db = create_engine(conn_string)
        sql = "SELECT * FROM information_schema.tables where table_name='stocks';"
        with db.begin() as conn:
            db_results = conn.execute(text(sql))
            self.assertEqual(db_results.rowcount, 0)
if __name__ == '__main__':
    unittest.main()