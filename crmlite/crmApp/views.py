from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from .models import User, Company, Storage, Supplier, Supply, Product, SupplyProduct
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiResponse
from .serializers import (
    UserSerializer, CompanySerializer,
    StorageSerializer, RegisterSerializer,
    SupplierSerializer, SupplySerializer,
    SupplyProductSerializer, ProductSerializer,
    AddProductSupplySerializer, CreateSupplySerializer,
    AttachUserSerializer,
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
    list=extend_schema(tags=['🏢 Компании']),
    create=extend_schema(tags=['🏢 Компании']),
    retrieve=extend_schema(tags=['🏢 Компании']),
    update=extend_schema(tags=['🏢 Компании']),
    partial_update=extend_schema(tags=['🏢 Компании']),
    destroy=extend_schema(tags=['🏢 Компании']),
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

    @extend_schema(
        summary='Закрепить пользователя за компанией',
        description='Доступно только владельцу компании. Принимает email или user_id пользователя',
        request=AttachUserSerializer,
        responses={
            20: OpenApiResponse(description='Пользователь успешно привязан'),
            400: OpenApiResponse(description='Ошибка валидации'),
            403: OpenApiResponse(description='Нет прав'),
            404: OpenApiResponse(description='Пользователь не найден')
        }
    )
    @action(detail=True, methods=['POST'])
    def attach_user(self, request, pk=None):
        company = request.user.company
        if not company:
            raise PermissionDenied(
                'У вас нет компании для закрепления пользователя'
            )
        if company.owner != request.user:
            raise PermissionDenied(
                'Только владелец компании может закрепить пользователей'
            )
        serialazer = AttachUserSerializer(data=request.data)
        serialazer.is_valid(raise_exception=True)

        user_to_attach = serialazer.context.get('user_to_attach')
        if not user_to_attach:
            return Response(
                {'error': 'Пользователь не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        if user_to_attach.company and user_to_attach.company != company:
            return Response(
                {'error': 'Этот пользователь привязан к другой компании'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if user_to_attach.company == company:
            return Response(
                {'error': 'Пользователь уже привязан к этой компании'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user_to_attach.company = company
        user_to_attach.is_company_owner = False
        user_to_attach.save(update_fields=['company', 'is_company_owner'])

        return Response(
            {
                'status': 'Пользователь успешно привязан к компании',
                'user': {
                    'id': user_to_attach.id,
                    'email': user_to_attach.email,
                    'company': user_to_attach.company.id if user_to_attach.company else None
                }
            },
            status=status.HTTP_200_OK
        )


@extend_schema_view(
    list=extend_schema(tags=['📦 Склады']),
    create=extend_schema(tags=['📦 Склады']),
    retrieve=extend_schema(tags=['📦 Склады']),
    update=extend_schema(tags=['📦 Склады']),
    partial_update=extend_schema(tags=['📦 Склады']),
    destroy=extend_schema(tags=['📦 Склады']),
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
            raise PermissionDenied('Этот склад не принадлежит вашей компании')

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
        serializer.save(company=self.request.user.company, quantity=0)

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

    @extend_schema(
        summary='Создание поставки с товарами',
        description='Создаем новую поставку и добавляем в нее список товаров',
        request=CreateSupplySerializer,
        responses={
            201: SupplySerializer,
            400: OpenApiResponse(description='Ошибка валидации'),
            403: OpenApiResponse(description='Нет прав'),
            404: OpenApiResponse(description='Поставщик или товар не найдены')
        }
    )
    def create(self, request, *args, **kwargs):
        user = request.user
        company = user.company
        # Проверка наличия компании
        if not company:
            raise PermissionDenied('У вас нет компании для создания поставки')
        # Валидация входящих данных через сериализатор
        serializer = CreateSupplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validate_data = serializer.validated_data
        supplier_id = validate_data['supplier']
        items = validate_data['items']

        try:
            supplier = Supplier.objects.get(id=supplier_id, company=company)
        except Supplier.DoesNotExist:
            return Response(
                {'error': 'Поставщик не найден или не принадлежит вашей компании'},
                status=status.HTTP_404_NOT_FOUND
            )
        product_to_add = []
        for item in items:
            try:
                product = Product.objects.get(id=item['product_id'], company=company)
                product_to_add.append((product, item))
            except Product.DoesNotExist:
                return Response(
                    {'error': f'Товар с ID {item["product_id"]} не найден или не принадлежит вашей компании'},
                    status=status.HTTP_404_NOT_FOUND
                )
        supply = Supply.objects.create(
            supplier=supplier,
            company=company
        )

        supply_products = []
        for product, item in product_to_add:
            quantity = item['quantity']
            purchase_price = item.get('purchase_price_at_supply', product.purchase_price)

            supply_product = SupplyProduct.objects.create(
                supply=supply,
                product=product,
                quantity=quantity,
                purchase_price_at_supply=purchase_price)

            supply_products.append(supply_product)

            product.quantity += int(quantity)
            product.save(update_fields=['quantity'])

        response_serializer = self.get_serializer(supply)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

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
        responses={
            201: SupplyProductSerializer,
            400: OpenApiResponse(description='Ошибка валидации'),
            403: OpenApiResponse(description='Нет прав'),
            404: OpenApiResponse(description='Поставщик или товар не найдены')
        }
    )
    @action(detail=True, methods=['POST'], url_path='add_product')
    def add_product(self, request, pk=None):
        supply = self.get_object()
        if supply.company.owner != request.user:
            raise PermissionDenied('Только владелец компании может добавлять товары в поставку')

        serializer = AddProductSupplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']
        purchase_price = serializer.validated_data.get('purchase_price_at_supply')

        try:
            product = Product.objects.get(id=product_id, company=request.user.company)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Товар не найден или не принадлежит вашей компании'},
                status=status.HTTP_404_NOT_FOUND)

        # Проверка на дублирование
        if SupplyProduct.objects.filter(supply=supply, product=product).exists():
            return Response(
                {'error': 'Этот товар уже добавлен в данную поставку'},
                status=status.HTTP_400_BAD_REQUEST
            )

        supply_product = SupplyProduct.objects.create(
            supply=supply,
            product=product,
            quantity=quantity,
            purchase_price_at_supply=purchase_price or product.purchase_price
        )
        product.quantity += int(quantity)
        product.save(update_fields=['quantity'])

        serializer = SupplyProductSerializer(supply_product)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
