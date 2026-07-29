import ast
import os

def analyze_file(filename, is_models=False):
    print(f"=== Analizando {filename} ===")
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=filename)
        
        items = []
        for node in tree.body:
            if is_models and isinstance(node, ast.ClassDef):
                items.append(node.name)
            elif not is_models and isinstance(node, ast.FunctionDef):
                items.append(node.name)
        
        for item in items:
            print(f"- {item}")
        print(f"Total: {len(items)}\n")
    except Exception as e:
        print('Error:', e)

analyze_file(r'c:\Proyecto_Final_Web\isben_solution\core\models.py', is_models=True)
analyze_file(r'c:\Proyecto_Final_Web\isben_solution\core\views.py', is_models=False)
