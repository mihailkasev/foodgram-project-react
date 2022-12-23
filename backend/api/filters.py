from django_filters.rest_framework import FilterSet, filters
from django_filters.rest_framework.filters import (BooleanFilter,
                                                   ModelMultipleChoiceFilter)
from rest_framework.filters import SearchFilter

from recipes.models import Recipe, Tag



class IngredientFilter(SearchFilter):
    name = filters.CharFilter(lookup_expr='startswith')


class RecipeFilterSet(FilterSet):
    tags = ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all()
    )
    is_favorited = BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = BooleanFilter(method='filter_is_in_shopping_cart')

    class Meta:
        fields = ('author', 'tags', 'is_favorited', 'is_in_shopping_cart')
        model = Recipe

    def filter_is_favorited(self, queryset, value):
        if self.request.user.is_authenticated and value:
            return queryset.filter(favorite__user=self.request.user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, value):
        if self.request.user.is_authenticated and value:
            return queryset.filter(cart__user=self.request.user)
        return queryset.all()
