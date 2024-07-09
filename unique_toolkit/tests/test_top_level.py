def test_top_level_log_import():
    from unique_toolkit import load_logging_config

    assert load_logging_config is not None
