import random
import math
from src.client import GameClient
from src.model import GameView
from src import hide_and_seek_pb2


INF = float('inf')
PR_STAY = 10


def write(txt):
    f = open("log_opponent1.log", "a")
    f.write(txt)
    f.write('\n')
    f.close()


def convert_paths_to_adj(paths, n):

    inf = float('inf')
    adj = [[inf for j in range(n+1)] for i in range(n+1)]

    min_price = inf
    for path in paths:
        adj[path.first_node_id][path.second_node_id] = path.price
        adj[path.second_node_id][path.first_node_id] = path.price
        if path.price < min_price:
            min_price = path.price

    for i in range(n+1):
        adj[i][i] = 0

    # Price normalization: All/Min
    if min_price != 0:
        for i in range(n+1):
            for j in range(n+1):
                adj[i][j] /= min_price

    write(str(adj))
    return adj


def floyd_warshall(paths, n):

    D = convert_paths_to_adj(paths, n)

    inf = float('inf')
    for k in range(n+1):
        for i in range(n+1):
            for j in range(n+1):
                if D[i][k] < inf and D[k][j] < inf:
                    D[i][j] = min(D[i][j], D[i][k] + D[k][j])

    return D


def get_thief_starting_node(view: GameView) -> int:
    return random.randint(2, len(view.config.graph.nodes))

    # i = int(len(view.config.graph.nodes)/len(AllThieves?!))
    # st_node = random.randint(i*view.id, i*view.id+i)
    # write(str(view.id) + " -> " + str(st_node))
    # return st_node


class Phone:
    def __init__(self, client: GameClient):
        self.client = client

    def send_message(self, message):
        self.client.send_message(message)


