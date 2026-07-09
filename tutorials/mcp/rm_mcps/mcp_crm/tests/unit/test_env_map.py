"""env_map — company_id → env resolution (from the forwarded tool-call _meta) and
graceful content-id lookup. DB monkeypatched; no Postgres needed."""
import types

import common.env_map as em


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
    # An explicit ?env= on the connector URL wins over the forwarded company id.
    monkeypatch.setattr(em, "_env_from_request", lambda: "sales")
    assert em.env_from_ctx(_Ctx("225319369280852798")) == "sales"  # company=qa, URL=sales → sales
    monkeypatch.setattr(em, "_env_from_request", lambda: "")
    assert em.env_from_ctx(_Ctx("225319369280852798")) == "qa"     # no URL → fall back to company id
