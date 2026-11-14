"""Member lookups for `/member info` (DESIGN.md §2.2)."""

from dataclasses import dataclass

from bot.database.models import LeaderRecord, MemberRecord, ProjectRecord, RoleRecord
from bot.services.authorization import is_officer
from bot.services.errors import PermissionDenied


@dataclass(frozen=True)
class MemberInfo:
    record: MemberRecord | None
    roles: list[RoleRecord]
    projects: list[ProjectRecord]
    leadership: list[LeaderRecord]


class MemberService:

    def __init__(self, db, officer_role_id):
        self.db = db
        self.officer_role_id = officer_role_id

    async def member_info(self, actor, target):
        """Who may look someone up:

        - anyone, about themselves;
        - Officers, about anyone;
        - a Project Lead or Manager, about members of a project they lead.
        """

        async with self.db.transaction() as repo:
            info = MemberInfo(
                record=await repo.get_member(target.id),
                roles=await repo.get_member_roles(target.id),
                projects=await repo.get_member_projects(target.id),
                leadership=await repo.get_member_leadership(target.id),
            )

            if actor.id == target.id or is_officer(actor, self.officer_role_id):
                return info

            led_project_ids = {
                leader.project_id
                for leader in await repo.get_member_leadership(actor.id)
            }

        if led_project_ids & {project.id for project in info.projects}:
            return info

        raise PermissionDenied(
            "You can view your own info, or members of projects you lead or "
            "manage. Officers can view anyone."
        )
