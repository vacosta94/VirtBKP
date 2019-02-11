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

# Get default values
cfg = ConfigParser.ConfigParser()
cfg.readfp(open(sys.argv[1]))
url=cfg.get('bkp', 'url')
user=cfg.get('bkp', 'user')
password=cfg.get('bkp', 'password')
ca_file=cfg.get('bkp', 'ca_file')
bckdir=cfg.get('bkp', 'bckdir')
bkpvm=cfg.get('bkp', 'bkpvm')
vmname=sys.argv[2]


date=str((time.strftime("%Y-%m-%d-%H")))
vmid=""
snapname = "BACKUP" + "_" + date +"h"


try:
  # Create a connection to the server:
  connection = sdk.Connection(
	url=url,
    	username=user,
  	password=password,
 	ca_file=ca_file)
  printf.OK("Connection to oVIrt API success %s" % url) 
except Exception as ex:
  printf.ERROR("Connection to oVirt API has failed")
  #print "Unexpected error: %s" % ex
  
# Funcion para obtener el id de la vm buscandola por el nombre
# Function to get VM_ID from VM name
def get_id_vm(vmname):
 vm_service = connection.service("vms")
 vms = vm_service.list()
 for vm in vms:
  if vm.name == vmname:
    return vm.id

# Funcion para obtener el ID del snapshot creado 
# Function to get ID of created snapshot
def get_snap_id(idvm):
 headers = {'Content-Type': 'application/xml', 'Accept': 'application/xml'}
 vmsnap_service = connection.service("vms/"+idvm+"/snapshots")
 snaps = vmsnap_service.list()
 for snap in snaps:
  if snap.description == snapname:
   return snap.id

# Funcion para obtener el estado del snapshot
# Function to get snapshot status
def get_snap_status(idvm,snapid):
 vmsnap_service = connection.service("vms/"+idvm+"/snapshots")
 snaps = vmsnap_service.list()
 for snap in snaps:
  if snap.id == snapid:
   return snap.snapshot_status

# Funcion para crear el snapshot
# Function to create snapshot
def create_snap(idvm):
 vm_service = connection.service("vms")
 snapshots_service = vm_service.vm_service(idvm).snapshots_service()
 snapshots_service.add(types.Snapshot(description=snapname, persist_memorystate=False))
 snapid = get_snap_id(vmid)
 status = get_snap_status(idvm,snapid)
 printf.INFO("Trying to create snapshot of VM: " + idvm)
 while str(status) == "locked":
    time.sleep(10)
    printf.INFO("Waiting until snapshot creation ends")
    status = get_snap_status(idvm,snapid)
 printf.OK("Snapshot created")

# Funcion para eliminar el snapshot
# Function to delte snapshot
def delete_snap(idvm,snapid):
 snap_service = connection.service("vms/"+idvm+"/snapshots/"+snapid)
 snap_service.remove()
 status = get_snap_status(idvm,snapid)
 while str(status) != "None":
    time.sleep(30)
    printf.INFO("Waiting until snapshot deletion ends") 
    status = get_snap_status(idvm,snapid)
 printf.OK("Snapshot deleted")

# Funcion para obtener el ID del disco de snapshot
# Function to get snapshost disk ID
def snap_disk_id(idvm,snapid):
 svc_path = "vms/"+idvm+"/snapshots/"+snapid+"/disks/"
 disksnap_service = connection.service(svc_path)
 disks = disksnap_service.list()
 vm_disks = ()
 for disk in disks:
  vm_disks = vm_disks + (disk.id,)
 return vm_disks

# Funcion para atachar disco a VM
# Function to attach disk to VM
def attach_disk(bkpid,diskid,snapid):
 xmlattach =  "<disk id=\""+diskid+"\"><snapshot id=\""+snapid+"\"/> <active>true</active></disk>"
 urlattach = url+"/v3/vms/"+bkpid+"/disks/"
 headers = {'Content-Type': 'application/xml', 'Accept': 'application/xml'}
 requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
 resp_attach = requests.post(urlattach, data=xmlattach, headers=headers, verify=False, auth=(user,password))

