# %%
from unique_toolkit.experimental.identity import Identity

identity = Identity.from_settings()
users = identity.users.list(take=10)
for user in users:
    print(user.id, user.display_name, user.email)

groups = identity.groups.list(take=10)
for group in groups:
    print(group.id, group.name)
