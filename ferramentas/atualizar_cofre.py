"""Atualiza o cofre.bin com o conteúdo local atual, sem pedir a senha.

Usa a chave interna salva em cofre-chave.json (gerada pelo app em Configurações → Cofre,
arquivo que fica só no computador e está no .gitignore). O cabeçalho do cofre — com a chave
interna embrulhada pela senha — é mantido, então a mesma senha continua abrindo o cofre e os
aparelhos já desbloqueados continuam funcionando.

Uso (na pasta UFBA-Assistente):  python ferramentas/atualizar_cofre.py
"""
import base64, gzip, json, os, sys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def ler_var(arquivo, var):
    t = open(os.path.join(RAIZ, arquivo), encoding="utf-8").read()
    a = t.index("window." + var + " = ") + len("window." + var + " = ")
    return json.loads(t[a:t.index(";\n", a)])

def main():
    kp = os.path.join(RAIZ, "cofre-chave.json")
    if not os.path.exists(kp):
        sys.exit("cofre-chave.json não encontrado — gere o cofre no app (Configurações → Cofre) e coloque o arquivo nesta pasta.")
    k = json.load(open(kp, encoding="utf-8"))
    if k.get("v") != 2: sys.exit("cofre-chave.json de versão desconhecida.")
    dk, cab = base64.b64decode(k["chave"]), base64.b64decode(k["cabecalho"])
    assert len(dk) == 32 and cab[:6] == b"UFBAC2" and len(cab) == 82, "chave ou cabeçalho inválidos"
    dados = {
        "QUESTOES_LOCAIS": ler_var("questoes-locais.js", "QUESTOES_LOCAIS"),
        "TEXTOS_LOCAIS": ler_var("questoes-locais.js", "TEXTOS_LOCAIS"),
        "FLASH_LOCAIS": ler_var("flashcards-locais.js", "FLASH_LOCAIS"),
        "NOTAS_APOSTILAS": ler_var("materiais-locais.js", "NOTAS_APOSTILAS"),
        "MATERIAIS_LOCAIS": ler_var("materiais-locais.js", "MATERIAIS_LOCAIS"),
    }
    iv = os.urandom(12)
    ct = AESGCM(dk).encrypt(iv, gzip.compress(json.dumps(dados, ensure_ascii=False).encode("utf-8")), None)
    open(os.path.join(RAIZ, "cofre.bin"), "wb").write(cab + iv + ct)
    # confere: abre de volta
    buf = open(os.path.join(RAIZ, "cofre.bin"), "rb").read()
    volta = json.loads(gzip.decompress(AESGCM(dk).decrypt(buf[82:94], buf[94:], None)))
    assert len(volta["QUESTOES_LOCAIS"]) == len(dados["QUESTOES_LOCAIS"])
    print(f"cofre.bin atualizado: {len(buf) / 1e6:.2f} MB · {len(volta['QUESTOES_LOCAIS'])} questões · {len(volta['FLASH_LOCAIS'])} flashcards")

if __name__ == "__main__":
    main()
