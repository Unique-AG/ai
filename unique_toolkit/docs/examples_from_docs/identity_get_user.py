# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "unique-toolkit>=2026.22.0",
#   "unique-sdk>=2026.22.0",
# ]
# ///


from unique_toolkit.experimental.identity import Identity

identity = Identity.from_settings()
target_email = "ada@example.com"
user = identity.users.get(email=target_email)
print(user.id, user.display_name)
