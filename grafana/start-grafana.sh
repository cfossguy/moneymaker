source .env
echo "Updating grafana configuration"
mkdir -p $GRAFANA_BASEDIR
cp -rf ./custom.ini $GRAFANA_HOME/conf/custom.ini
cp -rp ./provisioning/* $GRAFANA_HOME/conf/provisioning/
cp -f ./custom.ini $GRAFANA_HOME/conf/

$GRAFANA_HOME/bin/grafana-server -homepath $GRAFANA_HOME --config $GRAFANA_HOME/conf/custom.ini