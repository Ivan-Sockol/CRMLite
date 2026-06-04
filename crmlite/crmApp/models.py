from django.db import models
from django.contrib.auth.models import AbstractUser


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
