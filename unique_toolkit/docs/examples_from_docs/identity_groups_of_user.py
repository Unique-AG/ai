# %%
from unique_toolkit.experimental import (
    Identity,
)

identity = Identity.from_settings()
memberships = identity.groups_of(email="ada@example.com")
for m in memberships:
    print(m.id, m.name)

user = identity.get_user(email="ada@example.com")
is_eng = identity.is_member(user_id=user.id, group_id="g-eng")
