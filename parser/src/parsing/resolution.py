#!/usr/bin/python

import inspect
import utilities
from utilities import Identifier, Hashable
from typing import Union, List, Tuple, Dict, Set
from enum import Enum
from abc import ABC, abstractmethod
import ast
import exceptions


class SymbolTableEntryKind(Enum):
    SORT_DESCRIPTOR = 1
    FUNCTION_DESCRIPTOR = 2
    SYMBOL_DESCRIPTOR = 3


class SymbolTableEntry(ABC):
    __slots__ = ('entry_kind', 'identifier')

    def __init__(self, kind: SymbolTableEntryKind, identifier: Union[Identifier, str]):
        self.entry_kind: SymbolTableEntryKind = kind
        self.identifier: Identifier = utilities.canonicalize_identifier(identifier)


class SortKind(Enum):
    UNINTERPRETED = 1
    PRIMITIVE = 2
    DATATYPE = 3
    FUNCTION = 4
    ALIAS = 5
    PLACEHOLDER = 6


class SortDescriptor(SymbolTableEntry, Hashable):
    __slots__ = ('sort_kind', 'num_parameters', 'alias_target', 'sort_arguments',
                 'introduced_placeholders')

    def __init__(self, identifier: Union[Identifier, str]):
        super().__init__(SymbolTableEntryKind.SORT_DESCRIPTOR, identifier)
        self._hash = None

    @staticmethod
    def create_sort(identifier: Union[Identifier, str], num_parameters: int, sort_kind: SortKind) -> 'SortDescriptor':
        result = SortDescriptor(identifier)
        result.num_parameters: int = num_parameters
        result.sort_arguments = []
        result.introduced_placeholders = []
        result.sort_kind = sort_kind
        result.alias_target = None
        return result

    @staticmethod
    def create_placeholder(identifier: str):
        result = SortDescriptor(identifier)
        result.num_parameters = 0
        result.sort_arguments = []
        result.introduced_placeholders = []
        result.sort_kind = SortKind.PLACEHOLDER
        result.alias_target = None
        return result

    @staticmethod
    def create_alias(identifier: Union[Identifier, str], introduced_placeholders: List['SortDescriptor'],
                     alias_target: 'SortDescriptor') -> 'SortDescriptor':
        if introduced_placeholders is None:
            introduced_placeholders = []

        result = SortDescriptor(identifier)
        result.sort_kind = SortKind.ALIAS
        result.num_parameters = len(introduced_placeholders)
        result.sort_arguments = []
        result.alias_target: SortDescriptor = alias_target
        result.introduced_placeholders = list(introduced_placeholders)
        return result

    def _check_unbound_sort_arguments(self, allowed_placeholders: List['SortDescriptor']):
        for sort_argument in self.sort_arguments:
            if sort_argument.sort_kind != SortKind.PLACEHOLDER:
                continue
            elif sort_argument not in allowed_placeholders:
                raise exceptions.ResolutionException("Could not resolve name: " + sort_argument, None, None)

    def _compute_equals(self, other: 'SortDescriptor') -> bool:
        if self.identifier != other.identifier:
            return False

        return utilities.first_discrepancy(self.sort_arguments, other.sort_arguments) is None

    def _compute_hash(self) -> int:
        return utilities.hash_sequence(self.sort_arguments, hash(self.identifier))

    def instantiate(self, args: List['SortDescriptor']):
        if self.num_parameters == 0 or len(self.sort_arguments) > 0:
            raise TypeError('Cannot instantiate a non-parametric sort.')

        if len(args) != self.num_parameters:
            raise TypeError(f'Expected sort to be instantiated with {self.num_parameters} sorts, ' +
                            f'but was instantiated with {len(args)} sorts instead.')

        result = SortDescriptor(self.identifier)
        result.sort_kind = self.sort_kind
        result.num_parameters = self.num_parameters
        result.sort_arguments = list(args)
        result.alias_target = self.alias_target
        result.introduced_placeholders = []

        if len(self.introduced_placeholders) == 0:
            return result

        # we have introduced parameters, we need to instantiate alias targets
        # in a suitable manner
        subst_map = {}
        for i in range(len(self.introduced_placeholders)):
            subst_map[self.introduced_placeholders[i]] = args[i]
            result.alias_target = self.alias_target.substitute(subst_map)

        return result

    def resolve_aliases(self):
        if not self.is_concrete():
            raise TypeError('Cannot resolve aliases on a non-concrete sort.')
        if self.alias_target is None:
            return self
        return self.alias_target.resolver_aliases()

    def substitute(self, subst_dict):
        result = SortDescriptor(self.identifier)
        result.sort_kind = self.sort_kind
        result.num_parameters = self.num_parameters
        result.sort_arguments = [subst_dict[x] if x in subst_dict else x for x in self.sort_arguments]
        result.alias_target = self.alias_target.substitute(subst_dict)
        result.introduced_placeholders = self.introduced_placeholders

    def is_concrete(self):
        return self.num_parameters == 0 or (len(self.sort_arguments) == self.num_parameters and
                                            all(x.sort_kind != SortKind.PLACEHOLDER for x in self.sort_arguments))


