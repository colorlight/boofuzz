import collections

from .block import Block
from .aligned import Aligned
from .. import exception, helpers
from ..fuzzable import Fuzzable
from ..mutation_context import MutationContext


class Request(Fuzzable):
    def __init__(self, name):
        """
        Top level container instantiated by s_initialize(). Can hold any block structure or primitive. This can
        essentially be thought of as a super-block, root-block, daddy-block or whatever other alias you prefer.

        @type  name: str
        @param name: Name of this request
        """

        self._name = name
        self.label = name  # node label for graph rendering.
        self.stack = []  # the request stack.
        self.block_stack = []  # list of open blocks, -1 is last open block.
        self.closed_blocks = {}  # dictionary of closed blocks.
        # dictionary of list of sizers / checksums that were unable to complete rendering:
        self.callbacks = collections.defaultdict(list)
        self.names = {}  # dictionary of directly accessible primitives.
        self._rendered = b""  # rendered block structure.
        self._mutant_index = 0  # current mutation index.
        self._element_mutant_index = None  # index of current mutant element within self.stack
        self.mutant = None  # current primitive being mutated.

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def fuzzable(self):
        return True

    @property
    def original_value(self):
        # ensure there are no open blocks lingering.
        if self.block_stack:
            raise exception.SullyRuntimeError("UNCLOSED BLOCK: %s" % self.block_stack[-1].name)

        self._rendered = b""

        for item in self.stack:
            self._rendered += helpers.str_to_bytes(item.original_value)

        return self._rendered

    def mutations(self):
        for item in self.stack:
            self.mutant = item
            for mutation in item.mutations():
                yield mutation

    def num_mutations(self, default_value=None):  # TODO: default_value=None is a way of simulating FuzzableWrapper which does not take default_value
        """
        Determine the number of repetitions we will be making.

        @rtype:  int
        @return: Number of mutated forms this primitive can take.
        :param default_value:
        """
        num_mutations = 0

        for item in self.stack:
            if item.fuzzable:
                num_mutations += item.num_mutations()

        return num_mutations

    def pop(self):
        """
        The last open block was closed, so pop it off of the block stack.
        """

        if not self.block_stack:
            raise exception.SullyRuntimeError("BLOCK STACK OUT OF SYNC")

        self.block_stack.pop()

    def push(self, item):
        """
        Push an item into the block structure. If no block is open, the item goes onto the request stack. otherwise,
        the item goes onto the last open blocks stack.

        @type item: BasePrimitive | Block | Request | Size | Repeat
        @param item: Some primitive/block/request/etc.
        """
        context_path = ".".join(x.name for x in self.block_stack)  # TODO put in method
        context_path = ".".join(filter(None,(self.name, context_path)))
        item.context_path = context_path
        # ensure the name doesn't already exist.
        if item.name in list(self.names):
            raise exception.SullyRuntimeError("BLOCK NAME ALREADY EXISTS: %s" % item.name)

        self.names[item.name] = item

        # if there are no open blocks, the item gets pushed onto the request stack.
        # otherwise, the pushed item goes onto the stack of the last opened block.
        if not self.block_stack:
            self.stack.append(item)
        else:
            self.block_stack[-1].fuzz_object.push(item)

        # add the opened block to the block stack.
        if isinstance(item, Block) or isinstance(item, Aligned) or isinstance(item.fuzz_object, Block) or isinstance(item.fuzz_object, Aligned):  # TODO generic check here
            self.block_stack.append(item)

    def render_mutated(self, mutation_context):
        return self.get_child_data(mutation_context=mutation_context)

    def get_child_data(self, mutation_context):
        """

        :param mutation_context:
        :type mutation_context: MutationContext
        :return:
        """
        if self.block_stack:
            raise exception.SullyRuntimeError("UNCLOSED BLOCK: %s" % self.block_stack[-1].name)

        _rendered = b""
        for item in self.stack:
            _rendered += item.render_mutated(mutation_context=mutation_context)

        return helpers.str_to_bytes(_rendered)

    def walk(self, stack=None):
        """
        Recursively walk through and yield every primitive and block on the request stack.

        @param stack: Set to none -- used internally by recursive calls.
                      If None, uses self.stack.

        @rtype:  Sulley Primitives
        @return: Sulley Primitives
        """

        if not stack:
            stack = self.stack

        for item in stack:
            # if the item is a block, step into it and continue looping.
            if isinstance(item, Block) or isinstance(item, Aligned) or isinstance(item.fuzz_object,
                                                                                  Block) or isinstance(item.fuzz_object,
                                                                                                       Aligned):  # TODO generic check here
                for stack_item in self.walk(item.stack):
                    yield stack_item
            else:
                yield item

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.name)

    def __len__(self):
        length = 0
        for item in self.stack:
            length += len(item)
        return length

    def __bool__(self):
        """
        Make sure instances evaluate to True even if __len__ is zero.

        :return: True
        """
        return True
