from abc import ABC


class Widget(ABC):
    WIDGET_TYPE = 'BASE'

    def __init__(self, key, value):
        self.value = value
        self.key = key


class Text(Widget):
    WIDGET_TYPE = 'TEXT'

    def __init__(self, value, key=None):
        if not key:
            key = value

        super().__init__(key, value)


class TextInput(Widget):
    WIDGET_TYPE = 'TEXT_INPUT'

    def __init__(self, value, label, key=None):
        if not key:
            key = label

        super().__init__(key, value)
        self.label = label
