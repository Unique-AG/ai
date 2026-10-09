"""Person screening domain — WorldCheck (LSEG) synthetic watchlist lookup.

Port of the n8n "WorldCheck Screening Lookup" tool. Fuzzy-screens a person or
entity by name (+ optional refinements: country, nationality, date of birth,
place of birth, gender, entity type, passport / national-id / tax-id, or a direct
``wc_uid``) against the SYNTHETIC watchlist seeded in ``sql/worldcheck.sql``,
returning partial and exact matches with a 0-1 score.

The matching engine (Unicode-aware name folding + token/Levenshtein scoring,
country/nationality aliasing, multi-format DOB tolerance, identifier
normalisation) mirrors the n8n JS one-for-one. SYNTHETIC data — KYC/AML tool
testing only; never a compliance decision on its own.
"""

import json
import re
import unicodedata
from typing import Annotated

from pydantic import Field

from common.db import query_all

SOURCE = "WorldCheck LSEG (SYNTHETIC)"


def _records() -> list[dict]:
    """All watchlist records (the screen scores in-memory over the full set)."""
    return [r["data"] for r in query_all("SELECT data FROM worldcheck ORDER BY wc_uid")]


def _to_int(v, default: int) -> int:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        try:
            return int(float(str(v).strip()))
        except (TypeError, ValueError):
            return default


# ---------- text helpers (Unicode-aware: Latin, Cyrillic, Arabic, CJK…) ----------
def _fold(s) -> str:
    s = unicodedata.normalize("NFD", "" if s is None else str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))  # strip diacritics (\p{M})
    s = s.lower()
    s = "".join(c if (c.isalnum() or c.isspace()) else " " for c in s)  # keep \p{L}\p{N}
    return " ".join(s.split())


def _tokenize(s) -> list[str]:
    f = _fold(s)
    return [t for t in f.split(" ") if len(t) > 1] if f else []


def _rec_names(r: dict) -> list[str]:
    n = r.get("names") or {}
    return [x for x in ([n.get("primary"), n.get("original_script")] + (n.get("aliases") or [])) if x]


def _lev(a: str, b: str) -> int:
    m, n = len(a), len(b)
    if not m:
        return n
    if not n:
        return m
    prev = list(range(n + 1))
    cur = [0] * (n + 1)
    for i in range(1, m + 1):
        cur[0] = i
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev, cur = cur, prev
    return prev[n]


def _token_sim(t: str, x: str) -> float:
    if t == x:
        return 1.0
    big, small = max(len(t), len(x)), min(len(t), len(x))
    if (x.startswith(t) or t.startswith(x)) and small >= 3:
        return 0.85
    if big >= 4:
        d = _lev(t, x)
        allow = 2 if big >= 7 else 1
        if d <= allow:
            return 0.8 if d == 1 else 0.65
    return 0.0


def _name_score(qn: str, r: dict) -> float:
    q_tokens = _tokenize(qn)
    if not q_tokens:
        return 0.0
    best, fq = 0.0, _fold(qn)
    for nm in _rec_names(r):
        rt = _tokenize(nm)
        if not rt:
            continue
        hit = 0.0
        for t in q_tokens:
            best_tok = 0.0
            for x in rt:
                sim = _token_sim(t, x)
                if sim > best_tok:
                    best_tok = sim
                if sim == 1.0:
                    break
            hit += best_tok
        score = hit / len(q_tokens)
        fn = _fold(nm)
        if len(fq) > 2 and fq in fn:
            score = max(score, 0.92)
        best = max(best, score)
    return min(best, 1.0)


