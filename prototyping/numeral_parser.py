import operator
import functools
from lark import Lark, Transformer, Token
from pprint import pprint
WORDS_TO_NUMBERS = {
  "zero" : 0,
  "zéro" : 0,
  "un" : 1,
  "une" : 1,
  "deux" : 2,
  "trois" : 3,
  "quatre" : 4,
  "cinq" : 5,
  "six" : 6,
  "sept" : 7,
  "huit" : 8,
  "neuf" : 9,
  "dix" : 10,
  "onze" : 11,
  "douze" : 12,
  "treize" : 13,
  "quatorze" : 14,
  "quinze" : 15,
  "seize" : 16,
  "vingt": 20,
  "trente": 30,
  "quarante": 40,
  "cinquante": 50,
  "soixante": 60,
  "cent": 100,
  "mille": 1_000,
  "million": 1_000_000,
  "millions": 1_000_000,
  "milliard": 1_000_000_000,
  "milliards": 1_000_000_000,
}
class NumberTransformer(Transformer):
  def integer_numeral(self, t):
    (v,) = t
    return (operator.add, int(v))
  def numeral(self, t):
    (v,) = t
    return (operator.add, WORDS_TO_NUMBERS.get(v))
  
  def numeral2(self, t):
    (v,) = t
    return (operator.add, WORDS_TO_NUMBERS.get(v))
  def numeral4(self, t):
    return (operator.add, 80)
  def powers_of_ten(self, t):
    (v,) = t
    return (operator.mul, WORDS_TO_NUMBERS.get(v))
  def ANYTHING(self, t):
    return t
  def rules(self, t):
    return t[0]
  def start(self, v):
    val = 0
    acc = []
    for item in v:
      if isinstance(item, Token):
        # TODO got anything, that's probably another number!
        continue
      (op, arg) = item
      val = op(val, arg)
      if op == operator.mul:
        if not val and acc:
          val = op(acc.pop(), arg)
          
        acc.append(val if val else arg)
        val = 0
    acc.append(val)
    
    return functools.reduce(operator.add, acc)
parser = Lark(r"""
                    
integer_numeral: /(\d+)/
decimal_numeral: /(\d*,\d+)/
decimal_with_thousands_separator: /(\d+(([\. ])\d\d\d)+,\d+)/
integer_with_thousands_separator: /(\d{1,3}(([\. ])\d\d\d){1,5})/
numeral: /(z(e|é)ro|une?|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze|treize|quatorze|quinze|seize)/
numeral2: /(vingt|trente|quarante|cinquante|soixante)/
numeral4: /quatre[ -]vingts?/
powers_of_ten: /(cent|mille|millions?|milliards?)/
ANYTHING.0: /[a-z]+/
rules: decimal_numeral
  | decimal_with_thousands_separator
  | integer_with_thousands_separator
  | integer_numeral
  | numeral
  | numeral2
  | numeral4
  | powers_of_ten
  | ANYTHING
start: rules*
%import common.WS
%ignore WS
%ignore /-/
""", parser="lalr", transformer=NumberTransformer())
tests = {
  'quatre mille vingt': 4020,
  'un million deux cent mille': 1_200_000,
  'un million deux cent mille 2 cent 23': 1_200_223,
  'cent mille': 100_000,
  'cinq centre quatre vingt 2': 582,
  'soixante dix huit': 78,
  'quatre vingt douze': 92,
}
for text, expected in tests.items():
  print(text, '=>', 'expected', expected, 'got', parser.parse(text))