import logging
from logfmter import Logfmter
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

formatter = Logfmter(keys=["ts", "level"],mapping={"ts": "asctime", "level": "levelname"})

handler_stream = logging.StreamHandler()
handler_stream.setFormatter(formatter)

logging.getLogger().setLevel(logging.INFO)

load_dotenv()
conn_string = os.getenv('db_connect_string')

def stock_universe_import():
    spy_frame = pd.read_excel('stock_universe.xlsx', sheet_name="SPY")
    qqq_frame = pd.read_excel('stock_universe.xlsx', sheet_name="QQQ")
    dia_frame = pd.read_excel('stock_universe.xlsx', sheet_name="DIA")
    stocks_frame = pd.concat([spy_frame, qqq_frame, dia_frame], axis=0)

    db = create_engine(conn_string)

    with db.begin() as conn:
        stocks_frame.to_sql('stocks', con=conn, if_exists='replace',
              index=False)
    logging.info("stock universe records loaded from excel to DB")

def stock_universe_drop():
    db = create_engine(conn_string)
    sql = "DROP TABLE IF EXISTS stocks;"
    with db.begin() as conn:
        conn.execute(text(sql))
    logging.warning("stock universe table dropped from DB")
