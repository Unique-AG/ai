# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "unique-toolkit>=2026.22.0",
#   "unique-sdk>=2026.22.0",
# ]
# ///


from unique_toolkit.experimental.identity import Identity

identity = Identity.from_settings()
group = identity.groups.create(name="release-managers")

renamed = identity.groups.rename(group.id, new_name="release-captains")

identity.groups.delete(renamed.id)
