import pytest

from bot.services.errors import DiscordSyncError, InvalidRequest, NotFound, PermissionDenied
from bot.services.member_service import MemberService
from bot.services.project_service import ProjectService
from bot.services.role_service import RoleService
from bot.services.setup_service import FAIL, OK, WARN, SetupService
from tests.fakes import World, forbidden


@pytest.fixture
def service(world):
    return ProjectService(world.db, World.OFFICER_ROLE_ID)


@pytest.fixture
def projects(world, service, run):
    """Alpha and Beta, each with a Lead; Alpha also has a Manager."""

    ns = type("Projects", (), {})()
    run(service.create_project(world.officer, "Alpha", world.alpha_role))
    run(service.create_project(world.officer, "Beta", world.beta_role))

    ns.alpha_lead = world.member()
    ns.alpha_manager = world.member()
    ns.beta_lead = world.member()
    run(service.set_leader(world.officer, "Alpha", ns.alpha_lead, "lead"))
    run(service.set_leader(world.officer, "Alpha", ns.alpha_manager, "manager"))
    run(service.set_leader(world.officer, "Beta", ns.beta_lead, "lead"))
    return ns


def on_project(world, name, member):
    project = world.db.state.projects
    project_id = next(p.id for p in project.values() if p.name == name)
    return (project_id, member.id) in world.db.state.project_members


# --------------------------------------------------
# PROJECT DEFINITIONS
# --------------------------------------------------

def test_only_officers_create_and_delete(world, service, run):
    with pytest.raises(PermissionDenied):
        run(service.create_project(world.member(), "Alpha", world.alpha_role))

    run(service.create_project(world.officer, "Alpha", world.alpha_role))
    with pytest.raises(PermissionDenied):
        run(service.delete_project(world.member(), "Alpha"))

    run(service.delete_project(world.officer, "alpha"))
    assert run(service.list_projects()) == []


def test_project_role_cannot_double_as_functional_role(world, service, run):
    roles = RoleService(world.db, World.OFFICER_ROLE_ID)
    run(roles.register_role(world.officer, world.developer, "functional"))

    with pytest.raises(InvalidRequest, match="already registered"):
        run(service.create_project(world.officer, "Dev", world.developer))

    run(service.create_project(world.officer, "Alpha", world.alpha_role))
    with pytest.raises(InvalidRequest, match="project"):
        run(roles.register_role(world.officer, world.alpha_role, "functional"))


def test_duplicate_project_rejected(world, service, run):
    run(service.create_project(world.officer, "Alpha", world.alpha_role))
    with pytest.raises(InvalidRequest):
        run(service.create_project(world.officer, "alpha", world.beta_role))


# --------------------------------------------------
# ROSTER AUTHORITY (DESIGN.md §7.2)
# --------------------------------------------------

def test_lead_and_manager_assign_on_own_project(world, service, run, projects):
    a, b = world.member(), world.member()

    assert run(service.assign_member(projects.alpha_lead, "Alpha", a)) is True
    assert run(service.assign_member(projects.alpha_manager, "Alpha", b)) is True
    assert world.alpha_role in a.roles and world.alpha_role in b.roles
    assert on_project(world, "Alpha", a) and on_project(world, "Alpha", b)


def test_lead_cannot_manage_other_projects(world, service, run, projects):
    with pytest.raises(PermissionDenied):
        run(service.assign_member(projects.alpha_lead, "Beta", world.member()))
    with pytest.raises(PermissionDenied):
        run(service.roster(projects.alpha_lead, "Beta"))


def test_ordinary_member_cannot_manage(world, service, run, projects):
    with pytest.raises(PermissionDenied):
        run(service.assign_member(world.member(world.alpha_role), "Alpha", world.member()))


def test_assign_is_idempotent(world, service, run, projects):
    target = world.member()
    run(service.assign_member(projects.alpha_lead, "Alpha", target))
    assert run(service.assign_member(projects.alpha_lead, "Alpha", target)) is False


def test_remove_member(world, service, run, projects):
    target = world.member()
    run(service.assign_member(projects.alpha_manager, "Alpha", target))

    assert run(service.remove_member(projects.alpha_manager, "Alpha", target)) is True
    assert world.alpha_role not in target.roles
    assert not on_project(world, "Alpha", target)
    assert run(service.remove_member(projects.alpha_manager, "Alpha", target)) is False


def test_manager_cannot_remove_lead_or_other_manager(world, service, run, projects):
    with pytest.raises(PermissionDenied):
        run(service.remove_member(projects.alpha_manager, "Alpha", projects.alpha_lead))

    other_manager = world.member()
    run(service.set_leader(projects.alpha_lead, "Alpha", other_manager, "manager"))
    with pytest.raises(PermissionDenied):
        run(service.remove_member(projects.alpha_manager, "Alpha", other_manager))


