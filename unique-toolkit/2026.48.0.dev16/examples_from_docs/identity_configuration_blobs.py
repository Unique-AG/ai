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
me = identity.users.update_configuration(
    configuration={"theme": "dark", "sidebar": "collapsed"},
)
print(me.user_configuration)

updated_group = identity.groups.update_configuration(
    "g-eng",
    configuration={"default_assistant": "engineering-helper"},
)
print(updated_group.configuration)
