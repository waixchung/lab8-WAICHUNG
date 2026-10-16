#!/usr/bin/env python3
"""
Autograde - Laboratorio #8 (Desarrollo Web, Módulo III, Unidad II: PHP 3.5, 3.6 y 3.7)

Califica la rúbrica de 100 puntos, detecta señales de plagio y registra el resultado
en Supabase mediante la función RPC `registrar_lab8` (ver docente/supabase_lab8.sql).

DOCENTE: completa SUPABASE_URL y SUPABASE_ANON_KEY, y luego registra el SHA-256 de ESTE
archivo en la tabla lab8_config (ver docente/INSTRUCCIONES_DOCENTE.md).
"""
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

# ----------------------------------------------------------------------------------
# CONFIGURACIÓN DEL DOCENTE
# ----------------------------------------------------------------------------------
SUPABASE_URL = "https://ikusdplwwvcbxgvevkvw.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlrdXNkcGx3d3ZjYnhndmV2a3Z3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg5ODgyMjYsImV4cCI6MjEwNDU2NDIyNn0.TEA3ZOmZxv7zedc2hDZUaDoB0oGDVMXM2yh1M6D4YBc"

SEMILLA = "WEB2026-L8"
MIN_MINUTOS_TRABAJO = 40
MIN_COMMITS = 6 
# ----------------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
RESULTADO = ROOT / "resultado.json"
SIN_BD = os.environ.get("LAB_SIN_BD") == "1"          # solo para pruebas locales
REGISTRAR = os.environ.get("REGISTRAR", "false").lower() == "true"
PLACEHOLDERS = {"", "...", "-", "_", "n/a", "na", "xxx", "pendiente"}


# ----------------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------------
class Rubrica:
    def __init__(self):
        self.items = []     # (etapa, criterio, maximo, obtenido, nota)
        self.alertas = []   # señales de plagio / integridad

    def punto(self, etapa, criterio, maximo, obtenido, nota=""):
        obtenido = max(0, min(maximo, round(obtenido, 2)))
        self.items.append({"etapa": etapa, "criterio": criterio, "max": maximo,
                           "obtenido": obtenido, "nota": nota})

    def alerta(self, texto):
        self.alertas.append(texto)

    def total(self):
        return round(sum(i["obtenido"] for i in self.items), 2)

    def maximo(self):
        return sum(i["max"] for i in self.items)


def ejecutar(cmd, **kw):
    kw.setdefault("cwd", ROOT)
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    kw.setdefault("timeout", 30)
    try:
        return subprocess.run(cmd, **kw)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return subprocess.CompletedProcess(cmd, 99, "", str(e))


def leer(ruta):
    p = ROOT / ruta
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else None


def sin_placeholder(valor):
    return valor.strip().strip("*_ ").lower() not in PLACEHOLDERS


def palabras(texto):
    return re.findall(r"[a-záéíóúñü0-9_]+", texto.lower())


def derivar(cedula):
    """Valores únicos por estudiante, calculados igual que en PHP (ver README, Etapa 3)."""
    h = hashlib.sha256(f"{cedula}|{SEMILLA}".encode()).hexdigest()
    n1 = int(h[8:10], 16) % 90 + 10
    n2 = int(h[10:12], 16) % 90 + 10
    return {
        "huella": h,
        "codigo": h[:8],
        "n1": n1,
        "n2": n2,
        "precio": round(int(h[12:16], 16) / 100, 2),
        "activo": n1 % 2 == 0,
        "suma": n1 + n2,
        "division": round(n1 / n2, 2),
        "resto": n1 % n2,
        "cociente": n1 // n2,
    }


def token_entorno(est):
    h = hashlib.sha256(f"{est['cedula']}|{est['github_user']}|{SEMILLA}".encode()).hexdigest()
    return h[:10]


def cercano(a, b, tol=0.011):
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def tokenizar_php(ruta):
    r = ejecutar(["php", "autograde/tokenizar.php", ruta])
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def tipo_comentario(c):
    c = c.lstrip()
    if c.startswith("//"):
        return "//"
    if c.startswith("#"):
        return "#"
    if c.startswith("/*"):
        return "/*"
    return "?"


# ----------------------------------------------------------------------------------
# Huella de código (MinHash) para detectar similitud sin exponer el código
# ----------------------------------------------------------------------------------
_P = (1 << 61) - 1


