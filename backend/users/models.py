from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import F, Q


class UserRole:
    User = 'user'
    Admin = 'admin'
    ROLES = (
        (User, 'Авторизованный пользователь'),
        (Admin, 'Администратор'),
    )


class User(AbstractUser):

    role = models.CharField(
        max_length=16,
        choices=UserRole.ROLES,
        default=UserRole.User
    )
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True, max_length=254)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    models.UniqueConstraint(fields=['username', 'email'],
                            name='unique_username_email')

    models.UniqueConstraint(fields=['first_name', 'last_name'],
                            name='name')

    class Meta:
        ordering = ('username',)
        verbose_name = 'Пользователь',
        verbose_name_plural = 'Пользователи',

    def __str__(self):
        return self.username


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriber',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscription',
        verbose_name='Автор рецепта'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'author'),
                name='unique_follow'
            ),
            models.CheckConstraint(
                check=~Q(user=F('author')),
                name='self_following'
            )
        )

    def __str__(self):
        return f'{self.user} подписан на {self.author}'
