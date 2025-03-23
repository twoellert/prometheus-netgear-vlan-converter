# prometheus-netgear-vlan-converter
Prometheus VLAN Converter Docker Container for Netgear Switches

Custom exporter which grabs the dot1qVlanStaticEgressPorts, which is a Hex and needs to be interpreted Bit-wise to get the VLANs a port is assigned to.
Publishes the result as a new metric to Prometheus.

Since Grafana cannot interpret bit values out of hex values yet.

## Prometheus Config Example
Put this into _prometheus.yml_ after starting the docker container.
```
  - job_name: 'vlan-converter-snmp-main-switch'
    scrape_interval: 15s
    params:
      job: ['snmp-main-switch']
      value: ['dot1qVlanStaticEgressPorts']
    static_configs:
      - targets:
        - switch1.test.com
        - switch2.test.com
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: target
      - target_label: __address__
        replacement: whereTheDockerContainerRuns.test.com:5000
```

Also check the URL which the container should use towards your prometheus in the python code.
```
# Statics
prometheus_url = 'http://prometheus:9090'
```

## Dev Setup
```
apt install python3 python3-pip
pip install -r requirements.txt
python3 ./vlan_converter.py
```

## Docker Setup
```
docker build --tag vlan_converter .
docker run --publish 5000:5000 --rm vlan_converter
```

## Supported Netgear Switches
Tested with the following Netgear Switches. Information needs to first be collected to Prometheus via an snmp exporter.