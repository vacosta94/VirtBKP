#!/bin/python
import subprocess
import logging
import os
import ovirtsdk4 as sdk
import ovirtsdk4.types as types
import ConfigParser
import sys
import time

GREEN = '\033[92m'
ENDC = '\033[0m'

print len(sys.argv)
if len(sys.argv) <= 4:
	conf_file=sys.argv[1]
	cfg = ConfigParser.ConfigParser()
	cfg.readfp(open(sys.argv[1]))
	url=cfg.get('default', 'url')
	user=cfg.get('default', 'user')
	password=cfg.get('default', 'password')
	ca_file=cfg.get('default', 'ca_file')
	bkpvm=cfg.get('bkp','bkpvm')
	try:
	# Create a connection to the server:
		connection = sdk.Connection( url=url, username=user, password=password, ca_file=ca_file)
		print "Connect to: %s" % url
	except Exception as ex:
		print "Unexpected error: %s" % ex

	# definizione search string
	datacenter=sys.argv[2]
	search_string='name !=' + bkpvm + ' and datacenter ='+datacenter 

	if len(sys.argv) == 4:
		cluster = sys.argv[3]
		search_string='name !=' + bkpvm + ' and datacenter ='+ datacenter +' and cluster ='+cluster
		print search_string

	system_service = connection.system_service()
	vms_service = system_service.vms_service()
	vms = vms_service.list(search=search_string)
	disks_service = system_service.disks_service()

	for vm in vms:
		disks = vms_service.vm_service(vm.id).disk_attachments_service().list()
		for disk in disks:
			if disk.bootable == True:
				disk_service = disks_service.disk_service(disk.id)
				disk = disk_service.get()
				print(GREEN + "%s %s %s" % (vm.name,disk.name,disk.id )+ENDC)
				from backup_vm_select_disk import backup_vm
				b = backup_vm(conf_file,vm.name,disk.id)
				b.main()
	connection.close()

else:
	print ("Usage:")
	print ("backup_dc.py default.conf <dc_name>")
	exit(1)
