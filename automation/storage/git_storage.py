"""
Git-backed configuration storage similar to Oxidized.
"""
from __future__ import annotations

import logging
from pathlib import Path

from django.utils import timezone

try:
    from git import Repo, GitCommandError, InvalidGitRepositoryError, NoSuchPathError
except ImportError:  # pragma: no cover - optional dependency
    Repo = None  # type: ignore
    GitCommandError = InvalidGitRepositoryError = NoSuchPathError = Exception  # type: ignore

logger = logging.getLogger(__name__)


class ConfigBackupGitStorage:
    """
    Persist device configurations inside a Git repository.
    """

    def __init__(self, repo_path: str = "/web/zas/config-backups/"):
        self.repo_path = Path(repo_path)

    def store(self, device, config_text: str, timestamp=None) -> bool:
        """
        Write the configuration to disk and commit it if there are changes.
        Returns True when a commit was created.
        """
        if Repo is None:
            logger.warning(
                "GitPython is not installed. Skipping Git storage for %s.", device
            )
            return False

        timestamp = timestamp or timezone.now()
        try:
            repo = self._ensure_repo()
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Unable to initialize config backup repository: %s", exc)
            return False

        file_path = self.repo_path / f"{device.name}.cfg"
        content = config_text or ""

        try:
            if file_path.exists():
                existing = file_path.read_text(encoding="utf-8")
                if existing == content:
                    logger.debug("Configuration for %s unchanged; skipping commit.", device)
                    return False
            else:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            file_path.write_text(content, encoding="utf-8")
            repo.index.add([str(file_path)])
            commit_message = f"Backup: {device.name} @ {timestamp.isoformat()}"
            repo.index.commit(commit_message)
            logger.info("Stored configuration for %s in Git repo.", device)
            return True
        except (OSError, GitCommandError) as exc:
            logger.error("Failed to commit configuration for %s: %s", device, exc)
            return False

    def _ensure_repo(self):
        self.repo_path.mkdir(parents=True, exist_ok=True)
        try:
            return Repo(self.repo_path)
        except (InvalidGitRepositoryError, NoSuchPathError):
            logger.info("Initializing configuration backup repository at %s", self.repo_path)
            return Repo.init(self.repo_path)
