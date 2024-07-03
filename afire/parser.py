# Copyright (C) 2018 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Provides parsing functionality used by Python Fire."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import platform
import ast
from datetime import datetime, date
from typing import Union, Optional, Type, List, Tuple, Callable, Any, Dict, Set, TypeVar
from functools import partial


def CreateParser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--interactive", "-i", action="store_true")
    parser.add_argument("--separator", default="-")
    parser.add_argument("--completion", nargs="?", const="bash", type=str)
    parser.add_argument("--help", "-h", action="store_true")
    parser.add_argument("--trace", "-t", action="store_true")
    # TODO(dbieber): Consider allowing name to be passed as an argument.
    return parser


def SeparateFlagArgs(args):
    """Splits a list of args into those for Flags and those for Fire.

    If an isolated '--' arg is not present in the arg list, then all of the args
    are for Fire. If there is an isolated '--', then the args after the final '--'
    are flag args, and the rest of the args are fire args.

    Args:
      args: The list of arguments received by the Fire command.
    Returns:
      A tuple with the Fire args (a list), followed by the Flag args (a list).
    """
    if "--" in args:
        separator_index = len(args) - 1 - args[::-1].index("--")  # index of last --
        flag_args = args[separator_index + 1 :]
        args = args[:separator_index]
        return args, flag_args
    return args, []


def ParseTime(value: str) -> datetime:
    for format in [
        "%Y-%m-%d-%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y%m%d%H%M%S",
        "%Y/%m/%d",
        "%Y-%m-%d",
    ]:
        try:
            return datetime.strptime(value, format)
        except (ValueError, TypeError):
            pass
    raise ValueError(f"cannot parse {value} as date/datetime")


def _DeGenericAlias(t) -> Tuple[Type, List[Type]]:
    origin_type = None
    if platform.python_version().startswith("3.11."):
        if "__class__" in dir(t):
            from types import UnionType

            if t.__class__ == UnionType:
                origin_type = Union
    if origin_type is None:
        origin_type = t.__origin__

    if IsGenericAlias(t):
        if "__args__" not in dir(t):
            return origin_type, [Any]
        return origin_type, t.__args__
    return t, []


def IsGenericAlias(t) -> bool:
    if platform.python_version().startswith("3.11."):
        if "__class__" in dir(t):
            from types import UnionType

            if t.__class__ == UnionType:
                return True
    return "__origin__" in dir(t)


def ParseComplexValue(value: str, t):
    origin, args = _DeGenericAlias(t)
    if origin in (Union, Optional):
        if value == "None" and (origin == Optional or (origin == Union and type(None) in args)):
            return None

        for each_type in args:
            try:
                if IsGenericAlias(each_type):
                    return ParseComplexValue(value, each_type)

                if each_type is type(None):
                    continue
                return SpecTypeParseValueGen(each_type)(value)
            except ValueError as e:
                ...
    elif issubclass(origin, (Dict, List, Set, Tuple, bytes)):
        return _ParseConvert(DefaultParseValue(value), t)

    raise ValueError(f'cannot parse value "{value}" to type {t}')


def _ParseConvert(parsed: Any, t):
    origin, args = _DeGenericAlias(t)
    if origin == Union:
        # if is None, return directly
        if type(None) in args and parsed is None:
            return None
        for may_type in args:
            # filter None type
            if may_type == type(None):
                continue
            else:
                try:
                    if IsGenericAlias(may_type):
                        return _ParseConvert(parsed, may_type)
                    else:
                        return TypeToParser.get(may_type, may_type)(parsed)
                except ValueError:
                    continue
        raise ValueError(f'cannot parse value "{parsed}" to type {t}')
    elif issubclass(origin, (Tuple, List, Set)):
        res = []
        if issubclass(origin, Tuple):
            res_t = tuple
        else:
            if issubclass(origin, Set):
                res_t = set
            else:
                res_t = list
            args *= len(parsed)
        if len(parsed) != len(args):
            raise ValueError(f"number of args mismatch in type: {t} and value: {parsed}")
        for each_type, each_value in zip(args, parsed):
            if IsGenericAlias(each_type):
                res.append(_ParseConvert(each_value, each_type))
            elif type(None) == each_type:
                if each_value is not None:
                    raise ValueError(f'cannot parse value: "{each_value}" to type None in Tuple: {parsed}')
            elif each_type == TypeVar or type(each_type) == TypeVar or each_type is Any:
                res.append(each_value)
            else:
                res.append(TypeToParser.get(each_type, each_type)(each_value))
        return res_t(res)
    elif issubclass(origin, Dict):
        res = {}
        key_t, value_t = args
        if not isinstance(parsed, Dict):
            raise ValueError(f"the type hint is {t}, but got type: {type(parsed).__name__}, value: {parsed}")
        for k, v in parsed.items():
            if key_t == TypeVar or type(key_t) == TypeVar:
                res_key = k
            elif IsGenericAlias(key_t):
                res_key = _ParseConvert(k, key_t)
            else:
                res_key = TypeToParser.get(key_t, key_t)(k)

            if value_t == TypeVar:
                res_value = v
            elif IsGenericAlias(value_t):
                res_value = _ParseConvert(v, value_t)
            else:
                res_value = TypeToParser.get(value_t, value_t)(v)

            res[res_key] = res_value
        return res
    elif issubclass(origin, bytes):
        if isinstance(parsed, str):
            return parsed.encode("utf8")
        if not isinstance(parsed, bytes):
            raise ValueError(f"the type hint is {t}, but got type: {type(parsed).__name__}, value: {parsed}")
        return parsed
    raise ValueError(f"not support type {t} yet")


