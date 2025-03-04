# Copyright 2023 BentoML Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Some imports utils are vendorred from transformers/utils/import_utils.py for performance reasons.
"""
from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import logging
import os
import typing as t
from abc import ABCMeta
from collections import OrderedDict

import inflection
from packaging import version

from bentoml._internal.utils import LazyLoader
from bentoml._internal.utils import pkg


if t.TYPE_CHECKING:
    BackendOrderredDict = OrderedDict[str, tuple[t.Callable[[], bool], str]]
else:
    BackendOrderredDict = OrderedDict

logger = logging.getLogger(__name__)

OPTIONAL_DEPENDENCIES = {"fine-tune", "flan-t5", "openai", "agents"}
ENV_VARS_TRUE_VALUES = {"1", "ON", "YES", "TRUE"}
ENV_VARS_TRUE_AND_AUTO_VALUES = ENV_VARS_TRUE_VALUES.union({"AUTO"})

USE_TF = os.environ.get("USE_TF", "AUTO").upper()
USE_TORCH = os.environ.get("USE_TORCH", "AUTO").upper()
USE_JAX = os.environ.get("USE_FLAX", "AUTO").upper()

FORCE_TF_AVAILABLE = os.environ.get("FORCE_TF_AVAILABLE", "AUTO").upper()


def _is_package_available(package: str) -> bool:
    _package_available = importlib.util.find_spec(package) is not None
    if _package_available:
        try:
            importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            _package_available = False
    return _package_available


_torch_available = importlib.util.find_spec("torch") is not None
_tf_available = importlib.util.find_spec("tensorflow") is not None
_flax_available = importlib.util.find_spec("jax") is not None and importlib.util.find_spec("flax") is not None
_einops_available = _is_package_available("einops")
_cpm_kernel_available = _is_package_available("cpm_kernels")
_bitsandbytes_available = _is_package_available("bitsandbytes")


def is_transformers_supports_kbit() -> bool:
    return pkg.pkg_version_info("transformers")[:2] >= (4, 30)


def is_transformers_supports_agent() -> bool:
    return pkg.pkg_version_info("transformers")[:2] >= (4, 29)


def is_einops_available():
    return _einops_available


def is_cpm_kernels_available():
    return _cpm_kernel_available


def is_bitsandbytes_available():
    return _bitsandbytes_available


def is_torch_available():
    global _torch_available
    if USE_TORCH in ENV_VARS_TRUE_AND_AUTO_VALUES and USE_TF not in ENV_VARS_TRUE_VALUES:
        if _torch_available:
            try:
                importlib.metadata.version("torch")
            except importlib.metadata.PackageNotFoundError:
                _torch_available = False
    else:
        logger.info("Disabling PyTorch because USE_TF is set")
        _torch_available = False
    return _torch_available


def is_tf_available():
    global _tf_available
    if FORCE_TF_AVAILABLE in ENV_VARS_TRUE_VALUES:
        _tf_available = True
    else:
        _tf_version = None
        if USE_TF in ENV_VARS_TRUE_AND_AUTO_VALUES and USE_TORCH not in ENV_VARS_TRUE_VALUES:
            if _tf_available:
                candidates = (
                    "tensorflow",
                    "tensorflow-cpu",
                    "tensorflow-gpu",
                    "tf-nightly",
                    "tf-nightly-cpu",
                    "tf-nightly-gpu",
                    "intel-tensorflow",
                    "intel-tensorflow-avx512",
                    "tensorflow-rocm",
                    "tensorflow-macos",
                    "tensorflow-aarch64",
                )
                _tf_version = None
                # For the metadata, we have to look for both tensorflow and tensorflow-cpu
                for _pkg in candidates:
                    try:
                        _tf_version = importlib.metadata.version(_pkg)
                        break
                    except importlib.metadata.PackageNotFoundError:
                        pass
                _tf_available = _tf_version is not None
            if _tf_available:
                if _tf_version and version.parse(_tf_version) < version.parse("2"):
                    logger.info(f"TensorFlow found but with version {_tf_version}. OpenLLM only supports TF 2.x")
                    _tf_available = False
        else:
            logger.info("Disabling Tensorflow because USE_TORCH is set")
            _tf_available = False
    return _tf_available


def is_flax_available():
    global _flax_available
    if USE_JAX in ENV_VARS_TRUE_AND_AUTO_VALUES:
        if _flax_available:
            try:
                importlib.metadata.version("jax")
                importlib.metadata.version("flax")
            except importlib.metadata.PackageNotFoundError:
                _flax_available = False
    else:
        _flax_available = False
    return _flax_available


PYTORCH_IMPORT_ERROR_WITH_TF = """\
{0} requires the PyTorch library but it was not found in your environment.
However, we were able to find a TensorFlow installation. TensorFlow classes begin
with "TF", but are otherwise identically named to the PyTorch classes. This
means that the TF equivalent of the class you tried to import would be "TF{0}".
If you want to use TensorFlow, please use TF classes instead!

If you really do want to use PyTorch please go to
https://pytorch.org/get-started/locally/ and follow the instructions that
match your environment.
"""

TF_IMPORT_ERROR_WITH_PYTORCH = """\
{0} requires the TensorFlow library but it was not found in your environment.
However, we were able to find a PyTorch installation. PyTorch classes do not begin
with "TF", but are otherwise identically named to our TF classes.
If you want to use PyTorch, please use those classes instead!

