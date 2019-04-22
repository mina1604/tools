#!/usr/bin/python

from abc import abstractmethod, ABC
from typing import Union, List, Tuple, Dict
from enum import Enum

from .utilities import Identifier, Location
from . import utilities


class ASTVisitor(object):
    __slots__ = ('name',)

    def __init__(self, name: str):
        self.name: str = name

    @abstractmethod
    def visit_sort_expression(self, sort_expression: 'SortExpression'):
        raise NotImplemented

    @abstractmethod
    def visit_identifier_term(self, identifier_term: 'IdentifierTerm'):
        raise NotImplemented

    @abstractmethod
    def visit_literal_term(self, literal_term: 'LiteralTerm'):
        raise NotImplemented

    @abstractmethod
    def visit_function_application_term(self, function_application_term: 'FunctionApplicationTerm'):
        raise NotImplemented

    @abstractmethod
    def visit_quantified_term(self, quantified_term: 'QuantifiedTerm'):
        raise NotImplemented

    @abstractmethod
    def visit_let_term(self, let_term: 'LetTerm'):
        raise NotImplemented

    @abstractmethod
    def visit_check_synth_command(self, check_synth_command: 'CheckSynthCommand'):
        raise NotImplemented

    @abstractmethod
    def visit_constraint_command(self, constraint_command: 'ConstraintCommand'):
        raise NotImplemented

    @abstractmethod
    def visit_declare_var_command(self, declare_var_command: 'DeclareVarCommand'):
        raise NotImplemented

    @abstractmethod
    def visit_inv_constraint_command(self, inv_constraint_command: 'InvConstraintCommand'):
        raise NotImplemented

    @abstractmethod
    def visit_set_feature_command(self, set_feature_command: 'SetFeatureCommand'):
        raise NotImplemented

    @abstractmethod
    def visit_set_option_command(self, set_option_command: 'SetOptionCommand'):
        raise NotImplemented

    @abstractmethod
    def visit_set_logic_command(self, set_logic_command: 'SetLogicCommand'):
        raise NotImplemented

    @abstractmethod
    def visit_synth_fun_command(self, synth_fun_command: 'SynthFunCommand'):
        raise NotImplemented

    @abstractmethod
    def visit_synth_inv_command(self, synth_inv_command: 'SynthInvCommand'):
        raise NotImplemented

    @abstractmethod
    def visit_grammar_term(self, grammar_term: 'GrammarTerm'):
        raise NotImplemented

    @abstractmethod
    def visit_grouped_rule_list(self, grouped_rule_list: 'GroupedRuleList'):
        raise NotImplemented

    @abstractmethod
    def visit_grammar(self, grammar: 'Grammar'):
        raise NotImplemented

    @abstractmethod
    def visit_declare_sort_command(self, declare_sort_command: 'DeclareSortCommand'):
        raise NotImplemented

    @abstractmethod
    def visit_define_fun_command(self, define_fun_command: 'DefineFunCommand'):
        raise NotImplemented

    @abstractmethod
    def visit_define_sort_command(self, define_sort_command: 'DefineSortCommand'):
        raise NotImplemented

    @abstractmethod
    def visit_datatype_constructor(self, datatype_constructor: 'DatatypeConstructor'):
        raise NotImplemented

    @abstractmethod
    def visit_datatype_constructor_list(self, datatype_constructor_list: 'DatatypeConstructorList'):
        raise NotImplemented

    @abstractmethod
    def visit_declare_datatypes_command(self, declare_datatypes_command: 'DeclareDatatypesCommand'):
        raise NotImplemented

    @abstractmethod
    def visit_declare_datatype_command(self, declare_datatypes_command: 'DeclareDatatypeCommand'):
        raise NotImplemented

    @abstractmethod
    def visit_program(self, program: 'Program'):
        raise NotImplemented


class AST(object):
    __slots__ = ('start_location', 'end_location')

    def __init__(self, start_location: Location, end_location: Location):
        self.start_location = start_location
        self.end_location = end_location

    @abstractmethod
    def accept(self, visitor: ASTVisitor):
        raise NotImplemented


class SortExpression(AST):
    __slots__ = ('identifier', 'sort_arguments')

    def __init__(self, identifier: Union[str, Identifier],
                 sort_arguments: List['SortExpression'],
                 start_location: Location, end_location: Location):
        super().__init__(start_location, end_location)
        self.identifier = utilities.canonicalize_identifier(identifier)
        self.sort_arguments = list(sort_arguments) if sort_arguments is not None else []

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_sort_expression(self)


class LiteralKind(Enum):
    NUMERAL = 1
    DECIMAL = 2
    BOOLEAN = 3
    HEXADECIMAL = 4
    BINARY = 5
    STRING = 6


