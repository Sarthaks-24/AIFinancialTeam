from agents.models import Task


def get_tasks(user):
    org = user.profile.organization if hasattr(user, 'profile') else None
    tasks = Task.objects.filter(organization=org).order_by("-created_at")

    data = []

    for task in tasks:
        data.append({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "created_at": task.created_at
        })

    return data