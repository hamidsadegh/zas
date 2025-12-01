import logging
import socket
from typing import Iterable, Tuple

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db import transaction

from accounts.services.settings_service import get_system_settings

User = get_user_model()
log = logging.getLogger(__name__)


class IseTacacsBackend(ModelBackend):
    """
    Authenticate users against Cisco ISE via TACACS+ and keep a local shadow user.

    Behaviour:
    - If TACACS+ is disabled in SystemSettings → fall back to Django's default auth.
    - If TACACS+ network call fails (timeouts / connection errors) → fall back so
      local superusers can still log in.
    - On successful TACACS+ auth a local user is created/updated and its password
      is marked unusable to ensure TACACS is the source of truth.
    - On TACACS+ explicit deny we DO NOT fall back, unless the operator has enabled
      `allow_local_superusers`.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        config = get_system_settings()
        if not config.tacacs_enabled:
            return super().authenticate(request, username=username, password=password, **kwargs)

        try:
            ok, groups = self._tacacs_auth(
                username=username,
                password=password,
                host=config.tacacs_server_ip,
                port=config.tacacs_port,
                secret=config.tacacs_key,
                timeout=config.tacacs_session_timeout or 60,
                service=config.tacacs_authorization_service or "shell",
                retries=max(1, config.tacacs_retries or 1),
            )
        except (TimeoutError, ConnectionError, socket.timeout, OSError) as exc:
            log.warning("TACACS+ unreachable, falling back to local auth: %s", exc)
            return super().authenticate(request, username=username, password=password, **kwargs)

        if ok:
            return self._sync_shadow_user(username, groups, config)

        # TACACS explicitly rejected the credentials.
        if config.allow_local_superusers:
            try:
                local = User.objects.get(username=username, is_superuser=True)
            except User.DoesNotExist:
                local = None
            if local and local.check_password(password):
                return local

        return None

    def _sync_shadow_user(self, username: str, groups: Iterable[str], config) -> User:
        groups = groups or []
        with transaction.atomic():
            user, _ = User.objects.get_or_create(username=username, defaults={"is_active": True})

            # if config.tacacs_admin_group and config.tacacs_admin_group in groups:
            #     user.is_staff = True
            # if config.tacacs_superuser_group and config.tacacs_superuser_group in groups:
            #     user.is_superuser = True
            user.is_staff = True  # TACACS+ users are always staff

            user.is_active = True
            user.set_unusable_password()
            user.save()
            return user

    def _tacacs_auth(
        self,
        username: str,
        password: str,
        host: str,
        port: int,
        secret: str,
        timeout: int,
        service: str,
        retries: int = 1,
    ) -> Tuple[bool, Iterable[str]]:
        """
        Returns (ok, groups). Raises ConnectionError/TimeoutError on network issues.
        """
        if not host or not secret:
            raise ConnectionError("TACACS+ host or key missing from System Settings")

        last_error = None

        for attempt in range(max(1, retries)):
            try:
                from tacacs_plus.client import TACACSClient
                from tacacs_plus.flags import TAC_PLUS_AUTHEN_TYPE_ASCII

                client = TACACSClient(host, port, secret, timeout)
                try:
                    result = client.authenticate(
                        username,
                        password,
                        authen_type=TAC_PLUS_AUTHEN_TYPE_ASCII,
                    )
                except TypeError:
                    # Older tacacs_plus versions may not accept `service`
                    result = client.authenticate(
                        username,
                        password,
                        authen_type=TAC_PLUS_AUTHEN_TYPE_ASCII,
                    )

                ok = self._normalize_status(result)
                if not ok:
                    return False, []

                # Authorization step (optional). Not all deployments expose AV pairs.
                groups = self._fetch_groups(client, username, service)
                return True, groups

            except socket.timeout as exc:
                last_error = TimeoutError(str(exc))
            except Exception as exc:  # pylint: disable=broad-except
                last_error = ConnectionError(str(exc))

        if last_error:
            raise last_error
        raise ConnectionError("Unknown TACACS+ error")

    @staticmethod
    def _normalize_status(result) -> bool:
        """
        Return True only for explicit PASS/OK responses from the TACACS+ client.
        """
        # Result objects with a status attribute (common in tacacs_plus)
        status = getattr(result, "status", None)
        if status is not None:
            if isinstance(status, str):
                return status.upper() in {"PASS", "OK", "ACCEPT", "ACCEPTED", "SUCCESS"}
            try:
                return int(status) == 1  # TAC_PLUS_AUTHEN_STATUS_PASS
            except (TypeError, ValueError):
                return False

        # Tuple/list responses, e.g. (status, session_id)
        if isinstance(result, (tuple, list)) and result:
            first = result[0]
            if isinstance(first, str):
                return first.upper() in {"PASS", "OK", "ACCEPT", "ACCEPTED", "SUCCESS"}
            try:
                return int(first) == 1
            except (TypeError, ValueError):
                return False

        # Fallback: only truthy booleans should pass
        return result is True

    def _fetch_groups(self, client, username: str, service: str) -> Iterable[str]:
        """
        Attempt to pull AV pairs via authorize() to extract ISE role mappings.
        Not all TACACS+ clients expose this; swallow errors silently.
        """
        try:
            # Many TACACS+ deployments encode roles in cisco-av-pair attributes.
            authz = client.authorize(username, arguments=[("service", service)])
            return self._parse_groups_from_avpairs(authz)
        except Exception:  # pragma: no cover - library/ISE differences
            return []

    @staticmethod
    def _parse_groups_from_avpairs(authz_response) -> Iterable[str]:
        """
        authz_response format varies by tacacs_plus version; support the common
        tuple/list of (attribute, value) pairs and extract shell:roles entries.
        """
        groups = []
        if not authz_response:
            return groups

        pairs = authz_response if isinstance(authz_response, (list, tuple)) else []
        for pair in pairs:
            if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                continue
            attr, value = pair[0], pair[1]
            if isinstance(attr, bytes):
                attr = attr.decode()
            if isinstance(value, bytes):
                value = value.decode()
            if attr in ("cisco-av-pair", "shell:roles") and value:
                if "roles=" in value:
                    _, roles = value.split("roles=", 1)
                    groups.extend([r.strip() for r in roles.split(",") if r.strip()])
                else:
                    groups.append(value.strip())
        return groups
