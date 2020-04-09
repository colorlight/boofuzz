from ..fuzzable import Fuzzable
from ..mutation import Mutation


class Aligned(Fuzzable):
    """
    This block type is kind of special in that it is a hybrid between a block and a primitive (it can be fuzzed). The
    user does not need to be wary of this fact.
    """

    def __init__(
            self,
            request,
            modulus,
            pattern="\x00",
    ):
        """
        Create a sizer block bound to the block with the specified name. Size blocks that size their own parent or
        grandparent are allowed.

        :type  request:       Request
        :param request:       Request this block belongs to
        :type  modulus:     int
        :param modulus:     Pad length of child content to this many bytes
        :type  pattern:     bytes
        :param pattern:     Pad using these byte(s)
        """
        self.request = request
        self._modulus = modulus
        self._pattern = pattern

        self.stack = []  # block item stack.

    def mutations(self):
        for item in self.stack:
            self.request.mutant = item
            for mutation in item.mutations():
                yield mutation

    def num_mutations(self, default_value):
        """
        Wrap the num_mutations routine of the internal bit_field primitive.

        :param default_value:
        :rtype:  int
        :return: Number of mutated forms this primitive can take.
        """
        num_mutations = 0

        for item in self.stack:
            if item.fuzzable:
                num_mutations += item.num_mutations()
        return num_mutations

    def _align_it(self, data):
        """Align data.

        :param data: bytes to align
        :type data: bytes
        :return: data aligned to this object's modulus using pattern
        :rtype: bytes
        """
        padding_length = self._modulus - (len(data) % self._modulus)
        a, b = divmod(padding_length, len(self._pattern))
        return data + self._pattern * a + self._pattern[:b]

    def encode(self, value, child_data, mutation_context):
        return self._align_it(child_data)

    def get_child_data(self, mutation_context):
        rendered = b""
        for item in self.stack:
            rendered += item.render_mutated(mutation_context=mutation_context)
        return rendered

    def push(self, item):
        """
        Push an arbitrary item onto this blocks stack.
        @type item: BasePrimitive | Block | boofuzz.blocks.size.Size | boofuzz.blocks.repeat.Repeat
        @param item: Some primitive/block/etc.
        """

        self.stack.append(item)

    def __len__(self):
        return len(self.render())

    def __bool__(self):
        """
        Make sure instances evaluate to True even if __len__ is zero.

        :return: True
        """
        return True