def _params(n=128):
    out = []
    for i in range(n):
        d = hashlib.sha256(f"mh{i}".encode()).digest()
        out.append((int.from_bytes(d[:8], "big") % (_P - 1) + 1, int.from_bytes(d[8:16], "big") % _P))
    return out


_PARAMS = _params()


def minhash(tokens, k=3):
    if len(tokens) < 12:
        return None
    shingles = {" ".join(tokens[i:i + k]) for i in range(len(tokens) - k + 1)}
    hs = [int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8).digest(), "big") % _P for s in shingles]
    return [min((a * h + b) % _P for h in hs) for a, b in _PARAMS]


def tokens_libres_php(tok):
    """Solo lo que el estudiante escribe libremente: comentarios, cadenas y nombres de variables."""
    partes = []
    for c in tok["comentarios"]:
        partes.append(re.sub(r"^\s*(//|#|/\*+|\*+/|\*)", " ", c))
    partes.extend(tok["cadenas"])
    partes.extend(v.lstrip("$") for v in tok["variables"])
    return palabras(" ".join(partes))


# ----------------------------------------------------------------------------------
# ETAPA 0: estudiante.json
# ----------------------------------------------------------------------------------
def cargar_estudiante(rub):
    txt = leer("estudiante.json")
    try:
        est = json.loads(txt or "{}")
    except json.JSONDecodeError:
        est = {}
    claves = ["nombre", "apellido", "cedula", "github_user"]
    ok = all(isinstance(est.get(k), str) and est[k].strip() for k in claves)
    rub.punto("E0", "estudiante.json completo (nombre, apellido, cédula, usuario GitHub)", 0, 0,
              "OK" if ok else "Incompleto: el resto del autograde no puede calcular tus valores")
    if not ok:
        return None
    est = {k: est[k].strip() for k in claves}
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
    if owner and owner.lower() != est["github_user"].lower():
        rub.alerta(f"github_user ({est['github_user']}) no coincide con el dueño del repositorio ({owner})")
    return est


