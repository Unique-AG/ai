from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from core import get_search_engine
from core.malicious.generator import GeneratedPage
from core.malicious.schema import (
    MaliciousSearchParams,
    MaliciousSearchRequest,
    ThreatSkillDefinition,
    ThreatSkillType,
)
from core.malicious.threats import load_benign_skill, load_threats
from core.schema import SearchEngineType


class TestThreatSkillType:
    @pytest.mark.ai
    def test_enum_values(self):
        assert ThreatSkillType.INDIRECT_PROMPT_INJECTION == "indirect_prompt_injection"
        assert ThreatSkillType.LOCALHOST_ACCESS == "localhost_access"
        assert ThreatSkillType.DATA_EXFILTRATION == "data_exfiltration"

    @pytest.mark.ai
    def test_is_str_enum(self):
        assert isinstance(ThreatSkillType.INDIRECT_PROMPT_INJECTION, str)


class TestThreatSkillDefinition:
    @pytest.mark.ai
    def test_basic_creation(self):
        skill = ThreatSkillDefinition(
            name="Test Threat",
            description="A test threat",
            system_prompt="Generate malicious content",
        )
        assert skill.name == "Test Threat"
        assert skill.description == "A test threat"
        assert skill.system_prompt == "Generate malicious content"

    @pytest.mark.ai
    def test_camel_case_deserialization(self):
        data = {
            "name": "Test",
            "description": "desc",
            "systemPrompt": "prompt here",
        }
        skill = ThreatSkillDefinition.model_validate(data)
        assert skill.system_prompt == "prompt here"

    @pytest.mark.ai
    def test_camel_case_serialization(self):
        skill = ThreatSkillDefinition(
            name="Test", description="desc", system_prompt="prompt"
        )
        dumped = skill.model_dump(by_alias=True)
        assert "systemPrompt" in dumped


class TestMaliciousSearchParams:
    @pytest.mark.ai
    def test_defaults(self):
        params = MaliciousSearchParams()
        assert params.fetch_size == 5
        assert params.threat_rate == 0.3
        assert params.model_name == "AZURE_GPT_4o_2024_1120"
        assert params.enabled_threats is None
        assert params.custom_threats is None

    @pytest.mark.ai
    def test_custom_values_camel_case(self):
        data = {
            "fetchSize": 10,
            "threatRate": 0.5,
            "modelName": "custom-model",
            "enabledThreats": ["indirect_prompt_injection", "localhost_access"],
            "customThreats": [
                {
                    "name": "Custom",
                    "description": "custom threat",
                    "systemPrompt": "do something",
                }
            ],
        }
        params = MaliciousSearchParams.model_validate(data)
        assert params.fetch_size == 10
        assert params.threat_rate == 0.5
        assert params.enabled_threats == [
            ThreatSkillType.INDIRECT_PROMPT_INJECTION,
            ThreatSkillType.LOCALHOST_ACCESS,
        ]
        assert len(params.custom_threats) == 1
        assert params.custom_threats[0].name == "Custom"

    @pytest.mark.ai
    def test_fetch_size_bounds(self):
        with pytest.raises(Exception):
            MaliciousSearchParams.model_validate({"fetchSize": 0})
        with pytest.raises(Exception):
            MaliciousSearchParams.model_validate({"fetchSize": 21})

    @pytest.mark.ai
    def test_threat_rate_bounds(self):
        with pytest.raises(Exception):
            MaliciousSearchParams.model_validate({"threatRate": -0.1})
        with pytest.raises(Exception):
            MaliciousSearchParams.model_validate({"threatRate": 1.1})


class TestMaliciousSearchRequest:
    @pytest.mark.ai
    def test_defaults(self):
        req = MaliciousSearchRequest(query="test query")
        assert req.search_engine == SearchEngineType.MALICIOUS
        assert req.timeout == 10
        assert req.params.fetch_size == 5

    @pytest.mark.ai
    def test_camel_case(self):
        data = {
            "searchEngine": "malicious",
            "query": "test",
            "timeout": 60,
            "params": {
                "fetchSize": 3,
                "threatRate": 0.5,
                "enabledThreats": ["data_exfiltration"],
            },
        }
        req = MaliciousSearchRequest.model_validate(data)
        assert req.params.fetch_size == 3
        assert req.params.threat_rate == 0.5
        assert req.params.enabled_threats == [ThreatSkillType.DATA_EXFILTRATION]


