<!-- frontend/src/components/WorkspaceHeader.vue -->
<!-- Отображает общую навигацию авторизованного рабочего пространства JetPlan. -->
<script setup lang="ts">
const logout = () => {
  localStorage.removeItem('access_token')
  window.location.assign('/')
}
</script>

<template>
  <header class="workspace-header">
    <RouterLink class="workspace-brand" to="/">JetPlan Workspace</RouterLink>

    <nav class="workspace-nav" aria-label="Разделы рабочего пространства">
      <RouterLink class="workspace-nav-link" to="/">Задачи</RouterLink>
      <RouterLink class="workspace-nav-link" to="/kanban">Канбан</RouterLink>
      <RouterLink class="workspace-nav-link" to="/settings">Настройки</RouterLink>
      <button class="workspace-nav-link workspace-logout" type="button" @click="logout">Выйти</button>
    </nav>
  </header>
</template>

<style scoped>
.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  width: 100%;
  margin-bottom: 2rem;
  padding: 0 1rem;
}

.workspace-brand {
  flex: 0 0 auto;
  padding: 0;
  color: var(--color-heading);
  font-size: 1.2rem;
  font-weight: 800;
}

.workspace-brand:hover {
  background: transparent;
}

.workspace-nav {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.45rem;
}

.workspace-nav-link {
  min-height: 2.5rem;
  padding: 0.5rem 0.85rem;
  color: var(--color-text);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  font: inherit;
  font-size: 0.9rem;
  font-weight: 600;
  line-height: 1.4rem;
  cursor: pointer;
  transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.workspace-nav-link:hover {
  color: var(--color-heading);
  background: var(--color-background-mute);
  border-color: var(--color-border);
}

.workspace-nav-link:focus-visible {
  outline: 2px solid hsla(160, 100%, 37%, 0.8);
  outline-offset: 2px;
}

.workspace-nav-link.router-link-exact-active {
  color: hsla(160, 100%, 32%, 1);
  background: hsla(160, 100%, 37%, 0.1);
  border-color: hsla(160, 100%, 37%, 0.24);
}

.workspace-logout {
  border-color: var(--color-border);
}

@media (max-width: 720px) {
  .workspace-header {
    align-items: flex-start;
    flex-direction: column;
    margin-bottom: 1.25rem;
    padding: 0;
  }

  .workspace-nav {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    width: 100%;
  }

  .workspace-nav-link {
    width: 100%;
    min-height: 2.75rem;
    text-align: center;
  }
}
</style>
