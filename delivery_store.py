# File: delivery_store.py
#
# Backward-compatible bridge for installed delivery automation created before
# the v151 backend package organization. The maintained implementation remains
# in backend.store; no database or business logic is duplicated here.

"""Compatibility exports for the organized scanner data/business layer."""

from backend.store import *  # noqa: F401,F403
