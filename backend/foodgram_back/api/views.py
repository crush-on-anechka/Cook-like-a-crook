import csv

from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, OuterRef
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from recipes.models import (Amount, Favorite, Ingredient, Recipe, ShoppingCart,
                            Tag)
from rest_framework import filters, permissions, status, viewsets
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

    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)

    @action(detail=False,
            methods=['GET'],
            permission_classes=(permissions.IsAuthenticated,),
            url_path='subscriptions'
            )
    def _CustomUserViewSet__subscriptions(self, request):

        subscriptions = User.objects.filter(
            subscription__user=request.user).annotate(
                recipes_count=Count('recipes'))
        if not subscriptions:
            return Response(status=status.HTTP_200_OK)

        recipes_limit = request.query_params.get('recipes_limit')
        ctx = {'recipes_limit': int(recipes_limit)} if recipes_limit else {}

        page = self.paginate_queryset(subscriptions)
        if page:
            serializer = SubscriptionsListSerializer(
                page, many=True, context=ctx)
            return self.get_paginated_response(serializer.data)

        serializer = SubscriptionsListSerializer(
            subscriptions, many=True, context=ctx)
        return Response(serializer.data)

    @action(detail=True,
            methods=['POST', 'DELETE'],
            permission_classes=(permissions.IsAuthenticated,),
            url_path='subscribe'
            )
    def _CustomUserViewSet__subscribe(self, request, **kwargs):
        context = {'request': request}
        recipes_limit = request.query_params.get('recipes_limit')
        if recipes_limit:
            context['recipes_limit'] = int(recipes_limit)

        kwargs.update({
            'serializer': SubscribeSerializer,
            'model': Subscribe,
            'context': context
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
        user = self.request.user

        if user.is_authenticated:
            recipe = OuterRef('id')
            favorite = user.favorite.filter(recipe=recipe)
            shopping_cart = user.shopping_cart.filter(recipe=recipe)

            return Recipe.objects.annotate(
                is_favorited=Exists(favorite)).annotate(
                    is_in_shopping_cart=Exists(shopping_cart))

        return Recipe.objects.all()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True,
            methods=['POST', 'DELETE'],
            permission_classes=(permissions.IsAuthenticated,),
            url_path='shopping_cart'
            )
    def _RecipeViewSet__shopping_cart(self, request, **kwargs):
        kwargs.update({
            'serializer': ShoppingCartSerializer,
            'model': ShoppingCart,
        })
        return perform_action(self, request, 'recipe', **kwargs)

    @action(detail=True,
            methods=['POST', 'DELETE'],
            permission_classes=(permissions.IsAuthenticated,),
            url_path='favorite'
            )
    def _RecipeViewSet__favorite(self, request, **kwargs):
        kwargs.update({
            'serializer': FavoriteSerializer,
            'model': Favorite,
        })
        return perform_action(self, request, 'recipe', **kwargs)

    @action(detail=False,
            methods=['GET'],
            permission_classes=(permissions.IsAuthenticated,),
            url_path='download_shopping_cart'
            )
    def _RecipeViewSet__download_shopping_cart(self, request, **kwargs):

        SUMMED_UP_AMOUNTS = {}
        INGR_DATA = []

        recipes = Recipe.objects.filter(shopping_cart__user=request.user)

        for recipe in recipes:
            ingredients = recipe.ingredients.all()
            for ingredient in ingredients:
                if ingredient.name not in SUMMED_UP_AMOUNTS:
                    SUMMED_UP_AMOUNTS[ingredient.name] = 0
                ingred_in_recipe = get_object_or_404(
                    Amount, recipe=recipe, ingredient=ingredient).amount
                INGR_DATA.append((ingredient, recipe.name, ingred_in_recipe))
                SUMMED_UP_AMOUNTS[ingredient.name] = (
                    SUMMED_UP_AMOUNTS.get(ingredient.name) + ingred_in_recipe)

        response = HttpResponse(
            content_type='text/csv',
            headers={
                'Content-Disposition': 'attachment; '
                'filename="shopping_cart.txt"'
            },
        )

        writer = csv.writer(response)
        writer.writerow(['Список покупок:'])

        for name, amount in SUMMED_UP_AMOUNTS.items():
            ingredient = get_object_or_404(Ingredient, name=name)
            writer.writerow(
                [f'{name} — {amount} {ingredient.measurement_unit}:'])

            for item in INGR_DATA:
                if item[0] == ingredient:
                    writer.writerow([f'    {item[1]} — {item[2]}'])

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
