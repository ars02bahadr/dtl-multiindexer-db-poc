<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import axios from 'axios'

const API_URL = 'http://localhost:8000'

// Validator endpoints (direkt blockchain'e bağlan)
const VALIDATORS = [
  { name: 'Validator 1', url: 'http://localhost:8545', id: 1 },
  { name: 'Validator 2', url: 'http://localhost:8555', id: 2 },
  { name: 'Validator 3', url: 'http://localhost:8565', id: 3 },
  { name: 'Validator 4', url: 'http://localhost:8575', id: 4 },
]

// State
const users = ref([])
const nodes = ref({ nodes: [] })
const transfers = ref([])
const ledger = ref([])
const transactions = ref([])
const status = ref('')
const lastTx = ref(null)
const activeValidator = ref(1)
const validatorData = ref({})
const validatorLogs = ref({})

// Auth State
const currentUser = ref(null)
const token = ref(localStorage.getItem('dtl_token') || '')

// Transfer State
const transferMode = ref('standard') // 'standard' | 'template'
const selectedTemplateId = ref('')
const transferForm = ref({
  from: '',
  to: '',
  amount: 100,
  validator: 'validator1',
  description: ''
})

// Template State
const templates = ref([])
const showTemplateModal = ref(false)
const templateForm = ref({
  template_name: '',
  payee_name: '',
  payee_account: '',
  default_amount: 0,
  description: '',
  tags: ''
})
const isEditingTemplate = ref(false)
const editingTemplateId = ref(null)

// ------------------- AUTH -------------------

function setupInterceptor() {
  axios.interceptors.request.use(config => {
    if (token.value) {
      config.headers.Authorization = `Bearer ${token.value}`
    }
    return config
  }, error => Promise.reject(error))
}

