from django.template.defaultfilters import title
from rest_framework import serializers
from .models import User, Company, Storage
#
class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', 'email', 'is_company_owner', 'company']
        read_only_fields = ['id', 'is_company_owner', 'company']

class RegisterSerializer(serializers.ModelSerializer): # Для регистрации новых пользователей
    # Пароль не возвращается в ответе сервера
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user( # Хэшируем пароль
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
        read_only_fields = ['id', 'owner']

class StorageSerializer(serializers.ModelSerializer):
    # Дополнительное поле
    company_name = serializers.CharField(source='company.title', read_only=True)

    class Meta:
        model = Storage
        fields = ['id','address', 'company']
