from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from .models import MedicalRecord, Pet


class JWTAuthTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='admin',
            email='admin@example.com',
            password='securepass123',
            phone='123456789',
        )

    def test_login_with_username_and_password_returns_tokens(self):
        response = APIClient().post(
            '/api/token/',
            {'username': 'admin', 'password': 'securepass123'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)


class APITestCase(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='securepass123',
            phone='111111111',
        )
        self.other_user = user_model.objects.create_user(
            username='other',
            email='other@example.com',
            password='securepass123',
            phone='222222222',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def create_pet(self, owner=None, **overrides):
        values = {
            'owner': owner or self.user,
            'name': 'Luna',
            'species': 'dog',
            'breed': 'Mixed',
            'birth_date': timezone.localdate() - timedelta(days=365),
            'status': 'inactive',
        }
        values.update(overrides)
        return Pet.objects.create(**values)

    def create_record(self, pet=None, **overrides):
        values = {
            'pet': pet or self.create_pet(),
            'type_record': 'checkup',
            'description': 'Routine checkup',
        }
        values.update(overrides)
        return MedicalRecord.objects.create(**values)


class AuthenticationTests(APITestCase):
    def test_pet_and_medical_record_routes_require_authentication(self):
        client = APIClient()

        for url in ('/api/pets/', '/api/medical-records/'):
            response = client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PetAPITests(APITestCase):
    def test_pet_crud(self):
        create_response = self.client.post(
            '/api/pets/',
            {
                'name': 'Milo',
                'species': 'cat',
                'breed': 'Tabby',
                'birth_date': str(timezone.localdate() - timedelta(days=100)),
                'status': 'inactive',
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        pet_id = create_response.data['id']
        self.assertEqual(str(Pet.objects.get(id=pet_id).owner_id), str(self.user.id))

        list_response = self.client.get('/api/pets/')
        detail_response = self.client.get(f'/api/pets/{pet_id}/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        put_response = self.client.put(
            f'/api/pets/{pet_id}/',
            {
                'name': 'Milo Updated',
                'species': 'cat',
                'breed': 'Tabby',
                'birth_date': str(timezone.localdate() - timedelta(days=100)),
                'status': 'inactive',
            },
            format='json',
        )
        patch_response = self.client.patch(
            f'/api/pets/{pet_id}/', {'breed': 'European'}, format='json'
        )
        self.assertEqual(put_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)

        delete_response = self.client.delete(f'/api/pets/{pet_id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Pet.objects.filter(id=pet_id).exists())

    def test_active_pet_deletion_returns_conflict(self):
        pet = self.create_pet(status='active')

        response = self.client.delete(f'/api/pets/{pet.id}/')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Pet.objects.filter(id=pet.id).exists())

    def test_pet_with_active_medical_record_deletion_returns_conflict(self):
        record = self.create_record()

        response = self.client.delete(f'/api/pets/{record.pet_id}/')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_pet_with_archived_medical_record_deletion_returns_conflict(self):
        record = self.create_record(is_deleted=True, elimination_date=timezone.now())

        response = self.client.delete(f'/api/pets/{record.pet_id}/')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_pet_information_is_isolated_between_users(self):
        other_pet = self.create_pet(owner=self.other_user)

        list_response = self.client.get('/api/pets/')
        detail_response = self.client.get(f'/api/pets/{other_pet.id}/')
        update_response = self.client.patch(
            f'/api/pets/{other_pet.id}/', {'name': 'No access'}, format='json'
        )
        delete_response = self.client.delete(f'/api/pets/{other_pet.id}/')

        self.assertEqual(list_response.data, [])
        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(update_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(delete_response.status_code, status.HTTP_404_NOT_FOUND)


class MedicalRecordAPITests(APITestCase):
    def test_medical_record_crud_and_soft_delete(self):
        pet = self.create_pet()
        create_response = self.client.post(
            '/api/medical-records/',
            {
                'pet': str(pet.id),
                'type_record': 'vaccination',
                'description': 'First dose',
                'booster_date': (timezone.now() + timedelta(days=30)).isoformat(),
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        record_id = create_response.data['id']

        list_response = self.client.get('/api/medical-records/')
        detail_response = self.client.get(f'/api/medical-records/{record_id}/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        put_response = self.client.put(
            f'/api/medical-records/{record_id}/',
            {
                'pet': str(pet.id),
                'type_record': 'vaccination',
                'description': 'Updated dose',
                'booster_date': (timezone.now() + timedelta(days=40)).isoformat(),
            },
            format='json',
        )
        patch_response = self.client.patch(
            f'/api/medical-records/{record_id}/',
            {'description': 'Patched dose'},
            format='json',
        )
        self.assertEqual(put_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)

        delete_response = self.client.delete(f'/api/medical-records/{record_id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        record = MedicalRecord.objects.get(id=record_id)
        self.assertTrue(record.is_deleted)
        self.assertIsNotNone(record.elimination_date)
        self.assertEqual(
            self.client.get(f'/api/medical-records/{record_id}/').status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_archived_records_are_absent_from_lists_and_nested_pet_data(self):
        pet = self.create_pet()
        visible = self.create_record(pet=pet, description='Visible')
        archived = self.create_record(
            pet=pet,
            description='Archived',
            is_deleted=True,
            elimination_date=timezone.now(),
        )

        records_response = self.client.get('/api/medical-records/')
        pet_response = self.client.get(f'/api/pets/{pet.id}/')

        self.assertEqual(
            [item['id'] for item in records_response.data], [str(visible.id)]
        )
        nested_ids = [item['id'] for item in pet_response.data['medical_records']]
        self.assertEqual(nested_ids, [str(visible.id)])
        self.assertNotIn(str(archived.id), nested_ids)

    def test_filter_by_pet_only_returns_that_users_matching_records(self):
        pet = self.create_pet(name='First')
        other_pet = self.create_pet(name='Second')
        matching = self.create_record(pet=pet)
        self.create_record(pet=other_pet)
        foreign_pet = self.create_pet(owner=self.other_user)
        self.create_record(pet=foreign_pet)

        response = self.client.get('/api/medical-records/', {'pet': str(pet.id)})
        foreign_response = self.client.get(
            '/api/medical-records/', {'pet': str(foreign_pet.id)}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in response.data], [str(matching.id)])
        self.assertEqual(foreign_response.data, [])

    def test_invalid_pet_filter_returns_bad_request(self):
        response = self.client.get('/api/medical-records/', {'pet': 'invalid'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_medical_record_information_is_isolated_between_users(self):
        foreign_pet = self.create_pet(owner=self.other_user)
        foreign_record = self.create_record(pet=foreign_pet)

        self.assertEqual(self.client.get('/api/medical-records/').data, [])
        self.assertEqual(
            self.client.get(f'/api/medical-records/{foreign_record.id}/').status_code,
            status.HTTP_404_NOT_FOUND,
        )
        create_response = self.client.post(
            '/api/medical-records/',
            {
                'pet': str(foreign_pet.id),
                'type_record': 'checkup',
                'description': 'No access',
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_booster_date_before_application_date_is_rejected_on_post(self):
        pet = self.create_pet()

        response = self.client.post(
            '/api/medical-records/',
            {
                'pet': str(pet.id),
                'type_record': 'vaccination',
                'description': 'Invalid date',
                'booster_date': (timezone.now() - timedelta(days=1)).isoformat(),
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('booster_date', response.data)

    def test_booster_date_before_existing_application_date_is_rejected_on_updates(self):
        application_date = timezone.now() + timedelta(days=10)
        record = self.create_record(application_date=application_date)
        invalid_booster = (application_date - timedelta(days=1)).isoformat()
        full_payload = {
            'pet': str(record.pet_id),
            'type_record': record.type_record,
            'description': record.description,
            'booster_date': invalid_booster,
        }

        put_response = self.client.put(
            f'/api/medical-records/{record.id}/', full_payload, format='json'
        )
        patch_response = self.client.patch(
            f'/api/medical-records/{record.id}/',
            {'booster_date': invalid_booster},
            format='json',
        )

        self.assertEqual(put_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(patch_response.status_code, status.HTTP_400_BAD_REQUEST)
