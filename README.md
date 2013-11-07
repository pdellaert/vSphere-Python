vSphere-Python
==============

Collection of Python vSphere scripts using PySphere (http://code.google.com/p/pysphere/)

# Contributing #

1. Fork the repository on Github
2. Create a named feature branch
3. Write your change
5. Submit a Pull Request using Github

# multi-clone.py #
This script can be used to deploy multiple VMs from a template in an automatic way, with the possibility to add a post script. The post script gets two parameters: the VM name and possibly the IP address (either IPv4 or IPv6, depending on the parameters)

### Requirements ###
1. [PySphere 0.1.8+](https://code.google.com/p/pysphere/)
2. vCenter 5+ (tested with 5.1, 5.1u & 5.5)
3. If you only want to deploy templates without post processing: A user with a role with at least the following permission over the complete vCenter server:
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
    multi-clone.py [-h] [-6] -b BASENAME [-c COUNT] [-n AMOUNT]
                          [-p POST_SCRIPT] [-r RESOURCE_POOL] -s SERVER -t
                          TEMPLATE -u USERNAME [-v] [-w MAXWAIT]
     
    Deploy a template into multiple VM's
     
    optional arguments:
      -h, --help            show this help message and exit
      -6, --six             Get IPv6 address for VMs instead of IPv4
      -b BASENAME, --basename BASENAME
                            Basename of the newly deployed VMs
      -c COUNT, --count COUNT
                            Starting count, the name of the first VM deployed will
                            be <basename>-<count>, the second will be
                            <basename>-<count +1> (default=1)
      -n AMOUNT, --number AMOUNT
                            Amount of VMs to deploy (default=1)
      -p POST_SCRIPT, --post-script POST_SCRIPT
                            Script to be called after each VM is created and
                            booted. Arguments passed: name ip-address
      -r RESOURCE_POOL, --resource-pool RESOURCE_POOL
                            The resource pool in which the new VMs should reside
      -s SERVER, --server SERVER
                            The vCenter or ESXi server to connect to
      -t TEMPLATE, --template TEMPLATE
                            Template to deploy
      -u USERNAME, --user USERNAME
                            The username with which to connect to the server
      -v, --verbose         Enable verbose output
      -w MAXWAIT, --wait-max MAXWAIT
                            Maximum amount of seconds to wait when gathering
                            information (default 120)</count></basename></count></basename>

