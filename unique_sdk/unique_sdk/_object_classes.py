import unique_sdk

OBJECT_CLASSES = {
    # data structures
    unique_sdk.ListObject.OBJECT_NAME: unique_sdk.ListObject,
    # api resources
    unique_sdk.Message.OBJECT_NAME: unique_sdk.Message,
    unique_sdk.ChatCompletion.OBJECT_NAME: unique_sdk.ChatCompletion,
    unique_sdk.Span.OBJECT_NAME: unique_sdk.Span,
}
