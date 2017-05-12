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
  print "Se ha conectado correctamente a: %s" % url 
except Exception as ex:
  print "Unexpected error: %s" % ex
  
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
 while str(status) == "locked":
    time.sleep(10)
    print "Esperando a que termine el snapshot.."
    status = get_snap_status(idvm,snapid)

# Funcion para eliminar el snapshot
# Function to delte snapshot
def delete_snap(idvm,snapid):
 snap_service = connection.service("vms/"+idvm+"/snapshots/"+snapid)
 snap_service.remove()
 status = get_snap_status(idvm,snapid)
 while str(status) == "locked":
    time.sleep(30)
    print "Esperando a que termine de eliminar el snapshot.."
    status = get_snap_status(idvm,snapid)

# Funcion para obtener el ID del disco de snapshot
# Function to get snapshost disk ID
def snap_disk_id(idvm,snapid):
 svc_path = "vms/"+idvm+"/snapshots/"+snapid+"/disks/"
 disksnap_service = connection.service(svc_path)
 disks = disksnap_service.list()
 for disk in disks:
  return  disk.id

# Funcion para atachar disco a VM
# Function to attach disk to VM
def attach_disk(bkpid,diskid,snapid):
 xmlattach =  "<disk id=\""+diskid+"\"><snapshot id=\""+snapid+"\"/> <active>true</active></disk>"
 urlattach = url+"/v3/vms/"+bkpid+"/disks/"
 headers = {'Content-Type': 'application/xml', 'Accept': 'application/xml'}
 requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
 resp_attach = requests.post(urlattach, data=xmlattach, headers=headers, verify=ca_file, auth=(user,password))

# Funcion para desactivar disco virtual
# Function to deactivate virtual disk
def deactivate_disk(bkpid,diskid):
 xmldeactivate =  "<action/>"
 urldeactivate = url+"/v3/vms/"+bkpid+"/disks/"+diskid+"/deactivate"
 headers = {'Content-Type': 'application/xml', 'Accept': 'application/xml'}
 resp_attach = requests.post(urldeactivate, data=xmldeactivate, headers=headers, verify=ca_file, auth=(user,password))

# Funcion para desataschar disco de VM
# Function to dettach disk 
def detach_disk(bkpid,diskid):
 urldelete = url+"/vms/"+bkpid+"/diskattachments/"+diskid
 requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
 requests.delete(urldelete, verify=ca_file, auth=(user,password))

# Funcion para obtener el nombre de dispositivo de disco virtual
# Function to get device name of a virtual disk
def get_logical_disk(bkpid,diskid):
 dev="None"
 print "Obteniendo lista de discos de bkpvm"
 print "Esperando para detectar el nombre del dispositivo"
 while str(dev) == "None":
  urlget = "vms/"+bkpid+"/diskattachments/"
  disk_service = connection.service(urlget)
  for disk in disk_service.list():
   dev = str(disk.logical_name)
   if disk.id == diskid and str(dev) != "None":
     print str(dev)
     return str(dev)
   else:
     sys.stdout.write(".")
     dev="None"
     time.sleep(1)

# Funcion para crear imagen qcow2 del disco
# Function  to create qcow file of disk
def create_image_bkp(dev):
 bckfile= bckdir + "/" + vmname + "_" + date +"h.qcow2"
 print "Se procede a crear la imagen qcow2 " + bckfile
 cmd = "qemu-img convert -O qcow2 " + dev + " " +bckfile
 out = subprocess.call(cmd, shell=True)
 if int(out) == 0:
  print "Se creo correctamente la imagen"
  print "Se procede a eliminar el snapshot"
 else:
  print "ERROR al crear la imagen"
  print "Se procede a eliminar el snapshot"

def main():
 ## Parte Principal
 # Se consigue el ID de la VM a la cual se hara backup y la VM donde se montaran sus discos
 global vmid 
 global vmname
 global bkpvm
 vmid = get_id_vm(vmname)
 print bkpvm
 bkpvm = get_id_vm(bkpvm)
 print bkpvm
 print vmid
 # Se crea el snap y se espera un rato para que termine sin problemas y pueda detectar el nombre del disco en VM de backup
 create_snap(vmid)
 time.sleep(60)
 # Se obtiene el id del snap
 snapid = get_snap_id(vmid)
 # Se obtiene el ID del disco
 disk_id = snap_disk_id(vmid,snapid)
 # Se agrega el disco a la VM que tomara el backup
 attach_disk(bkpvm,disk_id,snapid)
 # Se obtiene el nombre del dispositivo
 dev = get_logical_disk(bkpvm,disk_id)
 # Backup
 create_image_bkp(dev)
 deactivate_disk(bkpvm,disk_id)
 time.sleep(10)
 detach_disk(bkpvm,disk_id)
 time.sleep(10)
 delete_snap(vmid,snapid)
  

main()
