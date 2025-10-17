
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from accounts.models import CustomUser
from ..models import (
    EmergencyContact, ResourceCategory, LearningResource, IncidentReport, 
    SafetyCheckSettings, EmergencyAlert, VideoEvidence
)
from rest_framework.authtoken.models import Token

class AegisViewsTest(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='test@example.com',
            password='password123',
            full_name='Test User'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        self.contact = EmergencyContact.objects.create(
            user=self.user,
            name='John Doe',
            phone='1234567890'
        )
        self.category = ResourceCategory.objects.create(name='Test Category')
        self.resource = LearningResource.objects.create(
            title='Test Resource',
            resource_type='article',
            category=self.category,
            is_published=True
        )
        self.incident = IncidentReport.objects.create(
            user=self.user,
            incident_type='other',
            title='Test Incident',
            description='Test description',
            incident_date='2025-10-17T12:00:00Z'
        )

    def test_emergency_contacts_list(self):
        url = reverse('emergency-contacts-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_emergency_contact_detail(self):
        url = reverse('emergency-contact-detail', kwargs={'pk': self.contact.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'John Doe')

    def test_resource_categories(self):
        url = reverse('resource-categories')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_learning_resource_list(self):
        url = reverse('learning-resources-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_learning_resource_detail(self):
        url = reverse('learning-resource-detail', kwargs={'id': self.resource.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_submit_incident_report(self):
        url = reverse('submit-incident')
        data = {
            'incident_type': 'theft',
            'title': 'Another Incident',
            'description': 'Another description',
            'incident_date': '2024-10-17T13:00:00Z'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_incident_report_list(self):
        url = reverse('incident-reports-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_incident_report_detail(self):
        url = reverse('incident-report-detail', kwargs={'id': self.incident.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_safety_settings(self):
        url = reverse('safety-settings')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_manual_check_in(self):
        url = reverse('manual-check-in')
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_activate_emergency(self):
        url = reverse('activate-emergency')
        data = {
            'activation_method': 'button',
            'is_silent': False
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