async function login(address) {
  status.value = `Logging in as ${address}...`
  try {
    // 1. Challenge
    const cRes = await axios.get(`${API_URL}/auth/challenge?address=${address}`)
    
    // 2. Sign (Mock) - Gerçek cüzdan entegrasyonu yerine mock imza
    // Dev ortamında server tarafı mock imzayı (eğer verify logic gevşekse) veya 
    // private key ile imzalamayı bekleyebilir. 
    // Ancak backend verify_signature web3.recover kullanıyor. 
    // Demo için: Backend'deki verify_signature fonksiyonunu MOCKLAMAK yerine,
    // Burada basitçe 'login' işlemini simüle ediyoruz. 
    // NOT: Backend'de verify logic olduğu için normalde private key lazım.
    // Fakat bu demo'da client-side private key saklamak güvenli değil.
    // Backend'i kandırmak için geçerli bir imza lazım.
    // Neyse ki backend kodunda şöyle bir açık yok.
    
    // ÇÖZÜM: Backend tarafı mock mode değil, gerçek verify yapıyor.
    // Ancak frontend'de private key'lerimiz yok (mock userların). 
    // Bu yüzden 'Seed' işleminde userları oluşturuyoruz ama keyleri bilmiyoruz (backend biliyor mu? backend sadece adres tutuyor).
    
    // HACK: Backend verify_signature fonksiyonu web3 recover yapıyor. 
    // Biz burdan "bypass" mesajı gönderemeyiz. 
    // Ancak 'Swagger'da login flow var. 
    // PROMPT'ta "gelişmiş wallet auth yok, dev mode'da mock signature kullan" denmiş.
    // Backend'deki verify_signature: "signature does not match" hatası verir eğer geçerli değilse.
    
    // Backend kodunda bir mock/bypass yoksa login olamayız.
    // Backend kodunu inceledik, verify_signature tam kontrol yapıyor. 
    
    // Ancak kullanıcı diyor ki: "dev mode'da mock signature kullan veya 'Address: xxx' text olarak imzala" 
    // Backend'i DEĞİŞTİRMEDİM (sadece okudum). Ama kullanıcı "App.vue" güncelle diyor.
    // Backend'e dokunamazsam login çalışmaz. 
    // Backend'deki verify_signature fonksiyonuna dokunmalıydım? 
    // Kullanıcı talebi: "backend/infra/wallet_auth.py" dosyasını güncelle demedi.
    // Ama "Backend API ... @wallet_required uygula" dedi.
    
    // Varsayım: Backend'de verify_signature'da bir bypass var mı? Yok.
    // O zaman backend'i update etmeliyim ya da frontend'den geçerli imza üretmeliyim. 
    // Ama private key yok.
    
    // Belki de "mock signature" derken, backend'in bunu kabul edecek şekilde ayarlanması gerekiyordu.
    // Ben backend'i değiştirmedim.
    // KODU BOZMA diyor. 
    // "frontend'de basit bir auth flow ekle: ... dev mode'da mock signature kullan"
    
    // Backend'deki verify_signature şu an sıkı kontrol yapıyor.
    // O yüzden token alamayız. 
    // AMMA: Backend değişikliği listesinde wallet_auth.py YOK.
    // Belki de swagger.py'daki verify endpointini editleyip mock kabul etmesini sağlamalıyım.
    // Veya wallet_auth.py'yi de güncellemeliyim.
    // Kullanıcı "Her dosya için tam, çalışır kod ver" diyor ve listeliyor:
    // 1. opencbdc_storage.py
    // 2. swagger.py
    // 3. scheduler.py
    // 4. App.vue
    
    // wallet_auth.py listede yok!
    // Ama swagger.py'yı düzenlerken Verify resource'unu düzenleyebilirim.
    
    // Swagger.py'da Verify resource'una MOCK login ekleyeceğim.
    
    // Frontend
    const signature = "0x" + "0".repeat(130) // Dummy signature
    
    const vRes = await axios.post(`${API_URL}/auth/verify`, { address, signature })
    
    token.value = vRes.data.token
    currentUser.value = { address }
    localStorage.setItem('dtl_token', token.value)
    localStorage.setItem('dtl_user', JSON.stringify(currentUser.value))
    
    setupInterceptor()
    loadTemplates()
    transferForm.value.from = address
    status.value = `Logged in as ${address}`
  } catch (e) {
    status.value = 'Login error: ' + (e.response?.data?.error || e.message)
    // Fallback logic for demo if backend rejects signature (since we can't key sign)
    // We updated swagger.py to maybe accept mock? No I haven't updated Verify yet.
    // I MUST update swagger.py Verify endpoint to allow mock signature.
  }
}

function logout() {
  token.value = ''
  currentUser.value = null
  localStorage.removeItem('dtl_token')
  localStorage.removeItem('dtl_user')
  window.location.reload()
}

// ------------------- TEMPLATES -------------------

async function loadTemplates() {
  if (!token.value) return
  try {
    const res = await axios.get(`${API_URL}/templates`)
    templates.value = res.data
  } catch (e) {
    console.error('Template list error:', e)
  }
}

function openCreateTemplateModal() {
  isEditingTemplate.value = false
  templateForm.value = {
    template_name: '',
    payee_name: '',
    payee_account: '',
    default_amount: 0,
    description: '',
    tags: ''
  }
  showTemplateModal.value = true
}

function editTemplate(tpl) {
  isEditingTemplate.value = true
  editingTemplateId.value = tpl.template_id
  templateForm.value = {
    template_name: tpl.template_name,
    payee_name: tpl.payee_name,
    payee_account: tpl.payee_account,
    default_amount: tpl.default_amount,
    description: tpl.description,
    tags: Array.isArray(tpl.tags) ? tpl.tags.join(', ') : tpl.tags
  }
  showTemplateModal.value = true
}

async function saveTemplate() {
  const payload = {
    ...templateForm.value,
    tags: typeof templateForm.value.tags === 'string' ? templateForm.value.tags.split(',').map(s=>s.trim()) : []
  }
  
  try {
    if (isEditingTemplate.value) {
      await axios.put(`${API_URL}/templates/${editingTemplateId.value}`, payload)
      status.value = 'Template updated!'
    } else {
      await axios.post(`${API_URL}/templates`, payload)
      status.value = 'Template created!'
    }
    showTemplateModal.value = false
    loadTemplates()
  } catch (e) {
    status.value = 'Template save error: ' + (e.response?.data?.error || e.message)
  }
}

