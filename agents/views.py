import logging

import pandas as pd
from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FinancialMetric, FinancialUpload, QueryLog, Task
from .pagination import CustomPagination
from .permissions import (
    IsAuditorOrAdmin,
    IsCFOOrAdmin,
    IsFinanceManagerOrAdmin,
)
from .serializers import (
    AskAgentSerializer,
    FinancialMetricSerializer,
    FinancialUploadSerializer,
    QueryLogSerializer,
    TaskSerializer,
)
from .services.chief_agent import handle_query
from .services.dashboard_service import get_dashboard_data
from .services.history_service import get_query_history
from .services.kpi_service import get_kpis
from .services.report_service import get_reports
from nexus.registry import list_specialists
from nexus.permissions import user_can_access
from voice.service import ask_with_voice
from echo import service as echo

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ask_agent(request):

    serializer = AskAgentSerializer(data=request.data)

    serializer.is_valid(raise_exception=True)

    question = serializer.validated_data["question"]
    specialist_name = serializer.validated_data.get("specialist")
    conversation_id = serializer.validated_data.get("conversation_id")
    companion_mode = serializer.validated_data.get("companion_mode", False)

    if conversation_id and not echo.get_conversation(request.user.id, conversation_id):
        return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)

    from django.http import StreamingHttpResponse
    import json
    import threading
    import queue

    def stream_response():
        q = queue.Queue()
        
        def emit_event(event_type, data):
            q.put({"event": event_type, "data": data})

        def worker():
            try:
                res = handle_query(
                    question,
                    user=request.user,
                    specialist_name=specialist_name,
                    stream=True,
                    conversation_id=conversation_id,
                    event_sink=emit_event,
                    companion_mode=companion_mode,
                )
                q.put({"event": "result", "data": res})
            except Exception as e:
                logger.exception("Worker thread failed")
                q.put({"event": "error", "data": str(e)})

        thread = threading.Thread(target=worker)
        thread.start()

        while True:
            msg = q.get()
            event = msg["event"]
            data = msg["data"]

            if event == "result":
                result_payload = data
                
                # First send metadata
                metadata = {k: v for k, v in result_payload.items() if k != "analysis"}
                yield f"event: metadata\ndata: {json.dumps(metadata)}\n\n"
                
                # Then stream analysis chunks
                analysis = result_payload.get("analysis", "")
                full_analysis = ""
                if isinstance(analysis, str):
                    full_analysis = analysis
                    yield f"event: chunk\ndata: {json.dumps({'text': analysis})}\n\n"
                else:
                    # iterate the generator here in the main thread
                    try:
                        for chunk in analysis:
                            full_analysis += chunk
                            yield f"event: chunk\ndata: {json.dumps({'text': chunk})}\n\n"
                    except Exception as e:
                        logger.exception("Error while iterating analysis generator")
                        yield f"event: chunk\ndata: {json.dumps({'text': ' [Stream interrupted.]'})}\n\n"
                        
                # Log it after complete
                org = request.user.profile.organization if hasattr(request.user, 'profile') else None
                QueryLog.objects.create(
                    organization=org,
                    question=question,
                    agent_name=result_payload.get("agent"),
                    response=full_analysis
                )
                
                echo.write_turn(
                    request.user.id,
                    result_payload.get("agent") or specialist_name,
                    "specialist",
                    full_analysis,
                    conversation_id=conversation_id,
                )
                
                yield "event: end\ndata: {}\n\n"
                break
                
            elif event == "error":
                yield "event: end\ndata: {}\n\n"
                break
                
            else:
                # pass through out-of-band events (delegation_started, etc)
                yield f"event: {event}\ndata: {json.dumps(data)}\n\n"

    return StreamingHttpResponse(stream_response(), content_type="text/event-stream")