class Literal(AST):
    __slots__ = ('literal_kind', 'literal_value')

    def __init__(self, literal_kind: LiteralKind, literal_value: str,
                 start_location: Location, end_location: Location):
        super().__init__(start_location, end_location)
        self.literal_kind = literal_kind
        self.literal_value = literal_value

    def accept(self, visitor: ASTVisitor):
        pass


class Term(AST, ABC):
    __slots__ = ('sort_descriptor', 'symbol_table_scope')

    def __init__(self, start_location: Location, end_location: Location):
        super().__init__(start_location, end_location)
        self.sort_descriptor = None
        self.symbol_table_scope = None


class IdentifierTerm(Term):
    __slots__ = ('identifier',)

    def __init__(self, identifier: Union[Identifier, str],
                 start_location: Location, end_location: Location):
        super().__init__(start_location, end_location)
        self.identifier = utilities.canonicalize_identifier(identifier)

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_identifier_term(self)


class LiteralTerm(Term):
    __slots__ = ('literal',)

    def __init__(self, literal: Literal, start_location: Location, end_location: Location):
        super().__init__(start_location, end_location)
        self.literal = literal

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_literal_term(self)


class FunctionApplicationTerm(Term):
    __slots__ = ('function_identifier', 'arguments')

    def __init__(self, identifier: Union[Identifier, str], arguments: List[Term],
                 start_location: Location, end_location: Location):
        super().__init__(start_location, end_location)
        self.function_identifier = utilities.canonicalize_identifier(identifier)
        self.arguments = list(arguments)

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_function_application_term(self)


class QuantifierKind(Enum):
    FORALL = 1
    EXISTS = 2


class QuantifiedTerm(Term):
    __slots__ = ('quantifier_kind', 'quantified_variables', 'term_body')

    def __init__(self, quantifier_kind: QuantifierKind,
                 quantified_variables: List[Tuple[str, SortExpression]], term_body: Term,
                 start_location: Location, end_location: Location):
        super().__init__(start_location, end_location)
        self.quantifier_kind = quantifier_kind
        self.quantified_variables = list(quantified_variables)
        self.term_body = term_body

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_quantified_term(self)


class LetTerm(Term):
    __slots__ = ('variable_bindings', 'let_body')

    def __init__(self, bindings: List[Tuple[str, Term]], let_body: Term,
                 start_location: Location, end_location: Location):
        super().__init__(start_location, end_location)
        self.variable_bindings = list(bindings)
        self.let_body = let_body

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_let_term(self)


class CommandKind(Enum):
    CHECK_SYNTH = 1
    CONSTRAINT = 2
    DECLARE_VAR = 3
    INV_CONSTRAINT = 4
    SET_FEATURE = 5
    SET_OPTION = 6
    SET_LOGIC = 7
    SYNTH_FUN = 8
    SYNTH_INV = 9
    DECLARE_SORT = 10
    DEFINE_FUN = 11
    DEFINE_SORT = 12
    DECLARE_DATATYPES = 13
    DECLARE_DATATYPE = 14


class Command(AST, ABC):
    __slots__ = ('command_kind',)

    def __init__(self, command_kind: CommandKind, start_location: Location, end_location: Location):
        super().__init__(start_location, end_location)
        self.command_kind: CommandKind = command_kind


class CheckSynthCommand(Command):
    def __init__(self, start_location: Location, end_location: Location):
        super().__init__(CommandKind.CHECK_SYNTH, start_location, end_location)

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_check_synth_command(self)


class ConstraintCommand(Command):
    __slots__ = ('constraint',)

    def __init__(self, constraint: Term, start_location: Location, end_location: Location):
        super().__init__(CommandKind.CONSTRAINT, start_location, end_location)
        self.constraint: Term = constraint

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_constraint_command(self)


class DeclareVarCommand(Command):
    __slots__ = ('symbol', 'sort_expression')

    def __init__(self, symbol: str, sort_expression: SortExpression,
                 start_location: Location, end_location: Location):
        super().__init__(CommandKind.DECLARE_VAR, start_location, end_location)
        self.symbol: str = symbol
        self.sort_expression: SortExpression = sort_expression

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_declare_var_command(self)


class InvConstraintCommand(Command):
    __slots__ = ('inv_fun_symbol', 'pre_symbol', 'trans_symbol', 'post_symbol')

    def __init__(self, inv_fun_symbol: str, pre_symbol: str, trans_symbol: str, post_symbol: str,
                 start_location: Location, end_location: Location):
        super().__init__(CommandKind.INV_CONSTRAINT, start_location, end_location)
        self.inv_fun_symbol = inv_fun_symbol
        self.pre_symbol = pre_symbol
        self.trans_symbol = trans_symbol
        self.post_symbol = post_symbol

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_inv_constraint_command(self)


