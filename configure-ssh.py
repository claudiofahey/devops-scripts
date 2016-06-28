#!/usr/bin/env python
# Written by claudio.fahey@emc.com

"""%prog [options] host ...

%prog will configure password-less SSH to remote hosts.

Examples:
  %prog -u root host1
    This is the simplest usage. It will prompt for the password for root@host1.
    When it is done, "ssh root@host1" should run without asking for a password.

  %prog -u root host1 host2
    Same as above but it will repeat for host1 and host2.

  %prog -u root $(cat master.txt worker.txt)
    Same as above but it will repeat for each host listed in the files master.txt and worker.txt.

  %prog -u root -p mysecretpassword host1 host2
    To avoid being prompted for a password, specify it with the -p option.
    You must have sshpass installed for this to work.
    Understand the risks of using sshpass before using this in a secure setting.

  %prog -u user1 -U centos host1
    When configuring password-less SSH, use the account centos@host1 to establish the
    initial SSH connection. This will configure the ~/.ssh directory for user1@host1 to
    allow password-less SSH to this account.

  %prog -u user1 -U centos -s host1
    Same as above but centos@host1 will use sudo to access user1@host1's home directory.
    This is useful for cloud images where password-less SSH already exists for centos@host1 but
    not other accounts.

  %prog --help
    View all options."""

import os
import optparse
import tempfile
import shutil
import os.path

def configure_ssh(host, user, password, configure_as_user, sudo, public_key_path, configure_as_identity, identity):
    """host can be IP, fqdn, or relative host name"""
   
    # Use a dictionary to make it easy to build the various command strings.
    p = {
        'password': password, 
        'user': user, 
        'host': host, 
        'configure_as_user': configure_as_user, 
        'public_key_path': public_key_path, 
        'configure_as_identity': configure_as_identity,
        'identity': identity,
        }

    if p['password']:
        p['sshpass'] = 'sshpass -p "%(password)s" ' % p
    else:
        p['sshpass'] = ''

    if not p['configure_as_user']:
        p['configure_as_user'] = p['user']

    if sudo:
        p['sudo'] = 'sudo '
        p['ssh_opt_tt'] = '-tt '
    else:
        p['sudo'] = ''
        p['ssh_opt_tt'] = ''

    # Note that when ssh -tt is used, read from stdin blocks. Therefore, use head -1 to prevent blocking.
    p['remote_cmd'] = ((
        '%(sudo)smkdir -p ~%(user)s/.ssh ' +
        '; %(sudo)stouch ~%(user)s/.ssh/authorized_keys ' +
        '; %(sudo)schmod 700 ~%(user)s/.ssh ' +
        '; %(sudo)schown -R %(user)s ~%(user)s/.ssh ' +
        '; %(sudo)schown -R :%(user)s ~%(user)s/.ssh ' +
        '; %(sudo)schmod 600 ~%(user)s/.ssh/authorized_keys ' +
        '; head -1 - | %(sudo)stee -a ~%(user)s/.ssh/authorized_keys')
        % p)

    p['ssh_cmd'] = '"%(remote_cmd)s"' % p

    if p['configure_as_identity']:
        p['ssh_opt_i'] = '-i %(configure_as_identity)s ' % p
    else:
        p['ssh_opt_i'] = ''

    if p['identity']:
        p['ssh_opt_i_test'] = '-i %(identity)s ' % p
    else:
        p['ssh_opt_i_test'] = ''

    # Remove host from known_hosts file to avoid problems with IP address reuse
    cmd = 'ssh-keygen -R %(host)s' % p
    print('# %s' % cmd)
    os.system(cmd)

    # Configure password-less SSH
    cmd = ((
        'cat %(public_key_path)s ' +
        '| %(sshpass)sssh -o StrictHostKeyChecking=no %(ssh_opt_tt)s%(ssh_opt_i)s%(configure_as_user)s@%(host)s %(ssh_cmd)s')
        % p)
    print('# %s' % cmd)
    os.system(cmd)

    # Test password-less SSH
    cmd = 'ssh %(ssh_opt_i_test)s%(user)s@%(host)s "echo -n success: ; hostname"' % p
    print('# %s' % cmd)
    os.system(cmd)

def main():
    parser = optparse.OptionParser(usage=__doc__)
    parser.add_option('-u', '--user', action='append', dest='users', 
        help='target user on remote host')
    parser.add_option('-U', '--configure-as-user', action='store', dest='configure_as_user', 
        help='configure using this user account on remote host')
    parser.add_option('-k', '--public-key', action='store', dest='public_key', default='~/.ssh/id_rsa.pub', 
        help='id_rsa.pub key file to authorize')
    parser.add_option('-i', '--identity', action='store', dest='identity', default='~/.ssh/id_rsa', 
        help='id_rsa private key file for local user that should be allowed to SSH into the remote host')
    parser.add_option('-I', '--configure-as-identity', action='store', dest='configure_as_identity', default='~/.ssh/id_rsa', 
        help='configure using id_rsa private key file')
    parser.add_option('-n', '--host', action='append', dest='hosts', 
        help='name of remote host (-n is optional)')
    parser.add_option('-p', '--password', action='store', dest='password', 
        help='password of user on remote host (requires sshpass)')
    parser.add_option('-s', '--sudo', action='store_true', dest='sudo', 
        help='use sudo on remote host')
    options, args = parser.parse_args()
    hosts = args
    if options.hosts:
        hosts += options.hosts
    if not options.users or not hosts:
        parser.error('Missing required parameters')

    public_key_path = os.path.expanduser(options.public_key)
    if not os.path.isfile(public_key_path):
        parser.error('The public key file %s is missing. Use the command "ssh-keygen -t rsa -b 4096" to create a key pair.' % public_key_path)

    for user in options.users:
        for host in hosts:
            configure_ssh(host, user, options.password, options.configure_as_user, options.sudo, public_key_path, options.configure_as_identity, options.identity)

if __name__ == '__main__':
    main()