# ----------------------------------------------------------------------------------
# ETAPA 1 (25 pts): instalación del servidor web, PHP y base de datos (3.6)
# ----------------------------------------------------------------------------------
def etapa1(rub, est, extra):
    # 1a. instalacion.md (3 pts) + capturas (2 pts)
    md = leer("evidencias/instalacion.md") or ""
    claves = ["sistema operativo", "paquete usado", "versión de php", "servidor web",
              "base de datos", "puerto del servidor web", "ruta de instalación"]
    valores = {}
    for linea in md.splitlines():
        m = re.match(r"\s*-\s*\*\*(.+?):\*\*\s*(.*)", linea)
        if m:
            valores[m.group(1).strip().lower()] = m.group(2).split("  (")[0].strip()
    llenos = sum(1 for k in claves if k in valores and sin_placeholder(valores[k]))
    problema = valores.get("problema encontrado y cómo lo resolviste", "")
    problema_ok = len(palabras(problema)) >= 15 and sin_placeholder(problema)
    pts = 3 * (llenos / len(claves)) * (1 if problema_ok else 0.8)
    rub.punto("E1", "instalacion.md completo y con tus palabras", 3, pts,
              f"{llenos}/{len(claves)} campos; problema {'ok' if problema_ok else 'incompleto (<15 palabras)'}")
    extra["version_md"] = re.search(r"\d+\.\d+(\.\d+)?", valores.get("versión de php", ""))
    extra["version_md"] = extra["version_md"].group(0) if extra["version_md"] else None

    caps = []
    for nombre in ("phpinfo.png", "phpmyadmin.png"):
        p = ROOT / "evidencias" / nombre
        if p.is_file() and p.stat().st_size > 15_000:
            caps.append(hashlib.sha256(p.read_bytes()).hexdigest())
    rub.punto("E1", "Capturas evidencias/phpinfo.png y evidencias/phpmyadmin.png", 2, len(caps),
              f"{len(caps)}/2 válidas (la revisión visual es del docente)")
    extra["hash_capturas"] = caps

    # 1b. base_datos.sql se importa en un MySQL real (5 pts)
    sql = leer("evidencias/base_datos.sql") or ""
    if SIN_BD or not shutil.which("mysql"):
        rub.punto("E1", "base_datos.sql se importa y contiene tu fila", 5, 0, "No evaluado (sin MySQL en este entorno)")
    else:
        base = ["mysql", "-h127.0.0.1", "-P3306", "-uroot", "-proot"]
        ejecutar(base + ["-e", "DROP DATABASE IF EXISTS lab8_web"])
        imp = ejecutar(base, input=sql)
        if imp.returncode != 0:
            rub.punto("E1", "base_datos.sql se importa y contiene tu fila", 5, 0,
                      "Error al importar: " + (imp.stderr or "").strip()[:160])
        else:
            q = ejecutar(base + ["-N", "-B", "-e",
                                 "SELECT cedula, codigo FROM lab8_web.estudiantes"])
            filas = [l.split("\t") for l in q.stdout.strip().splitlines()] if q.returncode == 0 else []
            d = derivar(est["cedula"])
            propia = [f for f in filas if len(f) == 2 and f[0] == est["cedula"]]
            ok_cod = bool(propia) and propia[0][1] == d["codigo"]
            rub.punto("E1", "base_datos.sql se importa y contiene tu fila", 5,
                      3 + (2 if ok_cod else 0),
                      "Importa bien; " + ("tu fila y código correctos" if ok_cod else
                      "falta tu fila en lab8_web.estudiantes o el código no coincide con tu fórmula"))

    # 1c. entorno.php ejecutado en el CI con conexión real a la BD (5 pts)
    if SIN_BD or not shutil.which("mysql"):
        rub.punto("E1", "entorno.php conecta a la BD y devuelve el JSON esperado", 5, 0,
                  "No evaluado (sin MySQL en este entorno)")
    else:
        cfg = ROOT / "config" / "db.php"
        cfg.write_text("<?php\nreturn ['host'=>'127.0.0.1','user'=>'root','pass'=>'root',"
                       "'name'=>'lab8_web','port'=>3306];\n")
        r = ejecutar(["php", "public/entorno.php"])
        cfg.unlink(missing_ok=True)
        pts, nota = 0, ""
        try:
            j = json.loads(r.stdout)
            claves = {"php_version", "sapi", "os_family", "servidor", "mysqli", "db_version",
                      "db_nombre", "filas", "token"}
            falt = claves - set(j)
            pts += 1.5 if not falt else 0
            pts += 1 if j.get("mysqli") is True else 0
            pts += 1 if str(j.get("db_version", "")).strip() and j.get("db_nombre") == "lab8_web" else 0
            pts += 0.5 if isinstance(j.get("filas"), int) and j["filas"] >= 1 else 0
            pts += 1 if j.get("token") == token_entorno(est) else 0
            nota = f"faltan claves {sorted(falt)}" if falt else "estructura completa"
        except (json.JSONDecodeError, TypeError):
            nota = "la salida no es un JSON válido: " + (r.stdout + r.stderr).strip()[:140]
        rub.punto("E1", "entorno.php conecta a la BD y devuelve el JSON esperado", 5, pts, nota)

    # 1d. entorno_salida.json: evidencia servida por TU servidor web (10 pts)
    txt = leer("evidencias/entorno_salida.json")
    pts, notas = 0, []
    try:
        j = json.loads(txt or "")
        pts += 2
        ver = str(j.get("php_version", ""))
        m = re.match(r"(\d+)\.(\d+)", ver)
        if m and (int(m.group(1)), int(m.group(2))) >= (8, 1):
            pts += 2
        else:
            notas.append("PHP < 8.1")
        sapi = str(j.get("sapi", "")).lower()
        if sapi in ("apache2handler", "fpm-fcgi", "cgi-fcgi", "litespeed"):
            pts += 3
        elif sapi == "cli-server":
            pts += 1
            notas.append("cli-server: usaste el servidor embebido, no Apache/Nginx")
        else:
            notas.append(f"sapi '{sapi}' no demuestra un servidor web")
        if re.search(r"apache|nginx", str(j.get("servidor", "")), re.I):
            pts += 1
        if j.get("mysqli") is True and str(j.get("db_version", "")).strip():
            pts += 1
        if j.get("token") == token_entorno(est):
            pts += 1
        else:
            notas.append("token incorrecto")
            rub.alerta("entorno_salida.json: token no corresponde a este estudiante")
        if extra.get("version_md") and ver and not ver.startswith(extra["version_md"]):
            rub.alerta(f"Versión de PHP distinta entre instalacion.md ({extra['version_md']}) y entorno_salida.json ({ver})")
    except json.JSONDecodeError:
        notas.append("entorno_salida.json no es JSON válido o no existe")
    rub.punto("E1", "entorno_salida.json generado desde tu servidor web", 10, pts, "; ".join(notas) or "OK")


