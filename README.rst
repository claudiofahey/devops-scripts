
===================================
DevOps Scripts
===================================

claudio.fahey@emc.com

This repository contains various Python scripts that can be used to automate various devops tasks.

- configue-ssh.py: configure password-less SSH to remote hosts

- mount-nfs.py: permanently mount an NFS export

- prepare-data-disks.py: partition, format, and mount each of the specified disks.

See the help in each script for usage and examples.


Simple Command Execution on Multiple Hosts using Xargs
------------------------------------------------------

There are many tools for executing commands on multiple hosts. However most such tools require
additional packages to be installed. For quick and dirty tasks, xargs can easily be used and shown below.

Setup is extremely easily. Create a text file where each line is the FQDN (fully qualified domain name),
hostname without domain, or the IP address
of each host in your cluster. If you have different groups of nodes, then you may want to create
a different file for each group. For instance, the file master.txt may contain the following:

.. parsed-literal::

  mycluster1-master-1.example.com
  mycluster1-master-2.example.com
  mycluster1-master-3.example.com

You would then create another file named worker.txt with the FQDN of your worker hosts.
Now you are ready to automate some tasks as shown in the below examples.

First a quick test. We'll just print the name of each FQDN prefixed with "Hello".
The **-n 1** option tells xargs to run the supplied command on each line instead of grouping
them into batches. The **-i** option tells xargs to replace the string **{}** with the
contents of the line which is our FQDN.

.. parsed-literal::

  $ cat master.txt worker.txt | xargs -n 1 -i echo Hello {}.
  Hello mycluster1-master-1.example.com.
  Hello mycluster1-master-2.example.com.
  Hello mycluster1-master-3.example.com.
  Hello mycluster1-worker-1.example.com.
  ...

To run a command on each host using SSH, use this command.
Note that you'll need password-less SSH configured or you will be prompted for a password on each connection.
If you haven't configured password-less SSH, see the script `<configure-ssh.py>`_ in this repository.

.. parsed-literal::

  $ cat master.txt worker.txt | xargs -n 1 -i ssh root@{} free -m

To run a compound command on each host:

.. parsed-literal::

  $ cat master.txt worker.txt | xargs -n 1 -i ssh root@{} "hostname ; swapon -s ; free -m"

You can easily filter the list of hosts to run commands on. This is useful for testing on one host before
running on all hosts.

.. parsed-literal::

  $ cat worker.txt | head -1 | xargs -n 1 -i ssh root@{} free -m

By default, xargs will run the commands sequentially, one host at a time.
If any command returns an error, xargs will stop and will not run additional commands.
You can run all commands concurrently with the **-P 0** option. This will also effectively
ignore any errors.

.. parsed-literal::

  $ cat master.txt worker.txt | xargs -n 1 -i -P 0 ssh root@{} yum install -y big_package

You can also use SCP to copy files between the local host and the remote hosts.

.. parsed-literal::

  $ cat master.txt worker.txt | xargs -n 1 -i scp /etc/hosts root@{}:/etc/hosts

Sometimes, you will need to execute sudo on the remote host. When sudo executes on certain
versions of CentOS or RedHat, it requires a TTY. This can be faked with the ssh **-tt** option.

.. parsed-literal::

  $ cat master.txt worker.txt | xargs -n 1 -i ssh -tt centos@{} sudo mount -a
