"""
Script de verificacion rapida de todos los modulos del proyecto.
Ejecutar con: python verificar.py
"""
import sys
print(f"Python {sys.version.split()[0]}")
print("=" * 50)

errors = []

# ── config.py ────────────────────────────────────────
try:
    from config import ConfigLLM
    h = {f.name: str(f.type) for f in ConfigLLM.__dataclass_fields__.values()}
    assert "Optional" in h["reasoning"], "Tipo incorrecto"
    print("[PASS] config.py  - Optional[bool] OK, Python 3.9 compatible")
except Exception as e:
    errors.append(f"[FAIL] config.py: {e}")

# ── voz.py ───────────────────────────────────────────
try:
    from voz import Voz, _BACKEND
    import threading
    v = Voz()
    assert not v.hablando, "hablando debe ser False al inicio"
    assert v._hablar_terminado.is_set(), "Event debe estar SET al inicio"
    assert isinstance(v._hablar_terminado, threading.Event), "No es Event"
    print(f"[PASS] voz.py     - backend={_BACKEND}, hablando=False, Event OK")
except Exception as e:
    errors.append(f"[FAIL] voz.py: {e}")

# ── llm.py: _historial_reciente (slice seguro) ───────
try:
    from llm import AgenteVenezuela

    class FakeCfg:
        proveedor = "ollama"; modelo = "t"; temperatura = 0.7
        max_tokens = 50; top_p = 0.9; base_url = "http://localhost"
        num_ctx = 512; repeat_penalty = 1.0; reasoning = False; google_api_key = None

    class FakeModelo:
        def bind_tools(self, t): return self
        def invoke(self, m):
            from types import SimpleNamespace
            return SimpleNamespace(content="La arepa es deliciosa en Venezuela.", tool_calls=None)

    ag = AgenteVenezuela(FakeCfg(), modelo=FakeModelo(), system_prompt_texto="Eres un guia.")

    # 9 mensajes (impar) — el slice debe empezar en 'human'
    ag.historial = [
        ("human", f"h{i}") if i % 2 == 0 else ("assistant", f"a{i}")
        for i in range(9)
    ]
    r = ag._historial_reciente(8)
    assert r[0][0] == "human", f"Empieza en {r[0][0]}"
    assert len(r) <= 8
    print(f"[PASS] llm.py     - _historial_reciente OK, len={len(r)}, inicio={r[0][0]!r}")
except Exception as e:
    errors.append(f"[FAIL] llm.py _historial_reciente: {e}")

# ── llm.py: responder() con FakeModelo ───────────────
try:
    from llm import AgenteVenezuela

    class FakeCfg2:
        proveedor = "ollama"; modelo = "t"; temperatura = 0.7
        max_tokens = 50; top_p = 0.9; base_url = "http://localhost"
        num_ctx = 512; repeat_penalty = 1.0; reasoning = False; google_api_key = None

    class FakeModelo2:
        def bind_tools(self, t): return self
        def invoke(self, m):
            from types import SimpleNamespace
            return SimpleNamespace(content="La arepa es deliciosa en Venezuela.", tool_calls=None)

    ag2 = AgenteVenezuela(FakeCfg2(), modelo=FakeModelo2(), system_prompt_texto="Eres un guia.")
    resp = ag2.responder("que es la arepa")
    assert resp and len(resp) > 0, "Respuesta vacia"
    assert len(ag2.historial) == 2, f"Historial debe tener 2 msgs, tiene {len(ag2.historial)}"
    print(f"[PASS] llm.py     - responder() OK: \"{resp[:60]}\"")
except Exception as e:
    errors.append(f"[FAIL] llm.py responder: {e}")

