"""Citation rows for every tool result shape of Unique's Office 365 MCP servers.

One case per tool, so a change to how a result is split into records, titled
or linked shows up against the servers whose results it affects. Each payload
keeps the fields extraction reads — titles, links and the lists and wrappers
around them — in the order the server sends them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from unique_sdk.cli.commands.mcp import record_mcp_citations

# office-365-mcp: Python, snake_case. `uri` is the server's own non-http handle.
_OFFICE_365_CASES: list[
    tuple[str, dict[str, Any], list[tuple[str | None, str | None]]]
] = [
    ("get_me", {"display_name": "root 0"}, [("root 0", None)]),
    (
        "onenote_append_to_page",
        {
            "uri": "o365:///root/0",
            "title": "root 0",
            "web_url": "https://o365.example.com/root/0/web_url",
            "client_url": "https://o365.example.com/root/0/client_url",
        },
        [("root 0", "https://o365.example.com/root/0/web_url")],
    ),
    ("onenote_copy_notebook", {}, [(None, None)]),
    ("onenote_copy_page", {}, [(None, None)]),
    ("onenote_copy_section", {}, [(None, None)]),
    (
        "onenote_create_notebook",
        {
            "uri": "o365:///root/0",
            "name": "root 0",
            "web_url": "https://o365.example.com/root/0/web_url",
            "client_url": "https://o365.example.com/root/0/client_url",
        },
        [("root 0", "https://o365.example.com/root/0/web_url")],
    ),
    (
        "onenote_create_page",
        {
            "uri": "o365:///root/0",
            "title": "root 0",
            "web_url": "https://o365.example.com/root/0/web_url",
            "client_url": "https://o365.example.com/root/0/client_url",
        },
        [("root 0", "https://o365.example.com/root/0/web_url")],
    ),
    (
        "onenote_create_section",
        {
            "uri": "o365:///root/0",
            "name": "root 0",
            "web_url": "https://o365.example.com/root/0/web_url",
            "client_url": "https://o365.example.com/root/0/client_url",
        },
        [("root 0", "https://o365.example.com/root/0/web_url")],
    ),
    (
        "onenote_create_section_group",
        {"uri": "o365:///root/0", "name": "root 0"},
        [("root 0", None)],
    ),
    ("onenote_delete_page", {"title": "root 0"}, [("root 0", None)]),
    (
        "onenote_edit_page",
        {
            "uri": "o365:///root/0",
            "title": "root 0",
            "web_url": "https://o365.example.com/root/0/web_url",
            "client_url": "https://o365.example.com/root/0/client_url",
        },
        [("root 0", "https://o365.example.com/root/0/web_url")],
    ),
    (
        "onenote_find_notebook_from_url",
        {
            "uri": "o365:///root/0",
            "name": "root 0",
            "web_url": "https://o365.example.com/root/0/web_url",
            "client_url": "https://o365.example.com/root/0/client_url",
        },
        [("root 0", "https://o365.example.com/root/0/web_url")],
    ),
    ("onenote_get_operation", {}, [(None, None)]),
    (
        "onenote_list_notebooks",
        {
            "notebooks": [
                {
                    "uri": "o365:///notebooks/1",
                    "name": "notebooks 1",
                    "web_url": "https://o365.example.com/notebooks/1/web_url",
                },
                {
                    "uri": "o365:///notebooks/2",
                    "name": "notebooks 2",
                    "web_url": "https://o365.example.com/notebooks/2/web_url",
                },
            ]
        },
        [
            ("notebooks 1", "https://o365.example.com/notebooks/1/web_url"),
            ("notebooks 2", "https://o365.example.com/notebooks/2/web_url"),
        ],
    ),
    (
        "onenote_list_pages",
        {
            "pages": [
                {
                    "uri": "o365:///pages/1",
                    "title": "pages 1",
                    "web_url": "https://o365.example.com/pages/1/web_url",
                    "client_url": "https://o365.example.com/pages/1/client_url",
                },
                {
                    "uri": "o365:///pages/2",
                    "title": "pages 2",
                    "web_url": "https://o365.example.com/pages/2/web_url",
                    "client_url": "https://o365.example.com/pages/2/client_url",
                },
            ]
        },
        [
            ("pages 1", "https://o365.example.com/pages/1/web_url"),
            ("pages 2", "https://o365.example.com/pages/2/web_url"),
        ],
    ),
    (
        "onenote_list_recent_notebooks",
        {
            "notebooks": [
                {
                    "name": "notebooks 1",
                    "web_url": "https://o365.example.com/notebooks/1/web_url",
                    "client_url": "https://o365.example.com/notebooks/1/client_url",
                },
                {
                    "name": "notebooks 2",
                    "web_url": "https://o365.example.com/notebooks/2/web_url",
                    "client_url": "https://o365.example.com/notebooks/2/client_url",
                },
            ]
        },
        [
            ("notebooks 1", "https://o365.example.com/notebooks/1/web_url"),
            ("notebooks 2", "https://o365.example.com/notebooks/2/web_url"),
        ],
    ),
    (
        "onenote_list_sections",
        {
            "sections": [
                {
                    "uri": "o365:///sections/1",
                    "name": "sections 1",
                    "web_url": "https://o365.example.com/sections/1/web_url",
                },
                {
                    "uri": "o365:///sections/2",
                    "name": "sections 2",
                    "web_url": "https://o365.example.com/sections/2/web_url",
                },
            ],
            "section_groups": [
                {"uri": "o365:///section_groups/1", "name": "section_groups 1"},
                {"uri": "o365:///section_groups/2", "name": "section_groups 2"},
            ],
        },
        [
            ("sections 1", "https://o365.example.com/sections/1/web_url"),
            ("sections 2", "https://o365.example.com/sections/2/web_url"),
            ("section_groups 1", None),
            ("section_groups 2", None),
        ],
    ),
    ("onenote_preview_page", {}, [(None, None)]),
    (
        "onenote_read_page",
        {
            "page": {
                "uri": "o365:///page/0",
                "title": "page 0",
                "web_url": "https://o365.example.com/page/0/web_url",
                "client_url": "https://o365.example.com/page/0/client_url",
            }
        },
        [(None, None)],
    ),
    (
        "onenote_rename_page",
        {
            "page": {
                "uri": "o365:///page/0",
                "title": "page 0",
                "web_url": "https://o365.example.com/page/0/web_url",
                "client_url": "https://o365.example.com/page/0/client_url",
            }
        },
        [(None, None)],
    ),
    (
        "outlook_browse_folders",
        {
            "folders": [
                {"uri": "o365:///folders/1", "display_name": "folders 1"},
                {"uri": "o365:///folders/2", "display_name": "folders 2"},
            ]
        },
        [("folders 1", None), ("folders 2", None)],
    ),
    (
        "outlook_cancel_event",
        {"uri": "o365:///root/0", "subject": "root 0"},
        [("root 0", None)],
    ),
    (
        "outlook_check_availability",
        {"window": {}, "schedules": [{}, {}]},
        [(None, None)],
    ),
    (
        "outlook_copy_mail",
        {"messages": [{"uri": "o365:///messages/1"}, {"uri": "o365:///messages/2"}]},
        [(None, None)],
    ),
    ("outlook_create_category", {"name": "root 0"}, [("root 0", None)]),
    (
        "outlook_create_contact",
        {"uri": "o365:///root/0", "display_name": "root 0"},
        [("root 0", None)],
    ),
    (
        "outlook_create_event",
        {
            "uri": "o365:///root/0",
            "subject": "root 0",
            "join_url": "https://teams.example.com/join/root/0",
            "web_link": "https://o365.example.com/root/0/web_link",
        },
        [("root 0", "https://o365.example.com/root/0/web_link")],
    ),
    (
        "outlook_create_event_on_behalf",
        {
            "uri": "o365:///root/0",
            "subject": "root 0",
            "join_url": "https://teams.example.com/join/root/0",
            "web_link": "https://o365.example.com/root/0/web_link",
        },
        [("root 0", "https://o365.example.com/root/0/web_link")],
    ),
    (
        "outlook_create_folder",
        {"uri": "o365:///root/0", "display_name": "root 0"},
        [("root 0", None)],
    ),
    (
        "outlook_create_mail_rule",
        {"uri": "o365:///root/0", "display_name": "root 0"},
        [("root 0", None)],
    ),
    (
        "outlook_delete_calendar",
        {"uri": "o365:///root/0", "name": "root 0"},
        [("root 0", None)],
    ),
    ("outlook_delete_category", {"name": "root 0"}, [("root 0", None)]),
    (
        "outlook_delete_event",
        {"uri": "o365:///root/0", "subject": "root 0"},
        [("root 0", None)],
    ),
    (
        "outlook_delete_folder",
        {"uri": "o365:///root/0", "display_name": "root 0"},
        [("root 0", None)],
    ),
    (
        "outlook_delete_mail_rule",
        {"uri": "o365:///root/0", "display_name": "root 0"},
        [("root 0", None)],
    ),
    (
        "outlook_disable_mail_rule",
        {"uri": "o365:///root/0", "display_name": "root 0"},
        [("root 0", None)],
    ),
    (
        "outlook_draft_mail",
        {
            "uri": "o365:///root/0",
            "web_link": "https://o365.example.com/root/0/web_link",
            "subject": "root 0",
        },
        [("root 0", "https://o365.example.com/root/0/web_link")],
    ),
    (
        "outlook_draft_reply",
        {
            "uri": "o365:///root/0",
            "web_link": "https://o365.example.com/root/0/web_link",
            "subject": "root 0",
        },
        [("root 0", "https://o365.example.com/root/0/web_link")],
    ),
    (
        "outlook_draft_reply_all",
        {
            "uri": "o365:///root/0",
            "web_link": "https://o365.example.com/root/0/web_link",
            "subject": "root 0",
        },
        [("root 0", "https://o365.example.com/root/0/web_link")],
    ),
    (
        "outlook_find_recipient",
        {
            "candidates": [
                {"display_name": "candidates 1"},
                {"display_name": "candidates 2"},
            ]
        },
        [("candidates 1", None), ("candidates 2", None)],
    ),
    (
        "outlook_find_rooms",
        {"rooms": [{"display_name": "rooms 1"}, {"display_name": "rooms 2"}]},
        [("rooms 1", None), ("rooms 2", None)],
    ),
    (
        "outlook_forward_event",
        {"uri": "o365:///root/0", "subject": "root 0"},
        [("root 0", None)],
    ),
    ("outlook_get_mail_tips", {"recipients": [{}, {}]}, [(None, None)]),
    (
        "outlook_get_mailbox_settings",
        {
            "rules": [
                {"uri": "o365:///rules/1", "display_name": "rules 1"},
                {"uri": "o365:///rules/2", "display_name": "rules 2"},
            ],
            "automatic_reply": {"scheduled_start": {}, "scheduled_end": {}},
            "working_hours": {},
            "language": {"display_name": "language 0"},
        },
        [("rules 1", None), ("rules 2", None)],
    ),
    (
        "outlook_list_attachments",
        {
            "attachments": [
                {"uri": "o365:///attachments/1", "name": "attachments 1"},
                {"uri": "o365:///attachments/2", "name": "attachments 2"},
            ]
        },
        [("attachments 1", None), ("attachments 2", None)],
    ),
    (
        "outlook_list_calendar_groups",
        {"groups": [{"name": "groups 1"}, {"name": "groups 2"}]},
        [("groups 1", None), ("groups 2", None)],
    ),
    (
        "outlook_list_calendar_shares",
        {
            "shares": [
                {"uri": "o365:///shares/1", "name": "shares 1"},
                {"uri": "o365:///shares/2", "name": "shares 2"},
            ]
        },
        [("shares 1", None), ("shares 2", None)],
    ),
    (
        "outlook_list_calendars",
        {
            "calendars": [
                {"uri": "o365:///calendars/1", "name": "calendars 1"},
                {"uri": "o365:///calendars/2", "name": "calendars 2"},
            ]
        },
        [("calendars 1", None), ("calendars 2", None)],
    ),
    (
        "outlook_list_categories",
        {"categories": [{"name": "categories 1"}, {"name": "categories 2"}]},
        [("categories 1", None), ("categories 2", None)],
    ),
    (
        "outlook_list_contacts",
        {
            "contacts": [
                {"uri": "o365:///contacts/1", "display_name": "contacts 1"},
                {"uri": "o365:///contacts/2", "display_name": "contacts 2"},
            ]
        },
        [("contacts 1", None), ("contacts 2", None)],
    ),
    (
        "outlook_list_event_attachments",
        {
            "attachments": [
                {"uri": "o365:///attachments/1", "name": "attachments 1"},
                {"uri": "o365:///attachments/2", "name": "attachments 2"},
            ]
        },
        [("attachments 1", None), ("attachments 2", None)],
    ),
    (
        "outlook_list_event_instances",
        {
            "window": {},
            "events": [
                {
                    "uri": "o365:///events/1",
                    "subject": "events 1",
                    "join_url": "https://teams.example.com/join/events/1",
                    "web_link": "https://o365.example.com/events/1/web_link",
                },
                {
                    "uri": "o365:///events/2",
                    "subject": "events 2",
                    "join_url": "https://teams.example.com/join/events/2",
                    "web_link": "https://o365.example.com/events/2/web_link",
                },
            ],
        },
        [
            ("events 1", "https://o365.example.com/events/1/web_link"),
            ("events 2", "https://o365.example.com/events/2/web_link"),
        ],
    ),
    (
        "outlook_list_events",
        {
            "calendar": {"uri": "o365:///calendar/0", "name": "calendar 0"},
            "window": {},
            "events": [
                {
                    "uri": "o365:///events/1",
                    "subject": "events 1",
                    "join_url": "https://teams.example.com/join/events/1",
                    "web_link": "https://o365.example.com/events/1/web_link",
                },
                {
                    "uri": "o365:///events/2",
                    "subject": "events 2",
                    "join_url": "https://teams.example.com/join/events/2",
                    "web_link": "https://o365.example.com/events/2/web_link",
                },
            ],
        },
        [
            ("events 1", "https://o365.example.com/events/1/web_link"),
            ("events 2", "https://o365.example.com/events/2/web_link"),
        ],
    ),
    ("outlook_list_focused_overrides", {"overrides": [{}, {}]}, [(None, None)]),
    (
        "outlook_list_group_events",
        {
            "window": {},
            "events": [
                {
                    "subject": "events 1",
                    "join_url": "https://teams.example.com/join/events/1",
                    "web_link": "https://o365.example.com/events/1/web_link",
                },
                {
                    "subject": "events 2",
                    "join_url": "https://teams.example.com/join/events/2",
                    "web_link": "https://o365.example.com/events/2/web_link",
                },
            ],
        },
        [
            ("events 1", "https://o365.example.com/events/1/web_link"),
            ("events 2", "https://o365.example.com/events/2/web_link"),
        ],
    ),
    (
        "outlook_list_mail",
        {
            "messages": [
                {
                    "uri": "o365:///messages/1",
                    "subject": "messages 1",
                    "web_link": "https://o365.example.com/messages/1/web_link",
                },
                {
                    "uri": "o365:///messages/2",
                    "subject": "messages 2",
                    "web_link": "https://o365.example.com/messages/2/web_link",
                },
            ]
        },
        [
            ("messages 1", "https://o365.example.com/messages/1/web_link"),
            ("messages 2", "https://o365.example.com/messages/2/web_link"),
        ],
    ),
    (
        "outlook_list_reminders",
        {
            "reminders": [
                {
                    "subject": "reminders 1",
                    "web_link": "https://o365.example.com/reminders/1/web_link",
                },
                {
                    "subject": "reminders 2",
                    "web_link": "https://o365.example.com/reminders/2/web_link",
                },
            ]
        },
        [
            ("reminders 1", "https://o365.example.com/reminders/1/web_link"),
            ("reminders 2", "https://o365.example.com/reminders/2/web_link"),
        ],
    ),
    (
        "outlook_list_time_zones",
        {
            "time_zones": [
                {"display_name": "time_zones 1"},
                {"display_name": "time_zones 2"},
            ]
        },
        [("time_zones 1", None), ("time_zones 2", None)],
    ),
    (
        "outlook_mark_mail",
        {"messages": [{"uri": "o365:///messages/1"}, {"uri": "o365:///messages/2"}]},
        [(None, None)],
    ),
    (
        "outlook_move_mail",
        {"messages": [{"uri": "o365:///messages/1"}, {"uri": "o365:///messages/2"}]},
        [(None, None)],
    ),
    (
        "outlook_read_contact",
        {"uri": "o365:///root/0", "display_name": "root 0"},
        [("root 0", None)],
    ),
    (
        "outlook_read_event",
        {
            "uri": "o365:///root/0",
            "subject": "root 0",
            "join_url": "https://teams.example.com/join/root/0",
            "web_link": "https://o365.example.com/root/0/web_link",
        },
        [("root 0", "https://o365.example.com/root/0/web_link")],
    ),
    (
        "outlook_read_mail",
        {
            "uri": "o365:///root/0",
            "subject": "root 0",
            "web_link": "https://o365.example.com/root/0/web_link",
        },
        [("root 0", "https://o365.example.com/root/0/web_link")],
    ),
    (
        "outlook_read_thread",
        {
            "messages": [
                {
                    "uri": "o365:///messages/1",
                    "subject": "messages 1",
                    "web_link": "https://o365.example.com/messages/1/web_link",
                },
                {
                    "uri": "o365:///messages/2",
                    "subject": "messages 2",
                    "web_link": "https://o365.example.com/messages/2/web_link",
                },
            ]
        },
        [
            ("messages 1", "https://o365.example.com/messages/1/web_link"),
            ("messages 2", "https://o365.example.com/messages/2/web_link"),
        ],
    ),
    (
        "outlook_rename_folder",
        {"uri": "o365:///root/0", "display_name": "root 0"},
        [("root 0", None)],
    ),
    (
        "outlook_respond_to_invite",
        {"uri": "o365:///root/0", "subject": "root 0"},
        [("root 0", None)],
    ),
    (
        "outlook_search_mail",
        {
            "messages": [
                {
                    "uri": "o365:///messages/1",
                    "subject": "messages 1",
                    "web_link": "https://o365.example.com/messages/1/web_link",
                },
                {
                    "uri": "o365:///messages/2",
                    "subject": "messages 2",
                    "web_link": "https://o365.example.com/messages/2/web_link",
                },
            ]
        },
        [
            ("messages 1", "https://o365.example.com/messages/1/web_link"),
            ("messages 2", "https://o365.example.com/messages/2/web_link"),
        ],
    ),
    ("outlook_send_draft", {"subject": "root 0"}, [("root 0", None)]),
    (
        "outlook_set_automatic_reply",
        {"scheduled_start": {}, "scheduled_end": {}},
        [(None, None)],
    ),
    ("outlook_set_focused_override", {}, [(None, None)]),
    (
        "outlook_share_calendar",
        {"uri": "o365:///root/0", "name": "root 0"},
        [("root 0", None)],
    ),
    (
        "outlook_suggest_meeting_times",
        {"window": {}, "suggestions": [{}, {}]},
        [(None, None)],
    ),
    ("outlook_unshare_calendar", {}, [(None, None)]),
    (
        "outlook_update_contact",
        {"uri": "o365:///root/0", "display_name": "root 0"},
        [("root 0", None)],
    ),
    (
        "outlook_update_draft",
        {
            "uri": "o365:///root/0",
            "web_link": "https://o365.example.com/root/0/web_link",
            "subject": "root 0",
        },
        [("root 0", "https://o365.example.com/root/0/web_link")],
    ),
    (
        "outlook_update_event",
        {
            "uri": "o365:///root/0",
            "subject": "root 0",
            "join_url": "https://teams.example.com/join/root/0",
            "web_link": "https://o365.example.com/root/0/web_link",
        },
        [("root 0", "https://o365.example.com/root/0/web_link")],
    ),
    (
        "outlook_update_mail_rule",
        {"uri": "o365:///root/0", "display_name": "root 0"},
        [("root 0", None)],
    ),
    (
        "sharepoint_browse_folder",
        {
            "items": [
                {
                    "uri": "o365:///items/1",
                    "name": "items 1",
                    "web_url": "https://o365.example.com/items/1/web_url",
                },
                {
                    "uri": "o365:///items/2",
                    "name": "items 2",
                    "web_url": "https://o365.example.com/items/2/web_url",
                },
            ]
        },
        [
            ("items 1", "https://o365.example.com/items/1/web_url"),
            ("items 2", "https://o365.example.com/items/2/web_url"),
        ],
    ),
    (
        "sharepoint_copy_item",
        {
            "source_web_url": "https://o365.example.com/root/0/source_web_url",
            "destination_web_url": "https://o365.example.com/root/0/destination_web_url",
            "name": "root 0",
        },
        [("root 0", "https://o365.example.com/root/0/source_web_url")],
    ),
    (
        "sharepoint_create_folder",
        {
            "uri": "o365:///root/0",
            "name": "root 0",
            "web_url": "https://o365.example.com/root/0/web_url",
        },
        [("root 0", "https://o365.example.com/root/0/web_url")],
    ),
    ("sharepoint_create_list_item", {}, [(None, None)]),
    ("sharepoint_create_share_link", {}, [(None, None)]),
    (
        "sharepoint_create_text_file",
        {
            "uri": "o365:///root/0",
            "name": "root 0",
            "web_url": "https://o365.example.com/root/0/web_url",
        },
        [("root 0", "https://o365.example.com/root/0/web_url")],
    ),
    ("sharepoint_delete_item", {"name": "root 0"}, [("root 0", None)]),
    ("sharepoint_delete_list_item", {"title": "root 0"}, [("root 0", None)]),
    (
        "sharepoint_get_list",
        {"columns": [{"name": "columns 1"}, {"name": "columns 2"}]},
        [("columns 1", None), ("columns 2", None)],
    ),
    (
        "sharepoint_invite",
        {
            "recipients": [
                {"display_name": "recipients 1"},
                {"display_name": "recipients 2"},
            ]
        },
        [("recipients 1", None), ("recipients 2", None)],
    ),
    (
        "sharepoint_list_drives",
        {
            "drives": [
                {
                    "name": "drives 1",
                    "web_url": "https://o365.example.com/drives/1/web_url",
                },
                {
                    "name": "drives 2",
                    "web_url": "https://o365.example.com/drives/2/web_url",
                },
            ]
        },
        [
            ("drives 1", "https://o365.example.com/drives/1/web_url"),
            ("drives 2", "https://o365.example.com/drives/2/web_url"),
        ],
    ),
    (
        "sharepoint_list_items",
        {
            "items": [
                {
                    "uri": "o365:///items/1",
                    "web_url": "https://o365.example.com/items/1/web_url",
                },
                {
                    "uri": "o365:///items/2",
                    "web_url": "https://o365.example.com/items/2/web_url",
                },
            ]
        },
        [(None, None)],
    ),
    (
        "sharepoint_list_lists",
        {
            "lists": [
                {
                    "uri": "o365:///lists/1",
                    "display_name": "lists 1",
                    "web_url": "https://o365.example.com/lists/1/web_url",
                },
                {
                    "uri": "o365:///lists/2",
                    "display_name": "lists 2",
                    "web_url": "https://o365.example.com/lists/2/web_url",
                },
            ]
        },
        [
            ("lists 1", "https://o365.example.com/lists/1/web_url"),
            ("lists 2", "https://o365.example.com/lists/2/web_url"),
        ],
    ),
    (
        "sharepoint_move_item",
        {
            "item": {
                "uri": "o365:///item/0",
                "name": "item 0",
                "web_url": "https://o365.example.com/item/0/web_url",
            }
        },
        [(None, None)],
    ),
    (
        "sharepoint_rename_item",
        {
            "item": {
                "uri": "o365:///item/0",
                "name": "item 0",
                "web_url": "https://o365.example.com/item/0/web_url",
            }
        },
        [(None, None)],
    ),
    (
        "sharepoint_resolve_url",
        {
            "uri": "o365:///root/0",
            "name": "root 0",
            "web_url": "https://o365.example.com/root/0/web_url",
        },
        [("root 0", "https://o365.example.com/root/0/web_url")],
    ),
    (
        "sharepoint_search_files",
        {
            "files": [
                {
                    "uri": "o365:///files/1",
                    "name": "files 1",
                    "web_url": "https://o365.example.com/files/1/web_url",
                },
                {
                    "uri": "o365:///files/2",
                    "name": "files 2",
                    "web_url": "https://o365.example.com/files/2/web_url",
                },
            ],
            "sites": [
                {"web_url": "https://o365.example.com/sites/1/web_url"},
                {"web_url": "https://o365.example.com/sites/2/web_url"},
            ],
        },
        [
            ("files 1", "https://o365.example.com/files/1/web_url"),
            ("files 2", "https://o365.example.com/files/2/web_url"),
        ],
    ),
    (
        "sharepoint_search_sites",
        {
            "sites": [
                {
                    "web_url": "https://o365.example.com/sites/1/web_url",
                    "display_name": "sites 1",
                },
                {
                    "web_url": "https://o365.example.com/sites/2/web_url",
                    "display_name": "sites 2",
                },
            ]
        },
        [
            ("sites 1", "https://o365.example.com/sites/1/web_url"),
            ("sites 2", "https://o365.example.com/sites/2/web_url"),
        ],
    ),
    ("sharepoint_update_list_item", {}, [(None, None)]),
    ("teams_add_chat_member", {}, [(None, None)]),
    (
        "teams_browse_channel",
        {
            "messages": [
                {
                    "uri": "o365:///messages/1",
                    "subject": "messages 1",
                    "web_url": "https://o365.example.com/messages/1/web_url",
                },
                {
                    "uri": "o365:///messages/2",
                    "subject": "messages 2",
                    "web_url": "https://o365.example.com/messages/2/web_url",
                },
            ]
        },
        [
            ("messages 1", "https://o365.example.com/messages/1/web_url"),
            ("messages 2", "https://o365.example.com/messages/2/web_url"),
        ],
    ),
    ("teams_create_chat", {}, [(None, None)]),
    (
        "teams_create_meeting",
        {"join_web_url": "https://teams.example.com/join/root/0", "subject": "root 0"},
        [("root 0", "https://teams.example.com/join/root/0")],
    ),
    ("teams_delete_meeting", {"subject": "root 0"}, [("root 0", None)]),
    ("teams_delete_message", {}, [(None, None)]),
    (
        "teams_edit_message",
        {"mentions": [{"name": "mentions 1"}, {"name": "mentions 2"}]},
        [("mentions 1", None), ("mentions 2", None)],
    ),
    (
        "teams_get_channel_files_folder",
        {
            "uri": "o365:///root/0",
            "name": "root 0",
            "web_url": "https://o365.example.com/root/0/web_url",
        },
        [("root 0", "https://o365.example.com/root/0/web_url")],
    ),
    (
        "teams_list_call_transcripts",
        {
            "transcripts": [
                {"uri": "o365:///transcripts/1"},
                {"uri": "o365:///transcripts/2"},
            ],
            "unmatched_calls": [{}, {}],
        },
        [(None, None)],
    ),
    (
        "teams_list_channels",
        {"channels": [{"display_name": "channels 1"}, {"display_name": "channels 2"}]},
        [("channels 1", None), ("channels 2", None)],
    ),
    (
        "teams_list_chat_members",
        {"members": [{"display_name": "members 1"}, {"display_name": "members 2"}]},
        [("members 1", None), ("members 2", None)],
    ),
    (
        "teams_list_chat_messages",
        {
            "messages": [
                {
                    "uri": "o365:///messages/1",
                    "subject": None,
                    "web_url": "https://o365.example.com/messages/1/web_url",
                },
                {
                    "uri": "o365:///messages/2",
                    "subject": None,
                    "web_url": "https://o365.example.com/messages/2/web_url",
                },
            ]
        },
        [(None, None)],
    ),
    ("teams_list_chats", {"chats": [{}, {}]}, [(None, None)]),
    ("teams_list_meeting_recordings", {"subject": "root 0"}, [("root 0", None)]),
    ("teams_list_meeting_transcripts", {"subject": "root 0"}, [("root 0", None)]),
    (
        "teams_list_message_replies",
        {
            "messages": [
                {
                    "uri": "o365:///messages/1",
                    "subject": "messages 1",
                    "web_url": "https://o365.example.com/messages/1/web_url",
                },
                {
                    "uri": "o365:///messages/2",
                    "subject": "messages 2",
                    "web_url": "https://o365.example.com/messages/2/web_url",
                },
            ]
        },
        [
            ("messages 1", "https://o365.example.com/messages/1/web_url"),
            ("messages 2", "https://o365.example.com/messages/2/web_url"),
        ],
    ),
    (
        "teams_list_my_teams",
        {"teams": [{"display_name": "teams 1"}, {"display_name": "teams 2"}]},
        [("teams 1", None), ("teams 2", None)],
    ),
    ("teams_react_to_message", {}, [(None, None)]),
    ("teams_read_call_transcript", {"turns": [{}, {}]}, [(None, None)]),
    (
        "teams_read_meeting",
        {
            "meeting": {
                "join_web_url": "https://teams.example.com/join/meeting/0",
                "subject": "meeting 0",
            },
            "reports": [{}, {}],
            "newest_report_attendance": [
                {"display_name": "newest_report_attendance 1"},
                {"display_name": "newest_report_attendance 2"},
            ],
        },
        [("newest_report_attendance 1", None), ("newest_report_attendance 2", None)],
    ),
    (
        "teams_read_message",
        {
            "uri": "o365:///root/0",
            "subject": "root 0",
            "web_url": "https://o365.example.com/root/0/web_url",
        },
        [("root 0", "https://o365.example.com/root/0/web_url")],
    ),
    ("teams_read_transcript", {"turns": [{}, {}]}, [(None, None)]),
    ("teams_remove_chat_member", {}, [(None, None)]),
    ("teams_rename_chat", {}, [(None, None)]),
    (
        "teams_search_messages",
        {
            "messages": [
                {
                    "uri": "o365:///messages/1",
                    "subject": "messages 1",
                    "web_url": "https://o365.example.com/messages/1/web_url",
                },
                {
                    "uri": "o365:///messages/2",
                    "subject": "messages 2",
                    "web_url": "https://o365.example.com/messages/2/web_url",
                },
            ]
        },
        [
            ("messages 1", "https://o365.example.com/messages/1/web_url"),
            ("messages 2", "https://o365.example.com/messages/2/web_url"),
        ],
    ),
    (
        "teams_send_channel_message",
        {
            "uri": "o365:///root/0",
            "subject": "root 0",
            "web_url": "https://o365.example.com/root/0/web_url",
        },
        [("root 0", "https://o365.example.com/root/0/web_url")],
    ),
    (
        "teams_send_channel_message_with_files",
        {
            "uri": "o365:///root/0",
            "subject": "root 0",
            "web_url": "https://o365.example.com/root/0/web_url",
        },
        [("root 0", "https://o365.example.com/root/0/web_url")],
    ),
    (
        "teams_send_chat_message",
        {
            "uri": "o365:///root/0",
            "subject": "root 0",
            "web_url": "https://o365.example.com/root/0/web_url",
        },
        [("root 0", "https://o365.example.com/root/0/web_url")],
    ),
    (
        "teams_send_chat_message_with_files",
        {
            "uri": "o365:///root/0",
            "subject": "root 0",
            "web_url": "https://o365.example.com/root/0/web_url",
        },
        [("root 0", "https://o365.example.com/root/0/web_url")],
    ),
    ("teams_update_meeting", {"subject": "root 0"}, [("root 0", None)]),
]

# outlook-semantic-mcp: TypeScript, camelCase.
_OUTLOOK_SEMANTIC_CASES: list[
    tuple[str, dict[str, Any], list[tuple[str | None, str | None]]]
] = [
    (
        "search_emails",
        {
            "success": True,
            "results": [
                {
                    "uniqueContentId": "cont_1",
                    "msGraphMessageId": "M1",
                    "folderId": "inbox",
                    "title": "Budget Q3.eml",
                    "from": "Alex Doe <alex@example.com>",
                    "receivedDateTime": "2026-11-02T09:00:00Z",
                    "isDraft": False,
                    "text": "Numbers for the quarter.",
                    "outlookWebLink": "https://outlook.office365.com/owa/?ItemID=M1&exvsurl=1&viewmodel=ReadMessageItem",
                    "sourceMailbox": "alex@example.com",
                    "uniqueContentUrl": "https://ingestion.example.com/read/cont_1",
                    "backend": "Unique",
                    "openEmailParams": {"id": "M1"},
                    "replyToParams": {"isReplyable": True},
                },
                {
                    "uniqueContentId": "cont_2",
                    "msGraphMessageId": "M2",
                    "folderId": "inbox",
                    "title": "Offsite plan.eml",
                    "from": "Alex Doe <alex@example.com>",
                    "receivedDateTime": "2026-11-02T09:00:00Z",
                    "isDraft": False,
                    "text": "Numbers for the quarter.",
                    "outlookWebLink": "",
                    "sourceMailbox": None,
                    "uniqueContentUrl": "https://ingestion.example.com/read/cont_2",
                    "backend": "Unique",
                    "openEmailParams": {"id": "M2"},
                    "replyToParams": {"isReplyable": True},
                },
            ],
            "hasMore": True,
            "pages": [
                {
                    "backend": "graph",
                    "query": "budget",
                    "status": "ok",
                    "cursorId": "c1",
                }
            ],
        },
        [
            (
                "Budget Q3.eml",
                "https://outlook.office365.com/owa/?ItemID=M1&exvsurl=1&viewmodel=ReadMessageItem",
            ),
            ("Offsite plan.eml", None),
        ],
    ),
    (
        "fetch_next_search_pages",
        {
            "success": True,
            "results": [
                {
                    "uniqueContentId": "cont_3",
                    "msGraphMessageId": "M3",
                    "folderId": "inbox",
                    "title": "Invoice 4471",
                    "from": "Alex Doe <alex@example.com>",
                    "receivedDateTime": "2026-11-02T09:00:00Z",
                    "isDraft": False,
                    "text": "Numbers for the quarter.",
                    "outlookWebLink": "https://outlook.office365.com/owa/?ItemID=M3&exvsurl=1&viewmodel=ReadMessageItem",
                    "sourceMailbox": "alex@example.com",
                    "uniqueContentUrl": "https://ingestion.example.com/read/cont_3",
                    "backend": "Unique",
                    "openEmailParams": {"id": "M3"},
                    "replyToParams": {"isReplyable": True},
                }
            ],
            "hasMore": False,
            "pages": [{"backend": "graph", "query": "invoice", "status": "done"}],
        },
        [
            (
                "Invoice 4471",
                "https://outlook.office365.com/owa/?ItemID=M3&exvsurl=1&viewmodel=ReadMessageItem",
            )
        ],
    ),
    (
        "open_email",
        {
            "success": True,
            "emailData": {
                "id": "M1",
                "title": "Budget Q3",
                "metadata": {
                    "from": "alex@example.com",
                    "webLink": "https://outlook.office365.com/owa/?ItemID=M1&exvsurl=1&viewmodel=ReadMessageItem",
                    "hasAttachments": False,
                },
                "text": "Numbers for the quarter.",
                "bodyContentType": "text",
            },
        },
        [(None, None)],
    ),
    (
        "search_calendar_events",
        {
            "success": True,
            "message": "2 events",
            "events": [
                {
                    "subject": "Quarterly review",
                    "body": "Agenda attached.",
                    "bodyTruncated": False,
                    "start": {"dateTime": "2026-11-20T10:00:00", "timeZone": "UTC"},
                    "end": {"dateTime": "2026-11-20T11:00:00", "timeZone": "UTC"},
                    "location": "Room 4",
                    "joinUrl": "https://teams.example.com/join/ev",
                    "attendees": [
                        {
                            "name": "Alex Doe",
                            "email": "alex@example.com",
                            "response": "accepted",
                            "type": "required",
                        }
                    ],
                    "organizerName": "Sam Roe",
                    "webLink": "https://outlook.office365.com/calendar/item/E1",
                    "calendarName": "Calendar",
                    "eventRef": {"eventId": "E1", "calendarId": "C1"},
                },
                {
                    "subject": None,
                    "body": "Agenda attached.",
                    "bodyTruncated": False,
                    "start": {"dateTime": "2026-11-20T10:00:00", "timeZone": "UTC"},
                    "end": {"dateTime": "2026-11-20T11:00:00", "timeZone": "UTC"},
                    "location": "Room 4",
                    "joinUrl": "https://teams.example.com/join/ev",
                    "attendees": [
                        {
                            "name": "Alex Doe",
                            "email": "alex@example.com",
                            "response": "accepted",
                            "type": "required",
                        }
                    ],
                    "organizerName": "Sam Roe",
                    "webLink": None,
                    "calendarName": "Calendar",
                    "eventRef": {"eventId": "E1", "calendarId": "C1"},
                },
            ],
            "searchNotes": ["Private events show no subject."],
            "resolvedWindow": {
                "startDateTime": "2026-11-20T00:00:00",
                "endDateTime": "2026-11-21T00:00:00",
                "timeZone": "UTC",
            },
        },
        [("Quarterly review", "https://outlook.office365.com/calendar/item/E1")],
    ),
    (
        "list_calendars",
        {
            "success": True,
            "message": "1 calendar",
            "calendars": [
                {
                    "calendarRef": "C1",
                    "name": "Calendar",
                    "ownerEmail": "alex@example.com",
                    "isOwn": True,
                }
            ],
        },
        [("Calendar", None)],
    ),
    (
        "check_availability",
        {
            "success": True,
            "message": "1 person",
            "people": [
                {
                    "email": "alex@example.com",
                    "busyBlocks": [],
                    "items": [{"status": "busy", "subject": "1:1"}],
                    "workingHours": None,
                }
            ],
        },
        [(None, None)],
    ),
    (
        "suggest_meeting_times",
        {
            "success": True,
            "message": "1 suggestion",
            "suggestions": [
                {
                    "start": "2026-11-20T10:00:00",
                    "end": "2026-11-20T10:30:00",
                    "confidence": 100,
                }
            ],
        },
        [(None, None)],
    ),
    (
        "create_event",
        {
            "success": True,
            "message": "Created",
            "eventRef": "E9",
            "subject": "Kick-off",
            "joinUrl": "https://teams.example.com/join/e9",
            "webLink": "https://outlook.office365.com/calendar/item/E9",
        },
        [("Kick-off", "https://outlook.office365.com/calendar/item/E9")],
    ),
    (
        "update_event",
        {
            "success": True,
            "message": "Updated",
            "eventRef": "E9",
            "subject": "Kick-off (moved)",
            "joinUrl": "https://teams.example.com/join/e9",
            "webLink": "https://outlook.office365.com/calendar/item/E9",
        },
        [("Kick-off (moved)", "https://outlook.office365.com/calendar/item/E9")],
    ),
    ("cancel_event", {"success": True, "message": "Cancelled"}, [(None, None)]),
    (
        "respond_to_invite",
        {"success": True, "message": "Accepted", "response": "accept"},
        [(None, None)],
    ),
    (
        "draft_email",
        {
            "success": True,
            "draftId": "D1",
            "idIsImmutable": True,
            "webLink": "https://outlook.office365.com/owa/?ItemID=D1&exvsurl=1&viewmodel=ReadMessageItem",
            "message": "Draft saved",
        },
        [(None, None)],
    ),
    (
        "update_draft_email",
        {
            "success": True,
            "draftId": "D1",
            "webLink": "https://outlook.office365.com/owa/?ItemID=D1&exvsurl=1&viewmodel=ReadMessageItem",
            "message": "Draft updated",
        },
        [(None, None)],
    ),
    (
        "add_attachments_to_draft_email",
        {"success": True, "message": "Attached", "attachmentsFailed": []},
        [(None, None)],
    ),
    (
        "remove_attachments_from_draft_email",
        {"success": True, "message": "Removed", "removed": ["a.pdf"], "failed": []},
        [(None, None)],
    ),
    (
        "lookup_contacts",
        {
            "contacts": [
                {
                    "name": "Alex Doe",
                    "email": "alex@example.com",
                    "source": "directory",
                    "similarityScore": 0.98,
                },
                {
                    "name": "Alexa Poe",
                    "email": "alexa@example.com",
                    "source": "mailbox",
                    "similarityScore": 0.71,
                },
            ]
        },
        [("Alex Doe", None), ("Alexa Poe", None)],
    ),
    (
        "list_mailboxes_and_directories",
        {
            "success": True,
            "message": "1 mailbox",
            "mailboxes": [
                {
                    "email": "alex@example.com",
                    "displayName": "Alex Doe",
                    "isOwn": True,
                    "folders": [
                        {
                            "id": "f1",
                            "displayName": "Inbox",
                            "canReadContent": True,
                            "children": [],
                        }
                    ],
                }
            ],
        },
        [("Alex Doe", None)],
    ),
    (
        "list_categories",
        {
            "success": True,
            "message": "2 categories",
            "categories": ["Red", "Blue"],
            "count": 2,
        },
        [(None, None)],
    ),
    (
        "sync_progress",
        {
            "state": "running",
            "message": "Syncing",
            "userEmail": "alex@example.com",
            "syncStats": None,
            "ingestionStats": None,
        },
        [(None, None)],
    ),
    (
        "verify_inbox_connection",
        {
            "status": "active",
            "message": "Connected",
            "subscription": {"id": "s1", "expiresAt": "2026-11-21T00:00:00Z"},
        },
        [(None, None)],
    ),
    (
        "reconnect_inbox",
        {
            "success": True,
            "message": "Reconnected",
            "subscription": {"id": "s1", "status": "active"},
        },
        [(None, None)],
    ),
    ("delete_inbox_data", {"success": True, "message": "Deleted"}, [(None, None)]),
]


class _FakeMCPResponse:
    def __init__(self, content: list[dict[str, Any]]) -> None:
        self.content = content
        self.isError = False
        self.mcpServerId = None


def _record(
    tool: str, response: _FakeMCPResponse, unique_dir: Path, text: str
) -> list[tuple[str | None, str | None]]:
    record_mcp_citations(
        response,
        tool_name=tool,
        server_name="office",
        unique_dir=unique_dir,
        formatted_text=text,
    )
    rows = [
        json.loads(line)
        for line in (unique_dir / "mcp-refs.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    return [(row["title"], row.get("url")) for row in rows]


@pytest.mark.parametrize(
    ("tool", "payload", "expected"),
    [pytest.param(*case, id=f"office-365:{case[0]}") for case in _OFFICE_365_CASES]
    + [
        pytest.param(*case, id=f"outlook-semantic:{case[0]}")
        for case in _OUTLOOK_SEMANTIC_CASES
    ],
)
def test_tool_result_yields_one_row_per_titled_record(
    tmp_path: Path,
    tool: str,
    payload: dict[str, Any],
    expected: list[tuple[str | None, str | None]],
) -> None:
    text = json.dumps(payload)
    response = _FakeMCPResponse(content=[{"type": "text", "text": text}])

    assert _record(tool, response, tmp_path / ".unique", text) == expected


def test_sharepoint_read_file_cites_its_resource_link(tmp_path: Path) -> None:
    # office-365-mcp sends the file as an embedded resource and its browser link as a
    # resource_link, which is cited by name with the link's uri.
    url = "https://o365.example.com/files/1/web_url"
    response = _FakeMCPResponse(
        content=[
            {
                "type": "resource",
                "resource": {
                    "uri": "o365:///files/1",
                    "mimeType": "text/plain",
                    "text": "Q3 numbers",
                },
            },
            {
                "type": "resource_link",
                "uri": url,
                "name": "Q3 Report.docx",
                "description": "Open in a browser",
            },
        ]
    )

    assert _record(
        "sharepoint_read_file", response, tmp_path / ".unique", "Q3 numbers"
    ) == [("Q3 Report.docx", url)]
