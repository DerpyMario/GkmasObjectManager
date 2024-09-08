"""
gkmasToolkit
============
Written by Ziyuan Chen (https://github.com/AllenHeartcore/gkmasToolkit_core).
Refactored from Kishida Natsumi (https://github.com/kishidanatsumi/gkmasToolkit),
which in turn was adapted from Vibbit (https://github.com/MalitsPlus/HoshimiToolkit).

This module defines an object-oriented interface for interacting with blob databases
(hereafter referred to as "manifests", usually named "octocacheevai")
in the mobile game Gakuen Idolm@ster (https://gakuen.idolmaster-official.jp/).

Note that "blob" includes both asset bundles and multimedia resources.

Features
--------
- Decrypt and export octocache as raw ProtoDB, JSON, or CSV
- Differentiate between octocache versions
- Download and deobfuscate blobs in parallel

Example Usage
-------------
```python
from gkmasToolkit import GkmasManifest
manifest = GkmasManifest("EncryptedCache/octocacheevai")
manifest.export('DecryptedCache/')
manifest.download('adv.*ttmr.*', 'sud_vo.*fktn.*', 'mdl.*hski.*', nworker=8)

from gkmasToolkit import ALL_ASSETBUNDLES, ALL_RESOURCES
manifest.download(ALL_ASSETBUNDLES, ALL_RESOURCES)

manifest_old = GkmasManifest("EncryptedCache/octocacheevai_old")
mdiff = manifest - manifest_old
mdiff.export('DecryptedCache/diff/')
```
"""

from .manifest import GkmasManifest
from .const import ALL_ASSETBUNDLES, ALL_RESOURCES