class FunctionKind(Enum):
    UNINTERPRETED = 1
    SYNTH_FUN = 2
    SYNTH_INV = 3
    USER_DEFINED = 4
    DATATYPE_CONSTRUCTOR = 5
    DATATYPE_TESTER = 6
    THEORY = 7


class FunctionDescriptor(SymbolTableEntry):
    __slots__ = ('function_kind', 'argument_sorts', 'argument_names',
                 'introduced_sort_placeholders', 'range_sort',
                 'function_body', 'synthesis_grammar', 'is_chainable')

    def __init__(self, identifier: Union[Identifier, str]):
        super().__init__(SymbolTableEntryKind.FUNCTION_DESCRIPTOR, identifier)

    @staticmethod
    def create_uninterpreted_function(identifier: Union[Identifier, str],
                                      arg_sorts: List[SortDescriptor],
                                      range_sort: SortDescriptor) -> 'FunctionDescriptor':
        result = FunctionDescriptor(identifier)
        result.function_kind = FunctionKind.UNINTERPRETED
        result.argument_sorts = list(arg_sorts)
        result.argument_names = None
        result.range_sort = range_sort
        result.introduced_sort_placeholders = None
        result.function_body = None
        result.synthesis_grammar = None
        result.is_chainable = False
        return result

    @staticmethod
    def create_synthesis_objective(identifier: Union[Identifier, str],
                                   parameters: List[Tuple[str, SortDescriptor]],
                                   range_sort: SortDescriptor,
                                   function_kind: FunctionKind,
                                   synthesis_grammar: ast.Grammar) -> 'FunctionDescriptor':
        if function_kind != FunctionKind.SYNTH_FUN and function_kind != FunctionKind.SYNTH_INV:
            raise ValueError('function_kind must be FunctionKind.SYNTH_FUN or FunctionKind.SYNTH_INV '
                             'in call to FunctionDescriptor.create_synthesis_objective()')

        result = FunctionDescriptor(identifier)
        result.function_kind = function_kind
        result.argument_sorts = [x[1] for x in parameters]
        result.argument_names = [x[0] for x in parameters]
        result.range_sort = range_sort
        result.introduced_sort_placeholders = None
        result.function_body = None
        result.synthesis_grammar: ast.Grammar = synthesis_grammar
        result.is_chainable = False
        return result

    @staticmethod
    def create_user_defined_function(identifier: Union[Identifier, str],
                                     parameters: List[Tuple[str, SortDescriptor]],
                                     range_sort: SortDescriptor,
                                     function_body: ast.Term) -> 'FunctionDescriptor':
        result = FunctionDescriptor(identifier)
        result.function_kind = FunctionKind.USER_DEFINED
        result.argument_sorts = [x[1] for x in parameters]
        result.argument_names = [x[0] for x in parameters]
        result.range_sort = range_sort
        result.function_body = function_body
        result.introduced_sort_placeholders = None
        result.synthesis_grammar = None
        result.is_chainable = False
        return result

    @staticmethod
    def create_datatype_constructor(identifier: str,
                                    introduced_sort_placeholders: List[SortDescriptor],
                                    parameters: List[Tuple[str, SortDescriptor]],
                                    datatype_sort: SortDescriptor) -> 'FunctionDescriptor':
        result = FunctionDescriptor(identifier)
        result.function_kind = FunctionKind.DATATYPE_CONSTRUCTOR
        result.introduced_sort_placeholders = list(introduced_sort_placeholders)
        result.argument_names = [x[0] for x in parameters]
        result.argument_sorts: List[Union[SortDescriptor, str]] = []

        for parameter in parameters:
            if parameter[1].sort_kind == SortKind.PLACEHOLDER and parameter[1] not in introduced_sort_placeholders:
                raise ValueError('Unresolved type name: ' + str(parameter[1].identifier))
            result.argument_sorts.append(parameter[1])

        result.range_sort = datatype_sort
        result.function_body = None
        result.synthesis_grammar = None
        result.is_chainable = False
        return result

    @staticmethod
    def create_datatype_tester(constructor_name: str, datatype_sort_descriptor: SortDescriptor) -> 'FunctionDescriptor':
        tester_identifier = Identifier('is', constructor_name)
        result = FunctionDescriptor(tester_identifier)
        result.function_kind = FunctionKind.DATATYPE_TESTER
        result.introduced_sort_placeholders = None
        result.argument_names = None
        result.argument_sorts = [datatype_sort_descriptor]
        result.range_sort = CoreResolver.get_boolean_sort()
        result.function_body = None
        result.synthesis_grammar = None
        result.is_chainable = False
        return result

    @staticmethod
    def create_theory_function(identifier: Union[Identifier, str],
                               arg_sorts: List[SortDescriptor],
                               range_sort: SortDescriptor,
                               is_chainable: bool) -> 'FunctionDescriptor':
        identifier = utilities.canonicalize_identifier(identifier)
        result = FunctionDescriptor(identifier)
        result.function_kind: FunctionKind = FunctionKind.THEORY
        result.introduced_sort_placeholders = None
        result.argument_names = None
        result.argument_sorts = list(arg_sorts)
        result.range_sort = range_sort
        result.function_body = None
        result.synthesis_grammar = None
        result.is_chainable = is_chainable
        if is_chainable and len(arg_sorts) != 1:
            raise ValueError('Chainable functions must have a unique argument sort.')
        return result

    def can_apply(self, arg_sorts: List[SortDescriptor]) -> Union[SortDescriptor, None]:
        if self.introduced_sort_placeholders is not None and len(self.introduced_sort_placeholders) > 0:
            subst_map = {}
            for i in range(self.argument_sorts):
                if self.argument_sorts[i].sort_kind == SortKind.PLACEHOLDER:
                    subst_map[self.argument_sorts[i]] = arg_sorts[i]
            return self.range_sort.substitute(subst_map)
        elif not self.is_chainable:
            if utilities.first_discrepancy(self.argument_sorts, arg_sorts) is None:
                return self.range_sort
            return None
        else:
            if utilities.are_all_elements_equal(arg_sorts, self.argument_sorts[0]):
                return self.range_sort
            return None


