# Dash in the class issue

If dash in the class occurs between single character range and closing bracket,
then closed bracket is treated as the boundary of a range: `[0-9_-]` results
in `0-9` and `_-]`, and the rest of the grammar is captured.

```
Grammar(
  [
    Rule(Id('Grammar'), Expr([
      Alt([
        NamedItem(None, Id('A')),
        NamedItem(None, Id('Char1')),
        NamedItem(None, Id('B')),
        NamedItem(None, Id('Char2')),
        NamedItem(None, Id('EOF'))])
      ]), entry=True),
    Rule(Id('A'), Expr([
      Alt([NamedItem(None, Char('a'))]),
      Alt([NamedItem(None, Char('b'))])])),
    Rule(Id('Char1'), Expr([
      Alt([
        NamedItem(None,
          Class([
              Range(Char('0'), Char('9')),
              Range(Char('_'), Char(']')),
              # The rest of the grammar captured
              Range(Char('\n'), None),
              Range(Char('B'), None),
              Range(Char(' '), None),
              Range(Char('<'), Char(' ')),
              Range(Char("'"), None),
              Range(Char('c'), None),
              Range(Char("'"), None),
              Range(Char(' '), None),
              Range(Char('/'), None),
              Range(Char(' '), None),
              Range(Char("'"), None),
              Range(Char('d'), None),
              Range(Char("'"), None),
              Range(Char('\n'), None),
              Range(Char('C'), None),
              Range(Char('h'), None),
              Range(Char('a'), None),
              Range(Char('r'), None),
              Range(Char('2'), None),
              Range(Char(' '), None),
              Range(Char('<'), Char(' ')),
              Range(Char('['), None),
              Range(Char('x'), Char('z'))
          ]))
        ])
      ])),
    Rule(Id('EOF'), Expr([Alt([NamedItem(None, Not(AnyChar()))])])),
  ],
[]
)

```
