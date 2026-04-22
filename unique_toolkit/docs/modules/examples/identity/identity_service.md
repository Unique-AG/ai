# Identity Service — Users & Groups

!!! warning "Experimental"

    The `Identity` service lives under `unique_toolkit.experimental.identity`.
    Its public API, method names, argument shapes, and return types may change
    without notice and are **not** covered by the toolkit's normal stability
    guarantees. Pin your toolkit version if you depend on a specific shape.

The `Identity` service is a thin facade over two CRUD-style sub-services that
wrap `unique_sdk.User` and `unique_sdk.Group`:

- `identity.users` — user-centric operations (`list`, `get`,
  `update_configuration`, plus `groups_of` / `is_member`).
- `identity.groups` — group-centric operations (`list`, `create`, `delete`,
  `rename`, `update_configuration`, `add_members`, `remove_members`).

The Linux-inspired mental model still applies: `users.list()` is `getent passwd`,
`users.get(...)` is `id <user>`, `users.groups_of(...)` is `groups <user>`, and
membership operations map to `gpasswd -a` / `gpasswd -d`.

Constructors (`Identity`, `Users`, and `Groups`) are **keyword-only**, so there
is no positional-argument ordering to remember — you always pass
`user_id=...`, `company_id=...`.

```{.python #identity_imports}
from unique_toolkit.experimental.identity import Identity
```

<!--
```{.python #identity_service_setup}
<<common_imports>>
from unique_toolkit.experimental.identity import Identity
identity = Identity.from_settings()
```
-->

## Listing users and groups

```{.python #identity_list_users_and_groups}
users = identity.users.list(take=10)
for user in users:
    print(user.id, user.display_name, user.email)

groups = identity.groups.list(take=10)
for group in groups:
    print(group.id, group.name)
```

<!--
```{.python file=./docs/.python_files/identity_list_users_and_groups.py}
<<identity_service_setup>>
<<identity_list_users_and_groups>>
```
-->

## Looking up a single user (`id <user>`)

`users.get` and `users.groups_of` each accept exactly **one** of `user_id=`,
`email=`, or `user_name=`. Type checkers enforce this via `@overload`; at
runtime, mixing identifiers raises `TypeError`.

```{.python #identity_get_user_overloads}
by_id = identity.users.get(user_id="usr_01HN0...")
by_email = identity.users.get(email="ada@example.com")
by_name = identity.users.get(user_name="ada")
```

<!--
```{.python file=./docs/.python_files/identity_get_user.py}
<<identity_service_setup>>
target_email = "ada@example.com"
user = identity.users.get(email=target_email)
print(user.id, user.display_name)
```
-->

## Listing a user's groups (`groups <user>`)

```{.python #identity_groups_of_user}
memberships = identity.users.groups_of(email="ada@example.com")
for m in memberships:
    print(m.id, m.name)

user = identity.users.get(email="ada@example.com")
is_eng = identity.users.is_member(user_id=user.id, group_id="g-eng")
```

<!--
```{.python file=./docs/.python_files/identity_groups_of_user.py}
<<identity_service_setup>>
<<identity_groups_of_user>>
```
-->

## Creating, renaming, and deleting groups

```{.python #identity_group_lifecycle}
group = identity.groups.create(name="release-managers")

renamed = identity.groups.rename(group.id, new_name="release-captains")

identity.groups.delete(renamed.id)
```

<!--
```{.python file=./docs/.python_files/identity_group_lifecycle.py}
<<identity_service_setup>>
<<identity_group_lifecycle>>
```
-->

## Managing membership (`gpasswd -a` / `gpasswd -d`)

Membership operations are bulk — pass a list of user ids.

```{.python #identity_membership}
memberships = identity.groups.add_members(
    group_id="g-eng",
    user_ids=["u-alice", "u-bob"],
)
for m in memberships:
    print(m.entity_id, "→", m.group_id)

success = identity.groups.remove_members(group_id="g-eng", user_ids=["u-bob"])
assert success is True
```

<!--
```{.python file=./docs/.python_files/identity_membership.py}
<<identity_service_setup>>
<<identity_membership>>
```
-->

## Updating configuration blobs

Both users and groups have a free-form `configuration` blob that the platform
treats as opaque JSON — useful for storing per-user preferences or per-group
feature flags.

```{.python #identity_configuration_blobs}
me = identity.users.update_configuration(
    configuration={"theme": "dark", "sidebar": "collapsed"},
)
print(me.user_configuration)

updated_group = identity.groups.update_configuration(
    "g-eng",
    configuration={"default_assistant": "engineering-helper"},
)
print(updated_group.configuration)
```

<!--
```{.python file=./docs/.python_files/identity_configuration_blobs.py}
<<identity_service_setup>>
<<identity_configuration_blobs>>
```
-->

??? example "Full Examples (Click to expand)"

    <!--codeinclude-->
    [List users and groups](../../../examples_from_docs/identity_list_users_and_groups.py)
    [Get a user](../../../examples_from_docs/identity_get_user.py)
    [List a user's groups](../../../examples_from_docs/identity_groups_of_user.py)
    [Group lifecycle](../../../examples_from_docs/identity_group_lifecycle.py)
    [Membership](../../../examples_from_docs/identity_membership.py)
    [Configuration blobs](../../../examples_from_docs/identity_configuration_blobs.py)
    <!--/codeinclude-->

## Linux-to-toolkit method map

| Linux | Toolkit method |
| --- | --- |
| `getent passwd` | `identity.users.list(...)` |
| `id <user>` | `identity.users.get(user_id= \| email= \| user_name=)` |
| `groups <user>` | `identity.users.groups_of(user_id= \| email= \| user_name=)` |
| `id -Gn <user> \| grep <group>` | `identity.users.is_member(user_id=..., group_id=...)` |
| `getent group` | `identity.groups.list(...)` |
| `groupadd <name>` | `identity.groups.create(name=...)` |
| `groupdel <id>` | `identity.groups.delete(group_id)` |
| `groupmod -n <new> <old>` | `identity.groups.rename(group_id, new_name=...)` |
| `gpasswd -a <user> <group>` | `identity.groups.add_members(group_id, user_ids=[...])` |
| `gpasswd -d <user> <group>` | `identity.groups.remove_members(group_id, user_ids=[...])` |
