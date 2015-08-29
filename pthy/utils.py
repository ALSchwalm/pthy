from hy.lex import lexer


def get_tokens_in_current_sexp(document):
    text = document.text_before_cursor
    tokens = list(lexer.lex(text))

    counts = [0, 0, 0]
    for i, token in enumerate(tokens[::-1]):
        if token.name == "RPAREN":
            counts[0] += 1
        elif token.name == "RBRACKET":
            counts[1] += 1
        elif token.name == "RCURLY":
            counts[2] += 1
        elif token.name in ("LPAREN", "LBRACKET", "LCURLY"):
            if counts[0] == 0 and counts[1] == 0 and counts[1] == 0:
                break
            if token.name == "LPAREN":
                counts[0] -= 1
            elif token.name == "LBRACKET":
                counts[1] -= 1
            elif token.name == "LCURLY":
                counts[2] -= 1
    return tokens[len(tokens)-i:]
