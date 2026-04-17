# Identity Service — Users & Groups

!!! warning "Experimental"

    The `Identity` service lives under `unique_toolkit.experimental.identity`.
    Its public API, method names, argument shapes, and return types may change
    without notice and are **not** covered by the toolkit's normal stability
    guarantees. Pin your toolkit version if you depend on a specific shape.

The `Identity` service is the toolkit wrapper around `unique_sdk.User` and
`unique_sdk.Group`. It exposes a small Linux-inspired API so that users and
groups feel familiar: `list_users` is `getent passwd`, `get_user` is `id <user>`,
`groups_of` is `groups <user>`, and membership operations map to
`gpasswd -a` / `gpasswd -d`.

```{.python #identity_imports}
from unique_toolkit.experimental import Identity
```

<!--
```{.python #identity_service_setup}
<<common_imports>>
from unique_toolkit.experimental import Identity
identity = Identity.from_settings()
```
-->

## Listing users and groups

```{.python #identity_list_users_and_groups}
users = identity.list_users(take=10)
for user in users:
    print(user.id, user.display_name, user.email)

groups = identity.list_groups(take=10)
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

The `get_user` and `groups_of` methods each accept exactly **one** of `user_id=`,
`email=`, or `user_name=`. Type checkers enforce this via `@overload`; at
runtime, mixing identifiers raises `TypeError`.

```{.python #identity_get_user_overloads}
by_id = identity.get_user(user_id="usr_01HN0...")
by_email = identity.get_user(email="ada@example.com")
by_name = identity.get_user(user_name="ada")
```

<!--
```{.python file=./docs/.python_files/identity_get_user.py}
<<identity_service_setup>>
target_email = "ada@example.com"
user = identity.get_user(email=target_email)
print(user.id, user.display_name)
```
-->

## Listing a user's groups (`groups <user>`)

```{.python #identity_groups_of_user}
memberships = identity.groups_of(email="ada@example.com")
for m in memberships:
    print(m.id, m.name)

user = identity.get_user(email="ada@example.com")
is_eng = identity.is_member(user_id=user.id, group_id="g-eng")
```

<!--
```{.python file=./docs/.python_files/identity_groups_of_user.py}
<<identity_service_setup>>
<<identity_groups_of_user>>
```
-->

## Creating, renaming, and deleting groups

```{.python #identity_group_lifecycle}
group = identity.create_group(name="release-managers")

renamed = identity.rename_group(group.id, new_name="release-captains")

identity.delete_group(renamed.id)
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
memberships = identity.add_members(
    group_id="g-eng",
    user_ids=["u-alice", "u-bob"],
)
for m in memberships:
    print(m.entity_id, "→", m.group_id)

success = identity.remove_members(group_id="g-eng", user_ids=["u-bob"])
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
me = identity.update_user_configuration(
    configuration={"theme": "dark", "sidebar": "collapsed"},
)
print(me.user_configuration)

updated_group = identity.update_group_configuration(
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

| Linux | `Identity` method |
| --- | --- |
| `getent passwd` | `list_users(...)` |
| `id <user>` | `get_user(user_id= \| email= \| user_name=)` |
| `groups <user>` | `groups_of(user_id= \| email= \| user_name=)` |
| `id -Gn <user> \| grep <group>` | `is_member(user_id=..., group_id=...)` |
| `getent group` | `list_groups(...)` |
| `groupadd <name>` | `create_group(name=...)` |
| `groupdel <id>` | `delete_group(group_id)` |
| `groupmod -n <new> <old>` | `rename_group(group_id, new_name=...)` |
| `gpasswd -a <user> <group>` | `add_members(group_id, user_ids=[...])` |
| `gpasswd -d <user> <group>` | `remove_members(group_id, user_ids=[...])` |
