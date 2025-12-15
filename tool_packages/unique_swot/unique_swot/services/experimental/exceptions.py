class SWOTReportAgentException(Exception):
    pass


class FailedToGeneratePlanException(SWOTReportAgentException):
    pass


class InvalidPlanException(SWOTReportAgentException):
    pass


class FailedToExtractFactsException(SWOTReportAgentException):
    pass


class FailedToCreateNewSectionException(SWOTReportAgentException):
    pass


class FailedToUpdateExistingSectionException(SWOTReportAgentException):
    pass


class SectionNotFoundException(SWOTReportAgentException):
    pass


class SourceFactsIdsNotFoundException(SWOTReportAgentException):
    pass


class InvalidCommandException(SWOTReportAgentException):
    pass
