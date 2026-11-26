import unique_sdk


async def get_readable_skill_versions_async(
    *,
    user_id: str,
    company_id: str,
    space_id: str,
) -> dict[str, str]:
    """Return the last-modified time of each skill file the user can read in the space.

    The platform filters the list by the user's read access, so a content ID
    in the result is a skill this user may read. Keys are content IDs of
    ``SKILL.md`` files. A skill the platform lists without a last-modified
    time is left out.

    Raises:
        unique_sdk.UniqueError: If the platform rejects or cannot serve the request.
    """
    response = await unique_sdk.Space.get_skills_async(
        user_id=user_id,
        company_id=company_id,
        space_id=space_id,
    )
    return {
        skill["contentId"]: updated_at
        for skill in response["skills"]
        if (updated_at := skill.get("updatedAt"))
    }
