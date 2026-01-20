from unique_follow_up_questions.config import FollowUpQuestionsConfig
from unique_stock_ticker.config import StockTickerConfig

from unique_orchestrator.config import EvaluationConfig, UniqueAIServices


class TestUniqueAIServicesStockTickerConfigValidator:
    """Test suite for UniqueAIServices.check_if_stock_ticker_config_is_none validator"""

    def test_returns_default_config_when_none(self):
        """Test that a default StockTickerConfig with enabled=False is returned when config is None"""
        services = UniqueAIServices(stock_ticker_config=None)

        assert isinstance(services.stock_ticker_config, StockTickerConfig)
        assert services.stock_ticker_config.enabled is False

    def test_returns_default_config_when_empty_dict(self):
        """Test that a default StockTickerConfig with enabled=False is returned when config is empty dict"""
        services = UniqueAIServices(stock_ticker_config={})

        assert isinstance(services.stock_ticker_config, StockTickerConfig)
        assert services.stock_ticker_config.enabled is False

    def test_returns_provided_config_when_valid(self):
        """Test that the provided config is returned when it's a valid StockTickerConfig"""
        custom_config = StockTickerConfig(enabled=True)
        services = UniqueAIServices(stock_ticker_config=custom_config)

        assert services.stock_ticker_config.enabled is True

    def test_returns_provided_dict_config_when_valid(self):
        """Test that the provided dict config is used when it contains valid data"""
        services = UniqueAIServices(stock_ticker_config={"enabled": True})

        assert services.stock_ticker_config.enabled is True


class TestUniqueAIServicesFollowUpQuestionsConfigValidator:
    """Test suite for UniqueAIServices.check_if_follow_up_questions_config_is_one validator"""

    def test_returns_default_config_when_none(self):
        """Test that a default FollowUpQuestionsConfig with number_of_questions=0 is returned when config is None"""
        services = UniqueAIServices(follow_up_questions_config=None)

        assert isinstance(
            services.follow_up_questions_config, FollowUpQuestionsConfig
        )
        assert services.follow_up_questions_config.number_of_questions == 0

    def test_returns_default_config_when_empty_dict(self):
        """Test that a default FollowUpQuestionsConfig with number_of_questions=0 is returned when config is empty dict"""
        services = UniqueAIServices(follow_up_questions_config={})

        assert isinstance(
            services.follow_up_questions_config, FollowUpQuestionsConfig
        )
        assert services.follow_up_questions_config.number_of_questions == 0

    def test_returns_provided_config_when_valid(self):
        """Test that the provided config is returned when it's a valid FollowUpQuestionsConfig"""
        custom_config = FollowUpQuestionsConfig(number_of_questions=5)
        services = UniqueAIServices(follow_up_questions_config=custom_config)

        assert services.follow_up_questions_config.number_of_questions == 5

    def test_returns_provided_dict_config_when_valid(self):
        """Test that the provided dict config is used when it contains valid data"""
        services = UniqueAIServices(follow_up_questions_config={"number_of_questions": 7})

        assert services.follow_up_questions_config.number_of_questions == 7


class TestUniqueAIServicesEvaluationConfigValidator:
    """Test suite for UniqueAIServices.check_if_evaluation_config_is_none validator"""

    def test_returns_default_config_when_none(self):
        """Test that a default EvaluationConfig is returned when config is None"""
        services = UniqueAIServices(evaluation_config=None)

        assert isinstance(services.evaluation_config, EvaluationConfig)

    def test_returns_default_config_when_empty_dict(self):
        """Test that a default EvaluationConfig is returned when config is empty dict"""
        services = UniqueAIServices(evaluation_config={})

        assert isinstance(services.evaluation_config, EvaluationConfig)

    def test_returns_provided_config_when_valid(self):
        """Test that the provided config is returned when it's a valid EvaluationConfig"""
        custom_config = EvaluationConfig()
        services = UniqueAIServices(evaluation_config=custom_config)

        assert isinstance(services.evaluation_config, EvaluationConfig)

    def test_returns_provided_dict_config_when_valid(self):
        """Test that the provided dict config is used when it contains valid data"""
        services = UniqueAIServices(evaluation_config={"hallucination_config": {}})

        assert isinstance(services.evaluation_config, EvaluationConfig)