class SymbolKind(Enum):
    UNIVERSAL_VARIABLE = 1
    PARAMETER = 2
    QUANTIFIED_VARIABLE = 3
    LET_BOUND_VARIABLE = 4
    GRAMMAR_NONTERMINAL = 5


class SymbolDescriptor(SymbolTableEntry):
    __slots__ = ('symbol_sort', 'symbol_kind')

    def __init__(self, symbol_kind: SymbolKind, symbol: str, symbol_sort: SortDescriptor):
        super().__init__(SymbolTableEntryKind.SYMBOL_DESCRIPTOR, symbol)
        self.symbol_sort: SortDescriptor = symbol_sort
        self.symbol_kind: SymbolKind = symbol_kind


class SymbolTable(object):
    __slots__ = ('scope_stack', 'logic_name', 'enabled_features', 'options',
                 'inv_functions', 'synth_functions', 'user_defined_functions')

    def __init__(self):
        self.scope_stack = [{}]
        self.logic_name: str = ''
        self.enabled_features: Set[str] = {'grammars'}
        self.options: Dict[str, ast.Literal] = {}
        self.inv_functions: Dict[utilities.Identifier, FunctionDescriptor] = {}
        self.synth_functions: Dict[utilities.Identifier, FunctionDescriptor] = {}
        self.user_defined_functions: Dict[utilities.Identifier, FunctionDescriptor] = {}

    def push_scope(self, scope: Dict[Identifier, SymbolTableEntry] = None):
        self.scope_stack.append(scope if scope is not None else {})

    def pop_scope(self) -> Dict[Identifier, SymbolTableEntry]:
        return self.scope_stack.pop()

    def set_logic(self, logic_name: str):
        self.logic_name = logic_name

    def set_option(self, option_name: str, option_value: ast.Literal):
        self.options[option_name] = option_value

    def enable_feature(self, feature_name: str):
        self.enabled_features.add(feature_name)

    def disable_feature(self, feature_name: str):
        self.enabled_features.remove(feature_name)

    def _lookup(self, identifier: Union[Identifier, str]):
        key = utilities.canonicalize_identifier(identifier)

        for i in reversed(range(len(self.scope_stack))):
            scope = self.scope_stack[i]
            if key in scope:
                return scope[key]

        return None

    def lookup_sort(self, identifier: Union[Identifier, str]) -> SortDescriptor:
        res = self._lookup(identifier)
        return res if isinstance(res, SortDescriptor) else None

    def lookup_function(self, identifier: Union[Identifier, str]) -> FunctionDescriptor:
        res = self._lookup(identifier)
        return res if isinstance(res, FunctionDescriptor) else None

    def lookup_symbol(self, identifier: str) -> SymbolDescriptor:
        res = self._lookup(identifier)
        return res if isinstance(res, SymbolDescriptor) else None

    def lookup_or_resolve_sort(self, identifier: Union[Identifier, str]) -> SortDescriptor:
        res = self.lookup_sort(identifier)
        return res if res is not None else Resolver.resolve_sort(identifier)

    def lookup_or_resolve_function(self, identifier: Union[Identifier, str],
                                   *arg_sorts: SortDescriptor) -> FunctionDescriptor:
        res = self.lookup_function(identifier)
        return res if res is not None else Resolver.resolve_function(identifier, *arg_sorts)

    def add_sort(self, sort_descriptor: SortDescriptor) -> None:
        key = sort_descriptor.identifier
        if self._lookup(key) is not None:
            raise KeyError(f'Redefinition of identifier: {key}')

        self.scope_stack[-1][key] = sort_descriptor

    def add_function(self, function_descriptor: FunctionDescriptor):
        key = function_descriptor.identifier
        if self._lookup(key) is not None:
            raise KeyError(f'Redefinition of identifier: {key}')

        self.scope_stack[-1][key] = function_descriptor

        if function_descriptor.function_kind == FunctionKind.SYNTH_INV:
            self.inv_functions[key] = function_descriptor
        elif function_descriptor.function_kind == FunctionKind.SYNTH_FUN:
            self.synth_functions[key] = function_descriptor
        elif function_descriptor.function_kind == FunctionKind.USER_DEFINED:
            self.user_defined_functions[key] = function_descriptor

    def add_symbol(self, symbol_descriptor: SymbolDescriptor):
        key = symbol_descriptor.identifier
        if key in self.scope_stack[-1]:
            raise KeyError('Attempted to redefine symbol "%s"' % str(symbol_descriptor.identifier))
        self.scope_stack[-1][key] = symbol_descriptor


