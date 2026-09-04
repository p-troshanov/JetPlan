<!-- frontend/src/views/SettingsView.vue -->
<!-- Показывает профиль, настройки приложения, смену пароля и безопасную привязку Telegram. -->
<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore, type UserProfileUpdate } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const formData = ref({
  first_name: '',
  last_name: '',
  ai_provider: 'groq' as 'groq' | 'openrouter',
  ai_api_key: '',
  ai_model: '',
  stt_provider: 'groq' as const,
  stt_api_key: '',
  task_hotkey: 'ctrl+q',
  auto_postpone_overdue: false
})

const passData = ref({
  old_password: '',
  new_password: ''
})

const tgUsername = ref('')
const tgCode = ref('')
const codeSent = ref(false)
const message = ref('')
const isError = ref(false)
type ProfileSettingsSection = 'profile' | 'ai' | 'stt' | 'app'

const savingSection = ref<ProfileSettingsSection | null>(null)
let messageTimer: ReturnType<typeof setTimeout> | undefined

const profileSaveMessages: Record<ProfileSettingsSection, string> = {
  profile: 'Профиль сохранён',
  ai: 'Настройки нейросети сохранены',
  stt: 'Настройки голосового ввода сохранены',
  app: 'Настройки приложения сохранены',
}

const aiProviderName = computed(() => (
  formData.value.ai_provider === 'openrouter' ? 'OpenRouter' : 'Groq'
))

const aiKeyPlaceholder = computed(() => (
  userStore.profile?.ai_api_key_configured
    ? 'Ключ сохранён, оставьте поле пустым'
    : `API-ключ ${aiProviderName.value}`
))

const sttKeyPlaceholder = computed(() => (
  userStore.profile?.stt_api_key_configured
    ? 'Ключ Groq Whisper сохранён'
    : 'API-ключ Groq для Whisper'
))

onMounted(async () => {
  await userStore.fetchProfile()
  if (userStore.profile) {
    formData.value.first_name = userStore.profile.first_name || ''
    formData.value.last_name = userStore.profile.last_name || ''
    formData.value.ai_provider = userStore.profile.ai_provider || 'groq'
    formData.value.ai_api_key = ''
    formData.value.ai_model = userStore.profile.ai_model || ''
    formData.value.stt_api_key = ''
    formData.value.task_hotkey = userStore.profile.task_hotkey || 'ctrl+q'
    formData.value.auto_postpone_overdue = userStore.profile.auto_postpone_overdue || false
  }
})

const showMessage = (msg: string, error = false) => {
  if (messageTimer) clearTimeout(messageTimer)
  message.value = msg
  isError.value = error
  messageTimer = setTimeout(() => { message.value = '' }, 5000)
}

onUnmounted(() => {
  if (messageTimer) clearTimeout(messageTimer)
})

const saveProfile = async (section: ProfileSettingsSection) => {
  if (savingSection.value) return

  savingSection.value = section
  const payload: UserProfileUpdate = {
    first_name: formData.value.first_name,
    last_name: formData.value.last_name,
    ai_provider: formData.value.ai_provider,
    ai_model: formData.value.ai_provider === 'openrouter' ? formData.value.ai_model.trim() : null,
    stt_provider: 'groq',
    task_hotkey: formData.value.task_hotkey,
    auto_postpone_overdue: formData.value.auto_postpone_overdue,
  }
  if (formData.value.ai_api_key.trim()) payload.ai_api_key = formData.value.ai_api_key.trim()
  if (formData.value.stt_api_key.trim()) payload.stt_api_key = formData.value.stt_api_key.trim()

  const result = await userStore.updateProfile(payload)
  if (result.ok) {
    formData.value.ai_api_key = ''
    formData.value.stt_api_key = ''
    showMessage(profileSaveMessages[section])
  } else {
    showMessage(result.error || 'Ошибка при сохранении', true)
  }
  savingSection.value = null
}

const changePassword = async () => {
  if (!passData.value.old_password || !passData.value.new_password) return
  
  const res = await fetch('/api/auth/password', {
    method: 'PUT',
    headers: userStore.getHeaders(),
    body: JSON.stringify(passData.value)
  })
  
  if (res.ok) {
    showMessage('Пароль успешно изменен')
    passData.value.old_password = ''
    passData.value.new_password = ''
  } else {
    const err = await res.json()
    showMessage(err.detail || 'Ошибка изменения пароля', true)
  }
}

