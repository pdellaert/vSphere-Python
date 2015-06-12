"""
multi-clone is a Python script which allows you to clone a virtual machine or virtual machine template into multiple new virtual machines in a VMware vSphere environment. 

This script has the following capabilities:
    * Deploy a specified amount of virtual machines
    * Deploy in a specified folder
    * Deploy in a specified resource pool
    * Specify if the cloned virtual machines need to be powered on
    * Print out information of the main network interface (mac and ip, either IPv4 or IPv6)
    * Run a post-processing script with 3 parameters (virtual machine name, mac and ip)
    * Instead of setting the basename, amount, resource pool and folder a CSV can be used
    * Print logging to a log file or stdout
    * Do this in a threaded way

--- Using threads ---
Deciding on the optimal amount of threads might need a bit of experimentation. Keep certain things in mind:
    * The optimal amount of threads depends on the IOPS of the datastore as each thread will start a template deployment task, which in turn starts copying the disks.
    * vCenter will, by default, only run 8 deployment tasks simultaniously while other tasks are queued, so setting the amount of threads to more than 8, is not really usefull.

--- Using CSV file ---
A CSV file can be provided with a line for each VM that needs to be created, with specific parameters for each VM. The format of each row should be (fields surrounded with <> are mandatory, fields surrounded with [] are optional):
'<Clone name>';'[Resouce Pool]';'[Folder]';'[MAC Address]';'[Post-processing Script]';'[Advanced VM Parameters in JSON format]'
For instance:
'Test01';'Development';'IT';'00:50:56:11:11:11';'run.sh';'{"parameter.1":"value.1","parameter.2":"value.2"}'

--- Post-processing Script ---
The Post-processing script is run for each VM created if it is provided either as a commandline parameter or as a field in the CSV. 
It is run with the following parameters:
    * virtual machine name, mac and ip : If Print IPs or Print MACs is enabled, combined with Power on
    * virtual machine name, mac: If a custom mac address was specified (even if VM is not powered on)
    * virtual machine name: If a power on is disabled and no custom mac address is enabled

--- Usage ---
Run 'multi-clone.py -h' for an overview

--- Documentation ---
https://github.com/pdellaert/vSphere-Python/blob/master/docs/multi-clone.md

--- Author ---
Philippe Dellaert <philippe@dellaert.org>

--- License ---
https://raw.github.com/pdellaert/vSphere-Python/master/LICENSE.md

"""

import argparse
import atexit
import csv
import getpass
import json
import multiprocessing
import logging
import os.path
import re
import requests
import subprocess
import sys

from time import sleep
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl
from multiprocessing.dummy import Pool as ThreadPool

