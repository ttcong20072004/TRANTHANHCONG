pragma solidity ^0.8.7;
import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
contract GameNFT is ERC1155("https://ipfs.io/ipfs/bafybeibsypycoiijvhn5arrrq4ipssvcjd6rzx4ju2dg qayilv4bppaj5e/{id}.json") {
uint256 public constant CHARIZARD = 6;
uint256 public constant IVYSAUR = 7;
uint256 public constant VENUSAUR = 8;
uint256 public constant CHARMANDER = 9;
constructor() { _mint(msg.sender, CHARIZARD, 10, "");
_mint(msg.sender, IVYSAUR, 10, "");
_mint(msg.sender, VENUSAUR, 10, ""); 
_mint(msg.sender, CHARMANDER, 10, "");
}
}
