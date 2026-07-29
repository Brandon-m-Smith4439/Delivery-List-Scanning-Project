# File: scanner_config.py
#
# Backward-compatible bridge for installed delivery automation created before
# the v151 backend package organization. New application code imports
# backend.config directly; this file only preserves old automation entry points.

"""Compatibility exports for the organized scanner configuration module."""

from backend.config import AppConfig, load_config

__all__ = ["AppConfig", "load_config"]
