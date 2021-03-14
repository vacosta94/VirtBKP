#!/bin/python

import printf
import ovirtsdk4 as sdk
import ovirtsdk4.types as types
import time
import sys
import subprocess
import requests
import requests
import ConfigParser
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings()
import xml.etree.ElementTree as ET
import thread
import virtbkp_utils
import signal

class backup_vm():
 #def __init__():
 def __init__(self,conf_file,vmname,my_disk):
  cfg = ConfigParser.ConfigParser()
  cfg.readfp(open(conf_file))
  self.vmname=vmname
  self.vmid=''
  self.url=cfg.get('bkp', 'url')
  self.user=cfg.get('bkp', 'user')
  self.password=cfg.get('bkp', 'password')
  self.ca_file=cfg.get('bkp', 'ca_file')
  self.bckdir=cfg.get('bkp', 'bckdir')
  self.bkpvm=cfg.get('bkp', 'bkpvm')
  self.date=str((time.strftime("%Y-%m-%d-%H")))
  self.my_disk=my_disk
  try:
    self.timeout_detect=int(cfg.get('bkp','timeout_detect'))
  except:
    self.timeout_detect=3600
  self.vmid=''
  self.snapname = "BACKUP" + "_" + self.date +"h"
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
  
# Funcion para obtener el id de la vm buscandola por el nombre
# Function to get VM_ID from VM name
 def get_id_vm(self,vmname):
  vm_service = self.connection.service("vms")
  vms = vm_service.list()
  for vm in vms:
   if vm.name == vmname:
     return vm.id

# Funcion para obtener el ID del snapshot creado 
# Function to get ID of created snapshot
 def get_snap_id(self,vmid):
  headers = {'Content-Type': 'application/xml', 'Accept': 'application/xml'}
  vmsnap_service = self.connection.service("vms/"+vmid+"/snapshots")
  snaps = vmsnap_service.list()
  for snap in snaps:
   if snap.description == self.snapname:
    return snap.id

# Funcion para obtener el estado del snapshot
# Function to get snapshot status
 def get_snap_status(self,vmid,snapid):
  vmsnap_service = self.connection.service("vms/"+vmid+"/snapshots")
  snaps = vmsnap_service.list()
  for snap in snaps:
   if snap.id == snapid:
    return snap.snapshot_status

# Funcion para crear el snapshot
# Function to create snapshot
 def create_snap(self,vmid,snapname,my_disk):
  vm_service = self.connection.service("vms")
  snapshots_service = vm_service.vm_service(vmid).snapshots_service()
  snapshots_service.add(types.Snapshot(description=snapname,persist_memorystate=False, disk_attachments=[ types.DiskAttachment( disk=types.Disk( id=my_disk)) ]))
  snapid = self.get_snap_id(vmid)
  status = self.get_snap_status(vmid,snapid)
  printf.INFO("Trying to create snapshot of VM: " + vmid)
  while str(status) == "locked":
    time.sleep(10)
    printf.INFO("Waiting until snapshot creation ends")
    status = self.get_snap_status(vmid,snapid)
  printf.OK("Snapshot created")

# Funcion para eliminar el snapshot
# Function to delte snapshot
 def delete_snap(self,vmid,snapid):
  snap_service = self.connection.service("vms/"+vmid+"/snapshots/"+snapid)
  snap_service.remove()
  status = self.get_snap_status(vmid,snapid)
  while str(status) != "None":
    time.sleep(30)
    printf.INFO("Waiting until snapshot deletion ends") 
    status = self.get_snap_status(vmid,snapid)
  printf.OK("Snapshot deleted")

# Funcion para obtener el ID del disco de snapshot
# Function to get snapshost disk ID
 def snap_disk_id(self,vmid,snapid):
  svc_path = "vms/"+vmid+"/snapshots/"+snapid+"/disks/"
  disksnap_service = self.connection.service(svc_path)
  disks = disksnap_service.list()
  vm_disks = ()
  for disk in disks:
    vm_disks = vm_disks + (disk.id,)
  return vm_disks

# Funcion para atachar disco a VM
# Function to attach disk to VM
 def attach_disk(self,bkpid,diskid,snapid):
  xmlattach =  "<disk id=\""+diskid+"\"><snapshot id=\""+snapid+"\"/> <active>true</active></disk>"
  urlattach = self.url+"/v3/vms/"+bkpid+"/disks/"
  headers = {'Content-Type': 'application/xml', 'Accept': 'application/xml'}
  requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
  resp_attach = requests.post(urlattach, data=xmlattach, headers=headers, verify=False, auth=(self.user,self.password))

# Funcion para desactivar disco virtual
# Function to deactivate virtual disk
 def deactivate_disk(self,bkpid,diskid):
  xmldeactivate =  "<action/>"
  urldeactivate = self.url+"/v3/vms/"+bkpid+"/disks/"+diskid+"/deactivate"
  headers = {'Content-Type': 'application/xml', 'Accept': 'application/xml'}
  resp_attach = requests.post(urldeactivate, data=xmldeactivate, headers=headers, verify=False, auth=(self.user,self.password))

# Funcion para desataschar disco de VM
# Function to dettach disk 
 def detach_disk(self,bkpid,diskid):
  urldelete = self.url+"/vms/"+bkpid+"/diskattachments/"+diskid
  requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
  requests.delete(urldelete, verify=False, auth=(self.user,self.password))

# Funcion para obtener el nombre de dispositivo de disco virtual
# Function to get device name of a virtual disk
 def get_logical_disk(self,bkpid,diskid):
  dev="None"
  b=True
  urlget = "vms/"+bkpid+"/diskattachments/"
  serial=diskid[0:20]
  cmd="grep -Rlw '"+serial+"' /sys/block/*/serial|awk -F '/' '{print $4}'"  
  while b:
   # Trying to  identify VIRTIO devices
   try: 
    path = subprocess.check_output(cmd, shell=True).replace("\n","")
    if path.startswith("vd") or path.startswith("sd") :
      dev = "/dev/" + path
      time.sleep(1)
   except:
    continue
   if str(dev) != "None":
    printf.INFO("Disk found using serial number")
    b=False
   else:
  # Trying to identify devices through API
    disk_service = self.connection.service(urlget)
    for disk in disk_service.list():
     dev = str(disk.logical_name)
     if disk.id == diskid and str(dev) != "None":
       printf.INFO("Disk found using API")
       b=False
     else:
       dev="None"
       time.sleep(1)
  return dev

 def run_qemu_convert(self,cmd):
  out = subprocess.call(cmd, shell=True)
  qcowfile = cmd.split()[-1]
  if int(out) == 0:
   #print "Se creo correctamente la imagen"
   print
   printf.OK("qcow2 file creation success")
  else:
   print
   printf.ERROR("qcow2 file creation failed")
   printf.ERROR("Deleting file %s" % qcowfile)
   subprocess.call("rm -rf %s" % qcowfile , shell=True)  

 # Funcion para crear imagen qcow2 del disco
 # Function  to create qcow file of disk
 def create_image_bkp(self,dev,diskname):
   bckfiledir = self.bckdir + "/" + self.vmname + "/" + self.date
   mkdir = "mkdir -p " + bckfiledir
   time.sleep(5)
   subprocess.call(mkdir, shell=True) 
   bckfile = bckfiledir + "/" + diskname + ".qcow2"
   printf.INFO("Creating qcow2 file: " + bckfile)
   cmd = "qemu-img convert -U -O qcow2 " + dev + " " +bckfile
   printf.INFO("cmd:" + cmd)
   utils=virtbkp_utils.virtbkp_utils()
   thread.start_new_thread(self.run_qemu_convert,(cmd,))
   utils.progress_bar_qcow(bckfile)
 
 # Funcion para obtener el nombre del disco virtual 
 # Function to get virtual disk name
 def get_disk_name(self,vmid,snapid,diskid):
   svc_path = "vms/"+vmid+"/snapshots/"+snapid+"/disks/"
   disksnap_service = self.connection.service(svc_path)
   disks = disksnap_service.list()
   for disk in disks:
     if diskid == str(disk.id):
       return disk.alias
 
 def handler_timeout():
   printf.ERROR("Time Out reached ")
   raise Exception("Time Out")
   #printf.INFO("Deactivate disk of bkpvm")
   #self.deactivate_disk(bkpvm,disk_id)
   #time.sleep(10)
   #printf.INFO("Dettach snap disk of bkpvm")
   #self.detach_disk(bkpvm,disk_id)
   #time.sleep(10)
 
 def backup(self,vmid,snapid,disk_id,bkpvm):
   # Se agrega el disco a la VM que tomara el backup
   
   try: 
     signal.signal(signal.SIGALRM, self.handler_timeout)  
     signal.alarm(self.timeout_detect) 
     printf.INFO("Timeout is defined to %s" % self.timeout_detect)
     printf.INFO("Attach snap disk to bkpvm")
     self.attach_disk(bkpvm,disk_id,snapid)
     # Se obtiene el nombre del dispositivo
     printf.INFO("Identifying disk device, this might take a while")
     dev = self.get_logical_disk(bkpvm,disk_id)
     # Se obtiene el nombre del disco
     diskname = self.get_disk_name(vmid,snapid,disk_id)
     time.sleep(10)
     signal.alarm(0)
     # Se crea la image qcow que seria el  backup como tal
     self.create_image_bkp(dev,diskname)
     # Se desactiva el disco del cual se hizo el backup
     self.deactivate_disk(bkpvm,disk_id)
     time.sleep(10)
     # Se detacha el disco de la BKPVM
     printf.INFO("Dettach snap disk of bkpvm")
     self.detach_disk(bkpvm,disk_id)
   except:
     printf.ERROR("Time Out reached ")
     self.deactivate_disk(bkpvm,disk_id)
     time.sleep(10)
     printf.INFO("Dettach snap disk of bkpvm")
     self.detach_disk(bkpvm,disk_id)

 def main(self):
  self.start()
  ## Parte Principal
  # Se consigue el ID de la VM a la cual se hara backup y la VM donde se montaran sus discos
  self.vmid = self.get_id_vm(self.vmname)
  self.bkpvm = self.get_id_vm(self.bkpvm)
  # Se crea el snap y se espera un rato para que termine sin problemas y pueda detectar el nombre del disco en VM de backup
 
  printf.INFO("my_disk=" + self.my_disk)
  self.create_snap(self.vmid,self.snapname,self.my_disk)
  #time.sleep(60)
  # Se obtiene el id del snap
  self.snapid = self.get_snap_id(self.vmid)
  # Se obtiene el ID del disco
  vm_disks = self.snap_disk_id(self.vmid,self.snapid)
  for disk_id in vm_disks:
    printf.INFO("Trying to create a qcow2 file of disk " + disk_id)
    # Backup
    self.backup(self.vmid,self.snapid,disk_id,self.bkpvm)
  printf.INFO("Trying to delete snapshot of " + self.vmname)
  self.delete_snap(self.vmid,self.snapid)
