from jsonschema.validators import create
from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from .models import User, Company, Storage
from drf_spectacular.utils import extend_schema_view, extend_schema
from .serializers import (
    UserSerializer, CompanySerializer,
    StorageSerializer, RegisterSerializer
)
@extend_schema_view(
    list=extend_schema(tags=['👥 Пользователи']),
    create=extend_schema(tags=['👥 Пользователи']),
    retrieve=extend_schema(tags=['👥 Пользователи']),
    update=extend_schema(tags=['👥 Пользователи']),
    partial_update=extend_schema(tags=['👥 Пользователи']),
    destroy=extend_schema(tags=['👥 Пользователи']),
)
class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.company:
            return User.objects.filter(company=user.company)
        return User.objects.filter(id=user.id)

    @action(detail=False, methods=['GET'], url_path='me')
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

@extend_schema_view(
    list=extend_schema(tags=["🏢 Компании"]),
    create=extend_schema(tags=["🏢 Компании"]),
    retrieve=extend_schema(tags=["🏢 Компании"]),
    update=extend_schema(tags=["🏢 Компании"]),
    partial_update=extend_schema(tags=["🏢 Компании"]),
    destroy=extend_schema(tags=["🏢 Компании"]),
)
class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer
    # Аналог queryset = Company.objects.all(), отличие в том, что пользователь не увидит чужие компании и зависит от
    # текущего пользователя
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.company:
            return Company.objects.filter(id=user.company.id)
        return Company.objects.none()

    # Переопределяем метод create
    def create(self, request, *args, **kwargs):
        # Проверка
        if request.user.company:
            return Response(
                {'detail': 'У вас уже есть компания'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if hasattr(request.user, 'owned_company') and request.user.owned_company:
            return Response(
                {'detail': 'Вы уже владеете компанией'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Сериализация входных данных
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Сохраняем объект
        company = serializer.save(owner=request.user)
        # Обновляем пользователя
        request.user.company = company
        request.user.is_company_owner = True
        request.user.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # Переопределение метода retrieve
    def retrieve(self, request, *args, **kwargs):
        # Проверка наличия компании
        if not request.user.company:
            raise PermissionDenied('Вы не привязаны к компании')
        # Берем компанию пользователя игнорируя id
        company = request.user.company
        serializer = self.get_serializer(company)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        # Проверка прав
        company = request.user.company
        if not company or company.owner != request.user:
            raise PermissionDenied('Вы не являетесь владельцем компании')

        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(company, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        company = request.user.company
        if not company or company.owner != request.user:
            raise PermissionDenied('Вы не являетесь владельцем компании')

        company.users.update(company=None, is_company_owner=False)

        company.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['GET'], url_path='my')
    def my_company(self, request):
        if not request.user.company:
            return Response(
                {'detail': 'Вы не привязаны к компании'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(request.user.company)
        return Response(serializer.data)

    @action(detail=False, methods=['GET'], url_path='employees')
    def employees(self, request):

        company = request.user.company
        if not company or company.owner != request.user:
            raise PermissionDenied('Только владелец может видеть сотрудников')

        employees = User.objects.filte(company=company)
        serializer = UserSerializer(employees, many=True)
        return Response(serializer.data)

@extend_schema_view(
    list=extend_schema(tags=["📦 Склады"]),
    create=extend_schema(tags=["📦 Склады"]),
    retrieve=extend_schema(tags=["📦 Склады"]),
    update=extend_schema(tags=["📦 Склады"]),
    partial_update=extend_schema(tags=["📦 Склады"]),
    destroy=extend_schema(tags=["📦 Склады"]),
)
class StorageViewSet(viewsets.ModelViewSet):

    def get_queryset(self):
        user = self.request.user
        if not user.company:
            return Storage.objects.none()

        return Storage.objects.filter(company=user.company)

    def create(self, request, *args, **kwargs):

        company = request.user.company
        if not company or company.owner != request.user:
            raise PermissionDenied('Вы не являетесь владельцем компании')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    def retrieve(self, request, *args, **kwargs):
        storage = self.get_object()

        if not request.user.company or request.user.company != storage.company:
            raise PermissionDenied('Вы не связаны с этой компанией')

        serializer = self.get_serializer(storage)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):

        storage = self.get_object()
        company = request.user.company

        if not company or company.owner != request.user:
            raise PermissionDenied('Только владелец компании может редактировать склад')

        if storage.company != company:
            raise PermissionDenied('Этот склад ен принадлежит вашей компании')

        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(storage, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)