class AI:
    def __init__(self, phone: Phone):
        self.phone = phone
        self.cost = None
        self.degrees = None

    def get_degrees(self, view: GameView) -> list:
        nodes_count = len(view.config.graph.nodes)
        degrees = [0]*(nodes_count+1)
        for n in range(1, nodes_count+1):
            for adj in range(1, nodes_count+1):
                if self.cost[n][adj] != INF:
                    degrees[n] += 1
        return degrees

    def police_count(self, node_id, team, view: GameView) -> int:
        pc = 0
        for vu in view.visible_agents:
            if (
                not vu.is_dead and
                vu.node_id == node_id and
                vu.agent_type == hide_and_seek_pb2.AgentType.POLICE and
                vu.team == team
            ):
                pc += 1
        return pc

    def thieves_count(self, node_id, team, view: GameView) -> int:
        tc = 0
        for vu in view.visible_agents:
            if (
                not vu.is_dead and
                vu.node_id == node_id and
                vu.agent_type == hide_and_seek_pb2.AgentType.THIEF and
                vu.team == team
            ):
                tc += 1
        return tc

    def pr_police(self, node_id, team_type: str, view: GameView) -> float:
        if self.degrees is None:
            self.degrees = self.get_degrees(view)

        pr = 1

        nodes_count = len(view.config.graph.nodes)
        for adj_id in range(1, nodes_count+1):
            if self.cost[node_id][adj_id] != INF:
                p_count = None
                if team_type == "same":
                    p_count = self.police_count(adj_id, view.viewer.team, view)
                else:
                    if view.viewer.team == hide_and_seek_pb2.Team.FIRST:
                        p_count = self.police_count(
                            adj_id, hide_and_seek_pb2.Team.SECOND, view)
                    else:
                        p_count = self.police_count(
                            adj_id, hide_and_seek_pb2.Team.FIRST, view)

                pr += p_count / self.degrees[adj_id]
        return pr

    def pr_theives(self, node_id, team_type: str, view: GameView) -> float:
        pr = 1

        if view.turn.turn_number not in view.config.visible_turns:
            return pr

        nodes_count = len(view.config.graph.nodes)
        for adj_id in range(1, nodes_count+1):
            if self.cost[node_id][adj_id] != INF:
                t_count = None
                if team_type == "same":
                    t_count = self.thieves_count(
                        adj_id, view.viewer.team, view)
                else:
                    if view.viewer.team == hide_and_seek_pb2.Team.FIRST:
                        t_count = self.thieves_count(
                            adj_id, hide_and_seek_pb2.Team.SECOND, view)
                    else:
                        t_count = self.thieves_count(
                            adj_id, hide_and_seek_pb2.Team.FIRST, view)

                pr += t_count / self.degrees[adj_id]
        return pr

    def thief_move_ai(self, view: GameView) -> int:
        nodes_count = len(view.config.graph.nodes)
        if self.cost is None:
            self.cost = convert_paths_to_adj(
                view.config.graph.paths, nodes_count)
        if self.degrees is None:
            self.degrees = self.get_degrees(view)
        # message = ''
        # for m in range(len(view.visible_agents)):
        #     message = message  + '0'
        # self.phone.send_message(message)
        h = {}      # h(next) = cost * (prob. Of polices)
        current_node = view.viewer.node_id
        current_threat = self.pr_police(current_node, "opp", view)
        for adj_id in range(1, nodes_count+1):
            h[adj_id] = INF
            # write(f"{current_node} !!! {adj_id}")
            if self.cost[current_node][adj_id] != INF and adj_id != current_node:
                h[adj_id] = self.pr_police(adj_id, "opp", view)
            #     h[adj_id] = INF
            #     if self.degrees[adj_id] != 1 and view.balance > self.cost[current_node][adj_id]:
            #         h[adj_id] = (math.sqrt(self.cost[current_node][adj_id])) * \
            #             self.pr_police(adj_id, view)

        min_h = INF
        move_to = current_node
        # for adj_id in h.keys():
        #     # be ehtemale 1/PR-1 bemoone sare jash
        #     if h[adj_id] == 0 and random.randint(0, PR_STAY-1):
        #         continue
        #     if h[adj_id] < min_h:
        #         # age mosavi shod, ba ehtemale 1/2 bere ya bemoone
        #         if h[adj_id] == min_h and random.randint(0, 1):
        #             min_h = h[adj_id]
        #             move_to = adj_id
        #         else:
        #             min_h = h[adj_id]
        #             move_to = adj_id
        min_threat = current_threat
        for adj_id in h.keys():
            # if h[adj_id] <= min_threat:
            if h[adj_id] != INF and (h[adj_id] < min_threat or (h[adj_id] == min_threat and random.randint(0, 1))):

                min_threat = h[adj_id]
                move_to = adj_id

        write("Thief: "+str(h))

        # if min_h != INF:
        if True:
            write("Thief with id " + str(view.viewer.id) + " in node " +
                  str(current_node) + " move to " + str(move_to))
            return move_to
        else:
            write("Thief with id " + str(view.viewer.id) + " in node " +
                  str(current_node) + " move to " + str(current_node))
            return current_node  # Stay

    def police_move_ai(self, view: GameView) -> int:
        nodes_count = len(view.config.graph.nodes)
        if self.cost is None:
            self.cost = convert_paths_to_adj(
                view.config.graph.paths, len(view.config.graph.nodes))
        if self.degrees is None:
            self.degrees = self.get_degrees(view)

        h = {}  # h(x) = (cost * pr_police) / (pr_thieves * degree)
        current_node = view.viewer.node_id
        current_threat = self.pr_theives(current_node, "opp", view)
        for adj_id in range(1, nodes_count+1):
            h[adj_id] = INF
            if self.cost[current_node][adj_id] != INF and adj_id != current_node:
                h[adj_id] = self.pr_theives(adj_id, "opp", view)
                # and self.degree == 1
                # if view.balance > self.cost[current_node][adj_id]:
                #     h[adj_id] = (math.sqrt(self.cost[current_node][adj_id])) * self.pr_police(
                #         adj_id, view) / self.pr_theives(adj_id, view)  # * self.degrees[adj_id])

        min_h = INF
        move_to = current_node
        # for adj_id in h.keys():
        #     # be ehtemale 1/PR bemoone sare jash
        #     if h[adj_id] == 0 and random.randint(0, PR_STAY-1):
        #         continue
        #     if h[adj_id] < min_h:
        #         # age mosavi shod, ba ehtemale 1/2 bere ya bemoone
        #         if h[adj_id] == min_h and random.randint(0, 1):
        #             min_h = h[adj_id]
        #             move_to = adj_id
        #         else:
        #             min_h = h[adj_id]
        #             move_to = adj_id
        max_threat = current_threat
        for adj_id in h.keys():
            if h[adj_id] != INF and (h[adj_id] > max_threat or (h[adj_id] == max_threat and random.randint(0, 1))):
                move_to = adj_id
                max_threat = h[adj_id]

        write("Police: " + str(h))

        # if min_h != INF:
        if True:
            write("Police with id " + str(view.viewer.id) + " in node " +
                  str(current_node) + " move to " + str(move_to))
            return move_to
        else:
            write("Police with id " + str(view.viewer.id) + " in node " +
                  str(current_node) + " move to " + str(current_node))
            return current_node  # Stay