# ----------------------------------------------------------------------------------
# ETAPA 2 (20 pts): Introducción a PHP - public/index.php (3.5)
# ----------------------------------------------------------------------------------
def etapa2(rub, est, extra):
    ruta = "public/index.php"
    if not (ROOT / ruta).is_file():
        rub.punto("E2", "public/index.php", 20, 0, "No existe")
        return
    tok = tokenizar_php(ruta)
    r = ejecutar(["php", ruta])
    salida = r.stdout
    low = salida.lower()

    ok_html = r.returncode == 0 and "<!doctype html>" in low and "<html" in low and "</html>" in low \
        and re.search(r"<title>[^<]*lab\s*8[^<]*</title>", salida, re.I) is not None \
        and est["apellido"].lower() in re.search(r"<title>(.*?)</title>", salida, re.I | re.S).group(1).lower()
    rub.punto("E2", "Página HTML5 válida; <title> con 'Lab 8' y tu apellido", 4, 4 if ok_html else (1.5 if r.returncode == 0 and "<html" in low else 0),
              "OK" if ok_html else ("Error de ejecución: " + r.stderr.strip()[:120] if r.returncode else "Revisa doctype/html/title"))
    rub.punto("E2", "Muestra tu nombre y apellido leídos de estudiante.json", 3,
              3 if est["nombre"].lower() in low and est["apellido"].lower() in low else 0)
    ver = ejecutar(["php", "-r", "echo PHP_VERSION;"]).stdout.strip()
    rub.punto("E2", "Muestra la versión de PHP (PHP_VERSION / phpversion())", 3, 3 if ver and ver in salida else 0)

    ahora = datetime.datetime.now(ZoneInfo("America/Panama"))
    fechas = {(ahora + datetime.timedelta(days=d)).strftime("%d/%m/%Y") for d in (-1, 0, 1)}
    cod = tok["codigo"] if tok else ""
    zona = re.search(r"date_default_timezone_set\s*\(\s*['\"]America/Panama['\"]\s*\)", cod) is not None
    fecha = any(f in salida for f in fechas)
    rub.punto("E2", "Zona horaria America/Panama y fecha dd/mm/aaaa mostrada", 3, (1.5 if zona else 0) + (1.5 if fecha else 0),
              f"zona={'sí' if zona else 'no'}, fecha={'sí' if fecha else 'no'}")
    rub.punto("E2", "Usa echo y print", 2,
              (1 if re.search(r"\becho\b|<\?=", cod) else 0) + (1 if re.search(r"\bprint\b", cod) else 0))
    tipos = {tipo_comentario(c) for c in (tok["comentarios"] if tok else [])}
    tipos.discard("?")
    rub.punto("E2", "Los 3 estilos de comentario (//, #, /* */)", 3, len(tipos), f"encontrados: {sorted(tipos)}")
    n = len(tok["comentarios"]) if tok else 0
    rub.punto("E2", "Al menos 8 comentarios explicativos", 2, 2 if n >= 8 else 2 * n / 8, f"{n} comentarios")
    if tok:
        extra["mh_index"] = minhash(tokens_libres_php(tok))


