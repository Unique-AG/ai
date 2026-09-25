"""env_map — company_id → env resolution (from the forwarded tool-call _meta) and
graceful content-id lookup. DB monkeypatched; no Postgres needed."""
import types

import pytest

import common.env_map as em


@pytest.fixture(autouse=True)
def _clear_url_env():
    """Reset the per-request URL-env ContextVar around every test so a value set by one
    test can never leak into the next (the middleware sets it fresh per request)."""
    em.set_url_env("")
    yield
    em.set_url_env("")


class _Ctx:
    """Minimal stand-in for a FastMCP Context carrying the forwarded `_meta`
    (node-chat sets `_meta.companyId` when `unique.app/auth/` forwarding is on)."""

    def __init__(self, company_id=None):
        meta = types.SimpleNamespace()
        if company_id:
            meta.companyId = company_id
        self.request_context = types.SimpleNamespace(meta=meta)


def test_env_from_ctx_maps_known_companies():
    assert em.env_from_ctx(_Ctx("304938286579712187")) == "sales"
    assert em.env_from_ctx(_Ctx("295318162692374905")) == "bnpp"
    assert em.env_from_ctx(_Ctx("225319369280852798")) == "qa"


def test_env_from_ctx_defaults_when_unresolvable():
    assert em.env_from_ctx(_Ctx()) == em.DEFAULT_ENV        # no companyId forwarded
    assert em.env_from_ctx(None) == em.DEFAULT_ENV          # no ctx at all
    assert em.env_from_ctx(_Ctx("999999")) == em.DEFAULT_ENV  # unknown company


def test_content_id_for_returns_mapped_id(monkeypatch):
    monkeypatch.setattr(em, "query_one", lambda sql, params=(): {"content_id": "cont_sales_x"})
    assert em.content_id_for("sales", "dashboard:CH-PB-0049217") == "cont_sales_x"


def test_content_id_for_degrades_to_empty(monkeypatch):
    monkeypatch.setattr(em, "query_one", lambda sql, params=(): None)
    assert em.content_id_for("sales", "dashboard:x") == ""   # no row → "" (→ filePath)
    assert em.content_id_for("sales", "") == ""              # no key
    assert em.content_id_for("", "dashboard:x") == ""        # no env

    def boom(sql, params=()):
        raise RuntimeError("no database")

    monkeypatch.setattr(em, "query_one", boom)
    assert em.content_id_for("sales", "dashboard:x") == ""   # DB error → "" (never raises)


def test_url_env_takes_priority(monkeypatch):
    # An explicit env on the connector URL wins over the forwarded company id.
    monkeypatch.setattr(em, "_env_from_request", lambda: "sales")
    assert em.env_from_ctx(_Ctx("225319369280852798")) == "sales"  # company=qa, URL=sales → sales
    monkeypatch.setattr(em, "_env_from_request", lambda: "")
    assert em.env_from_ctx(_Ctx("225319369280852798")) == "qa"     # no URL → fall back to company id


def test_path_env_signal_is_read_and_wins():
    # The path middleware records the env via set_url_env; _env_from_request reads it back
    # (no HTTP request needed) and it wins over the forwarded company id.
    em.set_url_env("sales")
    assert em._env_from_request() == "sales"
    assert em.env_from_ctx(_Ctx("225319369280852798")) == "sales"  # company=qa, path=sales → sales
    em.set_url_env("")
    assert em._env_from_request() == ""                            # cleared → no signal


def test_set_url_env_allowlists_known_envs():
    # Only a real, allowlisted env label is ever stored — guards the SQL key space and
    # means a stray/hostile path segment can never become the env.
    assert em.KNOWN_ENVS >= {"qa", "uat", "bnpp", "sales", "local"}
    em.set_url_env("../etc/passwd")
    assert em._env_from_request() == ""
    em.set_url_env("bogus")
    assert em._env_from_request() == ""
    em.set_url_env("uat")
    assert em._env_from_request() == "uat"
