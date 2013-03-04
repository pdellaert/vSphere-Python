#!/usr/bin/python
import sys, re, getpass, argparse, subprocess
from time import sleep
from pysphere import MORTypes, VIServer, VITask, VIProperty, VIMor, VIException
from pysphere.vi_virtual_machine import VIVirtualMachine

def print_verbose(message):
	if verbose:
		print message

def find_vm(name):
	try:
		vm = con.get_vm_by_name(name)
		return vm
	except VIException:
		return None

def find_resource_pool(name):
	rps = con.get_resource_pools()
	for mor, path in rps.iteritems():
		print_verbose('Parsing RP '+path)
		if re.match('.*'+name,path):
			return mor
	return None

def run_post_script(name,ip):
	print_verbose('Running post script: '+post_script+' '+name+' '+ip)
	retcode = subprocess.call([post_script,name,ip])
	if retcode < 0:
		print 'ERROR: '+post_script+' '+name+' '+ip+' : Returned a non-zero result'
		sys.exit(1)

def find_ip(vm,ipv6=False):
	net_info = None
	while net_info is None:
		net_info = vm.get_property('net',False)
		print_verbose('Waiting 5 seconds ...')
		sleep(5)
	for ip in net_info[0]['ip_addresses']:
		if ipv6 and re.match('\d{1,4}\:.*',ip) and not re.match('fe83\:.*',ip):
			print_verbose('IPv6 address found: '+ip)
			return ip
		elif not ipv6 and re.match('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',ip) and ip != '127.0.0.1':
			print_verbose('IPv4 address found: '+ip)
			return ip
	print_verbose('No IP address found')
	return None

parser = argparse.ArgumentParser(description="Deploy a template into multiple VM's")
parser.add_argument('-6', '--six', required=False, help='Get IPv6 address for VMs instead of IPv4', dest='ipv6', action='store_true')
parser.add_argument('-b', '--basename', nargs=1, required=True, help='Basename of the newly deployed VMs', dest='basename', type=str)
parser.add_argument('-c', '--count', nargs=1, required=False, help='Starting count, the name of the first VM deployed will be <basename>-<count>, the second will be <basename>-<count+1> (default=1)', dest='count', type=int, default=1)
parser.add_argument('-n', '--number', nargs=1, required=False, help='Amount of VMs to deploy (default=1)', dest='amount', type=int, default=1)
parser.add_argument('-p', '--post-script', nargs=1, required=False, help='Script to be called after each VM is created and booted. Arguments passed: name ip-address', dest='post_script', type=str)
parser.add_argument('-r', '--resource-pool', nargs=1, required=False, help='The resource pool in which the new VMs should reside', dest='resource_pool', type=str)
parser.add_argument('-s', '--server', nargs=1, required=True, help='The vCenter or ESXi server to connect to', dest='server', type=str)
parser.add_argument('-t', '--template', nargs=1, required=True, help='Template to deploy', dest='template', type=str)
parser.add_argument('-u', '--user', nargs=1, required=True, help='The username with which to connect to the server', dest='username', type=str)
parser.add_argument('-v', '--verbose', required=False, help='Enable verbose output', dest='verbose', action='store_true')

args = parser.parse_args()

ipv6		= args.ipv6
amount 		= args.amount[0]
basename 	= args.basename[0]
count 		= args.count[0]
post_script 	= None
if args.post_script: 
	post_script = args.post_script[0]
resource_pool 	= None
if args.resource_pool:
	resource_pool = args.resource_pool[0]
server 		= args.server[0]
template 	= args.template[0]
username 	= args.username[0]
verbose		= args.verbose

# Asking Users password for server
password=getpass.getpass(prompt='Enter password for vCenter %s for user %s: ' % (server,username))

# Connecting to server
print_verbose('Connecting to server %s with username %s' % (server,username))
con = VIServer()
con.connect(server,username,password)
print_verbose('Connected to server'+server)
print_verbose('Server type: '+con.get_server_type())
print_verbose('API version: '+con.get_api_version())

# Verify the template exists
print_verbose('Finding template '+template)
template_vm = find_vm(template)
if template_vm is None:
	print 'ERROR: '+template+' not found'
	sys.exit(1)
print_verbose('Template '+template+' found')

# Verify the target Resource Pool exists
print_verbose('Finding resource pool '+resource_pool)
resource_pool_mor = find_resource_pool(resource_pool)
if resource_pool_mor is None:
	print 'ERROR: '+resource_pool+' not found'
	sys.exit(1)
print_verbose('Resource pool '+resource_pool+' found')

# Dictionary with name->IP elements for post script processing
vms_to_ps = {}
# Looping through amount that needs to be created
for a in range(1,amount+1):
	print_verbose('================================================================================')
	vm_name = basename+'-'+str(count)
	print_verbose('Trying to clone '+template+' to VM '+vm_name)
	if find_vm(vm_name):
		print 'ERROR: '+vm_name+' already exists'
	else:
		clone = template_vm.clone(vm_name, True, None, resource_pool_mor, None, None, False)
		print_verbose('VM '+vm_name+' created')
		
		print_verbose('Booting VM '+vm_name)
		clone.power_on()
		
		if post_script:
			ip = find_ip(clone,ipv6)
			if ip:
				vms_to_ps[vm_name] = ip
	count += 1

# Looping through post scripting if necessary
if post_script:
	for name in sorted(vms_to_ps.iterkeys()):
		run_post_script(name,vms_to_ps[name])

# Disconnecting from server
con.disconnect()
