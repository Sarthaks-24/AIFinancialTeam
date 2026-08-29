from agents.models import QueryLog


def get_query_history(user):
    org = user.profile.organization if hasattr(user, 'profile') else None
    logs = QueryLog.objects.filter(organization=org).order_by("-created_at")

    data = []

    for log in logs:
        data.append({
            "question": log.question,
            "agent": log.agent_name,
            "created_at": log.created_at
        })

    return data