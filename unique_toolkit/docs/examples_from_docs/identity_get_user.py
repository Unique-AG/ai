# %%
from unique_toolkit.experimental import (
    Identity,
)

identity = Identity.from_settings()
target_email = "ada@example.com"
user = identity.get_user(email=target_email)
print(user.id, user.display_name)
