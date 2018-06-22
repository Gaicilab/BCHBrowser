import os

from flask import current_app
from flask import render_template, Blueprint, send_from_directory
from decimal import Decimal
from collections import deque

import bitcoin.core as core
import bitcoin.base58 as base58

from lincoln import create_app, db, coinserv
from lincoln.models import Block, Transaction, Output

from . import models as m
from . import db, root
import bitcoin.core.script as op
import bitcoin.core.serialize as serialize

import time
import datetime

main = Blueprint('main', __name__)


@main.route('/address/<address>')
def address(address):
    pubkey_hash = base58.decode(address)
    # Strip off the version and checksum, database doesn't store them
    pubkey_hash = pubkey_hash[1:-4]
    outputs = (m.Output.query.options(db.joinedload('spent_tx'),
                                      db.joinedload('origin_tx')).
               filter_by(dest_address=pubkey_hash))
    return render_template('address.html', outputs=outputs, address=address)


@main.route('/block/<hash>')
def block(hash):
    block = m.Block.query.filter_by(hash=core.lx(hash)).first()
    return render_template('block.html', block=block)


@main.route('/transaction/<hash>')
def transaction(hash):
    transaction = m.Transaction.query.filter_by(txid=core.lx(hash)).first()
    return render_template('transaction.html', transaction=transaction)


@main.route('/transactions')
def transactions():
    transactions = m.Transaction.query.order_by(m.Transaction.id.desc()).limit(100)
    return render_template('transactions.html', transactions=transactions)


@main.route('/')
@main.route('/blocks')
def blocks():
    blocks = m.Block.query.order_by(m.Block.height.desc()).limit(100)
    return render_template('blocks.html', blocks=blocks)


@main.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(root, 'static'),
        'favicon.ico', mimetype='image/vnd.microsoft.icon')

@main.route('/sync')
def sync():
    # Get the most recent block in our database
    highest = Block.query.order_by(Block.height.desc()).first()
    if highest:
        highest_hash = coinserv.getblockhash(highest.height)

    # This means the coinserver and local index are on different chains
    #if highest_hash != highest.hash:

    server_height = coinserv.getinfo()['blocks']
    server_hash = coinserv.getblockhash(server_height)

    block_times = deque([], maxlen=1000)
    information = ""
    while True:
        t = time.time()
        if not highest:
            curr_height = 0
        else:
            curr_height = highest.height + 1

        if curr_height > server_height:
            break
        else:
            curr_hash = coinserv.getblockhash(curr_height)

        block = coinserv.getblock(curr_hash)
        block_obj = Block(hash=block.GetHash(),
                          height=curr_height,
                          ntime=datetime.datetime.utcfromtimestamp(block.nTime),
                          orphan=False,
                          total_in=0,
                          total_out=0,
                          difficulty=block.difficulty,
                          algo=current_app.config['algo']['display'],
                          currency=current_app.config['currency']['code'])
        current_app.logger.info(
            "Syncing block {}".format(block_obj))
        information = "Syncing block {"+format(block_obj)+"}"

        db.session.add(block_obj)

        # all TX's in block are connectable; index
        for tx in block.vtx:
            tx_obj = Transaction(block=block_obj,
                                 txid=tx.GetHash(),
                                 total_in=0,
                                 total_out=0)
            db.session.add(tx_obj)
            current_app.logger.info("Found new tx {}".format(tx_obj))
            information = information + "\n Found new tx {"+format(tx_obj)+"}"


            for i, txout in enumerate(tx.vout):
                out_dec = Decimal(txout.nValue) / 100000000
                tx_obj.total_out += out_dec

                # Sloppy as hell destination address checking
                # ------------------------------------------------
                scr = []
                try:
                    scr = list(txout.scriptPubKey)
                except op.CScriptTruncatedPushDataError:
                    pass

                out = Output(origin_tx=tx_obj,
                             index=i,
                             amount=out_dec)
                db.session.add(out)
                # pay-to-pubkey-hash
                if (len(scr) == 5 and
                        scr[0] == op.OP_DUP and
                        scr[1] == op.OP_HASH160 and
                        scr[3] == op.OP_EQUALVERIFY and
                        scr[4] == op.OP_CHECKSIG):
                    out.type = 1
                    out.dest_address = scr[2]
                elif (len(scr) == 3 and
                      scr[0] == op.OP_HASH160 and
                      scr[2] == op.OP_EQUAL):
                    out.type = 0
                    out.dest_address = scr[1]
                elif len(scr) == 2 and scr[1] == op.OP_CHECKSIG:
                    out.type = 2
                    out.dest_address = serialize.Hash160(scr[0])
                else:
                    out.type = 3
                    current_app.logger.info("Unrecognized script {}"
                                            .format(scr))
                    information=information+"\n Unrecognized script {"+format(scr)+"}"
            db.session.flush()

            if not tx.is_coinbase():
                for txin in tx.vin:
                    obj = Output.query.filter_by(
                        origin_tx_hash=txin.prevout.hash,
                        index=txin.prevout.n).one()
                    obj.spent_tx = tx_obj
                    tx_obj.total_in += obj.amount
            else:
                tx_obj.coinbase = True

            block_obj.total_in += tx_obj.total_in
            block_obj.total_out += tx_obj.total_out

        highest = block_obj
        db.session.commit()
        block_times.append(time.time() - t)

        # Display progress information
        time_per = sum(block_times) / len(block_times)
        time_remain = datetime.timedelta(
            seconds=time_per * (server_height - curr_height))
        current_app.logger.info(
            "{:,}/{:,} {} estimated to catchup"
            .format(curr_height, server_height, time_remain))
        information = information + "\n {:"+format(curr_height)+",}/{:"+format(server_height)+"} {"+ format(time_remain) +"} estimated to catchup"


    db.session.commit()
    return information
