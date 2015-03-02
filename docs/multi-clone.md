multi-clone.py
==============
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

### Using threads ###
Deciding on the optimal amount of threads might need a bit of experimentation. Keep certain things in mind:
* The optimal amount of threads depends on the IOPS of the datastore as each thread will start a template deployment task, which in turn starts copying the disks.
* vCenter will, by default, only run 8 deployment tasks simultaniously while other tasks are queued, so setting the amount of threads to more than 8, is not really usefull.

### Using CSV file ###
A CSV file can be provided with a line for each VM that needs to be created, with specific parameters for each VM. The format of each row should be (fields surrounded with <> are mandatory, fields surrounded with [] are optional):
    "<Clone name>";"[Resouce Pool]";"[Folder]";"[MAC Address]";"[Post-processing Script]"
For instance:
    "Test01";"Development";"IT";"00:50:56:11:11:11";"run.sh"

### Post-processing Script ###
The Post-processing script is run for each VM created if it is provided either as a commandline parameter or as a field in the CSV. 
It is run with the following parameters:
* virtual machine name, mac and ip : If Print IPs or Print MACs is enabled, combined with Power on
* virtual machine name, mac: If a custom mac address was specified (even if VM is not powered on)
* virtual machine name: If a power on is disabled and no custom mac address is enabled

### Usage ###
    usage: multi-clone.py [-h] [-6] [-b BASENAME] [-c COUNT] [-C CSVFILE] [-d]
                          [-f FOLDER] -H HOST [-i] [-m] [-l LOGFILE] [-n AMOUNT]
                          [-o PORT] [-p PASSWORD] [-P] [-r RESOURCE_POOL]
                          [-s POST_SCRIPT] [-S] -t TEMPLATE [-T THREADS] -u
                          USERNAME [-v] [-w MAXWAIT]

    Deploy a template into multiple VM's. You can get information returned with
    the name of the virtual machine created and it's main mac and ip address.
    Either in IPv4 or IPv6 format. You can specify which folder and/or resource
    pool the clone should be placed in. Verbose and debug output can either be
    send to stdout, or saved to a log file. A post-script can be specified for
    post-processing. And it can all be done in a number of parallel threads you
    specify. The script also provides the ability to use a CSV for a lot of it
    settings and if you want to specify the mac address of the clones (usefull for
    DHCP/PXE configuration).

    optional arguments:
      -h, --help            show this help message and exit
      -6, --six             Get IPv6 address for VMs instead of IPv4
      -b BASENAME, --basename BASENAME
                            Basename of the newly deployed VMs
      -c COUNT, --count COUNT
                            Starting count, the name of the first VM deployed will
                            be <basename>-<count>, the second will be
                            <basename>-<count+1> (default = 1)
      -C CSVFILE, --csv CSVFILE
                            An optional CSV overwritting the basename and count.
                            For each line, a clone will be created. A line consits
                            of the following fields, fields inside <> are
                            mandatory, fields with [] are not: "<Clone
                            name>";"[Resouce Pool]";"[Folder]";"[MAC
                            Address]";"[Post Script]"
      -d, --debug           Enable debug output
      -f FOLDER, --folder FOLDER
                            The folder in which the new VMs should reside (default
                            = same folder as source virtual machine)
      -H HOST, --host HOST  The vCenter or ESXi host to connect to
      -i, --print-ips       Enable IP output
      -m, --print-macs      Enable MAC output
      -l LOGFILE, --log-file LOGFILE
                            File to log to (default = stdout)
      -n AMOUNT, --number AMOUNT
                            Amount of VMs to deploy (default = 1)
      -o PORT, --port PORT  Server port to connect to (default = 443)
      -p PASSWORD, --password PASSWORD
                            The password with which to connect to the host. If not
                            specified, the user is prompted at runtime for a
                            password
      -P, --disable-power-on
                            Disable power on of cloned VMs
      -r RESOURCE_POOL, --resource-pool RESOURCE_POOL
                            The resource pool in which the new VMs should reside,
                            (default = Resources, the root resource pool)
      -s POST_SCRIPT, --post-script POST_SCRIPT
                            Script to be called after each VM is created and
                            booted. Arguments passed: name mac-address ip-address
      -S, --disable-SSL-certificate-verification
                            Disable SSL certificate verification on connect
      -t TEMPLATE, --template TEMPLATE
                            Template to deploy
      -T THREADS, --threads THREADS
                            Amount of threads to use. Choose the amount of threads
                            with the speed of your datastore in mind, each thread
                            starts the creation of a virtual machine. (default =
                            1)
      -u USERNAME, --user USERNAME
                            The username with which to connect to the host
      -v, --verbose         Enable verbose output
      -w MAXWAIT, --wait-max MAXWAIT
                            Maximum amount of seconds to wait when gathering
                            information (default = 120)

### Issues and feature requests
Feel free to use the [Github issue tracker](https://github.com/pdellaert/vSphere-Python/issues) of the repository to post issues and feature requests

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
