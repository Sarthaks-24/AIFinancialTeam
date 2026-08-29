from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):

    response = exception_handler(exc, context)

    if response is not None:

        message = response.data

        if isinstance(message, dict):
            message = message.get("detail", message)

        return Response(
            {
                "success": False,
                "status": response.status_code,
                "message": message,
            },
            status=response.status_code,
        )

    return Response(
        {
            "success": False,
            "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": "Something went wrong. Please try again later.",
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )