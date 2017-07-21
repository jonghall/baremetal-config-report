##
## Account Bare Metal Configuration Compliance Report
##

from flask import Flask, request, render_template, redirect, url_for, send_file, Blueprint
import SoftLayer,json

global username, apiKey

bp = Blueprint('baremetal-config-report', __name__,
                        template_folder='templates',
                        static_folder='static',
                        url_prefix='/baremetal-config-report')


@bp.route('/', methods=["GET","POST"])
def input():
    global username, apiKey, requestType
    username = request.args.get('username')
    apiKey = request.args.get('apiKey')
    requestType = request.args.get('output')

    if username != None and apiKey != None:
        return redirect(url_for('baremetal-config-report.runReport'))
    else:
        return render_template('input.html')

@bp.route('/runReport', methods=["GET", "POST"])
def runReport():
    global username, apiKey
    # If posted from form get username & apikey
    if request.method == "POST":
        username = request.form['username']
        apiKey = request.form['apiKey']
        return redirect(url_for('baremetal-config-report.runReport'))

    #establish SoftLayer API connection
    client = SoftLayer.Client(username=username, api_key=apiKey)

    # initialize output list
    output=[]

    #
    # GET LIST OF ALL DEDICATED HARDWARE IN ACCOUNT
    #

    hardwarelist = client['Account'].getHardware(mask='datacenterName')

    for hardware in hardwarelist:
        hardwareid = hardware['id']

        #
        # LOOKUP HARDWARE INFORMATION BY HARDWARE ID
        #

        mask_object = "datacenterName,networkVlans,backendRouters,frontendRouters,backendNetworkComponentCount,backendNetworkComponents,frontendNetworkComponentCount,frontendNetworkComponents,uplinkNetworkComponents"
        hardware = client['Hardware'].getObject(mask=mask_object, id=hardwareid)

        # FIND Index for MGMT Interface and get it's ComponentID Number
        mgmtnetworkcomponent=[]
        for backend in hardware['backendNetworkComponents']:
            if backend['name'] == "mgmt":
                mgmtnetworkcomponent=client['Network_Component'].getObject(mask="router, uplinkComponent",id=backend['id'])
                continue

        # OBTAIN INFORMATION ABOUT PRIVATE (BACKEND) INTERFACES
        backendnetworkcomponents=[]
        for backend in hardware['backendNetworkComponents']:
            if backend['name'] == "eth":
                backendnetworkcomponent=client['Network_Component'].getObject(mask="router, uplinkComponent",id=backend['id'])
                # Get trunked vlans
                backendnetworkcomponent['trunkedvlans'] = client['Network_Component'].getNetworkVlanTrunks(mask='networkVlan', id=backendnetworkcomponent['uplinkComponent']['id'])
                backendnetworkcomponents.append(backendnetworkcomponent)

        # FIND INFORMATION ABOUT PUBLIC (FRONTEND) INTERFACES
        frontendnetworkcomponents=[]
        for frontend in hardware['frontendNetworkComponents']:
            if frontend['name'] == "eth":
                frontendnetworkcomponent=client['Network_Component'].getObject(mask="router, uplinkComponent",id=frontend['id'])
                # Get trunked vlans
                frontendnetworkcomponent['trunkedvlans'] = client['Network_Component'].getNetworkVlanTrunks(mask='networkVlan', id=frontendnetworkcomponent['uplinkComponent']['id'])
                frontendnetworkcomponents.append(frontendnetworkcomponent)

        if 'manufacturerSerialNumber' in hardware:
            manufacturerSerialNumber = hardware['manufacturerSerialNumber']
        else:
            manufacturerSerialNumber = ""

        if 'datacenterName' in hardware:
            datacenterName = hardware['datacenterName']
        else:
            datacenterName = ""

        #
        # POPULATE OUTPUT WITH FRONTEND DATA
        #

        data = []
        trunkdata= []
        for frontendnetworkcomponent in frontendnetworkcomponents:
            network={}
            network['interface'] = "%s%s" % (frontendnetworkcomponent['name'], frontendnetworkcomponent['port'])
            if 'macAddress' in frontendnetworkcomponent:
                network['mac'] = frontendnetworkcomponent['macAddress']
            else:
                network['mac'] = ""

            if 'primaryIpAddress' in frontendnetworkcomponent:
                network['primaryIpAddress'] = frontendnetworkcomponent['primaryIpAddress']
            network['speed'] = frontendnetworkcomponent['speed']
            network['status'] = frontendnetworkcomponent['status']
            network['switch'] = frontendnetworkcomponent['uplinkComponent']['hardware']['hostname']
            network['router'] = frontendnetworkcomponent['router']['hostname']
            network['router_mfg'] = frontendnetworkcomponent['router']['hardwareChassis']['manufacturer']
            network['router_ip'] = frontendnetworkcomponent['router']['primaryIpAddress']
            if len(hardware['networkVlans']) > 1:
                network['vlan'] = hardware['networkVlans'][1]['vlanNumber']
                if 'name' in hardware['networkVlans'][1].keys(): network['vlanName'] = hardware['networkVlans'][0]['name']
            data.append(network)
            for trunk in frontendnetworkcomponent['trunkedvlans']:
                trunkedvlan = {}
                trunkedvlan['interface'] = network['interface']
                trunkedvlan['vlanNumber'] = trunk['networkVlan']['vlanNumber']
                if 'name' in trunk['networkVlan'].keys(): trunkedvlan['vlanName'] = trunk['networkVlan']['name']
                trunkdata.append(trunkedvlan)
        frontend_data = data

        #
        # POPULATE OUTPUT WITH BACKEND DATA
        #

        interfacedata = []
        for backendnetworkcomponent in backendnetworkcomponents:
            network={}
            network['interface'] = "%s%s" % (backendnetworkcomponent['name'], backendnetworkcomponent['port'])
            if 'macAddress' in backendnetworkcomponent:
                network['mac'] = backendnetworkcomponent['macAddress']
            else:
                network['mac'] = ""

            if 'primaryIpAddress' in backendnetworkcomponent:
                    network['primaryIpAddress'] = backendnetworkcomponent['primaryIpAddress']
            network['speed'] = backendnetworkcomponent['speed']
            network['status'] = backendnetworkcomponent['status']
            network['vlan'] = hardware['networkVlans'][0]['vlanNumber']
            if 'name' in hardware['networkVlans'][0].keys(): network['vlanName'] = hardware['networkVlans'][0]['name']
            network['switch'] = backendnetworkcomponent['uplinkComponent']['hardware']['hostname']
            network['router'] = backendnetworkcomponent['router']['hostname']
            network['router_mfg'] =backendnetworkcomponent['router']['hardwareChassis']['manufacturer']
            network['router_ip'] = backendnetworkcomponent['router']['primaryIpAddress']
            interfacedata.append(network)
            for trunk in backendnetworkcomponent['trunkedvlans']:
                trunkedvlan = {}
                trunkedvlan['interface'] = network['interface']
                trunkedvlan['vlanNumber'] = trunk['networkVlan']['vlanNumber']
                if 'name' in trunk['networkVlan'].keys(): trunkedvlan['vlanName'] = trunk['networkVlan']['name']
                trunkdata.append(trunkedvlan)


        #
        # POPULATE OUTPUT WITH MGMT DATA
        #
        data = []
        network = {}

        if 'ipmiMacAddress' in mgmtnetworkcomponent:
            network['mac'] = mgmtnetworkcomponent['ipmiMacAddress']
        else:
            network['mac'] = ""

        if 'ipmiIpAddress' in mgmtnetworkcomponent:
            network['primaryIpAddress'] = mgmtnetworkcomponent['ipmiIpAddress']
        else:
            network['primaryIpAddress'] = ""

        if 'speed' in mgmtnetworkcomponent:
            network['speed'] = mgmtnetworkcomponent['speed']
        else:
            network['speed']=""

        if 'status' in mgmtnetworkcomponent:
            network['status'] = mgmtnetworkcomponent['status']
        else:
            network['status'] = ""

        if len(hardware['networkVlans']) > 0:
            network['vlan'] = hardware['networkVlans'][0]['vlanNumber']
            if 'name' in hardware['networkVlans'][0].keys(): network['vlanName'] = hardware['networkVlans'][0]['name']
        else:
            network['vlan'] = ""
            network['vlanName'] = ""

        if 'uplinkComponent' in mgmtnetworkcomponent:
            network['switch'] = mgmtnetworkcomponent['uplinkComponent']['hardware']['hostname']
        else:
            network['switch'] = ""
        if 'router' in mgmtnetworkcomponent:
            network['router'] = mgmtnetworkcomponent['router']['hostname']
            network['router_mfg'] =mgmtnetworkcomponent['router']['hardwareChassis']['manufacturer']
            network['router_ip'] = mgmtnetworkcomponent['router']['primaryIpAddress']
        else:
            network['router'] = ""
            network['router_mfg'] = ""
            network['router_ip'] = ""

        data.append(network)
        mgmt_data=data


        result = client['Hardware'].getComponents(id=hardwareid)
        data = []
        for device in result:
            hwdevice = {}
            hwdevice['devicetype'] = \
            device['hardwareComponentModel']['hardwareGenericComponentModel']['hardwareComponentType']['type']
            hwdevice['manufacturer'] = device['hardwareComponentModel']['manufacturer']
            hwdevice['name'] = device['hardwareComponentModel']['name']
            hwdevice['description'] = device['hardwareComponentModel']['hardwareGenericComponentModel']['description']
            hwdevice['modifydate'] = device['modifyDate']
            if 'serialNumber' in device.keys(): hwdevice['serialnumber'] = device['serialNumber']
            data.append(hwdevice)

        hardware_data=data

        # Add to output list
        output.append(
            {'fullyQualifiedDomainName': hardware['fullyQualifiedDomainName'],
             'datacenterName': datacenterName,
             'manufacturerSerialNumber': manufacturerSerialNumber,
             'frontend_data': frontend_data,
             'backend_data': interfacedata,
             'trunkdata': trunkdata,
             'mgmt_data': mgmt_data,
             'hardware_data': hardware_data
        })

    if requestType == "json":
        return json.dumps(output,indent=2)
    else:
        return render_template('report.html', output=output)

app = Flask(__name__)
app.register_blueprint(bp)
app.secret_key = 'sdfssdf2df23423sdfsdfsdf'

if __name__ == '__main__':
    app.run(host='0.0.0.0')
