<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from '../composables/useI18n'
import { useSidebar } from '../composables/useSidebar'

const route = useRoute()
const { t } = useI18n()
const { collapsed, toggle, initResponsive, cleanupResponsive } = useSidebar()

onMounted(() => initResponsive())
onUnmounted(() => cleanupResponsive())

// Icon path data — 20×20 viewBox, stroke-only, currentColor
const ICON_PATHS = {
  // 2×2 grid of squares (Overview/Dashboard)
  overview: [
    'M2 2h7v7H2z',
    'M11 2h7v7h-7z',
    'M2 11h7v7H2z',
    'M11 11h7v7h-7z',
  ],
  // Hexagonal box / package (Inventory)
  inventory: [
    'M10 2l8 4.5v7L10 18l-8-4.5v-7L10 2z',
    'M2 6.5l8 4.5 8-4.5',
    'M10 11v7',
  ],
  // Rounded-rect document with list lines (Orders)
  orders: [
    'M5 3h10a1 1 0 011 1v13a1 1 0 01-1 1H5a1 1 0 01-1-1V4a1 1 0 011-1z',
    'M8 8h5',
    'M8 11h5',
    'M8 14h3',
  ],
  // Three vertical bars + baseline (Finance / bar chart)
  finance: [
    'M4 17V9',
    'M10 17V4',
    'M16 17V11',
    'M2 17h16',
  ],
  // Zigzag trend line + arrow-corner tip (Demand)
  demand: [
    'M2 16l5-6 4 3 7-9',
    'M14 4h4v4',
  ],
  // Inbox tray with down arrow (Restocking)
  restocking: [
    'M4 14h12v3H4z',
    'M10 2v9',
    'M6 8l4 5 4-5',
  ],
  // Document with folded corner + lines (Reports)
  reports: [
    'M5 2h8l4 4v12a1 1 0 01-1 1H5a1 1 0 01-1-1V3a1 1 0 011-1z',
    'M13 2v5h4',
    'M8 10h5',
    'M8 13h5',
    'M8 16h3',
  ],
}

// Nav item definitions (computed so labels react to locale changes)
const navItems = computed(() => [
  { to: '/',           icon: 'overview',    label: t('nav.overview'),        exact: true },
  { to: '/inventory',  icon: 'inventory',   label: t('nav.inventory') },
  { to: '/orders',     icon: 'orders',      label: t('nav.orders') },
  { to: '/spending',   icon: 'finance',     label: t('nav.finance') },
  { to: '/demand',     icon: 'demand',      label: t('nav.demandForecast') },
  { to: '/restocking', icon: 'restocking',  label: t('nav.restocking') },
  { to: '/reports',    icon: 'reports',     label: 'Reports' },
])

const isActive = (item) => {
  if (item.exact) return route.path === item.to
  return route.path === item.to
}

const toggleLabel = computed(() =>
  collapsed.value ? 'Expand sidebar' : 'Collapse sidebar'
)
</script>

<template>
  <aside
    class="sidebar"
    :class="{ 'sidebar--collapsed': collapsed }"
  >
    <!-- Header: logo/mark + collapse toggle -->
    <div class="sidebar-header">
      <div v-if="!collapsed" class="logo">
        <span class="logo-name">{{ t('nav.companyName') }}</span>
        <span class="logo-subtitle">{{ t('nav.subtitle') }}</span>
      </div>
      <div v-else class="logo-mark" aria-hidden="true">CC</div>

      <button
        class="toggle-btn"
        @click="toggle"
        :aria-label="toggleLabel"
        :aria-expanded="String(!collapsed)"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 18 18"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <!-- Chevron left = collapse, chevron right = expand -->
          <path v-if="!collapsed" d="M11 4L6 9L11 14" />
          <path v-else d="M7 4L12 9L7 14" />
        </svg>
      </button>
    </div>

    <!-- Navigation list -->
    <nav aria-label="Main navigation">
      <ul class="nav-list">
        <li v-for="item in navItems" :key="item.to">
          <router-link
            :to="item.to"
            class="nav-item"
            :class="{ 'nav-item--active': isActive(item) }"
            :aria-current="isActive(item) ? 'page' : undefined"
            :aria-label="collapsed ? item.label : undefined"
            :title="collapsed ? item.label : undefined"
          >
            <span class="nav-icon" aria-hidden="true">
              <svg
                width="20"
                height="20"
                viewBox="0 0 20 20"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path
                  v-for="d in ICON_PATHS[item.icon]"
                  :key="d"
                  :d="d"
                />
              </svg>
            </span>
            <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
          </router-link>
        </li>
      </ul>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  width: 240px;
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
  transition: width 0.2s ease;
  z-index: 100;
}

.sidebar--collapsed {
  width: 64px;
}

/* ── Header ─────────────────────────────────────── */
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0 1rem;
  height: 60px;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.sidebar--collapsed .sidebar-header {
  flex-direction: column;
  justify-content: center;
  gap: 0.625rem;
  padding: 0.75rem 0;
  height: auto;
  min-height: 70px;
}

.logo {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.logo-name {
  display: block;
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.logo-subtitle {
  display: block;
  font-size: 0.688rem;
  color: #64748b;
  font-weight: 400;
  margin-top: 0.125rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.logo-mark {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
  color: white;
  font-size: 0.688rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
  flex-shrink: 0;
}

.toggle-btn:hover {
  background: #f1f5f9;
  color: #0f172a;
  border-color: #cbd5e1;
}

/* ── Nav list ────────────────────────────────────── */
.nav-list {
  list-style: none;
  padding: 0.625rem 0.5rem;
  margin: 0;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.nav-list li {
  margin-bottom: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0.75rem;
  color: #64748b;
  text-decoration: none;
  font-weight: 500;
  font-size: 0.875rem;
  border-radius: 6px;
  transition: background 0.15s ease, color 0.15s ease;
  white-space: nowrap;
  overflow: hidden;
}

.nav-item:hover {
  color: #0f172a;
  background: #f1f5f9;
}

.nav-item--active {
  color: #2563eb;
  background: #eff6ff;
}

/* Collapsed: center the icon */
.sidebar--collapsed .nav-item {
  justify-content: center;
  padding: 0.625rem 0;
}

.nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.nav-label {
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
