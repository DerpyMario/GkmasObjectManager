from gkmasToolkit.manifest import GkmasManifest
from gkmasToolkit.utils import ASSETBUNDLES, RESOURCES


manifest = GkmasManifest("EncryptedCache/octocacheevai")
manifest.export("DecryptedCache/")
manifest.download_all([ASSETBUNDLES, RESOURCES])
