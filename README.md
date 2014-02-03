vSphere-Python
==============

Collection of Python vSphere scripts

# multi-clone.py #
An extension and improvement on the earlier released pysphere-multi-clone.py script using the pyVmomi library of VMware. The scripts provide extended capabilities to clone a virtual machine or template to one or more virtual machines in a parallel (threaded) way. 

It allows you to specify the ability to print out the mac address of the main nic, the ip address or both. The format will be '<virtual machine name> [mac] [ip]'.

The same information can be given to a post-process script. If no mac and/or ip information is available, it will only get the virtual machine name as argument.

Check [the multi-clone.py documentation](https://github.com/pdellaert/vSphere-Python/blob/master/docs/multi-clone.md) for more information on the options and capabilities.

# pysphere-multi-clone.py #
This script can be used to deploy multiple VMs from a template in an automatic way, with the possibility to add a post script. The post script gets two parameters: the VM name and possibly the IP address (either IPv4 or IPv6, depending on the parameters)

Check [the pysphere-multi-clone.py documentation](https://github.com/pdellaert/vSphere-Python/blob/master/docs/pysphere-multi-clone.md) for more information on the options and capabilities.

Contributing
============
1. Fork the repository on Github
2. Create a named feature branch
3. Write your change
5. Submit a Pull Request using Github
