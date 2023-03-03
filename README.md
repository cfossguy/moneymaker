## Quickstart

### Step #1 - Set environment variables - Python API
Create a .env file in ```./moneymaker``` with the 
following entries

```
db_connect_string=postgresql://[username]:[password]@[host]:[port]/[dbname]
polygon_api_key=[polygon.io api key]
FLASK_APP=api.py
pinecone_api_key=[pinecone api key - not used yet]
pinecone_env=us-west1-gcp
```

### Step #2 - Startup python flask API

```
cd ./moneymaker
source .env
python ./api.py
```

### Step #3 - Install, Configure and Start Grafana
Create a .env file in ```./grafana``` with the 
following entries
```
POLYGON_API_KEY=[polygon.io api key]
POSTGRES_MONEYMAKER_PASSWORD=[postgres db password]

GRAFANA_BASEDIR=[directory where grafana installations live]
GRAFANA_VERSION=9.4.3
GRAFANA_HOME=$GRAFANA_BASEDIR/grafana-$GRAFANA_VERSION
GF_DATABASE_TYPE=[database type for grafana custom.ini]
GF_DATABASE_HOST=[database host for grafana custom.ini]
GF_DATABASE_NAME=[database name for grafana custom.ini]
GF_DATABASE_USER=[database user for grafana custom.ini]
GF_DATABASE_PASSWORD=[database password for grafana custom.ini]
```
Install grafana, apply custom config then start
```
cd ./grafana
source .env
./install-grafana.sh
./start-grafana.sh
```

#### OPTIONAL - Install moneymaker API as a package

```pip install -e .```

Run moneymaker API in gunicorn with self-signed certificate

```
gunicorn --certfile cert.pem --keyfile key.pem moneymaker:app
```