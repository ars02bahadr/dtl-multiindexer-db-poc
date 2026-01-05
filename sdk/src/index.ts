import { ethers } from 'ethers';

const MONEY_TOKEN_ABI = [
    "function balanceOf(address owner) view returns (uint256)"
];

export interface IndexerResult {
    balance: string;
    nodeUrl: string;
    success: boolean;
    error?: string;
}

export interface ConsensusResult {
    balance: string;
    consensus: boolean;
    agreementPercentage: number;
    details: IndexerResult[];
}

export class DTLMultiIndexer {
    private nodes: string[];
    private tokenAddress: string;

    constructor(nodes: string[], tokenAddress: string) {
        this.nodes = nodes;
        this.tokenAddress = tokenAddress;
    }

    async getBalanceEffectively(userAddress: string): Promise<ConsensusResult> {
        const promises = this.nodes.map(async (url) => {
            try {
                const provider = new ethers.JsonRpcProvider(url);
                const contract = new ethers.Contract(this.tokenAddress, MONEY_TOKEN_ABI, provider);
                const balance = await contract.balanceOf(userAddress);
                return {
                    balance: ethers.formatEther(balance),
                    nodeUrl: url,
                    success: true
                } as IndexerResult;
            } catch (e: any) {
                return {
                    balance: "0",
                    nodeUrl: url,
                    success: false,
                    error: e.message
                } as IndexerResult;
            }
        });

        const results = await Promise.all(promises);

        // Calculate consensus
        const successfulResults = results.filter(r => r.success);
        if (successfulResults.length === 0) {
            return {
                balance: "0",
                consensus: false,
                agreementPercentage: 0,
                details: results
            };
        }

        // Count occurrences
        const counts = new Map<string, number>();
        successfulResults.forEach(r => {
            counts.set(r.balance, (counts.get(r.balance) || 0) + 1);
        });

        // Find majority
        let maxCount = 0;
        let majorityBalance = "0";
        counts.forEach((count, balance) => {
            if (count > maxCount) {
                maxCount = count;
                majorityBalance = balance;
            }
        });

        const agreementPercentage = (maxCount / this.nodes.length) * 100;

        return {
            balance: majorityBalance,
            consensus: agreementPercentage > 50,
            agreementPercentage,
            details: results
        };
    }
}
