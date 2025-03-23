from http.server import BaseHTTPRequestHandler, HTTPServer
from prometheus_client import start_http_server, Gauge
import urllib.parse
import requests
import copy

# Statics
prometheus_url = 'http://prometheus:9090'

#
# FETCH VALUE FROM PROMETHEUS
#
def fetch_from_prometheus(target, job, value):

    # Query Prometheus API to get the results
    query_url = f'{prometheus_url}/api/v1/query'
    query_params = value + "{instance=\"" + target + "\",job=\"" + job + "\"}"
    params = {'query': query_params}
    response = requests.get(query_url, params=params)

    if response.status_code == 200:
        data = response.json()
        return data.get('data', {})
    return None

#
# CONVERTER FOR handle_dot1qVlanStaticEgressPorts
# Converts the Hex Value given for dot1qVlanStaticEgressPorts into a comma-separated list of ports
#
def handle_dot1qVlanStaticEgressPorts(promData):
    convData = copy.deepcopy(promData)
    for metric in convData['result']:
            metricData = metric['metric']

            for parameterKey in metricData:
                if parameterKey == "dot1qVlanStaticEgressPorts":
                    parameterValue = metricData[parameterKey]
                    convValue = ""
                    binaryData = bin(int(parameterValue, 16))
                    reverseBinaryData = binaryData[-1:1:-1]
                    reverseBinaryData = reverseBinaryData + (1024 - len(reverseBinaryData))*'0'
                
                    # Check for which ports this VLAN is enabled (0-9, translating into Port 1-10)
                    for portIndex in range(10):
                        if int(reverseBinaryData, 2) & (1<<portIndex):

                            if len(convValue) > 0:
                                convValue += ","
                            convValue += str(portIndex+1)

                    if len(convValue) == 0:
                        convValue = "None"

                    parameterValue = convValue
                    metricData[parameterKey] = parameterValue


    return "# HELP dot1qVlanStaticEgressPorts The set of ports that are permanently assigned to the egress list for this VLAN by management - 1.3.6.1.2.1.17.7.1.4.3.1.2", "# TYPE dot1qVlanStaticEgressPorts gauge", convData

#
# HANDLER FOR INCOMING SCRAPE CALLS FROM PROMETHEUS
#
class PrometheusHandler(BaseHTTPRequestHandler):
    # Disable logging of incoming requests
    def log_request(code='-', size='-'):
        return
    
    def do_GET(self):
        # Parse the query parameters
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)

        # Retrieve 'target' parameter
        target = query_params.get('target', [None])[0]
        if not target:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(bytes("Error: 'target' parameter is missing", 'utf-8'))
            return

        # Retrieve 'job' parameter
        job = query_params.get('job', [None])[0]
        if not job:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(bytes("Error: 'job' parameter is missing", 'utf-8'))
            return

        # Retrieve 'value' parameter
        value = query_params.get('value', [None])[0]
        if not value:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(bytes("Error: 'value' parameter is missing", 'utf-8'))
            return

        # Fetch specified value from Prometheus
        promData = fetch_from_prometheus(target, job, value)
        if promData is None:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(bytes(f"Error: Unable to fetch value from prometheusor target", 'utf-8'))
            return

        # Convert the data based on the value name
        convHelp = "# HELP Unknown"
        convType = "# TYPE Unknown"
        convData = None

        if value == "dot1qVlanStaticEgressPorts":
            convHelp, convType, convData = handle_dot1qVlanStaticEgressPorts(promData)
        else:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(bytes(f"Error: Unable to convert data for given value name", 'utf-8'))
            return

        # Check if we succeeded in the conversion
        if convData is None:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(bytes(f"Error: Unable to convert data from prometheusor target", 'utf-8'))
            return

        # Go through convData and create one value per element, presenting it to prometheus on export
        convMetrics = convData['result']
        
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(bytes(convHelp, 'utf-8'))
        self.wfile.write(bytes("\n", 'utf-8'))
        self.wfile.write(bytes(convType, 'utf-8'))
        self.wfile.write(bytes("\n", 'utf-8'))

        for metric in convMetrics:
            metricData = metric['metric']
            metricValue = metric['value']

            outputValues = ""
            for parameterKey in metricData:
                parameterValue = metricData[parameterKey]
                if parameterKey == "__name__" or parameterKey == "instance" or parameterKey == "job":
                    continue

                if len(outputValues) > 0:
                    outputValues += ","
                tmpOutput = parameterKey + "=\"" + parameterValue + "\""
                outputValues += tmpOutput
            
            outputData = value + "{" + outputValues + "} " + metricValue[1] + "\n"
            self.wfile.write(bytes(outputData, 'utf-8'))

#
# MAIN FUNCTION
#
if __name__ == "__main__":
    # Start the Prometheus exporter server
    server_address = ('', 5000)
    httpd = HTTPServer(server_address, PrometheusHandler)
    httpd.serve_forever()