class Resolver(ABC):
    __slots__ = ('name',)

    _resolver_types: List[type] = []
    _resolvers: List['Resolver'] = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._resolver_types.append(cls)

    def __init__(self, name: str):
        self.name = name

    @classmethod
    def _initialize(cls):
        if cls._resolvers is not None and len(cls._resolvers) == len(cls._resolver_types):
            return

        if cls._resolvers is None:
            cls._resolvers = []

        for t in cls._resolver_types:
            if inspect.isabstract(t):
                continue

            if not any(isinstance(x, t) for x in cls._resolvers):
                cls._resolvers.append(t())

    @classmethod
    def resolve_sort(cls, identifier: Union[Identifier, str]) -> Union[SortDescriptor, None]:
        cls._initialize()
        identifier = utilities.canonicalize_identifier(identifier)
        for resolver in cls._resolvers:
            result = resolver._resolve_sort_impl(identifier)
            if result is not None:
                return result
        return None

    @classmethod
    def resolve_function(cls, identifier: Union[Identifier, str],
                         *arg_sorts: SortDescriptor) -> Union[FunctionDescriptor, None]:
        cls._initialize()
        identifier = utilities.canonicalize_identifier(identifier)
        for resolver in cls._resolvers:
            result = resolver._resolve_function_impl(identifier, *arg_sorts)
            if result is not None:
                return result
        return None

    @abstractmethod
    def _resolve_sort_impl(self, identifier: Identifier) -> SortDescriptor:
        raise NotImplemented

    @abstractmethod
    def _resolve_function_impl(self, identifier: Identifier, *arg_sorts: SortDescriptor) -> FunctionDescriptor:
        raise NotImplemented


