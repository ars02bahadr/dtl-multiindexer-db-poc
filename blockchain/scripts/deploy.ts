import { ethers } from "hardhat";

async function main() {
    const MoneyToken = await ethers.getContractFactory("MoneyToken");
    const token = await MoneyToken.deploy();

    await token.waitForDeployment();

    console.log(`MoneyToken deployed to ${token.target}`);

    // Mint to Alice and Bob
    const alice = "0xfe3b557e8fb62b89f4916b721be55ceb828dbd73";
    const bob = "0x627306090abab3a6e1400e9345bc60c78a8bef57";

    await token.mint(alice, ethers.parseEther("1200"));
    console.log(`Minted 1200 DTL to Alice (${alice})`);

    await token.mint(bob, ethers.parseEther("1200"));
    console.log(`Minted 1200 DTL to Bob (${bob})`);
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
