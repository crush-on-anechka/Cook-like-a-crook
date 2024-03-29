import re
from django.core.exceptions import ValidationError


def validate_name(value):
    reg = re.compile('^[-a-zA-Z0-9_]+$')
    if not reg.match(value):
        raise ValidationError(
            'Enter a valid “name” consisting of letters, '
            'numbers, underscores or hyphens.'
            )


def validate_color(value):
    reg = re.compile('^#([a-f0-9]{6})$')
    if not reg.match(value):
        raise ValidationError(
            'Enter a valid HEX code starting with # and consisting '
            'of 6 symbols which are letters a-f or numbers.'
        )
