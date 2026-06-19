from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password
# Кастомный менеджер для регистрации пользователя
class CustomUserManager(BaseUserManager):

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Email должен быть указан')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Расширенная модель пользователя"""
    username = None

    email = models.EmailField(unique=True)
    is_company_owner = models.BooleanField(default=False)
    company = models.ForeignKey('Company',
                                null=True,
                                on_delete=models.SET_NULL,
                                blank=True,
                                related_name='users')

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class Company(models.Model):
    """Модель компании"""
    inn = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=250)
    owner = models.OneToOneField(User,
                                 on_delete=models.CASCADE,
                                 related_name='owned_company')

    def __str__(self):
        return f'{self.title} - [{self.inn}]'


class Storage(models.Model):
    """Модель склада"""
    address = models.TextField()
    company = models.ForeignKey('Company',
                                on_delete=models.CASCADE,
                                related_name='storages')

    def __str__(self):
        return self.address

class Supplier(models.Model):
    name = models.CharField(max_length=250)
    inn = models.CharField(max_length=100, unique=True)
    company = models.ForeignKey('Company',
                                on_delete=models.CASCADE,
                                related_name='suppliers',
                                verbose_name='Компания')
    
    class Meta:
        verbose_name='Поставщик'
        verbose_name_plural='Поставщики'
        unique_together=('company', 'inn')

    def __str__(self):
        return f'{self.name} ИНН:{self.inn}'

class Product(models.Model):
    name = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=0)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    company = models.ForeignKey('Company',
                                on_delete=models.CASCADE,
                                related_name='products',
                                verbose_name='Компания')

    class Meta:
        verbose_name='Товар'
        verbose_name_plural='Товары'

    def __str__(self):
        return f'{self.name} - {self.quantity}'

    @property
    def profit_per_unit(self):
        return self.sale_price - self.purchase_price

class Supply(models.Model):
    supplier = models.ForeignKey('Supplier',
                                 on_delete=models.PROTECT,
                                 related_name='supplies',
                                 verbose_name='Поставщик')
    company = models.ForeignKey('Company',
                                on_delete=models.CASCADE,
                                related_name='supplies',
                                verbose_name='Компания')
    delivery_date = models.DateTimeField(auto_now_add=True)
    # Связь ManyToMany через промежуточную таблицу
    products = models.ManyToManyField('Product',
                                      through='SupplyProduct',
                                      related_name='supplies',
                                      verbose_name='Товары в поставке')

    class Meta:
        verbose_name='Поставка'
        verbose_name_plural='Поставки'

    def __str__(self):
        return f'Поставка #{self.id}, от {self.delivery_date.strftime('%d.%m.%Y %H:%M')}'

class SupplyProduct(models.Model):
    supply = models.ForeignKey('Supply',
                               on_delete=models.CASCADE)
    product = models.ForeignKey('Product',
                                on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    purchase_price_at_supply = models.DecimalField(max_digits=10,
                                                   decimal_places=2)

    class Meta:
        verbose_name='Товар в поставке'
        verbose_name_plural='Товары в поставке'
        unique_together=('supply', 'product')

    def __str__(self):
        return f'{self.product.name} в поставке #{self.product.id}'