class TestThreatLoading:
    @pytest.mark.ai
    def test_load_all_threats(self):
        threats = load_threats(enabled=None)
        assert len(threats) == len(ThreatSkillType)
        names = {t.name for t in threats}
        assert "Indirect Prompt Injection" in names
        assert "Localhost Access" in names
        assert "Data Exfiltration" in names

    @pytest.mark.ai
    def test_load_specific_threats(self):
        threats = load_threats(
            enabled=[ThreatSkillType.INDIRECT_PROMPT_INJECTION]
        )
        assert len(threats) == 1
        assert threats[0].name == "Indirect Prompt Injection"

    @pytest.mark.ai
    def test_load_benign_skill(self):
        skill = load_benign_skill()
        assert skill.name == "Benign Content"
        assert "legitimate" in skill.system_prompt.lower()

    @pytest.mark.ai
    def test_loaded_threats_are_valid_definitions(self):
        threats = load_threats(enabled=None)
        for threat in threats:
            assert isinstance(threat, ThreatSkillDefinition)
            assert threat.name
            assert threat.description
            assert threat.system_prompt


class TestFactory:
    @pytest.mark.ai
    def test_malicious_engine_registered(self):
        from core.malicious.search import MaliciousSearchEngine

        engine_cls = get_search_engine(SearchEngineType.MALICIOUS)
        assert engine_cls is MaliciousSearchEngine


class TestGeneratedPage:
    @pytest.mark.ai
    def test_basic_creation(self):
        page = GeneratedPage(
            url="https://example.com/page",
            title="Test Page",
            snippet="A test page snippet",
            content="<html><body>Hello</body></html>",
        )
        assert page.url == "https://example.com/page"
        assert page.title == "Test Page"
        assert page.snippet == "A test page snippet"
        assert "<html>" in page.content


class TestMaliciousSearchEngine:
    @pytest.mark.ai
    @patch("core.malicious.search.init_malicious_sdk")
    async def test_search_returns_results(self, mock_init_sdk):
        from core.malicious.search import MaliciousSearchEngine

        mock_settings = MagicMock()
        mock_settings.auth.company_id.get_secret_value.return_value = "test-company"
        mock_settings.auth.user_id.get_secret_value.return_value = "test-user"
        mock_init_sdk.return_value = mock_settings

        fake_page = GeneratedPage(
            url="https://fake.com",
            title="Fake",
            snippet="snippet",
            content="<html>content</html>",
        )

        with patch("core.malicious.search.LanguageModelService"), patch(
            "core.malicious.search.generate_page",
            new_callable=AsyncMock,
            return_value=fake_page,
        ):
            params = MaliciousSearchParams(fetch_size=3, threat_rate=0.5)
            engine = MaliciousSearchEngine(params=params)
            results = await engine.search("test query")

        assert len(results) == 3
        assert all(r.url == "https://fake.com" for r in results)

    @pytest.mark.ai
    @patch("core.malicious.search.init_malicious_sdk")
    async def test_search_handles_none_pages(self, mock_init_sdk):
        from core.malicious.search import MaliciousSearchEngine

        mock_settings = MagicMock()
        mock_settings.auth.company_id.get_secret_value.return_value = "test-company"
        mock_settings.auth.user_id.get_secret_value.return_value = "test-user"
        mock_init_sdk.return_value = mock_settings

        with patch("core.malicious.search.LanguageModelService"), patch(
            "core.malicious.search.generate_page",
            new_callable=AsyncMock,
            return_value=None,
        ):
            params = MaliciousSearchParams(fetch_size=2, threat_rate=0.0)
            engine = MaliciousSearchEngine(params=params)
            results = await engine.search("test query")

        assert len(results) == 0

    @pytest.mark.ai
    @patch("core.malicious.search.init_malicious_sdk")
    async def test_custom_threats_merged(self, mock_init_sdk):
        from core.malicious.search import MaliciousSearchEngine

        mock_settings = MagicMock()
        mock_settings.auth.company_id.get_secret_value.return_value = "test-company"
        mock_settings.auth.user_id.get_secret_value.return_value = "test-user"
        mock_init_sdk.return_value = mock_settings

        custom = [
            ThreatSkillDefinition(
                name="Custom Threat",
                description="A custom threat",
                system_prompt="custom prompt",
            )
        ]

        with patch("core.malicious.search.LanguageModelService"):
            params = MaliciousSearchParams(
                fetch_size=1,
                threat_rate=1.0,
                enabled_threats=[ThreatSkillType.INDIRECT_PROMPT_INJECTION],
                custom_threats=custom,
            )
            engine = MaliciousSearchEngine(params=params)

        assert len(engine.threat_pool) == 2
        pool_names = {t.name for t in engine.threat_pool}
        assert "Indirect Prompt Injection" in pool_names
        assert "Custom Threat" in pool_names