def get_args():
    """
    Supports the command-line arguments listed below.
    """

    parser = argparse.ArgumentParser(description="Deploy a template into multiple VM's. You can get information returned with the name of the virtual machine created and it's main mac and ip address. Either in IPv4 or IPv6 format. You can specify which folder and/or resource pool the clone should be placed in. Verbose and debug output can either be send to stdout, or saved to a log file. A post-script can be specified for post-processing. And it can all be done in a number of parallel threads you specify. The script also provides the ability to use a CSV for a lot of it settings and if you want to specify the mac address of the clones (usefull for DHCP/PXE configuration).")
    parser.add_argument('-6', '--six', required=False, help='Get IPv6 address for VMs instead of IPv4', dest='ipv6', action='store_true')
    parser.add_argument('-b', '--basename', nargs=1, required=False, help='Basename of the newly deployed VMs', dest='basename', type=str)
    parser.add_argument('-c', '--count', nargs=1, required=False, help='Starting count, the name of the first VM deployed will be <basename>-<count>, the second will be <basename>-<count+1> (default = 1)', dest='count', type=int, default=[1])
    parser.add_argument('-C', '--csv', nargs=1, required=False, help='An optional CSV overwritting the basename and count. For each line, a clone will be created. A line consits of the following fields, fields inside <> are mandatory, fields with [] are not: "<Clone name>";"[Resouce Pool]";"[Folder]";"[MAC Address]";"[Post Script]"', dest='csvfile', type=str)
    parser.add_argument('-d', '--debug', required=False, help='Enable debug output', dest='debug', action='store_true')
    parser.add_argument('-f', '--folder', nargs=1, required=False, help='The folder in which the new VMs should reside (default = same folder as source virtual machine)', dest='folder', type=str)
    parser.add_argument('-H', '--host', nargs=1, required=True, help='The vCenter or ESXi host to connect to', dest='host', type=str)
    parser.add_argument('-i', '--print-ips', required=False, help='Enable IP output', dest='ips', action='store_true')
    parser.add_argument('-m', '--print-macs', required=False, help='Enable MAC output', dest='macs', action='store_true')
    parser.add_argument('-l', '--log-file', nargs=1, required=False, help='File to log to (default = stdout)', dest='logfile', type=str)
    parser.add_argument('-n', '--number', nargs=1, required=False, help='Amount of VMs to deploy (default = 1)', dest='amount', type=int, default=[1])
    parser.add_argument('-o', '--port', nargs=1, required=False, help='Server port to connect to (default = 443)', dest='port', type=int, default=[443])
    parser.add_argument('-p', '--password', nargs=1, required=False, help='The password with which to connect to the host. If not specified, the user is prompted at runtime for a password', dest='password', type=str)
    parser.add_argument('-P', '--disable-power-on', required=False, help='Disable power on of cloned VMs', dest='nopoweron', action='store_true')
    parser.add_argument('-r', '--resource-pool', nargs=1, required=False, help='The resource pool in which the new VMs should reside, (default = Resources, the root resource pool)', dest='resource_pool', type=str, default=['Resources'])
    parser.add_argument('-s', '--post-script', nargs=1, required=False, help='Script to be called after each VM is created and booted. Arguments passed: name mac-address ip-address', dest='post_script', type=str)
    parser.add_argument('-S', '--disable-SSL-certificate-verification', required=False, help='Disable SSL certificate verification on connect', dest='nosslcheck', action='store_true')
    parser.add_argument('-t', '--template', nargs=1, required=True, help='Template to deploy', dest='template', type=str)
    parser.add_argument('-T', '--threads', nargs=1, required=False, help='Amount of threads to use. Choose the amount of threads with the speed of your datastore in mind, each thread starts the creation of a virtual machine. (default = 1)', dest='threads', type=int, default=[1])
    parser.add_argument('-u', '--user', nargs=1, required=True, help='The username with which to connect to the host', dest='username', type=str)
    parser.add_argument('-v', '--verbose', required=False, help='Enable verbose output', dest='verbose', action='store_true')
    parser.add_argument('-w', '--wait-max', nargs=1, required=False, help='Maximum amount of seconds to wait when gathering information (default = 120)', dest='maxwait', type=int, default=[120])
    args = parser.parse_args()
    return args

def find_vm(si,logger,name,threaded=False):
    """
    Find a virtual machine by it's name and return it
    """

    content = si.content
    obj_view = content.viewManager.CreateContainerView(content.rootFolder,[vim.VirtualMachine],True)
    vm_list = obj_view.view

    for vm in vm_list:
        if threaded:
            logger.debug('THREAD %s - Checking virtual machine %s' % (name,vm.name))
        else:
            logger.debug('Checking virtual machine %s' % vm.name)
        if vm.name == name:
            if threaded:
                logger.debug('THREAD %s - Found virtual machine %s' % (name,vm.name))
            else:
                logger.debug('Found virtual machine %s' % vm.name)
            return vm
    return None

