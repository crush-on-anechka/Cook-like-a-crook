from django_filters import (CharFilter, ChoiceFilter, FilterSet,
                            ModelMultipleChoiceFilter)
from recipes.models import Tag


class RecipeFilterSet(FilterSet):

    BOOL_CHOICES = {
        (1, True),
        (0, False)
    }

    author = CharFilter(
        field_name='author__id',
        lookup_expr='icontains'
    )

    tags = ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )

    is_favorited = ChoiceFilter(
        choices=BOOL_CHOICES,
        field_name='is_favorited',
    )

    is_in_shopping_cart = ChoiceFilter(
        choices=BOOL_CHOICES,
        field_name='is_in_shopping_cart',
    )
