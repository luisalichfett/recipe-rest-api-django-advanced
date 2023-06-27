"""
Test for the ingredients API.
"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (Ingredient, Recipe)

from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse('recipe:ingredient-list')


def detail_url(ingredient_id):
    """Create and return a ingredient detail URL."""

    return reverse('recipe:ingredient-detail', args=[ingredient_id])


def create_user(email='test@example.com', password='testpass123'):
    """Create and return a new user."""

    return get_user_model().objects.create_user(email=email, password=password)


def create_ingredient(user, **params):
    """Create and return a sample ingredient."""

    defaults = {'name': 'Sugar'}

    defaults.update(params)

    ingredient = Ingredient.objects.create(user=user, **defaults)

    return ingredient


class PublicIngredientsApiTests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving ingredients."""

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        """Test retrieving a list of ingredients."""

        create_ingredient(user=self.user)
        create_ingredient(user=self.user, name='Salt')

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data, serializer.data)

    def test_ingredient_list_limited_to_user(self):
        """Test list of ingredients is limited to authenticated user."""

        other_user = create_user(
            email='other@example.com',
            password='password123',
        )

        create_ingredient(user=other_user, name='Pepper')
        ingredient = create_ingredient(user=self.user, name='Olive Oil')

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'], ingredient.id)

    def test_update_ingredient(self):
        """Test updating a ingredient."""

        ingredient = create_ingredient(user=self.user, name='Cilantro')

        payload = {'name': 'Coriander'}

        url = detail_url(ingredient.id)

        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        ingredient.refresh_from_db()

        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        """Test deleting a ingredient successful."""

        ingredient = create_ingredient(user=self.user, name='Lettuce')

        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        ingredients = Ingredient.objects.filter(user=self.user)

        self.assertFalse(ingredients.exists())

    def test_filter_ingredients_assigned_to_recipes(self):
        """Tets listing ingredients by those assigned to recipes."""

        ingredient1 = create_ingredient(user=self.user, name='Apples')
        ingredient2 = create_ingredient(user=self.user, name='Peanuts')

        recipe = Recipe.objects.create(
            title='Apple Pie',
            time_minutes=30,
            price='5.00',
            user=self.user,
        )

        recipe.ingredients.add(ingredient1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        s1 = IngredientSerializer(ingredient1)
        s2 = IngredientSerializer(ingredient2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filter_ingredients_unique(self):
        """Tets filtered ingredients returns a unique list."""

        ingredient = create_ingredient(user=self.user, name='Chocolate Sirup')
        create_ingredient(user=self.user, name='Ice cream')

        recipe1 = Recipe.objects.create(
            title='Milk Shake',
            time_minutes=5,
            price='3.50',
            user=self.user,
        )

        recipe2 = Recipe.objects.create(
            title='Sundae',
            time_minutes=7,
            price='4.00',
            user=self.user,
        )

        recipe1.ingredients.add(ingredient)
        recipe2.ingredients.add(ingredient)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
