# %%
from unique_toolkit.experimental import (
    Identity,
)

identity = Identity.from_settings()
me = identity.update_user_configuration(
    configuration={"theme": "dark", "sidebar": "collapsed"},
)
print(me.user_configuration)

updated_group = identity.update_group_configuration(
    "g-eng",
    configuration={"default_assistant": "engineering-helper"},
)
print(updated_group.configuration)
