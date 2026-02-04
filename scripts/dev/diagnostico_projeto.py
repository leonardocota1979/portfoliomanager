#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║           DIAGNÓSTICO COMPLETO DO PROJETO - DETECTOR DE LIXO        ║
║                         Versão: 1.0.0                                ║
╚══════════════════════════════════════════════════════════════════════╝

DESCRIÇÃO:
    Script que analisa TUDO no projeto e identifica:
    - Onde estão os arquivos
    - O que é lixo
    - O que pode ser deletado
    - Quanto espaço vai liberar
    
EXECUÇÃO:
    python3 diagnostico_projeto.py
    
AUTOR: Claude (Anthropic)
DATA: 26 de Janeiro de 2026
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Cores para output
class Cor:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    VERDE = '\033[32m'
    AMARELO = '\033[33m'
    VERMELHO = '\033[31m'
    AZUL = '\033[34m'
    CIANO = '\033[36m'
    DIM = '\033[2m'

EMOJI = {
    'check': '✅', 'cross': '❌', 'warning': '⚠️',
    'folder': '📁', 'file': '📄', 'trash': '🗑️',
    'magnify': '🔍', 'chart': '📊', 'bomb': '💣',
}

# ═══════════════════════════════════════════════════════════════════════
# FUNÇÕES DE ANÁLISE
# ═══════════════════════════════════════════════════════════════════════

def contar_arquivos_recursivo(pasta):
    """
    Conta arquivos recursivamente em uma pasta
    
    Returns:
        (total_arquivos, total_tamanho_bytes)
    """
    total_arquivos = 0
    total_tamanho = 0
    
    try:
        for root, dirs, files in os.walk(pasta):
            total_arquivos += len(files)
            for f in files:
                try:
                    filepath = os.path.join(root, f)
                    total_tamanho += os.path.getsize(filepath)
                except:
                    pass
    except:
        pass
    
    return total_arquivos, total_tamanho