def find_resource_pool(si,logger,name):
    """
    Find a resource pool by it's name and return it
    """

    content = si.content
    obj_view = content.viewManager.CreateContainerView(content.rootFolder,[vim.ResourcePool],True)
    rp_list = obj_view.view

    for rp in rp_list:
        logger.debug('Checking resource pool %s' % rp.name)
        if rp.name == name:
            logger.debug('Found resource pool %s' % rp.name)
            return rp
    return None

def find_folder(si,logger,name):
    """
    Find a folder by it's name and return it
    """

    content = si.content
    obj_view = content.viewManager.CreateContainerView(content.rootFolder,[vim.Folder],True)
    folder_list = obj_view.view

    for folder in folder_list:
        logger.debug('Checking folder %s' % folder.name)
        if folder.name == name:
            logger.debug('Found folder %s' % folder.name)
            return folder
    return None

def find_mac_ip(logger,vm,maxwait,ipv6=False,threaded=False):
    """
    Find the external mac and IP of a virtual machine and return it
    """

    mac = None
    ip = None
    found = False
    waitcount = 0

    while waitcount < maxwait:
        if threaded:
            logger.debug('THREAD %s - Waited for %s seconds, gathering net information' % (vm.config.name,waitcount))
        else: 
            logger.debug('Waited for %s seconds, gathering net information for virtual machine %s' % (waitcount,vm.config.name))
        net_info = vm.guest.net

        for cur_net in net_info:
            if cur_net.macAddress:
                if threaded:
                    logger.debug('THREAD %s - Mac address %s found' % (vm.config.name,cur_net.macAddress))
                else: 
                    logger.debug('Mac address %s found for virtual machine %s' % (cur_net.macAddress,vm.config.name))
                mac = cur_net.macAddress
            if mac and cur_net.ipConfig:
                if cur_net.ipConfig.ipAddress:
                    for cur_ip in cur_net.ipConfig.ipAddress:
                        if threaded:
                            logger.debug('THREAD %s - Checking ip address %s' % (vm.config.name,cur_ip.ipAddress))
                        else:
                            logger.debug('Checking ip address %s for virtual machine %s' % (cur_ip.ipAddress,vm.config.name))
                        if ipv6 and re.match('\d{1,4}\:.*',cur_ip.ipAddress) and not re.match('fe83\:.*',cur_ip.ipAddress):
                            ip = cur_ip.ipAddress
                        elif not ipv6 and re.match('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',cur_ip.ipAddress) and cur_ip.ipAddress != '127.0.0.1':
                            ip = cur_ip.ipAddress
                        if ip:
                            if threaded:
                                logger.info('THREAD %s - Mac %s and ip %s found' % (vm.config.name,mac,ip))
                            else:
                                logger.info('Mac %s and ip %s found for virtual machine %s' % (mac,ip,vm.config.name))
                            return [mac, ip]

        if threaded:
            logger.debug('THREAD %s - No IP found, waiting 5 seconds and retrying' % vm.config.name)
        else:
            logger.debug('No IP found for virtual machine %s, waiting 5 seconds and retrying' % vm.config.name)
        waitcount += 5
        sleep(5)
    if mac:
        if threaded:
            logger.info('THREAD %s - Found mac address %s, No ip address found' % (vm.config.name,mac))
        else:
            logger.info('Found mac address %s, No ip address found for virtual machine %s' % (mac,vm.config.name))
        return [mac, '']
    if threaded:
        logger.info('THREAD %s - Unable to find mac address or ip address' % vm.config.name)
    else:
        logger.info('Unable to find mac address or ip address for virtual machine %s' % vm.config.name)
    return None

