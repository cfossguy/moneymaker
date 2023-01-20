from flask import Flask, request
from prometheus_flask_exporter import PrometheusMetrics
import logging
from logfmter import Logfmter

formatter = Logfmter(keys=["ts", "level"],mapping={"ts": "asctime", "level": "levelname"})

handler_stream = logging.StreamHandler()
handler_stream.setFormatter(formatter)

logging.getLogger().setLevel(logging.INFO)

app = Flask(__name__)
metrics = PrometheusMetrics(app)


@app.route('/')
def index():
    return 'Web App with Python Flask!'

@app.route("/watchlist/stocks")
def watchlist_stocks():
    return f"watchlist for stocks"

app.run(host='0.0.0.0', port=8080)
