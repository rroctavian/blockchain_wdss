import random
import time
import threading
from copy import deepcopy
from blocklogic import Block, Blockchain

'''
Network management area
'''

# Network participants
full_nodes = []
clients = []
# Thread lock
lock = threading.Lock()

def register_transaction(tx):
    '''
    Connect with all full nodes and
    send them the new transaction
    '''
    with lock:
        for node in full_nodes:
            node.blockchain.add_new_transaction(tx)
        return True

'''
Network participant classes
'''

class Client:
    '''
    Sends transactions.
    '''
    def __init__(self):
        pass

    def send_transaction(self, tx):
        '''
        FIXME: (just an idea, not necessary)
        Send transaction to network. Currently dummy txs,
        no financial data, therefore cannot fail to have
        enough funds. Always return True for now.
        '''
        return register_transaction(tx)

class FullNode:
    '''
    Stores all available block data and
    also mines. They are mining full nodes.
    Currently we do not support stand-alone
    miners.
    '''
    def __init__(self):
        self.blockchain = self.download_blockchain()
        self.register_on_network()

    def register_on_network(self):
        '''
        Register on network
        '''
        with lock:
            full_nodes.append(self)

    def send_chain(self):
        '''
        Allow requests for longest chain
        '''
        return self.blockchain.chain

    def download_blockchain(self):
        '''
        Function to download a consensus chain first
        time the Full Node joins the network.
        '''
        with lock:
            # Number of existing full nodes in network
            num_nodes = len(full_nodes)
            # If empty network, we're first node
            # so just create a brand new blockchain
            if num_nodes == 0:
                return Blockchain()
            # Else, fetch blocks from existing node
            node_idx = random.randint(0, num_nodes-1)
            return deepcopy(full_nodes[node_idx].blockchain)

    def match_outstanding_transactions(self, consensus_bc):
        '''
        Take a consensus chain and update self.blockchain's 
        outstanding transactions, returning the good list.
        Assuming consensus_chain is always longer.
        :param consensus_bc: of class Blockchain
        '''
        # If shorter consensus, complain
        if len(self.blockchain.chain) >= len(consensus_bc.chain):
            raise Exception(
                "Trying to match transactions with shorter \
                 or equal length consensus chain."
            )
        # List of good transactions
        matched_tx = self.blockchain.outstanding_transactions
        # Find out what's the most recent common block
        # Offset positions by how many blocks consensus is longer
        offset = len(consensus_bc.chain) - len(self.blockchain.chain)
        local_pos = -1
        other_pos = -1-offset
        while self.blockchain.chain[local_pos] != consensus_bc.chain[other_pos]:
            local_pos = local_pos - 1
            other_pos = other_pos - 1
        # We know the most recent common block
        # Want to add back the tx executed on our chain
        add_back_tx = []
        for local_idx in range(local_pos+1, 0):
            for tx in self.blockchain.chain[local_idx].transactions:
                add_back_tx.append(tx)
        matched_tx = matched_tx + add_back_tx
        # Want to remove the tx execute on outside consensus chain
        remove_tx = []
        for other_idx in range(other_pos+1, 0):
            for tx in consensus_bc.chain[other_idx].transactions:
                remove_tx.append(tx)
        for tx in remove_tx:
            matched_tx.remove(tx)
        # Have the matched transactions ready
        return matched_tx
        
    def external_consensus(self):
        '''
        Check other nodes in the network for the
        longest internal consensus chain
        '''
        with lock:
            # Current depth of own chain
            curr_depth = self.blockchain.last_block.depth
            # Max depth found already
            max_depth = -1
            # Node to request form
            request_node = None
            for node in full_nodes:
                if (
                    node.blockchain.last_block.depth > curr_depth and
                    node.blockchain.last_block.depth > max_depth
                ):
                    request_node = node
                    max_depth = node.blockchain.last_block.depth
            # Set our chain to request_node's chain
            if request_node is not None:
                # Update transactions to not lose own tx's
                self.blockchain.outstanding_transactions = self.match_outstanding_transactions(
                        request_node.blockchain
                    )
                self.blockchain.chain = deepcopy(request_node.blockchain.chain)
                return True
            # Return False if nothing changed
            return False

    def longest_mine(
        self, num_sprints = 5, sprint_time = 10
    ):
        '''
        Function to do mining work to longest chain
        and stop when there's news about a longer chain.
        Runs for a certain amout of time, default 60s.
        Current version does short mining sprints with
        broadcast reading in between.
        Returns number of successes during work.
        '''
        # If non-positive number of sprints, no work needed
        if num_sprints <= 0:
            return 0
        # Establish initial consensus with network
        self.external_consensus()
        # Do nothing if no trasactions
        if not self.blockchain.outstanding_transactions:
            return 0
        # Choose transactions to mine, call it bucket
        mine_bucket = self.blockchain.get_outstanding_transactions()[
            :Blockchain.block_capacity
        ]
        # Create new block on top of base block
        new_block = Block(
            depth=self.blockchain.last_block.depth + 1,
            transactions=mine_bucket,
            timestamp=time.time(),
            previous_hash=self.blockchain.last_block.hash
        )
        # Do proof of work in sprints
        proof = None
        for spr in range(num_sprints):
            # Before sprint, check for external consensus
            # and do that every sprint
            if self.external_consensus():
                # If updated blockchain, start mining again
                # for the remaining time with the fresh consensus
                return self.longest_mine(
                    num_sprints=num_sprints-spr,
                    sprint_time=sprint_time
                )
            # Perform PoW sprint
            proof = Blockchain.proof_of_work(
                new_block, work_time=sprint_time
            )
            # If proof was found, add block and return True
            if proof:
                add_res = self.blockchain.add_block(
                    new_block, proof, 
                    self.blockchain.last_block
                )
                # Only remove transactions once block was successful
                if add_res:
                    self.blockchain.remove_front_transactions()
                # In case fork becomes larger, consensus
                self.blockchain.internal_consensus()
                # Since already
                return (1 + self.longest_mine(
                    num_sprints=num_sprints-spr-1,
                    sprint_time=sprint_time
                ))
        # If nothing found
        return 0