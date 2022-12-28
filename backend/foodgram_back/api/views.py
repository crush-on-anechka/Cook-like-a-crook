import csv

from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, OuterRef
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from recipes.models import (Amount, Favorite, Ingredient, Recipe, ShoppingCart,
                            Tag)
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from users.models import Subscribe

from .filters import RecipeFilterSet
from .permissions import IsAuthorOrReadOnly
from .serializers import (FavoriteSerializer, IngredientSerializer,
                          RecipeCreateUpdateSerializer, RecipeGetSerializer,
                          ShoppingCartSerializer, SubscribeSerializer,
                          SubscriptionsListSerializer, TagSerializer)
from .utils import perform_action

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    '''User model view set.'''

    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):

        if self.request.user.is_authenticated:

            subscribed = Subscribe.objects.filter(
                user=self.request.user,
                subscription=OuterRef('id')
            )
            return User.objects.annotate(
                is_subscribed=Exists(subscribed))

        return User.objects.all()

    @action(detail=False,
            methods=['GET'],
            permission_classes=(permissions.IsAuthenticated,),
            name='My information'
            )
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False,
            methods=['GET'],
            permission_classes=(permissions.IsAuthenticated,),
            )
    def subscriptions(self, request):
        subscribers_ids = self.request.user.subscriber.values_list(
            'subscription',
            flat=True
        )
        subscribers = User.objects.filter(
            pk__in=subscribers_ids).annotate(recipes_count=Count('recipes'))

        recipes_limit = request.query_params.get('recipes_limit')
        ctx = {'recipes_limit': int(recipes_limit)} if recipes_limit else {}

        page = self.paginate_queryset(subscribers)
        if page is not None:
            serializer = SubscriptionsListSerializer(
                page, many=True, context=ctx)
            return self.get_paginated_response(serializer.data)

        serializer = SubscriptionsListSerializer(
            subscribers, many=True, context=ctx)
        return Response(serializer.data)

    @action(detail=True,
            methods=['POST', 'DELETE'],
            permission_classes=(permissions.IsAuthenticated,),
            )
    def subscribe(self, request, **kwargs):
        recipes_limit = request.query_params.get('recipes_limit')
        ctx = {'recipes_limit': int(recipes_limit)} if recipes_limit else {}

        kwargs.update({
            'serializer': SubscribeSerializer,
            'model': Subscribe,
            'ctx': ctx
        })
        return perform_action(self, request, 'subscription', **kwargs)


class RecipeViewSet(viewsets.ModelViewSet):
    '''Recipe model view set.'''

    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilterSet

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecipeGetSerializer
        return RecipeCreateUpdateSerializer

    def get_permissions(self):
        if self.action in ('update', 'partial_update', 'destroy'):
            return (IsAuthorOrReadOnly(),)
        return super().get_permissions()

    def get_queryset(self):

        if self.request.user.is_authenticated:

            favorite = Favorite.objects.filter(
                user=self.request.user,
                recipe=OuterRef('id')
            )
            shopping_cart = ShoppingCart.objects.filter(
                user=self.request.user,
                recipe=OuterRef('id')
            )
            return Recipe.objects.annotate(
                is_favorited=Exists(favorite)).annotate(
                    is_in_shopping_cart=Exists(shopping_cart))

        return Recipe.objects.all()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True,
            methods=['POST', 'DELETE'],
            permission_classes=(permissions.IsAuthenticated,),
            )
    def shopping_cart(self, request, **kwargs):
        kwargs.update({
            'serializer': ShoppingCartSerializer,
            'model': ShoppingCart,
        })
        return perform_action(self, request, 'recipe', **kwargs)

    @action(detail=True,
            methods=['POST', 'DELETE'],
            permission_classes=(permissions.IsAuthenticated,),
            )
    def favorite(self, request, **kwargs):
        kwargs.update({
            'serializer': FavoriteSerializer,
            'model': Favorite,
        })
        return perform_action(self, request, 'recipe', **kwargs)

    @action(detail=False,
            methods=['GET'],
            permission_classes=(permissions.IsAuthenticated,),
            )
    def download_shopping_cart(self, request, **kwargs):

        SHOPPING_LIST = {}

        recipes = request.user.recipes.all()
        for recipe in recipes:
            ingredients = recipe.ingredients.all()
            for ingredient in ingredients:
                if ingredient.name not in SHOPPING_LIST:
                    SHOPPING_LIST[ingredient.name] = 0
                ingredient_in_recipe = Amount.objects.get(
                    recipe=recipe, ingredient=ingredient)
                intermediate_amount = SHOPPING_LIST.get(ingredient.name)
                SHOPPING_LIST[ingredient.name] = (
                    intermediate_amount + ingredient_in_recipe.amount)

        response = HttpResponse(
            content_type='text/csv',
            headers={
                'Content-Disposition': 'attachment; '
                'filename="shopping_cart.txt"'
            },
        )

        writer = csv.writer(response)
        writer.writerow(['Список покупок:'])
        for name, amount in SHOPPING_LIST.items():
            unit = get_object_or_404(Ingredient, name=name).measurement_unit
            writer.writerow([f'{name} ({unit}) — {amount}'])

        return response


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    '''Tag model view set.'''

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    '''Ingredient model view set.'''

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (filters.SearchFilter,)
    pagination_class = None
    search_fields = ('^name',)
