"""Errors raised by services.

The message of every ServiceError is safe to show to the Discord user who ran
the command; the command layer sends it back as an ephemeral reply.
"""


class ServiceError(Exception):
    pass


class PermissionDenied(ServiceError):
    pass


class NotFound(ServiceError):
    pass


class InvalidRequest(ServiceError):
    pass


class DiscordSyncError(ServiceError):
    """Discord rejected a role change. The database change was rolled back."""
