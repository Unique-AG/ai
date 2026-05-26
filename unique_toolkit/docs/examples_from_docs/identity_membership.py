# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "unique-toolkit>=2026.22.0",
#   "unique-sdk>=2026.22.0",
# ]
# ///


from unique_toolkit.experimental.identity import Identity

identity = Identity.from_settings()
memberships = identity.groups.add_members(
    group_id="g-eng",
    user_ids=["u-alice", "u-bob"],
)
for m in memberships:
    print(m.entity_id, "→", m.group_id)

success = identity.groups.remove_members(group_id="g-eng", user_ids=["u-bob"])
assert success is True
