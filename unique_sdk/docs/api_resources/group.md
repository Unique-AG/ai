# Group API

The Group API manages user groups and their configurations in Unique AI.

## Overview

Organize users into groups for permission management and access control.

## Methods

??? example "`unique_sdk.Group.create_group` - Create a new group"

    !!! info "Compatibility"
        Compatible with release >.48

    Create a new group in a company.

    **Parameters:**

    - `name` (str, required) - Group name
    - `externalId` (str, optional) - External system ID
    - `parentId` (str, optional) - Parent group ID for nesting

    **Returns:**

    Returns a [`Group`](#group) object.

    **Example:**

    ```python
    group = unique_sdk.Group.create_group(
        user_id=user_id,
        company_id=company_id,
        name="Engineering Team",
        externalId="ext_eng_001",
        parentId="group_parent123"
    )

    print(f"Created group: {group.id}")
    ```

??? example "`unique_sdk.Group.get_groups` - Get groups with filtering"

    !!! info "Compatibility"
        Compatible with release >.48

    Get groups with optional filtering and pagination.

    **Parameters:**

    - `skip` (int, optional) - Number of records to skip (default: 0)
    - `take` (int, optional) - Number of records to return (default: 50, max: 1000)
    - `name` (str, optional) - Filter by group name

    **Returns:**

    Returns a [`Groups`](#groups) object.

    **Example:**

    ```python
    groups = unique_sdk.Group.get_groups(
        user_id=user_id,
        company_id=company_id,
        skip=0,
        take=50
    )
    ```

    **Filter by Name:**

    ```python
    groups = unique_sdk.Group.get_groups(
        user_id=user_id,
        company_id=company_id,
        name="Admin"
    )
    ```

??? example "`unique_sdk.Group.update_group` - Update group name"

    !!! info "Compatibility"
        Compatible with release >.48

    Update a group's name.

    **Parameters:**

    - `group_id` (str, required) - Group ID to update
    - `name` (str, optional) - New group name

    **Returns:**

    Returns a [`Group`](#group) object.

    **Example:**

    ```python
    updated_group = unique_sdk.Group.update_group(
        user_id=user_id,
        company_id=company_id,
        group_id="group_a9cs7wr2z1bg2sxczvltgjch",
        name="New Group Name"
    )
    ```

??? example "`unique_sdk.Group.add_users_to_group` - Add users to group"

    !!! info "Compatibility"
        Compatible with release >.48

    Add multiple users to a group.

    **Parameters:**

    - `group_id` (str, required) - Group ID to add users to
    - `userIds` (List[str], required) - List of user IDs to add

    **Returns:**

    Returns an [`AddUsersToGroupResponse`](#adduserstogroupresponse) object.

    **Example:**

    ```python
    result = unique_sdk.Group.add_users_to_group(
        user_id=user_id,
        company_id=company_id,
        group_id="group_a9cs7wr2z1bg2sxczvltgjch",
        userIds=[
            "299420877169688584",
            "325402458132058201",
            "299426678160031752"
        ]
    )
    ```

??? example "`unique_sdk.Group.remove_users_from_group` - Remove users from group"

    !!! info "Compatibility"
        Compatible with release >.48

    Remove multiple users from a group.

    **Parameters:**

    - `group_id` (str, required) - Group ID to remove users from
    - `userIds` (List[str], required) - List of user IDs to remove

    **Returns:**

    Returns a [`RemoveUsersFromGroupResponse`](#removeusersfromgroupresponse) object.

    **Example:**

    ```python
    result = unique_sdk.Group.remove_users_from_group(
        user_id=user_id,
        company_id=company_id,
        group_id="group_a9cs7wr2z1bg2sxczvltgjch",
        userIds=[
            "299426678160031752",
            "299426678160031752"
        ]
    )
    ```

??? example "`unique_sdk.Group.update_group_configuration` - Update group configuration"

    !!! info "Compatibility"
        Compatible with release >.48

    Update group configuration (JSON object).

    **Parameters:**

    - `group_id` (str, required) - Group ID to update
    - `configuration` (Dict[str, Any], required) - Group configuration dictionary

    **Returns:**

    Returns a [`GroupWithConfiguration`](#groupwithconfiguration) object.

    **Example:**

    ```python
    updated_group = unique_sdk.Group.update_group_configuration(
        user_id=user_id,
        company_id=company_id,
        group_id="group_abc123",
        configuration={
            "email": "team@unique.ai",
            "department": "Engineering",
            "budget_code": "ENG-2024"
        }
    )
    ```

??? example "`unique_sdk.Group.delete_group` - Delete a group"

    !!! info "Compatibility"
        Compatible with release >.48

    Delete a group by ID.

    **Parameters:**

    - `group_id` (str, required) - Group ID to delete

    **Returns:**

    Returns a [`DeleteResponse`](#deleteresponse) object.

    **Example:**

    ```python
    result = unique_sdk.Group.delete_group(
        user_id=user_id,
        company_id=company_id,
        group_id="group_a9cs7wr2z1bg2sxczvltgjch"
    )
    ```

## Use Cases

??? example "Team Setup"

    ```python
    def setup_department_teams(company_id, admin_user_id):
        """Create department structure with teams."""
        
        # Create parent group
        engineering = unique_sdk.Group.create_group(
            user_id=admin_user_id,
            company_id=company_id,
            name="Engineering"
        )
        
        # Create sub-teams
        teams = ["Backend", "Frontend", "DevOps"]
        for team_name in teams:
            team = unique_sdk.Group.create_group(
                user_id=admin_user_id,
                company_id=company_id,
                name=team_name,
                parentId=engineering.id
            )
            print(f"Created: Engineering > {team_name}")
        
        return engineering.id

    setup_department_teams(company_id, admin_user_id)
    ```

??? example "Bulk User Management"

    ```python
    def assign_users_to_teams(user_email_list, team_id, company_id, admin_user_id):
        """Assign multiple users to a team."""
        
        # Find users by email
        user_ids = []
        for email in user_email_list:
            result = unique_sdk.User.get_users(
                user_id=admin_user_id,
                company_id=company_id,
                email=email
            )
            if result.data:
                user_ids.append(result.data[0].id)
        
        # Add to group
        if user_ids:
            unique_sdk.Group.add_users_to_group(
                user_id=admin_user_id,
                company_id=company_id,
                group_id=team_id,
                userIds=user_ids
            )
            print(f"Added {len(user_ids)} users to team")

    # Usage
    assign_users_to_teams(
        ["john@example.com", "jane@example.com"],
        "group_backend_team",
        company_id,
        admin_user_id
    )
    ```

??? example "Permission Management"

    ```python
    def grant_folder_access_to_group(group_id, folder_paths, access_type="READ"):
        """Grant group access to multiple folders."""
        
        for path in folder_paths:
            unique_sdk.Folder.add_access(
                user_id=admin_user_id,
                company_id=company_id,
                folderPath=path,
                scopeAccesses=[{
                    "entityId": group_id,
                    "type": access_type,  # "READ" or "WRITE"
                    "entityType": "GROUP"
                }],
                applyToSubScopes=True
            )
            print(f"Granted {access_type} access: {path}")

    # Grant engineering team access to their docs
    engineering_group_id = "group_engineering"
    grant_folder_access_to_group(
        engineering_group_id,
        ["/Company/Engineering", "/Company/Technical_Docs"],
        "WRITE"
    )
    ```

??? example "Group Configuration"

    ```python
    def configure_team(group_id, team_config):
        """Configure team settings."""
        
        return unique_sdk.Group.update_group_configuration(
            user_id=admin_user_id,
            company_id=company_id,
            group_id=group_id,
            configuration=team_config
        )

    # Configure team
    configure_team(
        "group_backend_team",
        {
            "slack_channel": "#backend-team",
            "oncall_rotation": ["user1", "user2", "user3"],
            "manager": "299420877169688584"
        }
    )
    ```

## Best Practices

??? example "Hierarchical Organization"

    ```python
    # Create department -> team -> sub-team hierarchy
    dept = unique_sdk.Group.create_group(name="Engineering")

    team = unique_sdk.Group.create_group(
        name="Backend",
        parentId=dept.id
    )

    subteam = unique_sdk.Group.create_group(
        name="API Team",
        parentId=team.id
    )
    ```

## Return Types

#### Group {#group}

??? note "The `Group` object represents a group in the company"

    **Fields:**

    - `id` (str) - Unique group identifier
    - `name` (str) - Group name
    - `externalId` (str) - External system identifier
    - `parentId` (str | None) - Parent group ID for nesting
    - `members` (List[GroupMember] | None) - List of group members. See [`Group.GroupMember`](#groupmember) for structure.
    - `createdAt` (str) - Creation timestamp (ISO 8601)
    - `updatedAt` (str) - Last update timestamp (ISO 8601)

    **Returned by:** `Group.create_group()`, `Group.update_group()`

#### GroupMember {#groupmember}

??? note "The `GroupMember` object represents a member of a group"

    **Fields:**

    - `entityId` (str) - User ID of the member

    **Used in:** `Group.members`

#### GroupWithConfiguration {#groupwithconfiguration}

??? note "The `GroupWithConfiguration` object represents a group with configuration"

    **Fields:**

    - All fields from [`Group`](#group)
    - `configuration` (Dict[str, Any]) - Group configuration dictionary

    **Returned by:** `Group.update_group_configuration()`

#### Groups {#groups}

??? note "The `Groups` object contains a list of groups"

    **Fields:**

    - `groups` (List[Group]) - List of group objects. See [`Group`](#group) for structure.

    **Returned by:** `Group.get_groups()`

#### AddUsersToGroupResponse {#adduserstogroupresponse}

??? note "The `AddUsersToGroupResponse` object contains membership information"

    **Fields:**

    - `memberships` (List[GroupMembership]) - List of created memberships. See [`GroupMembership`](#groupmembership) for structure.

    **Returned by:** `Group.add_users_to_group()`

#### GroupMembership {#groupmembership}

??? note "The `GroupMembership` object represents a membership relationship"

    **Fields:**

    - `entityId` (str) - User ID
    - `groupId` (str) - Group ID
    - `createdAt` (str) - Creation timestamp (ISO 8601)

    **Used in:** `AddUsersToGroupResponse.memberships`

#### RemoveUsersFromGroupResponse {#removeusersfromgroupresponse}

??? note "The `RemoveUsersFromGroupResponse` object indicates removal success"

    **Fields:**

    - `success` (bool) - Whether removal was successful

    **Returned by:** `Group.remove_users_from_group()`

#### DeleteResponse {#deleteresponse}

??? note "The `DeleteResponse` object contains the deleted group ID"

    **Fields:**

    - `id` (str) - ID of the deleted group

    **Returned by:** `Group.delete_group()`

## Related Resources

- [User API](user.md) - Manage individual users
- [Folder API](folder.md) - Manage folder access for groups

