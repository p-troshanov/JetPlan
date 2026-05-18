// frontend/src/views/HomeView.vue
<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import TasksDashboard from '../components/tasks/TasksDashboard.vue'

const router = useRouter()
const isAuthenticated = ref(false)
const userToken = ref(localStorage.getItem('access_token') || '')

// Состояния форм
const authMode = ref<'login' | 'register' | 'telegram'>('login')
const username = ref('')
const password = ref('')
const errorMessage = ref('')

// Состояния для интерактивной авторизации Telegram
const tgUsername = ref('')
const authRequestId = ref('')
const tgAuthStatus = ref('')
let tgPollInterval: any = null

onMounted(() => {
  if (userToken.value) {
    isAuthenticated.value = true
  }
})

onUnmounted(() => {
  if (tgPollInterval) clearInterval(tgPollInterval)
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

// Интерактивный Telegram вход
const requestTelegramInteractiveAuth = async () => {
  errorMessage.value = '';
  tgAuthStatus.value = '';
  
  if (!tgUsername.value) {
    errorMessage.value = 'Введите логин Telegram';
    return;
  }

  try {
    const response = await fetch('/api/auth/telegram-interactive/request', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username: tgUsername.value }),
    });

    if (response.ok) {
      const data = await response.json();
      authRequestId.value = data.request_id;
      tgAuthStatus.value = 'Ожидаем подтверждения... Откройте бота @jetplan_bot и нажмите "Разрешить вход".';
      
      tgPollInterval = setInterval(pollTelegramAuthStatus, 2000);
    } else {
      const data = await response.json();
      errorMessage.value = data.detail || 'Ошибка при запросе входа';
    }
  } catch (error) {
    console.error("Fetch error [tg-interactive]:", error);
    errorMessage.value = 'Ошибка соединения с сервером';
  }
};

const pollTelegramAuthStatus = async () => {
  if (!authRequestId.value) return;

  try {
    const response = await fetch(`/api/auth/telegram-interactive/status?request_id=${authRequestId.value}`);
    if (response.ok) {
      const data = await response.json();
      if (data.status === 'approved') {
        clearInterval(tgPollInterval);
        localStorage.setItem('access_token', data.access_token);
        userToken.value = data.access_token;
        isAuthenticated.value = true;
        authRequestId.value = '';
        tgAuthStatus.value = '';
      } else if (data.status === 'denied') {
        clearInterval(tgPollInterval);
        errorMessage.value = 'Вход был отклонен в боте.';
        authRequestId.value = '';
        tgAuthStatus.value = '';
      } else if (data.status === 'expired') {
        clearInterval(tgPollInterval);
        errorMessage.value = 'Время ожидания вышло. Попробуйте снова.';
        authRequestId.value = '';
        tgAuthStatus.value = '';
      }
    }
  } catch (err) {
    console.error("Polling error", err);
  }
};

const logout = () => {
  localStorage.removeItem('access_token');
  userToken.value = '';
  isAuthenticated.value = false;
  if (tgPollInterval) clearInterval(tgPollInterval);
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
        <form v-if="!authRequestId" @submit.prevent="requestTelegramInteractiveAuth" class="auth-form">
          <input type="text" v-model="tgUsername" placeholder="Ваш логин (например, @durov)" required />
          <button type="submit" class="primary-btn">Отправить запрос боту</button>
        </form>
        
        <div v-else class="polling-status">
          <div class="spinner"></div>
          <p>{{ tgAuthStatus }}</p>
          <button @click="() => { clearInterval(tgPollInterval); authRequestId = ''; }" class="btn-cancel">Отмена</button>
        </div>
        
        <p class="hint" v-if="!authRequestId">Бот пришлет вам сообщение с кнопкой подтверждения. Вы должны хотя бы раз нажать /start в боте перед этим.</p>
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

.polling-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 1rem 0;
}

.spinner {
  width: 30px;
  height: 30px;
  border: 3px solid rgba(0,0,0,0.1);
  border-radius: 50%;
  border-top-color: hsla(160, 100%, 37%, 1);
  animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.btn-cancel {
  background: transparent;
  border: none;
  color: var(--color-text-light-2);
  cursor: pointer;
  text-decoration: underline;
  font-size: 0.9rem;
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
