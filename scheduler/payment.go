package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"math/big"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"
)

// OpenCBDCClient arayüzü
type OpenCBDCClient interface {
	GetUTXOs(pubKey []byte) ([]UTXO, error)
	SendTransaction(tx *UTXOTransaction) error
}

// Global client
var cbdcClient OpenCBDCClient
var cbdcLogFile string

// ========== HTTP Client ==========

type HTTPClient struct {
	BaseURL string
	Client  *http.Client
}

func NewHTTPClient(baseURL string) *HTTPClient {
	return &HTTPClient{
		BaseURL: baseURL,
		Client:  &http.Client{Timeout: 10 * time.Second},
	}
}

func (c *HTTPClient) GetUTXOs(pubKey []byte) ([]UTXO, error) {
	url := fmt.Sprintf("%s/utxos?pubkey=%s", c.BaseURL, string(pubKey))
	resp, err := c.Client.Get(url)
	if err != nil {
		return nil, fmt.Errorf("HTTP request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}
	var utxos []UTXO
	if err := json.NewDecoder(resp.Body).Decode(&utxos); err != nil {
		return nil, fmt.Errorf("decode error: %w", err)
	}
	return utxos, nil
}

func (c *HTTPClient) SendTransaction(tx *UTXOTransaction) error {
	jsonData, err := json.Marshal(tx)
	if err != nil {
		return err
	}
	url := fmt.Sprintf("%s/send", c.BaseURL)
	resp, err := c.Client.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("error status: %d", resp.StatusCode)
	}
	return nil
}

// ========== Mock Client ==========

type InternalMockClient struct{}

func (m *InternalMockClient) GetUTXOs(pubKey []byte) ([]UTXO, error) {
	return []UTXO{
		{OutPoint: OutPoint{TxID: [32]byte{1}, Index: 0}, Amount: 5000, PubKey: pubKey},
		{OutPoint: OutPoint{TxID: [32]byte{1}, Index: 1}, Amount: 3000, PubKey: pubKey},
	}, nil
}

func (m *InternalMockClient) SendTransaction(tx *UTXOTransaction) error {
	log.Printf("📡 [Mock] Transaction Broadcasted internally:")
	log.Printf("   Inputs: %d, Outputs: %d", len(tx.Inputs), len(tx.Outputs))
	for _, out := range tx.Outputs {
		if len(out.Data) > 0 {
			log.Printf("   Memo/Data: %s", string(out.Data))
		}
	}
	return nil
}

// ========== Init & Execute ==========

// InitPaymentSystem - Ödeme sistemini başlatır
func InitPaymentSystem(opencbdcURL, logFile string) {
	cbdcLogFile = logFile

	if opencbdcURL == "mock" || opencbdcURL == "" {
		cbdcClient = &InternalMockClient{}
		log.Println("🔌 Initialized INTERNAL MOCK OpenCBDC Client")
	} else {
		cbdcClient = NewHTTPClient(opencbdcURL)
		log.Printf("🔌 Initialized HTTP OpenCBDC Client pointing to: %s", opencbdcURL)
	}
}

// ProcessPaymentTransaction - Para transferi işlemini yapar ve loglar
func ProcessPaymentTransaction(tx Transaction, startTime time.Time) *PaymentResult {
	elapsed := time.Since(startTime)

	// Gönderen adresi kısalt
	fromShort := shortenAddress(tx.From)

	var toShort, amountStr, txType string
	var task PaymentTask

	if isERC20Transfer(tx.Input) {
		// ERC20 Token Transfer
		erc20To, amount := decodeERC20Transfer(tx.Input)
		toShort = shortenAddress(erc20To)
		amountStr = amount + " DTL"
		txType = "TOKEN"

		amtFloat, _ := strconv.ParseFloat(amount, 64)
		task = PaymentTask{
			SenderPubKey:   []byte(tx.From),
			ReceiverPubKey: []byte(erc20To),
			Amount:         uint64(amtFloat),
			IpfsHash:       "TODO_EXTRACT_FROM_LOGS",
		}
	} else {
		// Native ETH Transfer
		if tx.To == "" {
			// Contract deployment - para transferi değil, atla
			return nil
		}

		toShort = shortenAddress(tx.To)
		ethAmount := weiToEther(tx.Value)
		amountStr = ethAmount + " ETH"
		txType = "ETH"

		amtFloat, _ := strconv.ParseFloat(ethAmount, 64)
		task = PaymentTask{
			SenderPubKey:   []byte(tx.From),
			ReceiverPubKey: []byte(tx.To),
			Amount:         uint64(amtFloat * 100),
			IpfsHash:       "Native_ETH_Transfer",
		}
	}

	// OpenCBDC ödeme işlemi
	report, err := executePayment(task)

	result := &PaymentResult{
		TxType: txType,
		From:   fromShort,
		To:     toShort,
		Amount: amountStr,
	}

	if err != nil {
		result.Success = false
		result.Error = err
		appendToLogFile(cbdcLogFile, fmt.Sprintf("\n❌ [OpenCBDC] Payment Failed: %v\n", err))
	} else {
		result.Success = true
		result.Report = report
		logContent := fmt.Sprintf("\n--- [%s] ---\n%s", time.Now().Format(time.RFC3339), report)
		appendToLogFile(cbdcLogFile, logContent)
		log.Printf("   💸 OpenCBDC Payment Logged | %s -> %s : %s (%v)", fromShort, toShort, amountStr, elapsed.Round(time.Millisecond))
	}

	return result
}

// ========== Internal Functions ==========

func executePayment(task PaymentTask) (string, error) {
	if cbdcClient == nil {
		cbdcClient = &InternalMockClient{}
	}

	report := fmt.Sprintf("💸 OpenCBDC Transfer Process Started for %d units...\n", task.Amount)

	// Coin Selection
	inputs, total, err := selectInputs(task.SenderPubKey, task.Amount)
	if err != nil {
		return "", err
	}

	report += fmt.Sprintf("   🔻 HARCANAN BANKNOTLAR (INPUTS) - Toplam: %d\n", total)
	for i, input := range inputs {
		shortTxID := fmt.Sprintf("%x...", input.OutPoint.TxID[:4])
		report += fmt.Sprintf("      %d. [TxID: %s | Index: %d] Değer: %d\n", i+1, shortTxID, input.OutPoint.Index, input.Amount)
	}

	// Output oluştur
	var outputs []Output
	receiverOutput := Output{Amount: task.Amount, PubKey: task.ReceiverPubKey}
	outputs = append(outputs, receiverOutput)

	if total > task.Amount {
		outputs = append(outputs, Output{Amount: total - task.Amount, PubKey: task.SenderPubKey})
	}

	if task.IpfsHash != "" {
		outputs[0].Data = []byte("IPFS:" + task.IpfsHash)
		report += fmt.Sprintf("   📎 Veri Eklendi (Memo): %s\n", task.IpfsHash)
	}

	tx := &UTXOTransaction{Inputs: convertUTXOsToInputs(inputs), Outputs: outputs}

	// Gönder
	if err := cbdcClient.SendTransaction(tx); err != nil {
		return "", err
	}

	report += fmt.Sprintf("   ✅ OLUŞAN YENİ BANKNOTLAR (OUTPUTS)\n")
	for i, out := range outputs {
		label := "Alıcı"
		if i == 1 {
			label = "Para Üstü (Sender)"
		}
		report += fmt.Sprintf("      %d. [%s] Miktar: %d", i+1, label, out.Amount)
		if len(out.Data) > 0 {
			report += " (Verili)"
		}
		report += "\n"
	}
	return report, nil
}

func selectInputs(senderPubKey []byte, targetAmount uint64) ([]UTXO, uint64, error) {
	utxos, err := cbdcClient.GetUTXOs(senderPubKey)
	if err != nil {
		return nil, 0, err
	}

	var selected []UTXO
	var total uint64 = 0
	for _, u := range utxos {
		selected = append(selected, u)
		total += u.Amount
		if total >= targetAmount {
			return selected, total, nil
		}
	}
	if total < targetAmount {
		return nil, total, fmt.Errorf("insufficient funds")
	}
	return selected, total, nil
}

func convertUTXOsToInputs(utxos []UTXO) []Input {
	var inputs []Input
	for _, u := range utxos {
		inputs = append(inputs, Input{PreviousOutPoint: u.OutPoint, Signature: []byte{}})
	}
	return inputs
}

// ========== Helper Functions ==========

func shortenAddress(addr string) string {
	if len(addr) > 10 {
		return addr[:6] + "..." + addr[len(addr)-4:]
	}
	return addr
}

func appendToLogFile(filename, content string) error {
	f, err := os.OpenFile(filename, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	defer f.Close()
	_, err = f.WriteString(content)
	return err
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

	wei, err := strconv.ParseUint(cleanHex, 16, 64)
	if err != nil {
		return "0"
	}

	eth := float64(wei) / 1e18
	if eth == 0 {
		return "0"
	}
	return fmt.Sprintf("%.6f", eth)
}

// isERC20Transfer - ERC20 transfer olup olmadığını kontrol eder
func isERC20Transfer(input string) bool {
	return len(input) >= 10 && input[:10] == "0xa9059cbb"
}

// decodeERC20Transfer - ERC20 transfer verisini decode eder
func decodeERC20Transfer(input string) (to string, amount string) {
	if len(input) < 138 {
		return "", ""
	}

	toHex := input[10:74]
	to = "0x" + toHex[24:]

	amountHex := input[74:138]
	amountHex = strings.TrimLeft(amountHex, "0")
	if amountHex == "" {
		amountHex = "0"
	}

	amountBig := new(big.Int)
	amountBig.SetString(amountHex, 16)

	amountUint := amountBig.Uint64()
	if amountUint > 1e15 {
		amountFloat := new(big.Float).SetInt(amountBig)
		divisor := new(big.Float).SetFloat64(1e18)
		amountFloat.Quo(amountFloat, divisor)
		amount = amountFloat.Text('f', 2)
	} else {
		amount = amountBig.String()
	}

	return to, amount
}
