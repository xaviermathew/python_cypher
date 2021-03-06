# -*- coding: utf-8 -*-
"""
This script contains the ``CypherParserBaseClass``, which provides the basic
functionality to parse Cypher queries and run them against graphs.
"""

import copy
import hashlib
import random
import time

from python_cypher.utils import get_all_paths
from .cypher_tokenizer import *
from .cypher_parser import *
from .debugger import *

PRINT_TOKENS = False #True
PRINT_MATCHING_ASSIGNMENTS = False


def designations_from_atomic_facts(atomic_facts):
    """Returns a list of all the designations mentioned in the query."""
    designations = []
    for atomic_fact in atomic_facts:
        designations.append(getattr(atomic_fact, 'designation', None))
        designations.append(getattr(atomic_fact, 'node_1', None))
        designations.append(getattr(atomic_fact, 'node_2', None))
    designations = [designation for designation in designations if
                    designation is not None]
    designations = list(set(designations))
    designations.sort()
    return designations


class CypherParserBaseClass(object):
    """The base class that specific parsers will inherit from. Certain methods
       must be defined in the child class. See the docs."""

    def __init__(self, debug_enabled=True, default_debug_level = 'WARN'):
        self.debug_instance = Debug(name='CypherParserBaseClass')
        # self.debug_instance.set_debug_level(default_debug_level)
        # self.debug_instance.toggle_debug(force_state=debug_enabled)
        self.tokenizer = cypher_tokenizer
        self.parser = cypher_parser
        self.debug = self.debug_instance.debug

        ## Preparing debugger in ast modules
        # parser_debugger_instance.set_debug_level(default_debug_level)
        # parser_debugger_instance.toggle_debug(force_state=debug_enabled)
        # tokenizer_debugger_instance.set_debug_level(default_debug_level)
        # tokenizer_debugger_instance.toggle_debug(force_state=debug_enabled)

    # def set_debug_enabled(self, enabled):
    #     self.debug_instance.toggle_debug(force_state=enabled)
    #     ## ast modules
    #     parser_debugger_instance.toggle_debug(force_state=enabled)
    #     tokenizer_debugger_instance.toggle_debug(force_state=enabled)

    # def set_debug_level(self, level):
    #     self.debug_instance.set_debug_level(level)
    #     ## ast modules
    #     parser_debugger_instance.set_debug_level(level)
    #     tokenizer_debugger_instance.set_debug_level(level)

    def yield_var_to_element(self, parsed_query, graph_object):
        all_designations = []
        min_path_length = 1
        max_path_length = 1
        # Track down atomic_facts from outer scope.
        atomic_facts = extract_atomic_facts(parsed_query)
        self.debug('######################## yield_var_to_element ##########################')
        for fact in atomic_facts:
            self.debug('fact')
            self.debug(fact.__dict__)
            if hasattr(fact, 'designation') and fact.designation is not None:
                all_designations.append(fact.designation)
            elif hasattr(fact, 'literals'):
                for literal in fact.literals.literal_list:
                    self.debug('literal')
                    self.debug(literal.__dict__)
                    if hasattr(literal, 'designation') and literal.designation is not None:
                        all_designations.append(literal.designation)
                    for edge in literal.connecting_edges:
                        edge_constraint = []
                        if edge.min_path_length:
                            min_path_length += edge.min_path_length
                            edge_constraint.append(edge.min_path_length)
                        if edge.max_path_length:
                            max_path_length += edge.max_path_length
                            edge_constraint.append(edge.max_path_length)
                        if edge_constraint != [1, 1]:
                            all_designations.append(edge_constraint)

        self.debug('all_designations:%s min_path_length:%s max_path_length:%s' % (
            all_designations, min_path_length, max_path_length
        ))
        if len([designation for designation in all_designations if isinstance(designation, list)]) > 1:
            raise Exception('Cant have >1 variable length edge')

        for path in get_all_paths(graph_object, min_path_length, max_path_length):
            designations = []
            for designation in all_designations:
                if isinstance(designation, list):
                    num_extra_nodes = len(path) - (len(all_designations) - 1)
                    designations.extend(['_n%s' % i for i in range(num_extra_nodes)])
                else:
                    designations.append(designation)
            yield dict(zip(designations, path))

    def parse(self, query):
        """Calls yacc to parse the query string into an AST."""
        self.tokenizer.input(query)
        tok = self.tokenizer.token()
        while tok:
            if PRINT_TOKENS:
                self.debug(tok)
            tok = self.tokenizer.token()
        return self.parser.parse(query)

    def eval_constraint(self, constraint, assignment, graph_object):
        """This is the basis case for the recursive check
           on WHERE clauses."""
        # This might be broken because _get_node might expect the actual
        # node to be passed to it rather than the name of the node
        value = self._attribute_value_from_node_keypath(
            self._get_node(
                graph_object,
                assignment[constraint.keypath[0]]),
            constraint.keypath[1:])
        return constraint.function(value, constraint.value)

    def eval_boolean(self, clause, assignment, graph_object):
        """Recursive function to evaluate WHERE clauses. ``Or``
           and ``Not`` classes inherit from ``Constraint``."""
        if isinstance(clause, Or):
            return (self.eval_boolean(clause.left_disjunct,
                                      assignment, graph_object) or
                    self.eval_boolean(clause.right_disjunct,
                                      assignment, graph_object))
        elif isinstance(clause, Not):
            return not self.eval_boolean(clause.argument,
                                         assignment, graph_object)
        elif isinstance(clause, Constraint):
            return self.eval_constraint(clause, assignment, graph_object)

    def yield_return_values(self, graph_object, parsed_query):
        """This function routes the parsed
           query to a small number of high-level functions for handling
           specific types of queries (e.g. MATCH, CREATE, ...)"""
        def _test_match_where(clause, assignment, graph_object):
            sentinal = True  # Satisfied unless we fail
            for literal in clause.literals.literal_list:
                self.debug('_test_match_where literal')
                self.debug(literal.__dict__)
                designation = literal.designation
                desired_class = literal.node_class
                desired_document = literal.attribute_conditions
                node = graph_object._node[assignment[designation]]
                # Check the class of the node
                if (desired_class is not None and
                        node.get('class', None) != desired_class):
                    sentinal = False
                node_document = copy.deepcopy(node)
                # The `node_document` is a temporary copy for comparisons
                node_document.pop('class', None)
                if sentinal and (len(desired_document) > 0 and
                                 node_document != desired_document):
                    sentinal = False
                # Check all connecting edges from this node (literal)
                if not not literal.connecting_edges:  # not not -> empty?
                    edge_sentinal = True
                    for edge in literal.connecting_edges:
                        self.debug('_test_match_where edge')
                        self.debug(edge.__dict__)
                        edge_sentinal = False
                        source_designation = edge.node_1
                        target_designation = edge.node_2
                        edge_label = edge.edge_label 
                        attributes = edge.attribute_conditions
                        source_node = assignment[source_designation]
                        target_node = assignment[target_designation]
                        for one_edge_id in self._edges_connecting_nodes(
                                graph_object, source_node, target_node):
                            self.debug(f"xxxxxxxxxxxxxxx> {edge_label} {one_edge_id}")

                            one_edge = self._get_edge_from_id(graph_object, one_edge_id)

                            self.debug(f"yyyyyyyyyyyyyyy> {edge_label} {one_edge}")
                            if (edge_label is None or
                                    self._edge_class(one_edge) == edge_label):
                                if self._edge_compare_attributes(one_edge, attributes):
                                    edge_sentinal = True
                                    if getattr(edge, 'designation', None) is not None:
                                        assignment[edge.designation] = one_edge[2]['_id']
                                        # assignment[edge.designation] = one_edge_id
                    sentinal = sentinal and edge_sentinal
            # Check the WHERE claused
            # Note this isn't in the previous loop, because the WHERE clause
            # isn't restricted to a specific node
            if sentinal and clause.where_clause is not None:
                constraint = clause.where_clause.constraint
                constraint_eval = self.eval_boolean(
                    constraint, assignment, graph_object)
                sentinal = sentinal and constraint_eval
            return sentinal

        # Two cases: Starts with CREATE; doesn't start with CREATE.
        # First doesn't require enumeration of the domain; second does.

        if (isinstance(parsed_query.clause_list[0], CreateClause) and
                parsed_query.clause_list[0].is_head):
            # Run like before the refactor
            self.head_create_query(graph_object, parsed_query)
            yield 'foo'  # Need to return the created nodes, possibly
        else:
            # Importantly, we step through each assignment, and then for
            # each assignment, we step through each "clause" (need better name)
            for assignment in self.yield_var_to_element(
                    parsed_query, graph_object):
                self.debug('########### python_cypher.query #############')
                self.debug(assignment)
                satisfied = True
                for clause in parsed_query.clause_list:
                    if not satisfied:
                        break
                    if isinstance(clause, MatchWhere):  # MATCH... WHERE...
                        self.debug('########### python_cypher.query MatchWhere #############')
                        self.debug(assignment)
                        satisfied = satisfied and _test_match_where(
                            clause, assignment, graph_object)
                        self.debug(assignment)
                    elif isinstance(clause, ReturnVariables):
                        # We've added any edges to the assignment dictionary
                        # Now we need to step through the keypath lists that
                        # are stored in the ReturnVariables object under the
                        # attribute "variable_list"
                        return_values = []
                        for variable_path in clause.variable_list:
                            self.debug('########### python_cypher.query ReturnVar #############')
                            self.debug(assignment)
                            self.debug(variable_path)
                            # I expect this will choke on edges if we ask for
                            # their properties to be returned
                            if not isinstance(variable_path, list):
                                variable_path = [variable_path]
                            if variable_path[0] in {'nodes', 'edges'}:
                                if variable_path[0] == 'nodes':
                                    _get_node_or_edge = self._get_node
                                    _designation = '_n'
                                elif variable_path[0] == 'edges':
                                    _get_node_or_edge = self._get_edge
                                    _designation = '_e'
                                else:
                                    raise Exception("This will never happen. I'm just keeping my editor happy")
                                nodes_or_edges = [_get_node_or_edge(graph_object, assignment[designation])
                                                for designation in assignment.keys()
                                                if designation.startswith(_designation)]
                                return_value = [self._attribute_value_from_node_keypath(node_or_edge, variable_path[1:])
                                                for node_or_edge in nodes_or_edges]
                                return_values.extend(return_value)
                            else:
                                if self._is_edge(
                                        graph_object, assignment[variable_path[0]]):
                                    self.debug('############### _is_edge is True ##############')
                                    _get_node_or_edge = self._get_edge
                                elif self._is_node(
                                        graph_object, assignment[variable_path[0]]):
                                    self.debug('############### _is_node is True ##############')
                                    _get_node_or_edge = self._get_node
                                else:
                                    raise Exception("Neither a node nor an edge.")
                                node_or_edge = _get_node_or_edge(
                                    graph_object, assignment[variable_path[0]])
                                return_value = (
                                    self._attribute_value_from_node_keypath(
                                        node_or_edge, variable_path[1:]))
                                return_values.append(return_value)
                        yield return_values
                    else:
                        raise Exception("Unhandled case in query function.")

    def query(self, graph_object, query_string):
        """Top-level function that's called by the parser when a query has
           been transformed to its AST."""
        parsed_query = self.parse(query_string)
        yield from self.yield_return_values(graph_object, parsed_query)

    def head_create_query(self, graph_object, parsed_query):
        """For executing queries of the form CREATE... RETURN."""
        atomic_facts = extract_atomic_facts(parsed_query)
        designation_to_node = {}
        designation_to_edge = {}
        for create_clause in parsed_query.clause_list:
            if not isinstance(create_clause, CreateClause):
                continue
            for literal in create_clause.literals.literal_list:
                designation_to_node[literal.designation] = self._create_node(
                    graph_object, literal.node_class,
                    **literal.attribute_conditions)
        for edge_fact in [
                fact for fact in atomic_facts if
                isinstance(fact, EdgeExists)]:
            source_node = designation_to_node[edge_fact.node_1]
            target_node = designation_to_node[edge_fact.node_2]
            edge_label = edge_fact.edge_label
            attribute_conditions = edge_fact.attribute_conditions
            new_edge_id = self._create_edge(graph_object, source_node,
                                            target_node, edge_label=edge_label, 
                                            attribute_conditions=attribute_conditions)
            # Need an attribute for an edge designation
            designation_to_edge['placeholder'] = new_edge_id

    def _get_domain(self, *args, **kwargs):
        raise NotImplementedError(
            "Method _get_domain needs to be defined in child class.")

    def _get_node(self, *args, **kwargs):
        raise NotImplementedError(
            "Method _get_domain needs to be defined in child class.")

    def _node_attribute_value(self, *args, **kwargs):
        raise NotImplementedError(
            "Method _get_domain needs to be defined in child class.")

    def _edge_exists(self, *args, **kwargs):
        raise NotImplementedError(
            "Method _edge_exists needs to be defined in child class.")

    def _edges_connecting_nodes(self, *args, **kwargs):
        raise NotImplementedError(
            "Method _edges_connecting_nodes needs to be defined "
            "in child class.")

    def _node_class(self, *args, **kwargs):
        raise NotImplementedError(
            "Method _node_class needs to be defined in child class.")

    def _edge_class(self, *args, **kwargs):
        raise NotImplementedError(
            "Method _edge_class needs to be defined in child class.")

    def _create_node(self, *args, **kwargs):
        raise NotImplementedError(
            "Method _create_node needs to be defined in child class.")

    def _create_edge(self, *args, **kwargs):
        raise NotImplementedError(
            "Method _create_edge needs to be defined in child class.")

    def _get_edge_from_id(self, *args, **kwargs):
        raise NotImplementedError(
            "Method _get_edge_from_id needs to be defined in child class.")

    def _get_edge(self, *args, **kwargs):
        raise NotImplementedError(
            "Method _get_edge needs to be defined in child class.")

    def _attribute_value_from_node_keypath(self, *args, **kwargs):
        raise NotImplementedError(
            "Method _attribute_value_from_node_keypath needs to be defined.")

    def _is_edge(self, *args, **kwargs):
        raise NotImplementedError(
            "Method _is_edge needs to be defined.")

    def _is_node(self, *args, **kwargs):
        raise NotImplementedError(
            "Method _is_node needs to be defined.")


