#!/bin/python
import subprocess
import logging
import os
import ovirtsdk4 as sdk
import ovirtsdk4.types as types
import ssl
import ConfigParser
import sys
import time
import virtbkp_utils

from urlparse import urlparse
from httplib import HTTPSConnection
cfg = ConfigParser.ConfigParser()
cfg.readfp(open(sys.argv[1]))
url=cfg.get('restore', 'url')
user=cfg.get('restore', 'user')
password=cfg.get('restore', 'password')
ca_file=cfg.get('restore', 'ca_file')
storagedomain=cfg.get('restore', 'storage')
proxy=cfg.get('restore', 'proxy')
proxyport=cfg.get('restore', 'proxyport')

qcowfile=sys.argv[2]

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



system_service = connection.system_service()

# 1. The disk size is indicated using the 'provisioned_size' attribute,
#    but due to current limitations in the engine, the 'initial_size'
#    attribute also needs to be explicitly provided for _copy on write_
#    disks created on block storage domains, so that all the required
#    space is allocated upfront, otherwise the upload will eventually
#    fail.
#
# 2. The disk initial size must be bigger or the same as the size of the data
#    you will upload.
#cmd="qemu-img info "+ qcowfile + "|grep 'virtual size'|awk '{print $4}'|sed 's/(//g'"
#size=int(subprocess.check_output(cmd, shell=True))
utils = virtbkp_utils.virtbkp_utils()
provisioned_size = utils.get_qcow_size(qcowfile)

disks_service = connection.system_service().disks_service()
disk = disks_service.add(
    disk=types.Disk(
        name=qcowfile,
        description=qcowfile,
        format=types.DiskFormat.COW,
        provisioned_size=provisioned_size,
        storage_domains=[
            types.StorageDomain(
                name=storagedomain
            )
        ]
    )
)

# Wait till the disk is up, as the transfer can't start if the
# disk is locked:
disk_service = disks_service.disk_service(disk.id)
while True:
    time.sleep(5)
    disk = disk_service.get()
    if disk.status == types.DiskStatus.OK:
        break

# Get a reference to the service that manages the image
# transfer that was added in the previous step:
transfers_service = system_service.image_transfers_service()

# Add a new image transfer:
transfer = transfers_service.add(
    types.ImageTransfer(
        image=types.Image(
            id=disk.id
        )
     )
)

# Get reference to the created transfer service:
transfer_service = transfers_service.image_transfer_service(transfer.id)

# After adding a new transfer for the disk, the transfer's status will be INITIALIZING.
# Wait until the init phase is over. The actual transfer can start when its status is "Transferring".
while transfer.phase == types.ImageTransferPhase.INITIALIZING:
    time.sleep(1)
    transfer = transfer_service.get()

# Set needed headers for uploading:
upload_headers = {
    'Authorization': transfer.signed_ticket,
}

# At this stage, the SDK granted the permission to start transferring the disk, and the
# user should choose its preferred tool for doing it - regardless of the SDK.
# In this example, we will use Python's httplib.HTTPSConnection for transferring the data.
proxy_url = urlparse(transfer.proxy_url)
context = ssl.create_default_context()

# Note that ovirt-imageio-proxy by default checks the certificates, so if you don't have
# your CA certificate of the engine in the system, you need to pass it to HTTPSConnection.
context.load_verify_locations(cafile=ca_file)

proxy_connection = HTTPSConnection(
    proxy,
    proxyport,
    context=context,
)

path = qcowfile
MiB_per_request = 100
with open(path, "rb") as disk:
    size = os.path.getsize(path)
    chunk_size = 1024 * 1024 * MiB_per_request
    pos = 0
    while pos < size:
        # Extend the transfer session.
        transfer_service.extend()
        # Set the content range, according to the chunk being sent.
        upload_headers['Content-Range'] = "bytes %d-%d/%d" % (pos, min(pos + chunk_size, size) - 1, size)
        # Perform the request.
        proxy_connection.request(
            'PUT',
            proxy_url.path,
            disk.read(chunk_size),
            headers=upload_headers,
        )
        # Print response
        r = proxy_connection.getresponse()
        print r.status, r.reason, "Completed", "{:.0%}".format(pos / float(size))
        # Continue to next chunk.
        pos += chunk_size


print "Completed", "{:.0%}".format(pos / float(size))
# Finalize the session.
transfer_service.finalize()

# Close the connection to the server:
connection.close()
