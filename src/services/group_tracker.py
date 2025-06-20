"""Group tracking service for monitoring bot membership in groups."""
from pathlib import Path
from typing import Dict, Optional, Set
from datetime import datetime

from utils.logger import logger


class GroupTracker:
    """Tracks groups where bot is a member."""

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize group tracker.

        Args:
            storage_path: Path to JSON file for persistent storage
        """
        self.groups: Dict[int, Dict[str, str]] = {}

    def add_group(
        self, group_id: int, title: str, username: Optional[str] = None
    ) -> bool:
        """Add or update group information.

        Args:
            group_id: Telegram group ID
            title: Group title
            username: Group username (if public)

        Returns:
            True if this is a new group
        """
        is_new = group_id not in self.groups

        self.groups[group_id] = {
            "title": title,
            "username": username or "",
            "added_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
        }

        if is_new:
            logger.info(f"New group added: {title} (ID: {group_id})")
        else:
            # Update last seen time
            self.groups[group_id]["last_seen"] = datetime.now().isoformat()

        return is_new

    def remove_group(self, group_id: int) -> None:
        """Remove group from tracking.

        Args:
            group_id: Telegram group ID
        """
        if group_id in self.groups:
            title = self.groups[group_id]["title"]
            del self.groups[group_id]
            logger.info(f"Group removed: {title} (ID: {group_id})")

    def get_groups(self) -> Dict[int, Dict[str, str]]:
        """Get all tracked groups.

        Returns:
            Dictionary of groups with their information
        """
        return self.groups.copy()

    def get_group_ids(self) -> Set[int]:
        """Get set of all group IDs.

        Returns:
            Set of group IDs
        """
        return set(self.groups.keys())

    def is_tracked(self, group_id: int) -> bool:
        """Check if group is being tracked.

        Args:
            group_id: Telegram group ID

        Returns:
            True if group is tracked
        """
        return group_id in self.groups

    def get_group_info(self, group_id: int) -> Optional[Dict[str, str]]:
        """Get information about specific group.

        Args:
            group_id: Telegram group ID

        Returns:
            Group information or None
        """
        return self.groups.get(group_id)