class CacheKey(object):
    __slots__ = ('identifier', 'arg_sorts')

    def __init__(self, identifier: Identifier, arg_sorts: List[SortDescriptor]):
        self.identifier = identifier
        self.arg_sorts = tuple(arg_sorts)

    def __hash__(self):
        return utilities.hash_sequence(self.arg_sorts, hash(self.identifier))

    def __eq__(self, other):
        if other is None:
            return False
        if not isinstance(other, CacheKey):
            return False
        return (self.identifier == other.identifier and len(self.arg_sorts) == len(other.arg_sorts) and
                all(x[0] == x[1] for x in zip(self.arg_sorts, other.arg_sorts)))


class CachedResolver(Resolver):
    __slots__ = ('_function_resolution_cache', '_sort_resolution_cache')

    def __init__(self, name):
        super().__init__(name)
        self._function_resolution_cache: Dict[CacheKey, FunctionDescriptor] = {}
        self._sort_resolution_cache: Dict[Identifier, SortDescriptor] = {}

    @abstractmethod
    def _resolve_sort_impl_(self, identifier: Identifier) -> SortDescriptor:
        raise NotImplemented

    @abstractmethod
    def _resolve_function_impl_(self, identifier: Identifier, *arg_sorts: SortDescriptor) -> FunctionDescriptor:
        raise NotImplemented

    def _resolve_sort_impl(self, identifier: Identifier) -> SortDescriptor:
        desc = self._sort_resolution_cache.get(identifier, None)
        if desc is not None:
            return desc

        desc = self._resolve_sort_impl_(identifier)
        if desc is not None:
            self._sort_resolution_cache[identifier] = desc

        return desc

    def _resolve_function_impl(self, identifier: Identifier,
                               *arg_sorts: SortDescriptor) -> Union[FunctionDescriptor, None]:

        if len(arg_sorts) > 1 and utilities.are_all_elements_equal(arg_sorts):
            # first, try resolving with just one arg to see if we have something that's chainable
            key = CacheKey(identifier, [arg_sorts[0]])
            desc = self._function_resolution_cache.get(key, None)
            if desc is not None and desc.can_apply(arg_sorts) is not None:
                return desc

        key = CacheKey(identifier, list(arg_sorts))
        desc = self._function_resolution_cache.get(key, None)
        if desc is not None:
            return desc

        desc = self._resolve_function_impl_(identifier, *arg_sorts)

        if desc is not None:
            self._function_resolution_cache[key] = desc

        return desc

    def _add_sort(self, sort_descriptor: SortDescriptor):
        self._sort_resolution_cache[sort_descriptor.identifier] = sort_descriptor

    def _add_function(self, function_descriptor: FunctionDescriptor):
        key = CacheKey(function_descriptor.identifier, list(function_descriptor.argument_sorts))
        self._function_resolution_cache[key] = function_descriptor


