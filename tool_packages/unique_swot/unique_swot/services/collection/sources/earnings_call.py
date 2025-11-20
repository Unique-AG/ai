import asyncio
from datetime import datetime
from logging import getLogger
from typing import Sequence

from unique_quartr.constants.document_types import DocumentType
from unique_quartr.constants.event_types import EventType
from unique_quartr.endpoints.schemas import EventDto
from unique_quartr.service import DocumentDto, QuartrService
from unique_quartr.transcripts.earnings_call import QuartrEarningsCallTranscript
from unique_toolkit import KnowledgeBaseService
from unique_toolkit._common.docx_generator import DocxGeneratorService
from unique_toolkit.content import Content

from unique_swot.services.collection.registry import ContentChunkRegistry
from unique_swot.services.collection.schema import Source, SourceType
from unique_swot.services.collection.sources.utils import convert_content_to_sources
from unique_swot.services.session.schema import UniqueCompanyListing

_LOGGER = getLogger(__name__)

_MAX_INGESTION_RETRIES = 100
_INGESTION_RETRY_DELAY = 1


async def collect_earnings_calls(
    *,
    chunk_registry: ContentChunkRegistry,
    docx_generator_service: DocxGeneratorService,
    knowledge_base_service: KnowledgeBaseService,
    quartr_service: QuartrService,
    upload_scope_id: str,
    company: UniqueCompanyListing,
    earnings_call_start_date: datetime,
) -> list[Source]:
    event_type_ids = quartr_service.get_event_subtype_ids_from_event_types(
        [EventType.EARNINGS_CALL]
    )
    document_ids = quartr_service.get_document_ids_from_document_types(
        [DocumentType.TRANSCRIPT, DocumentType.IN_HOUSE_TRANSCRIPT]
    )

    events = quartr_service.fetch_company_events(
        company_ids=[company.id],
        event_ids=event_type_ids,
        start_date=earnings_call_start_date.strftime("%Y-%m-%d"),
    )

    events_mapping = {int(event.id): event for event in events.data}

    documents = quartr_service.fetch_event_documents(
        event_ids=list(events_mapping.keys()),
        document_ids=document_ids,
    )

    available_contents_in_knowledge_base: list[Content] = []
    list_of_transcripts_to_ingest: list[DocumentDto] = []

    for document in documents.data:
        if document.event_id is None:
            _LOGGER.warning(
                f"Document {document.id} has no event id. This is an unexpected behaviour. Skipping this document."
            )
            continue

        event = events_mapping[int(document.event_id)]
        document_title = f"{company.name} {event.title} Earnings Call"

        # Try to get the content from the knowledge_base if already exists
        content = _try_getting_content_from_knowledge_base(
            knowledge_base_service=knowledge_base_service,
            document_title=document_title,
        )
        if content is not None:
            _LOGGER.info(
                f"Content {document_title} already exists in the knowledge base"
            )
            available_contents_in_knowledge_base.append(content)
        else:
            _LOGGER.info(
                f"Content {document_title} not found in the knowledge base and will be added to ingestion queue!"
            )
            list_of_transcripts_to_ingest.append(document)

    ingested_contents = await _ingest_all_transcripts(
        list_of_transcripts_to_ingest=list_of_transcripts_to_ingest,
        knowledge_base_service=knowledge_base_service,
        docx_generator_service=docx_generator_service,
        upload_scope_id=upload_scope_id,
        company=company,
        events_mapping=events_mapping,
    )

    # Merging the available contents in the knowledge base and the ingested contents
    all_contents = available_contents_in_knowledge_base + ingested_contents

    sources = []

    for content in all_contents:
        source = Source(
            type=SourceType.EARNINGS_CALL,
            url=None,
            title=content.title or content.key or "Unknown Title",
            chunks=convert_content_to_sources(
                content=content, chunk_registry=chunk_registry
            ),
        )

        sources.append(source)

    return sources


