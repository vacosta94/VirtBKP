# en
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