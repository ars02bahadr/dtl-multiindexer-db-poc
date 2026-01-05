// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract MoneyToken is ERC20, Ownable {
    mapping(bytes32 => bool) public processedTxHashes;

    event MetadataUpdated(address indexed user, string metadataHash);

    constructor() ERC20("Digital Turkish Lira", "DTL") Ownable(msg.sender) {
        _mint(msg.sender, 1000000 * 10 ** decimals());
    }

    function mint(address to, uint256 amount) public onlyOwner {
        _mint(to, amount);
    }

    function burn(uint256 amount) public {
        _burn(msg.sender, amount);
    }

    // Example feature: Attach IPFS metadata hash to a transfer-like event (or simplified just state update)
    // In a real DTL scenario, we might want to attach invoice refs etc.
    function updateMetadata(string memory ipfsHash) public {
        emit MetadataUpdated(msg.sender, ipfsHash);
    }
}