def formatar_tamanho(bytes):
    """Formata bytes em KB, MB, GB"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.1f}{unit}"
        bytes /= 1024.0
    return f"{bytes:.1f}TB"

def analisar_pasta(pasta, nivel=0):
    """
    Analisa uma pasta e retorna estatísticas
    
    Returns:
        dict com: arquivos, tamanho, subpastas
    """
    info = {
        'nome': pasta.name,
        'caminho': str(pasta),
        'arquivos': 0,
        'tamanho': 0,
        'subpastas': [],
        'nivel': nivel
    }
    
    if not pasta.exists() or not pasta.is_dir():
        return info
    
    info['arquivos'], info['tamanho'] = contar_arquivos_recursivo(pasta)
    
    return info

def identificar_lixo(pasta_info):
    """
    Identifica se uma pasta é lixo baseado em padrões conhecidos
    
    Returns:
        (é_lixo, motivo, prioridade)
        prioridade: 1=CRÍTICO, 2=RECOMENDADO, 3=OPCIONAL
    """
    nome = pasta_info['nome'].lower()
    
    # LIXO CRÍTICO (pode deletar com segurança)
    lixo_critico = {
        'node_modules': 'Dependências JavaScript (projeto Python!)',
        '__pycache__': 'Cache Python (regenera automaticamente)',
        '.pytest_cache': 'Cache de testes',
        '.mypy_cache': 'Cache do MyPy',
        'htmlcov': 'Relatórios de cobertura de testes',
        'dist': 'Builds de distribuição',
        'build': 'Arquivos de build',
        '.eggs': 'Cache de eggs Python',
        '*.egg-info': 'Metadados de instalação',
    }
    
    for lixo, motivo in lixo_critico.items():
        if lixo.replace('*', '') in nome:
            return True, motivo, 1
    
    # LIXO RECOMENDADO (melhor deletar)
    lixo_recomendado = {
        '.venv': 'Ambiente virtual duplicado (já tem venv/)',
        'venv_old': 'Ambiente virtual antigo',
        'env': 'Outro ambiente virtual',
    }
    
    for lixo, motivo in lixo_recomendado.items():
        if nome == lixo:
            return True, motivo, 2
    
    # OPCIONAL (considerar deletar)
    if nome.startswith('.') and nome not in ['.git', '.env', '.gitignore', '.python-version']:
        return True, 'Arquivo/pasta oculto suspeito', 3
    
    return False, '', 0

# ═══════════════════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL DE DIAGNÓSTICO
# ═══════════════════════════════════════════════════════════════════════

def diagnosticar_projeto():
    """Executa diagnóstico completo do projeto"""
    
    print(f"\n{Cor.AZUL}{'='*70}{Cor.RESET}")
    print(f"{Cor.BOLD}{EMOJI['magnify']}  DIAGNÓSTICO COMPLETO DO PROJETO{Cor.RESET}")
    print(f"{Cor.AZUL}{'='*70}{Cor.RESET}\n")
    
    base_dir = Path.cwd()
    print(f"{Cor.CIANO}Diretório:{Cor.RESET} {base_dir}\n")
    
    # ═══════════════════════════════════════════════════════════════════
    # ETAPA 1: CONTAGEM GERAL
    # ═══════════════════════════════════════════════════════════════════
    
    print(f"{Cor.AMARELO}{'─'*70}{Cor.RESET}")
    print(f"{EMOJI['chart']} ETAPA 1: Contagem Geral")
    print(f"{Cor.AMARELO}{'─'*70}{Cor.RESET}\n")
    
    total_arquivos, total_tamanho = contar_arquivos_recursivo(base_dir)
    
    print(f"  Total de arquivos: {Cor.BOLD}{total_arquivos:,}{Cor.RESET}")
    print(f"  Tamanho total: {Cor.BOLD}{formatar_tamanho(total_tamanho)}{Cor.RESET}\n")
    
    # ═══════════════════════════════════════════════════════════════════
    # ETAPA 2: ANÁLISE POR PASTA (NÍVEL 1)
    # ═══════════════════════════════════════════════════════════════════
    
    print(f"{Cor.AMARELO}{'─'*70}{Cor.RESET}")
    print(f"{EMOJI['folder']} ETAPA 2: Análise de Pastas Principais")
    print(f"{Cor.AMARELO}{'─'*70}{Cor.RESET}\n")
    
    pastas_info = []
    
    # Analisa cada pasta no nível raiz
    for item in sorted(base_dir.iterdir()):
        if item.is_dir() and not item.name.startswith('.git'):
            info = analisar_pasta(item)
            pastas_info.append(info)
    
    # Ordena por número de arquivos (maior primeiro)
    pastas_info.sort(key=lambda x: x['arquivos'], reverse=True)
    
    # Mostra top 15
    print(f"  {'Pasta':<30} {'Arquivos':>10} {'Tamanho':>12}\n")
    
    for info in pastas_info[:15]:
        nome = info['nome']
        arquivos = info['arquivos']
        tamanho = formatar_tamanho(info['tamanho'])
        
        # Destaca pastas com muitos arquivos
        if arquivos > 1000:
            cor = Cor.VERMELHO
            icon = EMOJI['bomb']
        elif arquivos > 100:
            cor = Cor.AMARELO
            icon = EMOJI['warning']
        else:
            cor = Cor.VERDE
            icon = EMOJI['check']
        
        print(f"  {icon} {cor}{nome:<28}{Cor.RESET} {arquivos:>10,} {tamanho:>12}")
    
    print()
    
    # ═══════════════════════════════════════════════════════════════════
    # ETAPA 3: DETECTAR LIXO
    # ═══════════════════════════════════════════════════════════════════
    
    print(f"{Cor.AMARELO}{'─'*70}{Cor.RESET}")
    print(f"{EMOJI['trash']} ETAPA 3: Detecção de Lixo")
    print(f"{Cor.AMARELO}{'─'*70}{Cor.RESET}\n")
    
    lixo_encontrado = {
        1: [],  # Crítico
        2: [],  # Recomendado
        3: []   # Opcional
    }
    
    total_lixo_arquivos = 0
    total_lixo_tamanho = 0
    
    for info in pastas_info:
        é_lixo, motivo, prioridade = identificar_lixo(info)
        
        if é_lixo:
            lixo_encontrado[prioridade].append({
                'info': info,
                'motivo': motivo
            })
            total_lixo_arquivos += info['arquivos']
            total_lixo_tamanho += info['tamanho']
    
    # Mostra lixo por prioridade
    if lixo_encontrado[1]:
        print(f"{Cor.VERMELHO}{Cor.BOLD}🔥 LIXO CRÍTICO (PODE DELETAR COM SEGURANÇA):{Cor.RESET}\n")
        for item in lixo_encontrado[1]:
            info = item['info']
            print(f"  {EMOJI['cross']} {Cor.VERMELHO}{info['nome']}{Cor.RESET}")
            print(f"      Motivo: {item['motivo']}")
            print(f"      Arquivos: {info['arquivos']:,} | Tamanho: {formatar_tamanho(info['tamanho'])}")
            print(f"      Caminho: {Cor.DIM}{info['caminho']}{Cor.RESET}\n")
    
    if lixo_encontrado[2]:
        print(f"{Cor.AMARELO}{Cor.BOLD}⚠️  LIXO RECOMENDADO (MELHOR DELETAR):{Cor.RESET}\n")
        for item in lixo_encontrado[2]:
            info = item['info']
            print(f"  {EMOJI['warning']} {Cor.AMARELO}{info['nome']}{Cor.RESET}")
            print(f"      Motivo: {item['motivo']}")
            print(f"      Arquivos: {info['arquivos']:,} | Tamanho: {formatar_tamanho(info['tamanho'])}")
            print(f"      Caminho: {Cor.DIM}{info['caminho']}{Cor.RESET}\n")
    
    if not any(lixo_encontrado.values()):
        print(f"  {EMOJI['check']} {Cor.VERDE}Nenhum lixo óbvio detectado!{Cor.RESET}\n")
    
    # ═══════════════════════════════════════════════════════════════════
    # ETAPA 4: ANÁLISE PROFUNDA DO VENV
    # ═══════════════════════════════════════════════════════════════════
    
    print(f"{Cor.AMARELO}{'─'*70}{Cor.RESET}")
    print(f"{EMOJI['magnify']} ETAPA 4: Análise Detalhada do venv/")
    print(f"{Cor.AMARELO}{'─'*70}{Cor.RESET}\n")
    
    venv_path = base_dir / 'venv'
    if venv_path.exists():
        print(f"  Analisando venv/ em detalhes...\n")
        
        # Analisa subpastas do venv
        venv_subpastas = []
        for item in venv_path.iterdir():
            if item.is_dir():
                info = analisar_pasta(item)
                venv_subpastas.append(info)
        
        venv_subpastas.sort(key=lambda x: x['arquivos'], reverse=True)
        
        print(f"  {'Subpasta':<30} {'Arquivos':>10} {'Tamanho':>12}\n")
        
        for info in venv_subpastas[:10]:
            nome = info['nome']
            arquivos = info['arquivos']
            tamanho = formatar_tamanho(info['tamanho'])
            
            if arquivos > 500:
                cor = Cor.VERMELHO
            elif arquivos > 100:
                cor = Cor.AMARELO
            else:
                cor = Cor.VERDE
            
            print(f"    {cor}{nome:<28}{Cor.RESET} {arquivos:>10,} {tamanho:>12}")
        
        print()
    
    # ═══════════════════════════════════════════════════════════════════
    # RESUMO FINAL
    # ═══════════════════════════════════════════════════════════════════
    
    print(f"{Cor.AZUL}{'='*70}{Cor.RESET}")
    print(f"{Cor.BOLD}{EMOJI['chart']} RESUMO DO DIAGNÓSTICO{Cor.RESET}")
    print(f"{Cor.AZUL}{'='*70}{Cor.RESET}\n")
    
    print(f"  Total de arquivos no projeto: {Cor.BOLD}{total_arquivos:,}{Cor.RESET}")
    print(f"  Tamanho total: {Cor.BOLD}{formatar_tamanho(total_tamanho)}{Cor.RESET}\n")
    
    if total_lixo_arquivos > 0:
        print(f"  {EMOJI['trash']} Lixo detectado:")
        print(f"      Arquivos: {Cor.VERMELHO}{total_lixo_arquivos:,}{Cor.RESET}")
        print(f"      Tamanho: {Cor.VERMELHO}{formatar_tamanho(total_lixo_tamanho)}{Cor.RESET}")
        print(f"      Economia: {Cor.VERDE}{(total_lixo_tamanho/total_tamanho*100):.1f}%{Cor.RESET}\n")
    
    # ═══════════════════════════════════════════════════════════════════
    # RECOMENDAÇÕES
    # ═══════════════════════════════════════════════════════════════════
    
    print(f"{Cor.AZUL}{'='*70}{Cor.RESET}")
    print(f"{Cor.BOLD}💡 RECOMENDAÇÕES{Cor.RESET}")
    print(f"{Cor.AZUL}{'='*70}{Cor.RESET}\n")
    
    if lixo_encontrado[1]:
        print(f"{Cor.VERMELHO}1. DELETAR IMEDIATAMENTE:{Cor.RESET}")
        for item in lixo_encontrado[1]:
            print(f"   rm -rf {item['info']['caminho']}")
        print()
    
    if lixo_encontrado[2]:
        print(f"{Cor.AMARELO}2. CONSIDERAR DELETAR:{Cor.RESET}")
        for item in lixo_encontrado[2]:
            print(f"   rm -rf {item['info']['caminho']}")
        print()
    
    # Análise específica para venv grande
    venv_info = next((p for p in pastas_info if p['nome'] == 'venv'), None)
    if venv_info and venv_info['arquivos'] > 5000:
        print(f"{Cor.AMARELO}3. VENV MUITO GRANDE:{Cor.RESET}")
        print(f"   Seu venv/ tem {venv_info['arquivos']:,} arquivos!")
        print(f"   Isso é ANORMAL para um projeto Python simples.")
        print(f"   {Cor.BOLD}RECOMENDAÇÃO:{Cor.RESET} Recriar venv do zero:")
        print(f"   {Cor.DIM}rm -rf venv{Cor.RESET}")
        print(f"   {Cor.DIM}python3 -m venv venv{Cor.RESET}")
        print(f"   {Cor.DIM}source venv/bin/activate{Cor.RESET}")
        print(f"   {Cor.DIM}pip install -r requirements.txt{Cor.RESET}\n")
    
    print(f"{Cor.VERDE}✅ Diagnóstico concluído!{Cor.RESET}\n")

# ═══════════════════════════════════════════════════════════════════════
# EXECUÇÃO
# ═══════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    try:
        diagnosticar_projeto()
    except KeyboardInterrupt:
        print(f"\n\n{Cor.AMARELO}Diagnóstico cancelado pelo usuário.{Cor.RESET}\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Cor.VERMELHO}ERRO: {e}{Cor.RESET}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
