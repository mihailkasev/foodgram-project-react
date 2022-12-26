from django.contrib import admin

from .models import Cart, Favorite, Ingredient, IngredientInRecipe, Recipe, Tag


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    list_filter = ('name',)


class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'in_favorite')
    list_filter = ('name', 'author', 'tags')

    def in_favorite(self, obj):
        return obj.favorite.all().count()


class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)


class IngredientInRecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe')


admin.site.register(Favorite)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(IngredientInRecipe, IngredientInRecipeAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Cart)
