import unittest
import networkx as nx
import sys
import os
sys.path.append(os.path.abspath('../'))
# import python_cypher as p
from python_cypher.python_cypher import python_cypher
from python_cypher.python_cypher.debugger import *

 
class TestPythonCypher(unittest.TestCase):

    def test_upper(self):
        """Test we can parse a CREATE... RETURN query."""
        g = nx.MultiDiGraph()
        query = 'CREATE (n:SOMECLASS) RETURN n'
        test_parser = python_cypher.CypherToNetworkx()
        test_parser.query(g, query)

    def test_create_node(self):
        """Test we can build a query and create a node"""
        g = nx.MultiDiGraph()
        query = 'CREATE (n) RETURN n'
        test_parser = python_cypher.CypherToNetworkx()
        for i in test_parser.query(g, query):
            pass
        self.assertEqual(len(g.node), 1)

    def test_create_node_and_edge(self):
        """Test we can build a query and create two nodes and an edge"""
        g = nx.MultiDiGraph()
        query = 'CREATE (n)-->(m) RETURN n, m'
        test_parser = python_cypher.CypherToNetworkx()
        for i in test_parser.query(g, query):
            pass
        self.assertEqual(len(g.node), 2)
#        self.assertEqual(len(g.edge), 2)
        self.assertEqual(len(g.edges()), 1)

    def test_return_attribute(self):
        """Test we can return attribute from matching node"""
        g = nx.MultiDiGraph()
        create_query = 'CREATE (n:SOMECLASS {foo: "bar"}) RETURN n'
        match_query = 'MATCH (n) RETURN n.foo, n.class'
        test_parser = python_cypher.CypherToNetworkx()
        list(test_parser.query(g, create_query))
        out = list(test_parser.query(g, match_query))
        print (f"query:----------------- {out}")
        self.assertEqual(out, [['bar', 'SOMECLASS']])
    def test_underscore_attribute(self): 
        """Test we can return attribute from matching node"""
        g = nx.MultiDiGraph()
        create_query = 'CREATE (n:SOME_CLASS {foo: "bar"}) RETURN n'
        match_query = 'MATCH (n) RETURN n.foo, n.class'
        test_parser = python_cypher.CypherToNetworkx()
        list(test_parser.query(g, create_query))
        out = list(test_parser.query(g, match_query))
        print (f"query:----------------- {out}")
        self.assertEqual(out, [['bar', 'SOME_CLASS']])
    def test_where_node_class(self): 
        """Test we can return attribute from matching node"""
        g = nx.MultiDiGraph()
        create_query = 'CREATE (n:SOMECLASS {foo: "bar"}) RETURN n'
        create_query2 = 'CREATE (n:SOMECLASS {foo: "bar1"}) RETURN n'
        create_query3 = 'CREATE (n:SOMECLASS1 {foo: "barz"}) RETURN n'
        match_query = 'MATCH (n:SOMECLASS) RETURN n.foo, n.class'
        test_parser = python_cypher.CypherToNetworkx()
        list(test_parser.query(g, create_query))
        list(test_parser.query(g, create_query2))
        list(test_parser.query(g, create_query3))
        out = list(test_parser.query(g, match_query))
        print (f"query:----------------- {out}")
        self.assertEqual(out, [['bar', 'SOMECLASS'],['bar1', 'SOMECLASS']])
    def test_where_node_attributes_class(self): 
        """Test we can return attribute from matching node"""
        g = nx.MultiDiGraph()
        create_query = 'CREATE (n:SOMECLASS {foo: "bar"}) RETURN n'
        create_query2 = 'CREATE (n:SOMECLASS {foo: "bar1"}) RETURN n'
        create_query3 = 'CREATE (n:SOMECLASS1 {foo: "barz"}) RETURN n'
        match_query = 'MATCH (n:SOMECLASS {foo: "bar1"})  RETURN n.foo, n.class'
        test_parser = python_cypher.CypherToNetworkx()
        list(test_parser.query(g, create_query))
        list(test_parser.query(g, create_query2))
        list(test_parser.query(g, create_query3))
        out = list(test_parser.query(g, match_query))
        print (f"query:----------------- {out}")
        self.assertEqual(out, [['bar1', 'SOMECLASS']])
    def test_where_edge_class(self): 
        """Test we can return attribute from matching node"""
        g = nx.MultiDiGraph()
        create_query = 'CREATE (n:SOMECLASS {foo: "bar"})-[:SELECT {fooz: "bar"}]->(m:SOMECLASS {foo: "bar1"}) RETURN n,m,e'
        create_query2 = 'CREATE (n:SOMECLASS {foo: "bar2"})-[:SELECT {fooz: "bar2"}]->(m:SOMECLASS {foo: "bar"}) RETURN n,m,e'
        create_query3 = 'CREATE (n:SOMECLASS {foo: "bar3"})-[:SELECTZ {fooz: "bar"}]->(m:SOMECLASS {foo: "bar2"}) RETURN n,m,e'
        
        match_query = 'MATCH (n:SOMECLASS)-[e:SELECTZ]->(m)  RETURN n.foo, m.foo, m.class, e.edge_label'
        
        test_parser = python_cypher.CypherToNetworkx(debug_enabled=False, default_debug_level = 'WARN')
        _ = list(test_parser.query(g, create_query))
        _ = list(test_parser.query(g, create_query2))
        _ = list(test_parser.query(g, create_query3))
        expected_out = [
                    ['bar3', 'bar', 'SOMECLASS', 'SELECTZ'], 
                    ['bar3', 'bar1', 'SOMECLASS', 'SELECTZ'], 
                    ['bar3', 'bar2', 'SOMECLASS', 'SELECTZ'], 
                    ['bar3', 'bar', 'SOMECLASS', 'SELECTZ'], 
                    ['bar3', 'bar3', 'SOMECLASS', 'SELECTZ'], 
                    ['bar3', 'bar2', 'SOMECLASS', 'SELECTZ']
                ]
        out = list(test_parser.query(g, match_query))
        print (f"query:----------------- {out}")
        self.assertEqual(out, expected_out)

    def test_where_edge_attributes_class(self): 
        """Test we can return attribute from matching node"""
        g = nx.MultiDiGraph()
        create_query = 'CREATE (n:SOMECLASS {foo: "bar"})-[:SELECT {fooz: "bar"}]->(m:SOMECLASS {foo: "bar1"}) RETURN n,m,e'
        create_query2 = 'CREATE (n:SOMECLASS {foo: "bar2"})-[:SELECT {fooz: "bar2"}]->(m:SOMECLASS {foo: "bar"}) RETURN n,m,e'
        create_query3 = 'CREATE (n:SOMECLASS {foo: "bar3"})-[:SELECTZ {fooz: "bar"}]->(m:SOMECLASS {foo: "bar2"}) RETURN n,m,e'
        match_query = 'MATCH (n:SOMECLASS)-[e:SELECT {fooz: "bar"}]->(m)  RETURN n.foo, m.foo, m.class, e.edge_label, e.fooz'
        test_parser = python_cypher.CypherToNetworkx(debug_enabled=False, default_debug_level = 'WARN')
        _ = list(test_parser.query(g, create_query))
        _ = list(test_parser.query(g, create_query2))
        _ = list(test_parser.query(g, create_query3))

        expected_out = [
                ['bar', 'bar', 'SOMECLASS', 'SELECT', 'bar'], 
                ['bar', 'bar1', 'SOMECLASS', 'SELECT', 'bar'], 
                ['bar', 'bar2', 'SOMECLASS', 'SELECT', 'bar'], 
                ['bar', 'bar', 'SOMECLASS', 'SELECT', 'bar'], 
                ['bar', 'bar3', 'SOMECLASS', 'SELECT', 'bar'], 
                ['bar', 'bar2', 'SOMECLASS', 'SELECT', 'bar']
            ]
        out = list(test_parser.query(g, match_query))
        print (f"query:----------------- {out}")
        self.assertEqual(out, expected_out)
    
    def test_where_node_edge_attributes_class(self): 
        """Test we can return attribute from matching node"""
        g = nx.MultiDiGraph()
        create_query = 'CREATE (n:SOMECLASS {foo: "bar"})-[:SELECT {fooz: "bar"}]->(m:SOMECLASS {foo: "bar1"}) RETURN n,m,e'
        create_query2 = 'CREATE (n:SOMECLASS {foo: "bar2"})-[:SELECT {fooz: "bar2"}]->(m:SOMECLASS {foo: "bar"}) RETURN n,m,e'
        create_query3 = 'CREATE (n:SOMECLASS {foo: "bar3"})-[:SELECTZ {fooz: "bar"}]->(m:SOMECLASS {foo: "bar2"}) RETURN n,m,e'
        match_query = 'MATCH (n:SOMECLASS {foo: "bar2"})-[e:SELECT {fooz: "bar"}]->(m)  RETURN n.foo, m.foo, m.class, e.edge_label, e.fooz'
        test_parser = python_cypher.CypherToNetworkx(debug_enabled=False, default_debug_level = 'WARN')
        _ = list(test_parser.query(g, create_query))
        _ = list(test_parser.query(g, create_query2))
        _ = list(test_parser.query(g, create_query3))

        expected_out = []
        out = list(test_parser.query(g, match_query))
        print (f"query:----------------- {out}")
        self.assertEqual(out, expected_out)

    def test_where_node_edge_node_attributes_class(self): 
        """Test we can return attribute from matching node"""
        g = nx.MultiDiGraph()
        create_query = 'CREATE (n:SOMECLASS {foo: "bar"})-[:SELECT {fooz: "bar"}]->(m:SOMECLASS {foo: "bar1"}) RETURN n,m,e'
        create_query2 = 'CREATE (n:SOMECLASS {foo: "bar2"})-[:SELECT {fooz: "bar2"}]->(m:SOMECLASS {foo: "bar"}) RETURN n,m,e'
        create_query3 = 'CREATE (n:SOMECLASS {foo: "bar3"})-[:SELECTZ {fooz: "bar"}]->(m:SOMECLASS {foo: "bar2"}) RETURN n,m,e'
        match_query = 'MATCH (n:SOMECLASS {foo: "bar"})-[e:SELECT {fooz: "bar"}]->(m:SOMECLASS {foo: "bar"})  RETURN n.foo, m.foo, m.class, e.edge_label, e.fooz'
        test_parser = python_cypher.CypherToNetworkx(debug_enabled=False, default_debug_level = 'WARN')
        _ = list(test_parser.query(g, create_query))
        _ = list(test_parser.query(g, create_query2))
        _ = list(test_parser.query(g, create_query3))

        expected_out = [
                ['bar', 'bar', 'SOMECLASS', 'SELECT', 'bar'], 
                ['bar', 'bar', 'SOMECLASS', 'SELECT', 'bar']
            ]
        out = list(test_parser.query(g, match_query))
        print (f"query:----------------- {out}")
        self.assertEqual(out, expected_out)

if __name__ == '__main__':
    debug_instance = Debug(name='Teste')
    debug_instance.set_debug_level('WARN')
    debug_instance.toggle_debug(force_state=False)
    unittest.main()
 