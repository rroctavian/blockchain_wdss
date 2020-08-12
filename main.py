# General imports
import numpy as np
import multiprocessing
from multiprocessing.pool import ThreadPool
import threading
import time
import json
import re
from copy import deepcopy

# Own imports
from blocklogic import Block, Blockchain
from blockgraph import FullNode, Client, full_nodes, clients

def format_block_output(blk, max_line=35):
    '''
    Truncate the hashes a bit and 
    append spaces to allow tabulation
    for column-like display
    '''
    # Return empty block json if None
    if not blk:
        tx_lim = Blockchain.block_capacity
        return(["".ljust(max_line) for _ in range(9 + tx_lim)])
    # Do the formatting work
    blk_dict = deepcopy(blk.__dict__)
    hash_lim = Blockchain.difficulty + 10
    blk_dict["hash"] = str(blk_dict["hash"])[:hash_lim]
    blk_dict["previous_hash"] = str(blk_dict["previous_hash"])[:hash_lim]
    blk_json = json.dumps(
        blk_dict,
        sort_keys=True,
        indent=2
    )
    blk_json = re.split("\n", blk_json)
    for idx in range(len(blk_json)):
        blk_json[idx] = blk_json[idx].ljust(max_line)
    return blk_json

if __name__=='__main__':

    # Creating full nodes
    n1 = FullNode()
    n2 = FullNode()
    n3 = FullNode()
    n4 = FullNode()

    # Creating one client, e.g. wallet provider
    c1 = Client()

    # Request some transactions to be made by client
    tx_ids = np.random.choice(1000, 100)
    for tx_id in tx_ids:
        c1.send_transaction(f"Tx #{tx_id:04}")

    # Full nodes get to work
    args = (5,5) # (sprints, seconds)
    t1 = threading.Thread(target=n1.longest_mine, args=args)
    t2 = threading.Thread(target=n2.longest_mine, args=args)
    t3 = threading.Thread(target=n3.longest_mine, args=args)
    t4 = threading.Thread(target=n4.longest_mine, args=args)
    
    # Start mining the previously added transactions
    t1.start()
    t2.start()
    t3.start()
    t4.start()

    # Join the threads before any I/O jobs
    t1.join()
    t2.join()
    t3.join()
    t4.join()

    # Console log the chain lengths
    print("N1 chain length:\t" + str(len(n1.blockchain.chain)))
    print("N2 chain length:\t" + str(len(n2.blockchain.chain)))
    print("N2 chain length:\t" + str(len(n3.blockchain.chain)))
    print("N2 chain length:\t" + str(len(n4.blockchain.chain)))
    
    nodes = []
    nodes.append(n1)
    nodes.append(n2)
    nodes.append(n3)
    nodes.append(n4)

    # Format output nicely in .txt file
    with open("blocks_result.txt", 'w') as f:

        for n in range(len(nodes)):
            print(f"Node {n}".ljust(35), end="\t|\t", file=f)
        print("\n", end="", file=f)

        max_length = len(nodes[0].blockchain.chain)
        for node in nodes[1:]:
            max_length = max(max_length, len(node.blockchain.chain))

        # Print columns of blocks
        for row in range(max_length):
            # List of lines for all blocks on the same row/depth
            blk_lists = []
            for node in nodes:
                if len(node.blockchain.chain) <= row:
                    blk_lists.append(
                        format_block_output(blk=None)
                    )
                else:
                    blk_lists.append(
                        format_block_output(node.blockchain.chain[row])
                    )
            # Print each line by going through all nodes each time
            blk_num_lines = 9 + Blockchain.block_capacity
            for line_num in range(blk_num_lines):
                for node_idx in range(len(nodes)):
                    try:
                        print(blk_lists[node_idx][line_num].ljust(35), end="\t|\t", file=f)
                    except:
                        print("".ljust(35), end="\t|\t", file=f)
                print("\n", end="", file=f)
            # Append horizontal space
            print("\n", end="", file=f)

        # Horizontal space and _ separator line
        print("".join(["_" for _ in range(43 * len(nodes))]), file=f)
        
        # Print transaction leftovers
        txss = [deepcopy(node.blockchain.outstanding_transactions) for node in nodes]
        for txs in txss:
            print(
                str(len(txs)).ljust(35),
                end="\t|\t",
                file=f
            )
        print("\n", end="", file=f)
        
        max_txs = len(txss[0])
        for txs in txss[1:]:
            max_txs = max(max_txs, len(txs))
        for row in range(max_txs):
            for txs in txss:
                if len(txs) <= row:
                    print(
                        "".ljust(35),
                        end="\t|\t",
                        file=f
                    )
                else:
                    print(
                        txs[row].ljust(35),
                        end="\t|\t",
                        file=f
                    )
            print("\n", end="", file=f)