def _BytesParser(value) -> bytes:
    if value.startswith('b"') or value.startswith("b'"):
        value = DefaultParseValue(value)
    if isinstance(value, str):
        return value.encode("utf8")
    elif isinstance(value, bytes):
        return value
    elif isinstance(value, int):
        return value.to_bytes(8, "big")
    else:
        raise ValueError(f"cannot convert type: {type(value)}, value: {value} as type bytes")


TypeToParser = {
    datetime: ParseTime,
    date: lambda value: ParseTime(value).date,
    bool: lambda value: value == "True" or value == True,
    bytes: _BytesParser,
}


def SpecTypeParseValueGen(t) -> Callable[[str], Any]:
    # complex type, e.g. Union
    if IsGenericAlias(t):
        parse_fn = partial(ParseComplexValue, t=t)
    # try to use type to parser mapping or callable
    else:
        parse_fn = TypeToParser.get(t, t)
    return parse_fn


def DefaultParseValue(value):
    """The default argument parsing function used by Fire CLIs.

    If the value is made of only Python literals and containers, then the value
    is parsed as it's Python value. Otherwise, provided the value contains no
    quote, escape, or parenthetical characters, the value is treated as a string.

    Args:
      value: A string from the command line to be parsed for use in a Fire CLI.
    Returns:
      The parsed value, of the type determined most appropriate.
    """
    # Note: _LiteralEval will treat '#' as the start of a comment.
    try:
        return _LiteralEval(value)
    except (SyntaxError, ValueError):
        # If _LiteralEval can't parse the value, treat it as a string.
        return value


def _LiteralEval(value):
    """Parse value as a Python literal, or container of containers and literals.

    First the AST of the value is updated so that bare-words are turned into
    strings. Then the resulting AST is evaluated as a literal or container of
    only containers and literals.

    This allows for the YAML-like syntax {a: b} to represent the dict {'a': 'b'}

    Args:
      value: A string to be parsed as a literal or container of containers and
        literals.
    Returns:
      The Python value representing the value arg.
    Raises:
      ValueError: If the value is not an expression with only containers and
        literals.
      SyntaxError: If the value string has a syntax error.
    """
    root = ast.parse(value, mode="eval")
    if isinstance(root.body, ast.BinOp):  # pytype: disable=attribute-error
        raise ValueError(value)

    for node in ast.walk(root):
        for field, child in ast.iter_fields(node):
            if isinstance(child, list):
                for index, subchild in enumerate(child):
                    if isinstance(subchild, ast.Name):
                        child[index] = _Replacement(subchild)

            elif isinstance(child, ast.Name):
                replacement = _Replacement(child)
                setattr(node, field, replacement)

    # ast.literal_eval supports the following types:
    # strings, bytes, numbers, tuples, lists, dicts, sets, booleans, and None
    # (bytes and set literals only starting with Python 3.2)
    return ast.literal_eval(root)


def _Replacement(node):
    """Returns a node to use in place of the supplied node in the AST.

    Args:
      node: A node of type Name. Could be a variable, or builtin constant.
    Returns:
      A node to use in place of the supplied Node. Either the same node, or a
      String node whose value matches the Name node's id.
    """
    value = node.id
    # These are the only builtin constants supported by literal_eval.
    if value in ("True", "False", "None"):
        return node
    return ast.Str(value)