const requestTelegramCode = async () => {
  if (!tgUsername.value) {
    showMessage('Введите ваш логин Telegram', true)
    return
  }

  const res = await fetch('/api/auth/telegram/request-code', {
    method: 'POST',
    headers: userStore.getHeaders(),
    body: JSON.stringify({ username: tgUsername.value })
  })
  
  if (res.ok) {
    codeSent.value = true
    showMessage('Код отправлен вам в Telegram!')
  } else {
    const err = await res.json()
    showMessage(err.detail || 'Ошибка при отправке. Проверьте логин.', true)
  }
}

const verifyTelegramCode = async () => {
  if (!tgCode.value.trim()) {
    showMessage('Вставьте одноразовый код из Telegram', true)
    return
  }

  const res = await fetch('/api/auth/telegram/verify-code', {
    method: 'POST',
    headers: userStore.getHeaders(),
    body: JSON.stringify({ code: tgCode.value })
  })
  
  if (res.ok) {
    showMessage('Telegram успешно привязан')
    tgCode.value = ''
    codeSent.value = false
    await userStore.fetchProfile()
  } else {
    const err = await res.json()
    showMessage(err.detail || 'Неверный код', true)
  }
}
</script>

<template>
  <div class="settings-container">
    <div class="settings-header">
      <h2>Настройки</h2>
      <button class="btn btn-secondary" @click="router.push('/')">На главную</button>
    </div>

    <div
      v-if="message"
      :class="['alert', isError ? 'alert-error' : 'alert-success']"
      :role="isError ? 'alert' : 'status'"
      :aria-live="isError ? 'assertive' : 'polite'"
    >
      <span class="alert-icon" aria-hidden="true">{{ isError ? '!' : '✓' }}</span>
      <span>{{ message }}</span>
    </div>

    <div class="settings-content">
      
      <section class="settings-section">
        <h3>Профиль</h3>
        <div class="settings-form-grid">
          <label>Имя</label>
          <input type="text" v-model="formData.first_name" class="form-control" />
          
          <label>Фамилия</label>
          <input type="text" v-model="formData.last_name" class="form-control" />
          
          <div></div>
          <button
            class="btn btn-primary btn-auto"
            :disabled="savingSection !== null"
            :aria-busy="savingSection === 'profile'"
            @click="saveProfile('profile')"
          >
            {{ savingSection === 'profile' ? 'Сохранение…' : 'Сохранить профиль' }}
          </button>
        </div>
      </section>

      <section class="settings-section">
        <h3>Нейросеть</h3>
        <p class="section-description">Используется для текстовых команд на сайте и в Telegram.</p>
        <div class="settings-form-grid">
          <label>Провайдер</label>
          <select v-model="formData.ai_provider" class="form-control">
            <option value="groq">Groq</option>
            <option value="openrouter">OpenRouter</option>
          </select>

          <label v-if="formData.ai_provider === 'openrouter'">ID модели</label>
          <div v-if="formData.ai_provider === 'openrouter'">
            <input
              type="text"
              v-model="formData.ai_model"
              class="form-control"
              placeholder="anthropic/claude-sonnet-4.5"
              autocomplete="off"
              spellcheck="false"
            />
            <small class="hint">Точный ID из каталога OpenRouter в формате provider/model.</small>
          </div>
          
          <label>API-ключ</label>
          <div>
            <input
              type="password"
              v-model="formData.ai_api_key"
              class="form-control"
              :placeholder="aiKeyPlaceholder"
              autocomplete="new-password"
              spellcheck="false"
            />
            <small v-if="userStore.profile?.ai_api_key_configured" class="credential-status">Ключ сохранён</small>
          </div>
          
          <div></div>
          <button
            class="btn btn-primary btn-auto"
            :disabled="savingSection !== null"
            :aria-busy="savingSection === 'ai'"
            @click="saveProfile('ai')"
          >
            {{ savingSection === 'ai' ? 'Сохранение…' : 'Сохранить нейросеть' }}
          </button>
        </div>
      </section>

      <section class="settings-section">
        <h3>Голосовой ввод Telegram</h3>
        <p class="section-description">Whisper распознаёт речь отдельно, затем текст обрабатывает выбранная выше нейросеть.</p>
        <div class="settings-form-grid">
          <label>Распознавание</label>
          <select v-model="formData.stt_provider" class="form-control" disabled>
            <option value="groq">Groq Whisper Large V3</option>
          </select>

          <label>API-ключ Whisper</label>
          <div>
            <input
              type="password"
              v-model="formData.stt_api_key"
              class="form-control"
              :placeholder="sttKeyPlaceholder"
              autocomplete="new-password"
              spellcheck="false"
            />
            <small v-if="userStore.profile?.stt_api_key_configured" class="credential-status">Ключ распознавания сохранён</small>
            <small v-else class="hint">Можно использовать тот же Groq API-ключ, что и для текстовых запросов.</small>
          </div>

          <div></div>
          <button
            class="btn btn-primary btn-auto"
            :disabled="savingSection !== null"
            :aria-busy="savingSection === 'stt'"
            @click="saveProfile('stt')"
          >
            {{ savingSection === 'stt' ? 'Сохранение…' : 'Сохранить голосовой ввод' }}
          </button>
        </div>
      </section>

      <section class="settings-section">
        <h3>Приложение</h3>
        <div class="settings-form-grid">
          <label>Горячая клавиша</label>
          <div>
            <input type="text" v-model="formData.task_hotkey" class="form-control" placeholder="ctrl+q" />
            <small class="hint">Например: ctrl+q, alt+n. Работает независимо от раскладки.</small>
          </div>
          
          <label class="checkbox-label" style="grid-column: 1 / -1; margin-top: 1rem;">
            <input type="checkbox" v-model="formData.auto_postpone_overdue" />
            Автоматически переносить просроченные задачи на сегодня (00:00) с отключением напоминаний
          </label>
          
          <div style="grid-column: 1 / -1; display: flex; justify-content: flex-end;">
            <button
              class="btn btn-primary btn-auto"
              :disabled="savingSection !== null"
              :aria-busy="savingSection === 'app'"
              @click="saveProfile('app')"
            >
              {{ savingSection === 'app' ? 'Сохранение…' : 'Сохранить настройки' }}
            </button>
          </div>
        </div>
      </section>

      <section class="settings-section">
        <h3>Смена пароля</h3>
        <div class="settings-form-grid">
          <label>Старый пароль</label>
          <input type="password" v-model="passData.old_password" class="form-control" />
          
          <label>Новый пароль</label>
          <input type="password" v-model="passData.new_password" class="form-control" />
          
          <div></div>
          <button class="btn btn-primary btn-auto" @click="changePassword">Изменить пароль</button>
        </div>
      </section>

      <section class="settings-section">
        <h3>Telegram</h3>
        <div class="settings-form-grid">
          <label>Статус</label>
          <div v-if="userStore.profile?.telegram_id">
            <p class="text-success" style="margin-top: 0.5rem; font-weight: bold;">✓ Telegram аккаунт привязан</p>
          </div>
          <div v-else>
            
            <div v-if="!codeSent" style="display: flex; gap: 0.5rem; flex-direction: column; max-width: 320px;">
              <div style="display: flex; gap: 0.5rem;">
                <input type="text" v-model="tgUsername" class="form-control" placeholder="@username" />
                <button class="btn btn-primary btn-auto" @click="requestTelegramCode">Отправить код</button>
              </div>
              <small class="hint" style="margin-top: 0.5rem; line-height: 1.4;">
                Укажите логин. <b>Важно:</b> бот сможет отправить код, только если вы зайдете в <a href="https://t.me/jetplan_bot" target="_blank" class="tg-link">@jetplan_bot</a> и хотя бы раз нажмете <b>Запустить</b>.
              </small>
            </div>

            <div v-else style="display: flex; gap: 0.5rem; flex-direction: column; max-width: 320px;">
              <div style="display: flex; gap: 0.5rem;">
                <input
                  type="text"
                  v-model="tgCode"
                  class="form-control"
                  placeholder="Вставьте код из Telegram"
                  maxlength="128"
                  autocomplete="one-time-code"
                  spellcheck="false"
                />
                <button class="btn btn-primary btn-auto" @click="verifyTelegramCode">Подтвердить</button>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.5rem;">
                <small class="hint" style="margin: 0;">Код отправлен в бота.</small>
                <small class="hint" style="margin: 0; cursor: pointer; color: var(--color-heading); text-decoration: underline;" @click="codeSent = false">
                  Изменить логин
                </small>
              </div>
            </div>

          </div>
        </div>
      </section>

    </div>
  </div>
