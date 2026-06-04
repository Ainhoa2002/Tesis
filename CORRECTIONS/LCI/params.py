"""Compatibility shim re-exporting parameter library helpers.

This module provides a thin compatibility layer that exposes commonly used
parameter-library functions under the legacy `params` module name.
"""

from parameter_library import (
    delete_param,
    get_execution_scope,
    get_param,
    list_params,
    load_document,
    save_document,
    set_execution_scope,
    set_param,
)

__all__ = [
    "delete_param",
    "get_execution_scope",
    "get_param",
    "list_params",
    "load_document",
    "save_document",
    "set_execution_scope",
    "set_param",
]
