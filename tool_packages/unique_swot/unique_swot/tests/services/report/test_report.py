"""Tests for report generation."""

from unique_swot.services.report import REPORT_TEMPLATE


class TestReportTemplate:
    """Test cases for report template."""

    def test_report_template_exists(self):
        """Test that report template is loaded."""
        assert REPORT_TEMPLATE is not None

    def test_report_template_render_basic(self):
        """Test rendering report template with basic data."""
        context = {
            "objective": "Test SWOT Analysis",
            "strengths": {
                "result": "Strong brand recognition",
            },
            "weaknesses": {
                "result": "Limited market share",
            },
            "opportunities": {
                "result": "Expanding into new markets",
            },
            "threats": {
                "result": "Increasing competition",
            },
        }

        rendered = REPORT_TEMPLATE.render(**context)

        # Template includes section headers
        assert "# SWOT Analysis Report" in rendered
        assert "## Strengths" in rendered
        assert "Strong brand recognition" in rendered
        assert "## Weaknesses" in rendered
        assert "Limited market share" in rendered
        assert "## Opportunities" in rendered
        assert "Expanding into new markets" in rendered
        assert "## Threats" in rendered
        assert "Increasing competition" in rendered

    def test_report_template_render_with_empty_sections(self):
        """Test rendering report template with empty sections."""
        context = {
            "objective": "Test Analysis",
            "strengths": {"result": ""},
            "weaknesses": {"result": ""},
            "opportunities": {"result": ""},
            "threats": {"result": ""},
        }

        rendered = REPORT_TEMPLATE.render(**context)

        # With empty results, only the main header should appear
        assert "# SWOT Analysis Report" in rendered
        assert isinstance(rendered, str)
        # Empty sections should not include their headers
        assert "## Strengths" not in rendered
        assert "## Weaknesses" not in rendered

    def test_report_template_render_with_markdown(self):
        """Test rendering report template with markdown content."""
        context = {
            "objective": "Test Analysis",
            "strengths": {
                "result": "# Strong Points\n- Point 1\n- Point 2",
            },
            "weaknesses": {
                "result": "**Weakness**: Low efficiency",
            },
            "opportunities": {
                "result": "- Opportunity 1\n- Opportunity 2",
            },
            "threats": {
                "result": "*Threat*: Market volatility",
            },
        }

        rendered = REPORT_TEMPLATE.render(**context)

        assert "Strong Points" in rendered
        assert "Point 1" in rendered
        assert "Low efficiency" in rendered
        assert "Opportunity 1" in rendered
        assert "Market volatility" in rendered

    def test_report_template_with_citations(self):
        """Test rendering report template with citations."""
        context = {
            "objective": "Analysis with Citations",
            "strengths": {
                "result": "Strong market position<sup>1</sup>",
            },
            "weaknesses": {
                "result": "Limited resources<sup>2</sup>",
            },
            "opportunities": {
                "result": "New markets<sup>3</sup>",
            },
            "threats": {
                "result": "Competition<sup>4</sup>",
            },
        }

        rendered = REPORT_TEMPLATE.render(**context)

        assert "<sup>1</sup>" in rendered
        assert "<sup>2</sup>" in rendered
        assert "<sup>3</sup>" in rendered
        assert "<sup>4</sup>" in rendered

    def test_report_template_with_long_content(self):
        """Test rendering report template with long content."""
        long_content = "This is a very long analysis. " * 100
        context = {
            "objective": "Detailed Analysis",
            "strengths": {"result": long_content},
            "weaknesses": {"result": long_content},
            "opportunities": {"result": long_content},
            "threats": {"result": long_content},
        }

        rendered = REPORT_TEMPLATE.render(**context)

        # Template should render all sections with long content
        assert "# SWOT Analysis Report" in rendered
        assert len(rendered) > 1000
        assert "This is a very long analysis." in rendered

    def test_report_template_with_special_characters(self):
        """Test rendering report template with special characters."""
        context = {
            "objective": "Analysis with Special Chars: & < > \" '",
            "strengths": {
                "result": "Revenue increased by 50% & profit margins improved",
            },
            "weaknesses": {
                "result": "Cost > Revenue in Q1",
            },
            "opportunities": {
                "result": 'Partnership with "Top Company"',
            },
            "threats": {
                "result": "Market share < competitors'",
            },
        }

        rendered = REPORT_TEMPLATE.render(**context)

        # Check that special characters are rendered correctly
        assert isinstance(rendered, str)
        assert len(rendered) > 0
        assert "50%" in rendered
        assert "Cost > Revenue" in rendered
        assert "Top Company" in rendered

    def test_report_template_render_returns_string(self):
        """Test that render returns a string."""
        context = {
            "objective": "Simple Test",
            "strengths": {"result": "Test"},
            "weaknesses": {"result": "Test"},
            "opportunities": {"result": "Test"},
            "threats": {"result": "Test"},
        }

        rendered = REPORT_TEMPLATE.render(**context)

        assert isinstance(rendered, str)
