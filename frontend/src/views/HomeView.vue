// frontend/src/views/HomeView.vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import TasksDashboard from '../components/tasks/TasksDashboard.vue'
import TelegramLogin from '../components/TelegramLogin.vue'

const router = useRouter()
const isAuthenticated = ref(false)
const userToken = ref(localStorage.getItem('access_token') || '')

// Состояния форм
const authMode = ref<'login' | 'register' | 'telegram'>('login')
const username = ref('')
const password = ref('')
const errorMessage = ref('')

onMounted(() => {
  if (userToken.value) {
    isAuthenticated.value = true
  }
})

// Авторизация по логину/паролю
const handleLogin = async () => {
  errorMessage.value = '';
  try {
    const params = new URLSearchParams();
    params.append('username', username.value);
    params.append('password', password.value);

    const response = await fetch('/api/auth/token', {
      method: 'POST',
      body: params,
    });

    if (response.ok) {
      const data = await response.json();
      localStorage.setItem('access_token', data.access_token);
      userToken.value = data.access_token;
      isAuthenticated.value = true;
    } else {
      errorMessage.value = 'Неверный логин или пароль';
    }
  } catch (error) {
    console.error("Fetch error [login]:", error);
    errorMessage.value = 'Ошибка соединения с сервером (см. консоль)';
  }
};

// Регистрация
const handleRegister = async () => {
  errorMessage.value = '';
  try {
    const response = await fetch('/api/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username: username.value,
        password: password.value
      }),
    });

    if (response.ok) {
      await handleLogin();
    } else {
      const data = await response.json();
      errorMessage.value = data.detail || 'Ошибка при регистрации';
    }
  } catch (error) {
    console.error("Fetch error [register]:", error);
    errorMessage.value = 'Ошибка соединения с сервером (см. консоль)';
  }
};

// Авторизация через Telegram
const handleTelegramAuth = async (user: any) => {
  errorMessage.value = '';
  try {
    const response = await fetch('/api/auth/telegram', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(user),
    });

    if (response.ok) {
      const data = await response.json();
      localStorage.setItem('access_token', data.access_token);
      userToken.value = data.access_token;
      isAuthenticated.value = true;
    } else {
      errorMessage.value = 'Не удалось подтвердить авторизацию через Telegram.';
    }
  } catch (error) {
    console.error("Fetch error [telegram]:", error);
    errorMessage.value = 'Ошибка соединения с сервером (см. консоль)';
  }
};

const logout = () => {
  localStorage.removeItem('access_token');
  userToken.value = '';
  isAuthenticated.value = false;
};
</script>

<template>
  <main>
    <div v-if="!isAuthenticated" class="auth-container">
      <h2>JetPlan</h2>
      <p>Для управления задачами, пожалуйста, войдите в систему.</p>
      
      <div class="auth-tabs">
        <button :class="{ active: authMode === 'login' }" @click="authMode = 'login'">Вход</button>
        <button :class="{ active: authMode === 'register' }" @click="authMode = 'register'">Регистрация</button>
        <button :class="{ active: authMode === 'telegram' }" @click="authMode = 'telegram'">Telegram</button>
      </div>

      <div class="error-message" v-if="errorMessage">{{ errorMessage }}</div>

      <form v-if="authMode === 'login'" @submit.prevent="handleLogin" class="auth-form">
        <input type="text" v-model="username" placeholder="Логин" required />
        <input type="password" v-model="password" placeholder="Пароль" required />
        <button type="submit" class="primary-btn">Войти</button>
      </form>

      <form v-if="authMode === 'register'" @submit.prevent="handleRegister" class="auth-form">
        <input type="text" v-model="username" placeholder="Придумайте логин" required />
        <input type="password" v-model="password" placeholder="Придумайте пароль" required minlength="6" />
        <button type="submit" class="primary-btn">Зарегистрироваться</button>
      </form>

      <div v-if="authMode === 'telegram'" class="telegram-section">
        <TelegramLogin 
          botName="jetplan_bot" 
          @callback="handleTelegramAuth" 
        />
        <p class="hint">Убедитесь, что используете протокол HTTPS или localhost</p>
      </div>
    </div>
    
    <div v-else>
      <div class="header-controls">
        <div class="user-status-badge">JetPlan Workspace</div>
        <div style="display: flex; gap: 1rem;">
          <button @click="router.push('/settings')" class="logout-btn">Настройки</button>
          <button @click="logout" class="logout-btn">Выйти</button>
        </div>
      </div>
      <TasksDashboard />
    </div>
  </main>
</template>

<style scoped>
.auth-container {
  max-width: 400px;
  margin: 4rem auto;
  text-align: center;
  padding: 2.5rem;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background-color: var(--color-background-soft);
  box-shadow: 0 4px 20px rgba(0,0,0,0.05);
}

.auth-container h2 {
  margin-bottom: 0.5rem;
  color: hsla(160, 100%, 37%, 1);
  font-size: 2rem;
  font-weight: 700;
}

.auth-container p {
  margin-bottom: 1.5rem;
  color: var(--color-text);
  font-size: 0.95rem;
}

.auth-tabs {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1.5rem;
  background: var(--color-background-mute);
  border-radius: 8px;
  padding: 4px;
}

.auth-tabs button {
  flex: 1;
  background: transparent;
  border: none;
  padding: 0.6rem;
  color: var(--color-text);
  cursor: pointer;
  border-radius: 6px;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.auth-tabs button.active {
  background: var(--color-background);
  color: hsla(160, 100%, 37%, 1);
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  font-weight: bold;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.auth-form input {
  padding: 0.9rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-background);
  color: var(--color-text);
  font-size: 1rem;
}

.auth-form input:focus {
  outline: none;
  border-color: hsla(160, 100%, 37%, 1);
}

.primary-btn {
  background-color: hsla(160, 100%, 37%, 1);
  color: white;
  border: none;
  padding: 0.9rem;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: bold;
  cursor: pointer;
  transition: background-color 0.2s;
}

.primary-btn:hover {
  background-color: hsla(160, 100%, 32%, 1);
}

.error-message {
  color: #ff4a4a;
  margin-bottom: 1rem;
  font-size: 0.9rem;
  background: #ffeded;
  padding: 0.5rem;
  border-radius: 6px;
}

.telegram-section .hint {
  font-size: 0.8rem;
  color: var(--color-text-light-2);
  margin-top: 1rem;
}

.header-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding: 0 1rem;
  max-width: 100%;
}

.user-status-badge {
  font-size: 1.2rem;
  font-weight: 800;
  color: var(--color-heading);
}

.logout-btn {
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text);
  padding: 0.5rem 1.2rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s;
}

.logout-btn:hover {
  background-color: var(--color-background-mute);
  border-color: var(--color-border-hover);
}
</style>