def test_lead_removing_manager_from_project_drops_leadership(world, service, run, projects):
    run(service.remove_member(projects.alpha_lead, "Alpha", projects.alpha_manager))

    project_id = run(world.db.repo.get_project("Alpha")).id
    assert run(world.db.repo.get_leadership_level(project_id, projects.alpha_manager.id)) is None


def test_unknown_project(world, service, run, projects):
    with pytest.raises(NotFound):
        run(service.assign_member(world.officer, "Gamma", world.member()))


def test_deleted_discord_role_is_reported(world, service, run, projects):
    del world.guild.roles[world.alpha_role.id]
    with pytest.raises(InvalidRequest, match="no longer exists"):
        run(service.assign_member(world.officer, "Alpha", world.member()))


def test_discord_failure_rolls_back_assignment(world, service, run, projects):
    target = world.member()
    target.fail_with = forbidden()

    with pytest.raises(DiscordSyncError):
        run(service.assign_member(projects.alpha_lead, "Alpha", target))

    assert not on_project(world, "Alpha", target)
    assert world.audit_actions()[-1] != "project.assign"


def test_roster(world, service, run, projects):
    roster = run(service.roster(projects.alpha_manager, "Alpha"))

    assert {l.member_id: l.level for l in roster.leaders} == {
        projects.alpha_lead.id: "lead",
        projects.alpha_manager.id: "manager",
    }
    # Appointed leaders are added to the project as members too.
    assert {m.discord_id for m in roster.members} == {
        projects.alpha_lead.id, projects.alpha_manager.id,
    }


# --------------------------------------------------
# LEADERSHIP
# --------------------------------------------------

def test_only_officers_appoint_leads(world, service, run, projects):
    with pytest.raises(PermissionDenied, match="Only Officers"):
        run(service.set_leader(projects.alpha_lead, "Alpha", world.member(), "lead"))


def test_lead_appoints_and_removes_managers(world, service, run, projects):
    target = world.member()
    assert run(service.set_leader(projects.alpha_lead, "Alpha", target, "manager")) is True
    assert world.alpha_role in target.roles

    assert run(service.remove_leader(projects.alpha_lead, "Alpha", target)) == "manager"
    assert on_project(world, "Alpha", target)  # still a member


def test_manager_cannot_appoint_managers(world, service, run, projects):
    with pytest.raises(PermissionDenied):
        run(service.set_leader(projects.alpha_manager, "Alpha", world.member(), "manager"))


def test_lead_cannot_demote_another_lead(world, service, run, projects):
    second_lead = world.member()
    run(service.set_leader(world.officer, "Alpha", second_lead, "lead"))

    with pytest.raises(PermissionDenied):
        run(service.set_leader(projects.alpha_lead, "Alpha", second_lead, "manager"))
    with pytest.raises(PermissionDenied):
        run(service.remove_leader(projects.alpha_lead, "Alpha", second_lead))


def test_officer_promotes_manager_to_lead(world, service, run, projects):
    assert run(service.set_leader(world.officer, "Alpha", projects.alpha_manager, "lead")) is True
    assert run(service.set_leader(world.officer, "Alpha", projects.alpha_manager, "lead")) is False


def test_remove_leader_when_not_leader(world, service, run, projects):
    with pytest.raises(NotFound):
        run(service.remove_leader(world.officer, "Alpha", world.member()))


def test_leadership_changes_are_audited(world, service, run, projects):
    actions = world.audit_actions()
    assert actions.count("project.create") == 2
    assert actions.count("project.leader.set") == 3


# --------------------------------------------------
# /member info
# --------------------------------------------------

def test_member_info_visibility(world, service, run, projects):
    members = MemberService(world.db, World.OFFICER_ROLE_ID)
    alpha_member = world.member()
    run(service.assign_member(projects.alpha_lead, "Alpha", alpha_member))

    info = run(members.member_info(alpha_member, alpha_member))
    assert [p.name for p in info.projects] == ["Alpha"]

    run(members.member_info(world.officer, alpha_member))
    run(members.member_info(projects.alpha_manager, alpha_member))

    with pytest.raises(PermissionDenied):
        run(members.member_info(projects.beta_lead, alpha_member))
    with pytest.raises(PermissionDenied):
        run(members.member_info(world.member(), alpha_member))


# --------------------------------------------------
# /setup
# --------------------------------------------------

def test_setup_diagnostics(world, service, run, projects):
    setup = SetupService(world.db, World.OFFICER_ROLE_ID)

    with pytest.raises(PermissionDenied):
        run(setup.diagnose(world.member()))

    world.alpha_role.position = 25  # now above the bot
    run(service.create_project(world.officer, "Gamma", world.designer))

    checks = {c.subject: c.status for c in run(setup.diagnose(world.officer))}

    assert checks["Manage Roles permission"] == OK
    assert checks["Officer role"] == OK
    assert checks["Database"] == OK
    assert checks["Membership role"] == WARN
    assert checks["Project: Alpha"] == FAIL
    assert checks["Project: Beta"] == OK
    assert checks["Project: Gamma"] == WARN  # no lead yet
