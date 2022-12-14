import random
import math
import numpy as np
from src.client import GameClient
from src.model import GameView
from src import hide_and_seek_pb2
from src.model import AgentType

INF = float('inf')
PR_STAY = 10


#FIRST -> BLUE

def write(txt):
    f = open("logs/log_opponent1.log", "a")
    f.write(txt)
    f.write('\n')
    f.close()


def convert_paths_to_adj(paths, n, normalize=False):

    inf = float('inf')
    adj = [[inf for j in range(n+1)] for i in range(n+1)]

    min_price = inf
    for path in paths:
        adj[path.first_node_id][path.second_node_id] = path.price + 1
        adj[path.second_node_id][path.first_node_id] = path.price + 1
        if path.price < min_price:
            min_price = path.price + 1

    for i in range(n+1):
        adj[i][i] = 0

    # Price normalization: All/Min
    if normalize:
        if min_price != 0:
            for i in range(n+1):
                for j in range(n+1):
                    adj[i][j] /= min_price

    # write(str(adj))
    return adj


def floyd_warshall(paths, n, mode="distance") -> list:
    """mode: price, distance"""
    # TODO: mix floyd warshall distance and price

    D = convert_paths_to_adj(paths, n, True)

    if mode == "distance":
        for i in range(len(D)):
            for j in range(len(D[0])):
                if D[i][j] and D[i][j] != INF:
                    D[i][j] = 1

    inf = float('inf')
    for k in range(n+1):
        for i in range(n+1):
            for j in range(n+1):
                if D[i][k] < inf and D[k][j] < inf:
                    D[i][j] = min(D[i][j], D[i][k] + D[k][j])

    return D


def minDistance(dist, queue):
    minimum = float("Inf")
    min_index = -1

    for i in range(1, len(dist)):
        if dist[i] < minimum and i in queue:
            minimum = dist[i]
            min_index = i
    return min_index


def dijkstra(graph, source_node_id, target_node_id) -> list:
    row = len(graph)
    col = len(graph[0])

    dist = [float("Inf")] * row
    parent = [-1] * row
    dist[source_node_id] = 0

    queue = []
    for i in range(1, row):
        queue.append(i)

    while queue:
        u = minDistance(dist, queue)
        queue.remove(u)

        for i in range(1, col):
            is_one = 1 if graph[u][i] >= 0 and graph[u][i] != INF else 0
            if is_one and i in queue:
                if dist[u] + is_one < dist[i]:
                    dist[i] = dist[u] + is_one
                    parent[i] = u

    path = []
    node = target_node_id
    while parent[node] != -1:
        path.append(node)
        node = parent[node]
    path.append(node)
    return path


def get_thief_starting_node(view: GameView) -> int:
    # method 1
    # return random.randint(2, len(view.config.graph.nodes))

    # method 2
    thieves_ids = [view.viewer.id]
    team = view.viewer.team
    for agent in view.visible_agents:
        if agent.agent_type % 2== 0 and agent.team == team:
            thieves_ids.append(agent.id)

    count_node = len(view.config.graph.nodes)
    distances = floyd_warshall(
        view.config.graph.paths, count_node, mode="distance")

    police_distances = distances[1]
    police_distances[0] = -1
    
    argsorted_distances = np.argsort(police_distances)

    return argsorted_distances[-((((view.viewer.id - min(thieves_ids) + 1) * 2) - 1) % len(view.config.graph.nodes))]


class Phone:
    def __init__(self, client: GameClient):
        self.client = client
        self.last_index = 0

    def send_message(self, message):
        self.client.send_message(message)


