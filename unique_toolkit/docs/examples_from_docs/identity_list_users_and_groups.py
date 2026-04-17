# %%
from unique_toolkit.experimental import (
    Identity,
)

identity = Identity.from_settings()
users = identity.list_users(take=10)
for user in users:
    print(user.id, user.display_name, user.email)

groups = identity.list_groups(take=10)
for group in groups:
    print(group.id, group.name)
