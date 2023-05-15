import logging

from logfmter import Logfmter
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
from polygon import RESTClient
from sqlalchemy.exc import IntegrityError
from scipy.stats import linregress
from pandarallel import pandarallel
import time

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
    start = time.time()
    if use_small_dataset:
        stocks_frame = pd.read_excel('stock_universe.xlsx', sheet_name="TDA_SCREEN_SMALL")
    else:
        stocks_frame = pd.read_excel('stock_universe.xlsx', sheet_name="TDA_SCREEN")

    pandarallel.initialize(progress_bar=False)

    stocks_frame['rsi_rating'] = stocks_frame.parallel_apply(lambda row: get_rsi_rating(row.ticker.strip()), axis=1)
    logging.info("rsi_rating column added for all tickers")

    stocks_frame['sma_rating'] = stocks_frame.parallel_apply(lambda row: get_sma_rating(row.ticker.strip()), axis=1)
    logging.info("sma_rating column added for all tickers")

    stocks_frame['market_cap'] = stocks_frame.parallel_apply(lambda row: fix_market_cap(row.market_cap), axis=1)
    stocks_frame['dividend_yield'] = stocks_frame.parallel_apply(lambda row: fix_dividend_yield(row.dividend_yield), axis=1)

    stocks_frame['pe'] = stocks_frame.parallel_apply(lambda row: get_pe(row.ticker.strip()), axis=1)

    stocks_frame['macd_rating'] = stocks_frame.parallel_apply(lambda row: get_macd_rating(row.ticker.strip()), axis=1)

    stocks_frame[['rsi_rating', 'sma_rating', 'market_cap', 'dividend_yield', 'pe', 'macd_rating']].parallel_apply(pd.to_numeric)

    stocks_frame['news'] = stocks_frame.parallel_apply(lambda row: get_news(row.ticker.strip()), axis=1)

    db = create_engine(conn_string)

    with db.begin() as conn:
        stocks_frame.to_sql('stocks', con=conn, if_exists='replace', index=False)
    end = time.time()
    logging.info(f'stock universe records loaded from excel to DB in {end - start} seconds')

def watchlist_xls_import():
    watchlist_frame = pd.read_excel('stock_universe.xlsx', sheet_name="WATCHLIST")
    db = create_engine(conn_string)
    result = ""
    with db.begin() as conn:
        watchlist_frame.to_sql('watchlist', con=conn, if_exists='replace', index=False)
    with db.begin() as conn:
        db.execute(text("ALTER TABLE watchlist ADD CONSTRAINT constraint_ticker UNIQUE (ticker);"))
    result = "watchlist records loaded from excel to DB"
    logging.info(f"{result}")
    return result

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

def get_macd_rating(ticker):
    # get +- number of weeks that macd is going up/down poloygon.io
    try:
        macd_day = client.get_macd(ticker=f'{ticker}', timespan='day', short_window='12', long_window='26', signal_window='9', adjusted='true', series_type='close', order='asc').values
        macd_week = client.get_macd(ticker=f'{ticker}', timespan='week', short_window='12', long_window='26',
                                   signal_window='9', adjusted='true', series_type='close', order='asc').values
        macds_s = []
        macds_i = []
        for idx, macd_d in enumerate(macd_day):
            macds_s.append(macd_d.signal)
            macds_i.append(idx)
        macd_slope_d = round(linregress(macds_i, macds_s).slope, 2)
        logging.info(f'macd daily slope for {ticker} is: {macd_slope_d}')

        macds_s = []
        macds_i = []
        for idx, macd_w in enumerate(macd_week):
            macds_s.append(macd_w.signal)
            macds_i.append(idx)
        macd_slope_w = round(linregress(macds_i, macds_s).slope, 2)
        logging.info(f'macd weekly slope for {ticker} is: {macd_slope_w}')

        if macd_slope_d is None or macd_slope_w is None:
            logging.info(f'macd rating {ticker} is: 0')
            return 0
        if macd_slope_d > 0 and macd_slope_w > 0:
            logging.info(f'macd rating {ticker} is: 1')
            return 1
        elif macd_slope_w > 0:
            logging.info(f'macd rating {ticker} is: 2')
            return 2
        elif macd_slope_d > 0:
            logging.info(f'macd rating {ticker} is: 3')
            return 3
        elif macd_slope_d > macd_slope_w:
            logging.info(f'macd rating {ticker} is: 4')
            return 4
        else:
            logging.info(f'macd rating {ticker} is: 5')
            return 5

    except IndexError as e:
        logging.error(f'macd rating for {ticker} has error - {e} ')
        return -1
    except ValueError as ve:
        logging.error(f'macd rating for {ticker} has error - {ve}')
        return -1

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

def get_news(ticker):
    feed_details = str()
    try:
        news = client.list_ticker_news(ticker=f'{ticker}', limit=10)
        newsfeed = []
        while len(newsfeed) < 10:
            n = next(news)
            title = n.title
            description = n.description
            date = n.published_utc
            summary = f"{title}\n\n" \
                      f"{description}\n"
            newsfeed.append(summary)
        feed_details = '\n'.join([str(item) for item in newsfeed])
        logging.info(f'News for {ticker} is: {feed_details}')

        return feed_details

    except IndexError as e:
        logging.error(f'News for {ticker} has error - {e}. May not have data in polygon.io')
        return feed_details
    except BaseException as x:
        logging.error(f'News for {ticker} has error - {x}. Unknown error polygon.io')
        return feed_details


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
        f_ticker = ticker.upper().strip()
        f_kind = kind.upper()
        sql = f"INSERT INTO WATCHLIST(ticker,kind) VALUES(\'{f_ticker}\', \'{f_kind}\');"
        with db.begin() as conn:
            conn.execute(text(sql))
        result = f"{ticker} of kind {kind} inserted into watchlist"
        logging.info(result)
        return result
    except IntegrityError as ie:
        result = f"DB insert error: {ie}"
        logging.error(result)
        raise ie

def delete_ticker_from_watchlist(ticker, kind):
    try:
        db = create_engine(conn_string)
        ticker = ticker.upper()
        kind = kind.upper()
        sql = f"DELETE FROM watchlist WHERE ticker=\'{ticker}\' and kind=\'{kind}\';"
        with db.begin() as conn:
            conn.execute(text(sql))
        result = f"{ticker} of kind {kind} deleted from watchlist"
        logging.info(result)
        return result
    except IntegrityError as ie:
        result = f"DB delete error: {ie}"
        logging.error(result)
        raise ie