# ---------- geography ----------
COUNTRY_ALIASES = {
    "uk": "united kingdom", "gb": "united kingdom", "gbr": "united kingdom",
    "great britain": "united kingdom", "britain": "united kingdom", "england": "united kingdom",
    "us": "united states", "usa": "united states", "america": "united states",
    "united states of america": "united states",
    "ru": "russian federation", "rus": "russian federation", "russia": "russian federation",
    "ae": "united arab emirates", "uae": "united arab emirates", "emirates": "united arab emirates",
    "kp": "korea democratic", "dprk": "korea democratic", "north korea": "korea democratic",
    "kr": "korea republic", "south korea": "korea republic",
    "ir": "iran", "irn": "iran", "cn": "china", "prc": "china", "ve": "venezuela",
    "sy": "syria", "syr": "syria", "by": "belarus", "ua": "ukraine", "tr": "turkey",
    "turkiye": "turkey", "ch": "switzerland", "de": "germany", "fr": "france",
    "sa": "saudi arabia", "ksa": "saudi arabia", "hk": "hong kong", "sg": "singapore",
    "cy": "cyprus", "mt": "malta", "vg": "virgin islands", "bvi": "virgin islands",
    "ky": "cayman islands", "pa": "panama", "ng": "nigeria", "za": "south africa",
    "cd": "congo", "drc": "congo", "mm": "myanmar", "burma": "myanmar",
    "cz": "czech", "czechia": "czech", "nl": "netherlands", "holland": "netherlands",
}


def _norm_country(s) -> str:
    f = _fold(s)
    return COUNTRY_ALIASES.get(f, f)


def _geo_hit(qc, pool):
    """None = nothing to compare; False = compared, no hit; else the matched value."""
    if not qc:
        return None
    fc = _norm_country(qc)
    for c in pool:
        fcc = _norm_country(c)
        if fcc and (fc in fcc or fcc in fc):
            return c
    return False


def _country_match(qc, r):
    d = r.get("demographics") or {}
    pool = [x for x in (d.get("country_of_residence"), d.get("country_of_birth"),
                        d.get("place_of_birth")) if x]
    return _geo_hit(qc, pool)


def _nationality_match(qn, r):
    d = r.get("demographics") or {}
    return _geo_hit(qn, [x for x in (d.get("nationalities") or []) if x])


# ---------- date of birth (YYYY-MM-DD, YYYY-MM, YYYY, DD.MM.YYYY, DD/MM/YYYY) ----------
def _parse_dob(v):
    v = str(v).strip()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", v)
    if m:
        return (int(m[1]), int(m[2]), int(m[3]))
    m = re.match(r"^(\d{4})-(\d{1,2})$", v)
    if m:
        return (int(m[1]), int(m[2]), None)
    m = re.match(r"^(\d{4})$", v)
    if m:
        return (int(m[1]), None, None)
    m = re.match(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{4})$", v)
    if m:
        return (int(m[3]), int(m[2]), int(m[1]))
    return None


def _dob_match(qd, r, tol):
    """'full' | 'year' | 'close' | 'mismatch' | None (None = not comparable)."""
    if not qd:
        return None
    rd = (r.get("demographics") or {}).get("date_of_birth")
    if not rd:
        return None
    want, have = _parse_dob(qd), _parse_dob(rd)
    if not want or not have:
        return None
    wy, wmo, wd = want
    hy, hmo, hd = have
    if wy == hy:
        if wmo is None:
            return "year"
        if wmo == hmo and (wd is None or wd == hd):
            return "full"
        return "mismatch"
    if tol > 0 and abs(wy - hy) <= tol:
        return "close"
    return "mismatch"


# ---------- identifiers (passport / national ID / tax ID) ----------
def _norm_id(s) -> str:
    s = unicodedata.normalize("NFKC", "" if s is None else str(s)).upper()
    return "".join(c for c in s if c.isalnum())


def _id_match(qv, vals):
    """True | False (record has a value but it differs) | None (nothing to compare)."""
    if not qv:
        return None
    nq = _norm_id(qv)
    if not nq:
        return None
    pool = [n for n in (_norm_id(v) for v in (vals if isinstance(vals, list) else [vals]) if v) if n]
    if not pool:
        return None
    for v in pool:
        if v == nq or (len(nq) >= 5 and (nq in v or v in nq)):
            return True
    return False