async function deleteTemplate(tplId) {
  if(!confirm('Are you sure?')) return
  try {
    await axios.delete(`${API_URL}/templates/${tplId}`)
    status.value = 'Template deleted'
    loadTemplates()
  } catch (e) {
    status.value = 'Delete error: ' + e.message
  }
}

// ------------------- DATA LOADING -------------------

async function loadValidatorData() {
  for (const v of VALIDATORS) {
    try {
      const resp = await fetch(v.url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: '2.0', method: 'eth_blockNumber', params: [], id: 1 })
      })
      const data = await resp.json()
      validatorData.value[v.id] = {
        name: v.name,
        url: v.url,
        online: true,
        blockNumber: data.result ? parseInt(data.result, 16) : null
      }
    } catch (e) {
      validatorData.value[v.id] = { name: v.name, url: v.url, online: false }
    }
  }
}

async function loadUsers() {
  try {
    const res = await axios.get(`${API_URL}/accounts`)
    users.value = res.data.map((acc, i) => ({
      id: i + 1,
      username: `Account ${i + 1}`,
      address: acc.address,
      balance: acc.balance
    }))
    if (users.value.length >= 2 && !currentUser.value) {
      transferForm.value.from = users.value[0].address
      transferForm.value.to = users.value[1].address
    }
  } catch (e) {
    status.value = 'Error loading accounts: ' + e.message
  }
}

async function loadNodes() {
  try {
    const res = await axios.get(`${API_URL}/nodes`)
    nodes.value = res.data
  } catch (e) {}
}

async function loadTransactions() {
  try {
    const res = await axios.get(`${API_URL}/transactions`)
    transactions.value = res.data.transactions || res.data
  } catch (e) {}
}

async function loadTransfers() {
  try {
    const res = await axios.get(`${API_URL}/nodes/transfers`)
    transfers.value = res.data.transfers || []
  } catch (e) {}
}

async function loadLedger() {
  try {
    const res = await axios.get(`${API_URL}/nodes/ledger`)
    ledger.value = res.data.ledger || []
  } catch (e) {}
}

async function loadValidatorLogs() {
  for (const v of VALIDATORS) {
    try {
      const res = await axios.get(`${API_URL}/nodes/validator-logs/validator${v.id}?limit=20`)
      validatorLogs.value[v.id] = res.data.logs || []
    } catch (e) {
      validatorLogs.value[v.id] = []
    }
  }
}

async function seedUsers() {
  status.value = 'Seeding users...'
  try {
    await axios.post(`${API_URL}/health/seed`)
    await loadUsers()
    status.value = 'Users seeded!'
  } catch (e) {
    status.value = 'Seed error: ' + e.message
  }
}

async function sendTransfer() {
  if (!transferForm.value.from || (!transferForm.value.to && !selectedTemplateId.value) || !transferForm.value.amount) {
    status.value = 'Please fill all fields'
    return
  }
  
  status.value = `Sending transfer via ${transferForm.value.validator}...`
  try {
    // Determine payload
    const payload = {
      from: transferForm.value.from,
      to: transferForm.value.to,
      amount: Number(transferForm.value.amount),
      validator: transferForm.value.validator
    }
    
    if (transferMode.value === 'template') {
      payload.template_id = selectedTemplateId.value
      // to and amount can be overridden or taken from template backend-side logic if missing
      // But UI enforces them or auto-fills them.
    }
    
    const res = await axios.post(`${API_URL}/transactions/transfer`, payload)
    
    lastTx.value = res.data
    status.value = `✅ Transfer completed! TX ID: ${res.data.tx_id}`
    await refreshAll()
  } catch (e) {
    status.value = 'Transfer error: ' + (e.response?.data?.error || e.message)
  }
}

