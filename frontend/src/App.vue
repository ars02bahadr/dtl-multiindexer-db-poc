<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const API_URL = 'http://localhost:3000'

const users = ref([])
const selectedFrom = ref('')
const selectedTo = ref('')
const amount = ref(500)
const status = ref('')
const lastTx = ref(null)

async function loadUsers() {
  try {
    const res = await axios.get(`${API_URL}/users`)
    users.value = res.data
    if (users.value.length >= 2) {
      selectedFrom.value = users.value[0].address
      selectedTo.value = users.value[1].address
    }
  } catch (e) {
    status.value = 'Error loading users: ' + e.message
  }
}

async function seedUsers() {
  status.value = 'Seeding users...'
  try {
    await axios.post(`${API_URL}/seed`)
    await loadUsers()
    status.value = 'Users seeded! Alice and Bob each have 1200 DTL'
  } catch (e) {
    status.value = 'Seed error: ' + e.message
  }
}

async function sendTransfer() {
  if (!selectedFrom.value || !selectedTo.value || !amount.value) {
    status.value = 'Please fill all fields'
    return
  }
  status.value = 'Sending transfer...'
  try {
    const res = await axios.post(`${API_URL}/transfer`, {
      from: selectedFrom.value,
      to: selectedTo.value,
      amount: Number(amount.value)
    })
    lastTx.value = res.data
    status.value = `Transfer completed! IPFS CID: ${res.data.ipfs_cid || 'N/A'}`
    await loadUsers()
  } catch (e) {
    status.value = 'Transfer error: ' + (e.response?.data?.error || e.message)
  }
}

onMounted(loadUsers)
</script>

<template>
  <main>
    <div class="container">
      <h1>🇹🇷 Digital Turkish Lira (DTL) PoC</h1>

      <div class="actions">
        <button @click="seedUsers" class="seed-btn">🌱 Seed Demo Users</button>
        <button @click="loadUsers" class="refresh-btn">🔄 Refresh</button>
      </div>

      <div v-if="users.length" class="users-table">
        <h2>Users</h2>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Address</th>
              <th>Balance</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td>{{ user.name }}</td>
              <td class="address">{{ user.address }}</td>
              <td class="balance">{{ user.balance }} DTL</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="transfer-box">
        <h2>Transfer Funds</h2>
        <div class="form-row">
          <label>From:</label>
          <select v-model="selectedFrom">
            <option v-for="user in users" :key="user.id" :value="user.address">
              {{ user.name }} ({{ user.balance }} DTL)
            </option>
          </select>
        </div>
        <div class="form-row">
          <label>To:</label>
          <select v-model="selectedTo">
            <option v-for="user in users" :key="user.id" :value="user.address">
              {{ user.name }}
            </option>
          </select>
        </div>
        <div class="form-row">
          <label>Amount:</label>
          <input v-model="amount" type="number" placeholder="Amount" />
        </div>
        <button @click="sendTransfer" class="send-btn">💸 Send Transfer</button>
      </div>

      <div v-if="lastTx" class="last-tx">
        <h3>Last Transaction</h3>
        <p><strong>ID:</strong> {{ lastTx.tx_id }}</p>
        <p><strong>Status:</strong> {{ lastTx.status }}</p>
        <p v-if="lastTx.ipfs_cid"><strong>IPFS CID:</strong> {{ lastTx.ipfs_cid }}</p>
      </div>

      <p class="status">{{ status }}</p>
    </div>
  </main>
</template>

<style scoped>
.container {
  max-width: 700px;
  margin: 30px auto;
  padding: 25px;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  color: #e8e8e8;
}

h1 {
  text-align: center;
  margin-bottom: 20px;
  color: #00d9ff;
}

h2 {
  color: #00d9ff;
  border-bottom: 1px solid #00d9ff33;
  padding-bottom: 8px;
}

.actions {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

button {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: bold;
  transition: all 0.2s;
}

.seed-btn {
  background: #4caf50;
  color: white;
}

.refresh-btn {
  background: #2196f3;
  color: white;
}

.send-btn {
  background: #ff9800;
  color: white;
  width: 100%;
  margin-top: 10px;
}

button:hover {
  transform: translateY(-2px);
  opacity: 0.9;
}

.users-table table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
}

.users-table th,
.users-table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #333;
}

.users-table th {
  color: #00d9ff;
}

.address {
  font-family: monospace;
  font-size: 12px;
}

.balance {
  color: #4caf50;
  font-weight: bold;
}

.transfer-box {
  margin-top: 25px;
  padding: 20px;
  background: #0d1b2a;
  border-radius: 12px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.form-row label {
  width: 60px;
}

.form-row select,
.form-row input {
  flex: 1;
  padding: 10px;
  border-radius: 6px;
  border: 1px solid #333;
  background: #1a1a2e;
  color: white;
}

.last-tx {
  margin-top: 20px;
  padding: 15px;
  background: #0f3460;
  border-radius: 8px;
}

.last-tx h3 {
  color: #00d9ff;
  margin-bottom: 10px;
}

.status {
  margin-top: 20px;
  padding: 10px;
  background: #333;
  border-radius: 6px;
  text-align: center;
}
</style>