def run_post_script(logger,post_script,vm,mac_ip,custom_mac):
    """
    Runs a post script for a vm
    """
    if mac_ip:
        logger.info('Running post-script command: %s %s %s %s' % (post_script,vm.config.name,mac_ip[0],mac_ip[1]))
        retcode = subprocess.call([post_script,vm.config.name,mac_ip[0],mac_ip[1]])
        logger.debug('Received return code %s for command: %s %s %s %s' % (retcode,post_script,vm.config.name,mac_ip[0],mac_ip[1]))
    elif custom_mac:
        logger.info('Running post-script command: %s %s %s' % (post_script,vm.config.name,custom_mac))
        retcode = subprocess.call([post_script,vm.config.name])
        logger.debug('Received return code %s for command: %s %s' % (retcode,post_script,vm.config.name))
    else:
        logger.info('Running post-script command: %s %s' % (post_script,vm.config.name))
        retcode = subprocess.call([post_script,vm.config.name])
        logger.debug('Received return code %s for command: %s %s' % (retcode,post_script,vm.config.name))
    return retcode

def vm_clone_handler_wrapper(args):
    """
    Wrapping arround vm_clone_handler
    """

    return vm_clone_handler(*args)

def vm_clone_handler(si,logger,vm_name,resource_pool_name,folder_name,custom_mac,ipv6,maxwait,post_script,power_on,print_ips,print_macs,template,template_vm,mac_ip_pool,mac_ip_pool_results,adv_parameters):
    """
    Will handle the thread handling to clone a virtual machine and run post processing
    """

    run_loop = True
    vm = None

    logger.debug('THREAD %s - started' % vm_name)
    logger.info('THREAD %s - Trying to clone %s to new virtual machine' % (vm_name,template))

    # Find the correct Resource Pool
    resource_pool = None
    if resource_pool_name is not None:
        logger.debug('THREAD %s - Finding resource pool %s' % (vm_name,resource_pool_name))
        resource_pool = find_resource_pool(si,logger,resource_pool_name)
        if resource_pool is None:
            logger.critical('THREAD %s - Unable to find resource pool %s' % (vm_name,resource_pool_name))
            return 1
        logger.info('THREAD %s - Resource pool %s found' % (vm_name,resource_pool_name))

    # Find the correct folder
    folder = None
    if folder_name is not None:
        logger.debug('THREAD %s - Finding folder %s' % (vm_name,folder_name))
        folder = find_folder(si,logger,folder_name)
        if folder is None:
            logger.critical('THREAD %s - Unable to find folder %s' % (vm_name,folder_name))
            return 1
        logger.info('THREAD %s - Folder %s found' % (vm_name,folder_name))
    else: 
        logger.info('THREAD %s - Setting folder to template folder as default' % vm_name)
        folder = template_vm.parent

    # Creating necessary specs
    logger.debug('THREAD %s - Creating relocate spec' % vm_name)
    if resource_pool is not None:
        logger.debug('THREAD %s - Resource pool found, using' % vm_name)
        relocate_spec = vim.vm.RelocateSpec(pool=resource_pool)
    else:
        logger.debug('THREAD %s - No resource pool found, continuing without it' % vm_name)
        relocate_spec = vim.vm.RelocateSpec()

    logger.debug('THREAD %s - Creating clone spec' % vm_name)
    clone_spec = vim.vm.CloneSpec(powerOn=False,template=False,location=relocate_spec)

    if find_vm(si,logger,vm_name,True):
        logger.warning('THREAD %s - Virtual machine already exists, not creating' % vm_name)
        run_loop = False
    else:
        logger.debug('THREAD %s - Creating clone task' % vm_name)
        task = template_vm.Clone(name=vm_name,folder=folder,spec=clone_spec)
        logger.info('THREAD %s - Cloning task created' % vm_name)
        logger.info('THREAD %s - Checking task for completion. This might take a while' % vm_name)
    
    while run_loop:
        info = task.info
        logger.debug('THREAD %s - Checking clone task' % vm_name)
        if info.state == vim.TaskInfo.State.success:
            logger.info('THREAD %s - Cloned and running' % vm_name)
            vm = info.result
            run_loop = False
            break
        elif info.state == vim.TaskInfo.State.running:
            logger.debug('THREAD %s - Cloning task is at %s percent' % (vm_name,info.progress))
        elif info.state == vim.TaskInfo.State.queued:
            logger.debug('THREAD %s - Cloning task is queued' % vm_name)
        elif info.state == vim.TaskInfo.State.error:
            if info.error.fault:
                logger.info('THREAD %s - Cloning task has quit with error: %s' % (vm_name,info.error.fault.faultMessage))
            else:
                logger.info('THREAD %s - Cloning task has quit with cancelation' % vm_name)
            run_loop = False
            break
        logger.debug('THREAD %s - Sleeping 10 seconds for new check' % vm_name)
        sleep(10)

    if vm and custom_mac is not None and custom_mac is not '':
        vm_ethernet = None
        config_spec = None
        logger.info('THREAD %s - Trying to set mac to %s' % (vm_name,custom_mac))
        logger.debug('THREAD %s - Searching for ethernet device' % vm_name)
        for vm_device in vm.config.hardware.device:
            if isinstance(vm_device,vim.vm.device.VirtualEthernetCard):
                logger.debug('THREAD %s - Found ethernet device' % vm_name)
                vm_ethernet = vm_device
                break

        if vm_ethernet is not None:
            vm_ethernet.addressType = "Manual"
            vm_ethernet.macAddress = custom_mac
            logger.debug('THREAD %s - Creating of device spec for ethernet card' % vm_name)
            vm_device_spec = vim.vm.device.VirtualDeviceSpec(device=vm_ethernet,operation=vim.vm.device.VirtualDeviceSpec.Operation.edit)
            logger.debug('THREAD %s - Creating of config spec for VM' % vm_name)
            config_spec = vim.vm.ConfigSpec(deviceChange=[vm_device_spec])
            logger.info('THREAD %s - Applying MAC address change. This might take a couple of seconds' % vm_name)
            config_task = vm.ReconfigVM_Task(spec=config_spec)
            logger.debug('THREAD %s - Waiting fo MAC address change to complete' % vm_name)
            run_loop = True
            while run_loop:
                info = task.info
                if info.state == vim.TaskInfo.State.success:
                    run_loop = False
                    break
                elif info.state == vim.TaskInfo.State.error:
                    if info.error.fault:
                        logger.info('THREAD %s - MAC address change has quit with error: %s' % (vm_name,info.error.fault.faultMessage))
                    else:
                        logger.info('THREAD %s - MAC address change has quit with cancelation' % vm_name)
                    run_loop = False
                    break
                sleep(5)

    if vm and adv_parameters is not None and adv_parameters is not '':
        logger.info('THREAD %s - Setting advanced parameters' % vm_name)
        logger.debug('THREAD %s - Loading JSON data: %s' % (vm_name,adv_parameters))
        adv_parameters_dict = json.loads(adv_parameters)

    if vm and power_on:
        logger.info('THREAD %s - Powering on VM. This might take a couple of seconds' % vm_name)
        power_on_task = vm.PowerOn()
        logger.debug('THREAD %s - Waiting fo VM to power on' % vm_name)
        run_loop = True
        while run_loop:
            info = task.info
            if info.state == vim.TaskInfo.State.success:
                run_loop = False
                break
            elif info.state == vim.TaskInfo.State.error:
                if info.error.fault:
                    logger.info('THREAD %s - Power on has quit with error: %s' % (vm_name,info.error.fault.faultMessage))
                else:
                    logger.info('THREAD %s - Power on has quit with cancelation' % vm_name)
                run_loop = False
                break
            sleep(5)

    if vm and power_on and (post_script or print_ips or print_macs):
        logger.debug('THREAD %s - Creating mac, ip and post-script processing thread' % vm_name)
        mac_ip_pool_results.append(mac_ip_pool.apply_async(vm_mac_ip_handler,(logger,vm,ipv6,maxwait,post_script,power_on,print_ips,print_macs,custom_mac)))
    elif vm and (post_script or print_ips or print_macs):
        logger.error('THREAD %s - Power on is disabled, printing of IP and Mac is not possible' % vm_name)

    return vm

