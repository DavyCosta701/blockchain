import hashlib
import time
import json
from textwrap import dedent
from time import time
from uuid import uuid4

from flask import Flask, jsonify, request


class Blockchain(object):

    def __init__(self):
        self.chain = []
        self.current_transactions = []

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

    @staticmethod
    def vaild_proof(last_proof, proof):
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


# Inicializa o node
app = Flask(__name__)

# Gera um endereço global único para o node
node_identifier = str(uuid4()).replace('-', '')

# Instancia da blockchain
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    #Rodamos o Proof of work para pegarmos a proxima prova
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof(last_proof=last_proof)

    #Recebemos uma recompensa por acharmos a prova
    #O sender é "0" para sinalizarmos que o node foi minerado
    blockchain.new_transaction(sender="0", recipient=node_identifier, amount=1)

    #Forja um novo bloco, adicionando-o a chain
    previous_hash = blockchain.get_hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "Novo Bloco de Pcoin minerado",
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
    return "PCoin"


if (__name__) == '__main__':
    app.run(host='0.0.0.0', port=500)
