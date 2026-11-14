import pytest

from bot.services.authorization import (
    can_manage_leadership_level,
    can_manage_project_members,
    ensure_actor_outranks,
    ensure_bot_can_assign,
    ensure_role_is_manageable,
)
from bot.services.errors import InvalidRequest, PermissionDenied
from tests.fakes import FakeRole, permissions


@pytest.mark.parametrize("officer, level, expected", [
    (True, None, True),
    (False, "lead", True),
    (False, "manager", True),
    (False, None, False),
])
def test_project_member_authority(officer, level, expected):
    assert can_manage_project_members(officer, level) is expected


@pytest.mark.parametrize("officer, actor_level, target_level, expected", [
    (True, None, "lead", True),
    (True, None, "manager", True),
    (False, "lead", "manager", True),
    (False, "lead", "lead", False),       # only Officers appoint Leads
    (False, "manager", "manager", False), # Managers can't appoint Managers
    (False, None, "manager", False),
])
def test_leadership_authority(officer, actor_level, target_level, expected):
    assert can_manage_leadership_level(officer, actor_level, target_level) is expected


def test_rejects_everyone_managed_and_dangerous_roles(world):
    with pytest.raises(InvalidRequest):
        ensure_role_is_manageable(world.everyone)
    with pytest.raises(InvalidRequest):
        ensure_role_is_manageable(world.bot_role)
    with pytest.raises(InvalidRequest, match="administrator"):
        ensure_role_is_manageable(world.admin_role)
    with pytest.raises(InvalidRequest, match="manage_roles"):
        ensure_role_is_manageable(FakeRole(1, "Mod", 2, perms=permissions(manage_roles=True)))

    ensure_role_is_manageable(world.developer)


def test_bot_must_outrank_role_and_have_manage_roles(world):
    with pytest.raises(InvalidRequest, match="above my highest role"):
        ensure_bot_can_assign(world.admin_role, world.guild.me)

    world.guild.me.guild_permissions.manage_roles = False
    with pytest.raises(InvalidRequest, match="Manage Roles"):
        ensure_bot_can_assign(world.developer, world.guild.me)


def test_actor_must_outrank_role_unless_owner(world):
    low = world.member(world.designer)
    with pytest.raises(PermissionDenied):
        ensure_actor_outranks(world.developer, low)

    ensure_actor_outranks(world.developer, world.officer)

    owner = world.member()
    owner.id = world.guild.owner_id
    ensure_actor_outranks(world.admin_role, owner)
