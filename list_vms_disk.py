#!/bin/python
import subprocess
import logging
import os
import ovirtsdk4 as sdk
import ovirtsdk4.types as types
import ConfigParser
import sys
import time

cfg = ConfigParser.ConfigParser()
cfg.readfp(open(sys.argv[1]))
url=cfg.get('default', 'url')
user=cfg.get('default', 'user')
password=cfg.get('default', 'password')
ca_file=cfg.get('default', 'ca_file')

try:
  # Create a connection to the server:
  connection = sdk.Connection(
        url=url,
        username=user,
        password=password,
        ca_file=ca_file)
  print "Connect to: %s" % url
except Exception as ex:
  print "Unexpected error: %s" % ex



system_service = connection.system_service()
vms_service = system_service.vms_service()
vms = vms_service.list()

disks_service = system_service.disks_service()
#disks = disks_service.list()

for vm in vms:
	#vm_service = vms_service.vm_service(vm.id)
	disks = vms_service.vm_service(vm.id).disk_attachments_service().list()
	
	#print("%s %s %s" % (vm.id, vm.name, ))
	for disk in disks:
		if disk.bootable == True:
			disk_service = disks_service.disk_service(disk.id)
			disk = disk_service.get()
			print("%s %s %s" % (vm.name,disk.name,disk.id ))

connection.close()

