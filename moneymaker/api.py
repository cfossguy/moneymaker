from flask import request, jsonify, Flask
from sqlalchemy.exc import IntegrityError
import functools
from flask_cors import CORS
from logfmter import Logfmter
from dotenv import load_dotenv
import os
import logging
from prometheus_flask_exporter import PrometheusMetrics
from moneymaker import app, ticker_analytics
from multiprocessing import Process

app = Flask(__name__)
formatter = Logfmter(keys=["ts", "level"],mapping={"ts": "asctime", "level": "levelname"})

handler_stream = logging.StreamHandler()
handler_stream.setFormatter(formatter)

logging.getLogger().setLevel(logging.INFO)
metrics = PrometheusMetrics(app)

load_dotenv()
ticker_api_key = os.getenv('ticker_api_key')
CORS(app)

def token_required(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if api_key == ticker_api_key:
            return func(*args, **kwargs)
        else:
            return {"message": "The provided API key is not valid"}, 403
    return decorator

@app.route('/')
def index():
    logging.info("root url hit")
    return 'Web App with Python Flask!'

@app.route("/universe-import", methods=['POST'])
def universe_import():
    data = {}
    heavy_process = Process(
        target=ticker_analytics.stock_universe_xls_import,
        daemon=True
    )
    heavy_process.start()
    data['result'] = "universe import running in background"
    return jsonify(data), 200

@app.route('/watchlist', methods=['POST'])
#@token_required
def watchlist():
    data = {}
    try:
        query = request.json
        logging.info(f"query is: {query}")
        operation = query['operation']

        if operation == "add":
            ticker = query['ticker']
            kind = query['kind']
            data['result'] = ticker_analytics.add_ticker_to_watchlist(ticker=ticker, kind=kind)
            data['status'] = "OK"
            return jsonify(data), 200
        elif operation == "delete":
            ticker = query['ticker']
            kind = query['kind']
            data['result'] = ticker_analytics.delete_ticker_from_watchlist(ticker=ticker, kind=kind)
            data['status'] = "OK"
            return jsonify(data), 200
        elif operation == "import":
            data['result'] = ticker_analytics.watchlist_xls_import()
            data['status'] = "OK"
            return jsonify(data), 200
        else:
            data['result'] = "no op"
            data['status'] = "OK"
            return jsonify(data), 200
    except IntegrityError as ie:
        data['result'] = f"{ie}"
        data['status'] = "ERROR"
        logging.error(ie)
        return jsonify(data), 400
    except BaseException as be:
        data['result'] = f"{be}"
        data['status'] = "ERROR"
        logging.error(f"error processing query: {query}")
        logging.error(be)
        return jsonify(data), 500

if __name__ == '__main__':
    app.run(host= '0.0.0.0',debug=True, port='5000')