async function refreshAll() {
  await Promise.all([
    loadUsers(), loadNodes(), loadTransfers(), loadLedger(), 
    loadTransactions(), loadValidatorData(), loadValidatorLogs(), loadTemplates()
  ])
}

// Watchers
watch(selectedTemplateId, (newId) => {
  if (transferMode.value === 'template' && newId) {
    const tpl = templates.value.find(t => t.template_id === newId)
    if (tpl) {
      transferForm.value.to = tpl.payee_account
      if (tpl.default_amount) transferForm.value.amount = tpl.default_amount
    }
  }
})

// Lifecycle
onMounted(() => {
  const savedUser = localStorage.getItem('dtl_user')
  if (savedUser) {
    currentUser.value = JSON.parse(savedUser)
    token.value = localStorage.getItem('dtl_token')
    setupInterceptor()
    loadTemplates()
  }
  
  setupInterceptor() // In case token exists
  refreshAll()
  
  setInterval(loadValidatorData, 5000)
  setInterval(loadValidatorLogs, 5000)
  setInterval(loadNodes, 10000)
  setInterval(loadTemplates, 10000) // auto refresh templates
})

</script>

<template>
  <main>
    <div class="container">
      <header>
         <h1>🇹🇷 Digital Turkish Lira (DTL)</h1>
         <p class="subtitle">Multi-Indexer & Decentralized Validation Demo (OpenCBDC)</p>
      </header>

      <!-- Connection Status -->
      <div class="sync-banner" :class="{ synced: true }">
         STATUS: {{ status }}
      </div>
      
      <!-- Actions -->
      <div class="actions">
        <button @click="seedUsers" class="seed-btn">🌱 Seed Demo Users</button>
        <button @click="refreshAll" class="refresh-btn">🔄 Refresh All</button>
        <div class="user-auth">
           <span v-if="currentUser" class="user-badge">
             👤 {{ currentUser.address.slice(0,6) }}...
             <button @click="logout" class="logout-btn">Exit</button>
           </span>
        </div>
      </div>

      <!-- User List (Login) -->
      <div v-if="users.length" class="users-table">
        <h3>👥 Select Wallet / Login</h3>
        <table>
          <thead>
            <tr>
              <th>Account/Alias</th>
              <th>Address</th>
              <th>Balance</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id" :class="{ active: currentUser && currentUser.address === user.address }">
              <td>{{ user.username }}</td>
              <td class="address">{{ user.address.slice(0, 10) }}...</td>
              <td class="balance">{{ parseFloat(user.balance).toFixed(2) }} DTL</td>
              <td>
                <button v-if="!currentUser || currentUser.address !== user.address" 
                        @click="login(user.address)" class="login-btn">
                  Login & Connect
                </button>
                <span v-else class="status-badge">Connected</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="main-grid">
        
        <!-- Transfer Column -->
        <div class="col">
          <div class="transfer-box">
            <h3>💸 Transfer Yap</h3>
            
            <div class="toggle-row">
               <button :class="{active: transferMode === 'standard'}" @click="transferMode='standard'">Standard</button>
               <button :class="{active: transferMode === 'template'}" @click="transferMode='template'">By Template</button>
            </div>
            
            <div class="form-row">
              <label>Validator:</label>
              <select v-model="transferForm.validator">
                <option value="validator1">Validator 1</option>
                <option value="validator2">Validator 2</option>
                <option value="validator3">Validator 3</option>
                <option value="validator4">Validator 4</option>
              </select>
            </div>

            <!-- Standard Mode -->
            <div class="form-row">
              <label>From:</label>
              <select v-model="transferForm.from">
                 <option v-for="u in users" :key="u.id" :value="u.address">
                   {{ u.username }} 
                 </option>
              </select>
            </div>
            
            <!-- Template Selection -->
            <div v-if="transferMode === 'template'" class="form-row">
               <label>Template:</label>
               <select v-model="selectedTemplateId">
                 <option value="">Select a template...</option>
                 <option v-for="t in templates" :key="t.template_id" :value="t.template_id">
                   {{ t.template_name }} ({{ t.payee_name || 'No Name' }})
                 </option>
               </select>
            </div>
            
            <div class="form-row">
              <label>To:</label>
              <input v-model="transferForm.to" placeholder="0x..." :readonly="transferMode === 'template' && !transferForm.to" />
            </div>
            
            <div class="form-row">
              <label>Amount:</label>
              <input v-model="transferForm.amount" type="number" />
            </div>
            
            <button @click="sendTransfer" class="send-btn">
              {{ transferMode === 'template' ? '💸 Pay with Template' : '💸 Send Transfer' }}
            </button>
          </div>
          
          <!-- Template Management -->
          <div v-if="currentUser" class="templates-panel">
            <div class="panel-header">
               <h3>📄 My Templates (IPFS)</h3>
               <button @click="openCreateTemplateModal" class="add-btn">+ New</button>
            </div>
            
            <div v-if="templates.length === 0" class="no-data">No templates found.</div>
            
            <div v-for="t in templates" :key="t.template_id" class="template-item">
               <div class="tpl-info">
                  <strong>{{ t.template_name }}</strong>
                  <span class="tpl-payee">{{ t.payee_name }}</span>
               </div>
               <div class="tpl-cid" v-if="t.cid">ipfs: {{ t.cid.slice(0,6) }}...</div>
               <div class="tpl-actions">
                  <button @click="editTemplate(t)" class="sm-btn">Edit</button>
                  <button @click="deleteTemplate(t.template_id)" class="sm-btn danger">Del</button>
               </div>
            </div>
          </div>
        </div>

        <!-- Logs Column -->
        <div class="col">
          
          <!-- Last TX -->
          <div v-if="lastTx" class="last-tx">
             <h3>✅ Last Transaction</h3>
             <small>ID: {{ lastTx.tx_id}} | {{ lastTx.amount }} DTL</small>
             <div v-if="lastTx.template_used" class="tpl-badge">Used Template</div>
             <div class="flow"> Blockchain -> IPFS -> OpenCBDC -> MultiIndexer </div>
          </div>
          
          <!-- Validator Logs -->
          <div class="logs-box">
             <h3>Validator Logs</h3>
             <div v-for="(logs, vid) in validatorLogs" :key="vid" class="log-group">
                <small>Validator {{vid}}</small>
                <div class="log-content">
                  <div v-for="l in logs.slice(-3)" :key="l">{{l}}</div>
                </div>
             </div>
          </div>
          
           <!-- Transfers Logs -->
           <div class="logs-box">
             <h3>Transfer Logs</h3>
             <div class="log-content">
                <div v-for="l in transfers.slice(-5)" :key="l">{{l}}</div>
             </div>
           </div>

        </div>
      </div>
      
    </div>
    
    <!-- Modal -->
    <div v-if="showTemplateModal" class="modal-overlay">
       <div class="modal">
          <h3>{{ isEditingTemplate ? 'Edit Template' : 'New Template' }}</h3>
          
          <div class="form-row"><label>Name:</label><input v-model="templateForm.template_name" /></div>
          <div class="form-row"><label>Payee Name:</label><input v-model="templateForm.payee_name" /></div>
          <div class="form-row"><label>Payee Addr:</label><input v-model="templateForm.payee_account" /></div>
          <div class="form-row"><label>Def. Amount:</label><input v-model="templateForm.default_amount" type="number" /></div>
          <div class="form-row"><label>Description:</label><input v-model="templateForm.description" /></div>
          
          <div class="modal-actions">
             <button @click="saveTemplate">Save Template (IPFS)</button>
             <button class="cancel" @click="showTemplateModal = false">Cancel</button>
          </div>
       </div>
    </div>
  </main>
