# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "unique-toolkit>=2026.22.0",
#   "unique-sdk>=2026.22.0",
# ]
# ///

# %%


from unique_toolkit.experimental.identity import Identity

identity = Identity.from_settings()
memberships = identity.users.groups_of(email="ada@example.com")
for m in memberships:
    print(m.id, m.name)

user = identity.users.get(email="ada@example.com")
is_eng = identity.users.is_member(user_id=user.id, group_id="g-eng")