def _conversation_payload(conversation, include_turns=False):
    payload = {
        "id": conversation.id,
        "title": conversation.title or "New conversation",
        "started_at": conversation.started_at.isoformat(),
        "last_active_at": conversation.last_active_at.isoformat(),
        "archived_at": conversation.archived_at.isoformat() if conversation.archived_at else None,
    }
    if include_turns:
        payload["turns"] = [
            {
                "id": turn.id,
                "role": turn.role,
                "specialist_name": turn.specialist_name,
                "content": turn.content,
                "created_at": turn.created_at.isoformat(),
            }
            for turn in conversation.turns.all()
        ]
    return payload


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def conversations(request):
    if request.method == "POST":
        conversation = echo.create_conversation(
            request.user.id,
            title=request.data.get("title", ""),
        )
        return Response(_conversation_payload(conversation), status=status.HTTP_201_CREATED)

    queryset = request.user.echo_conversations.filter(archived_at__isnull=True).order_by("-last_active_at")
    paginator = CustomPagination()
    page = paginator.paginate_queryset(queryset, request)
    return paginator.get_paginated_response([_conversation_payload(item) for item in page])


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def conversation_detail(request, conversation_id):
    conversation = echo.get_conversation(request.user.id, conversation_id, include_archived=True)
    if not conversation:
        return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(_conversation_payload(conversation, include_turns=True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def archive_conversation(request, conversation_id):
    conversation = echo.archive_conversation(request.user.id, conversation_id)
    if not conversation:
        return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(_conversation_payload(conversation))

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def voice_ask(request):
    """Phase 1 voice round-trip: audio → Nova → spoken reply."""

    audio = request.FILES.get("audio")
    if not audio:
        return Response(
            {"error": "No audio file uploaded. Send multipart field 'audio'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    mime_type = audio.content_type or request.data.get("mime_type") or "audio/webm"
    specialist = request.data.get("specialist") or "Nova"
    voice_id = request.data.get("voice_id") or None

    outcome = ask_with_voice(
        audio=audio.read(),
        mime_type=mime_type,
        user=request.user,
        specialist_name=specialist,
        voice_id=voice_id,
    )

    if "error" in outcome and outcome.get("status"):
        http_status = outcome.pop("status")
        return Response(outcome, status=http_status)

    result = outcome.get("result") or {}
    org = request.user.profile.organization if hasattr(request.user, 'profile') else None
    QueryLog.objects.create(
        organization=org,
        question=outcome.get("transcript", ""),
        agent_name=result.get("agent", specialist),
        response=str(result),
    )

    return Response(outcome)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def specialist_list(request):
    """Return the Phase 2 specialists available to the current user."""
    return Response([
        {
            "name": specialist.name,
            "title": specialist.title,
            "description": specialist.description,
            "suggested_prompts": specialist.suggested_prompts,
            "voice_enabled": specialist.voice_enabled,
        }
        for specialist in list_specialists()
        if user_can_access(request.user, specialist)
    ])


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def query_history(request):

    org = request.user.profile.organization if hasattr(request.user, 'profile') else None
    logs = QueryLog.objects.filter(organization=org).order_by('-created_at')

    serializer = QueryLogSerializer(logs, many=True)

    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def task_list(request):

    org = request.user.profile.organization if hasattr(request.user, 'profile') else None
    tasks = Task.objects.filter(organization=org).order_by('-created_at')

    serializer = TaskSerializer(tasks, many=True)

    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_task_status(request):

    task_id = request.data.get("task_id")
    new_status = request.data.get("status")

    try:
        org = request.user.profile.organization if hasattr(request.user, 'profile') else None
        task = Task.objects.get(id=task_id, organization=org)

        task.status = new_status
        task.save()

        return Response({
            "message": "Task updated successfully",
            "task_id": task.id,
            "new_status": task.status
        })

    except Task.DoesNotExist:
        return Response(
            {"error": "Task not found"},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(["GET"])
@permission_classes([IsCFOOrAdmin])
def dashboard_view(request):

    data = get_dashboard_data(request.user)

    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def history_view(request):

    data = get_query_history(request.user)

    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuditorOrAdmin])
def report_view(request):

    data = get_reports(request.user)

    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def task_view(request):

    # Read query parameters
    status = request.query_params.get("status")
    priority = request.query_params.get("priority")
    search = request.query_params.get("search")

    # Get all tasks
    org = request.user.profile.organization if hasattr(request.user, 'profile') else None
    tasks = Task.objects.filter(organization=org).order_by("-created_at")

    # Filter by status
    if status:
        tasks = tasks.filter(status=status)

    # Filter by priority
    if priority:
        tasks = tasks.filter(priority=priority)
    
    if search:
        tasks = tasks.filter(
        Q(title__icontains=search) |
        Q(description__icontains=search)
    )

    # Pagination
    paginator = CustomPagination()
    paginated_tasks = paginator.paginate_queryset(tasks, request)

    serializer = TaskSerializer(paginated_tasks, many=True)

    return paginator.get_paginated_response(serializer.data)

@api_view(["GET"])
@permission_classes([IsFinanceManagerOrAdmin])
def kpi_view(request):

    data = get_kpis(request.user)

    return Response(data)

@api_view(["GET"])
@permission_classes([IsFinanceManagerOrAdmin])
def financial_months_view(request):

    org = request.user.profile.organization if hasattr(request.user, 'profile') else None
    records = FinancialMetric.objects.filter(organization=org).order_by("-created_at")
    serializer = FinancialMetricSerializer(records, many=True)
    return Response(serializer.data)


@api_view(["GET", "PUT"])
@permission_classes([IsFinanceManagerOrAdmin])
def financial_data_view(request):
    org = request.user.profile.organization if hasattr(request.user, "profile") else None
    month = request.query_params.get("month") or request.data.get("month")

    if not month:
        record = FinancialMetric.objects.filter(organization=org).order_by("-created_at").first()
    else:
        record = FinancialMetric.objects.filter(organization=org, month=month).first()

    if record is None:
        return Response(
            {"message": "No financial data found for that month."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        serializer = FinancialMetricSerializer(record)
        return Response(serializer.data)

    serializer = FinancialMetricSerializer(
        record,
        data=request.data,
        partial=True
    )

    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(serializer.data)

class FinancialUploadAPIView(APIView):

    permission_classes = [IsFinanceManagerOrAdmin]

    ALLOWED_EXTENSIONS = (".csv", ".xlsx", ".xls")
    MAX_FILE_SIZE_MB = 5
    REQUIRED_COLUMNS = {"Month", "Revenue", "Expenses", "EBITDA", "Cash", "Budget"}

    def post(self, request):

        file = request.FILES.get("file")

        if not file:
            return Response(
                {"error": "No file uploaded"},
                status=status.HTTP_400_BAD_REQUEST
            )

        file_name_lower = file.name.lower()

        if not file_name_lower.endswith(self.ALLOWED_EXTENSIONS):
            return Response(
                {"error": "Unsupported file type. Please upload a .csv, .xlsx, or .xls file."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if file.size > self.MAX_FILE_SIZE_MB * 1024 * 1024:
            return Response(
                {"error": f"File is too large. Maximum size is {self.MAX_FILE_SIZE_MB}MB."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if file_name_lower.endswith(".csv"):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        except Exception as e:
            logger.exception("File parse error during financial upload: %s", e)
            return Response(
                {"error": "Unable to read this file. Make sure it's a valid CSV or Excel file."},
                status=status.HTTP_400_BAD_REQUEST
            )

        df.columns = df.columns.astype(str).str.strip()

        missing_columns = self.REQUIRED_COLUMNS - set(df.columns)
        if missing_columns:
            return Response(
                {"error": f"Missing required columns: {', '.join(sorted(missing_columns))}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if df.empty:
            return Response(
                {"error": "The uploaded file has no data rows."},
                status=status.HTTP_400_BAD_REQUEST
            )

        numeric_columns = ["Revenue", "Expenses", "EBITDA", "Cash", "Budget"]
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        if df[numeric_columns].isnull().any().any():
            bad_rows = df[df[numeric_columns].isnull().any(axis=1)]
            bad_months = bad_rows["Month"].astype(str).tolist()
            return Response(
                {"error": f"Some rows have missing or non-numeric values in: {', '.join(bad_months)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        org = request.user.profile.organization if hasattr(request.user, "profile") else None
        upload = FinancialUpload.objects.create(
            organization=org,
            file_name=file.name,
            uploaded_file=file
        )

        rows_created = 0
        rows_updated = 0

        try:
            with transaction.atomic():
                for _, row in df.iterrows():
                    month_value = str(row["Month"]).strip()

                    obj, created = FinancialMetric.objects.update_or_create(
                        organization=org,
                        month=month_value,
                        defaults={
                            "revenue": float(row["Revenue"]),
                            "expenses": float(row["Expenses"]),
                            "ebitda": float(row["EBITDA"]),
                            "cash_position": float(row["Cash"]),
                            "budget": float(row["Budget"]),
                        },
                    )

                    if created:
                        rows_created += 1
                    else:
                        rows_updated += 1

        except Exception as e:
            logger.exception("Database insert error during financial upload: %s", e)
            return Response(
                {"error": "Something went wrong saving this data. Your previous data was kept."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        serializer = FinancialUploadSerializer(upload)

        return Response(
            {
                "message": f"File uploaded successfully — {rows_created} month(s) added, {rows_updated} month(s) updated.",
                "rows_found": len(df),
                "rows_created": rows_created,
                "rows_updated": rows_updated,
                "database_records": FinancialMetric.objects.filter(organization=org).count(),
                "columns": list(df.columns),
                "preview": df.head().to_dict(orient="records"),
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED
        )