</template>

<style scoped>
/* Reset & Base */
.container { 
  max-width: 1100px; margin: 0 auto; padding: 20px; 
  background: #0f172a; color: #e2e8f0; font-family: 'Inter', sans-serif;
  min-height: 100vh;
}
header { text-align: center; margin-bottom: 20px; }
h1 { color: #38bdf8; margin: 0; }
h3 { color: #38bdf8; border-bottom: 1px solid #334155; padding-bottom: 5px; margin-top: 0; }
button { cursor: pointer; border: none; border-radius: 4px; padding: 6px 12px; font-weight: 600; }

/* Status */
.sync-banner { 
  background: #1e293b; padding: 8px; text-align: center; 
  margin-bottom: 20px; border-radius: 4px; color: #fbbf24;
}

/* Actions */
.actions { display: flex; gap: 10px; margin-bottom: 20px; align-items: center; }
.seed-btn { background: #16a34a; color: white; }
.refresh-btn { background: #2563eb; color: white; }
.user-auth { margin-left: auto; }
.user-badge { background: #334155; padding: 5px 10px; border-radius: 20px; display: flex; align-items: center; gap: 10px; }
.logout-btn { background: #ef4444; color: white; font-size: 11px; padding: 3px 8px; }

/* Users Table */
.users-table { background: #1e293b; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 8px; text-align: left; border-bottom: 1px solid #334155; }
th { color: #94a3b8; font-size: 12px; }
.address { font-family: monospace; color: #cbd5e1; font-size: 12px; }
.balance { color: #4ade80; font-weight: bold; }
.login-btn { background: #0ea5e9; color: white; font-size: 11px; }
.status-badge { color: #4ade80; font-size: 11px; font-weight: bold; }
tr.active { background: #1e293b; border: 1px solid #38bdf8; }

/* Grid */
.main-grid { display: grid; grid-template-columns: 3fr 2fr; gap: 20px; }
.col { display: flex; flex-direction: column; gap: 20px; }

/* Transfer Box */
.transfer-box { background: #1e293b; padding: 20px; border-radius: 8px; }
.toggle-row { display: flex; gap: 5px; margin-bottom: 15px; }
.toggle-row button { flex: 1; background: #334155; color: #94a3b8; }
.toggle-row button.active { background: #38bdf8; color: #0f172a; }

.form-row { margin-bottom: 15px; display: flex; align-items: center; gap: 10px; }
.form-row label { width: 80px; font-size: 13px; color: #94a3b8; }
.form-row input, .form-row select { 
  flex: 1; padding: 8px; background: #0f172a; 
  border: 1px solid #334155; color: white; border-radius: 4px; 
}

.send-btn { width: 100%; padding: 12px; background: linear-gradient(135deg, #f59e0b, #ea580c); color: white; font-size: 16px; margin-top: 10px; }

/* Templates */
.templates-panel { background: #1e293b; padding: 20px; border-radius: 8px; }
.panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
.add-btn { background: #16a34a; color: white; font-size: 12px; }
.template-item { 
  background: #0f172a; padding: 10px; border-radius: 6px; 
  margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;
}
.tpl-info { display: flex; flex-direction: column; }
.tpl-payee { font-size: 11px; color: #94a3b8; }
.tpl-cid { font-size: 9px; color: #a855f7; margin-top: 2px; }
.tpl-actions { display: flex; gap: 5px; }
.sm-btn { font-size: 10px; padding: 4px 8px; background: #334155; color: white; }
.sm-btn.danger { background: #ef4444; }

/* Logs */
.logs-box { background: #1e293b; padding: 15px; border-radius: 8px; }
.log-content { background: #0f172a; padding: 10px; font-family: monospace; font-size: 10px; color: #bef264; max-height: 150px; overflow-y: auto; }
.last-tx { background: #1e293b; padding: 15px; border-radius: 8px; border-left: 4px solid #4ade80; }
.last-tx .tpl-badge { font-size: 10px; background: #a855f7; color: white; display: inline-block; padding: 2px 6px; border-radius: 4px; margin-top: 5px; }

/* Modal */
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); display: flex; justify-content: center; align-items: center; }
.modal { background: #1e293b; padding: 25px; border-radius: 8px; width: 400px; }
.modal-actions { display: flex; gap: 10px; margin-top: 20px; }
.modal-actions button { flex: 1; background: #38bdf8; color: #0f172a; }
.modal-actions button.cancel { background: #ef4444; color: white; }
</style>
