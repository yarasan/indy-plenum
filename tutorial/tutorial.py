"""
This tutorial illustrates a client request round trip with a simple consensus
pool.
"""
from tempfile import TemporaryDirectory

from ioflo.base.consoling import getConsole

from plenum.client.client import Client
from plenum.common.looper import Looper
from plenum.server.node import Node
from plenum.test.malicious_behaviors_node import faultyReply, makeNodeFaulty

console = getConsole()
console.reinit(verbosity=console.Wordage.terse)

"""
Nodes persist keys when bootstrapping to other nodes and reconnecting using an
ephemeral temporary directory when proving a concept is a nice way to keep
things tidy.
"""
with TemporaryDirectory() as tmpdir:

    """
    Looper runs an asynchronous message loop that services the nodes and client.
    It's also a context manager, so it cleans up after itself.
    """
    with Looper(debug=False) as looper:

        """
        A node registry is a dictionary of Node names and their IP addresses
        and port numbers.
        """
        nodeReg = {
            'Alpha': ('127.0.0.1', 7560),
            'Beta': ('127.0.0.1', 7562),
            'Gamma': ('127.0.0.1', 7564),
            'Delta': ('127.0.0.1', 7566)}

        """
        Create a node called Alpha
        """
        alpha = Node('Alpha', nodeReg, basedirpath=tmpdir)

        """
        Add the Alpha node to the looper, so it can be serviced.
        """
        looper.add(alpha)

        """
        Start key sharing among nodes. Key sharing is a way to bootstrap a
        consensus pool when you don't want to manually construct keys
        beforehand. See the github wiki for more details on key sharing.
        """
        alpha.startKeySharing()

        """
        Do the same process for the other nodes. Ordinarily, we would never have
        more than one node on a machine, but this is for demonstration purposes.
        """
        beta = Node('Beta', nodeReg, basedirpath=tmpdir)
        looper.add(beta)
        beta.startKeySharing()

        gamma = Node('Gamma', nodeReg, basedirpath=tmpdir)
        looper.add(gamma)
        gamma.startKeySharing()

        delta = Node('Delta', nodeReg, basedirpath=tmpdir)
        looper.add(delta)
        delta.startKeySharing()

        """
        Give the nodes time to come up, find each other, share long-term keys,
        and establish connections.
        """
        looper.runFor(5)

        """
        The client has a slightly different node registry than the nodes. The
        Nodes have two network interfaces, one for other nodes, and one for
        client. This registry points to the nodes' client-facing interfaces.
        """
        cliNodeReg = {
            'AlphaC': ('127.0.0.1', 7561),
            'BetaC': ('127.0.0.1', 7563),
            'GammaC': ('127.0.0.1', 7565),
            'DeltaC': ('127.0.0.1', 7567)}

        """
        A bi-directional connection is made from the client. This is the ip
        address and port for the client's interfact to the nodes.
        """
        client_addr = ("127.0.0.1", 8000)

        """
        Create a client.
        """
        clientName = "my_client_id"
        client = Client(name=clientName,
                        ha=client_addr,
                        nodeReg=cliNodeReg,
                        basedirpath=tmpdir)
        looper.add(client)

        """
        A client signs its requests. By default, a simple yet secure signing
        mechanism is created for a client.
        """
        idAndKey = client.getSigner().identifier, client.getSigner().verkey

        """
        A client's signature verification key must be bootstrapped out of band
        into the consensus pool. For demonstration, we'll add it directly to
        each node.
        """
        for node in alpha, beta, gamma, delta:
            node.clientAuthNr.addClient(*idAndKey)

        """
        We give the client a little time to connect
        """
        looper.runFor(3)

        """
        Create a simple message.
        """
        msg = {'life_answer': 42}

        """
        And submit it to the pool.
        """
        request, = client.submit(msg)

        """
        Allow some time for the request to be executed.
        """
        looper.runFor(3)

        """
        Let's get the reply.
        """
        reply, status = client.getReply(request.reqId)

        """
        Check the reply and see if consensus has been reached.
        """
        print("Reply: {}\n".format(reply))
        print("Status: {}\n".format(status))

        """
        See the reply details of a request.
        """
        client.showReplyDetails(request.reqId)

        """
        As we are using 4 nodes, we have an f-value of 1, which means that
        consensus can be still achieved with one faulty node. In this example,
        we're going to cause Beta to be malicious, altering a client's request
        before propagating to other nodes.
        """
        makeNodeFaulty(beta, faultyReply)

        """
        Create a new message.
        """
        msg = {"type": "sell", "amount": 101}

        """
        And submit it to the pool.
        """
        request2, = client.submit(msg)

        """
        Allow time for the message to be executed.
        """
        looper.runFor(10)

        """
        Observe that consensus is still reached with one node replying with a different response.
        """
        reply, consensusReached = client.getReply(request2.reqId)
        print("Reply for the request: {}\n".format(reply))
        print("Consensus Reached?: {}\n".format(consensusReached))

        client.showReplyDetails(request2.reqId)
