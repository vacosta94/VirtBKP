#!/bin/python
import sys 

from backup_vm_last import backup_vm
b = backup_vm(sys.argv[1],sys.argv[2],sys.argv[3])
b.main()

