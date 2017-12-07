#!/usr/bin/python -u
# Written by claudio.fahey@emc.com

"""%prog [options] /dev/disk ...

%prog will partition, format, and mount each of the specified disks.

Examples:
  %prog /dev/sdb
    This will create a single partition on /dev/sdb, format it using ext4,
    and then mount it as /dcos/volume0.

  %prog /dev/sdb /dev/sdc
    Same as above but will repeat with /dev/sdc and mount it is /dcos/volume1.

  %prog -a -m sdb-z
    Automatically discover the disks that match the pattern /dev/sd[b-z],
    then partition, format, and mount them.

  %prog -a -m sdb-z -t
    Automatically discover the disks that match the pattern /dev/sd[b-z].
    Prints the list of disks but does not take any action to partition,
    format, or mount the disks. Use the -t option to ensure the list of 
    disks is correct before preparing them.

  %prog --help
    View all options.

WARNING! THIS WILL ERASE THE CONTENTS OF DISKS!"""

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

def umount_partitions(part_info):
    print('%s: Umounting partition %s' % (platform.node(), part_info['part_device']))
    os.system('umount %s' % part_info['part_device'])

def partition_disk(disk_info):
    disk = disk_info['disk']
    disk_number = disk_info['disk_number']    
    part_info = disk_info['part_info']
    print('%s: Partitioning disk %d, %s, %d partitions' % (platform.node(), disk_number, disk, len(part_info)))
    if True:
        assert os.system('parted -s %s mklabel GPT' % disk) == 0
        # Must sleep to avoid errors updating OS partition table.
        sleep(0.2)
        for pi in part_info:
            assert os.system('parted -s -a cylinder %s -- mkpart primary ext4 %s %s' % (disk, pi['begin_pct'], pi['end_pct'])) == 0

def format_partition(part_info):
    if part_info['skip_format']:
        return
    part_device = part_info['part_device']
    disk_number = part_info['disk_number']    
    mount = part_info['mount']    
    print('%s: Formatting partition %s, mount %s, disk %d' % (platform.node(), part_device, mount, disk_number))
    if True:
        assert os.system('mkfs.ext4 -q -T largefile -m 0 %s' % part_device) == 0

def mount_partitions(part_info):
    part_device = part_info['part_device']
    disk_number = part_info['disk_number']    
    mount = part_info['mount']    
    if not mount:
        return
    print('%s: Mounting partition %s, mount %s, disk %d' % (platform.node(), part_device, mount, disk_number))
    assert os.system('mkdir -p %s' % mount) == 0
    assert os.system('echo %s\t%s\text4\tdefaults,noatime\t0\t0 >> /etc/fstab' % (part_device, mount)) == 0
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
    parser.add_option('-p', '--partitions', action='store', dest='partitions_per_disk', type='int', default=1,
        help='create this many partitions per disk')    
    parser.add_option('', '--mount-prefix', action='store', dest='mount_prefix', default="/dcos/volume",
        help='partitions will be mounted using this prefix')    
    parser.add_option('', '--unmount-only', action='store_true', dest='unmount_only',
        help='only unmount partitions')    
    parser.add_option('', '--skip-format', action='store_true', dest='skip_format',
        help='skip formatting new partitions')    
    parser.add_option('', '--skip-mount', action='store_true', dest='skip_mount',
        help='skip mounting new partitions')    
    options, args = parser.parse_args()
    disks = args

    # Get list of disks to format and mount.
    if options.auto:
        disks += get_disks_to_prepare(discover_method=options.discover_method)

    if options.exclude:
        disks = [d for d in disks if d not in options.exclude]

    if len(disks) == 0:
        parser.error("No disks available")

    part_index = 0
    part_info = []
    disk_info = []
    for disk_number, disk in enumerate(disks):
        di = {
            'disk_number': disk_number,     # First disk will be 0
            'disk': disk,
            'part_info': [],
        }
        for part_number in range(options.partitions_per_disk):
            pi = {
                'part_index': part_index,
                'part_number': part_number,
                'part_device': '%s%d' % (disk, part_number + 1),
                'begin_pct': '%d%%' % int(100 * part_number / options.partitions_per_disk),
                'end_pct': '%d%%' % int(100 * (part_number + 1) / options.partitions_per_disk),
                'skip_format': options.skip_format,
                'mount': '' if options.skip_mount else '%s%d' % (options.mount_prefix, part_index),
                'disk_number': disk_number,
                'disk': disk,
            }
            part_info = part_info + [pi]
            di['part_info'] = di['part_info'] + [pi]
            part_index += 1
        disk_info = disk_info + [di]

    print('The following %d disks will be erased:' % len(disks))
    print('  ' + '\n  '.join(disks))

    print('The following %d partitions will be created:' % len(part_info))
    print('  ' + '\n  '.join(['%s mounted on %s, %s to %s' % (pi['part_device'], pi['mount'], pi['begin_pct'], pi['end_pct']) for pi in part_info]))

    if options.disk_count:
        assert len(disks) == options.disk_count

    if options.test:
        return 0

    # Remove existing mounts from fstab.
    assert os.system('egrep -v "%s" /etc/fstab > /tmp/fstab ; cp /tmp/fstab /etc/fstab' % options.mount_prefix) == 0

    map(umount_partitions, part_info)

    if not options.unmount_only:
        map(partition_disk, disk_info)
        map(umount_partitions, part_info)

        # Format all disks in parallel.
        pool = multiprocessing.Pool(len(part_info))
        pool.map(format_partition, part_info)
        print('Format done.')

        map(mount_partitions, part_info)

        if not options.skip_mount:
            assert os.system('mount | grep %s' % options.mount_prefix) == 0

    print('%s: prepare_data_disks complete.' % platform.node())

if __name__ == '__main__':
    main()
