from agents.models import Report


def get_reports(user):
    org = user.profile.organization if hasattr(user, 'profile') else None
    reports = Report.objects.filter(organization=org).order_by("-created_at")

    data = []

    for report in reports:
        data.append({
            "id": report.id,
            "report_type": report.report_type,
            "summary": report.summary,
            "created_at": report.created_at
        })

    return data