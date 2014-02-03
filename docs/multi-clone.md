multi-clone.py
==============
An extension and improvement on the earlier released pysphere-multi-clone.py script using the pyVmomi library of VMware. The scripts provide extended capabilities to clone a virtual machine or template to one or more virtual machines in a parallel (threaded) way. 

It allows you to specify the ability to print out the mac address of the main nic, the ip address or both. The format will be '[virtual machine name] [mac] [ip]'.

The same information can be given to a post-process script. If no mac and/or ip information is available, it will only get the virtual machine name as argument.

Check the Usage chapter for more information on the options and capabilities.

### Requirements ### 
1. [pyVmomi](https://github.com/vmware/pyvmomi)
2. vCenter 5+ (tested with 5.1, 5.1u & 5.5)
3. A user with a role with at least the following permission over the complete vCenter server:
    * Datastore 
        * Allocate space
    * Network
        * Assign Network
    * Resource
        * Apply recommendation
        * Assign virtual machine to resource pool
    * Scheduled task
        * Create tasks
        * Run task
    * Virtual Machine
        * Configuration
            * Add new disk
        * Interaction
            * Power on
        * Inventory
            * Create from existing
        * Provisioning
            * Clone virtual machine
            * Deploy from template

### Usage ###
    usage: multi-clone.py [-h] [-6] -b BASENAME [-c COUNT] [-d] [-f FOLDER] -H
                          HOST [-i] [-m] [-l LOGFILE] [-n AMOUNT] [-o PORT]
                          [-p PASSWORD] [-P] [-r RESOURCE_POOL] [-s POST_SCRIPT]
                          -t TEMPLATE [-T THREADS] -u USERNAME [-v] [-w MAXWAIT]

    Deploy a template into multiple VM's. You can get information returned with
    the name of the virtual machine created and it's main mac and ip address.
    Either in IPv4 or IPv6 format. You can specify which folder and/or resource
    pool the clone should be placed in. Verbose and debug output can either be
    send to stdout, or saved to a log file. A post-script can be specified for
    post-processing. And it can all be done in a number of parallel threads you
    specify.

    optional arguments:
      -h, --help            show this help message and exit
      -6, --six             Get IPv6 address for VMs instead of IPv4
      -b BASENAME, --basename BASENAME
                            Basename of the newly deployed VMs
      -c COUNT, --count COUNT
                            Starting count, the name of the first VM deployed will
                            be <basename>-<count>, the second will be
                            <basename>-<count+1> (default=1)
      -d, --debug           Enable debug output
      -f FOLDER, --folder FOLDER
                            The folder in which the new VMs should reside
      -H HOST, --host HOST  The vCenter or ESXi host to connect to
      -i, --print-ips       Enable IP output
      -m, --print-macs      Enable MAC output
      -l LOGFILE, --log-file LOGFILE
                            File to log to, if not specified, stdout is used
      -n AMOUNT, --number AMOUNT
                            Amount of VMs to deploy (default=1)
      -o PORT, --port PORT  Server port to connect to
      -p PASSWORD, --password PASSWORD
                            The password with which to connect to the host
      -P, --disable-power-on
                            Disable power on of cloned VMs
      -r RESOURCE_POOL, --resource-pool RESOURCE_POOL
                            The resource pool in which the new VMs should reside,
                            (default=Resources , the root resource pool
      -s POST_SCRIPT, --post-script POST_SCRIPT
                            Script to be called after each VM is created and
                            booted. Arguments passed: name ip-address
      -t TEMPLATE, --template TEMPLATE
                            Template to deploy
      -T THREADS, --threads THREADS
                            Amount of threads to use (default=amount of cores in
                            your environment)
      -u USERNAME, --user USERNAME
                            The username with which to connect to the host
      -v, --verbose         Enable verbose output
      -w MAXWAIT, --wait-max MAXWAIT
                            Maximum amount of seconds to wait when gathering
                            information (default 120)
