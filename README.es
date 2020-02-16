# Crear backup de maquinas virtuales oVirt/RHEV >= 4 v1.2
[TOC]
## Introduccion
Vengo trabajando con oVirt desde la version 3.5 como plataforma de virtualizacion tanto para ambientes de laboratorio, ambientes de produccion y hasta este mismo sitio, desde el inicio busque una forma facil de crear backups de maquinas virtuales basadas en `snapshots`, luego de investigar encontre de que existia una `API` pensada para realizar backups de maquinas virtuales, investigando un poco mas encontre scripts que permitian exportar maquinas virtuales de forma a tener un respaldo de las mismas.

Si bien esa solucion me sirvio durante mucho tiempo, rapidamente se volvio muy poco practica a medida que las maquinas virtuales que alojaba crecian, por el simple hecho de que esta solucion necesitaba 3 veces el tamaño de tu maquina virtual debido a que antes de exportar la maquina, la debe clonar.

Una vez que el espacio se volvio un problema decidi, crear mi propio script de backup para maquinas virtuales sobre oVirt.

El proceso es quizas un poco mas complejo que la solucion que acabo de comentar pero necesito menos espacio en disco!. En este documento detallare como funciona y como utilizar la herramienta que cree, espero que le sirva a alguien.

## Como funciona
### Requisitos
Los requisitos para utilizar esta solucion son los siguientes:
- oVirt >= 4.0
- Una maquina virtual CentOS 7 a la que llamaremos `bkpvm`
- Esta maquina virtual debe estar en el mismo `Datacenter` que las VMs a las que queremos respaldar
- Esta maquina virtual debe tener espacio suficiente para copiar el disco virtual de las VMs

### Que hace exactamente
El script se debe ejecutar en la `bkpvm` y la misma debe poder acceder a los dominios de almacenamiento donde estan los discos de las maquinas que queremos respaldar.
Los pasos que ejecuta el `script` son los siguientes:
- Se conecta a la `API` de oVirt
- Crea un `snapshot` de la maquina que queremos respaldar
- Adjunta el disco del `snapshot` a la `bkpvm`
- Crea una imagen `qcow2` del disco en cuestion
- Elimina el snapshot
- Se desconecta de la `API` de oVirt

Al terminar en forma de *respaldo* nos queda un archivo `qcow2` que no es mas que *el disco de la maquina virtual*, este archivo lo podemos luego subir al oVirt.

## Descargar y utilizar la herramienta
#### Descargar
Una vez que tenemos nuestra `bkpvm` instalada debemos instalar un par de paquetes que utiliza el script
Primero debemos habilitar epel y el repositorio de oVirt
```bash
yum install -y epel-release
yum install -y http://resources.ovirt.org/pub/yum-repo/ovirt-release43.rpm 

```
Luego instalamos las librerias necesarias de python 
```bash
yum install -y qemu-img python-ovirt-engine-sdk4 python-requests git ovirt-guest-agent

```
Luego descargamos la ultima version de la herramienta 
```bash
cd /opt
git clone https://github.com/vacosta94/VirtBKP.git
```
Obtener `CA` de nuestro `oVirt`, deben reemplazar `ovirt.example.com` por la url de acceso de su oVirt
```bash
cd /opt/VirtBKP
curl --insecure "https://ovirt.example.com/ovirt-engine/services/pki-resource?resource=ca-certificate&format=X509-PEM-CA" -o ca.crt
```
#### Configurar
Dentro de la carpeta `VirtBKP` existe un archivo llamado `default.conf`, ese archivo es el ejemplo de configuracion que utiliza la herramienta, deben modificar ese archivo con sus datos de acceso, el archivo debe quedar de la siguiente forma:
```bash 
vim /opt/VirtBKP/default.conf
```
```python
[bkp]
url		= https://ovirt.example.com/ovirt-engine/api
user		= admin@internal
password	= password
ca_file		= ca.crt
bkpvm		= bkpvm
bckdir 		= /mnt/

[restore]
url		= https://ovirt.example.com/ovirt-engine/api
user		= admin@internal
password	= password
ca_file		= ca.crt
storage		= gfs_pool0
proxy		= ovirt.example.com
proxyport	= 54323
```
- `url` Es la URL de nuestro oVirt
- `user` El usuario a utilizar para las tareas de backup
- `password` Password de dicho usuario
- `ca_file` Ruta del `ca.crt` que descargamos anteriormente
- `bkpvm` Nombre de la maquina virtual que creara los backups, este nombre debe ser el nombre que se ve en el portal de administracion de oVirt
- `bckdir` Directorio donde se almacenaran los archivos `.qcow2` 
- `storage` Dominio de almacenamiento donde se restaurara la imagen `.qcow2`, este nombre debe ser el nombre que se ve en el portal de administracion de oVirt
- `proxy` Equipo que se utilizara como proxy para restaurar la imagen `qcow2`
- `proxyport` Puerto de dicho proxy 54323 es el puerto por defecto del `ovirt-image-io-proxy`

#### Crear backup
Para crear backups de maquinas virtuales la sintaxis es la siguiente
```bash
/opt/VirtBKP/backup_vm.py <archivo_conf> <nombre_vm_respaldar>
```
Por ejemplo para crear un backup de una VM de nombre `webserver` utilizando la configuracion cargada en el archivo `default.conf`
```bash
/opt/VirtBKP/backup_vm.py /opt/VirtBKP/default.conf webserver
```

#### Restaurar backup
Para restaurar un backup la sintaxis en la siguiente
```bash
/opt/VirtBKP/upload_disk.py <archivo_conf> <archivo_qcow2>
```
El archivo `qcow2` es el archivo que se creo durante la tarea de respaldo, por ejemplo si el archivo se encuentra en `/mnt/webserver_2017-04-28-00h.qcow2`
```bash
/opt/VirtBKP/upload_disk.py /opt/VirtBKP/default.conf /mnt/webserver_2017-04-28-00h.qcow2

```
