import openai
import pinecone
import pandas as pd
import logging
import os
import string

from logfmter import Logfmter
from dotenv import load_dotenv

import nltk
import ssl
from langchain.text_splitter import NLTKTextSplitter

#try:
#    _create_unverified_https_context = ssl._create_unverified_context
#except AttributeError:
#    pass
#else:
#    ssl._create_default_https_context = _create_unverified_https_context

#nltk.download()

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
index = pinecone.Index('moneymaker')

use_small_dataset = True

def stock_universe_pinecone_import():
    try:
        # check if 'moneymaker' index already exists (only create index if not)
        if 'moneymaker' not in pinecone.list_indexes():
            pinecone.create_index('moneymaker', dimension=1536, metric='dotproduct')

        tickers_list = pd.read_sql_table("stocks", conn_string, schema=None, index_col=None, coerce_float=True, parse_dates=None,
                              columns=None, chunksize=None).to_dict(orient='records')
        index_id = 0
        for ticker_details in tickers_list:
            embed_tags = str()
            for k, v in ticker_details.items():
                if k == "ticker" or k == "name" or k == "industry" or k == "sector" or k == "industry":
                    embed_tags = embed_tags + f"#{k}:{v.lower()} "
                if k == "beta":
                    beta_rating = "med"
                    try:
                        if float(v) <= 1.0:
                            beta_rating = "low"
                        elif float(v) >= 1.5:
                            beta_rating = "high"
                        embed_tags = embed_tags + f"#{k}:{beta_rating} "
                    except ValueError:
                        logging.error(f"no beta rating for {ticker_details['ticker']}")
                if k == "pe":
                    pe_rating = "med"
                    try:
                        if int(v) <= 10:
                            pe_rating = "low"
                        elif int(v) >= 30:
                            pe_rating = "high"
                        embed_tags = embed_tags + f"#{k}:{pe_rating} "
                    except ValueError:
                        logging.error(f"no PE rating for {ticker_details['ticker']}")
                if k == "news":
                    text_splitter = NLTKTextSplitter()
                    news_chunks = text_splitter.split_text(v)
                    news_chunks.append(embed_tags)
                    #news_details = v.lower().translate(str.maketrans('', '', string.punctuation))
            openai_embedding = openai.Embedding.create(input=news_chunks, engine=model)
            logging.debug(f'Embed text for {index_id} is: {news_chunks}')
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
