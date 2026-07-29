import ast
import sys

filename = r'c:\Proyecto_Final_Web\isben_solution\core\views.py'
try:
    with open(filename, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read(), filename=filename)
    
    functions = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)
            
    print(f'Total views: {len(functions)}')
    
    # Agrupar en lotes lógicos o simplemente imprimir los primeros para entender
    for f in functions:
        print(f)
except Exception as e:
    print('Error:', e)