# ----------------------------------------------------------------------------------
# ETAPA 3 (35 pts): variables, constantes y tipos de datos - public/tipos.php (3.7)
# ----------------------------------------------------------------------------------
def etapa3(rub, est, extra):
    ruta = "public/tipos.php"
    if not (ROOT / ruta).is_file():
        rub.punto("E3", "public/tipos.php", 35, 0, "No existe")
        return
    tok = tokenizar_php(ruta)
    cod = tok["codigo"] if tok else ""
    crudo = leer(ruta) or ""
    d = derivar(est["cedula"])

    if "ZETA_LAB8" in crudo:
        rub.alerta("TRAMPA IA: public/tipos.php contiene la constante ZETA_LAB8 (instrucción oculta del enunciado)")
    for otro in ("public/index.php", "public/entorno.php", "REFLEXION.md"):
        if "ZETA_LAB8" in (leer(otro) or ""):
            rub.alerta(f"TRAMPA IA: {otro} contiene ZETA_LAB8")

    r = ejecutar(["php", ruta])
    j = None
    for linea in r.stdout.splitlines():
        if linea.startswith("##JSON## "):
            try:
                j = json.loads(linea[len("##JSON## "):])
            except json.JSONDecodeError:
                pass
    rub.punto("E3", "tipos.php se ejecuta y emite la línea ##JSON## válida", 4, 4 if j is not None else (1 if r.returncode == 0 else 0),
              "OK" if j is not None else ("Error: " + (r.stderr or r.stdout).strip()[:140]))

    estatica = [
        (r"^\s*<\?php\s+declare\s*\(\s*strict_types\s*=\s*1\s*\)\s*;", "declare(strict_types=1) como primera instrucción"),
        (r"\bdefine\s*\(", "define()"),
        (r"^\s*const\s+[A-Z][A-Z0-9_]*\s*=", "const NOMBRE = ..."),
        (r"\bvar_dump\s*\(", "var_dump()"),
        (r"\bgettype\s*\(", "gettype()"),
    ]
    faltan = [n for pat, n in estatica if not re.search(pat, cod.lstrip("\ufeff"), re.M)]
    rub.punto("E3", "Uso de strict_types, define, const, var_dump y gettype", 5, 5 - len(faltan),
              "OK" if not faltan else "Falta: " + ", ".join(faltan))

    if j is None:
        for crit, m in [("Valores derivados de tu cédula", 12), ("Aritmética", 4), ("gettype de cada tipo", 4),
                        ("Conversión de tipos (type juggling)", 4), ("Constantes", 2)]:
            rub.punto("E3", crit, m, 0, "Sin JSON")
        if tok:
            extra["mh_tipos"] = minhash(tokens_libres_php(tok))
        return

    # valores derivados (12)
    v = 0
    v += 3 if j.get("codigo") == d["codigo"] else 0
    v += 2 if j.get("n1") == d["n1"] and isinstance(j.get("n1"), int) else 0
    v += 2 if j.get("n2") == d["n2"] and isinstance(j.get("n2"), int) else 0
    v += 3 if cercano(j.get("precio"), d["precio"]) else 0
    v += 2 if j.get("activo") is d["activo"] else 0
    rub.punto("E3", "Valores derivados de TU cédula (codigo, n1, n2, precio, activo)", 12, v,
              "OK" if v == 12 else "Algún valor no coincide con la fórmula aplicada a tu cédula")

    # aritmética (4)
    a = 0
    a += 1 if j.get("suma") == d["suma"] else 0
    a += 1 if cercano(j.get("division"), d["division"]) else 0
    a += 1 if j.get("resto") == d["resto"] else 0
    a += 1 if j.get("cociente") == d["cociente"] else 0
    rub.punto("E3", "Aritmética: suma, division, resto, cociente (intdiv)", 4, a)

    # tipos (4)
    esperado_t = {"codigo": "string", "n1": "integer", "precio": "double", "activo": "boolean",
                  "nulo": "NULL", "lista": "array"}
    t = j.get("tipos") if isinstance(j.get("tipos"), dict) else {}
    ok_t = sum(1 for k, val in esperado_t.items() if t.get(k) == val)
    rub.punto("E3", "gettype() de string, integer, double, boolean, NULL y array", 4, 4 * ok_t / 6, f"{ok_t}/6")

    # juggling (4)
    esperado_j = {"suma_str": 15, "concat": "510", "cast_int": 12, "float_eq": False, "loose": True, "strict": False}
    g = j.get("juggling") if isinstance(j.get("juggling"), dict) else {}
    ok_j = sum(1 for k, val in esperado_j.items() if k in g and g[k] == val and type(g[k]) is type(val))
    rub.punto("E3", "Conversión de tipos: \"5\"+\"10\", \"5\".\"10\", (int)\"12abc\", 0.1+0.2==0.3, == vs ===", 4,
              4 * ok_j / 6, f"{ok_j}/6")

    # constantes (2)
    c = j.get("constantes") if isinstance(j.get("constantes"), dict) else {}
    ok_c = (c.get("SEMILLA_LAB8") == SEMILLA) + (c.get("LAB_NUMERO") == 8) + (c.get("redefinir") is False)
    rub.punto("E3", "Constantes SEMILLA_LAB8 (define), LAB_NUMERO (const) y redefinición rechazada", 2, 2 * ok_c / 3, f"{ok_c}/3")

    if tok:
        extra["mh_tipos"] = minhash(tokens_libres_php(tok))


# ----------------------------------------------------------------------------------
# ETAPA 4 (10 pts): REFLEXION.md
# ----------------------------------------------------------------------------------
def etapa4(rub, est, extra):
    txt = leer("REFLEXION.md") or ""
    d = derivar(est["cedula"])
    partes = re.split(r"^##\s*Pregunta\s*\d\s*$", txt, flags=re.M | re.I)[1:]
    largas = sum(1 for p in partes[:3] if len(palabras(p)) >= 40)
    rub.punto("E4", "REFLEXION.md existe y no es la plantilla vacía", 1, 1 if len(palabras(txt)) > 60 else 0)
    rub.punto("E4", "Las 3 respuestas tienen al menos 40 palabras", 3, largas)
    rub.punto("E4", "Menciona TU código personal de 8 caracteres", 3, 3 if d["codigo"] in txt.lower() else 0,
              "OK" if d["codigo"] in txt.lower() else "No aparece tu código personal en la reflexión")
    rub.punto("E4", "Usa los términos 'double' e 'integer' correctamente", 2,
              (1 if "double" in txt.lower() else 0) + (1 if "integer" in txt.lower() else 0))
    distintas = len(partes) >= 3 and len({" ".join(palabras(x)) for x in partes[:3]}) == 3
    rub.punto("E4", "Respuestas distintas entre sí y sin texto de relleno", 1,
              1 if distintas and "lorem" not in txt.lower() else 0)
    extra["mh_reflexion"] = minhash(palabras(txt))
    if "zeta_lab8" in txt.lower():
        rub.alerta("TRAMPA IA: REFLEXION.md menciona ZETA_LAB8")


# ----------------------------------------------------------------------------------
# ETAPA 5 (10 pts): disciplina con Git
# ----------------------------------------------------------------------------------
def etapa_git(rub, est, extra):
    meta = ejecutar(["git", "log", "--reverse", "--no-merges", "--pretty=format:%H%x09%an%x09%ae%x09%at%x09%s"])
    commits = []
    for linea in meta.stdout.splitlines():
        partes = linea.split("\t")
        if len(partes) < 5:
            continue
        h, an, ae, at, s = partes[:5]
        if s.strip().lower().startswith("initial commit"):
            continue
        ns = ejecutar(["git", "show", "--numstat", "--format=", h]).stdout
        add = 0
        for l in ns.splitlines():
            p = l.split("\t")
            if len(p) == 3 and p[0].isdigit() and re.search(r"\.(php|md|sql|json)$", p[2]):
                add += int(p[0])
        commits.append({"h": h, "autor": an, "email": ae, "t": int(at), "msg": s, "add": add})

    n = len(commits)
    rub.punto("G", f"Al menos {MIN_COMMITS} commits propios", 3, 3 if n >= MIN_COMMITS else 3 * n / MIN_COMMITS, f"{n} commits")
    etapas = {m.group(1).upper() for c in commits if (m := re.match(r"\[(E[0-4])[a-z]?\]", c["msg"], re.I))}
    rub.punto("G", "Mensajes con etiqueta [E0] a [E4]", 2, 2 * len(etapas) / 5, f"etapas: {sorted(etapas)}")
    minutos = (commits[-1]["t"] - commits[0]["t"]) / 60 if n >= 2 else 0
    rub.punto("G", f"Trabajo distribuido en el tiempo (≥ {MIN_MINUTOS_TRABAJO} min entre primer y último commit)", 2,
              2 if minutos >= MIN_MINUTOS_TRABAJO else 2 * minutos / MIN_MINUTOS_TRABAJO, f"{minutos:.0f} min")
    total = sum(c["add"] for c in commits)
    mayor = max((c["add"] for c in commits), default=0)
    reparto_ok = total > 0 and mayor / total <= 0.5
    rub.punto("G", "Ningún commit concentra más del 50 % de las líneas", 2, 2 if reparto_ok else 0,
              f"mayor commit = {100 * mayor / total:.0f} %" if total else "sin líneas")
    autores = {c["email"].lower() for c in commits}
    rub.punto("G", "Todos los commits provienen de una sola cuenta", 1, 1 if len(autores) == 1 else 0)

    if n < MIN_COMMITS:
        rub.alerta(f"Historial insuficiente: {n} commits (mínimo {MIN_COMMITS})")
    if n >= 2 and minutos < MIN_MINUTOS_TRABAJO:
        rub.alerta(f"Laboratorio de 90 min completado en solo {minutos:.0f} min de historial")
    if total and not reparto_ok:
        rub.alerta(f"Un solo commit concentra {100 * mayor / total:.0f} % del código (posible pegado masivo)")
    if len(autores) > 1:
        rub.alerta("Commits de más de una cuenta/correo: " + ", ".join(sorted(autores)))


