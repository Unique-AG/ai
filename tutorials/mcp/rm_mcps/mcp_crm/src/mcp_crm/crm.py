"""CRM domain — party identity / identifiers / relationship / mandate / history /
entity ownership, plus the client roster (list_clients) and the read-only
document catalogue (list_available_documents).

Port of the n8n "RM Demo — CRM" workflow. Per-client records come from sql/crm.sql;
the roster + resolution come from sql/clients.sql.
"""

import json
from typing import Annotated

from pydantic import Field

from common.db import make_client_tools, query_all, query_one, resolve_client, unknown

SPECS = [
    {
        "name": "get_party_identity",
        "table": "party_identity",
        "style": "record",
        "meta": {"unique.app/icon": "id-card"},
        "description": (
            "[CRM 1a] Party identity: full legal name, aliases, DOB, place of birth, gender, "
            "nationalities, country of residence, tax residences + TIN. Input: client name or "
            "client_id."
        ),
    },
    {
        "name": "get_identifiers",
        "table": "identifiers",
        "style": "record",
        "meta": {"unique.app/icon": "fingerprint"},
        "description": (
            "[CRM 1b] Identifiers: passport, national ID, LEI, company registration, internal "
            "party ID. Input: client name or client_id."
        ),
    },
    {
        "name": "get_entity_ownership",
        "table": "entity_ownership",
        "style": "record",
        "meta": {"unique.app/icon": "sitemap"},
        "description": (
            "[CRM 1c] Entity & ownership: entity type, beneficial owners, directors, controllers, "
            "signatories, ownership depth. Input: client name or client_id."
        ),
    },
    {
        "name": "get_relationship",
        "table": "relationship",
        "style": "record",
        "meta": {"unique.app/icon": "handshake"},
        "description": (
            "[CRM 1d] Relationship: client/prospect status, owning RM/team/booking centre, "
            "segment, referral, related parties, languages, contact + preferred channel. Input: "
            "client name or client_id."
        ),
    },
    {
        "name": "get_mandate_objectives",
        "table": "mandate",
        "style": "record",
        "meta": {"unique.app/icon": "target"},
        "description": (
            "[CRM 1e] Mandate & objectives: mandate type, investment objective, risk profile, "
            "horizon/liquidity, constraints, reference currency, fee schedule. Input: client name "
            "or client_id."
        ),
    },
    {
        "name": "get_history",
        "table": "history",
        "style": "record",
        "meta": {"unique.app/icon": "clock-rotate-left"},
        "description": (
            "[CRM 1f] History: interaction log/meeting notes, open tasks, life events, "
            "complaints. Input: client name or client_id."
        ),
    },
]

_LIST_CLIENTS_DESC = (
    "[CRM 1g] Client book / roster + SEARCH (RM cockpit & client lookup). Optional args: q "
    "(free-text substring over name/client_id/segment/rm/status), status (client|prospect), "
    "segment (e.g. UHNW), rm, limit, skip. Returns {total, count, skip, limit, clients[]}."
)
_LIST_DOCS_DESC = (
    "[CRM 1m] CATALOG — every document in a client's KB folder with its contentId. Pass client_id "
    "(or name). Returns {client_id, count, documents:[{title, contentId, kind}]}. Use this to "
    "discover what files exist for a client."
)


def register(mcp) -> None:
    make_client_tools(mcp, SPECS)

    @mcp.tool(
        name="list_clients",
        title="List Clients",
        description=_LIST_CLIENTS_DESC,
        meta={"unique.app/icon": "users"},
    )
    def list_clients(
        q: Annotated[str, Field(description="Free-text substring over name/client_id/segment/rm/status.")] = "",
        status: Annotated[str, Field(description="client | prospect")] = "",
        segment: Annotated[str, Field(description="e.g. UHNW")] = "",
        rm: Annotated[str, Field(description="Owning RM.")] = "",
        limit: Annotated[int, Field(description="Page size.")] = 50,
        skip: Annotated[int, Field(description="Page offset.")] = 0,
    ) -> str:
        rows = [r["data"] for r in query_all("SELECT data FROM clients ORDER BY client_id")]

        def keep(c: dict) -> bool:
            if q and q.lower() not in (str(c.get("name", "")) + " " + str(c.get("client_id", ""))
                                       + " " + str(c.get("segment", "")) + " " + str(c.get("rm", ""))
                                       + " " + str(c.get("status", ""))).lower():
                return False
            # status / segment match case-insensitively; rm matches as a substring
            # (the rm field is "username · booking-centre", e.g. "marc.dubois · Zürich").
            if status and str(c.get("status", "")).lower() != status.lower():
                return False
            if segment and str(c.get("segment", "")).lower() != segment.lower():
                return False
            if rm and rm.lower() not in str(c.get("rm", "")).lower():
                return False
            return True

        matched = [c for c in rows if keep(c)]
        page = matched[skip: skip + limit]
        return json.dumps({"total": len(matched), "count": len(page), "skip": skip,
                           "limit": limit, "clients": page})

    @mcp.tool(
        name="list_available_documents",
        title="List Available Documents",
        description=_LIST_DOCS_DESC,
        meta={"unique.app/icon": "folder-open"},
    )
    def list_available_documents(
        input: Annotated[str, Field(description="Client name or client_id.")] = "",
        client_id: Annotated[str, Field(description="Client id (alternative to input).")] = "",
    ) -> str:
        cid = resolve_client(input or client_id)
        if cid is None:
            return json.dumps(unknown(input or client_id))
        row = query_one("SELECT data FROM documents_catalog WHERE client_id = %s", (cid,))
        docs = row["data"] if row else []
        return json.dumps({"client_id": cid, "count": len(docs), "documents": docs, "items": docs})
