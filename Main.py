from gkmasToolkit import GkmasManifest, ALL_ASSETBUNDLES, ALL_RESOURCES


manifest = GkmasManifest("EncryptedCache/octocacheevai")
manifest.export("DecryptedCache/")
manifest.download(ALL_ASSETBUNDLES, ALL_RESOURCES)