# ----------------------------------------------------------------------------------
# Supabase
# ----------------------------------------------------------------------------------
def registrar(rub, est, extra):
    payload = {
        "nombre": est["nombre"], "apellido": est["apellido"], "cedula": est["cedula"],
        "github_user": est["github_user"],
        "repo": os.environ.get("GITHUB_REPOSITORY", ""), "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "nota_final": rub.total(), "detalle": rub.items, "alertas": rub.alertas,
        "autograde_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "hash_capturas": extra.get("hash_capturas", []),
        "mh_index": extra.get("mh_index"), "mh_tipos": extra.get("mh_tipos"),
        "mh_reflexion": extra.get("mh_reflexion"),
    }
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/rpc/registrar_lab8",
        data=json.dumps({"p": payload}).encode(),
        headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                 "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


# ----------------------------------------------------------------------------------
def main():
    rub = Rubrica()
    extra = {}
    est = cargar_estudiante(rub)
    if est is None:
        print("::error::Completa estudiante.json (nombre, apellido, cedula, github_user)")
        RESULTADO.write_text(json.dumps({"error": "estudiante.json incompleto"}))
        return 0

    etapa1(rub, est, extra)
    etapa2(rub, est, extra)
    etapa3(rub, est, extra)
    etapa4(rub, est, extra)
    etapa_git(rub, est, extra)

    respuesta = None
    if REGISTRAR and not SIN_BD:
        respuesta = registrar(rub, est, extra)
        if respuesta and respuesta.get("error"):
            print("::warning::No se pudo registrar en Supabase:", respuesta["error"])
        elif respuesta:
            if respuesta.get("similitud_max") is not None and respuesta.get("alerta_similitud"):
                rub.alerta(f"Similitud de código {respuesta['similitud_max']:.2f} con otro envío")
            if respuesta.get("capturas_repetidas"):
                rub.alerta("Una captura de pantalla es idéntica a la de otro estudiante")
            if respuesta.get("autograde_valido") is False:
                rub.alerta("El archivo autograde.py fue modificado")

    # ---- reporte ----
    lineas = [f"# Resultado Lab 8: {est['nombre']} {est['apellido']}", "",
              f"**Nota automática: {rub.total()} / {rub.maximo()}**", "",
              "| Etapa | Criterio | Pts | Máx | Detalle |", "|---|---|---|---|---|"]
    for i in rub.items:
        if i["max"] == 0:
            continue
        lineas.append(f"| {i['etapa']} | {i['criterio']} | {i['obtenido']} | {i['max']} | {i['nota']} |")
    lineas.append("")
    if REGISTRAR:
        if respuesta and not respuesta.get("error"):
            lineas.append(f"Registro oficial en Supabase: intento #{respuesta.get('intento')}.")
        else:
            lineas.append("**No se registró en Supabase** (avisa a tu docente).")
    else:
        lineas.append("Modo práctica: esta ejecución NO se registra. Para la entrega, el último commit debe llevar `[E4]`.")
    if rub.alertas:
        lineas += ["", "## Observaciones para el docente", *[f"- {a}" for a in rub.alertas]]
    reporte = "\n".join(lineas)
    print(reporte)
    resumen = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        Path(resumen).write_text(reporte, encoding="utf-8")
    RESULTADO.write_text(json.dumps({"nota": rub.total(), "items": rub.items, "alertas": rub.alertas,
                                     "registrado": bool(respuesta and not respuesta.get("error"))},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
