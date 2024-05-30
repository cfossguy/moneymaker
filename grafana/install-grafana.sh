echo "setting environment variables"
source .env
echo "downloading grafana"
curl -O https://dl.grafana.com/enterprise/release/grafana-enterprise-$GRAFANA_VERSION.darwin-amd64.tar.gz
tar -zxvf grafana-enterprise-$GRAFANA_VERSION.darwin-amd64.tar.gz

echo "uninstalling existing grafana if exists"
rm -rf $GRAFANA_HOME

echo "install grafana"
mkdir -p $GRAFANA_HOME
mv ./grafana-v$GRAFANA_VERSION $GRAFANA_BASEDIR

echo "install grafana plugins"
$GRAFANA_HOME/bin/grafana cli --pluginsDir $GRAFANA_HOME/data/plugins plugins install yesoreyeram-infinity-datasource
$GRAFANA_HOME/bin/grafana cli --pluginsDir $GRAFANA_HOME/data/plugins plugins install volkovlabs-form-panel
$GRAFANA_HOME/bin/grafana cli --pluginsDir $GRAFANA_HOME/data/plugins plugins install marcusolsson-dynamictext-panel
$GRAFANA_HOME/bin/grafana cli --pluginsDir $GRAFANA_HOME/data/plugins plugins install marcusolsson-static-datasource

rm -f grafana-enterprise-$GRAFANA_VERSION.darwin-amd64.tar.gz
