from unique_search_proxy.web.core.crawlers.basic.processing import (
    CONTENT_TYPE_PROCESSORS,
    DEFAULT_HTML_HANDLERS,
    ContentTypeHandlerPolicy,
)
from unique_search_proxy.web.core.crawlers.basic.schema import (
    BasicCrawlerCall,
    BasicCrawlerConfig,
)
from unique_search_proxy.web.core.crawlers.basic.service import BasicCrawlerService

__all__ = [
    "BasicCrawlerCall",
    "BasicCrawlerConfig",
    "BasicCrawlerService",
    "CONTENT_TYPE_PROCESSORS",
    "DEFAULT_HTML_HANDLERS",
    "ContentTypeHandlerPolicy",
]
