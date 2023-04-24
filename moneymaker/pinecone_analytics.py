import openai
import pinecone
import pandas as pd
import logging
import os

from logfmter import Logfmter
from dotenv import load_dotenv

formatter = Logfmter(keys=["ts", "level"],mapping={"ts": "asctime", "level": "levelname"})
logging.getLogger().setLevel(logging.INFO)

load_dotenv()

conn_string = os.getenv('db_connect_string')
pinecone_api_key = os.getenv('pinecone_api_key')
pinecone_environment = os.getenv('pinecone_env')
openai.api_key = os.getenv('openai_api_key')
model = "text-embedding-ada-002"

pinecone.init(api_key=pinecone_api_key,
            environment=pinecone_environment)
index = pinecone.Index('openai')

use_small_dataset = True

def stock_universe_pinecone_import():
    try:
        # check if 'openai' index already exists (only create index if not)
        if 'openai' not in pinecone.list_indexes():
            pinecone.create_index('openai', dimension=1536)

        tickers_list = pd.read_sql_table("stocks", conn_string, schema=None, index_col=None, coerce_float=True, parse_dates=None,
                              columns=None, chunksize=None).to_dict(orient='records')
        index_id = 0
        for ticker_details in tickers_list:
            embed_text = str()
            for k, v in ticker_details.items():
                embed_text = embed_text + f"{k}={v} AND "
            openai_embedding = openai.Embedding.create(input=embed_text, engine=model)
            logging.debug(f'Embed text for {index_id} is: {embed_text}')
            meta = {"ticker": ticker_details['ticker'],
                    "rsi_rating": ticker_details['rsi_rating'],
                    "sma_rating": ticker_details['sma_rating'],
                    "macd_rating": ticker_details['macd_rating']}
            embedding_result = openai_embedding['data'][0]['embedding']

            index.upsert([
                (str(index_id), embedding_result, meta)
            ])
            logging.info(f"Embedded text loaded into pinecone for {meta['ticker']}")
            logging.info(f"Embedded completion % {index_id / len(tickers_list) * 100}")
            index_id = index_id + 1

    except BaseException as be:
        logging.error(be)
        raise be

def pinecone_query(prompt, max_rsi_rating, max_macd_rating, max_sma_rating):
    xq = openai.Embedding.create(input=prompt, engine=model)['data'][0]['embedding']
    res = index.query([xq], top_k=3, include_metadata=True,
                      filter={"rsi_rating": {"$lte": max_rsi_rating},
                              "macd_rating": {"$lte": max_macd_rating},
                              "sma_rating": {"$lte": max_sma_rating},
                              })
    values = []
    for match in res['matches']:
        value = {
            "score": f"{match['score']:.2f}",
            "ticker": match['metadata']['ticker'],
            "rsi_rating": match['metadata']['rsi_rating'],
            "macd_rating": match['metadata']['macd_rating'],
            "sma_rating": match['metadata']['sma_rating'],
        }
        values.append(value)

    return values