# ---------- shape one record for the screening response ----------
def _summarise(r: dict) -> dict:
    d = r.get("demographics") or {}
    c = r.get("classification") or {}
    p = r.get("pep") or {}
    s = r.get("sanctions") or {}
    n = r.get("names") or {}
    return {
        "wc_uid": r.get("wc_uid"),
        "entity_type": r.get("entity_type"),
        "primary_name": n.get("primary"),
        "aliases": n.get("aliases") or [],
        "original_script": n.get("original_script"),
        "gender": d.get("gender"),
        "date_of_birth": d.get("date_of_birth"),
        "place_of_birth": d.get("place_of_birth"),
        "nationalities": d.get("nationalities") or [],
        "country_of_residence": d.get("country_of_residence"),
        "categories": c.get("categories") or [],
        "sub_category": c.get("sub_category"),
        "risk_rating": c.get("risk_rating"),
        "record_status": c.get("record_status"),
        "is_pep": bool(p.get("is_pep")),
        "pep_class": p.get("class"),
        "pep_position": p.get("position"),
        "is_sanctioned": bool(s.get("is_sanctioned")),
        "sanctions_lists": s.get("lists") or [],
        "sanctions_programs": s.get("programs") or [],
        "listing_date": s.get("listing_date"),
        "adverse_media_topics": (r.get("adverse_media") or {}).get("topics") or [],
        "identifiers": r.get("identifiers") or {},
        "address": r.get("address"),
        "linked_associates": r.get("linked_associates") or [],
        "sources": r.get("sources") or [],
        "profile_notes": r.get("profile_notes"),
        "last_updated": (r.get("audit") or {}).get("last_updated"),
    }


