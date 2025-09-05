# Language Models Overview

This page provides a comprehensive overview of all supported language models in the unique_toolkit.

## Model Properties

The following properties are documented for each model:

- **Name**: The display name of the model
- **Provider**: The service provider (Azure, LiteLLM, etc.)
- **Version**: Model version information
- **Encoder**: Tokenizer/encoder used within the code for the model
- **Token Limits**: Input, output, and total token limits
- **Capabilities**: Supported features (streaming, function calling, etc.)
- **Temperature Bounds**: Min/max temperature settings (if available)

## Quick Reference

### Token Limits Summary

| Model | Provider | Input Tokens | Output Tokens | Total Tokens |
|-------|----------|--------------|---------------|--------------|
| [AZURE_GPT_35_TURBO_0125](models/model_AZURE_GPT_35_TURBO_0125.md) | AZURE | 16,385 | 4,096 | 20,481 |
| [AZURE_GPT_41_2025_0414](models/model_AZURE_GPT_41_2025_0414.md) | AZURE | 1,047,576 | 32,768 | 1,080,344 |
| [AZURE_GPT_41_MINI_2025_0414](models/model_AZURE_GPT_41_MINI_2025_0414.md) | AZURE | 1,047,576 | 32,768 | 1,080,344 |
| [AZURE_GPT_41_NANO_2025_0414](models/model_AZURE_GPT_41_NANO_2025_0414.md) | AZURE | 1,047,576 | 32,768 | 1,080,344 |
| [AZURE_GPT_45_PREVIEW_2025_0227](models/model_AZURE_GPT_45_PREVIEW_2025_0227.md) | AZURE | 128,000 | 16,384 | 144,384 |
| [AZURE_GPT_4_0613](models/model_AZURE_GPT_4_0613.md) | AZURE | 3,276 | 4,915 | 8,191 |
| [AZURE_GPT_4_32K_0613](models/model_AZURE_GPT_4_32K_0613.md) | AZURE | 13,107 | 19,660 | 32,767 |
| [AZURE_GPT_4_TURBO_2024_0409](models/model_AZURE_GPT_4_TURBO_2024_0409.md) | AZURE | 128,000 | 4,096 | 132,096 |
| [AZURE_GPT_4o_2024_0513](models/model_AZURE_GPT_4o_2024_0513.md) | AZURE | 128,000 | 4,096 | 132,096 |
| [AZURE_GPT_4o_2024_0806](models/model_AZURE_GPT_4o_2024_0806.md) | AZURE | 128,000 | 16,384 | 144,384 |
| [AZURE_GPT_4o_2024_1120](models/model_AZURE_GPT_4o_2024_1120.md) | AZURE | 128,000 | 16,384 | 144,384 |
| [AZURE_GPT_4o_MINI_2024_0718](models/model_AZURE_GPT_4o_MINI_2024_0718.md) | AZURE | 128,000 | 16,384 | 144,384 |
| [AZURE_GPT_5_2025_0807](models/model_AZURE_GPT_5_2025_0807.md) | AZURE | 272,000 | 128,000 | 400,000 |
| [AZURE_GPT_5_CHAT_2025_0807](models/model_AZURE_GPT_5_CHAT_2025_0807.md) | AZURE | 128,000 | 16,384 | 144,384 |
| [AZURE_GPT_5_MINI_2025_0807](models/model_AZURE_GPT_5_MINI_2025_0807.md) | AZURE | 272,000 | 128,000 | 400,000 |
| [AZURE_GPT_5_NANO_2025_0807](models/model_AZURE_GPT_5_NANO_2025_0807.md) | AZURE | 272,000 | 128,000 | 400,000 |
| [AZURE_o1_2024_1217](models/model_AZURE_o1_2024_1217.md) | AZURE | 200,000 | 100,000 | 300,000 |
| [AZURE_o1_MINI_2024_0912](models/model_AZURE_o1_MINI_2024_0912.md) | AZURE | 128,000 | 65,536 | 193,536 |
| [AZURE_o3_2025_0416](models/model_AZURE_o3_2025_0416.md) | AZURE | 200,000 | 100,000 | 300,000 |
| [AZURE_o3_MINI_2025_0131](models/model_AZURE_o3_MINI_2025_0131.md) | AZURE | 200,000 | 100,000 | 300,000 |
| [AZURE_o4_MINI_2025_0416](models/model_AZURE_o4_MINI_2025_0416.md) | AZURE | 200,000 | 100,000 | 300,000 |
| [litellm:anthropic-claude-3-7-sonnet](models/model_litellm:anthropic-claude-3-7-sonnet.md) | LITELLM | 180,000 | 128,000 | 308,000 |
| [litellm:anthropic-claude-3-7-sonnet-thinking](models/model_litellm:anthropic-claude-3-7-sonnet-thinking.md) | LITELLM | 180,000 | 128,000 | 308,000 |
| [litellm:anthropic-claude-opus-4](models/model_litellm:anthropic-claude-opus-4.md) | LITELLM | 180,000 | 32,000 | 212,000 |
| [litellm:anthropic-claude-sonnet-4](models/model_litellm:anthropic-claude-sonnet-4.md) | LITELLM | 180,000 | 64,000 | 244,000 |
| [litellm:deepseek-r1](models/model_litellm:deepseek-r1.md) | LITELLM | 64,000 | 4,000 | 68,000 |
| [litellm:deepseek-v3-1](models/model_litellm:deepseek-v3-1.md) | LITELLM | 128,000 | 4,000 | 132,000 |
| [litellm:gemini-2-0-flash](models/model_litellm:gemini-2-0-flash.md) | LITELLM | 1,048,576 | 8,192 | 1,056,768 |
| [litellm:gemini-2-5-flash](models/model_litellm:gemini-2-5-flash.md) | LITELLM | 1,048,576 | 65,536 | 1,114,112 |
| [litellm:gemini-2-5-flash-lite-preview-06-17](models/model_litellm:gemini-2-5-flash-lite-preview-06-17.md) | LITELLM | 1,000,000 | 64,000 | 1,064,000 |
| [litellm:gemini-2-5-flash-preview-05-20](models/model_litellm:gemini-2-5-flash-preview-05-20.md) | LITELLM | 1,048,576 | 65,536 | 1,114,112 |
| [litellm:gemini-2-5-pro](models/model_litellm:gemini-2-5-pro.md) | LITELLM | 1,048,576 | 65,536 | 1,114,112 |
| [litellm:gemini-2-5-pro-exp-03-25](models/model_litellm:gemini-2-5-pro-exp-03-25.md) | LITELLM | 1,048,576 | 65,536 | 1,114,112 |
| [litellm:gemini-2-5-pro-preview-06-05](models/model_litellm:gemini-2-5-pro-preview-06-05.md) | LITELLM | 1,048,576 | 65,536 | 1,114,112 |
| [litellm:openai-gpt-4-1-mini](models/model_litellm:openai-gpt-4-1-mini.md) | LITELLM | 1,047,576 | 32,768 | 1,080,344 |
| [litellm:openai-gpt-4-1-nano](models/model_litellm:openai-gpt-4-1-nano.md) | LITELLM | 1,047,576 | 32,768 | 1,080,344 |
| [litellm:openai-gpt-5](models/model_litellm:openai-gpt-5.md) | LITELLM | 272,000 | 128,000 | 400,000 |
| [litellm:openai-gpt-5-chat](models/model_litellm:openai-gpt-5-chat.md) | LITELLM | 128,000 | 16,384 | 144,384 |
| [litellm:openai-gpt-5-mini](models/model_litellm:openai-gpt-5-mini.md) | LITELLM | 272,000 | 128,000 | 400,000 |
| [litellm:openai-gpt-5-nano](models/model_litellm:openai-gpt-5-nano.md) | LITELLM | 272,000 | 128,000 | 400,000 |
| [litellm:openai-o1](models/model_litellm:openai-o1.md) | LITELLM | 200,000 | 100,000 | 300,000 |
| [litellm:openai-o3](models/model_litellm:openai-o3.md) | LITELLM | 200,000 | 100,000 | 300,000 |
| [litellm:openai-o3-deep-research](models/model_litellm:openai-o3-deep-research.md) | LITELLM | 200,000 | 100,000 | 300,000 |
| [litellm:openai-o3-pro](models/model_litellm:openai-o3-pro.md) | LITELLM | 200,000 | 100,000 | 300,000 |
| [litellm:openai-o4-mini](models/model_litellm:openai-o4-mini.md) | LITELLM | 200,000 | 100,000 | 300,000 |
| [litellm:openai-o4-mini-deep-research](models/model_litellm:openai-o4-mini-deep-research.md) | LITELLM | 200,000 | 100,000 | 300,000 |
| [litellm:qwen-3-235B-A22B](models/model_litellm:qwen-3-235B-A22B.md) | LITELLM | 256,000 | 32,768 | 288,768 |
| [litellm:qwen-3-235B-A22B-thinking](models/model_litellm:qwen-3-235B-A22B-thinking.md) | LITELLM | 256,000 | 32,768 | 288,768 |
### Capabilities Matrix