class SetFeatureCommand(Command):
    __slots__ = ('feature_name', 'feature_value')

    def __init__(self, feature_name: str, feature_value: bool, start_location: Location, end_location: Location):
        super().__init__(CommandKind.SET_FEATURE, start_location, end_location)
        self.feature_name: str = feature_name
        self.feature_value: bool = feature_value

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_set_feature_command(self)


class SetOptionCommand(Command):
    __slots__ = ('option_name', 'option_value')

    def __init__(self, option_name: str, option_value: Literal, start_location: Location, end_location: Location):
        super().__init__(CommandKind.SET_OPTION, start_location, end_location)
        self.option_name: str = option_name
        self.option_value: Literal = option_value

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_set_option_command(self)


class SetLogicCommand(Command):
    __slots__ = ('logic_name',)

    def __init__(self, logic_name: str, start_location: Location, end_location: Location):
        super().__init__(CommandKind.SET_LOGIC, start_location, end_location)
        self.logic_name: str = logic_name

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_set_logic_command(self)


class GrammarTermKind(Enum):
    CONSTANT = 1
    VARIABLE = 2
    BINDER_FREE = 3


class GrammarTerm(Term):
    __slots__ = ('grammar_term_kind', 'sort_expression', 'binder_free_term')

    def __init__(self, start_location: Location, end_location: Location):
        super().__init__(start_location, end_location)

    @staticmethod
    def create_constant_term(sort_expression: SortExpression,
                             start_location: Location, end_location: Location) -> 'GrammarTerm':
        result = GrammarTerm(start_location, end_location)
        result.sort_expression = sort_expression
        result.binder_free_term = None
        result.grammar_term_kind: GrammarTermKind = GrammarTermKind.CONSTANT
        return result

    @staticmethod
    def create_variable_term(sort_expression: SortExpression, start_location: Location, end_location: Location):
        result = GrammarTerm(start_location, end_location)
        result.sort_expression = sort_expression
        result.binder_free_term = None
        result.grammar_term_kind: GrammarTermKind = GrammarTermKind.VARIABLE
        return result

    @staticmethod
    def create_binder_free_grammar_term(binder_free_term: Term, start_location: Location, end_location: Location):
        result = GrammarTerm(start_location, end_location)
        result.sort_expression = None
        result.binder_free_term = binder_free_term
        result.grammar_term_kind: GrammarTermKind = GrammarTermKind.BINDER_FREE
        return result

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_grammar_term(self)


class GroupedRuleList(AST):
    __slots__ = ('head_symbol', 'head_symbol_sort_expression', 'expansion_rules', 'head_symbol_sort_descriptor')

    def __init__(self, head_symbol: str, head_symbol_sort_expression: SortExpression,
                 expansion_rules: List[GrammarTerm],
                 start_location: Location, end_location: Location):
        super().__init__(start_location, end_location)
        self.head_symbol = head_symbol
        self.head_symbol_sort_expression = head_symbol_sort_expression
        self.expansion_rules = list(expansion_rules)
        self.head_symbol_sort_descriptor = None

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_grouped_rule_list(self)


class Grammar(AST):
    __slots__ = ('nonterminals', 'grouped_rule_lists', 'symbol_table_scope')

    def __init__(self, nonterminals: List[Tuple[str, SortExpression]], grouped_rule_lists: List[GroupedRuleList],
                 start_location: Location, end_location: Location):
        super().__init__(start_location, end_location)
        self.nonterminals = list(nonterminals)
        self.grouped_rule_lists: Dict[str, GroupedRuleList] = {}
        for grouped_rule_list in grouped_rule_lists:
            head = grouped_rule_list.head_symbol
            if head in self.grouped_rule_lists:
                raise KeyError('The symbol: %s has more than one group of rules associated with it.\n'
                               'At: %s -- %s' % (head, str(grouped_rule_list.start_location),
                                                 str(grouped_rule_list.end_location)))
            self.grouped_rule_lists[head] = grouped_rule_list
        self.symbol_table_scope = None

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_grammar(self)


class SynthFunCommand(Command):
    __slots__ = ('function_symbol', 'parameters_and_sorts', 'range_sort_expression',
                 'synthesis_grammar', 'symbol_table_scope')

    def __init__(self, function_symbol: str, parameters_and_sorts: List[Tuple[str, SortExpression]],
                 range_sort_expression: SortExpression, synthesis_grammar: Grammar,
                 start_location: Location, end_location: Location):
        super().__init__(CommandKind.SYNTH_FUN, start_location, end_location)
        self.function_symbol = function_symbol
        self.parameters_and_sorts: List[Tuple[str, SortExpression]] = list(parameters_and_sorts)
        self.range_sort_expression: SortExpression = range_sort_expression
        self.synthesis_grammar = synthesis_grammar
        self.symbol_table_scope = None

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_synth_fun_command(self)


