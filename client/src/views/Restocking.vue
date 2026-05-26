<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <!-- Budget Slider Card -->
    <div class="card budget-card">
      <div class="card-header">
        <h3 class="card-title">{{ t('restocking.budgetLabel') }}</h3>
      </div>
      <div class="budget-controls">
        <div class="budget-display">{{ formatCurrency(budget, currentCurrency.value) }}</div>
        <input
          type="range"
          min="0"
          max="5000"
          step="100"
          v-model.number="budget"
          class="budget-slider"
        />
        <p class="budget-help-text">{{ t('restocking.budgetHelp') }}</p>
      </div>
    </div>

    <!-- Success Banner -->
    <div v-if="successMessage" class="success-banner">
      <span>{{ successMessage }}</span>
      <router-link to="/orders" class="view-orders-link">{{ t('restocking.viewInOrders') }}</router-link>
    </div>

    <!-- Error Banner -->
    <div v-if="errorMessage" class="error">{{ errorMessage }}</div>

    <!-- Summary Stats -->
    <div class="stats-grid">
      <div class="stat-card info">
        <div class="stat-label">{{ t('restocking.itemsSelected') }}</div>
        <div class="stat-value">{{ itemsSelected }}</div>
      </div>
      <div class="stat-card warning">
        <div class="stat-label">{{ t('restocking.totalCost') }}</div>
        <div class="stat-value stat-value-currency">{{ formatCurrency(totalCost, currentCurrency.value) }}</div>
      </div>
      <div class="stat-card success">
        <div class="stat-label">{{ t('restocking.budgetRemaining') }}</div>
        <div class="stat-value stat-value-currency">{{ formatCurrency(budgetRemaining, currentCurrency.value) }}</div>
      </div>
    </div>

    <!-- Recommendations Card -->
    <div class="card">
      <div class="card-header">
        <div class="card-header-left">
          <h3 class="card-title">{{ t('restocking.recommendedTitle') }} ({{ recommendations.length }})</h3>
          <p class="card-sub-help">{{ t('restocking.recommendedHelp') }}</p>
        </div>
        <button
          class="place-order-btn"
          :disabled="recommendations.length === 0 || submitting"
          @click="placeOrder"
        >
          {{ submitting ? t('restocking.placingOrder') : t('restocking.placeOrder') }}
        </button>
      </div>

      <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
      <div v-else-if="loadError" class="error">{{ loadError }}</div>
      <div v-else-if="recommendations.length === 0" class="empty-state-row">
        {{ t('restocking.noRecommendations') }}
      </div>
      <div v-else class="table-container">
        <table>
          <thead>
            <tr>
              <th>{{ t('restocking.table.sku') }}</th>
              <th>{{ t('restocking.table.itemName') }}</th>
              <th>{{ t('restocking.table.currentDemand') }}</th>
              <th>{{ t('restocking.table.forecastedDemand') }}</th>
              <th>{{ t('restocking.table.shortfall') }}</th>
              <th>{{ t('restocking.table.orderQty') }}</th>
              <th>{{ t('restocking.table.unitCost') }}</th>
              <th>{{ t('restocking.table.lineTotal') }}</th>
              <th>{{ t('restocking.table.trend') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in recommendations" :key="item.item_sku">
              <td><strong>{{ item.item_sku }}</strong></td>
              <td>{{ item.item_name }}</td>
              <td>{{ item.current_demand }}</td>
              <td><strong>{{ item.forecasted_demand }}</strong></td>
              <td>{{ item.shortfall }}</td>
              <td>{{ item.quantity }}</td>
              <td>{{ formatCurrency(item.unit_cost, currentCurrency.value) }}</td>
              <td><strong>{{ formatCurrency(item.line_total, currentCurrency.value) }}</strong></td>
              <td>
                <span :class="['badge', item.trend]">{{ t('trends.' + item.trend) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrency } from '../utils/currency'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency } = useI18n()

    const forecasts = ref([])
    const budget = ref(2500)
    const loading = ref(true)
    const loadError = ref(null)
    const submitting = ref(false)
    const successMessage = ref('')
    const errorMessage = ref('')
    const lastOrderNumber = ref('')

    const loadForecasts = async () => {
      loading.value = true
      loadError.value = null
      try {
        forecasts.value = await api.getDemandForecasts()
      } catch (err) {
        loadError.value = 'Failed to load demand forecasts'
        console.error(err)
      } finally {
        loading.value = false
      }
    }

    const recommendations = computed(() => {
      const candidates = forecasts.value
        .map(f => {
          const shortfall = f.forecasted_demand - f.current_demand
          const unitCost = f.unit_cost || 0
          return {
            ...f,
            shortfall,
            quantity: shortfall,
            unit_cost: unitCost,
            line_total: Math.round(shortfall * unitCost * 100) / 100
          }
        })
        .filter(c => c.shortfall > 0)
        .sort((a, b) => (b.shortfall - a.shortfall) || (b.line_total - a.line_total))

      const result = []
      let remaining = budget.value
      for (const c of candidates) {
        if (c.line_total <= remaining) {
          result.push(c)
          remaining = Math.round((remaining - c.line_total) * 100) / 100
        }
      }
      return result
    })

    const itemsSelected = computed(() => recommendations.value.length)

    const totalCost = computed(() =>
      Math.round(recommendations.value.reduce((sum, r) => sum + r.line_total, 0) * 100) / 100
    )

    const budgetRemaining = computed(() =>
      Math.round((budget.value - totalCost.value) * 100) / 100
    )

    const placeOrder = async () => {
      submitting.value = true
      errorMessage.value = ''
      successMessage.value = ''
      try {
        const payload = {
          budget: budget.value,
          items: recommendations.value.map(r => ({
            item_sku: r.item_sku,
            item_name: r.item_name,
            quantity: r.quantity,
            unit_cost: r.unit_cost,
            line_total: r.line_total
          }))
        }
        const order = await api.createRestockingOrder(payload)
        lastOrderNumber.value = order.order_number
        successMessage.value = t('restocking.orderPlaced', { orderNumber: order.order_number })
      } catch (e) {
        errorMessage.value = t('restocking.orderError')
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadForecasts)

    return {
      t,
      currentCurrency,
      formatCurrency,
      forecasts,
      budget,
      loading,
      loadError,
      submitting,
      successMessage,
      errorMessage,
      lastOrderNumber,
      recommendations,
      itemsSelected,
      totalCost,
      budgetRemaining,
      placeOrder
    }
  }
}
</script>

<style scoped>
.restocking {
  /* uses global page layout */
}

/* Budget Card */
.budget-card {
  margin-bottom: 1.25rem;
}

.budget-controls {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.5rem 0;
}

.budget-display {
  font-size: 2.5rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.budget-slider {
  width: 100%;
  max-width: 600px;
  height: 6px;
  border-radius: 3px;
  appearance: none;
  -webkit-appearance: none;
  background: #e2e8f0;
  outline: none;
  cursor: pointer;
  accent-color: #2563eb;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2563eb;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(37, 99, 235, 0.4);
  transition: background 0.2s;
}

.budget-slider::-webkit-slider-thumb:hover {
  background: #1d4ed8;
}

.budget-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2563eb;
  cursor: pointer;
  border: none;
  box-shadow: 0 1px 3px rgba(37, 99, 235, 0.4);
}

.budget-help-text {
  font-size: 0.813rem;
  color: #64748b;
}

/* Success Banner */
.success-banner {
  background: #d1fae5;
  border: 1px solid #6ee7b7;
  color: #065f46;
  padding: 1rem 1.25rem;
  border-radius: 8px;
  margin-bottom: 1.25rem;
  font-size: 0.938rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.view-orders-link {
  display: inline-block;
  padding: 0.375rem 0.875rem;
  background: #059669;
  color: white;
  border-radius: 6px;
  text-decoration: none;
  font-size: 0.813rem;
  font-weight: 600;
  transition: background 0.2s;
  white-space: nowrap;
}

.view-orders-link:hover {
  background: #047857;
}

/* Stats */
.stat-value-currency {
  font-size: 1.75rem;
}

/* Card header with button */
.card-header-left {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.card-sub-help {
  font-size: 0.813rem;
  color: #64748b;
  margin-top: 0.25rem;
}

/* Place Order Button */
.place-order-btn {
  padding: 0.625rem 1.5rem;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, opacity 0.2s;
  white-space: nowrap;
  flex-shrink: 0;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.place-order-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
  opacity: 0.7;
}

/* Empty State */
.empty-state-row {
  padding: 2rem 1rem;
  text-align: center;
  color: #64748b;
  font-size: 0.938rem;
}
</style>
