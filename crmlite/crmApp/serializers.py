from rest_framework import serializers
from .models import User, Company, Storage, Supplier, Supply, SupplyProduct, Product


#
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'is_company_owner', 'company']
        read_only_fields = ['id', 'is_company_owner', 'company']


class RegisterSerializer(serializers.ModelSerializer):  # Для регистрации новых пользователей
    # Пароль не возвращается в ответе сервера
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(  # Хэшируем пароль
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user


class CompanySerializer(serializers.ModelSerializer):
    #
    owner_email = serializers.EmailField(source='owner.email', read_only=True)

    class Meta:
        model = Company
        fields = ['id', 'title', 'inn', 'owner', 'owner_email']
        read_only_fields = ['id', 'owner', 'owner_email']



class StorageSerializer(serializers.ModelSerializer):
    # Дополнительное поле
    company_name = serializers.CharField(source='company.title', read_only=True)

    class Meta:
        model = Storage
        fields = ['id', 'address', 'company', 'company_name']

class SupplierSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.title', read_only=True)

    class Meta:
        model = Supplier
        fields = ['id', 'name', 'inn', 'company', 'company_name']
        read_only_fields = ['id', 'company']


class ProductSerializer(serializers.ModelSerializer):
    profit_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    company_name = serializers.CharField(source='company.title', read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'description',
                  'quantity', 'purchase_price',
                  'sale_price', 'company', 'profit_per_unit', 'company_name']
        read_only_fields = ['id', 'company']

class SupplyProductSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = SupplyProduct
        fields = ['id', 'product', 'product_name', 'quantity', 'purchase_price_at_supply']

class SupplySerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    company_name = serializers.CharField(source='company.title', read_only=True)
    products = SupplyProductSerializer(source='supplyproduct_set', many=True, read_only=True)

    class Meta:
        model = Supply
        fields = ['id', 'supplier', 'supplier_name', 'company',
                  'company_name', 'delivery_date', 'products']
        read_only_fields = ['id', 'company', 'delivery_date']

class AddProductSupplySerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    purchase_price_at_supply = serializers.DecimalField(max_digits=10, decimal_places=2)

class CreateSupplySerializer(serializers.Serializer):
    supplier = serializers.IntegerField()
    items = serializers.ListField(
        child=AddProductSupplySerializer(),
        min_length=1,
        help_text='Список товаров в поставке'
    )

    def validate_supplier(self, value):
        return value

    def validated_items(self, value):
        products_ids = [item['product_id'] for item in value]
        if len(products_ids) != len(set(products_ids)):
            raise serializers.ValidationError('Товары в поставке должны быть уникальными')

        return value

class AttachUserSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, help_text='Email пользователя')
    user_id = serializers.IntegerField(required=False, help_text='ID пользователя')

    def validate(self, data):
        email = data.get('email')
        user_id = data.get('user_id')

        if not email and not user_id:
            raise serializers.ValidationError(
                'Необходимо указать email или user_id пользователя'
            )
        if email and user_id:
            raise serializers.ValidationError(
                'Укажите только одно поле: email или user_id'
            )
        return data

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                f'Пользователь с email "{value}" не найден'
            )
        self.context['user_to_attach'] = user
        return value

    def validate_user_id(self, value):
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                f'Пользователь с ID "{value}" не найден'
            )
        self.context['user_to_attach'] = user
        return value





