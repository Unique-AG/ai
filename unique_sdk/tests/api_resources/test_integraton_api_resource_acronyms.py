import pytest

from unique_sdk.api_resources._acronyms import Acronyms


@pytest.mark.integration
class TestAcronyms:
    def test_get_acronyms(self, event):
        """Test retrieving acronyms synchronously in sandbox."""
        response = Acronyms.get(
            user_id=event.user_id,
            company_id=event.company_id,
        )
        assert isinstance(response, list)
        for data in response:
            assert "acronym" in data
            assert "text" in data

    @pytest.mark.asyncio
    async def test_get_acronyms_async(self, event):
        """Test retrieving acronyms asynchronously in sandbox."""
        response = await Acronyms.get_async(
            user_id=event.user_id,
            company_id=event.company_id,
        )
        assert isinstance(response, list)
        for data in response:
            assert "acronym" in data
            assert "text" in data
