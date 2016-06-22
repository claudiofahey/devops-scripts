#!/usr/bin/env python
# Written by claudio.fahey@emc.com

"""%prog [options]

%prog will permanently mount an NFS export.

Examples:
  %prog -m /mnt/home -p nfs-server.example.com:/home
    This will create the mount point directory, modify /etc/fstab,
    and mount the NFS export.

  %prog --help
    View all options."""

import optparse
import os

def create_mount(mount_point, nfs_path):
    assert os.system('umount %s ; mkdir -p %s' % (mount_point, mount_point)) == 0
    assert os.system('grep -v %s /etc/fstab > /tmp/fstab ; cp /tmp/fstab /etc/fstab' % mount_point) == 0
    assert os.system('echo %s\t%s\tnfs\tnolock,nfsvers=3,tcp,rw,hard,intr,timeo=600,retrans=2,rsize=524288,wsize=524288 >> /etc/fstab' % (nfs_path, mount_point)) == 0
    assert os.system('mount -a ; ls -lh %s' % mount_point) == 0

def main():
    parser = optparse.OptionParser(usage=__doc__)
    parser.add_option('-m', '--mount-point', action='store', dest='mount_point',
        help='mount point (e.g. /mnt/home)')
    parser.add_option('-p', '--nfs-path', action='store', dest='nfs_path', 
        help='NFS path (e.g. nfs-server.example.com:/home)')
    options, args = parser.parse_args()
    if not options.mount_point or not options.nfs_path:
        parser.error('Missing required parameters')

    create_mount(options.mount_point, options.nfs_path)

if __name__ == '__main__':
    main()
