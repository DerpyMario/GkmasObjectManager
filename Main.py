from gkmasToolkit.manifest import GkmasManifest
from gkmasToolkit.utils import ALL_ASSETBUNDLES, ALL_RESOURCES


manifest = GkmasManifest("EncryptedCache/octocacheevai")
manifest.export("DecryptedCache/")
manifest.download(ALL_ASSETBUNDLES, ALL_RESOURCES)