class CoreResolver(CachedResolver):
    _boolean_sort = SortDescriptor.create_sort('Bool', 0, SortKind.PRIMITIVE)

    def __init__(self):
        super().__init__('Core')
        bool_sort = self.get_boolean_sort()
        self._add_sort(self.get_boolean_sort())
        self._add_function(FunctionDescriptor.create_theory_function('not', [bool_sort], bool_sort, False))
        self._add_function(FunctionDescriptor.create_theory_function('=>', [bool_sort], bool_sort, True))
        self._add_function(FunctionDescriptor.create_theory_function('and', [bool_sort], bool_sort, True))
        self._add_function(FunctionDescriptor.create_theory_function('or', [bool_sort], bool_sort, True))
        self._add_function(FunctionDescriptor.create_theory_function('xor', [bool_sort], bool_sort, True))

    @classmethod
    def get_boolean_sort(cls):
        return cls._boolean_sort

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _resolve_sort_impl_(self, identifier: Identifier) -> Union[SortDescriptor, None]:
        return None

    def _resolve_function_impl_(self, identifier: Identifier, *arg_sorts: SortDescriptor):
        if str(identifier) == '=' or identifier.symbol == 'distinct':
            if len(arg_sorts) < 2:
                return None
            if utilities.are_all_elements_equal(arg_sorts):
                return FunctionDescriptor.create_theory_function(identifier, [arg_sorts[0]],
                                                                 self.get_boolean_sort(), True)
            return None

        if str(identifier) == 'ite':
            if len(arg_sorts) != 3 or arg_sorts[0] != self.get_boolean_sort() or arg_sorts[1] != arg_sorts[2]:
                return None

            return FunctionDescriptor.create_theory_function(identifier, list(arg_sorts),
                                                             self.get_boolean_sort(), False)

        return None


class IntegerResolver(CachedResolver):
    _integer_sort = SortDescriptor.create_sort('Int', 0, SortKind.PRIMITIVE)

    def __init__(self):
        super().__init__('Integers')
        int_sort = self.get_integer_sort()
        bool_sort = CoreResolver.get_boolean_sort()

        self._add_sort(int_sort)

        self._add_function(FunctionDescriptor.create_theory_function('-', [int_sort], int_sort, False))
        self._add_function(FunctionDescriptor.create_theory_function('abs', [int_sort], int_sort, False))
        self._add_function(FunctionDescriptor.create_theory_function('mod', [int_sort, int_sort], int_sort, False))

        self._add_function(FunctionDescriptor.create_theory_function('-', [int_sort], int_sort, True))
        self._add_function(FunctionDescriptor.create_theory_function('+', [int_sort], int_sort, True))
        self._add_function(FunctionDescriptor.create_theory_function('*', [int_sort], int_sort, True))
        self._add_function(FunctionDescriptor.create_theory_function('div', [int_sort], int_sort, True))

        self._add_function(FunctionDescriptor.create_theory_function('<', [int_sort], bool_sort, True))
        self._add_function(FunctionDescriptor.create_theory_function('<=', [int_sort], bool_sort, True))
        self._add_function(FunctionDescriptor.create_theory_function('>', [int_sort], bool_sort, True))
        self._add_function(FunctionDescriptor.create_theory_function('>=', [int_sort], bool_sort, True))

    @classmethod
    def get_integer_sort(cls):
        return cls._integer_sort

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _resolve_sort_impl_(self, identifier: Identifier):
        return None

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _resolve_function_impl_(self, identifier: Identifier, *arg_sorts: SortDescriptor):
        return None


