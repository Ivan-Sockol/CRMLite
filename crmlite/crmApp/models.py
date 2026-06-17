from django.contrib.admindocs.utils import explicit_title_re
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

    def crete_user(self, email, password=None, **extra_fields):
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
