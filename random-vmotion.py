"""
random-vmotion is a Python script which takes a list of VMs and a list of Hosts and will vMotion VMs randomly between those hosts per a provided interval. It will continue to do so until you stop it.

This script has the following capabilities:
    * vMotion VMs to a random host
    * Continue until stopped
    * Print logging to a log file or stdout
    * Do this threaded

--- Usage ---
Run 'random-vmotion.py -h' for an overview

--- Using threads ---
Deciding on the optimal amount of threads might need a bit of experimentation. Keep certain things in mind:
    * The optimal amount of threads depends on the memory consumption of the VMs, the activity of the VMs and the amount of hosts as each thread will execute a vMotion task. If this is all to the same host with the a lot of activity in the VM, you might get in trouble.

--- Files ---
The files are a list of VMs and Hosts, each in a seperate file and with one entry per line

--- Documentation ---
https://github.com/pdellaert/vSphere-Python/blob/master/docs/random-vmotion.md

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
import random
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

    parser = argparse.ArgumentParser(description="Randomly vMotion each VM from a list one by one to a random host from a list, until stopped.")
    parser.add_argument('-1', '--one-run', required=False, help='Stop after vMotioning each VM once', dest='onerun', action='store_true')
    parser.add_argument('-d', '--debug', required=False, help='Enable debug output', dest='debug', action='store_true')
    parser.add_argument('-H', '--host', nargs=1, required=True, help='The vCenter or ESXi host to connect to', dest='host', type=str)
    parser.add_argument('-i', '--interval', nargs=1, required=False, help='The amount of time to wait after a vMotion is finished to schedule a new one (default 30 seconds)', dest='interval', type=int, default=[30])
    parser.add_argument('-l', '--log-file', nargs=1, required=False, help='File to log to (default = stdout)', dest='logfile', type=str)
    parser.add_argument('-o', '--port', nargs=1, required=False, help='Server port to connect to (default = 443)', dest='port', type=int, default=[443])
    parser.add_argument('-p', '--password', nargs=1, required=False, help='The password with which to connect to the host. If not specified, the user is prompted at runtime for a password', dest='password', type=str)
    parser.add_argument('-S', '--disable-SSL-certificate-verification', required=False, help='Disable SSL certificate verification on connect', dest='nosslcheck', action='store_true')
    parser.add_argument('-t', '--targets', nargs=1, required=True, help='File with the list of target hosts to vMotion to', dest='targetfile', type=str)
    parser.add_argument('-T', '--threads', nargs=1, required=False, help='Amount of simultanious vMotions to execute at once. (default = 1)', dest='threads', type=int, default=[1])
    parser.add_argument('-u', '--user', nargs=1, required=True, help='The username with which to connect to the host', dest='username', type=str)
    parser.add_argument('-v', '--verbose', required=False, help='Enable verbose output', dest='verbose', action='store_true')
    parser.add_argument('-V', '--vms', nargs=1, required=True, help='File with the list of VMs to vMotion', dest='vmfile', type=str)
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

def find_host(si,logger,name,threaded=False):
    """
    Find a host by it's name and return it
    """

    content = si.content
    obj_view = content.viewManager.CreateContainerView(content.rootFolder,[vim.HostSystem],True)
    host_list = obj_view.view

    for host in host_list:
        if threaded:
            logger.debug('THREAD %s - Checking host %s' % (name,host.name))
        else:
            logger.debug('Checking host %s' % host.name)
        if host.name == name:
            if threaded:
                logger.debug('THREAD %s - Found host %s' % (name,host.name))
            else:
                logger.debug('Found host %s' % host.name)
            return host
    return None

def vm_vmotion_handler(si,logger,vm,host,interval):
    """
    Will handle the thread handling to vMotion a virtual machine
    """

    logger.debug('THREAD %s - started' % vm.name)

    # Getting resource pool
    resource_pool = vm.resourcePool

    # Checking powerstate
    if vm.runtime.powerState != 'poweredOn':
        logger.warning('THREAD %s - VM is not powered on, vMotion is only available for powered on VMs.' % vm.name)
        return 0

    # Setting migration priority
    migrate_priority = vim.VirtualMachine.MovePriority.defaultPriority

    # Starting migration
    logger.debug('THREAD %s - Starting migration to host %s' % (vm.name,host.name))
    migrate_task = vm.Migrate(pool=resource_pool, host=host, priority=migrate_priority)

    run_loop = True
    while run_loop:
        info = migrate_task.info
        logger.debug('THREAD %s - Checking vMotion task' % vm.name)
        if info.state == vim.TaskInfo.State.success:
            logger.debug('THREAD %s - vMotion finished' % vm.name)
            run_loop = False
            break
        elif info.state == vim.TaskInfo.State.running:
            logger.debug('THREAD %s - vMotion task is at %s percent' % (vm.name,info.progress))
        elif info.state == vim.TaskInfo.State.queued:
            logger.debug('THREAD %s - vMotion task is queued' % vm.name)
        elif info.state == vim.TaskInfo.State.error:
            if info.error.fault:
                logger.info('THREAD %s - vMotion task has quit with error: %s' % (vm.name,info.error.fault.faultMessage))
            else:
                logger.info('THREAD %s - vMotion task has quit with cancelation' % vm.name)
            run_loop = False
            break
        logger.debug('THREAD %s - Sleeping 1 second for new check' % vm.name)
        sleep(1)

    logger.debug('THREAD %s - Waiting %s seconds (interval) before ending the thread and releasing it for a new task' % (vm.name,interval))
    sleep(interval)

def wait_for_pool_end(logger,pool,pool_results):
    """
    Waits for all running tasks to end.
    """

    logger.debug('Waiting for %s vMotions to finish' % len(pool_results))
    for result in pool_results:
        result.wait()
    pool.close()
    pool.join()

def main():
    """
    Clone a VM or template into multiple VMs with logical names with numbers and allow for post-processing
    """

    # Handling arguments
    args = get_args()
    onerun      = args.onerun
    debug       = args.debug
    host        = args.host[0]
    interval    = args.interval[0]
    log_file= None
    if args.logfile:
        log_file = args.logfile[0]
    port        = args.port[0]
    password = None
    if args.password:
        password = args.password[0]
    nosslcheck  = args.nosslcheck
    targetfile  = args.targetfile[0]
    threads     = args.threads[0]
    username    = args.username[0]
    verbose     = args.verbose
    vmfile      = args.vmfile[0]

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
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context

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

        # Handling vms file
        logger.debug('Parsing VMs %s' % vmfile)

        if not os.path.isfile(vmfile):
            logger.critical('VM file %s does not exist, exiting' % vmfile)
            return 1

        # Getting VMs
        vms = []
        with open(vmfile,'rb') as tasklist:
            taskreader = csv.reader(tasklist,delimiter=';',quotechar="'")
            for row in taskreader:
                logger.debug('Found CSV row: %s' % ','.join(row))
                # VM Name
                if row[0] is None or row[0] is '':
                    logger.warning('No VM name specified, skipping this vm')
                    continue
                else:
                    cur_vm_name = row[0]

                # Finding VM
                cur_vm = find_vm(si,logger,cur_vm_name)

                # Adding VM to list
                if cur_vm is not None:
                    vms.append(cur_vm)
                else:
                    logger.warning('VM %s does not exist, skipping this vm' % cur_vm_name)

        # Getting hosts
        hosts = []
        with open(targetfile,'rb') as tasklist:
            taskreader = csv.reader(tasklist,delimiter=';',quotechar="'")
            for row in taskreader:
                logger.debug('Found CSV row: %s' % ','.join(row))
                # Host Name
                if row[0] is None or row[0] is '':
                    logger.warning('No host name specified, skipping this host')
                    continue
                else:
                    cur_host_name = row[0]

                # Finding Host
                cur_host = find_host(si,logger,cur_host_name)

                # Adding Host to list
                if cur_host is not None:
                    hosts.append(cur_host)
                else:
                    logger.warning('Host %s does not exist, skipping this host' % cur_host_name)

        if len(vms) < threads:
            logger.warning('Amount of threads %s can not be higher than amount of vms: Setting amount of threads to %s' % (threads,len(vms)))
            threads = len(vms)
        
        # Pool handling
        logger.debug('Setting up pools and threads')
        pool = ThreadPool(threads)
        pool_results = []
        logger.debug('Pools created with %s threads' % threads)

        vm_index = 0
        run_loop = True
        while run_loop:
            # Check if a pool_result is finished
            for result in pool_results:
                if result.ready():
                    logger.debug('Removing finished task from the pool results')
                    pool_results.remove(result)

            # If the pool is still filled, continue
            if len(pool_results) >= threads:
                logger.debug('All threads running, not creating new vMotion tasks. Waiting 5 seconds to check again')
                sleep(5)
                continue

            # If not, create new task (selects next VM, selects random host)
            vm = vms[vm_index]
            host = random.choice(hosts)
            logger.info('Creating vMotion task for VM %s to host %s' % (vm.name,host.name))
            pool_results.append(pool.apply_async(vm_vmotion_handler,(si,logger,vm,host,interval)))

            vm_index += 1
            if vm_index >= len(vms) and onerun:
                logger.debug('One-run is enabled, all VMs are scheduled to vMotion. Finishing.')
                wait_for_pool_end(logger,pool,pool_results)
                run_loop = False
                break

            if vm_index >= len(vms):
                logger.debug('Looping back to first VM')
                vm_index = 0

    except KeyboardInterrupt:
        logger.info('Received interrupt, finishing running threads and not creating any new migrations')
        if pool is not None and pool_results is not None:
            wait_for_pool_end(logger,pool,pool_results)
        
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
