import os
import shutil
import re

def limpar_ambiente():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backup_dir = os.path.join(root_dir, '_OLD_BACKUPS')
    
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        print(f"Pasta criada: {backup_dir}")
        
    duplicate_pattern = re.compile(r'\(\d+\)')
    
    for dp, dn, filenames in os.walk(root_dir):
        if '_OLD_BACKUPS' in dp.split(os.sep):
            continue
            
        for f in filenames:
            file_path = os.path.join(dp, f)
            move_file = False
            
            # .bak files
            if f.endswith('.bak'):
                move_file = True
            # duplicate files like name (1).py
            elif duplicate_pattern.search(f):
                move_file = True
            # .txt files outside dados/logs, excluding requirements
            elif f.endswith('.txt') and 'requirements' not in f.lower():
                path_parts = dp.split(os.sep)
                is_in_logs = 'dados' in path_parts and 'logs' in path_parts
                if not is_in_logs:
                    move_file = True
            
            if move_file:
                dst = os.path.join(backup_dir, f)
                base, ext = os.path.splitext(f)
                counter = 1
                while os.path.exists(dst):
                    dst = os.path.join(backup_dir, f"{base}_{counter}{ext}")
                    counter += 1
                try:
                    shutil.move(file_path, dst)
                    print(f"Movido: {file_path} -> {dst}")
                except Exception as e:
                    print(f"Erro ao mover {file_path}: {e}")

    # Clean __pycache__ and .pyc in pemara/
    pemara_dir = os.path.join(root_dir, 'pemara')
    if os.path.exists(pemara_dir):
        for dp, dn, filenames in os.walk(pemara_dir, topdown=False):
            for f in filenames:
                if f.endswith('.pyc'):
                    pyc_path = os.path.join(dp, f)
                    try:
                        os.remove(pyc_path)
                        print(f"Apagado: {pyc_path}")
                    except Exception as e:
                        pass
            
            for d in dn:
                if d == '__pycache__':
                    pycache_path = os.path.join(dp, d)
                    try:
                        shutil.rmtree(pycache_path)
                        print(f"Apagado: {pycache_path}")
                    except Exception as e:
                        pass

if __name__ == '__main__':
    limpar_ambiente()
