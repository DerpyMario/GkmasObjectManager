from .assetbundle import GkmasAssetBundle
from .resource import GkmasResource

from ..const import GKMAS_UNITY_VERSION

import UnityPy


UnityPy.config.FALLBACK_UNITY_VERSION = GKMAS_UNITY_VERSION
