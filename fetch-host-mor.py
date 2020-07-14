"""
fetch-host-mor is a Python script which will provide the MOR details of one or all ESXi hosts in a vCenter environment. 

--- Usage ---
Run 'fetch-host-mor.py -h' for an overview

--- Author ---
Philippe Dellaert <philippe@dellaert.org>

--- License ---
https://raw.github.com/pdellaert/vSphere-Python/master/LICENSE.md

"""

from builtins import str
import argparse
import atexit
import json
import getpass
import logging

from prettytable import PrettyTable
from pyVim.connect import SmartConnect, SmartConnectNoSSL, Disconnect
from pyVmomi import vim, vmodl


def get_args():
    """
    Supports the command-line arguments listed below.
    """

    parser = argparse.ArgumentParser(description="Randomly vMotion each VM from a list one by one to a random host from a list, until stopped.")
    parser.add_argument('-d', '--debug', required=False, help='Enable debug output', dest='debug', action='store_true')
    parser.add_argument('-H', '--host', nargs=1, required=False, help='The host for which to return the MOR details, if not provided, provides MOR details for all ESXi hosts', dest='host', type=str)
    parser.add_argument('-j', '--json', required=False, help='Print as JSON, not as a table', dest='json_output', action='store_true')
    parser.add_argument('-l', '--log-file', nargs=1, required=False, help='File to log to (default = stdout)', dest='logfile', type=str)
    parser.add_argument('-o', '--port', nargs=1, required=False, help='Server port to connect to (default = 443)', dest='port', type=int, default=[443])
    parser.add_argument('-p', '--password', nargs=1, required=False, help='The password with which to connect to the host. If not specified, the user is prompted at runtime for a password', dest='password', type=str)
    parser.add_argument('-S', '--disable-SSL-certificate-verification', required=False, help='Disable SSL certificate verification on connect', dest='nosslcheck', action='store_true')
    parser.add_argument('-u', '--user', nargs=1, required=True, help='The username with which to connect to the host', dest='username', type=str)
    parser.add_argument('-v', '--verbose', required=False, help='Enable verbose output', dest='verbose', action='store_true')
    parser.add_argument('-V', '--vcenter', nargs=1, required=True, help='The vCenter or ESXi host to connect to', dest='vcenter', type=str)
    args = parser.parse_args()
    return args


def main():
    """
    Find one or all ESXi hosts and print the MOR information
    """

    # Handling arguments
    args = get_args()
    debug = args.debug
    host = None
    if args.host:
        host = args.host[0]
    json_output = args.json_output
    log_file = None
    if args.logfile:
        log_file = args.logfile[0]
    port = args.port[0]
    password = None
    if args.password:
        password = args.password[0]
    nosslcheck = args.nosslcheck
    username = args.username[0]
    verbose = args.verbose
    vcenter = args.vcenter[0]

    # Logging settings
    if debug:
        log_level = logging.DEBUG
    elif verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    if log_file:
        logging.basicConfig(filename=log_file, format='%(asctime)s %(levelname)s %(message)s', level=log_level)
    else:
        logging.basicConfig(filename=log_file, format='%(asctime)s %(levelname)s %(message)s', level=log_level)
    logger = logging.getLogger(__name__)

    if json_output:
        logger.debug('Setting up json output')
        json_object = []
    else:
        logger.debug('Setting up basic output table')
        pt = PrettyTable(['Name', 'MOR value', 'HW UUID'])

    # Getting user password
    if password is None:
        logger.debug('No command line password received, requesting password from user')
        password = getpass.getpass(prompt='Enter password for vCenter %s for user %s: ' % (host, username))

    try:
        si = None
        try:
            logger.info('Connecting to server %s:%s with username %s' % (vcenter, port, username))
            if nosslcheck:
                si = SmartConnectNoSSL(host=vcenter, user=username, pwd=password, port=int(port))
            else:
                si = SmartConnect(host=vcenter, user=username, pwd=password, port=int(port))
        except IOError as e:
            pass

        if not si:
            logger.error('Could not connect to host %s with user %s and specified password' % (vcenter, username))
            return 1

        logger.debug('Registering disconnect at exit')
        atexit.register(Disconnect, si)

        # Getting hosts
        content = si.content
        obj_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
        esxi_host_list = obj_view.view
        esxi_hosts = []
        found_host = False
        for esxi_host in esxi_host_list:
            logger.debug('Found Host %s' % esxi_host.name)
            if host == None:
                esxi_hosts.append(esxi_host)
            elif esxi_host.name == host:
                esxi_hosts.append(esxi_host)
                found_host = True
                break

        if host != None and not found_host:
            logger.error('Host %s does not exist' % host)

        for esxi_host in esxi_hosts:
            esxi_host_name = esxi_host.name
            esxi_host_mor = str(esxi_host).split(':')[1].replace("'", '')
            esxi_host_hw_uuid = esxi_host.summary.hardware.uuid
            logger.debug('name: %s, mor: %s, hw uuid: %s' % (esxi_host_name, esxi_host_mor, esxi_host_hw_uuid))
            if json_output:
                json_dict = {
                        'Name': esxi_host_name,
                        'MOR value': esxi_host_mor,
                        'HW UUID': esxi_host_hw_uuid
                    }
                json_object.append(json_dict)
            else: 
                pt.add_row([esxi_host_name, esxi_host_mor, esxi_host_hw_uuid])

        if json_output:
            print(json.dumps(json_object, sort_keys=True, indent=4))
        else:
            print(pt)

    except KeyboardInterrupt:
        logger.info('Received interrupt, finishing running threads and not creating any new migrations')
        if pool is not None and pool_results is not None:
            wait_for_pool_end(logger, pool, pool_results)

    except vmodl.MethodFault as e:
        logger.critical('Caught vmodl fault: %s' % e.msg)
        return 1
    #except Exception as e:
    #    logger.critical('Caught exception: %s' % str(e))
    #    return 1

    logger.info('Finished all tasks')
    return 0

# Start program
if __name__ == "__main__":
    main()
