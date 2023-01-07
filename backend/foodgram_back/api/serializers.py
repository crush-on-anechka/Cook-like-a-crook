import base64

import djoser
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.files.base import ContentFile
from django.db import transaction
from recipes.models import (Amount, Favorite, Ingredient, Recipe, ShoppingCart,
                            Tag)
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from users.models import Subscribe

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class UserSerializer(djoser.serializers.UserSerializer):
    '''Basic user model serializer.'''

    is_subscribed = serializers.SerializerMethodField()

    def get_is_subscribed(self, obj):
        request_user = self.context.get('request').user
        if type(request_user) == AnonymousUser:
            return False
        subscription = request_user.subscriber.filter(subscription=obj)
        return bool(subscription)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name',
                  'last_name', 'is_subscribed')
        validators = [
            UniqueTogetherValidator(
                queryset=User.objects.all(),
                fields=('username', 'email'),
                message='Пользователь с таким именем и email уже существует'
            ),
        ]


class UserCreateSerializer(djoser.serializers.UserCreateSerializer):
    '''User model serializer for POST method.'''

    class Meta(UserSerializer.Meta):
        fields = ('id', 'username', 'email', 'first_name',
                  'last_name', 'password')
        extra_kwargs = {'password': {'write_only': True}}


class TagSerializer(serializers.ModelSerializer):
    '''Tag model serializer.'''

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug', 'color')


class IngredientSerializer(serializers.ModelSerializer):
    '''Ingredient model serializer.'''

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class AmountSerializer(serializers.ModelSerializer):
    '''Amount (of ingredients in a recipe) model serializer.'''

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = Amount
        fields = ('id', 'name', 'measurement_unit', 'amount')


class IngredientCreateSerializer(serializers.ModelSerializer):
    '''Ingredient model serializer to be nested in creating recipe.'''

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )

    class Meta:
        model = Amount
        fields = ('id', 'amount')


class RecipeGetSerializer(serializers.ModelSerializer):
    '''Recipe model serializer for GET method.'''

    author = UserSerializer()
    ingredients = serializers.SerializerMethodField()
    tags = TagSerializer(many=True)
    is_favorited = serializers.BooleanField(default=False)
    is_in_shopping_cart = serializers.BooleanField(default=False)

    def get_ingredients(self, obj):
        return AmountSerializer(
            obj.amount.all(), many=True).data

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'text', 'cooking_time', 'image',
            'author', 'ingredients', 'tags',
            'is_in_shopping_cart', 'is_favorited'
        )


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    '''Recipe model serializer for POST/PATCH methods.'''

    ingredients = IngredientCreateSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
    )
    image = Base64ImageField(required=False)

    def validate(self, data):
        blank_fields = []
        for field in self.Meta.fields:
            if field not in data:
                blank_fields.append(field)
        blank_fields.remove('id')
        blank_fields.remove('image')
        if len(blank_fields) > 0:
            raise serializers.ValidationError(
                f'{", ".join(str(x) for x in blank_fields)} may not be blank.'
            )
        return data

    @transaction.atomic
    def create(self, validated_data):
        try:
            ingredients = validated_data.pop('ingredients')
            tags = validated_data.pop('tags')
        except KeyError as err:
            raise serializers.ValidationError(
                f'sorry, unexpected error occured (KeyError: {err})')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)

        for ingredient in ingredients:
            Amount.objects.create(
                recipe=recipe,
                ingredient=ingredient.get('ingredient'),
                amount=ingredient.get('amount')
            )
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            ingredients = validated_data.pop('ingredients')
        except KeyError as err:
            raise serializers.ValidationError(
                f'sorry, unexpected error occured (KeyError: {err})')

        _ = [item.delete() for item in instance.amount.all()]

        for ingredient in ingredients:
            Amount.objects.create(
                recipe=instance,
                ingredient=ingredient.get('ingredient'),
                amount=ingredient.get('amount')
                )

        return super().update(instance, validated_data)

    def to_representation(self, obj):
        try:
            self.fields.pop('ingredients')
        except KeyError as err:
            raise serializers.ValidationError(
                f'sorry, unexpected error occured (KeyError: {err})')
        results = super().to_representation(obj)
        results['ingredients'] = IngredientCreateSerializer(
            obj.amount.all(), many=True).data
        return results

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'text', 'cooking_time',
            'ingredients', 'tags', 'image'
        )


class RecipeMinifiedSerializer(RecipeGetSerializer):
    '''Minified recipe model serializer to be nested for
    subscription actions.'''

    class Meta(RecipeGetSerializer.Meta):
        fields = ('id', 'name', 'cooking_time', 'image')


class ShoppingCartFavoriteSerializer(serializers.ModelSerializer):
    '''Shopping cart and Favorite models base serializer.'''

    def to_representation(self, obj):
        return {
            'id': obj.recipe.id,
            'name': obj.recipe.name,
            'image': obj.recipe.image.url,
            'cooking_time': obj.recipe.cooking_time
        }

    class Meta:
        fields = ('id', 'user', 'recipe')


class ShoppingCartSerializer(ShoppingCartFavoriteSerializer):
    '''Shopping Cart model serializer.'''

    class Meta(ShoppingCartFavoriteSerializer.Meta):
        model = ShoppingCart

        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже в корзине'
            ),
        ]


class FavoriteSerializer(ShoppingCartFavoriteSerializer):
    '''Favorite model serializer.'''

    class Meta(ShoppingCartFavoriteSerializer.Meta):
        model = Favorite

        validators = [
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже в избранном'
            ),
        ]


class SubscriptionsListSerializer(UserSerializer):
    '''List of subscriptions serializer.'''

    recipes = RecipeMinifiedSerializer(read_only=True, many=True)
    recipes_count = serializers.IntegerField(read_only=True, required=False)
    is_subscribed = serializers.BooleanField(default=True)

    def to_representation(self, obj):
        recipes_limit = self.context.get('recipes_limit')
        results = super().to_representation(obj)
        results['recipes'] = RecipeMinifiedSerializer(
            obj.recipes.all()[:recipes_limit], many=True).data
        return results

    class Meta(UserSerializer.Meta):
        fields = ('id', 'username', 'first_name', 'recipes_count',
                  'last_name', 'is_subscribed', 'recipes', 'email')
        read_only_fields = ('email', 'first_name', 'last_name', 'username')


class SubscribeSerializer(serializers.ModelSerializer):
    '''Subscribe model serializer.'''

    def validate(self, data):
        if self.context.get('request').user == data.get('subscription'):
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя')
        return data

    def to_representation(self, obj):
        recipes_limit = self.context.get('recipes_limit')
        user = obj.subscription
        user_recipes = user.recipes.all()
        recipes_to_repr = RecipeMinifiedSerializer(
            user_recipes[:recipes_limit], many=True).data

        request_user = self.context.get('request').user
        subscription = request_user.subscriber.filter(subscription=user)
        is_subscribed = bool(subscription)

        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'recipes': recipes_to_repr,
            'is_subscribed': is_subscribed,
            'recipes_count': user_recipes.count()
        }

    class Meta:
        model = Subscribe
        fields = ('id', 'user', 'subscription')

        validators = [
            UniqueTogetherValidator(
                queryset=Subscribe.objects.all(),
                fields=('user', 'subscription'),
                message='Вы уже подписаны'
            )
        ]
