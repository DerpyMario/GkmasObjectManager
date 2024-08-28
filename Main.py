from MaskedHeaderStream import unObfuscate, rename
from Downloader import download

from gkmasToolkit.manifest import GkmasManifest


global output_dir
output_dir = "./gkmas"

download_asset = 1
download_resource = 0

manifest = GkmasManifest("EncryptedCache/octocacheevai")
manifest.export("DecryptedCache/")

# download(jDict, output_dir, download_asset, download_resource)
# unObfuscate(jDict)
# rename(jDict)
