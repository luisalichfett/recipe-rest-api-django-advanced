"""
Tests for tags API.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (Tag, Recipe)

from recipe.serializers import TagSerializer


TAGS_URL = reverse('recipe:tag-list')


def detail_url(tag_id):
    """Create and return a tag detail URL."""

    return reverse('recipe:tag-detail', args=[tag_id])


def create_user(email='test@example.com', password='testpass123'):
    """Create and return a new user."""

    return get_user_model().objects.create_user(email=email, password=password)


def create_tag(user, **params):
    """Create and return a sample tag."""

    defaults = {'name': 'Dessert'}

    defaults.update(params)

    tag = Tag.objects.create(user=user, **defaults)

    return tag


class PublicTagsApiTests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving tags."""

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """Test retrieving a list of tags."""

        create_tag(user=self.user)
        create_tag(user=self.user, name='Vegan')

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data, serializer.data)

    def test_tag_list_limited_to_user(self):
        """Test list of tags is limited to authenticated user."""

        other_user = create_user(
            email='other@example.com',
            password='password123',
        )

        create_tag(user=other_user, name='Fruity')
        tag = create_tag(user=self.user, name='Comfort Food')

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)

    def test_update_tag(self):
        """Test updating a tag."""

        tag = create_tag(user=self.user, name='After Dinner')

        payload = {'name': 'Dessert'}

        url = detail_url(tag.id)

        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        tag.refresh_from_db()

        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        """Test deleting a tag successful."""

        tag = create_tag(user=self.user, name='Breakfast')

        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        tags = Tag.objects.filter(user=self.user)

        self.assertFalse(tags.exists())

    def test_filter_tags_assigned_to_recipes(self):
        """Tets listing tags by those assigned to recipes."""

        tag1 = create_tag(user=self.user, name='Dessert')
        tag2 = create_tag(user=self.user, name='Winter')

        recipe = Recipe.objects.create(
            title='Apple Pie',
            time_minutes=30,
            price='5.00',
            user=self.user,
        )

        recipe.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filter_tags_unique(self):
        """Tets filtered tags returns a unique list."""

        tag = create_tag(user=self.user, name='Dessert')
        create_tag(user=self.user, name='Summer')

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

        recipe1.tags.add(tag)
        recipe2.tags.add(tag)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
