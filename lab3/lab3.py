import socket
import threading
import time
import random
import sys
import logging

# Define a custom formatter to handle milliseconds and align thread names
class CustomFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        record_time = self.converter(record.created)
        formatted_time = time.strftime("%M:%S", record_time)
        # Add milliseconds
        return f"{formatted_time}.{int(record.msecs):03d}"

    def format(self, record):
        # Ensure the thread name has a fixed width of 15 characters (padded or truncated)
        record.threadName = f"{record.threadName[:17]:<17}"  # Pad or truncate to 15 chars
        return super().format(record)

# Set up the logger with the custom formatter
formatter = CustomFormatter(
    fmt="%(asctime)s\t%(message)s"
)

handler = logging.StreamHandler()
handler.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)


# Color codes for nicer output
COLOR_RESET = "\033[0m"
COLOR_FOLLOWER = "\033[94m"    # Blue
COLOR_CANDIDATE = "\033[93m"   # Yellow
COLOR_LEADER = "\033[92m"      # Green
COLOR_EVENT = "\033[96m"       # Cyan (for internal events)
COLOR_ERROR = "\033[91m"       # Red

# node states:
FOLLOWER = "FOLLOWER"
CANDIDATE = "CANDIDATE"
LEADER = "LEADER"

# types of messages:
MSG_REQUEST_VOTE = "REQUEST_VOTE"
MSG_VOTE = "VOTE"
MSG_HEARTBEAT = "HEARTBEAT"


class Node:
    def __init__(self, node_id, cluster, base_port=5000):
        self.node_id = node_id
        self.cluster = cluster
        self.port = base_port + node_id
        self.state = FOLLOWER
        self.current_term = 0
        self.voted_for = None
        self.leader_id = None

        self.election_deadline = 0
        self.reset_election_timeout()

        self.heartbeat_interval = 1.0

        self.votes_received = 0

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", self.port))
        self.sock.settimeout(0.2)

        # thread for receiving messages
        self.alive = True
        self.listener_thread = threading.Thread(target=self.listen)
        self.listener_thread.start()

        # thread for main logic (timers, chagning node state)
        self.logic_thread = threading.Thread(target=self.run)
        self.logic_thread.start()

    def log(self, message, color=COLOR_RESET):
        logger.info(f"{color}[Node {self.node_id} | Term {self.current_term} | {self.state}] {message}{COLOR_RESET}")

    def reset_election_timeout(self):
        self.election_deadline = time.time() + random.uniform(2.5, 4.0)

    def listen(self):
        while self.alive:
            try:
                data, addr = self.sock.recvfrom(4096)
                msg = data.decode('utf-8')
                self.handle_message(msg)
            except socket.timeout:
                pass
            except Exception as e:
                self.log(f"Error receiving: {e}", COLOR_ERROR)

    def handle_message(self, msg):
        parts = msg.split("|")
        msg_type = parts[0]

        if msg_type == MSG_REQUEST_VOTE:  # REQUEST_VOTE|term|candidate_id
            term = int(parts[1])
            candidate_id = int(parts[2])
            self.on_request_vote(term, candidate_id)

        elif msg_type == MSG_VOTE:  # VOTE|term|voter_id|vote_granted
            term = int(parts[1])
            voter_id = int(parts[2])
            vote_granted = (parts[3] == "True")
            self.on_vote_response(term, voter_id, vote_granted)

        elif msg_type == MSG_HEARTBEAT:  # HEARTBEAT|term|leader_id
            term = int(parts[1])
            leader_id = int(parts[2])
            self.on_heartbeat(term, leader_id)

    def run(self):
        while self.alive:
            now = time.time()

            if self.state == FOLLOWER:
                if now >= self.election_deadline:
                    self.become_candidate()

            elif self.state == CANDIDATE:
                # if we're candidate but we haven't become leader by the end of election - become candidate (restart election)
                if now >= self.election_deadline:
                    self.become_candidate()

            elif self.state == LEADER:
                # leader is supposed to send heartbeats
                if now >= self.election_deadline:
                    if random.randint(1, 100) > 40: # simulate network issues
                        self.send_heartbeat()
                    # reset deadline to next heartbeat send
                    self.election_deadline = now + self.heartbeat_interval

            time.sleep(0.1)

    def become_candidate(self):
        self.state = CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.votes_received = 1  # voting for itself
        self.log("becoming candidate and starting an election", COLOR_CANDIDATE)
        self.reset_election_timeout()
        self.request_votes()

    def become_leader(self):
        self.state = LEADER
        self.leader_id = self.node_id
        self.log("became leader!", COLOR_LEADER)
        self.send_heartbeat()

    def become_follower(self, term):
        self.state = FOLLOWER
        self.current_term = term
        self.voted_for = None
        self.leader_id = None
        self.log("becoming follower", COLOR_FOLLOWER)
        self.reset_election_timeout()

    def send(self, node_id, msg):
        addr = ("127.0.0.1", 5000 + node_id)
        self.sock.sendto(msg.encode('utf-8'), addr)

    def broadcast(self, msg):
        for n in self.cluster:
            if n != self.node_id:
                self.send(n, msg)

    def request_votes(self):
        # sending REQUEST_VOTE to other nodes
        msg = f"{MSG_REQUEST_VOTE}|{self.current_term}|{self.node_id}"
        self.broadcast(msg)

    # handle vote requests from other candidates
    def on_request_vote(self, term, candidate_id):
        # candidate's term < current term -> reject
        if term < self.current_term:
            return

        if term > self.current_term:
            self.become_follower(term)

        # if we havent' voted or already voted for this cnadidate
        if (self.voted_for is None or self.voted_for == candidate_id):
            self.voted_for = candidate_id
            self.reset_election_timeout()
            self.send_vote(candidate_id, True)
            self.log(f"voted for candidate {candidate_id}", COLOR_EVENT)
        else:
           # we've already voted for someone else
            self.send_vote(candidate_id, False)

    def send_vote(self, candidate_id, vote_granted):
        msg = f"{MSG_VOTE}|{self.current_term}|{self.node_id}|{vote_granted}"
        self.send(candidate_id, msg)

    def on_vote_response(self, term, voter_id, vote_granted):
        if self.state != CANDIDATE:
            return
        if term < self.current_term:
            return

        if vote_granted:
            self.votes_received += 1
            self.log(f"received vote from {voter_id} (total: {self.votes_received})", COLOR_EVENT)
            # check if majority
            if self.votes_received > len(self.cluster)//2:
                self.become_leader()

    def send_heartbeat(self):
        if self.state == LEADER:
            msg = f"{MSG_HEARTBEAT}|{self.current_term}|{self.node_id}"
            self.broadcast(msg)
            self.log("sending heartbeat", COLOR_EVENT)

    def on_heartbeat(self, term, leader_id):
        # if term > current_term, follow this leader
        if term > self.current_term:
            self.become_follower(term)
        self.leader_id = leader_id
        if self.state != FOLLOWER:
            self.become_follower(term)
        else:
            self.log(f"heartbeat received from Leader {leader_id}", COLOR_EVENT)
            self.reset_election_timeout()


def main():
    cluster = [0, 1, 2]
    nodes = []
    for nid in cluster:
        n = Node(nid, cluster)
        nodes.append(n)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("shutting down...")
        for n in nodes:
            n.alive = False
        sys.exit(0)


main()
