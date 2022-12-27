from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from djoser.serializers import UserSerializer
from drf_base64.fields import Base64ImageField
from recipes.models import (Cart, Favorite, Ingredient, IngredientInRecipe,
                            Recipe, Tag)
from rest_framework import serializers
from rest_framework.serializers import (ModelSerializer, SerializerMethodField,
                                        UniqueTogetherValidator,
                                        ValidationError)
from users.models import Subscription, User


class UsersSerializer(UserSerializer):

    is_subscribed = SerializerMethodField(read_only=True)

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


class IngredientSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Ingredient


class CreateIngredientInRecipeSerializer(ModelSerializer):
    id = serializers.IntegerField(write_only=True)

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'amount')


class TagSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Tag


class RecipeReadSerializer(ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = UsersSerializer(read_only=True)
    ingredients = SerializerMethodField()
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

    def get_ingredients(self, obj):
        recipe = obj
        ingredients = recipe.ingredients.values(
            'id',
            'name',
            'measurement_unit',
            amount=F('ingredients_recipe__amount')
        )
        return ingredients

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
        queryset=Tag.objects.all(),
        many=True
    )
    image = Base64ImageField(
        use_url=True,
        max_length=None
    )
    author = UsersSerializer(read_only=True)

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
                ingredient=Ingredient.objects.get(id=ingredient['id'])
            ) for ingredient in ingredients]
        )

    def validate(self, data):
        list_ingredients = [
            ingredient['id'] for ingredient in data['ingredients']
        ]
        all_ingredients, unique_ingredients = (
            len(list_ingredients), len(set(list_ingredients)))

        if all_ingredients != unique_ingredients:
            raise ValidationError(
                {'IngredientsUniqueError':
                    'Ингредиенты должны быть уникальными'}
            )
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

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients')
        instance.ingredients.clear()
        self.create_ingredients(instance, ingredients)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeReadSerializer(
            instance,
            context={
                'request': self.context.get('request')
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
            user=self.context.get('request').user, author=author
        ).exists()

    def get_recipes(self, author):
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit')
        if not recipes_limit:
            return ShortRecipe(
                Recipe.objects.filter(author=author),
                many=True, context={'request': request}
            ).data
        return ShortRecipe(
            Recipe.objects.filter(author=author)[:int(recipes_limit)],
            many=True, context={'request': request}
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
