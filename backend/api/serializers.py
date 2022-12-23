from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.serializers import (ModelSerializer, SerializerMethodField,
                                        UniqueTogetherValidator,
                                        ValidationError)
from djoser.serializers import UserSerializer
from drf_base64.fields import Base64ImageField

from recipes.models import (Cart, Favorite, Ingredient, IngredientInRecipe,
                            Recipe, Tag)
from users.models import Subscription, User


class IngredientSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Ingredient


class ListIngredientInRecipeSerializer(ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient',
        read_only=True
    ),
    measurement_unit = serializers.SlugRelatedField(
        source='ingredient',
        slug_field='measurement_unit',
        read_only=True
    )
    name = serializers.SlugRelatedField(
        source='ingredient',
        slug_field='name',
        read_only=True
    )

    class Meta:
        model = IngredientInRecipe
        fields = (
            'id',
            'name',
            'measurement_unit',
            'amount',
        )


class CreateIngredientInRecipeSerializer(ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient',
        queryset=Ingredient.objects.all()
    )

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'amount')

    def create(self, validated_data):
        return IngredientInRecipe.objects.create(
            ingredient=validated_data.get('id'),
            amount=validated_data.get('amount')
        )


class TagSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Tag


class RecipeReadSerializer(ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = ListIngredientInRecipeSerializer(
        source='ingredients_recipe',
        many=True,
        read_only=True
    )
    is_favorited = SerializerMethodField(read_only=True)
    is_in_shopping_cart = SerializerMethodField(read_only=True)

    class Meta:
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time'
        )
        model = Recipe

    def get_is_favorited(self, obj):
        request = self.context['request']
        if not request or request.user.is_anonymous:
            return False
        return Favorite.objects.filter(
            user=self.context['request'].user, recipe__id=obj.id
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context['request']
        if not request or request.user.is_anonymous:
            return False
        return Cart.objects.filter(
            user=self.context['request'].user, recipe__id=obj.id
        ).exists()


class RecipeWriteSerializer(ModelSerializer):
    ingredients = CreateIngredientInRecipeSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField(use_url=True, required=False)
    author = UserSerializer(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'ingredients',
            'tags',
            'image',
            'author',
            'name',
            'text',
            'cooking_time'
        )

    def create_ingredients(self, recipe, ingredients):
        IngredientInRecipe.objects.bulk_create(
            [IngredientInRecipe(
                recipe=recipe,
                amount=ingredient['amount'],
                ingredient=ingredient['ingredient'],
            ) for ingredient in ingredients]
        )

    def validate(self, data):
        if data.get('ingredients'):
            ingredients = data.get('ingredients')
            ingredients_list = []
            for ingredient in ingredients:
                ingredient_id = ingredient.get('id')
                if ingredient_id in ingredients_list:
                    raise ValidationError(
                        'Подобный ингридиент уже имеется в рецепте.'
                    )
                ingredients_list.append(ingredient_id)
        return data

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request')
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(
            author=request.user,
            **validated_data
        )
        self.create_ingredients(recipe, ingredients)
        recipe.tags.set(tags)
        return recipe

    def update(self, instance, validated_data):
        if not validated_data.get('ingredients'):
            return super().update(instance, validated_data)
        with transaction.atomic():
            ingredients = validated_data.pop('ingredients')
            IngredientInRecipe.objects.filter(recipe=instance).delete()
            self.create_ingredients(instance, ingredients)
            return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeReadSerializer(
            instance,
            context={
                'request': self.context.get('request'),
            }
        ).data


class ShortRecipe(ModelSerializer):
    class Meta:
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )
        model = Recipe


class UsersSerializer(UserSerializer):

    is_subscribed = SerializerMethodField()

    class Meta:
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'is_subscribed'
        )
        model = User
        validators = (
            UniqueTogetherValidator(
                queryset=User.objects.all(),
                fields=('username', 'email')
            ),
        )

    def get_is_subscribed(self, obj: User):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Subscription.objects.filter(
            user=request.user, author=obj
        ).exists()


class SubscriptionListSerializer(ModelSerializer):
    is_subscribed = SerializerMethodField(read_only=True)
    recipes = SerializerMethodField()
    recipes_count = SerializerMethodField()

    class Meta:
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count'
        )
        model = User

    def get_is_subscribed(self, author):
        return Subscription.objects.filter(
            user=self.context['request'].user, author=author
        ).exists()

    def get_recipes(self, author):
        queryset = self.context['request']
        recipes_limit = queryset.query_params.get('recipes_limit')
        if not recipes_limit:
            return ShortRecipe(
                Recipe.objects.filter(author=author),
                many=True, context={'request': queryset}
            ).data
        return ShortRecipe(
                Recipe.objects.filter(author=author)[:int(recipes_limit)],
                many=True, context={'request: queryset'}
            ).data

    def get_recipes_count(self, author):
        return Recipe.objects.filter(author=author).count()


class SubscriptionSerializer(ModelSerializer):

    class Meta:
        model = Subscription
        fields = ('user', 'author')

    def validate(self, data):
        get_object_or_404(User, username=data.get('author'))
        if Subscription.objects.filter(
            user=self.context['request'].user,
            author=data.get('author')
        ).exists():
            raise ValidationError(
                {'Subscription_exists_error': 'Подписка существует.'}
            )
        if self.context['request'].user == data.get('author'):
            raise ValidationError(
                {'SelfSubscription_error':
                    'Подписка на самого себя невозможна'}
            )
        return data

    def to_representation(self, instance):
        return SubscriptionListSerializer(
            instance.author, context={'request': self.context['request']}
        ).data


class FavoriteSerializer(ModelSerializer):

    class Meta:
        fields = ('user', 'recipe')
        model = Favorite

    def validate(self, data):
        request = self.context['request']
        if not request or request.user.is_anonymous:
            return False
        if Favorite.objects.filter(
            user=request.user, recipe=data.get('recipe')
        ).exists():
            raise ValidationError(
                {'Favorite_exists_error': 'Рецепт уже в избранном.'}
            )
        return data

    def to_representation(self, instance):
        return ShortRecipe(
            instance.recipe,
            context={'request': self.context['request']}
        ).data


class CartSerializer(ModelSerializer):

    class Meta:
        model = Cart
        fields = ('user', 'recipe')

    def validate(self, data):
        request = self.context['request']
        if not request or request.user.is_anonymous:
            return False
        if Cart.objects.filter(
            user=request.user, recipe=data.get('recipe')
        ).exists():
            raise ValidationError(
                {'Cart_exists_error': 'Рецепт уже находится в корзине'}
            )
        return data

    def to_representation(self, instance):
        return ShortRecipe(
            instance.recipe,
            context={'request': self.context['request']}
        ).data
