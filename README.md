## Python tool to create full oVirt VM disk Backup

*version 0.1*
Limitations:
- Works only with VMs with just 1 disk

#### Glosary
- BKPVM: oVirt VM where the process starts and the qcow file are stored
- VM: oVirt VM we need backup of

#### Process
![Process Flow](http://git.infratic.com/Python/VirtBKP/raw/master/process_flow.jpg)
- This script should run on a oVirt VM, and it need access to VM's Storage domain
- After snapshot creation it attach VM's disk to BKPVM in order to create qcow file 

#### Dependencies
- 1 VM on the same cluster with qemu-img and ovirt-python-sdk installed <--- BKPVM
- BKPVM need access to VM's Storage Domain

# Install

## *BKPVM*

#### Install dependencies
```
yum install -y qemu-img python-ovirt-engine-sdk4 python-requests
```
#### Get source code
```
cd /opt
git clone http://git.infratic.com/Python/VirtBKP.git
```

#### Create VM Backup
*First you need to get your ovirt CA certificate*
```
cd /opt/VirtBKP
wget https://ovirt.example.com/ovirt-engine/services/pki-resource?resource=ca-certificate&format=X509-PEM-CA
```
*Edit default.conf*
*Create Backup of foreman VM*
```
python backup_vm.py default.conf foreman
```
*Restore disk*
```
python upload_disk.py upload_disk.py
```