from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    '''User model class.'''

    first_name = models.CharField('Имя', max_length=150)
    last_name = models.CharField('Фамилия', max_length=150)
    email = models.EmailField('Адрес электронной почты', max_length=254)


class Subscribe(models.Model):
    '''Users subscriptions on other users model class.'''

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='subscriber'
    )
    subscription = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь, на которого подписан текущий',
        related_name='subscription'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'subscription'],
                name='unique_subscription'
            )
        ]

    def __str__(self):
        return f'{self.user} is subscribed on {self.subscription}'
