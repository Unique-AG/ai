from unique_search_proxy_core.crawlers.basic.processing.policy import (
    DEFAULT_HTML_HANDLERS,
    ContentTypeHandlerPolicy,
)
from unique_search_proxy_core.crawlers.basic.schema import (
    BasicCrawlerCall,
    BasicCrawlerConfig,
)

from unique_search_proxy_client.web.core.crawlers.basic.processing import (
    CONTENT_TYPE_PROCESSORS,
)
from unique_search_proxy_client.web.core.crawlers.basic.service import BasicCrawlerService

__all__ = [
    "BasicCrawlerCall",
    "BasicCrawlerConfig",
    "BasicCrawlerService",
    "CONTENT_TYPE_PROCESSORS",
    "DEFAULT_HTML_HANDLERS",
    "ContentTypeHandlerPolicy",
]
