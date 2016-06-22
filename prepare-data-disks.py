#!/usr/bin/python -u
# Written by claudio.fahey@emc.com

"""%prog [options] /dev/disk ...

%prog will partition, format, and mount each of the specified disks.

Examples:
  %prog /dev/sdb
    This will create a single partition on /dev/sdb, format it using ext4,
    and then mount it as /grid/0.

  %prog /dev/sdb /dev/sdc
    Same as above but will repeat with /dev/sdc and mount it is /grid/1.

  %prog -a -m sdb-c
    Automatically discover the disks that match the pattern /dev/sd[b-z],
    then partition, format, and mount them.

  %prog -a -m sdb-c -t
    Automatically discover the disks that match the pattern /dev/sd[b-z].
    Prints the list of disks but does not take any action to partition,
    format, or mount the disks. Use the -t option to ensure the list of 
    disks is correct before preparing them.

  %prog --help
    View all options.

WARNING! THIS WILL ERASE THE CONTENTS OF THESE DISKS!"""

import os
import glob
import platform
import multiprocessing
import subprocess
import optparse
from time import sleep

def get_disks_to_prepare(discover_method):
    disks = []
    if discover_method == 'ecs':
        disk_list_commands = [
            'parted -m -s -l | grep /dev/.*:4001GB | cut -d : -f 1 | sort',
            'parted -m -s -l | grep /dev/.*:6001GB | cut -d : -f 1 | sort',
            'parted -m -s -l | grep /dev/.*:8002GB | cut -d : -f 1 | sort',
            ]
        disks = [subprocess.check_output(cmd, shell=True) for cmd in disk_list_commands]
        disks = ''.join(disks)
        disks = disks.rstrip('\n').split('\n')
        disks = [d for d in disks if d != '']
    elif discover_method == 'sdb-z':
        disks = sorted(glob.glob('/dev/sd[b-z]'))
    elif discover_method == 'vdb-z':
        disks = sorted(glob.glob('/dev/vd[b-z]'))
    return disks

def umount_disk(disk_info):
    disk = disk_info['disk']
    disk_number = disk_info['disk_number']    
    print('%s: Umounting disk %d, %s' % (platform.node(), disk_number, disk))
    os.system('umount %s1' % disk)

def partition_disk(disk_info):
    disk = disk_info['disk']
    disk_number = disk_info['disk_number']    
    print('%s: Partitioning disk %d, %s' % (platform.node(), disk_number, disk))
    if True:
        assert os.system('parted -s %s mklabel GPT' % disk) == 0
        os.system('parted -s %s rm 1' % disk)
        os.system('parted -s %s rm 2' % disk)
        # Must sleep to avoid errors updating OS partition table.
        sleep(0.2)
        assert os.system('parted -s -a cylinder %s -- mkpart primary ext4 1 -1' % disk) == 0

def format_disk(disk_info):
    disk = disk_info['disk']
    disk_number = disk_info['disk_number']    
    mount = disk_info['mount']    
    print('%s: Formatting disk %d, %s, %s' % (platform.node(), disk_number, disk, mount))
    if True:
        assert os.system('mkfs.ext4 -q -T largefile -m 0 %s1' % disk) == 0

def mount_disk(disk_info):
    disk = disk_info['disk']
    disk_number = disk_info['disk_number']    
    mount = disk_info['mount']    
    print('%s: Mounting disk %d, %s, %s' % (platform.node(), disk_number, disk, mount))
    assert os.system('mkdir -p /grid/%d' % disk_number) == 0
    assert os.system('echo %s1\t%s\text4\tdefaults,noatime\t0\t0 >> /etc/fstab' % (disk, mount)) == 0
    assert os.system('mount %s' % mount) == 0

def main():
    parser = optparse.OptionParser(usage=__doc__)
    parser.add_option('-a', '--auto', action='store_true', dest='auto', 
        help='automatically discover disks to prepare')
    parser.add_option('-m', '--discover-method', action='store', dest='discover_method', default='sdb-z',
        help='method to discover disks to prepare')
    parser.add_option('-x', '--exclude', action='append', dest='exclude', 
        help='disk to always exclude (will not be prepared)')
    parser.add_option('-t', '--test', action='store_true', dest='test', 
        help='show disks that will be prepared but do not prepare them')
    parser.add_option('-n', '--disk-count', action='store', dest='disk_count', type='int',
        help='ensure there are exactly this many disks to prepare')    
    options, args = parser.parse_args()
    disks = args

    # Get list of disk partitions to format and mount.
    if options.auto:
        disks += get_disks_to_prepare(discover_method=options.discover_method)

    if options.exclude:
        disks = [d for d in disks if d not in options.exclude]

    disk_info = [{
        'disk_number': disk_number,     # First disk will be 0
        'disk': disk,
        'mount': '/grid/%d' % disk_number
        } for disk_number, disk in enumerate(disks)]

    print('The following %d disks will be erased:' % len(disks))
    print('  ' + '\n  '.join(disks))

    if options.disk_count:
        assert len(disks) == options.disk_count

    if options.test:
        return 0

    assert os.system('mkdir -p /grid') == 0

    # Remove /grid mounts from fstab.
    assert os.system('egrep -v "/grid/" /etc/fstab > /tmp/fstab ; cp /tmp/fstab /etc/fstab') == 0

    map(umount_disk, disk_info)
    map(partition_disk, disk_info)
    map(umount_disk, disk_info)

    # Format all disks in parallel.
    pool = multiprocessing.Pool(len(disks))
    pool.map(format_disk, disk_info)
    print('Format done.')

    map(mount_disk, disk_info)

    assert os.system('mount | grep /grid/') == 0

    print('%s: prepare_data_disks complete.' % platform.node())

if __name__ == '__main__':
    main()
