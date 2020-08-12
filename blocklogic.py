from hashlib import sha256
import json
import time
import multiprocessing
import time
import numpy as np

class Block:
    def __init__(
        self, depth, transactions, timestamp,
        previous_hash, nonce=0
    ):
        self.depth = depth
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce

    def compute_hash(self):
        '''
        A function that return the hash of the block contents.
        '''
        block_str = json.dumps(self.__dict__, sort_keys=True)
        return sha256(block_str.encode()).hexdigest()

    def __eq__(self, other):
        '''
        Overloading the equality operator
        '''
        return self.__dict__ == other.__dict__

class Blockchain:
    '''
    Blockchain class;
    Inspired from IBM version at the moment.
    '''

    difficulty = 4
    block_capacity = 3

    def __init__(self):
        '''
        Choose initial difficulty and 
        create the genesis block

        [1]     They are the orphans and stale blocks
                It's a list of lists where we also
                store the block leading to the orphan.
                That block is stored multiple time (also
                in the longest chain)
        '''
        # Transactions to be mined
        self.outstanding_transactions = []
        # Consensus chain and extensions, see [1]
        self.chain = []
        self.extensions = []
        # Create genesis block
        self.create_genesis_block()

    def create_genesis_block(self):
        """
        A function to generate genesis block and appends it to
        the chain. The block has index 0, previous_hash as 0, and
        a valid hash.
        """
        genesis_block = Block(0, [], 0, "0")
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)

    @property
    def last_block(self):
        return self.chain[-1]

    def add_block_longest(self, block, proof):
        """
        Attempt to add a block after checking the validity of 
        the provided proof. Append to longest chain.
        """
        # Reject if previous hash not accurate
        if self.last_block.hash != block.previous_hash:
            return False
        # Reject if proof is not valid hash
        if not Blockchain.is_valid_proof(block, proof):
            return False
        block.hash = proof
        self.chain.append(block)
        return True

    def add_block(
        self, block, proof, base_block
    ):
        """
        Attempt to add a block after checking the validity of 
        the provided proof. Append to longest chain.
        :param base_block: the base block receiving the potential new block
        
        [1]     If base_block is not last block in longest chain, 
                check all extensions for their last block. If again, none
                of the extensions have the base_block as their last, create
                another extension. You could have nested extensions because of
                this, but shouldn't care.
        """
        # If the base block is the last block 
        # in longest chain, just use regular add
        if base_block == self.last_block:
            return self.add_block_longest(block, proof)
        
        # Previous hash should be accurate, reject otherwise
        if base_block.hash != block.previous_hash:
            return False    
        # Reject if proof is not valid hash of block
        if not Blockchain.is_valid_proof(block, proof):
            return False
        # If checks passed, update the block's hash
        block.hash = proof

        # Check all extensions for the base block
        # See add_block.[1] 
        for ext_idx in range(self.extensions):
            # Check each last block in extensions
            if base_block == self.extensions[ext_idx][-1]:
                # If found, proceed there
                self.extensions[ext_idx].append(block)
                return True
        # If not found there, create extension
        self.extensions.append([base_block, block])
        return True

    def internal_consensus(self):
        '''
        Method to update to longest chain using possibly
        larger extensions. So it checks if any extension
        is longer than current chain. In case of a change,
        the tail of the current chain becomes a new extension.
        
        [1]     If any update happens, return True and stop
                since another one is impossible. This is because
                we are calling this at each mine, so changes are
                continuously updated.
        '''
        for ext in self.extensions:
            if ext[-1].depth > self.last_block.depth:
                fork_depth = ext[0].depth
                # Create new extension with chain to be
                # dumped
                self.extensions.append(
                    self.chain[fork_depth:]
                )
                # Remove and store chain tail until 
                # depth of fork node, then add extension
                # tail to now have longest chain
                while self.last_block.depth >= fork_depth:
                    self.chain.pop()
                self.chain = self.chain + ext
                # See internal_consensus.[1]
                return True
        # If no internal consensus update, return False
        return False

    @staticmethod
    def proof_of_work(block, work_time = None):
        """
        Do proof of work and stop after a work_time seconds.
        :param starting_nonce: can store progress
        :param work_time: storing progress requires early stopping
            and we're using a potentially pre-set time
        """
        # Parse work_time None to inf
        if work_time is None:
            work_time = float('inf')
        start = time.time()
        # Start from 0, flexibility here to be debated
        block.nonce = 0
        # Do computational work
        computed_hash = block.compute_hash()
        while not computed_hash.startswith('0' * Blockchain.difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()
            # Return if out of time
            if (time.time() - start) > work_time:
                return
        # Return good hash
        return computed_hash

    def add_new_transaction(self, transaction):
        self.outstanding_transactions.append(transaction)

    def remove_front_transactions(self):
        self.outstanding_transactions = self.outstanding_transactions[Blockchain.block_capacity:]

    def get_outstanding_transactions(self):
        return self.outstanding_transactions

    @classmethod
    def is_valid_proof(cls, block, block_hash):
        """
        Check if block_hash is valid hash of block and satisfies
        the difficulty criteria.
        """
        return (block_hash.startswith('0' * Blockchain.difficulty) and
                block_hash == block.compute_hash())
