from inspect import isgeneratorfunction
from asyncio import iscoroutinefunction
from functools import update_wrapper
from typing import Callable, Dict, Generic, List, Tuple, TypeVar
from .validator import RaisesValidator, Validator
from .._state import state
from .._exceptions import ContractError


F = TypeVar('F', bound=Callable)
ATTR = '__deal_contract'


class Contracts(Generic[F]):
    func: F
    wrapped: F
    pres: List[Validator]
    posts: List[Validator]
    ensures: List[Validator]
    examples: List[Validator]
    raises: List[RaisesValidator]

    def __init__(self, func: F):
        self.func = func
        self.pres = []
        self.posts = []
        self.ensures = []
        self.examples = []
        self.raises = []

    @classmethod
    def attach(cls, contract_type: str, validator: Validator, func: F) -> F:
        contracts = cls.ensure_wrapped(func)
        validator.function = func
        getattr(contracts, contract_type).append(validator)
        return contracts.wrapped

    @classmethod
    def ensure_wrapped(cls, func: F) -> 'Contracts[F]':
        contracts = getattr(func, ATTR, None)
        if contracts is not None:
            return contracts
        contracts = cls(func)

        if iscoroutinefunction(func):
            async def wrapper(*args, **kwargs):
                return await contracts.run_async(args, kwargs)
        elif isgeneratorfunction(func):
            def wrapper(*args, **kwargs):
                yield from contracts.run_iter(args, kwargs)
        else:
            def wrapper(*args, **kwargs):
                return contracts.run_sync(args, kwargs)

        update_wrapper(wrapper=wrapper, wrapped=func)
        setattr(wrapper, ATTR, contracts)
        contracts.wrapped = wrapper  # type: ignore[assignment]
        return contracts

    def run_sync(self, args: Tuple[object], kwargs: Dict[str, object]):
        if not state.debug:
            return self.func(*args, **kwargs)

        # pre-validation
        state.debug = False
        try:
            for validator in self.pres:
                validator.validate(*args, **kwargs)
        finally:
            state.debug = True

        # running the function
        try:
            result = self.func(*args, **kwargs)
        except ContractError:
            raise
        except Exception as exc:
            for validator in self.raises:
                validator.validate(exc, args, kwargs)
            raise

        # post-validation
        state.debug = False
        try:
            for validator in self.posts:
                validator.validate(result)
            for validator in self.ensures:
                validator.validate(*args, **kwargs, result=result)
        finally:
            state.debug = True

        return result

    async def run_async(self, args: Tuple[object], kwargs: Dict[str, object]):
        if not state.debug:
            return await self.func(*args, **kwargs)

        # pre-validation
        state.debug = False
        try:
            for validator in self.pres:
                validator.validate(*args, **kwargs)
        finally:
            state.debug = True

        # running the function
        try:
            result = await self.func(*args, **kwargs)
        except ContractError:
            raise
        except Exception as exc:
            for validator in self.raises:
                validator.validate(exc, args, kwargs)
            raise

        # post-validation
        state.debug = False
        try:
            for validator in self.posts:
                validator.validate(result)
            for validator in self.ensures:
                validator.validate(*args, **kwargs, result=result)
        finally:
            state.debug = True

        return result

    def run_iter(self, args: Tuple[object], kwargs: Dict[str, object]):
        if not state.debug:
            yield from self.func(*args, **kwargs)

        # pre-validation
        state.debug = False
        try:
            for validator in self.pres:
                validator.validate(*args, **kwargs)
        finally:
            state.debug = True

        generator = self.func(*args, **kwargs)
        while True:
            # running the function
            try:
                result = next(generator)
            except StopIteration:
                return
            except ContractError:
                raise
            except Exception as exc:
                for validator in self.raises:
                    validator.validate(exc, args, kwargs)
                raise

            # post-validation
            state.debug = False
            try:
                for validator in self.posts:
                    validator.validate(result)
                for validator in self.ensures:
                    validator.validate(*args, **kwargs, result=result)
            finally:
                state.debug = True
            yield result
