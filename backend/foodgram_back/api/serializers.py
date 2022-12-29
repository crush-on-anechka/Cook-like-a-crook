import base64

import djoser
from django.contrib.auth import get_user_model
from django.db import transaction
from recipes.models import (Amount, Favorite, Ingredient, Recipe, ShoppingCart,
                            Tag)
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from users.models import Subscribe

User = get_user_model()


class Base64ToImage(serializers.Field):
    '''Custom field for decoding Base64 data to an image.'''

    def to_representation(self, value):
        return value

    def to_internal_value(self, data):
        return base64.decodebytes(data)


class UserSerializer(djoser.serializers.UserSerializer):
    '''Basic user model serializer.'''

    is_subscribed = serializers.BooleanField(default=False)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name',
                  'last_name', 'is_subscribed')
        unique = ('username',)


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


class IngredientAddSerializer(IngredientSerializer):
    '''Ingredient model serializer to be nested in creating recipe.'''

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )

    class Meta:
        model = Amount
        fields = ('id', 'amount')


class AmountSerializer(serializers.ModelSerializer):
    '''Amount (of ingredients in a recipe) model serializer.'''

    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = Amount
        fields = ('id', 'name', 'measurement_unit', 'amount')


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

    ingredients = IngredientAddSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
    )
    image = Base64ToImage()

    def validate(self, data):
        blank_fields = []
        for field in self.Meta.fields:
            if field not in data:
                blank_fields.append(field)
        blank_fields.remove('id')
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
        except KeyError:
            raise serializers.ValidationError(
                'sorry, unexpected error occured')
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
            tags = validated_data.pop('tags')
        except KeyError:
            raise serializers.ValidationError(
                'sorry, unexpected error occured')

        instance.name = validated_data.get('name')
        instance.text = validated_data.get('text')
        instance.image = validated_data.get('image')
        instance.cooking_time = validated_data.get('cooking_time')

        instance.tags.set(tags)

        amounts_before = instance.amount.all()
        amounts_after = []

        for ingredient in ingredients:
            try:
                amount = Amount.objects.get(
                    recipe=instance,
                    ingredient=ingredient.get('ingredient')
                )
                amount.amount = ingredient.get('amount')
                amount.save()
            except Amount.DoesNotExist:
                amount = Amount.objects.create(
                    recipe=instance,
                    ingredient=ingredient.get('ingredient'),
                    amount=ingredient.get('amount')
                )
            amounts_after.append(amount)

        for amount in amounts_before:
            if amount not in amounts_after:
                amount.delete()

        instance.save()
        return instance

    def to_representation(self, obj):
        self.fields.pop('ingredients')
        self.fields.pop('image')
        results = super().to_representation(obj)
        results['ingredients'] = IngredientAddSerializer(
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
        if data['user'] == data['subscription']:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя')
        return data

    def to_representation(self, obj):
        recipes_limit = self.context.get('recipes_limit')
        user = obj.subscription
        all_recipes = user.recipes.all()
        recipes_count = all_recipes.count()
        recipes_to_repr = RecipeMinifiedSerializer(
            all_recipes[:recipes_limit], many=True).data

        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'recipes': recipes_to_repr,
            'is_subscribed': True,
            'recipes_count': recipes_count
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
