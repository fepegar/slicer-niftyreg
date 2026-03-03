# NiftyReg

[3D Slicer](https://www.slicer.org/) module as a GUI for [`NiftyReg`](https://github.com/KCL-BMEIS/niftyreg), an open-source software for efficient medical image registration developed by [Marc Modat](https://github.com/mmodat) at King's College London.

In a terminal, run:
```
mkdir ~/git
cd ~/git
git clone https://github.com/fepegar/slicer-niftyreg.git
mkdir ~/bin
cd ~/bin
ln -s $(which reg_aladin)
ln -s $(which reg_f3d)
```


In `~/.slicerrc.py`:

```
from pathlib import Path
import qt

moduleFactory = slicer.app.moduleManager().factoryManager()
 
dirs = [Path('~/git/slicer-niftyreg').expanduser()]

dirs = [d for d in dirs if d.is_dir()]

for d in dirs:
    for fp in d.glob('*.py'):
        moduleFactory.registerModule(qt.QFileInfo(str(fp)))
        moduleFactory.loadModules([fp.stem])
```


