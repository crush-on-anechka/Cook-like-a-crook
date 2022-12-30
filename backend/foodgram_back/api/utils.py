from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomPageNumberPagination(PageNumberPagination):
    page_size_query_param = 'limit'


def perform_action(self, request, query_param, **kwargs):
    query_id = kwargs.get('id') or kwargs.get('pk')
    data = {
            'user': request.user.id,
            query_param: query_id
        }

    if request.method == 'POST':
        serializer = kwargs.get('serializer')(
            data=data,
            context=kwargs.get('context')
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    if request.method == 'DELETE':
        obj = kwargs.get('model').objects.filter(**data)
        if obj:
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(data={"errors": "Object doesn't exist"},
                        status=status.HTTP_400_BAD_REQUEST
                        )