# Funcion para desactivar disco virtual
# Function to deactivate virtual disk
def deactivate_disk(bkpid,diskid):
 xmldeactivate =  "<action/>"
 urldeactivate = url+"/v3/vms/"+bkpid+"/disks/"+diskid+"/deactivate"
 headers = {'Content-Type': 'application/xml', 'Accept': 'application/xml'}
 resp_attach = requests.post(urldeactivate, data=xmldeactivate, headers=headers, verify=False, auth=(user,password))

# Funcion para desataschar disco de VM
# Function to dettach disk 
def detach_disk(bkpid,diskid):
 urldelete = url+"/vms/"+bkpid+"/diskattachments/"+diskid
 requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
 requests.delete(urldelete, verify=False, auth=(user,password))

# Funcion para obtener el nombre de dispositivo de disco virtual
# Function to get device name of a virtual disk
def get_logical_disk(bkpid,diskid):
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
   disk_service = connection.service(urlget)
   for disk in disk_service.list():
    dev = str(disk.logical_name)
    if disk.id == diskid and str(dev) != "None":
      printf.INFO("Disk found using API")
      b=False
    else:
      dev="None"
      time.sleep(1)
 return dev

def run_qemu_convert(cmd):
 out = subprocess.call(cmd, shell=True)
 if int(out) == 0:
  #print "Se creo correctamente la imagen"
  print
  printf.OK("qcow2 file creation success")
 else:
  print
  printf.ERROR("qcow2 file creation failed")
# Funcion para crear imagen qcow2 del disco
# Function  to create qcow file of disk
def create_image_bkp(dev,diskname):
 bckfiledir = bckdir + "/" + vmname + "/" + date
 mkdir = "mkdir -p " + bckfiledir
 subprocess.call(mkdir, shell=True) 
 bckfile = bckfiledir + "/" + diskname + ".qcow2"
 printf.INFO("Creating qcow2 file: " + bckfile)
 cmd = "qemu-img convert -O qcow2 " + dev + " " +bckfile
 utils=virtbkp_utils.virtbkp_utils()
 thread.start_new_thread(run_qemu_convert,(cmd,))
 utils.progress_bar_qcow(bckfile)
 
# Funcion para obtener el nombre del disco virtual 
# Function to get virtual disk name
def get_disk_name(idvm,snapid,diskid):
 svc_path = "vms/"+idvm+"/snapshots/"+snapid+"/disks/"
 disksnap_service = connection.service(svc_path)
 disks = disksnap_service.list()
 for disk in disks:
  if diskid == str(disk.id):
   return disk.alias

def backup(vmid,snapid,disk_id,bkpvm):
  # Se agrega el disco a la VM que tomara el backup
  printf.INFO("Attach snap disk to bkpvm")
  attach_disk(bkpvm,disk_id,snapid)
  # Se obtiene el nombre del dispositivo
  printf.INFO("Identifying disk device, this might take a while")
  dev = get_logical_disk(bkpvm,disk_id)
  # Se obtiene el nombre del disco
  diskname = get_disk_name(vmid,snapid,disk_id)
  # Se crea la image qcow que seria el  backup como tal
  create_image_bkp(dev,diskname)
  # Se desactiva el disco del cual se hizo el backup
  deactivate_disk(bkpvm,disk_id)
  time.sleep(10)
  # Se detacha el disco de la BKPVM
  printf.INFO("Dettach snap disk of bkpvm")
  detach_disk(bkpvm,disk_id)
  time.sleep(10)



def main():
 ## Parte Principal
 # Se consigue el ID de la VM a la cual se hara backup y la VM donde se montaran sus discos
 global vmid 
 global vmname
 global bkpvm
 vmid = get_id_vm(vmname)
 bkpvm = get_id_vm(bkpvm)
 # Se crea el snap y se espera un rato para que termine sin problemas y pueda detectar el nombre del disco en VM de backup
 create_snap(vmid)
 #time.sleep(60)
 # Se obtiene el id del snap
 snapid = get_snap_id(vmid)
 # Se obtiene el ID del disco
 vm_disks = snap_disk_id(vmid,snapid)
 for disk_id in vm_disks:
   printf.INFO("Trying to create a qcow2 file of disk " + disk_id)
   # Backup
   backup(vmid,snapid,disk_id,bkpvm)
 printf.INFO("Trying to delete snapshot of " + vmname)
 delete_snap(vmid,snapid)
  

main()