class AI:
    def __init__(self, view: GameView, phone: Phone):
        self.phone = phone
        self.cost = None
        self.floyd_warshall_matrix = None
        self.degrees = None
        self.police_target = None
        self.prev_nodes = []
        self.view = view
        self.visible_thieves = {}
        # write(str(dir(view.viewer)))

    def get_degrees(self, view: GameView) -> list:
        nodes_count = len(view.config.graph.nodes)
        degrees = [0]*(nodes_count+1)
        for n in range(1, nodes_count+1):
            for adj in range(1, nodes_count+1):
                if self.cost[n][adj] != INF and adj != n:
                    degrees[n] += 1
        return degrees

    def get_adjacents(self, node_id, view: GameView) -> list:
        nodes_count = len(view.config.graph.nodes)
        neighbours = []
        for adj_id in range(1, nodes_count+1):
            if self.cost[node_id][adj_id] != INF and adj_id != node_id:
                neighbours.append(adj_id)
        return neighbours

    def police_count_all(self, view: GameView) -> int:
        pc = 0
        for vu in view.visible_agents:
            if(vu.agent_type % 2 == 1 and vu.team != view.viewer.team):
                pc += 1
        pc += 1
        return pc

    def get_units(self, view:GameView, agent_type:AgentType, team: str, return_type: str): #team == true : ours #
        results = []
        # write("test")
        # write("test " + str(view.viewer.agent_type) + str([v.agent_type for v in view.visible_agents]))
        for vu in view.visible_agents:
        # write(f'{vu.agent_type}')
            if team == "same" and vu.team == view.viewer.team and vu.agent_type % 2 == agent_type % 2 and not vu.is_dead:
                if return_type == "node":
                    results.append(vu.node_id)
                else:
                    results.append(vu.id)

            if team == "opp" and vu.team != view.viewer.team and vu.agent_type % 2== agent_type % 2 and not vu.is_dead:
                if return_type == "node":
                    results.append(vu.node_id)
                else:
                    results.append(vu.id)

        return results

    def police_count_node(self, node_id, team, view: GameView) -> int:
        pc = 0
        for vu in view.visible_agents:
            if (
                not vu.is_dead and
                vu.node_id == node_id and
                vu.agent_type % 2 == 1 and
                vu.team == team
            ):
                pc += 1
        return pc

    def thieves_count_node(self, node_id, team, view: GameView) -> int:
        tc = 0
        for vu in view.visible_agents:
            if (
                not vu.is_dead and
                vu.node_id == node_id and
                vu.agent_type % 2 == 0 and
                vu.team == team
            ):
                tc += 1
        return tc

    def isThiefin(self, node_id, view: GameView) -> bool:
        for t in view.visible_agents:
            if t.agent_type % 2 == 0 and self.view.viewer.team == t.team and t.node_id == node_id:
                return True
        return False

    def isPolicein(self, node_id, view: GameView, same_team: bool = False) -> bool:
        for t in view.visible_agents:
            if same_team:
                if t.agent_type % 2== 1 and self.view.viewer.team == t.team and t.node_id == node_id:
                    return True
            else:
                if t.agent_type % 2 == 1 and self.view.viewer.team != t.team and t.node_id == node_id:
                    return True
        return False

    def thief_move_ai(self, view: GameView) -> int:
        current_node = view.viewer.node_id
        nodes_count = len(view.config.graph.nodes)
        if self.cost is None:
            self.cost = convert_paths_to_adj(
                view.config.graph.paths, nodes_count)
        if self.degrees is None:
            self.degrees = self.get_degrees(view)
        if self.floyd_warshall_matrix is None:
            self.floyd_warshall_matrix = floyd_warshall(
                view.config.graph.paths, nodes_count)

        #dozd az dozd door beshe
        min_visible = min(view.config.visible_turns)
        if view.turn.turn_number < min_visible:
            adjs_mean = {}
            adj_array = self.get_adjacents(current_node,view)
            adj_array.append(current_node)
            for adj in adj_array:
                adj_distances = {}
                # adj_nodes = self.get_thief_nodes(view)
                adj_nodes = self.get_units(view, 0, "same", "node")
                # write(f'{adj_nodes=}')
                for tn in adj_nodes:
                    adj_distances[tn] = self.floyd_warshall_matrix[adj][tn]
                if adj_distances:
                    adjs_mean[adj] = min(list(adj_distances.values())) #TODO: clean
            
            max_distance = max(adjs_mean.values())
            
            move_to =[ key for key, value in adjs_mean.items() if value == max_distance]
            # write(f'{adjs_mean=}, {move_to=}')
            return random.choice(move_to)
            
        police_distances = {}
        
        # opponent_polices_nodes = self.get_opponent_polices_nodes(view)
        opponent_polices_nodes = self.get_units(view, 1, "opp", "node")
        for police_node in opponent_polices_nodes:
            police_distances[police_node] = self.floyd_warshall_matrix[current_node][police_node]

        shortest_dist = min(police_distances.values())
        # nearest_police = random.choice(
        #     [k for k, v in police_distances.items() if v == shortest_dist])

        nearest_police_to_adjacents = {}
        adjacents = []
        if shortest_dist <  max(police_distances.values()) // 2:
            adjacents = self.get_adjacents(current_node, view)
            
        else:
            flag = False
            flag2 = False
            for adj_id in range(1, nodes_count+1):
                if self.cost[current_node][adj_id] != INF and adj_id != current_node and not self.isThiefin(adj_id, view):
                    if self.degrees[adj_id] > 2:
                        flag = True
                        if not flag2:
                            flag2 = True
                            adjacents.clear()
                        adjacents.append(adj_id)
                    elif not flag: 
                        adjacents.append(adj_id)
        #adjacents.append(current_node)
        for adj_id in adjacents:
            nearest_police_to_adjacents[adj_id] = min([self.floyd_warshall_matrix[adj_id][p] for p in opponent_polices_nodes])
        
        furthest_dist_to_police = -1
    
        for p in nearest_police_to_adjacents.keys():
            if view.viewer.agent_type == 3:
                if view.viewer.team == 0:
                    if nearest_police_to_adjacents[p] > furthest_dist_to_police and self.police_count_node(p, 1, view) < 2 :
                        #HANDLE BATMAN
                        furthest_dist_to_police = nearest_police_to_adjacents[p]
                else:
                    if nearest_police_to_adjacents[p] > furthest_dist_to_police and self.police_count_node(p, 0, view) < 2:
                        furthest_dist_to_police = nearest_police_to_adjacents[p]
                
            else:
                if nearest_police_to_adjacents[p] > furthest_dist_to_police and not self.isPolicein(p, view):
                    furthest_dist_to_police = nearest_police_to_adjacents[p]
        


        furthest_adjacents = [
            k for k, v in nearest_police_to_adjacents.items() if v == furthest_dist_to_police]
        if furthest_adjacents:

            # max_degree = -1
            # move_to = current_node
            # for adj in furthest_adjacents:
            #     if self.degrees[adj] > max_degree:
            #         max_degree = self.degrees[adj]
            #         move_to = adj

            max_cost = -1
            move_to = current_node
            for adj in furthest_adjacents:
                if self.cost[adj][current_node] > max_cost:
                    max_cost = self.cost[adj][current_node]
                    move_to = adj

            # move_to = random.choice(furthest_adjacents)
            
            return move_to
        else:
            # TODO: idk
            h = {}      # h(next) = (prob. Of polices)
            current_node = view.viewer.node_id
            adjacents = self.get_adjacents(current_node, view)
            adjacents.append(current_node)
            for adj_id in adjacents:
                h[adj_id] = self.pr_police(adj_id, "opp", view)

            min_h = min(h.values())
            move_to = current_node
            if min_h != INF:
                min_nodes = [k for k, v in h.items() if v == min_h]
                move_to = random.choice(min_nodes)

            
            return move_to
    
    def send_thieves(self, view ,thieves):
        thief_to_police = {}
        for t in thieves:
            thief_to_police[t] = self.floyd_warshall_matrix[t][view.viewer.node_id]

        idk = [key for key,value in thief_to_police.items() if value == min(list(thief_to_police.values()))]
        idk = bin(random.choice(idk))
        bin_t = idk[2:]
        while bin_t[0] == '0':
            bin_t = bin_t[1:]
        if not bin_t in self.receive_thief(view): 
            self.phone.send_message(bin_t)

    def receive_thief(self, view):
        results = []
        flag = False
        
        # for b in view.chat_box:
        for t in range(self.phone.last_index, len(view.chat_box)):
            b = view.chat_box[t]
            flag = True
            results.append(int(b.text, 2))
        self.phone.last_index = len(view.chat_box)
        
        write(f'{results=}, {self.phone.last_index=}')
        return results

    def find_target_police(self, view: GameView):
        #self.phone.send_message("1010")
        self.visible_thieves = self.get_units(view, 0, "opp", "node")
        thieves = self.get_units(view, 0, "opp", "node")
        if thieves:
            self.send_thieves(view, thieves)

        self.visible_thieves.extend(self.receive_thief(view))
        self.visible_thieves = list(set(self.visible_thieves))
        # write(str(self.visible_thieves) + " =visible_thieves")

        current_node = view.viewer.node_id

        # thieves_nodes = [thief.node_id for thief in view.visible_agents
        #                  if (thief.agent_type == 0 and
        #                      thief.team != view.viewer.team and
        #                      not thief.is_dead)]

        for u in view.visible_agents:
            if u.agent_type == 3 and view.viewer.agent_type == 2:
                return u.node_id

        # if view.turn.turn_number in view.config.visible_turns:
        if self.visible_thieves:
            fwarshal_mat = self.floyd_warshall_matrix
            move_to = []
            thief_to_mean_police = {}
            
            for node_id in self.visible_thieves:
                # thief_to_mean_police[node_id] = np.mean([fwarshal_mat[node_id][p] for p in self.get_polices_nodes(view)])
                thief_to_mean_police[node_id] = np.mean([fwarshal_mat[node_id][p] for p in self.get_units(view, 1, "same", "node")])


            min_mean = min(list(thief_to_mean_police.values()))
            move_to = [key for key, value in thief_to_mean_police.items() if value == min_mean ]


            if not move_to:
                return random.choice(self.get_adjacents(current_node, view))

            return random.choice(move_to)
        else:
            if self.police_target is None:
                # polices = self.get_ours_polices_ids(view)
                polices = self.get_units(view, 1, "same", "id")
                polices = sorted(polices)

                nexts = []
                for adj_id in self.get_adjacents(current_node, view):
                    if not self.isPolicein(adj_id, view, True):
                        nexts.append(adj_id)

                if not nexts:
                    nexts.append(current_node)
                
                target = nexts[(view.viewer.id - min(polices)) % len(nexts)]
                x = 1
                while target in self.prev_nodes:
                    target = nexts[((view.viewer.id - min(polices)) + x) % len(nexts)]

                    x += 1
                    if x == 6:
                        break

                return target
            else:
                return self.police_target

    def push_to_prev_nodes(self, node_id: int):
        if len(self.prev_nodes) == 2:
            self.prev_nodes.remove(self.prev_nodes[0])
        self.prev_nodes.append(node_id)
    
    def police_move_ai(self, view: GameView) -> int:
        nodes_count = len(view.config.graph.nodes)
        current_node = view.viewer.node_id

        if self.cost is None:
            self.cost = convert_paths_to_adj(
                view.config.graph.paths, len(view.config.graph.nodes))
        if self.degrees is None:
            self.degrees = self.get_degrees(view)

        if self.police_target == current_node:
            self.police_target = None
        if self.floyd_warshall_matrix is None:
            self.floyd_warshall_matrix = floyd_warshall(
                view.config.graph.paths, nodes_count)

        self.police_target = self.find_target_police(view)

        polices_in = self.get_units(view, 1, "same", "id")

        polices_in = sorted(polices_in)    

        path = []
        adjacents_to_thief = {}
        if len(polices_in) > 1 and view.viewer.id in polices_in[1:]:
            for adj in self.get_adjacents(current_node, view):
                adjacents_to_thief[adj] = self.floyd_warshall_matrix[adj][self.police_target]
            sorted_adjs =list( dict(sorted(adjacents_to_thief.items(), key=lambda item: item[1])).keys())
            current_police_index = polices_in.index(view.viewer.id)
            adj_node = sorted_adjs[current_police_index]
            path = dijkstra(self.cost, adj_node, self.police_target)
            path.append(current_node)
            
        else:
            path = dijkstra(self.cost, current_node, self.police_target)
        
        if len(path) > 1:

            self.push_to_prev_nodes(path[-2])
            return path[-2]
        else:
            
            adjacents = self.get_adjacents(current_node, view)
            adjacents.append(current_node)
            
            target = random.choice(adjacents)
            x = 0
            while target in self.prev_nodes:
                target = random.choice(adjacents)
                x += 1
                if x == 5:
                    break

            self.push_to_prev_nodes(target)


            return target