def _screen(q: dict) -> dict:
    def s(v):
        return ("" if v is None else str(v)).strip()

    query_name = s(q.get("name") or q.get("full_name") or q.get("query"))
    q_country = s(q.get("country"))
    q_nat = s(q.get("nationality"))
    q_dob = s(q.get("date_of_birth") or q.get("dob") or q.get("year_of_birth"))
    q_pob = s(q.get("place_of_birth"))
    q_gender = s(q.get("gender") or q.get("sex"))
    q_entity = s(q.get("entity_type") or q.get("type"))
    q_passport = s(q.get("passport_number") or q.get("passport"))
    q_national = s(q.get("national_id") or q.get("id_number"))
    q_tax = s(q.get("tax_id") or q.get("tin") or q.get("inn"))
    q_uid = s(q.get("wc_uid") or q.get("uid"))
    dob_tol = max(0, min(5, _to_int(q.get("dob_tolerance_years"), 0)))
    max_results = max(1, min(100, _to_int(q.get("max_results"), 25)))
    thr = q.get("threshold")
    name_threshold = thr if isinstance(thr, (int, float)) and 0 < thr <= 1 else 0.45

    records = _records()
    matches: list[dict] = []
    message = None
    uid_handled = False

    # 1) Direct UID fetch takes precedence when provided.
    if q_uid:
        nu = _fold(q_uid).replace(" ", "")
        rec = next((r for r in records if _fold(r.get("wc_uid")).replace(" ", "") == nu), None)
        if rec:
            matches.append({"match_score": 1, "name_score": None, "match_type": "uid_lookup",
                            "matched_on": ["wc_uid"], "record": _summarise(rec)})
            uid_handled = True
            message = "Record fetched by wc_uid. SYNTHETIC data — verify before any decision."
        elif not query_name:
            message = f"No record found for wc_uid '{q_uid}' and no 'name' provided."
            uid_handled = True

    # 2) Name screen (name is the only required field; everything else refines).
    if not uid_handled and query_name:
        for r in records:
            if q_entity:
                fe = _fold(q_entity)
                wants_ind = bool(re.search(r"individual|person|natural", fe))
                wants_ent = bool(re.search(r"entity|company|organi[sz]|corporate|legal|business", fe))
                rec_ind = "individual" in _fold(r.get("entity_type"))
                if wants_ind and not rec_ind:
                    continue
                if wants_ent and rec_ind:
                    continue

            ns = _name_score(query_name, r)
            ids = r.get("identifiers") or {}
            id_results = [
                ("passport_number", _id_match(q_passport, ids.get("passport_numbers"))),
                ("national_id", _id_match(q_national, ids.get("national_id"))),
                ("tax_id", _id_match(q_tax, ids.get("tax_id"))),
            ]
            id_hit = any(res is True for _, res in id_results)

            # An exact identifier hit lets a record through even when the name score is
            # weak (e.g. an alias/transliteration not in the dataset).
            if ns < name_threshold and not id_hit:
                continue

            matched_on: list[str] = []
            score = ns
            if ns >= name_threshold:
                matched_on.append("name")
            for label, res in id_results:
                if res is True:
                    matched_on.append(label)
                elif res is False:
                    score -= 0.15
                    matched_on.append(label + "_mismatch")
            if id_hit:
                score = min(1, max(score, 0.9) + (0.1 if ns >= name_threshold else 0.05))

            cm = _country_match(q_country, r)
            if cm:
                score += 0.15
                matched_on.append("country:" + str(cm))
            elif cm is False:
                score -= 0.05
                matched_on.append("country_mismatch")

            nm = _nationality_match(q_nat, r)
            if nm:
                score += 0.10
                matched_on.append("nationality:" + str(nm))
            elif nm is False:
                score -= 0.05
                matched_on.append("nationality_mismatch")

            dm = _dob_match(q_dob, r, dob_tol)
            if dm == "full":
                score += 0.20
                matched_on.append("date_of_birth")
            elif dm == "year":
                score += 0.15
                matched_on.append("year_of_birth")
            elif dm == "close":
                score += 0.10
                matched_on.append(f"dob_within_{dob_tol}y")
            elif dm == "mismatch":
                score -= 0.10
                matched_on.append("dob_mismatch")

            if q_pob:
                d = r.get("demographics") or {}
                ph = _geo_hit(q_pob, [x for x in (d.get("place_of_birth"), d.get("country_of_birth")) if x])
                if ph:
                    score += 0.10
                    matched_on.append("place_of_birth:" + str(ph))

            if q_gender:
                rg = _fold((r.get("demographics") or {}).get("gender"))
                if rg:
                    fg = _fold(q_gender)
                    if fg and rg[0] == fg[0]:
                        score += 0.05
                        matched_on.append("gender")
                    else:
                        score -= 0.05
                        matched_on.append("gender_mismatch")

            score = max(0.0, min(score, 1.0))
            matches.append({
                "match_score": round(score * 100) / 100,
                "name_score": round(ns * 100) / 100,
                "match_type": "exact_identifier" if id_hit else ("exact_name" if ns >= 0.99 else "partial"),
                "matched_on": matched_on,
                "record": _summarise(r),
            })
        matches.sort(key=lambda x: (x["match_score"], x["name_score"] or 0), reverse=True)

    if not message:
        if not query_name and not q_uid:
            message = "No 'name' provided. Supply at least a name (or a wc_uid) to screen."
        elif matches:
            message = "Potential matches found. SYNTHETIC data — verify before any decision."
        else:
            message = "No matches found in the synthetic WorldCheck dataset."

    return {
        "source": SOURCE,
        "searched": {
            "name": query_name or None, "country": q_country or None, "nationality": q_nat or None,
            "date_of_birth": q_dob or None, "place_of_birth": q_pob or None, "gender": q_gender or None,
            "entity_type": q_entity or None, "passport_number": q_passport or None,
            "national_id": q_national or None, "tax_id": q_tax or None, "wc_uid": q_uid or None,
            "dob_tolerance_years": dob_tol or None, "threshold": name_threshold, "max_results": max_results,
        },
        "records_screened": len(records),
        "match_count": len(matches),
        "matches": matches[:max_results],
        "message": message,
    }


