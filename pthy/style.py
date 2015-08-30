from pygments.style import Style
from pygments.styles.monokai import MonokaiStyle
from pygments.token import Token


class HyStyle(Style):
    styles = MonokaiStyle.styles.copy()

    styles.update({
        Token.MatchingBracket : '#FF6600'
    })
