echo "setting environment variables"
source .env
echo "downloading grafana"
curl -O https://dl.grafana.com/enterprise/release/grafana-enterprise-$GRAFANA_VERSION.darwin-amd64.tar.gz
tar -zxvf grafana-enterprise-$GRAFANA_VERSION.darwin-amd64.tar.gz

echo "Installing grafana plugins"
$GRAFANA_HOME/bin/grafana-cli --pluginsDir $GRAFANA_HOME/data/plugins plugins install yesoreyeram-infinity-datasource
$GRAFANA_HOME/bin/grafana-cli --pluginsDir $GRAFANA_HOME/data/plugins plugins install volkovlabs-form-panel
$GRAFANA_HOME/bin/grafana-cli --pluginsDir $GRAFANA_HOME/data/plugins plugins install marcusolsson-dynamictext-panel

rm -f grafana-enterprise-$GRAFANA_VERSION.darwin-amd64.tar.gz
