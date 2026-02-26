import pytest
import tiktoken

from unique_toolkit.language_model.infos import EncoderName


@pytest.mark.ai
class TestEncoderNameGetDecoder:
    def test_cl100k_base_decoder(self):
        decode = EncoderName.CL100K_BASE.get_decoder()

        assert callable(decode)
        tokens = tiktoken.get_encoding("cl100k_base").encode("Hello world")
        result = decode(tokens)
        assert isinstance(result, str)
        assert result == "Hello world"

    def test_o200k_base_decoder(self):
        decode = EncoderName.O200K_BASE.get_decoder()
        tokens = tiktoken.get_encoding("o200k_base").encode("Hello world")
        result = decode(tokens)
        assert result == "Hello world"

    def test_qwen_decoder(self):
        encode = EncoderName.QWEN.get_encoder()
        decode = EncoderName.QWEN.get_decoder()

        assert callable(decode)
        tokens = encode("Hello world")
        result = decode(tokens)
        assert isinstance(result, str)
        assert result == "Hello world"

    def test_deepseek_decoder(self):
        encode = EncoderName.DEEPSEEK.get_encoder()
        decode = EncoderName.DEEPSEEK.get_decoder()

        assert callable(decode)
        tokens = encode("Hello world")
        result = decode(tokens)
        assert isinstance(result, str)
        assert result == "Hello world"

    def test_roundtrip_cl100k(self):
        encode = EncoderName.CL100K_BASE.get_encoder()
        decode = EncoderName.CL100K_BASE.get_decoder()

        text = "The quick brown fox jumps over the lazy dog."
        assert decode(encode(text)) == text

    def test_roundtrip_qwen_unicode(self):
        encode = EncoderName.QWEN.get_encoder()
        decode = EncoderName.QWEN.get_decoder()

        text = "你好世界"
        assert decode(encode(text)) == text

    def test_empty_tokens(self):
        decode = EncoderName.CL100K_BASE.get_decoder()
        result = decode([])
        assert result == ""