class CypherToNetworkx(CypherParserBaseClass):
    """Child class inheriting from ``CypherParserBaseClass`` to hook up
       Cypher functionality to NetworkX.
    """
    def _get_domain(self, obj):
        return obj.nodes()

    def _is_node(self, graph_object, node_name):
        return node_name in graph_object._node

    def _is_edge(self, graph_object, edge_name):
        self.debug('########### python_cypher._is_edge #############')
        self.debug(edge_name)
        self.debug('Nodes')
        self.debug([i for i in graph_object.nodes(data=True)])
        self.debug('Edges')
        self.debug([i for i in graph_object.edges(data=True)])
        for source_node_id, d, connections_dict in graph_object.edges(data=True):
            self.debug('''{}
            {}
            {}
            '''.format(source_node_id, d, connections_dict))
            for _, edges_dict in connections_dict.items (): #iteritems():
                if edges_dict == edge_name:
                    return True
                '''
                for _, edge_dict in edges_dict.items(): #iteritems():
                    if edge_dict.get('_id', None) == edge_name:
                        return True
                '''
        return False

    def _get_node(self, graph_object, node_name):
        return node_name
        # return graph_object._node[node_name]

    def _get_edge(self, graph_object, edge_name):
#        for source_node_id, connections_dict in graph_object.edge.iteritems():
        for source_node_id, target_node_id, edge_dict in graph_object.edges(data=True):
            if edge_dict.get('_id', None) == edge_name:
                return edge_dict
            # for _, edges_dict in connections_dict.iteritems():
            #     for _, edge_dict in edges_dict.iteritems():
            #         if edge_dict.get('_id', None) == edge_name:
            #             return edge_dict

    def _node_attribute_value(self, node, attribute_list):
        out = copy.deepcopy(node)
        for attribute in attribute_list:
            try:
                out = out.get(attribute)
            except:
                raise Exception(
                    "Asked for non-existent attribute {} in node {}.".format(
                        attribute, node))
        return out

    def _attribute_value_from_node_keypath(self, node, keypath):
        # We will try passing everything through this function
        if not isinstance(keypath, list) or len(keypath) == 0:
            return node
        value = node
        for key in keypath:
            try:
                value = value[key]
            except (KeyError, TypeError,):
                return None
        return value

    def _edge_exists(self, graph_obj, source, target,
                     edge_class=None, directed=True):
        raise NotImplementedError("Haven't finished _edge_exists.")

    def _get_edge_from_id(self, graph_object, edge_id):
        for source, target_id, data in graph_object.edges(data=True):
            #self.debug(f">>>> {source} {target_id} {edge_id} match:{edge_id==target_id}")
            if target_id == edge_id:
                return (source, target_id, data)
        #TODO
        '''
        for source, target_dict in graph_object.edge.iteritems():
            self.debug(f"--- {target_dict}")
            for target, edge_dict in target_dict.items (): #iteritems():
                self.debug(f"--- {target} {edge_dict}")
                for index, one_edge in edge_dict.iteritems():
                    if one_edge['_id'] == edge_id:
                        return one_edge
        '''
    def _edges_connecting_nodes(self, graph_object, source, target):
        try:
            #TODO            for index, data in graph_object.edge[source].get(
            #                    target, {}).iteritems():
            self.debug(f"----------- {source}")
            self.debug(f"----------- {target}")

            for index, e, data in graph_object.edges([source], data=True): #.get(target, {}).items():
                self.debug(f"..............>>> {index} {e} {data}")
                yield e #data #['_id']
        except:
            raise Exception("Error getting edges connecting nodes.")

    def _node_class(self, node, class_key='class'):
        return node.get(class_key, None)

    def _edge_class(self, edge, class_key='edge_label'):
        try:
            self.debug(f"----ec------> {edge}")
            out = edge[2].get(class_key, None)
            self.debug(f"----ec2------> {edge} {out}")
        except AttributeError:
            out = None
        return out

    def _edge_compare_attributes(self, edge, attributes):
        for attr_key in attributes.keys():
            attr = attributes[attr_key]
            try:
                self.debug(f"----ec------> {edge}")
                out = edge[2].get(attr_key, None)
                self.debug(f"----ec2------> {edge} {out}")
                if out != attr:
                    return False
            except AttributeError as e:
                self.debug('Error in comparation: {}'.format(e))
                return False
        return True

    def _create_node(self, graph_object, node_class, **attribute_conditions):
        """Create a node and return it so it can be referred to later."""
        new_id = unique_id()
        attribute_conditions['class'] = node_class
        graph_object.add_node(new_id, **attribute_conditions)
        return new_id

    def _create_edge(self, graph_object, source_node,
                     target_node, edge_label=None,
                     attribute_conditions=None):
        new_edge_id = unique_id()
        attr = attribute_conditions if attribute_conditions is not None else {}
        self.debug('############### _create_edge_ ##########################')
        self.debug(attr)
        attr['edge_label'] = edge_label
        attr['_id'] = new_edge_id
        graph_object.add_edge(
            source_node, target_node,
            **attr)
        return new_edge_id


