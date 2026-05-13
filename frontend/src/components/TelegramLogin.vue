// frontend/src/components/TelegramLogin.vue
<template>
  <div ref="telegramLoginRef" class="telegram-login"></div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';

const props = defineProps<{
  botName: string;
  redirectUrl?: string;
  requestAccess?: string;
  size?: 'large' | 'medium' | 'small';
  radius?: string;
}>();

const emit = defineEmits<{
  (e: 'callback', user: any): void;
}>();

const telegramLoginRef = ref<HTMLElement | null>(null);

declare global {
  interface Window {
    onTelegramAuth: (user: any) => void;
  }
}

onMounted(() => {
  // Очищаем контейнер перед добавлением, чтобы избежать дублирования при горячей перезагрузке
  if (telegramLoginRef.value) {
    telegramLoginRef.value.innerHTML = '';
  }

  const script = document.createElement('script');
  script.src = 'https://telegram.org/js/telegram-widget.js?22';
  script.setAttribute('data-telegram-login', props.botName);
  script.setAttribute('data-size', props.size || 'large');
  
  if (props.radius) {
    script.setAttribute('data-radius', props.radius);
  }
  
  if (props.requestAccess) {
    script.setAttribute('data-request-access', props.requestAccess);
  }
  
  if (props.redirectUrl) {
    script.setAttribute('data-auth-url', props.redirectUrl);
  } else {
    // Используем callback-функцию, если не указан URL для редиректа
    window.onTelegramAuth = (user: any) => {
      emit('callback', user);
    };
    script.setAttribute('data-onauth', 'onTelegramAuth(user)');
  }
  
  script.async = true;
  telegramLoginRef.value?.appendChild(script);
});
</script>

<style scoped>
.telegram-login {
  display: flex;
  justify-content: center;
  margin: 1rem 0;
  min-height: 40px; /* Резервируем место под кнопку */
}
</style>
