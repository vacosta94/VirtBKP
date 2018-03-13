import subprocess, time, os, sys

class virtbkp_utils:
  qcowfile=None
  def  __init__(self):
    global qcowfile

  def get_qcow_size(self,qcowfile):
    cmd="qemu-img info "+ qcowfile + "|grep 'virtual size'|awk '{print $4}'|sed 's/(//g'"
    size=int(subprocess.check_output(cmd, shell=True))
    return size

  def progress_bar(self,value,endvalue):
    bar_length=50
    percent = float(value) / endvalue
    arrow = '=' * int(round(percent * bar_length)-1) + '>'
    spaces = ' ' * (bar_length - len(arrow))
    bar="\r\033[94mProgress: [{0}]%\033[0m".format(arrow + spaces, int(round(percent * 100)))
    sys.stdout.write(bar + " " + str(round(percent*100,1)) + "%")
    sys.stdout.flush()

  def get_pid_read(self,pid):
    cmd="cat /proc/"+ str(pid) + "/io|awk /read_bytes/'{print $2}'"
    size=int(subprocess.check_output(cmd, shell=True))
    return size

  def pid_qcow_convert(self,qcowfile):
    cmd="ps aux|grep qemu-img|grep -wv grep|grep convert|grep "+ qcowfile + "|awk '{print $2}'"
    pid=int(subprocess.check_output(cmd, shell=True))
    return pid 
 
  def progress_bar_qcow(self,qcowfile):
    time.sleep(3)
    try:
      endvalue=self.get_qcow_size(qcowfile)
      pid=self.pid_qcow_convert(qcowfile) 
      while os.path.isfile("/proc/"+str(pid)+"/io"):
        value=self.get_pid_read(pid)
        self.progress_bar(value,endvalue)
 	time.sleep(0.5)
    except:
      print "ERROR to get process status"
      raise