def random_hash():
    """Return a random hash for naming new nods and edges."""
#    hash_value = hashlib.md5(str(random.random() + time.time())).hexdigest()
    hash_value = hashlib.md5(str(random.random() + time.time()).encode('utf-8')).hexdigest()
    return hash_value


def unique_id():
    """Call ``random_hash`` and prepend ``_id_`` to it."""
    return '_id_' + random_hash()


def extract_atomic_facts(query):
    my_parser = CypherToNetworkx()
    if isinstance(query, str):
        query = my_parser.parse(query)

    def _recurse(subquery):
        if subquery is None:
            return
        elif isinstance(subquery, list):
            for item in subquery:
                _recurse(item)
        elif isinstance(subquery, ReturnVariables):
            pass  # Ignore RETURN clause until after execution
        elif isinstance(subquery, FullQuery):
            for clause in subquery.clause_list:
                _recurse(clause)
        elif isinstance(subquery, MatchWhereReturnQuery):
            _recurse(subquery.match_clause)
            _recurse(subquery.where_clause)
        elif isinstance(subquery, MatchQuery):
            _recurse(subquery.literals)
            _recurse(subquery.where_clause)
        elif isinstance(subquery, CreateClause):
            _recurse(subquery.literals)
        elif isinstance(subquery, Literals):
            for literal in subquery.literal_list:
                _recurse(literal)

        # Add support for edges here in the recursion
        # Need to add an anonymous variable if a designation is not provided
        elif isinstance(subquery, EdgeExists):
            if (not hasattr(subquery, 'designation') or
                    subquery.designation is None):
                subquery.designation = (
                    '_v' + str(_recurse.next_anonymous_variable))
                _recurse.next_anonymous_variable += 1

        elif isinstance(subquery, Node):
            if (not hasattr(subquery, 'designation') or
                    subquery.designation is None):
                subquery.designation = (
                    '_v' + str(_recurse.next_anonymous_variable))
                _recurse.next_anonymous_variable += 1
            _recurse.atomic_facts.append(ClassIs(subquery.designation,
                                                 subquery.node_class))
            _recurse(subquery.connecting_edges)
            _recurse.atomic_facts += subquery.connecting_edges
            # print 'here'
            if hasattr(subquery, 'attribute_conditions'):
                _recurse.atomic_facts.append(
                    NodeHasDocument(
                        designation=subquery.designation,
                        document=(subquery.attribute_conditions if
                                  len(subquery.attribute_conditions) > 0
                                  else None)))
            if hasattr(subquery, 'foobarthingy'):
                # Don't think we'll need a case for edges
                pass
        elif isinstance(subquery, MatchWhere):
            _recurse.atomic_facts.append(subquery)
        elif isinstance(subquery, CreateClause):
            _recurse(subquery.create_clause)
        else:
            raise Exception(
                'unhandled case in extract_atomic_facts:' + (
                    subquery.__class__.__name__))
    _recurse.atomic_facts = []
    _recurse.next_anonymous_variable = 0
    _recurse(query)
    return _recurse.atomic_facts


