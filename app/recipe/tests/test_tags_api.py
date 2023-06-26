"""
Tests for tags API.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag

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