class SynthInvCommand(Command):
    __slots__ = ('function_symbol', 'parameters_and_sorts', 'synthesis_grammar',
                 'symbol_table_scope')

    def __init__(self, function_symbol: str, parameters_and_sorts: List[Tuple[str, SortExpression]],
                 synthesis_grammar: Grammar, start_location: Location, end_location: Location):
        super().__init__(CommandKind.SYNTH_INV, start_location, end_location)
        self.function_symbol = function_symbol
        self.parameters_and_sorts: List[Tuple[str, SortExpression]] = list(parameters_and_sorts)
        self.synthesis_grammar = synthesis_grammar
        self.symbol_table_scope = None

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_synth_inv_command(self)


class DeclareSortCommand(Command):
    __slots__ = ('sort_name', 'sort_arity')

    def __init__(self, sort_name: str, sort_arity: int, start_location: Location, end_location: Location):
        super().__init__(CommandKind.DECLARE_SORT, start_location, end_location)
        self.sort_name: str = sort_name
        self.sort_arity: int = sort_arity

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_declare_sort_command(self)


class DefineFunCommand(Command):
    __slots__ = ('function_name', 'function_parameters', 'function_range_sort', 'function_body')

    def __init__(self, function_name: str, function_parameters: List[Tuple[str, SortExpression]],
                 function_range_sort: SortExpression, function_body: Term,
                 start_location: Location, end_location: Location):
        super().__init__(CommandKind.DEFINE_FUN, start_location, end_location)
        self.function_name: str = function_name
        self.function_parameters: List[Tuple[str, SortExpression]] = list(function_parameters)
        self.function_range_sort: SortExpression = function_range_sort
        self.function_body: Term = function_body

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_define_fun_command(self)


class DefineSortCommand(Command):
    __slots__ = ('sort_name', 'sort_parameters', 'sort_expression')

    def __init__(self, sort_name: str,
                 sort_parameters: List[str],
                 sort_expression: SortExpression,
                 start_location: Location, end_location: Location):
        super().__init__(CommandKind.DEFINE_SORT, start_location, end_location)
        self.sort_name: str = sort_name
        self.sort_parameters: List[str] = list(sort_parameters)
        self.sort_expression: SortExpression = sort_expression

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_define_sort_command(self)


class DatatypeConstructor(AST):
    __slots__ = ('constructor_name', 'constructor_parameters')

    def __init__(self, constructor_name: str, constructor_parameters: List[Tuple[str, SortExpression]],
                 start_location: Location, end_location: Location):
        super().__init__(start_location, end_location)
        self.constructor_name: str = constructor_name
        self.constructor_parameters: List[Tuple[str, SortExpression]] = list(constructor_parameters)

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_datatype_constructor(self)


class DatatypeConstructorList(AST):
    __slots__ = ('introduced_sort_placeholders', 'constructors')

    def __init__(self, introduced_sort_placeholders: List[str], constructors: List[DatatypeConstructor],
                 start_location: Location, end_location: Location):
        super().__init__(start_location, end_location)
        self.introduced_sort_placeholders = list(introduced_sort_placeholders)
        self.constructors = list(constructors)

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_datatype_constructor_list(self)


class DeclareDatatypesCommand(Command):
    __slots__ = ('sort_names_and_arities', 'datatype_constructor_lists')

    def __init__(self, sort_names_and_arities: List[Tuple[str, int]],
                 datatype_constructor_lists: List[DatatypeConstructorList],
                 start_location: Location, end_location: Location):
        super().__init__(CommandKind.DECLARE_DATATYPES, start_location, end_location)
        self.sort_names_and_arities = list(sort_names_and_arities)
        self.datatype_constructor_lists = list(datatype_constructor_lists)

        if len(self.sort_names_and_arities) != len(self.datatype_constructor_lists):
            raise ValueError('Must have same number of datatype constructor lists as introduced sorts.\n' +
                             f'At: {start_location} -- {end_location}')

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_declare_datatypes_command(self)


class DeclareDatatypeCommand(Command):
    __slots__ = ('sort_name', 'sort_arity', 'datatype_constructor_list')

    def __init__(self, sort_name: str, sort_arity: int, datatype_constructor_list: DatatypeConstructorList,
                 start_location: Location, end_location: Location):
        super().__init__(CommandKind.DECLARE_DATATYPE, start_location, end_location)
        self.sort_name = sort_name
        self.sort_arity = sort_arity
        self.datatype_constructor_list = datatype_constructor_list

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_declare_datatype_command(self)


class Program(AST):
    __slots__ = ('commands',)

    def __init__(self, commands: List[Command]):
        super().__init__(commands[0].start_location, commands[-1].end_location)
        self.commands = list(commands)

    def accept(self, visitor: ASTVisitor):
        return visitor.visit_program(self)