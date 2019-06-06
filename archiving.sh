#!/bin/bash

# This script is an example to configure archiving for backups,
# this is very usefull to configure backup to be stored in a fast drive
# then be moved to a slower drive that can be a deduplicated volume
days=1
hotdir=/ovirt_backup
colddir=/backup/ovirt_backup/ 
directories=$(find $hotdir -mtime +$days -type d | sed "s@$hotdir@@g")
for dir in $directories
 do 
  mkdir -p $colddir/$dir 2>/dev/null
  mv -v $hotdir/$dir/* $colddir/$dir 
  # echo $dir
  # mkdir -p /backup/ovirt_backup/a
done
