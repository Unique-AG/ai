# %%
from unique_toolkit.experimental import Identity

identity = Identity.from_settings()
me = identity.users.update_configuration(
    configuration={"theme": "dark", "sidebar": "collapsed"},
)
print(me.user_configuration)

updated_group = identity.groups.update_configuration(
    "g-eng",
    configuration={"default_assistant": "engineering-helper"},
)
print(updated_group.configuration)