class RealResolver(CachedResolver):
    _real_sort = SortDescriptor.create_sort('Real', 0, SortKind.PRIMITIVE)

    def __init__(self):
        super().__init__('Reals')
        real_sort = self.get_real_sort()
        bool_sort = CoreResolver.get_boolean_sort()

        self._add_function(FunctionDescriptor.create_theory_function('-', [real_sort], real_sort, False))

        self._add_function(FunctionDescriptor.create_theory_function('-', [real_sort], real_sort, True))
        self._add_function(FunctionDescriptor.create_theory_function('+', [real_sort], real_sort, True))
        self._add_function(FunctionDescriptor.create_theory_function('*', [real_sort], real_sort, True))
        self._add_function(FunctionDescriptor.create_theory_function('/', [real_sort], real_sort, True))

        self._add_function(FunctionDescriptor.create_theory_function('<', [real_sort], bool_sort, True))
        self._add_function(FunctionDescriptor.create_theory_function('<=', [real_sort], bool_sort, True))
        self._add_function(FunctionDescriptor.create_theory_function('>', [real_sort], bool_sort, True))
        self._add_function(FunctionDescriptor.create_theory_function('>=', [real_sort], bool_sort, True))

    @classmethod
    def get_real_sort(cls):
        return cls._real_sort

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _resolve_sort_impl_(self, identifier: Identifier):
        return None

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _resolve_function_impl_(self, identifier: Identifier, *arg_sorts: SortDescriptor):
        return None


class ArrayResolver(CachedResolver):
    _array_sort = SortDescriptor.create_sort('Array', 2, SortKind.PRIMITIVE)

    def __init__(self):
        super().__init__('Arrays')

        self._add_sort(self.get_array_sort())

    @classmethod
    def get_array_sort(cls):
        return cls._array_sort

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _resolve_sort_impl_(self, identifier: Identifier):
        return None

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _resolve_function_impl_(self, identifier: Identifier, *arg_sorts: SortDescriptor):
        if (str(identifier) == 'select' and len(arg_sorts) == 2 and str(arg_sorts[0].identifier) == 'Array' and
                arg_sorts[1] == arg_sorts[0].sort_arguments[0]):
            return FunctionDescriptor.create_theory_function(identifier, list(arg_sorts),
                                                             arg_sorts[0].sort_arguments[1], False)

        if (str(identifier) == 'store' and len(arg_sorts) == 3 and str(arg_sorts[0].identifier) == 'Array' and
                arg_sorts[1] == arg_sorts[0].sort_arguments[1] and arg_sorts[2] == arg_sorts[0].sort_arguments[2]):
            return FunctionDescriptor.create_theory_function(identifier, list(arg_sorts), arg_sorts[0], False)

        return None


