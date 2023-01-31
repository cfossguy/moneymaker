## Quickstart

Install moneymaker API as a package

```pip install -e .```

Run moneymaker API in gunicorn with self-signed certificate

```
gunicorn --certfile cert.pem --keyfile key.pem moneymaker:app
```