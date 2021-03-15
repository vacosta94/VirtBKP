#!/bin/python
import sys 

if len(sys.argv) == 4:
	from backup_vm_select_disk import backup_vm
	b = backup_vm(sys.argv[1],sys.argv[2],sys.argv[3])
	b.main()
else:
	print ("Usage:")
	print ("backup_vm_disk.py default.conf <vm_name>  <disk_id>")
	exit (1)
