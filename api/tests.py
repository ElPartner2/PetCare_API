from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from .models import MedicalRecord, Pet


class UserRegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/users/register/'
        self.payload = {
            'username': 'newowner',
            'email': 'NewOwner@Example.com',
            'first_name': 'New',
            'last_name': 'Owner',
            'phone': '5551234567',
            'password': 'A-strong-password-938!',
            'password_confirm': 'A-strong-password-938!',
        }

    def test_registration_is_public_and_hashes_password(self):
        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(username='newowner')
        self.assertTrue(user.check_password(self.payload['password']))
        self.assertNotEqual(user.password, self.payload['password'])
        self.assertEqual(user.email, 'NewOwner@example.com')
        self.assertNotIn('password', response.data)
        self.assertNotIn('password_confirm', response.data)

    def test_mismatched_passwords_are_rejected(self):
        payload = {**self.payload, 'password_confirm': 'Different-password-1!'}

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password_confirm', response.data)

    def test_weak_password_is_rejected(self):
        payload = {
            **self.payload,
            'password': 'password',
            'password_confirm': 'password',
        }

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_duplicate_username_and_email_are_rejected_by_field(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username=self.payload['username'],
            email='first@example.com',
            password='A-strong-password-938!',
            phone='1',
        )
        username_response = self.client.post(self.url, self.payload, format='json')
        email_payload = {
            **self.payload,
            'username': 'anotherowner',
            'email': 'FIRST@EXAMPLE.COM',
        }
        email_response = self.client.post(self.url, email_payload, format='json')

        self.assertEqual(username_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', username_response.data)
        self.assertEqual(email_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', email_response.data)

    def test_users_are_not_publicly_listable(self):
        response = self.client.get('/api/users/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


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
    def test_patch_can_change_status_without_changing_owner(self):
        pet = self.create_pet(status='active')

        response = self.client.patch(
            f'/api/pets/{pet.id}/',
            {'status': 'inactive', 'owner': str(self.other_user.id)},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pet.refresh_from_db()
        self.assertEqual(pet.status, 'inactive')
        self.assertEqual(pet.owner, self.user)

    def test_future_birth_date_and_unknown_status_are_rejected(self):
        pet = self.create_pet()

        future_response = self.client.patch(
            f'/api/pets/{pet.id}/',
            {'birth_date': str(timezone.localdate() + timedelta(days=1))},
            format='json',
        )
        status_response = self.client.patch(
            f'/api/pets/{pet.id}/', {'status': 'lost'}, format='json'
        )

        self.assertEqual(future_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('birth_date', future_response.data)
        self.assertEqual(status_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', status_response.data)

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
    def test_patch_updates_editable_fields_but_not_application_date(self):
        application_date = timezone.now() - timedelta(days=2)
        record = self.create_record(application_date=application_date)
        booster_date = timezone.now() + timedelta(days=30)

        response = self.client.patch(
            f'/api/medical-records/{record.id}/',
            {
                'type_record': 'vaccination',
                'description': 'Updated through patch',
                'booster_date': booster_date.isoformat(),
                'application_date': (timezone.now() + timedelta(days=10)).isoformat(),
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        record.refresh_from_db()
        self.assertEqual(record.type_record, 'vaccination')
        self.assertEqual(record.description, 'Updated through patch')
        self.assertEqual(record.application_date, application_date)
        self.assertEqual(record.booster_date, booster_date)

    def test_record_cannot_be_reassigned_to_foreign_pet(self):
        record = self.create_record()
        foreign_pet = self.create_pet(owner=self.other_user)

        response = self.client.patch(
            f'/api/medical-records/{record.id}/',
            {'pet': str(foreign_pet.id)},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        record.refresh_from_db()
        self.assertNotEqual(record.pet, foreign_pet)

    def test_foreign_record_cannot_be_updated(self):
        foreign_pet = self.create_pet(owner=self.other_user)
        record = self.create_record(pet=foreign_pet)

        response = self.client.patch(
            f'/api/medical-records/{record.id}/',
            {'description': 'No access'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

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