If you really do want to use TensorFlow, please follow the instructions on the
installation page https://www.tensorflow.org/install that match your environment.
"""

TENSORFLOW_IMPORT_ERROR = """{0} requires the TensorFlow library but it was not found in your environment.
Checkout the instructions on the installation page: https://www.tensorflow.org/install and follow the
ones that match your environment. Please note that you may need to restart your runtime after installation.
"""


FLAX_IMPORT_ERROR = """{0} requires the FLAX library but it was not found in your environment.
Checkout the instructions on the installation page: https://github.com/google/flax and follow the
ones that match your environment. Please note that you may need to restart your runtime after installation.
"""

PYTORCH_IMPORT_ERROR = """{0} requires the PyTorch library but it was not found in your environment.
Checkout the instructions on the installation page: https://pytorch.org/get-started/locally/ and follow the
ones that match your environment. Please note that you may need to restart your runtime after installation.
"""

CPM_KERNELS_IMPORT_ERROR = """{0} requires the cpm_kernels library but it was not found in your environment.
You can install it with pip: `pip install cpm_kernels`. Please note that you may need to restart your
runtime after installation.
"""

EINOPS_IMPORT_ERROR = """{0} requires the einops library but it was not found in your environment.
You can install it with pip: `pip install einops`. Please note that you may need to restart
your runtime after installation.
"""

BACKENDS_MAPPING = BackendOrderredDict(
    [
        ("flax", (is_flax_available, FLAX_IMPORT_ERROR)),
        ("tf", (is_tf_available, TENSORFLOW_IMPORT_ERROR)),
        ("torch", (is_torch_available, PYTORCH_IMPORT_ERROR)),
        ("cpm_kernels", (is_cpm_kernels_available, CPM_KERNELS_IMPORT_ERROR)),
        ("einops", (is_einops_available, EINOPS_IMPORT_ERROR)),
    ]
)


class DummyMetaclass(ABCMeta):
    """Metaclass for dummy object. It will raises ImportError
    generated by ``require_backends`` if users try to access attributes from given class
    """

    _backends: t.List[str]

    def __getattribute__(cls, key: str) -> t.Any:
        if key.startswith("_"):
            return super().__getattribute__(key)
        require_backends(cls, cls._backends)


def require_backends(o: t.Any, backends: t.MutableSequence[str]):
    if not isinstance(backends, (list, tuple)):
        backends = list(backends)

    name = o.__name__ if hasattr(o, "__name__") else o.__class__.__name__

    # Raise an error for users who might not realize that classes without "TF" are torch-only
    if "torch" in backends and "tf" not in backends and not is_torch_available() and is_tf_available():
        raise ImportError(PYTORCH_IMPORT_ERROR_WITH_TF.format(name))

    # Raise the inverse error for PyTorch users trying to load TF classes
    if "tf" in backends and "torch" not in backends and is_torch_available() and not is_tf_available():
        raise ImportError(TF_IMPORT_ERROR_WITH_PYTORCH.format(name))

    checks = (BACKENDS_MAPPING[backend] for backend in backends)
    failed = [msg.format(name) for available, msg in checks if not available()]
    if failed:
        raise ImportError("".join(failed))


class ModelEnv:
    model_name: str

    if t.TYPE_CHECKING:
        config: property
        model_id: property
        quantize: property
        framework: property
        bettertransformer: property

        framework_value: property
        quantize_value: property
        bettertransformer_value: property

    def __getitem__(self, item: str | t.Any) -> t.Any:
        if hasattr(self, item):
            return getattr(self, item)
        raise KeyError(f"Key {item} not found in {self}")

    def __new__(cls, model_name: str, bettertransformer: bool | None = None, quantize: t.LiteralString | None = None):
        from .._configuration import _field_env_key
        from . import codegen

        model_name = inflection.underscore(model_name)

        res = super().__new__(cls)
        res.model_name = model_name

        # gen properties env key
        attributes = {"config", "model_id", "quantize", "framework", "bettertransformer"}
        for att in attributes:
            setattr(res, att, _field_env_key(model_name, att.upper()))

        # gen properties env value
        attributes_with_values = {
            "quantize": (bool, quantize),
            "bettertransformer": (bool, bettertransformer),
            "framework": (str, "pt"),
        }
        globs: dict[str, t.Any] = {
            "__bool_vars_value": ENV_VARS_TRUE_VALUES,
            "__env_get": os.environ.get,
            "self": res,
        }

        for attribute, (default_type, default_value) in attributes_with_values.items():
            lines: list[str] = []
            if default_type is bool:
                lines.append(
                    f"return str(__env_get(self['{attribute}'], str(__env_default)).upper() in __bool_vars_value)"
                )
            else:
                lines.append(f"return __env_get(self['{attribute}'], __env_default)")

            setattr(
                res,
                f"{attribute}_value",
                codegen.generate_function(
                    cls,
                    "_env_get_" + attribute,
                    lines,
                    ("__env_default",),
                    globs,
                )(default_value),
            )

        return res

    @property
    def start_docstring(self) -> str:
        return getattr(self.module, f"START_{self.model_name.upper()}_COMMAND_DOCSTRING")

    @property
    def module(self) -> LazyLoader:
        return LazyLoader(self.model_name, globals(), f"openllm.models.{self.model_name}")
