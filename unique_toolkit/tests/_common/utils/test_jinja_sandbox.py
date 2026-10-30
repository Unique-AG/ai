import jinja2
import pytest
from jinja2.exceptions import SecurityError, TemplateSyntaxError

from unique_toolkit._common.utils.jinja.render import render_template
from unique_toolkit._common.utils.jinja.sandbox import (
    sandboxed_template,
    validate_sandboxed_template,
)
from unique_toolkit._common.utils.jinja.schema import Jinja2PromptParams

RCE_PAYLOADS = [
    "{{ namespace.__init__.__globals__.os.popen('id').read() }}",
    "{{ cycler.__init__.__globals__.os.popen('id').read() }}",
    "{{ lipsum.__globals__['os'].popen('id').read() }}",
    "{{ ''.__class__.__mro__[1].__subclasses__() }}",
]

LEAK_PAYLOADS = [
    "{{ self._TemplateReference__context }}",
    "{{ '{0.__class__}'.format(1) }}",
    "{{ namespace.__init__ }}",
]

BENIGN_TEMPLATE = "a\n    {% if flag %}\n{{ name | upper }}\n    {% endif %}\n{% for t in tools %}{{ t.name }}{% if not loop.last %}, {% endif %}{% endfor %}"


class _Params(Jinja2PromptParams):
    name: str


@pytest.mark.ai
class TestSandboxedTemplate:
    @pytest.mark.parametrize("lstrip_blocks", [False, True])
    def test_renders_benign_template_like_plain_jinja(
        self, lstrip_blocks: bool
    ) -> None:
        context = {"flag": True, "name": "ada", "tools": [{"name": "a"}, {"name": "b"}]}

        sandboxed = sandboxed_template(BENIGN_TEMPLATE, lstrip_blocks=lstrip_blocks)
        plain = jinja2.Template(BENIGN_TEMPLATE, lstrip_blocks=lstrip_blocks)

        assert sandboxed.render(**context) == plain.render(**context)

    @pytest.mark.parametrize("payload", RCE_PAYLOADS)
    def test_rejects_gadget_chains_into_python_internals(self, payload: str) -> None:
        with pytest.raises(SecurityError):
            sandboxed_template(payload).render()

    @pytest.mark.parametrize("payload", LEAK_PAYLOADS)
    def test_renders_unsafe_attributes_as_empty(self, payload: str) -> None:
        assert sandboxed_template(payload).render() == ""

    def test_rejects_gadget_chains_through_context_objects(self) -> None:
        class Tool:
            name = "search"

        with pytest.raises(SecurityError):
            sandboxed_template(
                "{{ tool.__class__.__init__.__globals__['os'].popen('id').read() }}"
            ).render(tool=Tool())


@pytest.mark.ai
class TestValidateSandboxedTemplate:
    def test_accepts_benign_template(self) -> None:
        assert validate_sandboxed_template(BENIGN_TEMPLATE) == BENIGN_TEMPLATE

    @pytest.mark.parametrize(
        "payload",
        [
            *RCE_PAYLOADS,
            "{{ self._TemplateReference__context }}",
            "{{ namespace.__init__ }}",
            "{{ obj.mro() }}",
            "{{ gen.gi_frame }}",
        ],
    )
    def test_rejects_unsafe_attribute_access_statically(self, payload: str) -> None:
        with pytest.raises(SecurityError):
            validate_sandboxed_template(payload)

    @pytest.mark.parametrize("malformed", ["{{ unclosed", "{{ x | unknown_filter }}"])
    def test_rejects_syntax_and_filter_errors(self, malformed: str) -> None:
        with pytest.raises(TemplateSyntaxError):
            validate_sandboxed_template(malformed)


@pytest.mark.ai
class TestRenderTemplateIsSandboxed:
    @pytest.mark.parametrize("payload", RCE_PAYLOADS)
    def test_render_template_rejects_payload(self, payload: str) -> None:
        with pytest.raises(SecurityError):
            render_template(payload, {"name": "x"})

    @pytest.mark.parametrize("payload", RCE_PAYLOADS)
    def test_prompt_params_render_template_rejects_payload(self, payload: str) -> None:
        with pytest.raises(SecurityError):
            _Params(name="x").render_template(payload)

    def test_render_template_still_renders_params(self) -> None:
        assert render_template("Hi {{ name }}", _Params(name="Ada")) == "Hi Ada"
