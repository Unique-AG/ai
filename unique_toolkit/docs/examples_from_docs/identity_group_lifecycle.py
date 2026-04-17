# %%
from unique_toolkit.experimental import (
    Identity,
)

identity = Identity.from_settings()
group = identity.create_group(name="release-managers")

renamed = identity.rename_group(group.id, new_name="release-captains")

identity.delete_group(renamed.id)
