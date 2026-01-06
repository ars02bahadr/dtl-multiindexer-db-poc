package main

// JSONRPCRequest - JSON-RPC istek yapısı
type JSONRPCRequest struct {
	JSONRPC string        `json:"jsonrpc"`
	Method  string        `json:"method"`
	Params  []interface{} `json:"params"`
	ID      int           `json:"id"`
}

// JSONRPCResponse - JSON-RPC yanıt yapısı
type JSONRPCResponse struct {
	JSONRPC string      `json:"jsonrpc"`
	ID      int         `json:"id"`
	Result  interface{} `json:"result"`
	Error   *RPCError   `json:"error,omitempty"`
}

// RPCError - RPC hata yapısı
type RPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// BlockInfo - Blok bilgileri
type BlockInfo struct {
	Number       string        `json:"number"`
	Hash         string        `json:"hash"`
	Timestamp    string        `json:"timestamp"`
	Transactions []interface{} `json:"transactions"`
	Miner        string        `json:"miner"`
	GasUsed      string        `json:"gasUsed"`
	GasLimit     string        `json:"gasLimit"`
	Size         string        `json:"size"`
}

// Transaction - Blockchain transaction detayları
type Transaction struct {
	Hash        string `json:"hash"`
	From        string `json:"from"`
	To          string `json:"to"`
	Value       string `json:"value"`
	Gas         string `json:"gas"`
	GasPrice    string `json:"gasPrice"`
	Input       string `json:"input"`
	Nonce       string `json:"nonce"`
	BlockNumber string `json:"blockNumber"`
}

// TransactionReceipt - İşlem makbuzu
type TransactionReceipt struct {
	TransactionHash string `json:"transactionHash"`
	Status          string `json:"status"`
	GasUsed         string `json:"gasUsed"`
	ContractAddress string `json:"contractAddress"`
	Logs            []Log  `json:"logs"`
}

// Log - Event log
type Log struct {
	Address string   `json:"address"`
	Topics  []string `json:"topics"`
	Data    string   `json:"data"`
}

// ========== OpenCBDC Models ==========

// OutPoint - UTXO referansı
type OutPoint struct {
	TxID  [32]byte `json:"tx_id"`
	Index uint32   `json:"index"`
}

// Output - Transaction çıktısı
type Output struct {
	Amount uint64 `json:"amount"`
	PubKey []byte `json:"pub_key"`
	Data   []byte `json:"data,omitempty"`
}

// Input - Transaction girdisi
type Input struct {
	PreviousOutPoint OutPoint `json:"previous_out_point"`
	Signature        []byte   `json:"signature"`
}

// UTXOTransaction - UTXO tabanlı transaction
type UTXOTransaction struct {
	Inputs  []Input  `json:"inputs"`
	Outputs []Output `json:"outputs"`
}

// UTXO - Harcanmamış transaction çıktısı
type UTXO struct {
	OutPoint OutPoint `json:"out_point"`
	Amount   uint64   `json:"amount"`
	PubKey   []byte   `json:"pub_key"`
}

// PaymentTask - Ödeme görevi
type PaymentTask struct {
	SenderPubKey   []byte
	ReceiverPubKey []byte
	Amount         uint64
	IpfsHash       string
}

// PaymentResult - Ödeme sonucu
type PaymentResult struct {
	Success  bool
	Report   string
	TxType   string
	From     string
	To       string
	Amount   string
	Error    error
}
