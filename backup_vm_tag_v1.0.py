#!/bin/python

import printf
import ovirtsdk4 as sdk
import ovirtsdk4.types as types
import sys
import ConfigParser
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings()
import virtbkp_utils

from backup_vm_last import backup_vm

class backup_vm_tag():
 def __init__(self,conf_file):
  self.conf_file = conf_file
  cfg = ConfigParser.ConfigParser()
  cfg.readfp(open(conf_file))
  self.url=cfg.get('bkp', 'url')
  self.user=cfg.get('bkp', 'user')
  self.password=cfg.get('bkp', 'password')
  self.ca_file=cfg.get('bkp', 'ca_file')
  self.connection = None

 # Get  default values
 def start(self):
  try:
    # Create a connection to the server:
    self.connection = sdk.Connection(
        url=self.url,
        username=self.user,
        password=self.password,
        ca_file=self.ca_file)
    printf.OK("Connection to oVIrt API success %s" % self.url)
  except Exception as ex:
    print ex
    printf.ERROR("Connection to oVirt API has failed")

 def get_vm_tag(self,vmid):
  vms_service = self.connection.service("vms")
  vm_service = vms_service.vm_service(vmid)
  tags_service = vm_service.tags_service()
  tags = []
  for tag in tags_service.list():
    tags.append(tag.name)
  return tags

 def get_vms_with_tag(self,tag):
  vm_service = self.connection.service("vms")
  vm_list = []
  vms = vm_service.list()
  for vm in vms:
    if tag in self.get_vm_tag(vm.id):
      vm_list.append(vm.name)
  return vm_list
 
 def backup_vms_with_tag(self,tag):
  self.start()
  for vm in self.get_vms_with_tag(tag):
    try:
      printf.OK("Running backup of vm %s with tag %s" % vm,tag)
      b = backup_vm(self.conf_file,vm)
      b.main()
    except Exception as ex:
      printf.ERROR("Backup %s failed!" % vm)
      raise 

b = backup_vm_tag(sys.argv[1])
b.backup_vms_with_tag(sys.argv[2])