class StringResolver(CachedResolver):
    _string_sort = SortDescriptor.create_sort('String', 0, SortKind.PRIMITIVE)

    def __init__(self):
        super().__init__('Strings')

        string_sort = self.get_string_sort()
        int_sort = IntegerResolver.get_integer_sort()
        bool_sort = CoreResolver.get_boolean_sort()

        self._add_sort(string_sort)

        self._add_function(FunctionDescriptor.create_theory_function('str.++', [string_sort], string_sort, True))
        self._add_function(FunctionDescriptor.create_theory_function('str.replace', [string_sort] * 3,
                                                                     string_sort, False))
        self._add_function(FunctionDescriptor.create_theory_function('str.at', [string_sort, int_sort],
                                                                     string_sort, False))
        self._add_function(FunctionDescriptor.create_theory_function('str.from-int', [int_sort], string_sort, False))
        self._add_function(FunctionDescriptor.create_theory_function('str.substr', [string_sort, int_sort, int_sort],
                                                                     string_sort, False))
        self._add_function(FunctionDescriptor.create_theory_function('str.len', [string_sort], int_sort, False))
        self._add_function(FunctionDescriptor.create_theory_function('str.to-int', [string_sort], int_sort, False))
        self._add_function(FunctionDescriptor.create_theory_function('str.indexof',
                                                                     [string_sort, string_sort, int_sort],
                                                                     int_sort, False))
        self._add_function(FunctionDescriptor.create_theory_function('str.prefixof', [string_sort, string_sort],
                                                                     bool_sort, False))
        self._add_function(FunctionDescriptor.create_theory_function('str.suffixof', [string_sort, string_sort],
                                                                     bool_sort, False))
        self._add_function(FunctionDescriptor.create_theory_function('str.contains', [string_sort, string_sort],
                                                                     bool_sort, False))

    @classmethod
    def get_string_sort(cls):
        return cls._string_sort

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _resolve_sort_impl_(self, identifier: Identifier):
        return None

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _resolve_function_impl_(self, identifier: Identifier, *arg_sorts: SortDescriptor):
        return None


class BitVectorResolver(CachedResolver):
    _bit_vector_sorts: Dict[int, SortDescriptor] = {}

    def __init__(self):
        super().__init__("BitVector")

    @staticmethod
    def get_bit_vector_size(identifier: Identifier):
        if identifier.symbol == 'BitVec' and len(identifier.indices) == 1 and isinstance(identifier.indices[0], int):
            return identifier.indices[0]
        return None

    @classmethod
    def get_bit_vector_sort(cls, size: int):
        result = cls._bit_vector_sorts.get(size, None)

        if result is None:
            identifier = Identifier('BitVec', size)
            result = SortDescriptor.create_sort(identifier, 0, SortKind.PRIMITIVE)
            cls._bit_vector_sorts[size] = result

        return result

    def _resolve_sort_impl_(self, identifier: Identifier):
        size = self.get_bit_vector_size(identifier)
        return None if size is None else self.get_bit_vector_size(size)

    def _resolve_function_impl_(self, identifier: Identifier, *arg_sorts: SortDescriptor):
        if len(arg_sorts) < 1:
            return None
        size = self.get_bit_vector_size(arg_sorts[0].identifier)
        if size is None:
            return None

        if str(identifier) in ['bvnot', 'bvneg', 'bvcomp'] and len(arg_sorts) == 1:
            return FunctionDescriptor.create_theory_function(identifier, list(arg_sorts), arg_sorts[0], False)

        if (str(identifier) in ['bvurem', 'bvsrem', 'bvsmod', 'bvshl', 'bvlshr', 'bvashr'] and len(arg_sorts) == 2 and
                arg_sorts[1] == arg_sorts[2]):
            return FunctionDescriptor.create_theory_function(identifier, list(arg_sorts), arg_sorts[0], False)

        if (str(identifier) in ['bvand', 'bvor', 'bvnand', 'bvnor', 'bvxor', 'bvxnor',
                                'bvadd', 'bvsub', 'bvmul', 'bvudiv', 'bvsdiv'] and
                len(arg_sorts) >= 2 and utilities.are_all_elements_equal(arg_sorts)):
            return FunctionDescriptor.create_theory_function(identifier, [arg_sorts[0]], arg_sorts[0], True)

        if (str(identifier) in ['bvult', 'bvule', 'bvugt', 'bvuge', 'bvslt', 'bvsle', 'bvsgt', 'bvsge'] and
                len(arg_sorts) >= 2 and utilities.are_all_elements_equal(arg_sorts)):
            return FunctionDescriptor.create_theory_function(identifier, [arg_sorts[0]],
                                                             CoreResolver.get_boolean_sort(), True)

        return None