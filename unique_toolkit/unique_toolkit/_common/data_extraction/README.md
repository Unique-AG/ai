# Data Extraction Module

This module provides a flexible framework for extracting structured data from text using language models. It supports both basic and augmented data extraction capabilities.

## Overview

The module consists of two main components:

1. **Basic Data Extraction**: Uses language models to extract structured data from text based on a provided schema.
2. **Augmented Data Extraction**: Extends basic extraction by adding extra fields to the output schema while maintaining the original data structure.

## Components

### Base Classes

- `BaseDataExtractor`: Abstract base class that defines the interface for data extraction
- `BaseDataExtractionResult`: Generic base class for extraction results

### Basic Extraction

- `StructuredOutputDataExtractor`: Implements basic data extraction using language models
- `StructuredOutputDataExtractorConfig`: Configuration for the basic extractor

### Augmented Extraction

- `AugmentedDataExtractor`: Extends basic extraction with additional fields
- `AugmentedDataExtractionResult`: Result type for augmented extraction

## Usage Examples

### Basic Data Extraction

```python
from pydantic import BaseModel
from unique_toolkit._common.data_extraction import StructuredOutputDataExtractor, StructuredOutputDataExtractorConfig
from unique_toolkit import LanguageModelService

# Define your schema
class PersonInfo(BaseModel):
    name: str
    age: int
    occupation: str

# Create the extractor
config = StructuredOutputDataExtractorConfig()
lm_service = LanguageModelService()  # Configure as needed
extractor = StructuredOutputDataExtractor(config, lm_service)

# Extract data
text = "John is 30 years old and works as a software engineer."
result = await extractor.extract_data_from_text(text, PersonInfo)
print(result.data)  # PersonInfo(name="John", age=30, occupation="software engineer")
```

### Augmented Data Extraction

```python
from pydantic import BaseModel, Field
from _common.data_extraction import AugmentedDataExtractor, StructuredOutputDataExtractor

# Define your base schema
class PersonInfo(BaseModel):
    name: str
    age: int

# Create base extractor
base_extractor = StructuredOutputDataExtractor(...)

# Create augmented extractor with confidence scores
augmented_extractor = AugmentedDataExtractor(
    base_extractor,
    confidence=float,
    source=("extracted", Field(description="Source of the information"))
)

# Extract data
text = "John is 30 years old."
result = await augmented_extractor.extract_data_from_text(text, PersonInfo)
print(result.data)  # Original PersonInfo
print(result.augmented_data)  # Contains additional fields
```

## Configuration

The `StructuredOutputDataExtractorConfig` allows customization of:

- Language model selection
- System and user prompt templates
- Schema enforcement settings

## Best Practices

1. Always define clear Pydantic models for your extraction schemas
2. Use augmented extraction when you need additional metadata
3. Consider using strict mode for augmented extraction when you want to enforce schema compliance
4. Customize prompts for better extraction results in specific domains 