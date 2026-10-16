"""Env-agnostic unit tests for person_lookup (WorldCheck screening) — the pure
matching engine over a small monkeypatched dataset (no DB)."""

import person_lookup as pl

FIXTURE = [
    {
        "wc_uid": "WC-0001", "entity_type": "Individual",
        "names": {"primary": "Anatoly Stepanovich Volkov", "original_script": "Анатолий Волков",
                  "aliases": ["A.S. Volkov"], "title": "H.E."},
        "demographics": {"gender": "Male", "date_of_birth": "1962-03-14",
                         "place_of_birth": "Yekaterinburg", "country_of_birth": "Russian Federation",
                         "nationalities": ["Russian Federation"], "country_of_residence": "Russian Federation"},
        "classification": {"categories": ["PEP"], "risk_rating": "High", "record_status": "Active"},
        "pep": {"is_pep": True, "class": "PEP Class 1", "position": "Deputy Minister"},
        "sanctions": {"is_sanctioned": False, "lists": [], "programs": []},
        "adverse_media": {"topics": []},
        "identifiers": {"passport_numbers": ["75 1234567"], "national_id": "6500 123456", "tax_id": "772801234567"},
        "address": "Moscow", "linked_associates": [], "sources": ["src"], "audit": {"last_updated": "2026-05-21"},
    },
    {
        "wc_uid": "WC-0002", "entity_type": "Individual",
        "names": {"primary": "Maria Esperanza Rodriguez", "aliases": []},
        "demographics": {"gender": "Female", "date_of_birth": "1971-09-22", "nationalities": ["Spain"],
                         "country_of_residence": "Spain"},
        "classification": {"categories": [], "risk_rating": "Low", "record_status": "Active"},
        "pep": {"is_pep": False}, "sanctions": {"is_sanctioned": False},
        "adverse_media": {"topics": []}, "identifiers": {}, "linked_associates": [], "sources": [],
    },
]


def _screen(monkeypatch, **q):
    monkeypatch.setattr(pl, "_records", lambda: FIXTURE)
    return pl._screen(q)


def test_helpers():
    assert pl._fold("Ánatólij  VOLKOV!") == "anatolij volkov"      # NFD + strip marks/punct
    assert pl._parse_dob("14.03.1962") == (1962, 3, 14)             # day-first
    assert pl._parse_dob("1962") == (1962, None, None)
    assert pl._norm_id("75-1234 567") == "751234567"               # spaces/dashes ignored
    assert pl._lev("volkov", "volkow") == 1


def test_name_match_exact(monkeypatch):
    r = _screen(monkeypatch, name="Anatoly Volkov")
    assert r["match_count"] >= 1
    top = r["matches"][0]
    assert top["record"]["wc_uid"] == "WC-0001"
    assert "name" in top["matched_on"] and top["match_score"] >= 0.45


def test_uid_lookup(monkeypatch):
    r = _screen(monkeypatch, wc_uid="WC-0002")
    assert r["match_count"] == 1
    assert r["matches"][0]["match_type"] == "uid_lookup" and r["matches"][0]["match_score"] == 1


def test_identifier_surfaces_record_despite_weak_name(monkeypatch):
    # An exact passport hit is near-conclusive even when the name doesn't match.
    r = _screen(monkeypatch, name="Zzz Nobody", passport_number="751234567")
    hit = next((m for m in r["matches"] if m["record"]["wc_uid"] == "WC-0001"), None)
    assert hit is not None
    assert hit["match_type"] == "exact_identifier" and "passport_number" in hit["matched_on"]


def test_dob_and_country_refine(monkeypatch):
    top = _screen(monkeypatch, name="Anatoly Volkov", date_of_birth="1962-03-14", country="RU")["matches"][0]
    assert "date_of_birth" in top["matched_on"]
    assert any(t.startswith("country:") for t in top["matched_on"])


def test_no_match(monkeypatch):
    r = _screen(monkeypatch, name="Xyzzy Nonexistent Person")
    assert r["match_count"] == 0 and "No matches" in r["message"]


def test_summarise_shape(monkeypatch):
    rec = _screen(monkeypatch, wc_uid="WC-0001")["matches"][0]["record"]
    assert rec["is_pep"] is True and rec["pep_class"] == "PEP Class 1"
    assert {"wc_uid", "primary_name", "categories", "identifiers", "risk_rating"} <= set(rec)
