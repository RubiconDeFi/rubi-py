
def find_pure_pairs(g):
    # returns a list of pure pairs [(node1, node2)] where node1 has done all of its trading with node2

    pure_pairs = []
    for node in g.nodes:
        connected_nodes = list(g.successors(node))
        total_trade_volume_node = g.nodes[node]['data'].usd_traded

        for connected_node in connected_nodes:
            total_trade_volume_connected_node = g.nodes[connected_node]['data'].usd_traded
            total_trade_volume_edge = g.edges[node, connected_node]['data'].usd_amt
            
            if total_trade_volume_node == total_trade_volume_edge:
                pair = tuple((node, connected_node))
                if pair not in pure_pairs:
                    pure_pairs.append(pair)
            
            if total_trade_volume_connected_node == total_trade_volume_edge:
                pair = tuple((connected_node, node))
                if pair not in pure_pairs:
                    pure_pairs.append(pair)

    return pure_pairs