</template>

<style scoped>
.settings-container {
  max-width: 1000px;
  margin: 2rem auto;
  padding: 0 1rem;
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.settings-header h2 {
  color: var(--color-heading);
}

.settings-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 2.5rem;
}

.settings-section {
  padding-bottom: 2rem;
  border-bottom: 1px solid var(--color-border);
}

.settings-section:last-child {
  padding-bottom: 0;
  border-bottom: none;
}

.settings-section h3 {
  margin-bottom: 1.5rem;
  color: var(--color-heading);
  font-size: 1.2rem;
  font-weight: 600;
}

.section-description {
  max-width: 65ch;
  margin: -0.8rem 0 1.5rem;
  color: var(--color-text-light-2);
  line-height: 1.5;
}

.settings-form-grid {
  display: grid;
  grid-template-columns: 200px 1fr;
  align-items: center;
  gap: 1.2rem 2rem;
}

.settings-form-grid label {
  color: var(--color-text-light-2);
  font-weight: 500;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.95rem;
}

.form-control {
  width: 100%;
  padding: 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-background);
  color: var(--color-text);
  font-family: inherit;
}

.btn {
  padding: 0.8rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background-color: hsla(160, 100%, 37%, 1);
  color: white;
}

.btn-primary:hover {
  background-color: hsla(160, 100%, 32%, 1);
}

