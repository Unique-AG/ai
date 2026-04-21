# %%
from unique_toolkit.experimental import Identity

identity = Identity.from_settings()
group = identity.groups.create(name="release-managers")

renamed = identity.groups.rename(group.id, new_name="release-captains")

identity.groups.delete(renamed.id)
