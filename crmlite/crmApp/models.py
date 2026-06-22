from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password


# Кастомный менеджер для аутентификации пользователя по email вместо username
class CustomUserManager(BaseUserManager):
    # приватный метод, который содержит общую логику создания пользователя
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Email должен быть указан')
        email = self.normalize_email(email)  # Приводим email к единому формату при помощи <normalize_email>
        user = self.model(email=email, **extra_fields)  # Создаём объект пользователя (также передаём extra_fields,
        # если переданы дополнительные параметры
        user.password = make_password(password)  # Хешируем пароль
        user.save(using=self._db)
        return user
    # Создание обычного пользователя с соответствующими полномочиями
    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)
    # Создание суперпользователя с соответствующими полномочиями
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
    username = None # Убираем username

    email = models.EmailField(unique=True)
    is_company_owner = models.BooleanField(default=False)
    # Связь с моделью Company многие-к-одному
    company = models.ForeignKey('Company',
                                null=True, # Пользователь может быть не привязан к компании
                                on_delete=models.SET_NULL, # Пользователь не удаляется, в поле company=NULL
                                blank=True, # Можно оставить пустым
                                related_name='users') # Обратная связь, позволяет получить пользователей
                                # компании (company.users)

    objects = CustomUserManager() # Замена стандартного менеджера, кастомным
    # Говорим Django, что при аутентификации нужно использовать поле <email>
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'


class Company(models.Model):
    """Модель компании"""
    inn = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=250)
    # Связь Один-к-Одному (один пользователь-одна компания)
    owner = models.OneToOneField('User',
                                 on_delete=models.CASCADE, # Если пользователь удалён, то и компания будет удалена
                                 related_name='owned_company', # Обратная связь, получаем компанию пользователя
                                 verbose_name='Владелец') # Читаемое имя, отображается в админке

    def __str__(self):
        return f'{self.title} - [{self.inn}]'

    class Meta:
        verbose_name = 'Компания'
        verbose_name_plural = 'Компании'


class Storage(models.Model):
    """Модель склада"""
    address = models.TextField()
    company = models.ForeignKey('Company',
                                on_delete=models.CASCADE,
                                related_name='storages')

    def __str__(self):
        return self.address

    class Meta:
        verbose_name = 'Склад'
        verbose_name_plural = 'Склады'


class Supplier(models.Model):
    """Модель поставщика"""
    name = models.CharField(max_length=250)
    inn = models.CharField(max_length=20)
    company = models.ForeignKey('Company',
                                on_delete=models.CASCADE,
                                related_name='suppliers',
                                verbose_name='Компания')

    def __str__(self):
        return f'{self.name} ИНН:{self.inn}'

    class Meta:
        verbose_name = 'Поставщик'
        verbose_name_plural = 'Поставщики'
        unique_together = ('company', 'inn')




class Product(models.Model):
    """Модель товара"""
    name = models.CharField(max_length=250)
    description = models.TextField(blank=True) # Необязательное поле
    quantity = models.PositiveIntegerField(default=0) # Положительное поле, по умолчанию=0
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2) # Точность 10, знаки после запятой 2
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    company = models.ForeignKey('Company',
                                on_delete=models.CASCADE,
                                related_name='products',
                                verbose_name='Компания')
    storage = models.ForeignKey('Storage',
                                on_delete=models.CASCADE,
                                null=True,
                                blank=True,
                                related_name='products',
                                verbose_name='Склад')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

    def __str__(self):
        return f'{self.name} - {self.quantity}'
    # Вешаем свойство profit_per_unit для вычисления разницы между ценой закупки и продажи
    @property
    def profit_per_unit(self):
        return self.sale_price - self.purchase_price


class Supply(models.Model):
    """Модель поставки"""
    supplier = models.ForeignKey('Supplier',
                                 on_delete=models.PROTECT, # Нельзя удалить поставщика если есть поставки
                                 related_name='supplies',
                                 verbose_name='Поставщик')
    company = models.ForeignKey('Company',
                                on_delete=models.CASCADE,
                                related_name='supplies',
                                verbose_name='Компания')
    # Дата и время поставки (устанавливается автоматически при создании)
    delivery_date = models.DateTimeField(auto_now_add=True)
    # Связь ManyToMany через промежуточную таблицу (одна поставка-много товаров и много поставок-один товар)
    products = models.ManyToManyField('Product',
                                      through='SupplyProduct', # Указываем промежуточную модель для хранения информации
                                      related_name='supplies',
                                      verbose_name='Товары в поставке')

    class Meta:
        verbose_name = 'Поставка'
        verbose_name_plural = 'Поставки'

    def __str__(self):
        return f'Поставка #{self.id}, от {self.delivery_date.strftime("%d.%m.%Y %H:%M")}'


class SupplyProduct(models.Model):
    """Промежуточная модель Поставка-Товар"""
    supply = models.ForeignKey('Supply',
                               on_delete=models.CASCADE) # Если поставка удалена, то и удаляется записи в этой таблице
    product = models.ForeignKey('Product',
                                on_delete=models.PROTECT) # Нельзя удалить товар если он участвовал в поставке
    quantity = models.PositiveIntegerField()
    purchase_price_at_supply = models.DecimalField(max_digits=10,
                                                   decimal_places=2)

    class Meta:
        verbose_name = 'Товар в поставке'
        verbose_name_plural = 'Товары в поставке'
        unique_together = ('supply', 'product') # Гарантия того, что в одной поставке не будет дубликатов одного
        # товара (например: ноутбук в одной накладной может быть указан только один раз)

    def __str__(self):
        return f'{self.product.name} в поставке #{self.supply.id}'
