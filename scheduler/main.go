package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"
)

// Scheduler - Ana zamanlayıcı yapısı
type Scheduler struct {
	besuURL     string
	interval    time.Duration
	client      *http.Client
	besuLogFile string
}

// NewScheduler - Yeni scheduler oluşturur
func NewScheduler(besuURL string, interval time.Duration, besuLogFile string) *Scheduler {
	return &Scheduler{
		besuURL:     besuURL,
		interval:    interval,
		besuLogFile: besuLogFile,
		client: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

// appendToFile - Dosyaya ekleme yapar
func (s *Scheduler) appendToFile(filename, content string) error {
	f, err := os.OpenFile(filename, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	defer f.Close()
	_, err = f.WriteString(content)
	return err
}

// callRPC - JSON-RPC çağrısı yapar
func (s *Scheduler) callRPC(method string, params []interface{}) (*JSONRPCResponse, error) {
	reqBody := JSONRPCRequest{
		JSONRPC: "2.0",
		Method:  method,
		Params:  params,
		ID:      1,
	}

	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	resp, err := s.client.Post(s.besuURL, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to call RPC: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	var rpcResp JSONRPCResponse
	if err := json.Unmarshal(body, &rpcResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	if rpcResp.Error != nil {
		return nil, fmt.Errorf("RPC error: %s", rpcResp.Error.Message)
	}

	return &rpcResp, nil
}

// getBlockNumber - Güncel blok numarasını alır
func (s *Scheduler) getBlockNumber() (uint64, error) {
	resp, err := s.callRPC("eth_blockNumber", []interface{}{})
	if err != nil {
		return 0, err
	}

	hexStr, ok := resp.Result.(string)
	if !ok {
		return 0, fmt.Errorf("unexpected result type: %T", resp.Result)
	}

	if len(hexStr) < 2 {
		return 0, fmt.Errorf("invalid hex string: %s", hexStr)
	}

	cleanHex := hexStr
	if len(hexStr) >= 2 && hexStr[:2] == "0x" {
		cleanHex = hexStr[2:]
	}

	if cleanHex == "" {
		return 0, nil
	}

	blockNum, err := strconv.ParseUint(cleanHex, 16, 64)
	if err != nil {
		return 0, fmt.Errorf("failed to parse block number: %w", err)
	}

	return blockNum, nil
}

// getBlockWithTransactions - Transaction detayları ile blok alır
func (s *Scheduler) getBlockWithTransactions(blockNumber string) (*BlockInfo, []Transaction, error) {
	resp, err := s.callRPC("eth_getBlockByNumber", []interface{}{blockNumber, true})
	if err != nil {
		return nil, nil, err
	}

	blockData, err := json.Marshal(resp.Result)
	if err != nil {
		return nil, nil, err
	}

	var rawBlock struct {
		Number       string        `json:"number"`
		Hash         string        `json:"hash"`
		Timestamp    string        `json:"timestamp"`
		Transactions []Transaction `json:"transactions"`
		Miner        string        `json:"miner"`
		GasUsed      string        `json:"gasUsed"`
		GasLimit     string        `json:"gasLimit"`
	}

	if err := json.Unmarshal(blockData, &rawBlock); err != nil {
		return nil, nil, err
	}

	block := &BlockInfo{
		Number:    rawBlock.Number,
		Hash:      rawBlock.Hash,
		Timestamp: rawBlock.Timestamp,
		Miner:     rawBlock.Miner,
		GasUsed:   rawBlock.GasUsed,
		GasLimit:  rawBlock.GasLimit,
	}

	return block, rawBlock.Transactions, nil
}

// getRecentTransactions - Son N bloktaki transaction'ları alır
func (s *Scheduler) getRecentTransactions(blockCount int) ([]Transaction, error) {
	currentBlock, err := s.getBlockNumber()
	if err != nil {
		return nil, err
	}

	var allTxs []Transaction

	for i := 0; i < blockCount && currentBlock > 0; i++ {
		blockHex := fmt.Sprintf("0x%x", currentBlock-uint64(i))
		_, txs, err := s.getBlockWithTransactions(blockHex)
		if err != nil {
			continue
		}
		allTxs = append(allTxs, txs...)
	}

	return allTxs, nil
}

// runJob - Zamanlanmış görevi çalıştırır
func (s *Scheduler) runJob() {
	log.Println("========== Running scheduled job ==========")
	startTime := time.Now()

	// Blok numarasını al
	blockNum, err := s.getBlockNumber()
	if err != nil {
		log.Printf("❌ Error getting block number: %v", err)
	} else {
		log.Printf("📦 Current block number: %d", blockNum)
	}

	// Son transaction'ları al
	txs, err := s.getRecentTransactions(30)
	if err != nil {
		log.Printf("❌ Error getting transactions: %v", err)
		return
	}

	if len(txs) == 0 {
		log.Printf("📭 No transactions in last 30 blocks")
		return
	}

	log.Printf("💸 Found %d transactions in last 30 blocks", len(txs))

	// Her transaction'ı işle
	for _, tx := range txs {
		// Payment işlemini yap (sadece para transferi varsa çalışır)
		result := ProcessPaymentTransaction(tx, startTime)

		if result != nil {
			// Log satırını oluştur
			elapsed := time.Since(startTime)
			logLine := fmt.Sprintf("[%s] %s | Gönderen: %s | Alan: %s | Miktar: %s | Süre: %v\n",
				startTime.Format("2006-01-02 15:04:05"),
				result.TxType,
				result.From,
				result.To,
				result.Amount,
				elapsed.Round(time.Millisecond),
			)

			if err := s.appendToFile(s.besuLogFile, logLine); err != nil {
				log.Printf("❌ Dosyaya yazılamadı: %v", err)
			}

			log.Printf("   📝 Logged: %s -> %s : %s", result.From, result.To, result.Amount)
		}
	}

	log.Printf("✅ Job completed in %v", time.Since(startTime))
	log.Println("============================================")
}

// Start - Scheduler'ı başlatır
func (s *Scheduler) Start() {
	log.Printf("🚀 Starting DTL Scheduler")
	log.Printf("📡 Besu RPC URL: %s", s.besuURL)
	log.Printf("⏱️  Interval: %v", s.interval)
	log.Printf("📁 Besu Log file: %s", s.besuLogFile)

	// Başlangıçta hemen çalıştır
	s.runJob()

	ticker := time.NewTicker(s.interval)
	defer ticker.Stop()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	for {
		select {
		case <-ticker.C:
			s.runJob()
		case sig := <-sigChan:
			log.Printf("🛑 Received signal %v, shutting down...", sig)
			return
		}
	}
}

func main() {
	// Besu RPC URL
	besuURL := os.Getenv("BESU_RPC_URL")
	if besuURL == "" {
		besuURL = "http://localhost:8545"
	}

	// Interval
	intervalStr := os.Getenv("SCHEDULER_INTERVAL")
	interval := 30 * time.Second
	if intervalStr != "" {
		if d, err := time.ParseDuration(intervalStr); err == nil {
			interval = d
		}
	}

	// Log dosyası
	logFile := os.Getenv("LOG_FILE")
	if logFile == "" {
		logFile = "./logs/blockchain_report.txt"
	}

	// Log dizinini oluştur
	if err := os.MkdirAll("./logs", 0755); err != nil {
		log.Printf("⚠️  Warning: Could not create local log dir: %v", err)
	}

	// OpenCBDC URL
	opencbdcURL := os.Getenv("OPENCBDC_URL")
	if opencbdcURL == "" {
		opencbdcURL = "mock"
	}

	// Payment sistemini başlat
	cbdcLogFile := "./logs/opencbdc_report.txt"
	InitPaymentSystem(opencbdcURL, cbdcLogFile)

	// Scheduler'ı başlat
	scheduler := NewScheduler(besuURL, interval, logFile)
	scheduler.Start()
}
