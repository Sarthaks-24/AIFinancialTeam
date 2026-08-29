from agents.models import Task


def create_tasks(actions):

    created_tasks = []

    for action in actions:

        task = Task.objects.create(
            title=action[:100],
            description=action,
            status="Pending",
            priority="High"
        )

        created_tasks.append(task.title)

    return {
        "agent": "Execution Agent",
        "tasks_created": created_tasks
    }