def vm_mac_ip_handler(logger,vm,ipv6,maxwait,post_script,power_on,print_ips,print_macs,custom_mac):
    """
    Gather mac, ip and run post-script for a cloned virtual machine
    """

    mac_ip = None
    if print_macs or print_ips:
        logger.info('THREAD %s - Gathering mac and ip' % vm.config.name)
        mac_ip = find_mac_ip(logger,vm,maxwait,ipv6,True)
        if mac_ip and print_macs and print_ips:
            logger.info('THREAD %s - Printing mac and ip information: %s %s %s' % (vm.config.name,vm.config.name,mac_ip[0],mac_ip[1]))
            print '%s %s %s' % (vm.config.name,mac_ip[0],mac_ip[1])
        elif mac_ip and print_macs:
            logger.info('THREAD %s - Printing mac information: %s %s' % (vm.config.name,vm.config.name,mac_ip[0]))
            print '%s %s' % (vm.config.name,mac_ip[0])
        elif mac_ip and print_ips:
            logger.info('THREAD %s - Printing ip information: %s %s' % (vm.config.name,vm.config.name,mac_ip[1]))
            print '%s %s' % (vm.config.name,mac_ip[1])
        elif print_macs or print_ips:
            logger.error('THREAD %s - Unable to find mac or ip information within %s seconds' % (vm.config.name,maxwait))

    if post_script:
        retcode = run_post_script(logger,post_script,vm,mac_ip,custom_mac)
        if retcode > 0:
            logger.warning('THREAD %s - Post processing failed.' % vm.config.name)

