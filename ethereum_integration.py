import json
import time
from web3 import Web3

class EthereumBlockchain:
    def __init__(self):
        # Connect to Ethereum network (using Infura for this example)
        # You can replace this with your own Ethereum node URL or Infura project ID
        self.w3 = Web3(Web3.HTTPProvider("https://sepolia.infura.io/v3/1644a5b2aa5340d5b09b0b755f2cd4e3"))
        
        # Check connection
        if not self.w3.is_connected():
            print("Failed to connect to Ethereum network!")
        else:
            print("Connected to Ethereum network")
        
        # Contract details
        self.contract_address = "0xbac4eabE17C33647893544108fF0E676729a5f31"
        self.private_key = "071a43bc0fba7a86aa6386ddeda1bf1f07bdbb0e47b8a44cf51643ab9c7c9e34"
        
        # Load ABI (Application Binary Interface)
        self.contract_abi = [
            {
                "inputs": [
                    {"internalType": "string", "name": "_alertType", "type": "string"},
                    {"internalType": "string", "name": "_latitude", "type": "string"},
                    {"internalType": "string", "name": "_longitude", "type": "string"},
                    {"internalType": "bool", "name": "_deforestation", "type": "bool"}
                ],
                "name": "storeAlert",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "uint256", "name": "_id", "type": "uint256"}],
                "name": "getAlert",
                "outputs": [
                    {"internalType": "string", "name": "", "type": "string"},
                    {"internalType": "string", "name": "", "type": "string"},
                    {"internalType": "bool", "name": "", "type": "bool"},
                    {"internalType": "uint256", "name": "", "type": "uint256"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "getAlertCount",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "getRecentAlerts",
                "outputs": [
                    {
                        "components": [
                            {"internalType": "uint256", "name": "id", "type": "uint256"},
                            {"internalType": "string", "name": "alertType", "type": "string"},
                            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
                            {"internalType": "string", "name": "latitude", "type": "string"},
                            {"internalType": "string", "name": "longitude", "type": "string"},
                            {"internalType": "bool", "name": "deforestation", "type": "bool"}
                        ],
                        "internalType": "struct DeforestationTracker.Alert[]",
                        "name": "",
                        "type": "tuple[]"
                    }
                ],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        # Initialize contract
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.contract_abi)
        
        # Get account from private key
        self.account = self.w3.eth.account.from_key(self.private_key)
        print(f"Using account: {self.account.address}")
    
    def store_deforestation_alert(self, latitude, longitude, deforestation_score):
        """
        Store simplified deforestation alert in the blockchain
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            deforestation_score: Score from the model (0-1)
            
        Returns:
            dict: Transaction details or error message
        """
        try:
            # Determine status based on deforestation score
            is_deforestation = deforestation_score > 0.4
            alert_type = "DEFORESTED" if is_deforestation else "FOREST"
            
            if not is_deforestation:
                return {"status": "skipped", "message": "Area classified as forest, not storing in blockchain"}
            
            # Convert coordinates to strings
            lat_str = str(latitude)
            lon_str = str(longitude)

            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            # Estimate gas for the transaction
            gas_estimate = self.contract.functions.storeAlert(
                alert_type,
                lat_str,
                lon_str,
                is_deforestation
            ).estimate_gas({"from": self.account.address})
            
            # Build the transaction
            txn = self.contract.functions.storeAlert(
                alert_type,
                lat_str,
                lon_str,
                is_deforestation
            ).build_transaction({
                'chainId': 11155111,  # Sepolia chain ID
                'gas': int(gas_estimate * 1.2),
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce,
            })
            
            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(txn, private_key=self.private_key)
            txn_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash, timeout=120)
            
            return {
                "status": "success",
                "transaction_hash": receipt.transactionHash.hex(),
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "timestamp": int(time.time())
            }
            
        except Exception as e:
            print(f"Error storing alert in blockchain: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_recent_alerts(self):
        """Get the most recent alerts from the blockchain"""
        try:
            return self.contract.functions.getRecentAlerts().call()
        except Exception as e:
            print(f"Error getting recent alerts: {str(e)}")
            return []
    
    def get_alert_count(self):
        """Get the total number of alerts stored"""
        try:
            return self.contract.functions.getAlertCount().call()
        except Exception as e:
            print(f"Error getting alert count: {str(e)}")
            return 0