async def _ingest_all_transcripts(
    *,
    list_of_transcripts_to_ingest: list[DocumentDto],
    knowledge_base_service: KnowledgeBaseService,
    docx_generator_service: DocxGeneratorService,
    upload_scope_id: str,
    company: UniqueCompanyListing,
    events_mapping: dict[int, EventDto],
) -> list[Content]:
    tasks = []

    for document in list_of_transcripts_to_ingest:
        if document.event_id is None:
            _LOGGER.warning(
                f"Document {document.id} has no event id. This is an unexpected behaviour. Skipping this document."
            )
            continue

        event = events_mapping[int(document.event_id)]
        document_title = f"{company.name} {event.title} Earnings Call"

        task = asyncio.create_task(
            _ingest_transcript_and_get_content(
                knowledge_base_service=knowledge_base_service,
                docx_generator_service=docx_generator_service,
                scope_id=upload_scope_id,
                document_title=document_title,
                quarter_transcript_url=document.file_url,
                quarter_event_date=event.date,
            )
        )
        tasks.append(task)

    ingested_contents: Sequence[Content | None] = await asyncio.gather(*tasks)
    return [content for content in ingested_contents if content is not None]


def _try_getting_content_from_knowledge_base(
    *,
    knowledge_base_service: KnowledgeBaseService,
    document_title: str,
) -> Content | None:
    contents = knowledge_base_service.search_contents(
        where={"title": {"contains": document_title}}
    )
    if len(contents) == 0:
        return None

    assert len(contents) == 1, (
        "Expected exactly one content to be found for the given document title"
    )

    return contents[0]


async def _ingest_transcript_and_get_content(
    *,
    knowledge_base_service: KnowledgeBaseService,
    docx_generator_service: DocxGeneratorService,
    scope_id: str,
    document_title: str,
    quarter_transcript_url: str,
    quarter_event_date: datetime,
) -> Content | None:
    # Loading the transcript from the quarter transcript url
    transcript = QuartrEarningsCallTranscript.from_quartr_transcript_url(
        quarter_transcript_url
    )

    # Converting the transcript to markdown
    markdown = transcript.to_markdown()

    # Parsing the markdown to a list of content fields
    docx_bytes = docx_generator_service.parse_markdown_to_list_content_fields(markdown)

    # Generating the docx from the content fields and the template
    docx_bytes = docx_generator_service.generate_from_template(
        docx_bytes,
        {
            "title": document_title,
            "date": quarter_event_date.strftime("%Y-%m-%d"),
        },
    )

    # Early return if the docx generation failed
    if docx_bytes is None:
        _LOGGER.warning(f"Failed to generate the docx for the content {document_title}")
        return None

    # Uploading the docx to the knowledge base
    content = knowledge_base_service.upload_content_from_bytes(
        content=docx_bytes,
        content_name=document_title + ".docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        scope_id=scope_id,
    )

    # Waiting for the content to be ready
    content = await _wait_for_content_to_be_ready(content.id, knowledge_base_service)

    if content is None:
        _LOGGER.warning(f"Content {document_title} ingestion failed or still ingesting")
    else:
        _LOGGER.info(f"Content {document_title} ingestion finished")

    return content


async def _wait_for_content_to_be_ready(
    content_id: str, knowledge_base_service: KnowledgeBaseService
) -> Content | None:
    for _ in range(_MAX_INGESTION_RETRIES):
        contents = knowledge_base_service.search_contents(
            where={"id": {"equals": content_id}}, include_failed_content=True
        )
        if len(contents) > 0:
            ingestion_state = contents[0].ingestion_state
            _LOGGER.debug(f"Content {content_id} ingestion state: {ingestion_state}")
            if ingestion_state == "FINISHED":
                return contents[0]
            elif ingestion_state == "FAILED":
                raise ValueError(f"Content {content_id} ingestion failed")
            else:
                await asyncio.sleep(_INGESTION_RETRY_DELAY)

    return None
