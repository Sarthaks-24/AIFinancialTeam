from nexus.router import route_query


def handle_query(question, user=None, specialist_name=None, stream=True, conversation_id=None, event_sink=None, companion_mode=False):
    return route_query(
        question,
        user=user,
        specialist_name=specialist_name,
        stream=stream,
        conversation_id=conversation_id,
        event_sink=event_sink,
        companion_mode=companion_mode,
    )
