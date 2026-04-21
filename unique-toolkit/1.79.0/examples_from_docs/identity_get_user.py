# %%
from unique_toolkit.experimental import Identity

identity = Identity.from_settings()
target_email = "ada@example.com"
user = identity.users.get(email=target_email)
print(user.id, user.display_name)