# def main():
#     # sample = ','.join(['MATCH (x:SOMECLASS {bar : "baz"',
#     #                    'foo:"goo"})<-[:WHATEVER]-(:ANOTHERCLASS)',
#     #                    '(y:LASTCLASS) RETURN x.foo, y'])

#     # create = ('CREATE (n:SOMECLASS {foo: "bar", bar: {qux: "baz"}})'
#     #           '-[e:EDGECLASS]->(m:ANOTHERCLASS) RETURN n')
#     # create = 'CREATE (n:SOMECLASS {foo: "bar", qux: "baz"}) RETURN n'
#     create_query = ('CREATE (n:SOMECLASS {foo: {goo: "bar"}})'
#             '-[e:EDGECLASS]->(m:ANOTHERCLASS {qux: "foobar", bar: 10}) '
#                     'RETURN n')
#     test_query = ('MATCH (n:SOMECLASS {foo: {goo: "bar"}})-[e:EDGECLASS]->'
#                   '(m:ANOTHERCLASS) WHERE '
#                   'm.bar = 10 '
#                   'RETURN n.foo.goo, m.qux, e')
#     # atomic_facts = extract_atomic_facts(test_query)
#     graph_object = nx.MultiDiGraph()
#     my_parser = CypherToNetworkx()
#     for i in my_parser.query(graph_object, create_query):
#         pass  # a generator, we need to loop over results to run.
#     for i in my_parser.query(graph_object, test_query):
#         self.debug(i)


# if __name__ == '__main__':
#     # This main method is just for testing
#     main()
