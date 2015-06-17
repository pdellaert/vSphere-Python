random-vmotion.py
=================
random-vmotion is a Python script which will vMotion VMs randomly to a set of hosts until stopped by a keyboard interupt (ctrl-c)

This script has the following capabilities:
* vMotion VMs to a random host
* Continue until stopped
* Print logging to a log file or stdout
* Do this threaded

### Using threads ###
Deciding on the optimal amount of threads might need a bit of experimentation. Keep certain things in mind:
* The optimal amount of threads depends on the memory consumption of the VMs, the activity of the VMs and the amount of hosts as each thread will execute a vMotion task. If this is all to the same host with the a lot of activity in the VM, you might get in trouble.

### Files ###
The files are a list of VMs and Hosts, each in a seperate file and with one entry per line

### Usage ###
    usage: random-vmotion.py [-h] [-d] -H HOST [-i INTERVAL] [-l LOGFILE]
                             [-o PORT] [-p PASSWORD] [-S] -t TARGETFILE
                             [-T THREADS] -u USERNAME [-v] -V VMFILE

    Randomly vMotion each VM from a list one by one to a random host from a list,
    until stopped.

    optional arguments:
      -h, --help            show this help message and exit
      -d, --debug           Enable debug output
      -H HOST, --host HOST  The vCenter or ESXi host to connect to
      -i INTERVAL, --interval INTERVAL
                            The amount of time to wait after a vMotion is finished
                            to schedule a new one (default 30 seconds)
      -l LOGFILE, --log-file LOGFILE
                            File to log to (default = stdout)
      -o PORT, --port PORT  Server port to connect to (default = 443)
      -p PASSWORD, --password PASSWORD
                            The password with which to connect to the host. If not
                            specified, the user is prompted at runtime for a
                            password
      -S, --disable-SSL-certificate-verification
                            Disable SSL certificate verification on connect
      -t TARGETFILE, --targets TARGETFILE
                            File with the list of target hosts to vMotion to
      -T THREADS, --threads THREADS
                            Amount of simultanious vMotions to execute at once.
                            (default = 1)
      -u USERNAME, --user USERNAME
                            The username with which to connect to the host
      -v, --verbose         Enable verbose output
      -V VMFILE, --vms VMFILE
                            File with the list of VMs to vMotion

### Issues and feature requests ###
Feel free to use the [Github issue tracker](https://github.com/pdellaert/vSphere-Python/issues) of the repository to post issues and feature requests

### Requirements ### 
1. [pyVmomi](https://github.com/vmware/pyvmomi)
2. vCenter 5+ (tested with 5.1, 5.1u, 5.5 & 6.0)