def main():
    """
    Clone a VM or template into multiple VMs with logical names with numbers and allow for post-processing
    """

    # Handling arguments
    args = get_args()
    ipv6        = args.ipv6
    amount      = args.amount[0]
    basename    = None
    if args.basename:
        basename    = args.basename[0]
    count       = args.count[0]
    csvfile     = None
    if args.csvfile:
        csvfile = args.csvfile[0]
    debug       = args.debug
    folder_name = None
    if args.folder:
        folder_name = args.folder[0]
    host        = args.host[0]
    print_ips   = args.ips
    print_macs  = args.macs
    log_file= None
    if args.logfile:
        log_file = args.logfile[0]
    port        = args.port[0]
    post_script = None
    if args.post_script: 
        post_script = args.post_script[0]
    password = None
    if args.password:
        password = args.password[0]
    power_on    = not args.nopoweron
    resource_pool_name = None
    if args.resource_pool:
        resource_pool_name = args.resource_pool[0]
    nosslcheck  = args.nosslcheck
    template    = args.template[0]
    threads     = args.threads[0]
    username    = args.username[0]
    verbose     = args.verbose
    maxwait     = args.maxwait[0]

    # Logging settings
    if debug:
        log_level = logging.DEBUG
    elif verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    if log_file:
        logging.basicConfig(filename=log_file,format='%(asctime)s %(levelname)s %(message)s',level=log_level)
    else:
        logging.basicConfig(filename=log_file,format='%(asctime)s %(levelname)s %(message)s',level=log_level)
    logger = logging.getLogger(__name__)

    # Disabling SSL verification if set
    if nosslcheck:
        logger.debug('Disabling SSL certificate verification.')
        requests.packages.urllib3.disable_warnings()

    # Getting user password
    if password is None:
        logger.debug('No command line password received, requesting password from user')
        password = getpass.getpass(prompt='Enter password for vCenter %s for user %s: ' % (host,username))

    try:
        si = None
        try:
            logger.info('Connecting to server %s:%s with username %s' % (host,port,username))
            si = SmartConnect(host=host,user=username,pwd=password,port=int(port))
        except IOError, e:
            pass

        if not si:
            logger.error('Could not connect to host %s with user %s and specified password' % (host,username))
            return 1

        logger.debug('Registering disconnect at exit')
        atexit.register(Disconnect, si)

        # Find the correct VM
        logger.debug('Finding template %s' % template)
        template_vm = find_vm(si,logger,template,False)
        if template_vm is None:
            logger.error('Unable to find template %s' % template)
            return 1
        logger.info('Template %s found' % template)

        # Pool handling
        logger.debug('Setting up pools and threads')
        pool = ThreadPool(threads)
        mac_ip_pool = ThreadPool(threads)
        mac_ip_pool_results = []
        vm_specs = []
        logger.debug('Pools created with %s threads' % threads)

        if csvfile is None:
            # Generate VM names
            logger.debug('No CSV found working with amount and basename')
            logger.debug('Creating thread specifications')
            vm_names = []
            for a in range(1,amount+1):
                vm_names.append('%s-%i' % (basename,count))
                count += 1

            vm_names.sort()
            for vm_name in vm_names:
                vm_specs.append((si,logger,vm_name,resource_pool_name,folder_name,None,ipv6,maxwait,post_script,power_on,print_ips,print_macs,template,template_vm,mac_ip_pool,mac_ip_pool_results,None))
        else:
            # CSV fields:
            # VM Name, Resource Pool, Folder, MAC Address, Post Script
            logger.debug('Parsing csv %s' % csvfile)

            if not os.path.isfile(csvfile):
                logger.critical('CSV file %s does not exist, exiting' % csvfile)
                return 1

            with open(csvfile,'rb') as tasklist:
                taskreader = csv.reader(tasklist,delimiter=';',quotechar="'")
                for row in taskreader:
                    logger.debug('Found CSV row: %s' % ','.join(row))
                    # VM Name
                    if row[0] is None or row[0] is '':
                        logger.warning('No VM name specified, skipping this vm creation')
                        continue
                    else:
                        cur_vm_name = row[0]
                    # Resource Pool
                    if row[1] is None or row[1] is '':
                        cur_resource_pool_name = resource_pool_name
                    else:
                        cur_resource_pool_name = row[1]
                    # Folder
                    if row[2] is None or row[2] is '':
                        cur_folder_name = folder_name
                    else:
                        cur_folder_name = row[2]
                    # MAC
                    if row[3] is None or row[3] is '':
                        custom_mac = None
                    else:
                        custom_mac = row[3]
                    # Post script
                    if row[4] is None or row[4] is '':
                        cur_post_script = post_script
                    else:
                        cur_post_script = row[4]
                    # Advanced parameters
                    if row[5] is None or row[5] is '':
                        cur_adv_parameters = None
                    else:
                        cur_adv_parameters = row[5]

                    # Creating VM
                    vm_specs.append((si,logger,cur_vm_name,cur_resource_pool_name,cur_folder_name,custom_mac,ipv6,maxwait,cur_post_script,power_on,print_ips,print_macs,template,template_vm,mac_ip_pool,mac_ip_pool_results,cur_adv_parameters))


        logger.debug('Running virtual machine clone pool')
        pool.map(vm_clone_handler_wrapper,vm_specs)

        logger.debug('Closing virtual machine clone pool')
        pool.close()
        pool.join()

        logger.debug('Waiting for all mac, ip and post-script processes')
        for running_task in mac_ip_pool_results:
            running_task.wait()

        logger.debug('Closing mac, ip and post-script processes')
        mac_ip_pool.close()
        mac_ip_pool.join()

    except vmodl.MethodFault, e:
        logger.critical('Caught vmodl fault: %s' % e.msg)
        return 1
    except Exception, e:
        logger.critical('Caught exception: %s' % str(e))
        return 1

    logger.info('Finished all tasks')
    return 0

# Start program
if __name__ == "__main__":
    main()
