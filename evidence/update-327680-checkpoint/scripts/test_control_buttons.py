import ast,unittest
from pathlib import Path
from types import SimpleNamespace
W=Path(__file__).resolve().parent
class ButtonSafety(unittest.TestCase):
 def test_individual_plus_allowed_but_exit_chord_refused(self):
  tree=ast.parse((W/'control.py').read_text());n=next(n for n in ast.walk(tree) if isinstance(n,ast.Assert) and '0xc00' in ast.get_source_segment((W/'control.py').read_text(),n))
  expression=compile(ast.Expression(n.test),'<real-controller-guard>','eval')
  for mask,allow in [(0,True),(1,True),(0x400,True),(0x800,True),(0xc00,False),(0x10000,False)]:
   with self.subTest(mask=hex(mask)):self.assertEqual(bool(eval(expression,{'a':SimpleNamespace(ms=80,delay=2,buttons=mask)})),allow)
if __name__=='__main__':unittest.main()