.btn:disabled {
  cursor: wait;
  opacity: 0.65;
}

.btn-secondary {
  background-color: var(--color-background-mute);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  padding: 0.5rem 1rem;
}

.btn-secondary:hover {
  border-color: var(--color-border-hover);
}

.btn-auto {
  width: auto;
  align-self: flex-start;
  padding: 0.6rem 1.2rem;
}

.hint {
  display: block;
  margin-top: 0.3rem;
  font-size: 0.8rem;
  color: var(--color-text-light-2);
}

.credential-status {
  display: block;
  margin-top: 0.35rem;
  color: hsla(160, 100%, 32%, 1);
  font-size: 0.8rem;
  font-weight: 600;
}

.tg-link {
  color: hsla(160, 100%, 37%, 1);
  text-decoration: none;
  font-weight: 600;
  transition: color 0.2s;
}

.tg-link:hover {
  color: hsla(160, 100%, 32%, 1);
  text-decoration: underline;
}

.alert {
  position: fixed;
  z-index: 2000;
  top: 1.25rem;
  left: 50%;
  display: flex;
  align-items: center;
  gap: 0.65rem;
  width: min(calc(100vw - 2rem), 36rem);
  padding: 0.8rem 1rem;
  transform: translateX(-50%);
  border-radius: 8px;
  box-shadow: 0 12px 30px oklch(12% 0.01 160 / 28%);
  font-weight: 600;
}

.alert-success {
  color: oklch(94% 0.015 160);
  background-color: oklch(31% 0.055 160);
  border: 1px solid oklch(56% 0.095 160);
}

.alert-error {
  color: oklch(95% 0.012 25);
  background-color: oklch(34% 0.07 25);
  border: 1px solid oklch(59% 0.12 25);
}

.alert-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 1.5rem;
  width: 1.5rem;
  height: 1.5rem;
  border: 1px solid currentColor;
  border-radius: 50%;
  font-size: 0.85rem;
  font-weight: 700;
  line-height: 1;
}

.text-success {
  color: #4caf50;
}

@media (max-width: 768px) {
  .settings-form-grid {
    grid-template-columns: 1fr;
    gap: 0.5rem 1rem;
  }
  .settings-form-grid label {
    margin-top: 1rem;
  }
  .settings-form-grid label:first-child {
    margin-top: 0;
  }
}
</style>
