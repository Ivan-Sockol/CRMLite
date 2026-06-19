from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from .models import User, Company, Storage, Supplier, Supply, Product, SupplyProduct
from drf_spectacular.utils import extend_schema_view, extend_schema
from .serializers import (
    UserSerializer, CompanySerializer,
    StorageSerializer, RegisterSerializer,
    SupplierSerializer, SupplySerializer,
    SupplyProductSerializer, ProductSerializer,
    AddProductSupplySerializer
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

        employees = User.objects.filter(company=company)
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
    serializer_class = StorageSerializer

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
@extend_schema_view(
    list=extend_schema(tags=['🏪 Поставщик']),
    create=extend_schema(tags=['🏪 Поставщик']),
    retrieve=extend_schema(tags=['🏪 Поставщик']),
    update=extend_schema(tags=['🏪 Поставщик']),
    partial_update=extend_schema(tags=['🏪 Поставщик']),
    destroy=extend_schema(tags=['🏪 Поставщик'])
)
class SupplierViewSet(viewsets.ModelViewSet):
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.company:
            return Supplier.objects.none()
        return Supplier.objects.filter(company=user.company)

    def perform_create(self, serializer):
        user = self.request.user
        if not user.company:
            raise PermissionDenied('У вас нет компании, для того чтобы привязать поставщика')
        serializer.save(company=user.company)
@extend_schema_view(
    list=extend_schema(tags=['🛍️ Товар']),
    create=extend_schema(tags=['🛍️ Товар']),
    retrieve=extend_schema(tags=['🛍️ Товар']),
    update=extend_schema(tags=['🛍️ Товар']),
    partial_update=extend_schema(tags=['🛍️ Товар']),
    destroy=extend_schema(tags=['🛍️ Товар'])
)
class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.company:
            return Product.objects.none()
        return Product.objects.filter(company=user.company)

    def perform_create(self, serializer):
        user = self.request.user
        if not user.company:
            raise PermissionDenied('У вас нет компании для привязки товара')
        serializer.save(company=user.company)

    @action(detail=True, methods=['POST'])
    def adjust_quantity(self, request, pk=None):
        product = self.get_object()
        new_quantity = request.data.get('quantity')
        if new_quantity is None:
            return Response({'error': 'Необходимо указать quantity'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            product.quantity = int(new_quantity)
            product.save(update_fields=['quantity'])
            return Response({'status': 'Количество обновлено', 'new_quantity': product.quantity})
        except ValueError:
            return Response({'error': 'quantity должно быть целым числом'},
                           status=status.HTTP_400_BAD_REQUEST)

@extend_schema_view(
    list=extend_schema(tags=['🛵️ Поставка']),
    create=extend_schema(tags=['🛵️ Поставка']),
    retrieve=extend_schema(tags=['🛵️ Поставка']),
    update=extend_schema(tags=['🛵️ Поставка']),
    partial_update=extend_schema(tags=['🛵️ Поставка']),
    destroy=extend_schema(tags=['🛵️ Поставка'])
)
class SupplyViewSet(viewsets.ModelViewSet):
    serializer_class = SupplySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.company:
            return Supply.objects.none()
        return Supply.objects.filter(company=user.company)

    def perform_create(self, serializer):
        user = self.request.user
        if not user.company:
            raise PermissionDenied('У вас нет компании для привязки поставки')
        supplier_id = self.request.data.get('supplier')
        if supplier_id:
            try:
                supplier = Supplier.objects.get(id=supplier_id, company=user.company)
            except Supplier.DoesNotExist:
                raise PermissionDenied('Указанный поставщик не принадлежит вашей компании')
        else:
            raise PermissionDenied('Необходимо указать поставщика')
        serializer.save(company=user.company, supplier=supplier)
    @extend_schema(
        summary='Добавить товар в поставку',
        request=AddProductSupplySerializer,
        responses={201: SupplyProductSerializer}
    )
    @action(detail=True, methods=['POST'])
    def add_product(self, request, pk=None):
        serializer = AddProductSupplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        supply = self.get_object()
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity')
        purchase_price = request.data.get('purchase_price_at_supply')

        if not all([product_id, quantity, purchase_price]):
            return Response({'error': 'Необходимо указать product_id, quantity и purchase_price_at_supply'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            product = Product.objects.get(id=product_id, company=request.user.company)
        except Product.DoesNotExist:
            return Response({'error': 'Товар не найден или не принадлежит вашей компании'},
                            status=status.HTTP_404_NOT_FOUND)
        supply_product = SupplyProduct.objects.create(
            supply=supply,
            product=product,
            quantity=quantity,
            purchase_price_at_supply=purchase_price
        )
        product.quantity += int(quantity)
        product.save()

        serializer = SupplyProductSerializer(supply_product)
        return Response(serializer.data, status=status.HTTP_201_CREATED)