| Model | Streaming | Function Calling | Structured Output | Reasoning |
|-------|-----------|------------------|-------------------|-----------|
| [AZURE_GPT_35_TURBO_0125](models/model_AZURE_GPT_35_TURBO_0125.md) | ❌ | ✅ | ❌ | ❌ |
| [AZURE_GPT_41_2025_0414](models/model_AZURE_GPT_41_2025_0414.md) | ✅ | ✅ | ✅ | ❌ |
| [AZURE_GPT_41_MINI_2025_0414](models/model_AZURE_GPT_41_MINI_2025_0414.md) | ✅ | ✅ | ✅ | ❌ |
| [AZURE_GPT_41_NANO_2025_0414](models/model_AZURE_GPT_41_NANO_2025_0414.md) | ✅ | ✅ | ✅ | ❌ |
| [AZURE_GPT_45_PREVIEW_2025_0227](models/model_AZURE_GPT_45_PREVIEW_2025_0227.md) | ✅ | ✅ | ✅ | ❌ |
| [AZURE_GPT_4_0613](models/model_AZURE_GPT_4_0613.md) | ✅ | ✅ | ❌ | ❌ |
| [AZURE_GPT_4_32K_0613](models/model_AZURE_GPT_4_32K_0613.md) | ✅ | ✅ | ❌ | ❌ |
| [AZURE_GPT_4_TURBO_2024_0409](models/model_AZURE_GPT_4_TURBO_2024_0409.md) | ✅ | ✅ | ❌ | ❌ |
| [AZURE_GPT_4o_2024_0513](models/model_AZURE_GPT_4o_2024_0513.md) | ✅ | ✅ | ❌ | ❌ |
| [AZURE_GPT_4o_2024_0806](models/model_AZURE_GPT_4o_2024_0806.md) | ✅ | ✅ | ✅ | ❌ |
| [AZURE_GPT_4o_2024_1120](models/model_AZURE_GPT_4o_2024_1120.md) | ✅ | ✅ | ✅ | ❌ |
| [AZURE_GPT_4o_MINI_2024_0718](models/model_AZURE_GPT_4o_MINI_2024_0718.md) | ✅ | ✅ | ❌ | ❌ |
| [AZURE_GPT_5_2025_0807](models/model_AZURE_GPT_5_2025_0807.md) | ✅ | ✅ | ✅ | ✅ |
| [AZURE_GPT_5_CHAT_2025_0807](models/model_AZURE_GPT_5_CHAT_2025_0807.md) | ✅ | ❌ | ❌ | ❌ |
| [AZURE_GPT_5_MINI_2025_0807](models/model_AZURE_GPT_5_MINI_2025_0807.md) | ✅ | ✅ | ✅ | ✅ |
| [AZURE_GPT_5_NANO_2025_0807](models/model_AZURE_GPT_5_NANO_2025_0807.md) | ✅ | ✅ | ✅ | ✅ |
| [AZURE_o1_2024_1217](models/model_AZURE_o1_2024_1217.md) | ✅ | ✅ | ✅ | ✅ |
| [AZURE_o1_MINI_2024_0912](models/model_AZURE_o1_MINI_2024_0912.md) | ✅ | ✅ | ✅ | ✅ |
| [AZURE_o3_2025_0416](models/model_AZURE_o3_2025_0416.md) | ✅ | ✅ | ✅ | ✅ |
| [AZURE_o3_MINI_2025_0131](models/model_AZURE_o3_MINI_2025_0131.md) | ✅ | ✅ | ✅ | ✅ |
| [AZURE_o4_MINI_2025_0416](models/model_AZURE_o4_MINI_2025_0416.md) | ✅ | ✅ | ✅ | ✅ |
| [litellm:anthropic-claude-3-7-sonnet](models/model_litellm:anthropic-claude-3-7-sonnet.md) | ✅ | ✅ | ❌ | ❌ |
| [litellm:anthropic-claude-3-7-sonnet-thinking](models/model_litellm:anthropic-claude-3-7-sonnet-thinking.md) | ✅ | ✅ | ❌ | ✅ |
| [litellm:anthropic-claude-opus-4](models/model_litellm:anthropic-claude-opus-4.md) | ✅ | ✅ | ❌ | ✅ |
| [litellm:anthropic-claude-sonnet-4](models/model_litellm:anthropic-claude-sonnet-4.md) | ✅ | ✅ | ❌ | ✅ |
| [litellm:deepseek-r1](models/model_litellm:deepseek-r1.md) | ✅ | ✅ | ✅ | ✅ |
| [litellm:deepseek-v3-1](models/model_litellm:deepseek-v3-1.md) | ❌ | ✅ | ✅ | ✅ |
| [litellm:gemini-2-0-flash](models/model_litellm:gemini-2-0-flash.md) | ✅ | ✅ | ✅ | ✅ |
| [litellm:gemini-2-5-flash](models/model_litellm:gemini-2-5-flash.md) | ✅ | ✅ | ✅ | ✅ |
| [litellm:gemini-2-5-flash-lite-preview-06-17](models/model_litellm:gemini-2-5-flash-lite-preview-06-17.md) | ✅ | ✅ | ✅ | ✅ |
| [litellm:gemini-2-5-flash-preview-05-20](models/model_litellm:gemini-2-5-flash-preview-05-20.md) | ✅ | ✅ | ✅ | ✅ |
| [litellm:gemini-2-5-pro](models/model_litellm:gemini-2-5-pro.md) | ✅ | ✅ | ✅ | ✅ |
| [litellm:gemini-2-5-pro-exp-03-25](models/model_litellm:gemini-2-5-pro-exp-03-25.md) | ✅ | ✅ | ✅ | ✅ |
| [litellm:gemini-2-5-pro-preview-06-05](models/model_litellm:gemini-2-5-pro-preview-06-05.md) | ✅ | ✅ | ✅ | ✅ |
| [litellm:openai-gpt-4-1-mini](models/model_litellm:openai-gpt-4-1-mini.md) | ✅ | ✅ | ✅ | ❌ |
| [litellm:openai-gpt-4-1-nano](models/model_litellm:openai-gpt-4-1-nano.md) | ✅ | ✅ | ✅ | ❌ |
| [litellm:openai-gpt-5](models/model_litellm:openai-gpt-5.md) | ✅ | ✅ | ✅ | ✅ |
| [litellm:openai-gpt-5-chat](models/model_litellm:openai-gpt-5-chat.md) | ✅ | ❌ | ❌ | ❌ |
| [litellm:openai-gpt-5-mini](models/model_litellm:openai-gpt-5-mini.md) | ✅ | ✅ | ✅ | ✅ |
| [litellm:openai-gpt-5-nano](models/model_litellm:openai-gpt-5-nano.md) | ✅ | ✅ | ✅ | ✅ |
| [litellm:openai-o1](models/model_litellm:openai-o1.md) | ✅ | ✅ | ✅ | ✅ |
| [litellm:openai-o3](models/model_litellm:openai-o3.md) | ✅ | ✅ | ✅ | ✅ |
| [litellm:openai-o3-deep-research](models/model_litellm:openai-o3-deep-research.md) | ✅ | ❌ | ❌ | ❌ |
| [litellm:openai-o3-pro](models/model_litellm:openai-o3-pro.md) | ❌ | ✅ | ✅ | ✅ |
| [litellm:openai-o4-mini](models/model_litellm:openai-o4-mini.md) | ✅ | ✅ | ✅ | ❌ |
| [litellm:openai-o4-mini-deep-research](models/model_litellm:openai-o4-mini-deep-research.md) | ✅ | ❌ | ❌ | ❌ |
| [litellm:qwen-3-235B-A22B](models/model_litellm:qwen-3-235B-A22B.md) | ✅ | ✅ | ✅ | ✅ |
| [litellm:qwen-3-235B-A22B-thinking](models/model_litellm:qwen-3-235B-A22B-thinking.md) | ✅ | ✅ | ✅ | ✅ |
## Usage

To use any of these models in your application:

```python
from unique_toolkit import LanguageModelName
from unique_toolkit.language_model.infos import LanguageModelInfo

# Get model information
model_name = LanguageModelName.AZURE_GPT_4o_2024_1120
info = LanguageModelInfo.from_name(model_name)

# Use the model in your application
# ... your code here
```

## Model Selection Guide

### For High-Volume Applications
- **Cost-effective**: GPT-4o Mini, GPT-5 Mini, Claude 3.7 Sonnet
- **Balanced**: GPT-4o, GPT-5, Claude Sonnet 4

### For Complex Reasoning
- **Advanced**: o1, o3, Claude 3.7 Sonnet Thinking
- **Research**: o3 Deep Research, o4 Mini Deep Research

### For Function Calling
- **Reliable**: GPT-4o, GPT-5, Claude Sonnet 4
- **Fast**: GPT-4o Mini, GPT-5 Mini

### For Structured Output
- **All modern models** support structured output capabilities

---

*Last updated: 2025-09-05*