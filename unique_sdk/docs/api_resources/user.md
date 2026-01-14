# User API

The User API manages user accounts and configurations in Unique AI.

## Overview

Manage users within a company including user lookup and configuration management.

## Methods

??? example "`unique_sdk.User.get_users` - Get users with filtering"

    !!! info "Compatibility"
        Compatible with release >.48

    Get users in a company with optional filtering and pagination.

    **Parameters:**

    - `skip` (int, optional) - Number of records to skip (default: 0)
    - `take` (int, optional) - Number of records to return (default: 50, max: 1000)
    - `email` (str, optional) - Filter by email address
    - `displayName` (str, optional) - Filter by display name
    - `userName` (str, optional) - Filter by user name

    **Returns:**

    Returns a [`Users`](#users) object.

    **Example - List All Users:**

    ```python
    users = unique_sdk.User.get_users(
        user_id=user_id,
        company_id=company_id,
        skip=0,
        take=50
    )

    for user in users.data:
        print(f"{user.displayName} ({user.email})")
    ```

    **Example - Search by Email:**

    ```python
    users = unique_sdk.User.get_users(
        user_id=user_id,
        company_id=company_id,
        email="john@example.com"
    )
    ```

    **Example - Search by Name:**

    ```python
    users = unique_sdk.User.get_users(
        user_id=user_id,
        company_id=company_id,
        displayName="John"
    )
    ```

    **Example - Search by Username:**

    ```python
    users = unique_sdk.User.get_users(
        user_id=user_id,
        company_id=company_id,
        userName="john.doe"
    )
    ```

??? example "`unique_sdk.User.get_user_groups` - Get groups a user belongs to"

    !!! info "Compatibility"
        Compatible with release >.61

    Get all groups that a specific user belongs to.

    **Parameters:**

    - `target_user_id` (str, required) - The ID of the user to get groups for

    **Returns:**

    Returns a [`UserGroupsResponse`](#usergroupsresponse) object.

    **Example:**

    ```python
    user_groups = unique_sdk.User.get_user_groups(
        user_id=user_id,
        company_id=company_id,
        target_user_id="351283829975023795"
    )

    for group in user_groups["groups"]:
        print(f"Group: {group['name']} (ID: {group['id']})")
    ```

    **Example - Async:**

    ```python
    user_groups = await unique_sdk.User.get_user_groups_async(
        user_id=user_id,
        company_id=company_id,
        target_user_id="351283829975023795"
    )
    ```

??? example "`unique_sdk.User.update_user_configuration` - Update user configuration"

    !!! info "Compatibility"
        Compatible with release >.48

    Update the current user's configuration (JSON object).

    **Parameters:**

    - `userConfiguration` (Dict[str, Any], required) - JSON configuration object

    **Returns:**

    Returns a [`UserWithConfiguration`](#userwithconfiguration) object.

    **Example:**

    ```python
    updated_user = unique_sdk.User.update_user_configuration(
        user_id=user_id,
        company_id=company_id,
        userConfiguration={
            "location": "CH",
            "timezone": "Europe/Zurich",
            "preferences": {
                "theme": "dark",
                "language": "en"
            }
        }
    )
    ```

## Use Cases

??? example "User Directory"

    ```python
    def list_all_users(company_id, admin_user_id):
        """Get all users in pages."""
        all_users = []
        skip = 0
        take = 100
        
        while True:
            result = unique_sdk.User.get_users(
                user_id=admin_user_id,
                company_id=company_id,
                skip=skip,
                take=take
            )
            
            all_users.extend(result.data)
            
            if len(result.data) < take:
                break
            
            skip += take
        
        return all_users

    users = list_all_users(company_id, admin_user_id)
    print(f"Total users: {len(users)}")
    ```

??? example "User Lookup"

    ```python
    def find_user_by_email(email, company_id, admin_user_id):
        """Find a user by email address."""
        result = unique_sdk.User.get_users(
            user_id=admin_user_id,
            company_id=company_id,
            email=email
        )
        
        if result.data:
            return result.data[0]
        return None

    user = find_user_by_email("john@example.com", company_id, admin_user_id)
    if user:
        print(f"Found: {user.displayName}")
    ```

??? example "User Preferences Management"

    ```python
    def update_user_preferences(user_id, company_id, preferences):
        """Update user preferences."""
        return unique_sdk.User.update_user_configuration(
            user_id=user_id,
            company_id=company_id,
            userConfiguration={"preferences": preferences}
        )

    # Update preferences
    update_user_preferences(
        user_id,
        company_id,
        {
            "notifications": True,
            "emailDigest": "daily",
            "defaultAssistant": "assistant_abc123"
        }
    )
    ```

## Best Practices

??? example "Paginate Large User Lists"

    ```python
    # Process users in chunks
    def process_all_users(processor_func):
        skip = 0
        take = 100
        
        while True:
            users = unique_sdk.User.get_users(
                user_id=admin_user_id,
                company_id=company_id,
                skip=skip,
                take=take
            )
            
            for user in users.data:
                processor_func(user)
            
            if len(users.data) < take:
                break
            
            skip += take
    ```

??? example "Cache User Lookups"

    ```python
    class UserCache:
        def __init__(self):
            self.cache = {}
        
        def get_user(self, email, company_id, admin_user_id):
            if email in self.cache:
                return self.cache[email]
            
            result = unique_sdk.User.get_users(
                user_id=admin_user_id,
                company_id=company_id,
                email=email
            )
            
            if result.data:
                user = result.data[0]
                self.cache[email] = user
                return user
            
            return None

    cache = UserCache()
    ```

## Return Types

#### User {#user}

??? note "The `User` object represents a user in the company"

    **Fields:**

    - `id` (str) - Unique user identifier
    - `externalId` (str | None) - External system identifier
    - `firstName` (str) - User's first name
    - `lastName` (str) - User's last name
    - `displayName` (str) - User's display name
    - `userName` (str) - Username
    - `email` (str) - Email address
    - `updatedAt` (str) - Last update timestamp (ISO 8601)
    - `createdAt` (str) - Creation timestamp (ISO 8601)
    - `active` (bool) - Whether user is active

    **Returned by:** `User.get_users()`

#### UserWithConfiguration {#userwithconfiguration}

??? note "The `UserWithConfiguration` object represents a user with configuration"

    **Fields:**

    - All fields from [`User`](#user)
    - `userConfiguration` (Dict[str, Any]) - User configuration dictionary

    **Returned by:** `User.update_user_configuration()`

#### Users {#users}

??? note "The `Users` object contains a list of users"

    **Fields:**

    - `users` (List[User]) - List of user objects. See [`User`](#user) for properties.

    **Returned by:** `User.get_users()`

#### UserGroup {#usergroup}

??? note "The `UserGroup` object represents a group that a user belongs to"

    **Fields:**

    - `id` (str) - Unique group identifier
    - `name` (str) - Group name
    - `externalId` (str | None) - External system identifier
    - `parentId` (str | None) - Parent group ID
    - `createdAt` (str) - Creation timestamp (ISO 8601)
    - `updatedAt` (str) - Last update timestamp (ISO 8601)

    **Used in:** `UserGroupsResponse.groups`

#### UserGroupsResponse {#usergroupsresponse}

??? note "The `UserGroupsResponse` object contains groups a user belongs to"

    **Fields:**

    - `groups` (List[UserGroup]) - List of group objects. See [`UserGroup`](#usergroup) for properties.

    **Returned by:** `User.get_user_groups()`

## Related Resources

- [Group API](group.md) - Manage user groups
- [Folder API](folder.md) - Manage user access to folders

