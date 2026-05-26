import { ref } from 'vue'

const STORAGE_KEY = 'sidebar-collapsed'
const BREAKPOINT = 1024

function getStoredPreference() {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'true') return true
  if (stored === 'false') return false
  return false // default: expanded
}

// Singleton collapsed state — initialize based on viewport width at load time
const collapsed = ref(
  typeof window !== 'undefined' && window.innerWidth < BREAKPOINT
    ? true
    : getStoredPreference()
)

export function useSidebar() {
  // Manual toggle: update state and persist preference to localStorage
  const toggle = () => {
    collapsed.value = !collapsed.value
    localStorage.setItem(STORAGE_KEY, String(collapsed.value))
  }

  // Each Sidebar instance tracks its own handler reference
  let _resizeHandler = null

  const initResponsive = () => {
    _resizeHandler = () => {
      if (window.innerWidth < BREAKPOINT) {
        // Auto-collapse — do NOT write to localStorage (not a manual action)
        collapsed.value = true
      } else {
        // Viewport widened back: restore stored manual preference
        collapsed.value = getStoredPreference()
      }
    }
    window.addEventListener('resize', _resizeHandler)
  }

  const cleanupResponsive = () => {
    if (_resizeHandler) {
      window.removeEventListener('resize', _resizeHandler)
      _resizeHandler = null
    }
  }

  return { collapsed, toggle, initResponsive, cleanupResponsive }
}
