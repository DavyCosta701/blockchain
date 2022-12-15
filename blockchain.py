import hashlib
import time
import json
from textwrap import dedent
from time import time
from uuid import uuid4
from urllib.parse import urlparse
from flask import Flask, jsonify, request


class Blockchain(object):

    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()

        # Cria o GenesisBlock (seed) para inicializar a blockchain
        self.new_block(previous_hash=1, proof=100)

    def new_block(self, proof, previous_hash=None):
        """
        Cria um novo bloco na blockchain
        :param proof: <int> A prova dada pelo algoritimo 
        :param previous_hash: (Opcional) <str> Hash anterior, usado na prova do blockchain
        :return: <dicionario> Novo bloco
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or None

        }

        # Reseta o numero de transações ativas
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """
        Cria uma nova transação que irá para o próximo bloco minerado
        :param sender: <str> Endereço para quem irá receber 
        :param recipient: <str> Endereço de quem irá enviar
        :param amount: <int> Quantidade a enviar
        :return: <int> Índice que irá ser inserido no bloco
         """
        self.current_transactions.append(
            {
                'sender': sender,
                'recipient': recipient,
                'amount': amount
            }
        )
        return self.last_block['index'] + 1

    @staticmethod
    def get_hash(bloco):
        """
        Cria um hash SHA256 de um bloco
        :param bloco: Insere o block 
        :return: <str> Retorna um hash do bloco
        """
        # Ordenando o json para não termos hashes inconsistentes
        block_String = json.dumps(bloco, sort_keys=True).encode()
        return hashlib.sha256(block_String).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof(self, last_proof):
        """
        Algorítimo para prova da mineração. O funcionamento é simples, um número encontrado onde, se hashed com a prova anterior, revela uma nova prova com 4 (0)
        no começo do hash.
        :param last_proof: Última prova de cash
        :return: <int>
        """

        proof = 0
        while self.vaild_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Valida a prova. 
        O hash gerado por (last_proof, proof) começa com 4 zeros?
        :param last_proof: Última prova de mineração.
        :param proof: Prova atual.
        :return: <bool>
        """

        guess = f'{last_proof, proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def register_node(self, address):
        """
        Registra um novo node na lista de nodes
        :param adress: Endereço do node. Ex.: 'http://192.168.0.102:500'
        :return: void
        """

        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def validate_chain(self, chain):
        """
        Datermina se um blockchain é valido. O maior blockchain é dado como valid
        :param chain: <list> Blockchain
        :return: <bool> True se a chain é valida e false se não
        """

        last_block = chain[0]
        index = 1

        while index < len(chain):
            block = chain[index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n--------------------------------\n")
            # Checa se o hash do bloco está correto
            if block['previous_hash'] != self.get_hash(last_block):
                return False

            # Checa se o Proof of Work está correto
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            index += 1

        return True

    def consensus(self):
        """
        Algorítimo de consenso, para resolver conflitos entre os nodes. Substitui a nossa chain com a maior da network.
        :return: <bool> True se a chain for substituida, False se não
        """

        neighbor = self.nodes
        new_chain = None

        # Procuramos por chains maiores que as nossas
        max_chain = len(self.chain)

        # Pega e verifica as chains de todos os nodes vizinhos
        for n in neighbor:
            response = request.get(f'http://{n}/chain')

            if response.status_code == 200:
                lenght = response.json()['lenght']
                chain = response.json()['chain']

                # Checa se a chain é a maior e se ela é válida
                if lenght > max_chain & self.validate_chain(lenght):
                    new_chain = chain

        # Repõe a chain se encontrarmos uma chain válida e maior que a nossa
        if new_chain:
            self.chain = new_chain
            return True


# Inicializa o node
app = Flask(__name__)

# Gera um endereço global único para o node
node_identifier = str(uuid4()).replace('-', '')

# Instancia da blockchain
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    # Rodamos o Proof of work para pegarmos a proxima prova
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof(last_proof=last_proof)

    # Recebemos uma recompensa por acharmos a prova
    # O sender é "0" para sinalizarmos que o node foi minerado
    blockchain.new_transaction(sender="0", recipient=node_identifier, amount=1)

    # Forja um novo bloco, adicionando-o a chain
    previous_hash = blockchain.get_hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "Novo Bloco de Wake up Your E-Hero minerado",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'prev_hash': block['previous_hash'],
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Checa se os campos requeridos estão nas informações POSTadas
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Valores Faltando', 400

    # Criando a transação
    index = blockchain.new_transaction(
        values['sender'], values['recipient'], values['amount'])

    response = {'message': f'A transação será adicionada ao bloco {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200


@app.route('/', methods=['GET'])
def pag_inicial():
    return "<center>E-Hero - Chaos Neos</center>"


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error, dê uma lista de nodes válida", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': "Novo(s) node(s) adicionado(s)",
        'total_nodes': list(blockchain.nodes)

    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.consensus()

    if replaced:
        response = {
            'message': 'Conflito resolvido',
            'new_chain': blockchain.chain
        }
    
    else:
        response = {
            'message': 'Chain atual já é autoritativa',
            'chain': blockchain.chain
        }
    
    return jsonify(response), 200


if (__name__) == '__main__':
    app.run(host='0.0.0.0', port=500)
