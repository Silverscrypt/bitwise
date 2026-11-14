# Role management and permissions

How Bitwise decides who may change which roles, and how to set it up. See
DESIGN.md §2.2 and §7 for the reasoning.

## Authority model

| Who | Can do |
| --- | --- |
| **Officer** (holds the role in `OFFICER_ROLE_ID`) | Everything below on every project; register/unregister roles; give/remove functional roles; create/delete projects; appoint/remove Project Leads; run `/setup`. |
| **Project Lead** (per project) | On *their* projects only: add/remove members, appoint/remove Project Managers, view the roster. |
| **Project Manager** (per project) | On *their* projects only: add/remove ordinary members, view the roster. Can't remove a Lead or another Manager. |
| **Member** | `/member info` about themselves, `/project list`, `/role list`. |

Project leadership is stored in the `project_managers` table, not in a Discord
role. Leading Project Alpha grants nothing on Project Beta, and a Discord role
called "Project Lead" gives no Bitwise authority by itself.

`/member info` about someone else is allowed for Officers, and for Leads and
Managers of a project that person is on.

## Safety rules Bitwise enforces

- Every command checks authorization in the service layer. Command visibility is never relied on.
- Bitwise refuses to manage `@everyone`, integration-managed roles, and any role with moderation or admin permissions (Administrator, Manage Roles, Manage Channels, Kick/Ban, ...). This stops a Project Manager from handing out a role that grants more power than they have.
- Bitwise's own role must be above every role it manages, and it needs **Manage Roles**.
- For `/role add|remove`, the Officer's highest role must also be above the target role (the server owner is exempt).
- The database is the source of truth. Each change is written to the database and applied in Discord in one transaction. If Discord rejects the change, the database change is rolled back and nothing is recorded.
- Every change is written to `audit_logs` with the actor, target, action and details.

## Setting up a server

1. Put Bitwise's role near the top of **Server Settings → Roles**, above every functional and project role. Give it **Manage Roles**.
2. Set `OFFICER_ROLE_ID` in `.env` (Developer Mode → right-click the Officer role → Copy Role ID).
3. Register roles:
   - `/role register role:@Freelancer category:Membership`
   - `/role register role:@Developer category:Functional`. Repeat for each functional role.
4. Create projects: `/project create name:Alpha role:@Project Alpha`.
5. Appoint leadership: `/project leader set project:Alpha member:@someone level:Project Lead`.
6. Run `/setup` and fix anything marked ❌ or ⚠️.

## Command reference

| Command | Who |
| --- | --- |
| `/role add member role` / `/role remove member role` | Officers (functional roles only) |
| `/role register role category [name]` / `/role unregister name` | Officers |
| `/role list` | Anyone |
| `/project create name role [description]` / `/project delete project` | Officers |
| `/project list` | Anyone |
| `/project assign project member` / `/project remove project member` | Officers, the project's Lead/Managers |
| `/project roster project` | Officers, the project's Lead/Managers |
| `/project leader set project member level` | Lead: Officers. Manager: Officers or the project's Lead |
| `/project leader remove project member` | Same as above, by the level being removed |
| `/member info [member]` | Self; Officers; Lead/Managers of a shared project |
| `/setup` | Officers and server administrators |

Deleting a project or unregistering a role only removes Bitwise's records.
Discord roles and channels are left alone, so remove them in Discord if they're
no longer needed.

## Testing

```
pip install -r requirements-dev.txt
pytest
```

Service tests use in-memory fakes and need neither Discord nor PostgreSQL. The
repository tests in `tests/test_repositories_pg.py` run only when
`BITWISE_TEST_DATABASE_URL` points at a disposable database, because they
drop and recreate the tables.
