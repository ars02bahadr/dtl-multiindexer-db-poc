import { DTLMultiIndexer } from './index';

async function main() {
    // Configuration
    const tokenAddress = "0xa5A19a794fc1ec3010F832Dee431cF81D55D7Aee";
    const aliceAddress = "0xfe3b557e8fb62b89f4916b721be55ceb828dbd73";
    const bobAddress = "0x627306090abab3a6e1400e9345bc60c78a8bef57";

    // Nodes (Validator 1 & Validator 2)
    const nodes = [
        "http://localhost:8545",
        "http://localhost:8555"
    ];

    console.log("🔍 Starting Multi-Indexer Consensus Check...");
    console.log(`Nodes: ${nodes.join(", ")}`);
    console.log(`Token: ${tokenAddress}\n`);

    const indexer = new DTLMultiIndexer(nodes, tokenAddress);

    // Check Alice
    console.log("Checking Alice's Balance...");
    const resultAlice = await indexer.getBalanceEffectively(aliceAddress);
    printResult("Alice", resultAlice);

    // Check Bob
    console.log("\nChecking Bob's Balance...");
    const resultBob = await indexer.getBalanceEffectively(bobAddress);
    printResult("Bob", resultBob);
}

function printResult(name: string, result: any) {
    if (result.consensus) {
        console.log(`✅ ${name}: Consensus Reached!`);
        console.log(`   Balance: ${result.balance} DTL`);
        console.log(`   Agreement: ${result.agreementPercentage}%`);
    } else {
        console.log(`❌ ${name}: Consensus Failed!`);
    }
    console.log("   Details:");
    result.details.forEach((d: any) => {
        console.log(`   - Node ${d.nodeUrl}: ${d.success ? d.balance : "Error: " + d.error}`);
    });
}

main().catch(console.error);
