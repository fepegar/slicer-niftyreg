# NiftyReg

[3D Slicer](https://www.slicer.org/) module as a GUI for [`NiftyReg`](http://cmictig.cs.ucl.ac.uk/wiki/index.php/NiftyReg), an open-source software for efficient medical image registration developed by [Marc Modat](http://cmic.cs.ucl.ac.uk/staff/marc_modat/) at the University College London.

In a terminal, run:
```
mkdir ~/git
cd ~/git
git clone https://github.com/fepegar/slicer-niftyreg.git
mkdir ~/bin
ln -s $(which reg_aladin) ~/bin
ln -s $(which reg_f3d) ~/bin
```


In `~/.slicerrc.py`:

```
import os
import qt

moduleFactory = slicer.app.moduleManager().factoryManager()
 
dirs = ['~/git/slicer-niftyreg']

dirs = filter(os.path.isdir, [os.path.expanduser(d) for d in dirs])

for d in dirs:
    for fn in os.listdir(d):
        if not fn.endswith('.py'):
            continue
        fp = os.path.join(d, fn)
        moduleFactory.registerModule(qt.QFileInfo(fp))
        moduleFactory.loadModules([os.path.splitext(fn)[0]])
```


