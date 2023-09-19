"""
Tests for the health check API. 
"""

from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient


class HealthCheckTests(TestCase):
    """Test the health check API."""

    def text_health_check(self):
        """Test health check API."""

        client = APIClient()
        url = reverse("heatlh-check")
        res = client.get(url)

        self.assertEqual(res.status, status.HTTP_200_OK)