_DESC = (
    "Screens a person or entity against the WorldCheck (LSEG) synthetic watchlist database and returns "
    "all partial and exact matches. Required input: 'name' (Latin or original script, e.g. Cyrillic). All "
    "other inputs are optional refinements that raise or lower the match score: 'country' and 'nationality' "
    "(full names, ISO codes or common abbreviations like UK/USA/UAE), 'date_of_birth' (YYYY-MM-DD, YYYY-MM, "
    "YYYY, DD.MM.YYYY or DD/MM/YYYY) with optional 'dob_tolerance_years' for approximate year matching, "
    "'place_of_birth', 'gender', 'entity_type' ('Individual' or 'Entity'), and identifiers: 'passport_number' "
    "(series+number in any format; spaces/dashes/case ignored), 'national_id', 'tax_id' - an exact identifier "
    "hit is near-conclusive and is returned even when the name spelling differs (alias/transliteration). "
    "'wc_uid' fetches a specific record directly. 'threshold' (default 0.45) and 'max_results' (default 25) "
    "tune recall. Each result includes a match_score (0-1), match_type (uid_lookup/exact_identifier/"
    "exact_name/partial), what was matched_on (including any field mismatches), and the full screening "
    "record: PEP status and class, sanctions lists/programs, adverse media topics, risk rating, record "
    "status, identifiers, address, linked associates and sources. SYNTHETIC data for KYC/AML tool testing only."
)


def register(mcp) -> None:
    @mcp.tool(
        name="screen_person",
        title="WorldCheck Screening Lookup",
        description=_DESC,
        meta={"unique.app/icon": "shield-alert"},
    )
    def screen_person(
        name: Annotated[str, Field(description="Full name of the person or entity to screen. Latin or "
                                   "original script (e.g. Cyrillic). The ONLY required field.")] = "",
        country: Annotated[str, Field(description="Country of residence or birth. Full name or ISO/abbrev "
                                      "(e.g. 'Russia', 'RU', 'UK').")] = "",
        nationality: Annotated[str, Field(description="Nationality/citizenship. Full name or ISO/abbrev.")] = "",
        date_of_birth: Annotated[str, Field(description="DOB: YYYY-MM-DD, YYYY-MM, YYYY, DD.MM.YYYY or "
                                            "DD/MM/YYYY (day-first).")] = "",
        dob_tolerance_years: Annotated[int, Field(description="Treat a birth year within +/- N years (0-5) "
                                                  "as an approximate DOB match (default 0).")] = 0,
        place_of_birth: Annotated[str, Field(description="City or country of birth.")] = "",
        gender: Annotated[str, Field(description="Male or Female.")] = "",
        entity_type: Annotated[str, Field(description="'Individual' or 'Entity'.")] = "",
        passport_number: Annotated[str, Field(description="Passport series+number in any format "
                                              "(spaces/dashes/case ignored).")] = "",
        national_id: Annotated[str, Field(description="National ID / identity-card number.")] = "",
        tax_id: Annotated[str, Field(description="Tax ID / TIN / INN.")] = "",
        wc_uid: Annotated[str, Field(description="Fetch one WorldCheck record directly by its wc_uid.")] = "",
        threshold: Annotated[float, Field(description="Name-match score threshold 0-1 (default 0.45).")] = 0.45,
        max_results: Annotated[int, Field(description="Max results to return (default 25).")] = 25,
    ) -> str:
        return json.dumps(_screen({
            "name": name, "country": country, "nationality": nationality,
            "date_of_birth": date_of_birth, "dob_tolerance_years": dob_tolerance_years,
            "place_of_birth": place_of_birth, "gender": gender, "entity_type": entity_type,
            "passport_number": passport_number, "national_id": national_id, "tax_id": tax_id,
            "wc_uid": wc_uid, "threshold": threshold, "max_results": max_results,
        }))
