import pytest

from bot.services.errors import DiscordSyncError, InvalidRequest, NotFound, PermissionDenied
from bot.services.role_service import RoleService
from tests.fakes import World, forbidden


@pytest.fixture
def service(world):
    return RoleService(world.db, World.OFFICER_ROLE_ID)


@pytest.fixture
def registered(world, service, run):
    run(service.register_role(world.officer, world.developer, "functional"))
    run(service.register_role(world.officer, world.designer, "membership", "Freelancer"))


def role_ids(member):
    return {role.id for role in member.roles}


# --------------------------------------------------
# REGISTRATION
# --------------------------------------------------

def test_officer_registers_role(world, service, run):
    record = run(service.register_role(world.officer, world.developer, "functional"))

    assert record.name == "Developer"
    assert record.discord_role_id == world.developer.id
    assert world.audit_actions() == ["role.register"]


def test_non_officer_cannot_register(world, service, run):
    with pytest.raises(PermissionDenied):
        run(service.register_role(world.member(), world.developer, "functional"))


def test_cannot_register_officer_or_admin_roles(world, service, run):
    with pytest.raises(InvalidRequest):
        run(service.register_role(world.officer, world.officer_role, "functional"))
    with pytest.raises(InvalidRequest):
        run(service.register_role(world.officer, world.admin_role, "functional"))


def test_duplicate_registration_rejected(world, service, run, registered):
    with pytest.raises(InvalidRequest, match="already registered"):
        run(service.register_role(world.officer, world.developer, "functional", "Dev 2"))


def test_unregister(world, service, run, registered):
    run(service.unregister_role(world.officer, "developer"))
    assert run(world.db.repo.get_role_by_name("Developer")) is None

    with pytest.raises(NotFound):
        run(service.unregister_role(world.officer, "Developer"))


# --------------------------------------------------
# ADD / REMOVE
# --------------------------------------------------

def test_officer_adds_and_removes_functional_role(world, service, run, registered):
    target = world.member()

    assert run(service.add_role(world.officer, target, world.developer)) is True
    assert world.developer.id in role_ids(target)
    assert [r.name for r in run(world.db.repo.get_member_roles(target.id))] == ["Developer"]

    assert run(service.remove_role(world.officer, target, world.developer)) is True
    assert world.developer.id not in role_ids(target)
    assert run(world.db.repo.get_member_roles(target.id)) == []

    assert world.audit_actions()[-2:] == ["role.add", "role.remove"]


def test_add_is_idempotent(world, service, run, registered):
    target = world.member()
    run(service.add_role(world.officer, target, world.developer))
    audit_count = len(world.db.state.audit)

    assert run(service.add_role(world.officer, target, world.developer)) is False
    assert len(world.db.state.audit) == audit_count


def test_add_repairs_discord_drift(world, service, run, registered):
    target = world.member()
    run(service.add_role(world.officer, target, world.developer))
    target.roles.remove(world.developer)  # someone removed it by hand in Discord

    assert run(service.add_role(world.officer, target, world.developer)) is True
    assert world.developer.id in role_ids(target)
    assert world.db.state.audit[-1][3]["repaired_discord_only"] is True


def test_non_officer_cannot_add(world, service, run, registered):
    lead = world.member(world.beta_role)
    with pytest.raises(PermissionDenied):
        run(service.add_role(lead, world.member(), world.developer))


def test_unregistered_role_rejected(world, service, run, registered):
    with pytest.raises(NotFound):
        run(service.add_role(world.officer, world.member(), world.alpha_role))


def test_membership_role_not_managed_by_role_add(world, service, run, registered):
    with pytest.raises(InvalidRequest, match="membership"):
        run(service.add_role(world.officer, world.member(), world.designer))


def test_officer_below_role_is_denied(world, service, run, registered):
    # An Officer whose highest role sits below the target role can't grant it.
    world.officer_role.position = 2
    with pytest.raises(PermissionDenied, match="above your highest role"):
        run(service.add_role(world.officer, world.member(), world.developer))


def test_bots_cannot_receive_roles(world, service, run, registered):
    with pytest.raises(InvalidRequest):
        run(service.add_role(world.officer, world.member(bot=True), world.developer))


def test_discord_failure_rolls_back_database(world, service, run, registered):
    target = world.member()
    target.fail_with = forbidden()
    audit_count = len(world.db.state.audit)

    with pytest.raises(DiscordSyncError):
        run(service.add_role(world.officer, target, world.developer))

    assert run(world.db.repo.get_member_roles(target.id)) == []
    assert len(world.db.state.audit) == audit_count


def test_remove_failure_keeps_database_record(world, service, run, registered):
    target = world.member()
    run(service.add_role(world.officer, target, world.developer))
    target.fail_with = forbidden()

    with pytest.raises(DiscordSyncError):
        run(service.remove_role(world.officer, target, world.developer))

    assert [r.name for r in run(world.db.repo.get_member_roles(target.id))] == ["Developer"]
