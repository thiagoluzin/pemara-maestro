import os
import sys
import psutil
import time
import subprocess

# Portas utilizadas pelo Pemara v4.0 e suas ferramentas
PORTAS_ALVO = [
    8001, 8002, 8003, 8004, 8005, 8006, 8007,  # Microserviços
    9500,  # Frontend HTTP
    8188,  # ComfyUI
    3002,  # Perplexica
    7860,  # TripoSG
    3000,  # OpenHands
    5005,  # Gerador Sprunki
]

def matar_processo_forcado(pid):
    """
    Executa comandos de força bruta no Windows para derrubar um processo
    quando psutil falha por falta de permissões ou travamento.
    """
    try:
        # Método 1: taskkill tradicional
        subprocess.run(["taskkill", "/F", "/PID", str(pid), "/T"], capture_output=True, text=True)
        if not psutil.pid_exists(pid):
            return True
            
        # Método 2: PowerShell Stop-Process
        subprocess.run(["powershell", "-Command", f"Stop-Process -Id {pid} -Force"], capture_output=True, text=True)
        if not psutil.pid_exists(pid):
            return True
            
        # Método 3: WMI via PowerShell (Invoke-WmiMethod)
        subprocess.run(["powershell", "-Command", f"Invoke-WmiMethod -Path 'Win32_Process.Handle={pid}' -Name Terminate"], capture_output=True, text=True)
        if not psutil.pid_exists(pid):
            return True
            
        # Método 4: CIM via PowerShell (Invoke-CimMethod)
        subprocess.run(["powershell", "-Command", f"Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}' | Invoke-CimMethod -MethodName Terminate"], capture_output=True, text=True)
        if not psutil.pid_exists(pid):
            return True
            
    except Exception as e:
        print(f"  [ERRO] Falha ao executar comandos de força bruta para PID {pid}: {e}")
    return not psutil.pid_exists(pid)

def matar_processo_e_filhos(pid):
    try:
        parent = psutil.Process(pid)
        try:
            children = parent.children(recursive=True)
        except Exception:
            children = []
        
        # Tenta encerrar graciosamente primeiro
        for child in children:
            try:
                child.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        try:
            parent.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        # Aguarda 2 segundos
        gone, alive = psutil.wait_procs(children + [parent], timeout=2.0)
        
        # Força o encerramento se ainda estiverem vivos
        for p in alive:
            try:
                p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                matar_processo_forcado(p.pid)
                
        # Double check: se ainda existirem, força neles
        ainda_vivos = [p for p in (children + [parent]) if psutil.pid_exists(p.pid)]
        for p in ainda_vivos:
            matar_processo_forcado(p.pid)
            
        if psutil.pid_exists(pid):
            return matar_processo_forcado(pid)
        return True
    except psutil.NoSuchProcess:
        return False
    except psutil.AccessDenied:
        print(f"  [AVISO] Acesso negado ao tentar encerrar o processo PID {pid}. Utilizando força bruta...")
        return matar_processo_forcado(pid)
    except Exception as e:
        print(f"  [ERRO] Falha ao encerrar PID {pid}: {e}")
        return matar_processo_forcado(pid)

def desbloquear_portas():
    print("="*60)
    print("  DESBLOQUEADOR DO PEMARA v4.0")
    print("  Procurando processos presos nas portas do sistema...")
    print("="*60)
    
    processos_mortos = set()
    encontrou_algo = False

    for conn in psutil.net_connections(kind='inet'):
        if conn.laddr.port in PORTAS_ALVO and conn.status == 'LISTEN':
            pid = conn.pid
            porta = conn.laddr.port
            if pid and pid not in processos_mortos:
                encontrou_algo = True
                try:
                    p = psutil.Process(pid)
                    nome_processo = p.name()
                    print(f"\n> Porta {porta} bloqueada por: {nome_processo} (PID {pid})")
                    print(f"  Tentando encerrar árvore de processos...")
                    
                    if matar_processo_e_filhos(pid):
                        print(f"  [OK] Processo e dependentes encerrados com sucesso.")
                        processos_mortos.add(pid)
                    else:
                        print(f"  [FALHA] Não foi possível encerrar.")
                except psutil.NoSuchProcess:
                    pass
                except psutil.AccessDenied:
                    print(f"\n> Porta {porta} bloqueada pelo PID {pid}")
                    print(f"  [AVISO] Acesso negado. Tentando encerramento forçado WMI/PowerShell...")
                    if matar_processo_forcado(pid):
                        print(f"  [OK] Processo encerrado via força bruta.")
                        processos_mortos.add(pid)
                    else:
                        print(f"  [FALHA] Não foi possível derrubar o processo mesmo com força bruta.")

    if not encontrou_algo:
        print("\n[OK] Nenhuma porta do Pemara parece estar bloqueada.")
    else:
        print("\n[OK] Limpeza de portas concluída.")

def matar_todos_python_restantes():
    print("\n" + "="*60)
    print("  ENCERRANDO PROCESSOS PYTHON FANTASMAS")
    print("="*60)
    
    meu_pid = os.getpid()
    nomes_alvo = ["python.exe", "pythonw.exe"]
    encontrou_python = False
    
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            pid = proc.info['pid']
            name = proc.info['name']
            
            if pid == meu_pid:
                continue
                
            if name and name.lower() in nomes_alvo:
                # Evitar matar o agente de monitoramento (radar_monitor.py)
                try:
                    cmdline = proc.cmdline()
                    if cmdline and any("radar_monitor.py" in arg.lower() for arg in cmdline):
                        continue
                except Exception:
                    pass
                
                encontrou_python = True
                print(f"> Processo Python encontrado: PID {pid} ({name}) - Encerrando...")
                matar_processo_e_filhos(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
    if not encontrou_python:
        print("[OK] Nenhum outro processo Python pendente detectado.")
    else:
        print("[OK] Todos os outros processos Python foram eliminados.")

def limpar_arquivos_temporarios():
    print("\n" + "="*60)
    print("  LIMPANDO CACHE E ARQUIVOS TEMPORÁRIOS DO PYTHON")
    print("="*60)
    
    root_dir = os.path.dirname(os.path.abspath(__file__))
    pemara_dir = os.path.join(root_dir, 'pemara')
    
    apagados = 0
    if os.path.exists(pemara_dir):
        import shutil
        for dp, dn, filenames in os.walk(pemara_dir, topdown=False):
            # Apagar .pyc
            for f in filenames:
                if f.endswith('.pyc'):
                    pyc_path = os.path.join(dp, f)
                    try:
                        os.remove(pyc_path)
                        apagados += 1
                    except:
                        pass
            
            # Apagar __pycache__
            for d in dn:
                if d == '__pycache__':
                    pycache_path = os.path.join(dp, d)
                    try:
                        shutil.rmtree(pycache_path)
                        apagados += 1
                    except:
                        pass
                        
    if apagados > 0:
        print(f"[OK] Limpos {apagados} arquivos de cache/temporários do sistema.")
    else:
        print("[OK] Nenhum cache pendente para limpar.")

if __name__ == "__main__":
    desbloquear_portas()
    matar_todos_python_restantes()
    limpar_arquivos_temporarios()
    print("\n="*60)
    print("  SISTEMA PRONTO PARA UMA NOVA INICIALIZAÇÃO")
    print("="*60)
    time.sleep(3)
