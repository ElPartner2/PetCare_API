const API_URL = 'http://localhost:8000/api';

const loginSection = document.getElementById('login-section');
const dashboardSection = document.getElementById('dashboard-section');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const logoutBtn = document.getElementById('logout-btn');
const userGreeting = document.getElementById('user-greeting');
const petsList = document.getElementById('pets-list');
const petForm = document.getElementById('pet-form');
const medicalRecordsTable = document.getElementById('medical-records-table');
const selectedPetName = document.getElementById('selected-pet-name');

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('access_token');
    if (token) {
        showDashboard();
    } else {
        showLogin();
    }
});

loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    try {
        const response = await fetch(`${API_URL}/token/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const message = errorData.detail || errorData.non_field_errors?.[0] || 'Falló la autenticación';
            throw new Error(message);
        }

        const data = await response.json();
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        localStorage.setItem('user_email', '');
        localStorage.setItem('username', username);

        loginError.classList.add('hidden');
        showDashboard();
    } catch (error) {
        loginError.textContent = error.message || 'Credenciales incorrectas. Intenta de nuevo.';
        loginError.classList.remove('hidden');
        console.error(error);
    }
});

logoutBtn.addEventListener('click', () => {
    localStorage.clear();
    showLogin();
});

function showDashboard() {
    loginSection.classList.add('hidden');
    dashboardSection.classList.remove('hidden');
    logoutBtn.classList.remove('hidden');

    const displayName = localStorage.getItem('username') || localStorage.getItem('user_email') || 'Usuario';
    userGreeting.textContent = `Hola, ${displayName}`;
    userGreeting.classList.remove('hidden');

    loadPets();
}

function showLogin() {
    loginSection.classList.remove('hidden');
    dashboardSection.classList.add('hidden');
    logoutBtn.classList.add('hidden');
    userGreeting.classList.add('hidden');
    loginForm.reset();
    loginError.classList.add('hidden');
}

async function loadPets() {
    const token = localStorage.getItem('access_token');
    try {
        const response = await fetch(`${API_URL}/pets/`, {
            headers: { Authorization: `Bearer ${token}` }
        });

        if (response.status === 401 || response.status === 403) {
            logoutBtn.click();
            return;
        }

        const pets = await response.json();
        petsList.innerHTML = '';

        if (!Array.isArray(pets) || pets.length === 0) {
            petsList.innerHTML = '<li>No tienes mascotas registradas aún.</li>';
            return;
        }

        pets.forEach((pet) => {
            const li = document.createElement('li');
            li.className = 'pet-item';

            const info = document.createElement('span');
            info.innerHTML = `<strong>${pet.name}</strong> (${pet.species}${pet.breed ? ` · ${pet.breed}` : ''})`;

            const button = document.createElement('button');
            button.type = 'button';
            button.textContent = 'Ver Historial';
            button.style.padding = '2px 8px';
            button.style.cursor = 'pointer';
            button.addEventListener('click', () => loadMedicalRecords(pet.id, pet.name));

            li.appendChild(info);
            li.appendChild(button);
            petsList.appendChild(li);
        });
    } catch (error) {
        console.error('Error cargando mascotas:', error);
    }
}

petForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const token = localStorage.getItem('access_token');
    const nombre = document.getElementById('pet-name').value.trim();
    const especie = document.getElementById('pet-species').value.trim();
    const raza = document.getElementById('pet-breed').value.trim();
    const birthDate = document.getElementById('pet-birth-date').value;

    try {
        const response = await fetch(`${API_URL}/pets/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`
            },
            body: JSON.stringify({
                name: nombre,
                species: especie,
                breed: raza,
                birth_date: birthDate
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || errorData.birth_date?.[0] || 'No se pudo guardar la mascota');
        }

        petForm.reset();
        loadPets();
    } catch (error) {
        console.error('Error creando mascota:', error);
        alert(error.message);
    }
});

async function loadMedicalRecords(petId, petName) {
    const token = localStorage.getItem('access_token');
    selectedPetName.textContent = `- de ${petName}`;

    try {
        const response = await fetch(`${API_URL}/medical-records/`, {
            headers: { Authorization: `Bearer ${token}` }
        });

        if (response.status === 401 || response.status === 403) {
            logoutBtn.click();
            return;
        }

        const records = await response.json();
        medicalRecordsTable.innerHTML = '';

        const petRecords = Array.isArray(records)
            ? records.filter((record) => record.pet === petId)
            : [];

        if (petRecords.length === 0) {
            medicalRecordsTable.innerHTML = '<tr><td colspan="3" class="text-center">No hay registros clínicos para esta mascota.</td></tr>';
            return;
        }

        petRecords.forEach((record) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${record.application_date || 'N/A'}</td>
                <td>${record.description || 'Sin descripción'}</td>
                <td><button type="button" style="color:red; border:none; background:none; cursor:pointer;">Eliminar</button></td>
            `;

            const deleteButton = tr.querySelector('button');
            deleteButton.addEventListener('click', () => deleteRecord(record.id, petId, petName));
            medicalRecordsTable.appendChild(tr);
        });
    } catch (error) {
        console.error('Error cargando registros médicos:', error);
    }
}

async function deleteRecord(recordId, petId, petName) {
    if (!confirm('¿Estás seguro de eliminar este registro clínico?')) {
        return;
    }

    const token = localStorage.getItem('access_token');
    try {
        const response = await fetch(`${API_URL}/medical-records/${recordId}/`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${token}` }
        });

        if (response.ok) {
            loadMedicalRecords(petId, petName);
        }
    } catch (error) {
        console.error('Error al eliminar registro:', error);
    }
}