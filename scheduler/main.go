package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math/big"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"
)

type JSONRPCRequest struct {
	JSONRPC string        `json:"jsonrpc"`
	Method  string        `json:"method"`
	Params  []interface{} `json:"params"`
	ID      int           `json:"id"`
}

type JSONRPCResponse struct {
	JSONRPC string      `json:"jsonrpc"`
	ID      int         `json:"id"`
	Result  interface{} `json:"result"`
	Error   *RPCError   `json:"error,omitempty"`
}

type RPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

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

type Scheduler struct {
	besuURL  string
	interval time.Duration
	client   *http.Client
	logFile  string
}

func NewScheduler(besuURL string, interval time.Duration, logFile string) *Scheduler {
	return &Scheduler{
		besuURL:  besuURL,
		interval: interval,
		logFile:  logFile,
		client: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

// writeToFile - Dosyaya yazar
func (s *Scheduler) writeToFile(content string) error {
	f, err := os.OpenFile(s.logFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	defer f.Close()

	_, err = f.WriteString(content)
	return err
}

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

func (s *Scheduler) getBlockNumber() (uint64, error) {
	resp, err := s.callRPC("eth_blockNumber", []interface{}{})
	if err != nil {
		return 0, err
	}

	hexStr, ok := resp.Result.(string)
	if !ok {
		return 0, fmt.Errorf("unexpected result type: %T", resp.Result)
	}

	// Handle empty or invalid hex string
	if len(hexStr) < 2 {
		return 0, fmt.Errorf("invalid hex string: %s", hexStr)
	}

	// Remove 0x prefix if present
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

func (s *Scheduler) getLatestBlock() (*BlockInfo, error) {
	resp, err := s.callRPC("eth_getBlockByNumber", []interface{}{"latest", false})
	if err != nil {
		return nil, err
	}

	blockData, err := json.Marshal(resp.Result)
	if err != nil {
		return nil, err
	}

	var block BlockInfo
	if err := json.Unmarshal(blockData, &block); err != nil {
		return nil, err
	}

	return &block, nil
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

	// Raw block with transactions
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

// weiToEther - Wei'yi ETH'e çevirir
func weiToEther(weiHex string) string {
	if weiHex == "" || weiHex == "0x0" {
		return "0"
	}

	cleanHex := weiHex
	if len(weiHex) >= 2 && weiHex[:2] == "0x" {
		cleanHex = weiHex[2:]
	}

	// Parse as big int
	wei, err := strconv.ParseUint(cleanHex, 16, 64)
	if err != nil {
		return "0"
	}

	// Convert to ETH (1 ETH = 10^18 wei)
	eth := float64(wei) / 1e18
	if eth == 0 {
		return "0"
	}
	return fmt.Sprintf("%.6f", eth)
}

// isERC20Transfer - ERC20 transfer olup olmadığını kontrol eder
func isERC20Transfer(input string) bool {
	// ERC20 transfer method signature: 0xa9059cbb
	return len(input) >= 10 && input[:10] == "0xa9059cbb"
}

// decodeERC20Transfer - ERC20 transfer verisini decode eder
func decodeERC20Transfer(input string) (to string, amount string) {
	if len(input) < 138 {
		return "", ""
	}

	// to address: bytes 10-74 (32 bytes, last 20 bytes are address)
	toHex := input[10:74]
	to = "0x" + toHex[24:] // Son 20 byte (40 karakter)

	// amount: bytes 74-138 (32 bytes)
	amountHex := input[74:138]
	// Başındaki sıfırları kaldır
	amountHex = strings.TrimLeft(amountHex, "0")
	if amountHex == "" {
		amountHex = "0"
	}

	// Büyük sayılar için big.Int kullan
	amountBig := new(big.Int)
	amountBig.SetString(amountHex, 16)

	// Token'ın decimal'ına göre formatla
	// Önce raw değeri göster, eğer çok büyükse 18 decimal varsay
	amountUint := amountBig.Uint64()
	if amountUint > 1e15 {
		// Muhtemelen 18 decimal
		amountFloat := new(big.Float).SetInt(amountBig)
		divisor := new(big.Float).SetFloat64(1e18)
		amountFloat.Quo(amountFloat, divisor)
		amount = amountFloat.Text('f', 2)
	} else {
		// Raw değer (decimal yok veya düşük)
		amount = amountBig.String()
	}

	return to, amount
}

func (s *Scheduler) getPeerCount() (int, error) {
	resp, err := s.callRPC("net_peerCount", []interface{}{})
	if err != nil {
		return 0, err
	}

	hexStr, ok := resp.Result.(string)
	if !ok {
		return 0, fmt.Errorf("unexpected result type: %T", resp.Result)
	}

	if len(hexStr) < 2 {
		return 0, nil
	}

	cleanHex := hexStr
	if len(hexStr) >= 2 && hexStr[:2] == "0x" {
		cleanHex = hexStr[2:]
	}

	if cleanHex == "" {
		return 0, nil
	}

	count, err := strconv.ParseInt(cleanHex, 16, 64)
	if err != nil {
		return 0, fmt.Errorf("failed to parse peer count: %w", err)
	}

	return int(count), nil
}

func (s *Scheduler) runJob() {
	log.Println("========== Running scheduled job ==========")
	startTime := time.Now()

	var report strings.Builder
	report.WriteString("\n")
	report.WriteString("╔══════════════════════════════════════════════════════════════════════════════╗\n")
	report.WriteString(fmt.Sprintf("║  📅 BESU BLOCKCHAIN RAPORU - %s  ║\n", startTime.Format("2006-01-02 15:04:05")))
	report.WriteString("╠══════════════════════════════════════════════════════════════════════════════╣\n")
	report.WriteString("║                                                                              ║\n")
	report.WriteString("║  🔍 YAPILAN İŞLEM: Besu blockchain node'una bağlanıp aşağıdaki bilgiler      ║\n")
	report.WriteString("║     alındı ve bu dosyaya kaydedildi.                                         ║\n")
	report.WriteString("║                                                                              ║\n")

	// Get block number
	blockNum, err := s.getBlockNumber()
	if err != nil {
		log.Printf("❌ Error getting block number: %v", err)
		report.WriteString(fmt.Sprintf("║  ❌ Blok numarası alınamadı: %v\n", err))
	} else {
		log.Printf("📦 Current block number: %d", blockNum)
		report.WriteString(fmt.Sprintf("║  📦 GÜNCEL BLOK NUMARASI: %d                                          ║\n", blockNum))
	}

	// Get latest block info
	block, err := s.getLatestBlock()
	if err != nil {
		log.Printf("❌ Error getting latest block: %v", err)
		report.WriteString(fmt.Sprintf("║  ❌ Blok detayları alınamadı: %v\n", err))
	} else if block != nil && block.Timestamp != "" {
		cleanHex := block.Timestamp
		if len(cleanHex) >= 2 && cleanHex[:2] == "0x" {
			cleanHex = cleanHex[2:]
		}
		if cleanHex != "" {
			timestamp, _ := strconv.ParseInt(cleanHex, 16, 64)
			blockTime := time.Unix(timestamp, 0)
			hash := block.Hash
			if len(hash) > 20 {
				hash = hash[:20] + "..."
			}
			log.Printf("🔗 Latest block hash: %s", hash)
			log.Printf("⏰ Block timestamp: %s", blockTime.Format(time.RFC3339))
			log.Printf("📝 Transactions in block: %d", len(block.Transactions))
			log.Printf("⛏️  Miner/Validator: %s", block.Miner)

			report.WriteString("║                                                                              ║\n")
			report.WriteString("║  📋 SON BLOK DETAYLARI:                                                      ║\n")
			report.WriteString(fmt.Sprintf("║     • Blok Hash: %s                            ║\n", block.Hash[:42]))
			report.WriteString(fmt.Sprintf("║     • Blok Zamanı: %s                               ║\n", blockTime.Format("2006-01-02 15:04:05")))
			report.WriteString(fmt.Sprintf("║     • İşlem Sayısı: %d                                                      ║\n", len(block.Transactions)))
			report.WriteString(fmt.Sprintf("║     • Validator: %s       ║\n", block.Miner))

			// Gas bilgisi
			if block.GasUsed != "" {
				gasUsed, _ := strconv.ParseInt(block.GasUsed[2:], 16, 64)
				gasLimit, _ := strconv.ParseInt(block.GasLimit[2:], 16, 64)
				report.WriteString(fmt.Sprintf("║     • Gas Kullanımı: %d / %d                                   ║\n", gasUsed, gasLimit))
			}
		}
	}

	// Get peer count
	peerCount, err := s.getPeerCount()
	if err != nil {
		log.Printf("❌ Error getting peer count: %v", err)
	} else {
		log.Printf("👥 Connected peers: %d", peerCount)
		report.WriteString("║                                                                              ║\n")
		report.WriteString(fmt.Sprintf("║  👥 BAĞLI PEER SAYISI: %d                                                    ║\n", peerCount))
	}

	// Get syncing status
	syncing, err := s.getSyncingStatus()
	if err != nil {
		log.Printf("❌ Error getting sync status: %v", err)
	} else {
		syncStatus := "Senkronize ✅"
		if syncing {
			syncStatus = "Senkronize ediliyor... ⏳"
		}
		report.WriteString(fmt.Sprintf("║  🔄 SENKRON DURUMU: %s                                      ║\n", syncStatus))
	}

	// Son 10 bloktaki transaction'ları al
	report.WriteString("║                                                                              ║\n")
	report.WriteString("╠══════════════════════════════════════════════════════════════════════════════╣\n")
	report.WriteString("║  💸 SON TRANSFER İŞLEMLERİ (Son 10 blok):                                    ║\n")
	report.WriteString("╠══════════════════════════════════════════════════════════════════════════════╣\n")

	txs, err := s.getRecentTransactions(10)
	if err != nil {
		log.Printf("❌ Error getting transactions: %v", err)
		report.WriteString("║  ❌ Transaction bilgileri alınamadı                                           ║\n")
	} else if len(txs) == 0 {
		log.Printf("📭 No transactions in last 10 blocks")
		report.WriteString("║  📭 Son 10 blokta işlem yok                                                   ║\n")
	} else {
		log.Printf("💸 Found %d transactions in last 10 blocks", len(txs))
		for i, tx := range txs {
			if i >= 5 { // En fazla 5 transaction göster
				report.WriteString(fmt.Sprintf("║  ... ve %d işlem daha                                                        ║\n", len(txs)-5))
				break
			}

			fromShort := tx.From
			if len(fromShort) > 10 {
				fromShort = tx.From[:6] + "..." + tx.From[len(tx.From)-4:]
			}

			toShort := tx.To
			if tx.To == "" {
				toShort = "Contract Deploy"
			} else if len(toShort) > 10 {
				toShort = tx.To[:6] + "..." + tx.To[len(tx.To)-4:]
			}

			// Native ETH transfer mi, ERC20 transfer mi?
			if isERC20Transfer(tx.Input) {
				erc20To, amount := decodeERC20Transfer(tx.Input)
				erc20ToShort := erc20To
				if len(erc20ToShort) > 10 {
					erc20ToShort = erc20To[:6] + "..." + erc20To[len(erc20To)-4:]
				}
				report.WriteString("║  ─────────────────────────────────────────────────────────────────────────── ║\n")
				report.WriteString(fmt.Sprintf("║  🪙 TOKEN TRANSFER #%d                                                        ║\n", i+1))
				report.WriteString(fmt.Sprintf("║     Gönderen: %s                                              ║\n", fromShort))
				report.WriteString(fmt.Sprintf("║     Alan    : %s                                              ║\n", erc20ToShort))
				report.WriteString(fmt.Sprintf("║     Miktar  : %s DTL                                                    ║\n", amount))
				log.Printf("   🪙 Token: %s -> %s : %s DTL", fromShort, erc20ToShort, amount)
			} else {
				// Native ETH transfer
				ethAmount := weiToEther(tx.Value)
				report.WriteString("║  ─────────────────────────────────────────────────────────────────────────── ║\n")
				report.WriteString(fmt.Sprintf("║  💰 ETH TRANSFER #%d                                                          ║\n", i+1))
				report.WriteString(fmt.Sprintf("║     Gönderen: %s                                              ║\n", fromShort))
				report.WriteString(fmt.Sprintf("║     Alan    : %s                                              ║\n", toShort))
				report.WriteString(fmt.Sprintf("║     Miktar  : %s ETH                                                 ║\n", ethAmount))
				log.Printf("   💰 ETH: %s -> %s : %s ETH", fromShort, toShort, ethAmount)
			}
		}
	}

	elapsed := time.Since(startTime)
	log.Printf("✅ Job completed in %v", elapsed)
	log.Println("============================================")

	report.WriteString("║                                                                              ║\n")
	report.WriteString(fmt.Sprintf("║  ⏱️  İşlem Süresi: %v                                               ║\n", elapsed.Round(time.Millisecond)))
	report.WriteString("║                                                                              ║\n")
	report.WriteString("╚══════════════════════════════════════════════════════════════════════════════╝\n")

	// Dosyaya yaz
	if err := s.writeToFile(report.String()); err != nil {
		log.Printf("❌ Dosyaya yazılamadı: %v", err)
	} else {
		log.Printf("📝 Rapor dosyaya kaydedildi: %s", s.logFile)
	}
}

func (s *Scheduler) Start() {
	log.Printf("🚀 Starting DTL Scheduler")
	log.Printf("📡 Besu RPC URL: %s", s.besuURL)
	log.Printf("⏱️  Interval: %v", s.interval)
	log.Printf("📁 Log file: %s", s.logFile)

	// Başlangıç mesajını dosyaya yaz
	startMsg := fmt.Sprintf("\n\n🚀 SCHEDULER BAŞLATILDI - %s\n", time.Now().Format("2006-01-02 15:04:05"))
	startMsg += fmt.Sprintf("📡 Besu RPC: %s\n", s.besuURL)
	startMsg += fmt.Sprintf("⏱️  Interval: %v\n", s.interval)
	startMsg += "═══════════════════════════════════════════════════════════════════════════════\n"
	s.writeToFile(startMsg)

	// Run immediately on start
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
			s.writeToFile(fmt.Sprintf("\n🛑 SCHEDULER DURDURULDU - %s\n", time.Now().Format("2006-01-02 15:04:05")))
			return
		}
	}
}

// getSyncingStatus - Senkronizasyon durumunu kontrol eder
func (s *Scheduler) getSyncingStatus() (bool, error) {
	resp, err := s.callRPC("eth_syncing", []interface{}{})
	if err != nil {
		return false, err
	}

	// false dönerse senkronize demektir
	if syncing, ok := resp.Result.(bool); ok {
		return syncing, nil
	}

	// Object dönerse hala senkronize oluyor demektir
	return true, nil
}

func main() {
	besuURL := os.Getenv("BESU_RPC_URL")
	if besuURL == "" {
		besuURL = "http://dtl-validator1:8545"
	}

	intervalStr := os.Getenv("SCHEDULER_INTERVAL")
	interval := 2 * time.Minute
	if intervalStr != "" {
		if d, err := time.ParseDuration(intervalStr); err == nil {
			interval = d
		}
	}

	logFile := os.Getenv("LOG_FILE")
	if logFile == "" {
		logFile = "/app/logs/blockchain_report.txt"
	}

	// Log dizinini oluştur
	os.MkdirAll("/app/logs", 0755)

	scheduler := NewScheduler(besuURL, interval, logFile)
	scheduler.Start()
}
