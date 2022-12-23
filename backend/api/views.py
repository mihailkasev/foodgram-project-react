from datetime import datetime

from django.http import HttpResponse
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from recipes.models import (Cart, Favorite, Ingredient, IngredientInRecipe,
                            Recipe, Tag)
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from users.models import Subscription, User

from .filters import IngredientFilter, RecipeFilterSet
from .permissions import AdminOrReadOnly, RecipePermission
from .serializers import (CartSerializer, FavoriteSerializer,
                          IngredientSerializer, RecipeReadSerializer,
                          RecipeWriteSerializer, SubscriptionListSerializer,
                          SubscriptionSerializer, TagSerializer)


class IngredientViewSet(ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AdminOrReadOnly]
    filter_backends = (IngredientFilter,)
    search_fields = ('^name',)


class TagViewSet(ModelViewSet):
    queryset = Tag.objects.all()
    permission_classes = [AdminOrReadOnly]
    serializer_class = TagSerializer


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilterSet
    permission_classes = [RecipePermission]

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    @action(methods=['post', 'delete'], detail=True)
    def favorite(self, request, pk):
        if request.method != 'POST':
            favorite = get_object_or_404(
                Favorite,
                user=request.user,
                recipe=get_object_or_404(Recipe, pk=pk)
            )
            self.perform_destroy(favorite)
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = FavoriteSerializer(
            data={
                'user': request.user.id,
                'recipe': get_object_or_404(Recipe, pk=pk).pk
            },
            context={'request': request}
        )
        serializer.is_valid()
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=['post', 'delete'], detail=True)
    def shopping_cart(self, request, pk):
        if request.method != 'POST':
            shopping_cart = get_object_or_404(
                Cart,
                user=request.user,
                recipe=get_object_or_404(Recipe, pk=pk)
            )
            self.perform_destroy(shopping_cart)
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = CartSerializer(
            data={
                'user': request.user.id,
                'recipe': get_object_or_404(Recipe, pk=pk).pk
            },
            context={'request': request}
        )
        serializer.is_valid()
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        ingredients = IngredientInRecipe.objects.filter(
            recipe__cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(amount=Sum('amount'))

        today = datetime.today()
        shopping = (
            f'{request.user.username}, Ваш список покупок готов!\n'
            f'Дата: {today:%Y-%m-%d}\n\n'
        )
        shopping += '\n'.join([
            f'- {ingredient["ingredient__name"]} '
            f'({ingredient["ingredient__measurement_unit"]})'
            f' - {ingredient["amount"]}'
            for ingredient in ingredients
        ])
        filename = f'{request.user.username}_shopping.txt'
        response = HttpResponse(shopping, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response


class UsersViewSet(UserViewSet):

    @action(['get'], detail=False, permission_classes=[IsAuthenticated])
    def me(self, request, *args, **kwargs):
        self.get_object = self.get_instance
        return self.retrieve(request, *args, **kwargs)

    @action(['get'], detail=False)
    def subscriptions(self, request):
        all_subscriptions = self.paginate_queryset(User.objects.filter(
            subscription__user=request.user
        ))
        serializer = SubscriptionListSerializer(
            all_subscriptions,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(methods=['post', 'delete'], detail=True)
    def subscribe(self, request, id):
        if request.method != 'POST':
            subscription = get_object_or_404(
                Subscription,
                user=request.user,
                author=get_object_or_404(User, id=id)
            )
            self.perform_destroy(subscription)
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = SubscriptionSerializer(
            data={
                'user': request.user.id,
                'author': get_object_or_404(User, id=id).id
            },
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
