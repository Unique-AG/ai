# %%
from pathlib import Path
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit import LanguageModelName
from datetime import date
from jinja2 import Template
from collections import defaultdict


def model_info_to_markdown(info: LanguageModelInfo) -> str:
    """Convert a LanguageModelInfo object to markdown format using Jinja template."""
    
    # Load the model template
    model_template_path = Path(__file__).parent / "model_template.jinja2"
    with model_template_path.open("r") as f:
        template_content = f.read()
    
    template = Template(template_content)
    
    # Render the template with the model info
    markdown = template.render(info=info)
    
    return markdown

# Generate individual model files
prefix = "model"
models_data = []

# Create models directory
models_dir = Path(__file__).parent / "models"
models_dir.mkdir(exist_ok=True)

for m in LanguageModelName:
    info = LanguageModelInfo.from_name(m)
    markdown_output = model_info_to_markdown(info)
    file_path = models_dir / f"{prefix}_{m.value}.md"
    with file_path.open("w") as f:
        f.write(markdown_output)
    
    # Store model data for overview generation
    models_data.append({
        'info': info,
        'filename': f"{prefix}_{m.value}.md",
        'display_name': info.display_name,
        'provider': info.provider,
        'version': info.version,
        'token_limits': info.token_limits,
        'capabilities': [cap.value for cap in info.capabilities]
    })

# Generate overview page using Jinja template
template_path = Path(__file__).parent / "overview_template.jinja2"
with template_path.open("r") as f:
    template_content = f.read()

template = Template(template_content)

# Group models by provider
models_by_provider = defaultdict(list)
for model_data in models_data:
    provider_name = model_data['provider'].value if hasattr(model_data['provider'], 'value') else str(model_data['provider'])
    models_by_provider[provider_name].append(model_data)

# Sort models within each provider
for provider_models in models_by_provider.values():
    provider_models.sort(key=lambda x: x['display_name'])

# Render the template
overview_content = template.render(
    models_by_provider=dict(models_by_provider),
    all_models=sorted(models_data, key=lambda x: x['display_name']),
    generation_date=date.today().strftime("%Y-%m-%d")
)

# Write the overview page
overview_path = Path(__file__).parent / "language_model_overview.md"
with overview_path.open("w") as f:
    f.write(overview_content)

print(f"Generated overview page: {overview_path}")
print(f"Generated {len(models_data)} individual model files")

# %%
