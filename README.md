vSphere-Python
==============

Collection of Python vSphere scripts

# multi-clone.py #
multi-clone is a Python script which allows you to clone a virtual machine or virtual machine template into multiple new virtual machines in a VMware vSphere environment. 

This script has the following capabilities:
* Deploy a specified amount of virtual machines
* Deploy in a specified folder
* Deploy in a specified resource pool
* Set advanced configuration options
* Specify if the cloned virtual machines need to be powered on
* Print out information of the main network interface (mac and ip, either IPv4 or IPv6)
* Run a post-processing script with 3 parameters (virtual machine name, mac and ip)
* Instead of setting the basename, amount, resource pool and folder a CSV can be used
* Print logging to a log file or stdout
* Do this in a threaded way

Check [the multi-clone.py documentation](https://github.com/pdellaert/vSphere-Python/blob/master/docs/multi-clone.md) for more information on the options and capabilities.

# random-vmotion.py #
random-vmotion is a Python script which will vMotion VMs randomly to a set of hosts until stopped by a keyboard interupt (ctrl-c)

This script has the following capabilities:
* vMotion VMs to a random host
* Continue until stopped
* Print logging to a log file or stdout
* Do this threaded

Check [the random-vmotion.py documentation](https://github.com/pdellaert/vSphere-Python/blob/master/docs/random-vmotion.md) for more information on the options and capabilities.

# pysphere-multi-clone.py #
This script can be used to deploy multiple VMs from a template in an automatic way, with the possibility to add a post script. The post script gets two parameters: the VM name and possibly the IP address (either IPv4 or IPv6, depending on the parameters)

Check [the pysphere-multi-clone.py documentation](https://github.com/pdellaert/vSphere-Python/blob/master/docs/pysphere-multi-clone.md) for more information on the options and capabilities.

Contributing
============
1. Fork the repository on Github
2. Create a named feature branch
3. Write your change
5. Submit a Pull Request using Github
