#!/usr/bin/env python
# Copyright (C) 2020 - 2022  UserbotIndo Team, <https://github.com/userbotindo.git>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from inspect import signature

import pytest

from anjani.error import BadArgument
from anjani.util.converter import parse_arguments

from . import Context, Message

args = [1, 2, 3, 4, 5]
args_str = " ".join(map(str, args))
context = Context(message=Message(text="/test " + args_str))
no_args_context = Context(message=Message(text="/test"))


async def no_args(ctx):
    ...


async def one_arg(ctx, arg):
    ...


async def one_arg_with_default(ctx, arg=0):
    ...


async def one_arg_with_type(ctx, arg: int):
    ...


async def one_arg_with_default_and_type(ctx, arg: int = 0):
    ...


async def kwarg_only(ctx, *, kwarg):
    ...


async def kwarg_only_with_default(ctx, *, kwarg=1):
    ...


async def var_positional(ctx, *args):
    ...


async def var_keyword(ctx, **kwargs):
    ...


class TestBaseConverter:
    async def __parse_arguments(self, func):
        return await parse_arguments(signature(func), context, func)  # type: ignore

    async def __parse_arguments_no_args(self, func):
        return await parse_arguments(signature(func), no_args_context, func)  # type: ignore

    @pytest.mark.asyncio
    async def test_no_args(self):
        args, kwargs = await self.__parse_arguments(no_args)
        assert args == []
        assert kwargs == {}

    @pytest.mark.asyncio
    async def test_one_arg(self):
        args, kwargs = await self.__parse_arguments(one_arg)
        assert args == ["1"]
        assert kwargs == {}

    @pytest.mark.asyncio
    async def test_one_arg_with_default(self):
        args, kwargs = await self.__parse_arguments(one_arg_with_default)
        assert args == ["1"]
        assert kwargs == {}

        args, kwargs = await self.__parse_arguments_no_args(one_arg_with_default)
        assert args == [0]
        assert kwargs == {}

    @pytest.mark.asyncio
    async def test_one_arg_with_type(self):
        args, kwargs = await self.__parse_arguments(one_arg_with_type)
        assert args == [1]
        assert kwargs == {}

        args, kwargs = await self.__parse_arguments_no_args(one_arg_with_type)
        assert args == [None]
        assert kwargs == {}

    @pytest.mark.asyncio
    async def test_one_arg_with_default_and_type(self):
        args, kwargs = await self.__parse_arguments(one_arg_with_default_and_type)
        assert args == [1]
        assert kwargs == {}

        args, kwargs = await self.__parse_arguments_no_args(one_arg_with_default_and_type)
        assert args == [0]
        assert kwargs == {}

    @pytest.mark.asyncio
    async def test_kwarg_only(self):
        args, kwargs = await self.__parse_arguments(kwarg_only)
        assert args == []
        assert kwargs == {"kwarg": args_str}

        args, kwargs = await self.__parse_arguments_no_args(kwarg_only)
        assert args == []
        assert kwargs == {"kwarg": ""}

    @pytest.mark.asyncio
    async def test_kwarg_only_with_default(self):
        args, kwargs = await self.__parse_arguments(kwarg_only_with_default)
        assert args == []
        assert kwargs == {"kwarg": args_str}

        args, kwargs = await self.__parse_arguments_no_args(kwarg_only_with_default)
        assert args == []
        assert kwargs == {"kwarg": ""}

    @pytest.mark.asyncio
    async def test_var_positional(self):
        with pytest.raises(BadArgument):
            await self.__parse_arguments(var_positional)
            await self.__parse_arguments_no_args(var_positional)

    @pytest.mark.asyncio
    async def test_var_keyword(self):
        with pytest.raises(BadArgument):
            await self.__parse_arguments(var_keyword)
            await self.__parse_arguments_no_args(var_keyword)
