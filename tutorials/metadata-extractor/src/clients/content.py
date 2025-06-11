import httpx
from src.clients.token import TokenClient
from src.settings import get_settings


class ContentClient:
    def __init__(self):
        self.settings = get_settings()
        self.url = self.settings.content_url
        self.token_client = TokenClient()

    async def get_by_id(self, content_id):
        # Define the GraphQL query and variables
        query = """
        query Query($where: ContentWhereInput) {
        content(where: $where) {
            key
            appliedIngestionConfig
            metadata
            chunks {
                text
            }
        }
        }
        """

        variables = {"where": {"id": {"equals": content_id}}}
        result = await self._post(self.url, query, variables)
        content = result["data"]["content"][0]

        if not content:
            msg = f"Content with ID {content_id} not found"
            raise Exception(msg)
        return content

    async def get_all_in_scope(self, scope_id):
        query = """
        query Query($where: ContentWhereInput) {
        content(where: $where) {
            id
            key
            title
            metadata
        }
        }
        """
        variables = {"where": {"ownerId": {"equals": scope_id}}}
        result = await self._post(self.url, query, variables)
        return result

    async def update_metadata(self, content_id, metadata):
        # Define the GraphQL query and variables
        query = """
        mutation ContentUpdate($contentId: String!, $input: ContentUpdateInput!) {
            contentUpdate(contentId: $contentId, input: $input) {
                ingestionConfig
                appliedIngestionConfig
                metadata
            }
        }
        """
        variables = {"contentId": content_id, "input": {"metadata": metadata}}
        await self._post(self.url, query, variables)

    async def mark_rebuild_metadata(self, content_id):
        query = """
        mutation MarkAllForRebuidingMetadata($where: ContentWhereInput) {
            markAllForRebuidingMetadata(where: $where)
        }
        """
        variables = {"where": {"id": {"equals": content_id}}}
        await self._post(self.url, query, variables)

    async def mark_rebuild_metadata_by_ids(self, content_ids):
        query = """
        mutation MarkAllForRebuidingMetadata($where: ContentWhereInput) {
            markAllForRebuidingMetadata(where: $where)
        }
        """
        variables = {"where": {"id": {"in": content_ids}}}
        await self._post(self.url, query, variables)

    async def rebuild_metadata(self):
        query = """
        mutation RebuildMetadata {
            rebuildMetadata
        }
        """
        variables = {}
        await self._post(self.url, query, variables)

    async def _post(self, url, query, variables):
        """
        Makes a GraphQL request to the specified URL with the given token and content ID.

        Args:
            url (str): The GraphQL endpoint URL.
            query (str): The GraphQL query.
            variables (dict): Variables for the GraphQL query.

        Returns:
            dict: The JSON response from the GraphQL server.
        """
        token = await self.token_client.get_access_token()

        # Define the headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        # Define the payload
        payload = {"query": query, "variables": variables}
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            return response.json()
