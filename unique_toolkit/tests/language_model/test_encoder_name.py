import pytest
import tiktoken

from unique_toolkit.language_model.infos import EncoderName


@pytest.mark.ai
class TestEncoderNameGetEncoder:
    def test_cl100k_base_encoder(self):
        encode = EncoderName.CL100K_BASE.get_encoder()

        assert callable(encode)
        result = encode("Hello world")
        assert isinstance(result, list)
        assert all(isinstance(x, int) for x in result)

        expected = tiktoken.get_encoding("cl100k_base").encode("Hello world")
        assert result == expected

    def test_o200k_base_encoder(self):
        encode = EncoderName.O200K_BASE.get_encoder()
        result = encode("Hello world")

        expected = tiktoken.get_encoding("o200k_base").encode("Hello world")
        assert result == expected

    def test_qwen_encoder(self):
        encode = EncoderName.QWEN.get_encoder()

        assert callable(encode)
        result = encode("Hello world")
        assert isinstance(result, list)
        assert all(isinstance(x, int) for x in result)
        assert len(result) > 0

    def test_deepseek_encoder(self):
        encode = EncoderName.DEEPSEEK.get_encoder()

        assert callable(encode)
        result = encode("Hello world")
        assert isinstance(result, list)
        assert all(isinstance(x, int) for x in result)
        assert len(result) > 0

    def test_qwen_vs_tiktoken_different(self):
        qwen_encode = EncoderName.QWEN.get_encoder()
        tiktoken_encode = EncoderName.CL100K_BASE.get_encoder()

        text = "你好世界"
        qwen_result = qwen_encode(text)
        tiktoken_result = tiktoken_encode(text)

        assert qwen_result != tiktoken_result

    def test_empty_string(self):
        encode = EncoderName.CL100K_BASE.get_encoder()
        result = encode("")
        assert result == []