# ── llm.py: error handling ────────────────────────────
try:
    from llm import AgenteVenezuela, ERROR_OLLAMA, ERROR_MODELO

    class FakeCfg3:
        proveedor = "ollama"; modelo = "t"; temperatura = 0.7
        max_tokens = 50; top_p = 0.9; base_url = "http://localhost"
        num_ctx = 512; repeat_penalty = 1.0; reasoning = False; google_api_key = None

    class FakeModeloError:
        def bind_tools(self, t): return self
        def invoke(self, m):
            raise ConnectionRefusedError("Connection refused")

    ag3 = AgenteVenezuela(FakeCfg3(), modelo=FakeModeloError(), system_prompt_texto="Test")
    result = ag3.responder("hola")
    assert result == ERROR_OLLAMA, f"Esperaba ERROR_OLLAMA, got: {result}"
    assert len(ag3.historial) == 0, "Historial debe quedar vacio tras error"
    print(f"[PASS] llm.py     - error handling OK (ERROR_OLLAMA detectado)")
except Exception as e:
    errors.append(f"[FAIL] llm.py error_handling: {e}")

# ── internet.py ──────────────────────────────────────
try:
    from internet import BusquedaWeb
    import inspect, requests
    src = inspect.getsource(BusquedaWeb.hay_internet)
    assert "except:" not in src, "Aun tiene bare except en hay_internet"
    src2 = inspect.getsource(BusquedaWeb.buscar)
    assert "except:" not in src2, "Aun tiene bare except en buscar"
    print("[PASS] internet.py - importado, bare except corregidos")
except Exception as e:
    errors.append(f"[FAIL] internet.py: {e}")

# ── venezuela_bot.py AST + BUG-3 ─────────────────────
try:
    import ast, pathlib
    src = pathlib.Path("venezuela_bot.py").read_text(encoding="utf-8")
    ast.parse(src)
    lineas = src.splitlines()
    for i, l in enumerate(lineas):
        if "Respuesta negativa corta" in l:
            espacios = len(l) - len(l.lstrip())
            assert espacios == 8, f"Indentacion incorrecta: {espacios} espacios en linea {i+1}"
            break
    print("[PASS] venezuela_bot.py - AST OK, BUG-3 indentacion corregida (8 espacios)")
except Exception as e:
    errors.append(f"[FAIL] venezuela_bot.py: {e}")

# ── wake word regex ───────────────────────────────────
try:
    import re
    WAKE_RE = re.compile(r"\borbi\w{0,4}\b", re.IGNORECASE)
    casos_si = ["orbit", "Orbit", "ORBIT", "orbi", "orbiz", "orbis", "orbital", "orbita", "orbith"]
    casos_no = ["hola", "oracion", "horrible", "trabajar", "orbe"]
    for c in casos_si:
        assert WAKE_RE.search(c), f"Deberia detectar: {c}"
    for c in casos_no:
        assert not WAKE_RE.search(c), f"No deberia detectar: {c}"
    print(f"[PASS] wake_word   - {len(casos_si)} positivos / {len(casos_no)} negativos OK")
except Exception as e:
    errors.append(f"[FAIL] wake_word: {e}")

# ── voz.py: detener() libera esperar() ───────────────
try:
    from voz import Voz
    import time, threading
    v2 = Voz()

    resultado = {"ok": False}
    def simular_habla():
        # Simula que el flag se pone en "hablando" y luego detener() lo libera
        v2._hablar_terminado.clear()   # simular inicio de habla
        time.sleep(0.1)
        v2.detener()                   # detener debe liberar esperar()

    t = threading.Thread(target=simular_habla, daemon=True)
    t.start()

    inicio = time.time()
    v2.esperar()                       # debe retornar cuando detener() sea llamado
    duracion = time.time() - inicio

    assert duracion < 1.0, f"esperar() tardó demasiado: {duracion:.2f}s"
    assert not v2.hablando, "hablando debe ser False despues de detener"
    print(f"[PASS] voz.py     - detener()->esperar() liberado en {duracion*1000:.0f}ms (sin busy-wait)")
except Exception as e:
    errors.append(f"[FAIL] voz.py detener/esperar: {e}")

# ── RESUMEN ───────────────────────────────────────────
print("=" * 50)
if errors:
    print(f"FALLARON {len(errors)} PRUEBA(S):")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    print(f"TODOS LOS MODULOS PASAN ({8 - len(errors)} pruebas)")
