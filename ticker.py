import logging

from logfmter import Logfmter
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
from polygon import RESTClient
from sqlalchemy.exc import IntegrityError

formatter = Logfmter(keys=["ts", "level"],mapping={"ts": "asctime", "level": "levelname"})

handler_stream = logging.StreamHandler()
handler_stream.setFormatter(formatter)

logging.getLogger().setLevel(logging.INFO)

load_dotenv()
conn_string = os.getenv('db_connect_string')
polygon_api_key = os.getenv('polygon_api_key')
client = RESTClient(api_key=polygon_api_key)
use_small_dataset = False

def stock_universe_xls_import():

    if use_small_dataset:
        stocks_frame = pd.read_excel('stock_universe.xlsx', sheet_name="TDA_SCREEN_SMALL")
    else:
        stocks_frame = pd.read_excel('stock_universe.xlsx', sheet_name="TDA_SCREEN")

    stocks_frame['rsi_rating'] = stocks_frame.apply(lambda row: get_rsi_rating(row.ticker.strip()), axis=1)
    logging.info("rsi_rating column added for all tickers")

    stocks_frame['sma_rating'] = stocks_frame.apply(lambda row: get_sma_rating(row.ticker.strip()), axis=1)
    logging.info("sma_rating column added for all tickers")

    stocks_frame['market_cap'] = stocks_frame.apply(lambda row: fix_market_cap(row.market_cap), axis=1)
    stocks_frame['dividend_yield'] = stocks_frame.apply(lambda row: fix_dividend_yield(row.dividend_yield), axis=1)

    stocks_frame['pe'] = stocks_frame.apply(lambda row: get_pe(row.ticker.strip()), axis=1)

    stocks_frame[['rsi_rating', 'sma_rating', 'market_cap', 'dividend_yield', 'pe']].apply(pd.to_numeric)
    db = create_engine(conn_string)

    with db.begin() as conn:
        stocks_frame.to_sql('stocks', con=conn, if_exists='replace', index=False)
    logging.info("stock universe records loaded from excel to DB")

def watchlist_xls_import():
    watchlist_frame = pd.read_excel('stock_universe.xlsx', sheet_name="WATCHLIST")
    db = create_engine(conn_string)

    with db.begin() as conn:
        watchlist_frame.to_sql('watchlist', con=conn, if_exists='replace', index=False)
    with db.begin() as conn:
        db.execute(text("ALTER TABLE watchlist ADD CONSTRAINT constraint_ticker UNIQUE (ticker);"))
    logging.info("watchlist records loaded from excel to DB")

def get_rsi_rating(ticker):
    # get week or day or hour rsi for each stock from poloygon.io
    try:
        rsi_weekly = client.get_rsi(ticker=f'{ticker}', timespan='week', window='14', adjusted='true', series_type='close', order='desc').values[0].value
        rsi_day = client.get_rsi(ticker=f'{ticker}', timespan='day', window='14', adjusted='true', series_type='close', order='desc').values[0].value
        rsi_hour = client.get_rsi(ticker=f'{ticker}', timespan='hour', window='14', adjusted='true', series_type='close', order='desc').values[0].value
        rsi_rating = ((rsi_weekly * 0.6) + (rsi_day * 0.3) + (rsi_hour * .1))
        rsi_rating = round(float(rsi_rating), 1)
        logging.info(f'rsi rating for {ticker} is: {rsi_rating}')
        return rsi_rating
    except IndexError as e:
        logging.error(f'rsi for {ticker} has error - {e}')
        return 0

def get_sma_rating(ticker):
    sma_rating = 0
    try:
        sma10 = float(client.get_sma(ticker=f'{ticker}', window='10', timespan='day', series_type='close').values[0].value)
        sma50 = float(client.get_sma(ticker=f'{ticker}', window='50', timespan='day', series_type='close').values[0].value)
        sma100 = float(client.get_sma(ticker=f'{ticker}', window='100', timespan='day', series_type='close').values[0].value)
        if sma10 > sma50 and sma10 > sma100:
            sma_rating = 5
        elif sma10 > sma50:
            sma_rating = 4
        elif sma10 > sma100:
            sma_rating = 3
        elif sma50 > sma100:
            sma_rating = 2
        else:
            sma_rating = 1
        logging.info(f'SMA rating for {ticker} is: {sma_rating}')
        return sma_rating
    except IndexError as e:
        logging.error(f'SMA rating for {ticker} has error - {e}')
        return sma_rating

def get_pe(ticker):
    pe = 0
    try:
        financials = client.vx.list_stock_financials(ticker=f'{ticker}')
        eps_list = []

        while len(eps_list) < 4:
            n = next(financials)
            end_date = n.end_date
            basic_earnings_per_share = n.financials.income_statement.basic_earnings_per_share.value
            eps_list.append(basic_earnings_per_share)
            logging.info(f'basic_earnings={basic_earnings_per_share}, end_date={end_date}')
        previous_close = client.get_previous_close_agg(ticker=f'{ticker}')[0].close
        yearly_eps = sum(eps_list)
        logging.info(f'yearly_eps={yearly_eps}, previous_close={previous_close}')
        pe = previous_close / yearly_eps
        logging.info(f'PE for {ticker} is: {pe}')

        return pe

    except IndexError as e:
        logging.error(f'PE rating for {ticker} has error - {e}. May not have 4 past quarters of financials in polygon.io')
        return pe
    except BaseException as x:
        logging.error(f'PE rating for {ticker} has error - {x}. May not have 4 past quarters of financials in polygon.io')
        return pe


def fix_market_cap(market_cap):
    #returns market cap in millions
    market_cap = market_cap.replace('$', '')
    market_cap_float = 0.0
    if market_cap.endswith('B'):
        market_cap = market_cap.replace('B', '')
        market_cap_float = float(market_cap) * 1000
    elif market_cap.endswith('T'):
        market_cap = market_cap.replace('T', '')
        market_cap_float = float(market_cap) * 1000000
    elif market_cap.endswith('M'):
        market_cap = market_cap.replace('M', '')
        market_cap_float = float(market_cap)
    return round(market_cap_float, 1)

def fix_dividend_yield(dividend_yield):
    #converts dividend yield into a percentage
    dividend_yield_str = str(dividend_yield)
    if dividend_yield_str.startswith('--'):
        return 0.00
    dividend_yield = float(dividend_yield_str) * 100
    return round(dividend_yield, 4)

def stock_universe_drop():
    db = create_engine(conn_string)
    sql = "DROP TABLE IF EXISTS stocks;"
    with db.begin() as conn:
        conn.execute(text(sql))
    logging.warning("stock universe table dropped from DB")

def add_ticker_to_watchlist(ticker, kind):
    try:
        db = create_engine(conn_string)
        sql = f"INSERT INTO WATCHLIST(ticker,kind) VALUES(\'{ticker}\', \'{kind}\');"
        with db.begin() as conn:
            conn.execute(text(sql))
        logging.info(f"{ticker} of kind {kind} inserted into watchlist")
    except IntegrityError as ie:
        logging.error(f"DB insert error: {ie}")

