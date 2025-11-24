import sys

if sys.version_info[:2] >= (3, 8):
    # TODO: Import directly (no need for conditional) when `python_requires = >= 3.8`
    from importlib.metadata import PackageNotFoundError, version  # pragma: no cover
else:
    from importlib_metadata import PackageNotFoundError, version  # pragma: no cover

try:
    # Change here if project is renamed and does not equal the package name
    dist_name = __name__
    __version__ = version(dist_name)
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"
finally:
    del version, PackageNotFoundError

# 导出配置类
from pisa.config import Config
from pisa.startup import initialize_pisa, validate_system_ready, quick_start

__all__ = [
    "__version__",
    "Config",
    "initialize_pisa",
    "validate_system_ready",
    "quick_start"
]
