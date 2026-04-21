# %%
from unique_toolkit.experimental import Identity

identity = Identity.from_settings()
memberships = identity.groups.add_members(
    group_id="g-eng",
    user_ids=["u-alice", "u-bob"],
)
for m in memberships:
    print(m.entity_id, "→", m.group_id)

success = identity.groups.remove_members(group_id="g-eng", user_ids=["u-bob"])
assert success is True
